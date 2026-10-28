import { useEffect, useRef, useState } from "react";
import { Camera, X } from "lucide-react";
import { LiveCamera } from "@/features/onboarding/live-camera";
import { usePhotoPreview } from "@/features/onboarding/use-photo-preview";
import { MeasurementSliders } from "@/features/onboarding/measurement-sliders";
import { useMeasurementReview } from "@/features/onboarding/use-measurement-review";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type {
  AvatarProfile,
  PhotoCaptureInput,
  PhotoMeasurement,
  PhotoMeasurementField,
} from "@/integrations/mirra-api/types";
import { track } from "@/lib/analytics";
import { cmToInches, inchesToCm, lbToKg, type UnitSystem } from "@/lib/units";

const SHOE_SOLE_CM = 3; // typical sneaker sole; the pipeline subtracts it from the silhouette

const POLL_MS = 1500;

/**
 * Measure from photos: a front and a side photo plus height become the same
 * saved measurements the manual form writes (backend: /photo-measurements,
 * worker queue `measure`). The shopper always reviews — and can correct —
 * the numbers before they are saved; nothing reaches their profile unseen.
 * Photos are deleted on the server as soon as they have been measured.
 */
export function PhotoMeasurementFlow({
  onSaved,
  defaultGender = "female",
}: {
  onSaved?: (profile: AvatarProfile) => void;
  defaultGender?: "male" | "female";
}) {
  const qc = useQueryClient();
  const api = getRuntimeProvider();
  const [captureId, setCaptureId] = useState<string | null>(null);
  const [resumeChecked, setResumeChecked] = useState(false);

  // A reload mid-measurement picks the capture back up instead of losing it.
  useEffect(() => {
    let cancelled = false;
    api
      .getLatestPhotoMeasurement()
      .then((latest) => {
        if (cancelled || !latest) return;
        if (["queued", "processing", "ready"].includes(latest.state))
          setCaptureId(latest.captureId);
      })
      .catch(() => undefined)
      .finally(() => !cancelled && setResumeChecked(true));
    return () => {
      cancelled = true;
    };
  }, [api]);

  const capture = useQuery({
    queryKey: ["photo-measurement", captureId],
    queryFn: () => getRuntimeProvider().getPhotoMeasurement(captureId!),
    enabled: !!captureId,
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      return state === "queued" || state === "processing" ? POLL_MS : false;
    },
  });

  if (!resumeChecked) return <p className="text-sm text-muted">Loading…</p>;

  const current = capture.data;
  const restart = () => {
    setCaptureId(null);
    qc.removeQueries({ queryKey: ["photo-measurement"] });
  };

  if (!captureId) {
    return (
      <CaptureStep defaultGender={defaultGender} onStarted={(c) => setCaptureId(c.captureId)} />
    );
  }
  if (capture.isError) {
    return (
      <Problem
        message="We lost track of this measurement."
        onRetry={restart}
        retryLabel="Start again"
      />
    );
  }
  if (!current || current.state === "queued" || current.state === "processing") {
    return <Measuring label={current?.stageLabel ?? "Uploading your photos"} />;
  }
  if (current.state === "failed") {
    return (
      <Problem
        message={current.failureReason ?? "We couldn't measure these photos."}
        onRetry={restart}
        retryLabel="Retake photos"
      />
    );
  }
  return (
    <ReviewStep
      key={current.captureId}
      capture={current}
      onRetake={restart}
      onSaved={(profile) => {
        qc.setQueryData(["account", "avatar-profile"], profile);
        track("measurements_updated", { authenticated: true });
        onSaved?.(profile);
      }}
    />
  );
}

// ── Step 1: photos + height ───────────────────────────────────────────

function CaptureStep({
  defaultGender,
  onStarted,
}: {
  defaultGender: "male" | "female";
  onStarted: (capture: PhotoMeasurement) => void;
}) {
  return (
    <PhotoCaptureForm
      defaultGender={defaultGender}
      submit={(input) => getRuntimeProvider().startPhotoMeasurement(input)}
      onStarted={onStarted}
    />
  );
}

/**
 * The photos + height form. Shared by the signed-in flow above and the phone
 * page reached through the desktop's QR code (/capture/:token), which submits
 * through the pairing link instead.
 */
export function PhotoCaptureForm<T>({
  defaultGender,
  initial,
  submit: send,
  onStarted,
  submitLabel = "Measure me",
  compact = false,
}: {
  defaultGender: "male" | "female";
  initial?: { heightCm?: number | null; weightKg?: number | null };
  submit: (input: PhotoCaptureInput) => Promise<T>;
  onStarted: (result: T) => void;
  submitLabel?: string;
  compact?: boolean;
}) {
  const [gender, setGender] = useState<"male" | "female">(defaultGender);
  const [units, setUnits] = useState<UnitSystem>("metric");
  const [height, setHeight] = useState(initial?.heightCm ? String(initial.heightCm) : "");
  const [weight, setWeight] = useState(initial?.weightKg ? String(initial.weightKg) : "");
  const [shoes, setShoes] = useState(false);
  const [front, setFront] = useState<File | null>(null);
  const [side, setSide] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const start = useMutation({
    mutationFn: () => {
      const h = Number(height);
      const w = weight.trim() === "" ? null : Number(weight);
      return send({
        front: front!,
        side: side!,
        gender,
        heightCm: units === "metric" ? h : inchesToCm(h),
        weightKg: w === null ? null : units === "metric" ? w : lbToKg(w),
        shoeSoleCm: shoes ? SHOE_SOLE_CM : 0,
      });
    },
    onSuccess: onStarted,
  });

  function switchUnits(next: UnitSystem) {
    if (next === units) return;
    const convert = (
      value: string,
      toImperial: (n: number) => number,
      toMetric: (n: number) => number,
    ) => {
      const n = Number(value);
      if (value.trim() === "" || !Number.isFinite(n)) return value;
      return String(next === "imperial" ? toImperial(n) : toMetric(n));
    };
    setHeight((h) => convert(h, cmToInches, inchesToCm));
    setWeight((w) => convert(w, (kg) => Math.round(kg * 2.20462 * 10) / 10, lbToKg));
    setUnits(next);
  }

  function submit() {
    const h = Number(height);
    const cm = units === "metric" ? h : inchesToCm(h);
    if (!front || !side) return setLocalError("Add both a front and a side photo.");
    if (!Number.isFinite(h) || cm < 120 || cm > 230) {
      return setLocalError(
        units === "metric"
          ? "Enter your height in cm (120–230)."
          : "Enter your height in inches (48–90).",
      );
    }
    setLocalError(null);
    start.mutate();
  }

  return (
    <div>
      <ul
        hidden={compact}
        className="space-y-1.5 rounded-2xl border border-line bg-paper/70 px-5 py-4 text-[13px] text-ink-soft"
      >
        <li>• Fitted clothing, hair tied back, plain background if you can.</li>
        <li>• Phone upright at chest height, 2–3 m away, whole body in frame head to feet.</li>
        <li>
          • <strong>Front:</strong> face the camera, arms 20–40° away from your body.
        </li>
        <li>
          • <strong>Side:</strong> turn 90°, arms relaxed, a true profile.
        </li>
        <li>• Photos are deleted as soon as they've been measured — only the numbers are kept.</li>
      </ul>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Toggle
          label="Gender"
          options={[
            ["female", "Female"],
            ["male", "Male"],
          ]}
          value={gender}
          onChange={setGender}
        />
        <Toggle
          label="Units"
          options={[
            ["metric", "Metric"],
            ["imperial", "Imperial"],
          ]}
          value={units}
          onChange={switchUnits}
        />
      </div>

      <div className={`mt-5 grid gap-4 ${compact ? "grid-cols-2" : "sm:grid-cols-2"}`}>
        <NumberInput
          id="photo-height"
          label={`Height (${units === "metric" ? "cm" : "in"})`}
          value={height}
          onChange={setHeight}
          required
        />
        <NumberInput
          id="photo-weight"
          label={
            compact
              ? `Weight (${units === "metric" ? "kg" : "lb"})`
              : `Weight (${units === "metric" ? "kg" : "lb"}, optional — improves accuracy)`
          }
          value={weight}
          onChange={setWeight}
        />
      </div>
      {compact && (
        <p className="mt-2 text-xs text-muted">Height is required. Weight is optional.</p>
      )}
      <label className="mt-3 flex items-center gap-2 text-sm text-ink-soft">
        <input type="checkbox" checked={shoes} onChange={(e) => setShoes(e.target.checked)} />
        I'm wearing shoes in the photos
      </label>

      <div className={`mt-5 grid gap-4 ${compact ? "grid-cols-2" : "sm:grid-cols-2"}`}>
        <PhotoInput label="Front photo" file={front} onChange={setFront} onError={setLocalError} />
        <PhotoInput label="Side photo" file={side} onChange={setSide} onError={setLocalError} />
      </div>

      {(localError || start.error) && (
        <p role="alert" className="mt-4 rounded-xl bg-error/8 px-4 py-3 text-sm text-error">
          {localError ??
            (start.error instanceof Error
              ? start.error.message
              : "Upload didn't complete — please retry.")}
        </p>
      )}

      <Button
        type="button"
        size="lg"
        className="mt-6 w-full"
        onClick={submit}
        loading={start.isPending}
      >
        {submitLabel}
      </Button>
    </div>
  );
}

export function PhotoInput({
  label,
  file,
  onChange,
  onError,
  facing = "environment",
}: {
  label: string;
  file: File | null;
  onChange: (file: File | null) => void;
  onError: (message: string | null) => void;
  facing?: "environment" | "user";
}) {
  const preview = usePhotoPreview(file);
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (!open || !dialog.current) return;
    const element = dialog.current;
    element.showModal();
    return () => element.close();
  }, [open]);

  return (
    <div className="photo-input flex flex-col items-center justify-center gap-2 rounded-xl bg-paper/60 p-3 text-center text-sm text-ink-soft">
      {preview ? (
        <img src={preview} alt={label} className="h-44 w-full rounded-xl object-contain" />
      ) : (
        <span className="flex h-28 items-center text-xs text-muted">
          {facing === "user" ? "Face the camera" : "Keep your whole body in frame"}
        </span>
      )}
      <span className="font-semibold text-ink">{label}</span>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-ink px-3 text-xs font-medium text-white transition-colors hover:bg-ink/85"
      >
        <Camera size={15} />
        {preview ? "Retake photo" : "Open live camera"}
      </button>
      {open && (
        <dialog
          ref={dialog}
          className="camera-dialog"
          aria-label={`Take ${label.toLowerCase()} photo`}
          onCancel={() => setOpen(false)}
        >
          <header className="camera-dialog-header">
            <h2>{label}</h2>
            <button type="button" aria-label="Close camera" onClick={() => setOpen(false)}>
              <X size={18} />
            </button>
          </header>
          <LiveCamera
            label={label}
            facing={facing}
            hint={
              facing === "user"
                ? "Face the light. Keep your face in view and your expression relaxed."
                : "Keep your head and feet in view. Ask someone to hold the camera at chest height."
            }
            onConfirm={(photo) => {
              onError(null);
              onChange(photo);
              setOpen(false);
            }}
          />
        </dialog>
      )}
    </div>
  );
}

// ── Step 2: measuring ─────────────────────────────────────────────────

function Measuring({ label }: { label: string }) {
  return (
    <div role="status" aria-live="polite" className="py-10 text-center">
      <div className="mx-auto size-8 animate-spin rounded-full border-2 border-line border-t-ink" />
      <p className="mt-4 text-sm font-semibold text-ink">{label}</p>
      <p className="mt-1 text-xs text-muted">This usually takes a few seconds.</p>
    </div>
  );
}

function Problem({
  message,
  onRetry,
  retryLabel,
}: {
  message: string;
  onRetry: () => void;
  retryLabel: string;
}) {
  return (
    <div className="py-6">
      <p role="alert" className="rounded-xl bg-error/8 px-4 py-3 text-sm text-error">
        {message}
      </p>
      <Button type="button" variant="outline" className="mt-4" onClick={onRetry}>
        {retryLabel}
      </Button>
    </div>
  );
}

// ── Step 3: review, correct, save ─────────────────────────────────────

function ReviewStep({
  capture,
  onRetake,
  onSaved,
}: {
  capture: PhotoMeasurement;
  onRetake: () => void;
  onSaved: (profile: AvatarProfile) => void;
}) {
  const baseline = { ...capture.profile };
  if (capture.gender !== "female") {
    delete baseline.bust_circumference_cm;
    delete baseline.under_bust_circumference_cm;
  }
  const review = useMeasurementReview(baseline, false);

  const save = useMutation({
    mutationFn: (values: Partial<Record<PhotoMeasurementField, number>>) =>
      getRuntimeProvider().applyPhotoMeasurement(capture.captureId, values),
    onSuccess: onSaved,
  });

  function confirm() {
    if (save.isPending) return;
    const values = review.corrections();
    if (values) save.mutate(values);
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-soft">
          Check these against a tape measure. Use a slider or enter a value to correct anything that
          looks off.
        </p>
        <Toggle
          label="Units"
          options={[
            ["metric", "cm / kg"],
            ["imperial", "in / lb"],
          ]}
          value={review.units}
          onChange={review.setUnits}
          disabled={save.isPending}
        />
      </div>

      {capture.warnings.length > 0 && (
        <div className="mt-4 rounded-xl bg-mist px-4 py-3 text-[13px] text-ink-soft">
          <p className="font-semibold text-ink">Some numbers may be less accurate:</p>
          <ul className="mt-1 list-disc pl-5">
            {capture.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <MeasurementSliders review={review} disabled={save.isPending} />

      {(review.validation || save.error) && (
        <p role="alert" className="mt-3 rounded-xl bg-error/8 px-4 py-3 text-sm text-error">
          {review.validation ??
            (save.error instanceof Error
              ? save.error.message
              : "Saving didn't complete — please retry.")}
        </p>
      )}

      <div className="mt-6 flex flex-col gap-3 sm:flex-row">
        <Button
          type="button"
          size="lg"
          className="flex-1"
          onClick={confirm}
          loading={save.isPending}
        >
          Save to my profile
        </Button>
        <Button
          type="button"
          size="lg"
          variant="outline"
          onClick={onRetake}
          disabled={save.isPending}
        >
          Retake photos
        </Button>
      </div>
    </div>
  );
}

// ── Small controls ────────────────────────────────────────────────────

function Toggle<T extends string>({
  label,
  options,
  value,
  onChange,
  disabled = false,
}: {
  label: string;
  options: [T, string][];
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}) {
  return (
    <div
      className="flex rounded-full border border-line bg-paper p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]"
      role="group"
      aria-label={label}
    >
      {options.map(([key, text]) => (
        <button
          key={key}
          type="button"
          onClick={() => onChange(key)}
          aria-pressed={value === key}
          disabled={disabled}
          className={`min-h-9 rounded-full px-3.5 text-xs font-semibold ${
            value === key ? "bg-ink text-canvas" : "text-muted hover:text-ink"
          }`}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

function NumberInput({
  id,
  label,
  value,
  onChange,
  required,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1.5 text-xs font-semibold text-ink-soft">
      {label}
      <input
        id={id}
        type="number"
        inputMode="decimal"
        required={required}
        className="h-11 rounded-xl border border-line bg-white px-3 text-sm text-ink"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
