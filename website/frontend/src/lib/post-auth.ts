/**
 * Where to send a user after authentication. Only same-origin relative
 * paths are honoured (no open redirects). Simplified from user-side's
 * version, which branched on merchant launch context — standalone always
 * has the same destination shape.
 */
export function postAuthDestination(nextParam?: string | null): string {
  if (nextParam && /^\/(?!\/)/.test(nextParam)) return nextParam;
  return "/profile";
}

/** Temporary review shortcut — jumps straight to the studio. */
export function demoAccessDestination(nextParam?: string | null): string {
  if (nextParam && /^\/(?!\/)/.test(nextParam)) return nextParam;
  return "/studio";
}
