/** Typed error taxonomy for the Mirra runtime API boundary. */

export type MirraErrorCode =
  | "product_not_found"
  | "product_unpublished"
  | "variant_not_found"
  | "try_on_disabled"
  | "unauthenticated"
  | "email_unverified"
  | "invalid_credentials"
  | "account_exists"
  | "capture_session_expired"
  | "capture_token_used"
  | "capture_session_not_found"
  | "avatar_job_failed"
  | "render_not_found"
  | "render_expired"
  | "validation_failed"
  | "rate_limited"
  | "network_error"
  | "api_degraded"
  | "unknown";

export class MirraApiError extends Error {
  readonly code: MirraErrorCode;
  readonly status: number;
  readonly retryable: boolean;

  constructor(code: MirraErrorCode, message: string, status = 500) {
    super(message);
    this.name = "MirraApiError";
    this.code = code;
    this.status = status;
    this.retryable = status >= 500 || code === "network_error" || code === "api_degraded";
  }
}

export function toMirraError(err: unknown): MirraApiError {
  if (err instanceof MirraApiError) return err;
  if (err instanceof TypeError) {
    // fetch network failure
    return new MirraApiError("network_error", "The connection was interrupted.", 0);
  }
  return new MirraApiError("unknown", err instanceof Error ? err.message : "Unexpected error");
}

/** Safe, user-facing message per error code. Never leaks internals. */
export function userMessage(code: MirraErrorCode): string {
  switch (code) {
    case "product_not_found":
    case "product_unpublished":
      return "This item is no longer available to try on.";
    case "variant_not_found":
      return "That option is no longer available.";
    case "try_on_disabled":
      return "Try-on isn't available for this item right now.";
    case "invalid_credentials":
      return "That email and password combination doesn't match our records.";
    case "account_exists":
      return "An account with this email already exists. Try logging in instead.";
    case "capture_session_expired":
      return "This pairing code has expired. Generate a fresh one to continue.";
    case "capture_token_used":
      return "This pairing link was already used. Generate a fresh one to continue.";
    case "network_error":
      return "You appear to be offline. Check your connection and retry.";
    case "rate_limited":
      return "Too many attempts. Please wait a moment and retry.";
    default:
      return "Something didn't go as planned. Please retry.";
  }
}
