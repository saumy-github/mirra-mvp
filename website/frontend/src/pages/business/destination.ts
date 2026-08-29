/**
 * Where a business account lands after authentication. Mirrors
 * `lib/post-auth.ts` (same open-redirect guard: same-origin relative paths
 * only) but with the merchant surface as the allow-list and default, so a
 * brand is never dropped into the shopper studio.
 */
const BUSINESS_DESTINATIONS = new Set([
  "/dashboard/portal",
  "/dashboard/onboarding",
  "/join",
]);

const DEFAULT_BUSINESS_DESTINATION = "/dashboard/portal";

export function businessDestination(nextParam?: string | null): string {
  if (!nextParam || !/^\/(?!\/)/.test(nextParam)) return DEFAULT_BUSINESS_DESTINATION;

  const destination = new URL(nextParam, "https://mirra.local");
  // Anything under the merchant portal is fair game; everything else falls
  // back rather than bouncing a brand into a shopper-only page.
  if (
    BUSINESS_DESTINATIONS.has(destination.pathname) ||
    destination.pathname.startsWith("/dashboard/portal/")
  ) {
    return `${destination.pathname}${destination.search}${destination.hash}`;
  }

  return DEFAULT_BUSINESS_DESTINATION;
}
