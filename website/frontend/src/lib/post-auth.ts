/**
 * Where to send a user after authentication. Only same-origin relative
 * paths are honoured (no open redirects). Simplified from user-side's
 * version, which branched on merchant launch context — standalone always
 * has the same destination shape.
 */
const AUTH_DESTINATIONS = new Set([
  "/profile",
  "/profile/avatar",
  "/profile/measurements",
  "/profile/privacy",
  "/profile/signature-looks",
  "/studio",
  "/onboarding/qr",
]);

export function postAuthDestination(nextParam?: string | null): string {
  if (!nextParam || !/^\/(?!\/)/.test(nextParam)) return "/studio";

  const destination = new URL(nextParam, "https://mirra.local");
  if (AUTH_DESTINATIONS.has(destination.pathname)) {
    return `${destination.pathname}${destination.search}${destination.hash}`;
  }

  return "/studio";
}

/** Signup always completes its own setup, never a Profile detour. */
export function signupDestination(nextParam?: string | null): string {
  const next = postAuthDestination(nextParam);
  const studio = next.startsWith("/studio?") || next === "/studio" ? next : "/studio";
  return studio === "/studio"
    ? "/onboarding/qr"
    : `/onboarding/qr?next=${encodeURIComponent(studio)}`;
}

export function onboardingStudioDestination(nextParam?: string | null): string {
  const next = postAuthDestination(nextParam);
  return next === "/studio" || next.startsWith("/studio?") ? next : "/studio";
}
