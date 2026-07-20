import { z } from "zod";
import { getAccessToken, refreshAccessToken } from "./auth-token";
import { MirraApiError, toMirraError, type MirraErrorCode } from "./errors";
import { apiErrorBodySchema } from "./schemas";

/**
 * Minimal typed HTTP client for the real backend. Every response is
 * validated with a Zod schema before it reaches application code.
 *
 * Auth model (backend-implementation-plan.md, Phase 0 item 1): the access
 * JWT is attached as an Authorization: Bearer header from in-memory storage;
 * on a 401 the client silently mints a fresh access token from the httpOnly
 * refresh cookie (via /auth/refresh) and retries the request once.
 */

export interface HttpClientOptions {
  baseUrl: string;
  /** Number of retries for idempotent GETs on retryable failures. */
  getRetries?: number;
}

const STATUS_TO_CODE: Record<number, MirraErrorCode> = {
  401: "unauthenticated",
  404: "product_not_found",
  409: "capture_token_used",
  410: "capture_session_expired",
  422: "validation_failed",
  429: "rate_limited",
  503: "api_degraded",
};

/** Backend error.code values translated into the UI's error taxonomy. */
const BODY_CODE_TO_CODE: Record<string, MirraErrorCode> = {
  unauthorized: "unauthenticated",
  token_expired: "unauthenticated",
  refresh_reuse: "unauthenticated",
  refresh_expired: "unauthenticated",
  invalid_credentials: "invalid_credentials",
  account_exists: "account_exists",
  already_paired: "capture_token_used",
  gone: "capture_session_expired",
  validation_error: "validation_failed",
  engine_unavailable: "api_degraded",
  service_unavailable: "api_degraded",
};

export class MirraHttpClient {
  readonly baseUrl: string;
  private getRetries: number;

  constructor(opts: HttpClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.getRetries = opts.getRetries ?? 2;
  }

  async request<T>(
    method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE",
    path: string,
    schema: z.ZodType<T>,
    body?: unknown,
  ): Promise<T> {
    return this.send(method, path, schema, () => ({
      headers: (body !== undefined
        ? { "Content-Type": "application/json" }
        : {}) as Record<string, string>,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }));
  }

  /** Multipart request — the browser sets the Content-Type boundary itself. */
  async postMultipart<T>(path: string, schema: z.ZodType<T>, form: FormData): Promise<T> {
    return this.send("POST", path, schema, () => ({ headers: {}, body: form }));
  }

  private async send<T>(
    method: string,
    path: string,
    schema: z.ZodType<T>,
    makePayload: () => { headers: Record<string, string>; body?: BodyInit },
  ): Promise<T> {
    const attempts = method === "GET" ? this.getRetries + 1 : 1;
    let refreshTried = false;
    let lastError: MirraApiError | null = null;

    for (let attempt = 0; attempt < attempts; attempt++) {
      try {
        const res = await this.fetchOnce(method, path, makePayload());

        if (res.status === 401 && !refreshTried && path !== "/auth/refresh") {
          refreshTried = true;
          const token = await refreshAccessToken(this.baseUrl);
          if (token) {
            const retried = await this.fetchOnce(method, path, makePayload());
            return await this.handleResponse(retried, path, schema);
          }
        }
        return await this.handleResponse(res, path, schema);
      } catch (err) {
        const mirraErr = toMirraError(err);
        if (!mirraErr.retryable || attempt === attempts - 1) throw mirraErr;
        lastError = mirraErr;
        await backoff(attempt);
      }
    }
    throw lastError ?? new MirraApiError("unknown", "Request failed");
  }

  private fetchOnce(
    method: string,
    path: string,
    payload: { headers: Record<string, string>; body?: BodyInit },
  ): Promise<Response> {
    const token = getAccessToken();
    return fetch(`${this.baseUrl}${path}`, {
      method,
      // Cookies only matter for /auth/* (refresh cookie is path-scoped) but
      // including them everywhere is harmless and keeps this simple.
      credentials: "include",
      headers: {
        ...payload.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: payload.body,
      cache: "no-store",
    });
  }

  private async handleResponse<T>(res: Response, path: string, schema: z.ZodType<T>): Promise<T> {
    if (!res.ok) {
      let code: MirraErrorCode = STATUS_TO_CODE[res.status] ?? "unknown";
      let message = `Request failed (${res.status})`;
      try {
        const parsed = apiErrorBodySchema.safeParse(await res.json());
        if (parsed.success) {
          code = BODY_CODE_TO_CODE[parsed.data.error.code] ?? code;
          message = parsed.data.error.message;
        }
      } catch {
        // non-JSON error body — keep defaults
      }
      throw new MirraApiError(code, message, res.status);
    }

    if (res.status === 204) return schema.parse(undefined as unknown);
    const json = await res.json();
    const parsed = schema.safeParse(json);
    if (!parsed.success) {
      throw new MirraApiError(
        "validation_failed",
        `Response for ${path} did not match the expected contract.`,
        500,
      );
    }
    return parsed.data;
  }

  get<T>(path: string, schema: z.ZodType<T>) {
    return this.request("GET", path, schema);
  }
  post<T>(path: string, schema: z.ZodType<T>, body?: unknown) {
    return this.request("POST", path, schema, body);
  }
  patch<T>(path: string, schema: z.ZodType<T>, body?: unknown) {
    return this.request("PATCH", path, schema, body);
  }
  put<T>(path: string, schema: z.ZodType<T>, body?: unknown) {
    return this.request("PUT", path, schema, body);
  }
  delete<T>(path: string, schema: z.ZodType<T>) {
    return this.request("DELETE", path, schema);
  }
}

function backoff(attempt: number): Promise<void> {
  return new Promise((r) => setTimeout(r, 250 * 2 ** attempt));
}
