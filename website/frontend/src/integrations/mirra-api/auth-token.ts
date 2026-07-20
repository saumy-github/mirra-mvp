/**
 * In-memory access-token store + single-flight refresh.
 *
 * The access JWT lives ONLY in this module-level variable — never
 * localStorage, never a readable cookie (XSS can't exfiltrate what isn't
 * persisted). The 30-day refresh token rides an httpOnly cookie scoped to
 * /api/v1/auth and is invisible to JS entirely. On page load the app calls
 * refreshAccessToken() to restore the session from that cookie.
 * See website/backend-implementation-plan.md, Phase 0 item 1.
 */

let accessToken: string | null = null;
let inflight: Promise<string | null> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function clearAccessToken(): void {
  accessToken = null;
}

/**
 * Mint a fresh access token from the refresh cookie. Concurrent callers
 * share one network request. Returns null when there is no live session.
 */
export function refreshAccessToken(baseUrl: string): Promise<string | null> {
  if (!inflight) {
    inflight = (async () => {
      try {
        const res = await fetch(`${baseUrl.replace(/\/$/, "")}/auth/refresh`, {
          method: "POST",
          credentials: "include",
          cache: "no-store",
        });
        if (!res.ok) {
          accessToken = null;
          return null;
        }
        const json: unknown = await res.json();
        const token =
          typeof json === "object" && json !== null && "accessToken" in json
            ? (json as { accessToken: unknown }).accessToken
            : null;
        accessToken = typeof token === "string" ? token : null;
        return accessToken;
      } catch {
        accessToken = null;
        return null;
      } finally {
        inflight = null;
      }
    })();
  }
  return inflight;
}
