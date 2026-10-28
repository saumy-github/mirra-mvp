// Isolated visual QA fixture. Not an application route or a production build entry.
import { useState } from "react";
import { BuildingState, MeasurementReview, SetupTour } from "../src/features/onboarding/setup-flow";
import type { AvatarSetup } from "../src/integrations/mirra-api/types";
import "../src/styles/globals.css";

const setup: AvatarSetup = {
  pairing: {
    pairingId: "qa-only",
    expiresAt: "2099-01-01",
    active: true,
    captureId: "qa-only",
    buildAvatar: true,
    measurementMethod: "photos",
    phoneStage: "complete",
    captureComplete: true,
    faceSkipped: false,
  },
  capture: {
    captureId: "qa-only",
    state: "applied",
    stageLabel: "Measured",
    heightCm: 175,
    weightKg: 72,
    gender: "female",
    profile: null,
    bodyShapeType: null,
    skinToneHex: null,
    warnings: [],
    failureReason: null,
    createdAt: "",
    completedAt: null,
  },
  face: {
    faceId: "qa-only",
    state: "ready",
    stageLabel: "Ready",
    hasModel: true,
    views: ["front"],
    skinToneHex: null,
    warnings: [],
    failureReason: null,
    createdAt: "",
    completedAt: null,
  },
  job: {
    jobId: "qa-only",
    state: "generating",
    stageLabel: "Creating your 3D avatar",
    startedAt: "",
    failureReason: null,
    avatarProfileId: null,
  },
  state: "building",
  measurements: {
    height_cm: 175,
    weight_kg: 72,
    shoulder_width_cm: 42,
    chest_circumference_cm: 96,
    bust_circumference_cm: 94,
    under_bust_circumference_cm: 79,
    waist_circumference_cm: 78,
    hip_circumference_cm: 98,
    leg_length_cm: 81,
  },
  failureReason: null,
};
export function Preview() {
  const [stage, setStage] = useState(location.hash.slice(1) || "tour");
  const [result, setResult] = useState("");
  return (
    <div className="mirra-setup">
      <header className="setup-topbar">
        <span style={{ fontSize: 11 }}>VISUAL QA · FIXTURE DATA</span>
        <nav style={{ display: "flex", gap: 20 }}>
          {["tour", "building", "review"].map((s) => (
            <button className="setup-text-button" key={s} onClick={() => setStage(s)}>
              {s}
            </button>
          ))}
        </nav>
      </header>
      <main className="setup-main">
        {stage === "tour" ? (
          <SetupTour ready={false} onDone={() => setStage("building")} />
        ) : stage === "building" ? (
          <BuildingState setup={setup} />
        ) : (
          <MeasurementReview
            setup={{ ...setup, state: "review" }}
            pending={false}
            error={null}
            preview={
              <img
                src="/profile/capture-front.webp"
                alt="QA illustration, not a generated avatar"
                style={{ width: "100%", height: "100%", objectFit: "contain" }}
              />
            }
            onConfirm={(v) => setResult(JSON.stringify(v))}
          />
        )}
        {result && <output aria-label="Submitted corrections">{result}</output>}
      </main>
    </div>
  );
}
