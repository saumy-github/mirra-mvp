import { SetupFlow } from "@/features/onboarding/setup-flow";
import { SetupPreview } from "@/features/onboarding/setup-preview";
import { onboardingPreviewEnabled } from "@/features/onboarding/preview-config";
import { useSearchParams } from "react-router-dom";

/** Standalone signup / try-on onboarding. Never mounts the Profile shell. */
export default function QrPairing() {
  const [params] = useSearchParams();
  return onboardingPreviewEnabled && params.get("preview") === "1" ? (
    <SetupPreview />
  ) : (
    <SetupFlow />
  );
}
