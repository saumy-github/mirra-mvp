import { useNavigate, useSearchParams } from "react-router-dom";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MeasurementRow } from "@/features/onboarding/components/measurement-row";
import { Button } from "@/components/ui/button";
import { MirraMark } from "@/components/ui/logo";
import { Skeleton } from "@/components/ui/misc";
import { useAccount } from "@/hooks/use-shopper";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import { FIELD_META } from "@/integrations/mirra-api/live-schemas";
import type { MeasurementKey } from "@/integrations/mirra-api/types";
import { track } from "@/lib/analytics";
import { postAuthDestination } from "@/lib/post-auth";
import type { UnitSystem } from "@/lib/units";

const MEASUREMENT_KEYS = Object.keys(FIELD_META) as MeasurementKey[];
type Gender = "male" | "female";
type Accuracy = "accurate" | "approx";

const GENDER_OPTIONS: ReadonlyArray<{ value: Gender; label: string }> = [
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
];

const ACCURACY_OPTIONS: ReadonlyArray<{
  value: Accuracy;
  label: string;
  description: string;
}> = [
  {
    value: "accurate",
    label: "Measured",
    description: "I used a tape or known figures.",
  },
  {
    value: "approx",
    label: "Best estimate",
    description: "These are close, but not exact.",
  },
];

function defaultDraft(): Record<MeasurementKey, number> {
  return Object.fromEntries(
    MEASUREMENT_KEYS.map((key) => [key, FIELD_META[key].fallback]),
  ) as Record<MeasurementKey, number>;
}

/**
 * First-time, manual measurement intake — no photo/avatar required. Saves
 * straight to the `measurements` collection (website/backend measurements
 * service). Distinct from pages/onboarding/Measurements.tsx, which reviews
 * values an already-generated avatar estimated from photos.
 */
export default function Measurements() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const qc = useQueryClient();
  const { data: account, isLoading: accountLoading } = useAccount();
  const formRef = useRef<HTMLFormElement>(null);

  const [gender, setGender] = useState<Gender | null>(null);
  const [accuracy, setAccuracy] = useState<Accuracy | null>(null);
  const [units, setUnits] = useState<UnitSystem>("metric");
  const [draft, setDraft] = useState<Record<MeasurementKey, number>>(defaultDraft);
  const [invalidRows, setInvalidRows] = useState<Set<MeasurementKey>>(() => new Set());
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const currentPath = `/measurements${params.size ? `?${params.toString()}` : ""}`;

  useEffect(() => {
    if (!accountLoading && !account) {
      navigate(`/auth/login?next=${encodeURIComponent(currentPath)}`, { replace: true });
    }
  }, [account, accountLoading, currentPath, navigate]);

  const save = useMutation({
    mutationFn: (submission: {
      measurements: Record<MeasurementKey, number>;
      units: UnitSystem;
      gender: Gender;
      accuracy: Accuracy;
    }) =>
      getRuntimeProvider().updateMeasurements(submission.measurements, {
        unitsPreference: submission.units,
        gender: submission.gender,
        accuracy: submission.accuracy,
      }),
    onSuccess: (profile) => {
      qc.setQueryData(["account", "avatar-profile"], profile);
      track("measurements_updated", { authenticated: true });
      navigate(postAuthDestination(params.get("next") ?? "/onboarding/avatar"));
    },
  });

  const fields = useMemo(
    () =>
      MEASUREMENT_KEYS.map((key) => ({
        key,
        label: FIELD_META[key].label,
        value: draft[key],
        unit: FIELD_META[key].unit,
        min: FIELD_META[key].min,
        max: FIELD_META[key].max,
        step: 0.5,
        estimated: false,
        supported: true,
      })),
    [draft],
  );

  const invalidKeys = useMemo(() => {
    const next = new Set(invalidRows);
    for (const field of fields) {
      if (!Number.isFinite(field.value) || field.value < field.min || field.value > field.max) {
        next.add(field.key);
      }
    }
    return next;
  }, [fields, invalidRows]);

  const completedChoices = Number(Boolean(gender)) + Number(Boolean(accuracy));
  const validMeasurementCount = fields.length - invalidKeys.size;
  const formReady = Boolean(gender && accuracy && invalidKeys.size === 0);

  function handleFieldValidity(key: MeasurementKey, valid: boolean) {
    setInvalidRows((current) => {
      const currentlyInvalid = current.has(key);
      if (currentlyInvalid === !valid) return current;

      const next = new Set(current);
      if (valid) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitAttempted(true);

    if (!gender) {
      formRef.current?.querySelector<HTMLInputElement>('input[name="gender"]')?.focus();
      return;
    }
    if (!accuracy) {
      formRef.current?.querySelector<HTMLInputElement>('input[name="accuracy"]')?.focus();
      return;
    }
    if (invalidKeys.size > 0) {
      formRef.current?.querySelector<HTMLInputElement>('input[aria-invalid="true"]')?.focus();
      return;
    }

    save.mutate({ measurements: draft, units, gender, accuracy });
  }

  if (accountLoading || !account) {
    return (
      <main className="grid min-h-dvh place-items-center bg-white px-5">
        <Skeleton className="h-48 w-full max-w-sm rounded-(--radius-panel) bg-[#eceae5]" />
      </main>
    );
  }

  return (
    <main className="min-h-dvh bg-white text-[#20211f]">
      <header className="flex h-16 items-center justify-between px-5 sm:px-8">
        <div className="flex items-center gap-3">
          <MirraMark size={22} strokeWidth={1.15} />
          <span className="text-[13px] font-medium tracking-[-0.01em] text-[#686963]">
            Body profile
          </span>
        </div>
        <div
          className="flex items-center gap-3"
          role="progressbar"
          aria-label="Body profile setup progress"
          aria-valuemin={1}
          aria-valuemax={3}
          aria-valuenow={1}
          aria-valuetext="Step 1 of 3"
        >
          <span className="text-[11px] font-medium text-[#686963]">Step 1 of 3</span>
          <span className="h-1 w-16 rounded-full bg-[#eceae5]" aria-hidden>
            <span className="block h-full w-1/3 rounded-full bg-[#1b1c1a]" />
          </span>
        </div>
      </header>

      <form
        ref={formRef}
        noValidate
        onSubmit={handleSubmit}
        className="mx-auto w-full max-w-3xl px-5 pt-10 pb-6 sm:px-8 sm:pt-14 sm:pb-8"
      >
        <section className="max-w-xl">
          <h1 className="text-[clamp(2rem,5vw,2.75rem)] leading-[1.08] font-semibold tracking-[-0.04em] text-balance">
            Tell us your measurements
          </h1>
          <p className="mt-3 max-w-lg text-[15px] leading-6 text-[#686963]">
            Start with the values below and adjust only what you know. You can review everything
            later.
          </p>
        </section>

        <section className="mt-12" aria-labelledby="profile-details-heading">
          <div className="max-w-xl">
            <h2 id="profile-details-heading" className="text-lg font-semibold tracking-tight">
              Profile details
            </h2>
            <p className="mt-1 text-[12px] leading-5 text-[#686963]">
              Choose both options so the avatar pipeline knows how to interpret the values.
            </p>
          </div>

          <div className="mt-6 grid gap-x-10 gap-y-8 md:grid-cols-2">
            <fieldset
              className="min-w-0 border-0 p-0"
              aria-describedby={`gender-help${submitAttempted && !gender ? " gender-error" : ""}`}
            >
              <legend className="text-[13px] font-medium tracking-[-0.01em]">
                Avatar model
                <span className="ml-1 text-error" aria-hidden>
                  *
                </span>
              </legend>
              <p id="gender-help" className="mt-1 text-[11px] leading-4 text-[#777872]">
                Select the current model that fits you best.
              </p>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {GENDER_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-(--radius-control) border px-3.5 text-[13px] font-medium transition-colors has-[input:focus-visible]:ring-2 has-[input:focus-visible]:ring-[#20211f]/30 has-[input:focus-visible]:ring-offset-2 ${
                      gender === option.value
                        ? "border-[#20211f] bg-[#20211f] text-[#f2f0ea]"
                        : "border-[#e0ded8] bg-[#faf8f5] text-[#686963] hover:border-[#aaa69f] hover:text-[#20211f]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="gender"
                      value={option.value}
                      checked={gender === option.value}
                      required
                      aria-invalid={submitAttempted && !gender ? true : undefined}
                      onChange={() => setGender(option.value)}
                      className="size-4 shrink-0 accent-[#20211f] focus-visible:outline-none"
                    />
                    {option.label}
                  </label>
                ))}
              </div>
              {submitAttempted && !gender && (
                <p id="gender-error" role="alert" className="mt-2 text-xs text-error">
                  Choose an avatar model before continuing.
                </p>
              )}
            </fieldset>

            <fieldset
              className="min-w-0 border-0 p-0"
              aria-describedby={`accuracy-help${
                submitAttempted && !accuracy ? " accuracy-error" : ""
              }`}
            >
              <legend className="text-[13px] font-medium tracking-[-0.01em]">
                Measurement accuracy
                <span className="ml-1 text-error" aria-hidden>
                  *
                </span>
              </legend>
              <p id="accuracy-help" className="mt-1 text-[11px] leading-4 text-[#777872]">
                Be honest here—estimated values are completely okay.
              </p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2 md:grid-cols-1">
                {ACCURACY_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`flex min-h-14 cursor-pointer items-start gap-3 rounded-(--radius-control) border px-3.5 py-3 transition-colors has-[input:focus-visible]:ring-2 has-[input:focus-visible]:ring-[#20211f]/30 has-[input:focus-visible]:ring-offset-2 ${
                      accuracy === option.value
                        ? "border-[#20211f] bg-[#20211f] text-[#f2f0ea]"
                        : "border-[#e0ded8] bg-[#faf8f5] text-[#686963] hover:border-[#aaa69f] hover:text-[#20211f]"
                    }`}
                  >
                    <input
                      type="radio"
                      name="accuracy"
                      value={option.value}
                      checked={accuracy === option.value}
                      required
                      aria-invalid={submitAttempted && !accuracy ? true : undefined}
                      onChange={() => setAccuracy(option.value)}
                      className="mt-0.5 size-4 shrink-0 accent-[#20211f] focus-visible:outline-none"
                    />
                    <span>
                      <span className="block text-[13px] font-medium">{option.label}</span>
                      <span
                        className={`mt-0.5 block text-[11px] leading-4 ${
                          accuracy === option.value ? "text-[#d6d3cd]" : "text-[#777872]"
                        }`}
                      >
                        {option.description}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
              {submitAttempted && !accuracy && (
                <p id="accuracy-error" role="alert" className="mt-2 text-xs text-error">
                  Tell us whether these values are measured or estimated.
                </p>
              )}
            </fieldset>
          </div>

          <fieldset className="mt-8 min-w-0 border-0 p-0">
            <legend className="text-[13px] font-medium tracking-[-0.01em]">Display units</legend>
            <div className="mt-3 inline-grid grid-cols-2 gap-1 rounded-xl bg-[#efede8] p-1">
              {(["metric", "imperial"] as const).map((unit) => (
                <label
                  key={unit}
                  className={`cursor-pointer rounded-[9px] px-4 py-2 text-[12px] font-medium capitalize transition-colors has-[input:focus-visible]:ring-2 has-[input:focus-visible]:ring-[#20211f]/30 ${
                    units === unit
                      ? "bg-white text-[#20211f] shadow-sm"
                      : "text-[#686963] hover:text-[#20211f]"
                  }`}
                >
                  <input
                    type="radio"
                    name="units"
                    value={unit}
                    checked={units === unit}
                    onChange={() => {
                      setUnits(unit);
                      setInvalidRows(new Set());
                    }}
                    className="sr-only"
                  />
                  {unit}
                </label>
              ))}
            </div>
          </fieldset>
        </section>

        <section className="mt-12">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between sm:gap-6">
            <div>
              <h2 id="measurements-heading" className="text-lg font-semibold tracking-tight">
                Measurements
              </h2>
              <p className="mt-1 text-[12px] leading-5 text-[#686963]">
                The starting values are safe estimates. Change only the figures you know.
              </p>
            </div>
            <p className="text-[11px] font-medium text-[#686963]">
              {validMeasurementCount} of {fields.length} values in range
            </p>
          </div>
          <div
            className="mt-6 rounded-(--radius-panel) border border-[#ebe9e4] bg-[#faf8f5] px-5 py-6 sm:px-7 sm:py-8"
            aria-labelledby="measurements-heading"
          >
            <div className="grid gap-x-10 gap-y-7 md:grid-cols-2">
              {fields.map((field) => (
                <MeasurementRow
                  key={field.key}
                  field={field}
                  units={units}
                  showBounds={false}
                  onChange={(value) => setDraft((d) => ({ ...d, [field.key]: value }))}
                  onValidityChange={(valid) => handleFieldValidity(field.key, valid)}
                />
              ))}
            </div>
          </div>
        </section>

        {save.error && (
          <p
            role="alert"
            className="mt-4 rounded-(--radius-control) border border-error/20 bg-error/8 px-4 py-3 text-sm text-error"
          >
            {save.error instanceof Error
              ? save.error.message
              : "Saving didn't complete — please retry."}
          </p>
        )}

        <div className="sticky bottom-4 z-20 mt-10 flex flex-col gap-3.5 rounded-card border border-[#e5e3dc] bg-white/95 px-5 py-3.5 shadow-[0_16px_40px_-16px_rgba(24,24,23,0.14),0_4px_12px_-4px_rgba(24,24,23,0.06)] backdrop-blur-md sm:bottom-6 sm:flex-row sm:items-center sm:justify-between sm:gap-6 sm:px-6 sm:py-4">
          <div role="status" aria-live="polite" className="min-w-0">
            <div className="flex items-center gap-2">
              <span
                className={`size-2 rounded-full ${
                  formReady ? "bg-emerald-500" : "bg-[#9b557a]"
                }`}
                aria-hidden
              />
              <p className="text-[13px] font-semibold tracking-[-0.01em] text-[#20211f]">
                {formReady ? "Ready to save" : "Setup status"}
              </p>
            </div>
            <p className="mt-0.5 text-[11px] leading-4 text-[#686963]">
              {completedChoices} of 2 choices complete · {validMeasurementCount} of{" "}
              {fields.length} values in range
            </p>
          </div>
          <Button
            type="submit"
            size="lg"
            className="w-full shrink-0 bg-[#1b1c1a] px-8 text-[13px] font-medium text-white shadow-none transition-transform hover:bg-[#2c2d2a] active:scale-[0.99] focus-visible:ring-2 focus-visible:ring-[#20211f]/35 focus-visible:ring-offset-2 sm:w-auto"
            loading={save.isPending}
          >
            Save and continue
            <span aria-hidden>→</span>
          </Button>
        </div>
      </form>
    </main>
  );
}
