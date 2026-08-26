/**
 * Where to send a user after authentication. Only same-origin relative
 * paths are honoured (no open redirects). Simplified from user-side's
 * version, which branched on merchant launch context — standalone always
 * has the same destination shape.
 */
const AUTH_DESTINATIONS = new Set([
  "/measurements",
  "/onboarding/avatar",
  "/onboarding/measurements",
  "/profile",
  "/profile/avatar",
  "/profile/measurements",
  "/profile/privacy",
  "/profile/signature-looks",
  "/studio",
]);

export function postAuthDestination(nextParam?: string | null): string {
  if (!nextParam || !/^\/(?!\/)/.test(nextParam)) return "/profile";

  const destination = new URL(nextParam, "https://mirra.local");
  if (AUTH_DESTINATIONS.has(destination.pathname)) {
    return `${destination.pathname}${destination.search}${destination.hash}`;
  }

  return "/profile";
}
