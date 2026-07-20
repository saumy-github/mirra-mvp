import { Spinner } from "@/components/ui/misc";

/**
 * Suspense fallback for lazy-loaded routes — shown while a route's JS
 * chunk (and, for the studio, its data) is still loading. Deliberately not
 * a blank screen, per the CSR loading strategy in frontend-structure-plan.md.
 * A single shared fallback for now; swap for per-route skeletons if any
 * route's load time turns out to warrant it.
 */
export function PageFallback() {
  return (
    <div className="grid min-h-dvh place-items-center bg-canvas">
      <Spinner className="size-6 text-muted" />
    </div>
  );
}
