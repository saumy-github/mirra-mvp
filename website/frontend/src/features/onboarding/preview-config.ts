import { onboardingStudioDestination } from "@/lib/post-auth";

/** Temporary UI walkthrough. It never bypasses API auth or creates profile data. */
export const onboardingPreviewEnabled =
  import.meta.env.DEV || import.meta.env.VITE_ENABLE_ONBOARDING_PREVIEW === "true";

export function previewSetupUrl(next?: string | null) {
  const params = new URLSearchParams({ preview: "1" });
  const destination = onboardingStudioDestination(next);
  if (destination !== "/studio") params.set("next", destination);
  return `/onboarding/qr?${params}`;
}

export function previewStudioUrl(next?: string | null) {
  const url = new URL(onboardingStudioDestination(next), "https://mirra.local");
  url.searchParams.set("setupPreview", "1");
  return `${url.pathname}${url.search}${url.hash}`;
}
