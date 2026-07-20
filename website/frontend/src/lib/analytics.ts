import { getRuntimeProvider } from "@/integrations/mirra-api";

const analyticsFlag = import.meta.env.VITE_ANALYTICS_ENABLED;
const ANALYTICS_ENABLED =
  analyticsFlag === undefined ? true : analyticsFlag === "true" || analyticsFlag === "1";

/**
 * Analytics funnel. Given this pilot's whole point is measuring real user
 * behavior and load, this matters more than it would in a normal MVP.
 * Payloads carry safe context only: never photographs, tokens, passwords or
 * precise body measurements.
 */

export type AnalyticsEventName =
  | "page_view"
  | "signup_started"
  | "signup_completed"
  | "login_completed"
  | "guest_started"
  | "saved_avatar_selected"
  | "qr_session_created"
  | "qr_scanned"
  | "capture_consent_given"
  | "capture_started"
  | "capture_completed"
  | "avatar_generation_started"
  | "avatar_generation_completed"
  | "avatar_generation_failed"
  | "measurements_reviewed"
  | "measurements_updated"
  | "studio_opened"
  | "product_selected"
  | "variant_selected"
  | "size_selected"
  | "try_on_started"
  | "try_on_completed"
  | "try_on_failed"
  | "hanger_item_restored"
  | "signature_look_created"
  | "signature_look_applied"
  | "signature_look_removed"
  | "add_to_cart_clicked"
  | "session_abandoned";

export interface TrackContext {
  productPublicId?: string | null;
  variantPublicId?: string | null;
  sessionId?: string | null;
  authenticated?: boolean;
  engineVersion?: string | null;
  properties?: Record<string, string | number | boolean | null>;
}

const FORBIDDEN_PROPERTY_KEYS = /photo|password|token|secret|credential|measurement/i;

export function sanitizeProperties(
  props: Record<string, string | number | boolean | null> | undefined,
): Record<string, string | number | boolean | null> | undefined {
  if (!props) return undefined;
  const safe: Record<string, string | number | boolean | null> = {};
  for (const [k, v] of Object.entries(props)) {
    if (FORBIDDEN_PROPERTY_KEYS.test(k)) continue;
    safe[k] = v;
  }
  return safe;
}

export function track(event: AnalyticsEventName, ctx: TrackContext = {}): void {
  if (!ANALYTICS_ENABLED) return;
  const provider = getRuntimeProvider();
  void provider.trackEvent({
    event,
    productPublicId: ctx.productPublicId ?? null,
    variantPublicId: ctx.variantPublicId ?? null,
    sessionId: ctx.sessionId ?? null,
    authenticated: ctx.authenticated ?? false,
    engineVersion: ctx.engineVersion ?? null,
    appVersion: import.meta.env.VITE_APP_VERSION ?? "0.1.0",
    environment: import.meta.env.VITE_APP_ENV ?? "development",
    occurredAt: new Date().toISOString(),
    properties: sanitizeProperties(ctx.properties),
  });
}
