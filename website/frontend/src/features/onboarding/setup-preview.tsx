import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { MirraMark } from "@/components/ui/logo";
import type { AvatarSetup } from "@/integrations/mirra-api";
import { BuildingState, MeasurementReview, SetupTour } from "./setup-flow";
import { previewStudioUrl } from "./preview-config";

// Illustration-only data, isolated from all account queries and persistence.
const example: AvatarSetup = {
  pairing: {
    pairingId: "preview-only",
    expiresAt: "",
    active: false,
    captureId: null,
    buildAvatar: false,
    measurementMethod: "photos",
    phoneStage: "complete",
    captureComplete: true,
    faceSkipped: true,
  },
  capture: null,
  face: null,
  job: null,
  state: "review",
  failureReason: null,
  measurements: {
    height_cm: 175,
    weight_kg: 70,
    shoulder_width_cm: 42,
    chest_circumference_cm: 96,
    waist_circumference_cm: 80,
    hip_circumference_cm: 96,
    leg_length_cm: 81,
  },
};

/** No uploads, jobs, profile writes, or fake authentication. Safe to use with workers off. */
export function SetupPreview() {
  const [stage, setStage] = useState<"thanks" | "tour" | "building" | "review">("thanks");
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const destination = previewStudioUrl(params.get("next"));
  useEffect(() => {
    if (stage !== "thanks" && stage !== "building") return;
    const id = setTimeout(
      () => setStage(stage === "thanks" ? "tour" : "review"),
      stage === "thanks" ? 1800 : 6500,
    );
    return () => clearTimeout(id);
  }, [stage]);
  return (
    <div className="mirra-setup">
      <header className="setup-topbar">
        <Link to={destination} className="setup-brand" aria-label="Mirra Studio">
          <MirraMark size={28} />
          <span>MIRRA</span>
        </Link>
        <span className="setup-preview-badge">Preview · example data</span>
        <Link to="/onboarding/qr" className="setup-exit-link">
          Exit preview
        </Link>
      </header>
      <main className="setup-main">
        {stage === "thanks" ? (
          <section className="setup-centered setup-enter" role="status">
            <span className="phone-success">
              <CheckCircle2 size={56} strokeWidth={1.2} />
            </span>
            <h1>All here. Thank you.</h1>
            <p>This is the confirmation you’ll see once your photos are synced.</p>
          </section>
        ) : stage === "tour" ? (
          <SetupTour ready={false} preview onDone={() => setStage("building")} />
        ) : stage === "building" ? (
          <BuildingState setup={example} preview />
        ) : (
          <MeasurementReview
            setup={example}
            pending={false}
            error={null}
            preview={
              <img
                src="/profile/capture-front.webp"
                alt="Example figure for the preview; this is not your avatar"
              />
            }
            onConfirm={() => navigate(destination, { replace: true })}
          />
        )}
      </main>
      <footer className="setup-preview-footer">
        <span>Temporary walkthrough. Photos, measurements and account data are not saved.</span>
        <Link to="/onboarding/qr" className="setup-text-button">
          Back to real setup
        </Link>
      </footer>
    </div>
  );
}
