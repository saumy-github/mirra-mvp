import { useMemo, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MeasurementRow } from "./measurement-row";
import { Button } from "@/components/ui/button";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import { FIELD_META } from "@/integrations/mirra-api/live-schemas";
import type { AvatarProfile, MeasurementKey } from "@/integrations/mirra-api/types";
import { track } from "@/lib/analytics";
import type { UnitSystem } from "@/lib/units";

const MEASUREMENT_KEYS = Object.keys(FIELD_META) as MeasurementKey[];

function defaultDraft(): Record<MeasurementKey, number> {
  return Object.fromEntries(
    MEASUREMENT_KEYS.map((key) => [key, FIELD_META[key].fallback]),
  ) as Record<MeasurementKey, number>;
}

/**
 * First-time, manual measurement entry — gender/accuracy/units toggles plus
 * every v1-supported field. Used by ProfileMeasurements.tsx's empty state
 * (no avatar/measurements saved yet — /measurements, the old standalone
 * entry point, was removed once /profile/measurements could do this
 * itself). Saves straight to `user_measurements` (via updateMeasurements())
 * — see .agent/website-launch/23-profile-measurements-form-and-user-measurements-model.md.
 */
export function MeasurementForm({
  onSaved,
  saveLabel = "Save measurements",
}: {
  onSaved?: (profile: AvatarProfile) => void;
  saveLabel?: string;
}) {
  const qc = useQueryClient();
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
      onSaved?.(profile);
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

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
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
        {saveLabel}
      </Button>
    </div>
  );
}
