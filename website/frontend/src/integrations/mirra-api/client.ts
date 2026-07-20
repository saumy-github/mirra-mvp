import { z } from "zod";
import { MirraApiError, toMirraError, type MirraErrorCode } from "./errors";
import { apiErrorBodySchema } from "./schemas";

/**
 * Minimal typed HTTP client. Every response is validated with a Zod schema
 * before it reaches application code. Credentials ride on the session cookie.
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

export class MirraHttpClient {
  private baseUrl: string;
  private getRetries: number;

  constructor(opts: HttpClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.getRetries = opts.getRetries ?? 2;
  }

  async request<T>(
    method: "GET" | "POST" | "PATCH" | "DELETE",
    path: string,
    schema: z.ZodType<T>,
    body?: unknown,
  ): Promise<T> {
    const attempts = method === "GET" ? this.getRetries + 1 : 1;
    let lastError: MirraApiError | null = null;

    for (let attempt = 0; attempt < attempts; attempt++) {
      try {
        const res = await fetch(`${this.baseUrl}${path}`, {
          method,
          credentials: "include",
          headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
          body: body !== undefined ? JSON.stringify(body) : undefined,
          cache: "no-store",
        });

        if (!res.ok) {
          let code: MirraErrorCode = STATUS_TO_CODE[res.status] ?? "unknown";
          let message = `Request failed (${res.status})`;
          try {
            const parsed = apiErrorBodySchema.safeParse(await res.json());
            if (parsed.success) {
              code = parsed.data.error.code as MirraErrorCode;
              message = parsed.data.error.message;
            }
          } catch {
            // non-JSON error body — keep defaults
          }
          const err = new MirraApiError(code, message, res.status);
          if (!err.retryable || attempt === attempts - 1) throw err;
          lastError = err;
          await backoff(attempt);
          continue;
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
      } catch (err) {
        const mirraErr = toMirraError(err);
        if (!mirraErr.retryable || attempt === attempts - 1) throw mirraErr;
        lastError = mirraErr;
        await backoff(attempt);
      }
    }
    throw lastError ?? new MirraApiError("unknown", "Request failed");
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
  delete<T>(path: string, schema: z.ZodType<T>) {
    return this.request("DELETE", path, schema);
  }
}

function backoff(attempt: number): Promise<void> {
  return new Promise((r) => setTimeout(r, 250 * 2 ** attempt));
}
