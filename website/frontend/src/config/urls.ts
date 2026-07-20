/**
 * Route/URL builders. Ported down from user-side's tenancy-aware version
 * (path vs. subdomain tenancy, merchant launch URLs) — standalone has no
 * tenants, so this is now just the one URL that genuinely needs building:
 * the mobile capture link embedded in the QR code.
 */

/** Mobile capture URL embedded in the QR code. */
export function captureUrl(oneTimeToken: string): string {
  const origin = import.meta.env.VITE_RUNTIME_ORIGIN ?? "http://localhost:3000";
  return `${origin}/capture/${oneTimeToken}`;
}
