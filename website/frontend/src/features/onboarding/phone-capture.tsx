import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, Check, LoaderCircle } from "lucide-react";
import type { FacePhotosInput, PhotoCaptureInput } from "@/integrations/mirra-api/types";
import { cmToInches, inchesToCm, lbToKg } from "@/lib/units";
import { LiveCamera } from "./live-camera";
import { usePhotoPreview } from "./use-photo-preview";

function useCaptureHeading(step: string) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus({ preventScroll: true });
  }, [step]);
  return heading;
}

function CapturedPhoto({
  file,
  label,
  onRetake,
  disabled = false,
}: {
  file: File;
  label: string;
  onRetake: () => void;
  disabled?: boolean;
}) {
  const src = usePhotoPreview(file);
  return (
    <figure className="phone-captured">
      {src && <img src={src} alt={`Your ${label.toLowerCase()} photo`} />}
      <figcaption>
        <span>
          <Check size={13} />
          {label}
        </span>
        <button type="button" onClick={onRetake} disabled={disabled}>
          Retake
        </button>
      </figcaption>
    </figure>
  );
}

export function BodyCameraWizard<T>({
  initial,
  submit,
  onStarted,
}: {
  initial: { gender?: "male" | "female"; heightCm?: number | null; weightKg?: number | null };
  submit: (input: PhotoCaptureInput) => Promise<T>;
  onStarted: (result: T) => void;
}) {
  const [step, setStep] = useState<"details" | "front" | "side" | "review">("details");
  const heading = useCaptureHeading(step);
  const [gender, setGender] = useState<"male" | "female">(initial.gender ?? "male");
  const [imperial, setImperial] = useState(false);
  const [height, setHeight] = useState(initial.heightCm ? String(initial.heightCm) : "");
  const [weight, setWeight] = useState(initial.weightKg ? String(initial.weightKg) : "");
  const [shoes, setShoes] = useState(false);
  const [front, setFront] = useState<File | null>(null);
  const [side, setSide] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const start = useMutation({
    mutationFn: () =>
      submit({
        front: front!,
        side: side!,
        gender,
        heightCm: imperial ? inchesToCm(Number(height)) : Number(height),
        weightKg: !weight.trim() ? null : imperial ? lbToKg(Number(weight)) : Number(weight),
        shoeSoleCm: shoes ? 3 : 0,
      }),
    onSuccess: onStarted,
  });
  function units(next: boolean) {
    if (next === imperial) return;
    if (height.trim())
      setHeight(String(next ? cmToInches(Number(height)) : inchesToCm(Number(height))));
    if (weight.trim())
      setWeight(
        String(next ? Math.round(Number(weight) * 2.2046226 * 10) / 10 : lbToKg(Number(weight))),
      );
    setImperial(next);
  }
  function next(e: React.FormEvent) {
    e.preventDefault();
    const h = imperial ? inchesToCm(Number(height)) : Number(height);
    const w = imperial ? lbToKg(Number(weight)) : Number(weight);
    if (!Number.isFinite(h) || h < 120 || h > 230) {
      setError(
        imperial
          ? "Enter a height between 47.2 and 90.6 inches."
          : "Enter a height between 120 and 230 cm.",
      );
      return;
    }
    if (weight.trim() && (!Number.isFinite(w) || w < 30 || w > 250)) {
      setError(
        imperial
          ? "Enter a weight between 66 and 551 lb, or leave it empty."
          : "Enter a weight between 30 and 250 kg, or leave it empty.",
      );
      return;
    }
    setError(null);
    setStep(front && side ? "review" : "front");
  }
  return (
    <div className="phone-flow setup-enter" key={step}>
      <div className="phone-step-label">
        <span>Body photos</span>
        <span>
          {step === "details"
            ? "Before we start"
            : step === "review"
              ? "Ready to sync"
              : step === "front"
                ? "1 of 2"
                : "2 of 2"}
        </span>
      </div>
      {step === "details" ? (
        <>
          <h1 ref={heading} tabIndex={-1}>
            A little about your fit.
          </h1>
          <p className="phone-intro">
            Your height gives your photos the right scale. Then we’ll guide you through two quick
            shots.
          </p>
          <div className="phone-welcome-photos" aria-hidden="true">
            <img src="/profile/capture-front.webp" alt="" />
            <img src="/profile/capture-side.webp" alt="" />
            <p>
              A plain background.
              <br />
              Soft light.
              <br />
              Head to toe in view.
            </p>
          </div>
          <form className="phone-details" onSubmit={next}>
            <fieldset>
              <legend>Body model</legend>
              <div className="phone-segments">
                {(["female", "male"] as const).map((g) => (
                  <button
                    key={g}
                    type="button"
                    aria-pressed={gender === g}
                    onClick={() => setGender(g)}
                  >
                    {g === "female" ? "Female" : "Male"}
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend>Measurement units</legend>
              <div className="phone-segments">
                {[false, true].map((v) => (
                  <button
                    key={String(v)}
                    type="button"
                    aria-pressed={imperial === v}
                    onClick={() => units(v)}
                  >
                    {v ? "Imperial" : "Metric"}
                  </button>
                ))}
              </div>
            </fieldset>
            <label>
              Height <span>{imperial ? "in" : "cm"}</span>
              <input
                autoComplete="off"
                type="number"
                inputMode="decimal"
                step="any"
                required
                value={height}
                onChange={(e) => setHeight(e.target.value)}
                placeholder={imperial ? "e.g. 69" : "e.g. 175"}
              />
            </label>
            <label>
              Weight <span>optional · {imperial ? "lb" : "kg"}</span>
              <input
                autoComplete="off"
                type="number"
                inputMode="decimal"
                step="any"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                placeholder={imperial ? "e.g. 154" : "e.g. 70"}
              />
            </label>
            <label className="phone-checkbox">
              <input type="checkbox" checked={shoes} onChange={(e) => setShoes(e.target.checked)} />
              <span>I’ll be wearing shoes</span>
            </label>
            {error && (
              <p className="camera-error" role="alert">
                {error}
              </p>
            )}
            <button className="setup-primary" type="submit">
              Continue to camera <ArrowRight size={17} />
            </button>
          </form>
        </>
      ) : step === "front" || step === "side" ? (
        <>
          <h1 ref={heading} tabIndex={-1}>
            {step === "front" ? "First, face the camera." : "Now, turn to the side."}
          </h1>
          <p className="phone-intro">
            {step === "front"
              ? "Stand naturally with your arms a little apart."
              : "Turn 90°. Keep your arms relaxed and your whole body in view."}
          </p>
          <LiveCamera
            key={step}
            label={step === "front" ? "Front" : "Side"}
            guide={`/profile/capture-${step}.webp`}
            hint="Keep your head and feet in view. Ask someone to hold the camera at chest height."
            onConfirm={(photo) => {
              if (step === "front") {
                setFront(photo);
                setStep(side ? "review" : "side");
              } else {
                setSide(photo);
                setStep("review");
              }
            }}
            onCancel={() => setStep(step === "front" ? "details" : "front")}
          />
        </>
      ) : (
        <>
          <h1 ref={heading} tabIndex={-1}>
            Looking like you.
          </h1>
          <p className="phone-intro">
            Make sure both photos are clear, with your head and feet visible.
          </p>
          <div className="phone-photo-review">
            {front && (
              <CapturedPhoto
                file={front}
                label="Front"
                disabled={start.isPending}
                onRetake={() => setStep("front")}
              />
            )}
            {side && (
              <CapturedPhoto
                file={side}
                label="Side"
                disabled={start.isPending}
                onRetake={() => setStep("side")}
              />
            )}
          </div>
          <p className="phone-detail-summary">
            {height} {imperial ? "in" : "cm"}
            {weight && ` · ${weight} ${imperial ? "lb" : "kg"}`}
            <button type="button" disabled={start.isPending} onClick={() => setStep("details")}>
              Edit details
            </button>
          </p>
          {start.error && (
            <p className="camera-error" role="alert">
              {start.error.message}
            </p>
          )}
          <button
            className="setup-primary phone-full"
            disabled={start.isPending}
            onClick={() => start.mutate()}
          >
            {start.isPending ? (
              <>
                <LoaderCircle className="setup-spinner" size={17} /> Syncing your photos…
              </>
            ) : (
              <>
                Sync photos & continue <ArrowRight size={17} />
              </>
            )}
          </button>
        </>
      )}
    </div>
  );
}

export function FaceCameraWizard<T>({
  submit,
  onStarted,
  onSkip,
  skipPending = false,
}: {
  submit: (input: FacePhotosInput) => Promise<T>;
  onStarted: (result: T) => void;
  onSkip: () => void;
  skipPending?: boolean;
}) {
  const [step, setStep] = useState<"front" | "left" | "right" | "review">("front");
  const heading = useCaptureHeading(step);
  const [front, setFront] = useState<File | null>(null);
  const [left, setLeft] = useState<File | null>(null);
  const [right, setRight] = useState<File | null>(null);
  const upload = useMutation({
    mutationFn: () => submit({ front: front!, left, right }),
    onSuccess: onStarted,
  });
  const hint =
    step === "left"
      ? "Turn your head about 45° to your left."
      : step === "right"
        ? "Turn your head about 45° to your right."
        : "Look straight ahead. Face the light and keep your expression relaxed.";
  return (
    <div className="phone-flow setup-enter" key={step}>
      <div className="phone-step-label">
        <span>Your face</span>
        <span>Optional</span>
      </div>
      <h1 ref={heading} tabIndex={-1}>
        {step === "review"
          ? "The finishing touch."
          : step === "front"
            ? "Make it look like you."
            : `A little to the ${step}.`}
      </h1>
      <p className="phone-intro">
        {step === "review"
          ? "Your avatar can now include your face. Extra angles are optional."
          : "One clear photo is enough. Remove glasses and keep hair away from your face."}
      </p>
      {step === "review" ? (
        <>
          <div className="phone-photo-review" data-single={!left && !right}>
            {front && (
              <CapturedPhoto
                file={front}
                label="Face"
                disabled={upload.isPending || skipPending}
                onRetake={() => setStep("front")}
              />
            )}
            {left && (
              <CapturedPhoto
                file={left}
                label="Left"
                disabled={upload.isPending || skipPending}
                onRetake={() => setStep("left")}
              />
            )}
            {right && (
              <CapturedPhoto
                file={right}
                label="Right"
                disabled={upload.isPending || skipPending}
                onRetake={() => setStep("right")}
              />
            )}
          </div>
          {!left && (
            <button
              className="setup-text-button"
              disabled={upload.isPending || skipPending}
              onClick={() => setStep("left")}
            >
              Add side views
            </button>
          )}
          {upload.error && (
            <p className="camera-error" role="alert">
              {upload.error.message}
            </p>
          )}
          <button
            className="setup-primary phone-full"
            disabled={upload.isPending || skipPending}
            onClick={() => upload.mutate()}
          >
            {upload.isPending ? (
              <>
                <LoaderCircle size={17} className="setup-spinner" /> Syncing your face photo…
              </>
            ) : (
              <>
                Finish & sync <ArrowRight size={17} />
              </>
            )}
          </button>
        </>
      ) : (
        <LiveCamera
          key={step}
          label={`Face ${step}`}
          facing="user"
          guide="/profile/capture-face.webp"
          hint={hint}
          onConfirm={(photo) => {
            if (step === "front") {
              setFront(photo);
              setStep("review");
            } else if (step === "left") {
              setLeft(photo);
              setStep(right ? "review" : "right");
            } else {
              setRight(photo);
              setStep("review");
            }
          }}
          onCancel={step !== "front" || front ? () => setStep("review") : undefined}
        />
      )}
      <button
        className="setup-text-button phone-skip"
        disabled={upload.isPending || skipPending}
        onClick={onSkip}
      >
        {skipPending ? "Finishing…" : "Continue without a face photo"}
        <ArrowRight size={14} />
      </button>
      {step !== "front" && step !== "review" && (
        <button className="setup-text-button" onClick={() => setStep("review")}>
          <ArrowLeft size={13} /> Back to your photos
        </button>
      )}
    </div>
  );
}
