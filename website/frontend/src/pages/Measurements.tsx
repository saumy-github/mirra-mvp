import { useNavigate, useSearchParams } from "react-router-dom";
import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MeasurementRow } from "@/features/onboarding/components/measurement-row";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { useAccount } from "@/hooks/use-shopper";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import { FIELD_META } from "@/integrations/mirra-api/live-schemas";
import type { MeasurementKey } from "@/integrations/mirra-api/types";
import { track } from "@/lib/analytics";
import type { UnitSystem } from "@/lib/units";

const MEASUREMENT_KEYS = Object.keys(FIELD_META) as MeasurementKey[];

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

  const [gender, setGender] = useState<"male" | "female">("male");
  const [accuracy, setAccuracy] = useState<"accurate" | "approx">("accurate");
  const [units, setUnits] = useState<UnitSystem>("metric");
  const [draft, setDraft] = useState<Record<MeasurementKey, number>>(defaultDraft);

  const save = useMutation({
    mutationFn: () =>
      getRuntimeProvider().updateMeasurements(draft, { unitsPreference: units, gender, accuracy }),
    onSuccess: (profile) => {
      qc.setQueryData(["account", "avatar-profile"], profile);
      track("measurements_updated", { authenticated: true });
      navigate(params.get("next") ?? "/onboarding/avatar");
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

  if (accountLoading) {
    return (
      <main className="grid min-h-dvh place-items-center">
        <Skeleton className="h-64 w-80" />
      </main>
    );
  }

  if (!account) {
    navigate(`/auth/login?next=${encodeURIComponent("/measurements")}`, { replace: true });
    return null;
  }

  return (
    <main className="min-h-dvh bg-canvas px-5 py-10 sm:px-8">
      <div className="mx-auto w-full max-w-155">
        <p className="mono-tag tracking-widest!">Your measurements</p>
        <h1 className="mt-2 text-[clamp(1.8rem,4vw,2.5rem)] leading-[1.06] font-semibold tracking-[-0.04em]">
          Tell us your body measurements.
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-muted">
          These are used to build your digital twin. You can fine-tune them again later — nothing
          here is permanent.
        </p>

        <div className="mt-7 flex flex-wrap items-center gap-3">
          <div
            className="flex rounded-full border border-line bg-paper p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]"
            role="group"
            aria-label="Gender"
          >
            {(["male", "female"] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGender(g)}
                aria-pressed={gender === g}
                className={`min-h-9 rounded-full px-3.5 text-xs font-semibold capitalize ${
                  gender === g ? "bg-ink text-canvas" : "text-muted hover:text-ink"
                }`}
              >
                {g}
              </button>
            ))}
          </div>

          <div
            className="flex rounded-full border border-line bg-paper p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]"
            role="group"
            aria-label="How precise are these numbers"
          >
            {(
              [
                { key: "accurate", label: "I measured these" },
                { key: "approx", label: "These are estimates" },
              ] as const
            ).map((opt) => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setAccuracy(opt.key)}
                aria-pressed={accuracy === opt.key}
                className={`min-h-9 rounded-full px-3.5 text-xs font-semibold ${
                  accuracy === opt.key ? "bg-ink text-canvas" : "text-muted hover:text-ink"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div
            className="flex rounded-full border border-line bg-paper p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]"
            role="group"
            aria-label="Units"
          >
            {(["metric", "imperial"] as const).map((u) => (
              <button
                key={u}
                type="button"
                onClick={() => setUnits(u)}
                aria-pressed={units === u}
                className={`min-h-9 rounded-full px-3.5 text-xs font-semibold capitalize ${
                  units === u ? "bg-ink text-canvas" : "text-muted hover:text-ink"
                }`}
              >
                {u}
              </button>
            ))}
          </div>
        </div>

        <div className="mt-7 rounded-3xl border border-line bg-paper/80 px-5 shadow-[0_16px_44px_-34px_rgba(0,0,0,0.3)] sm:px-6">
          <div className="divide-y divide-line">
            {fields.map((field) => (
              <MeasurementRow
                key={field.key}
                field={field}
                units={units}
                onChange={(value) => setDraft((d) => ({ ...d, [field.key]: value }))}
              />
            ))}
          </div>
        </div>

        {save.error && (
          <p role="alert" className="mt-3 rounded-xl bg-error/8 px-4 py-3 text-sm text-error">
            {save.error instanceof Error ? save.error.message : "Saving didn't complete — please retry."}
          </p>
        )}

        <Button
          type="button"
          size="lg"
          className="mt-6 w-full"
          onClick={() => save.mutate()}
          loading={save.isPending}
        >
          Save measurements
        </Button>
      </div>
    </main>
  );
}
