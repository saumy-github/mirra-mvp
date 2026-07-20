import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MeasurementRow } from "@/features/onboarding/components/measurement-row";
import { Button } from "@/components/ui/button";
import { useAvatarProfile, useAccount } from "@/hooks/use-shopper";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { MeasurementKey } from "@/integrations/mirra-api/types";
import { track } from "@/lib/analytics";
import type { UnitSystem } from "@/lib/units";

export default function ProfileMeasurements() {
  const qc = useQueryClient();
  const { data: account } = useAccount();
  const { data: avatar } = useAvatarProfile(!!account);
  const [draft, setDraft] = useState<Partial<Record<MeasurementKey, number>>>({});
  const [units, setUnits] = useState<UnitSystem>("metric");

  useEffect(() => {
    if (avatar) setUnits(avatar.unitsPreference);
  }, [avatar]);

  const save = useMutation({
    mutationFn: () => getRuntimeProvider().updateMeasurements(draft, { unitsPreference: units }),
    onSuccess: (profile) => {
      qc.setQueryData(["account", "avatar-profile"], profile);
      setDraft({});
      track("measurements_updated", { authenticated: true });
    },
  });

  if (!avatar) {
    return <p className="text-sm text-muted">Measurements appear here once an avatar exists.</p>;
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Review your measurements</h1>
        <div
          className="flex rounded-full border border-line-strong p-0.5"
          role="group"
          aria-label="Units"
        >
          {(["metric", "imperial"] as const).map((u) => (
            <button
              key={u}
              type="button"
              onClick={() => setUnits(u)}
              aria-pressed={units === u}
              className={`rounded-full px-3 py-1 text-xs capitalize ${units === u ? "bg-ink text-canvas" : "text-muted"}`}
            >
              {u}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 divide-y divide-line">
        {avatar.measurements
          .filter((m) => m.supported)
          .map((m) => (
            <MeasurementRow
              key={m.key}
              field={{
                ...m,
                value: draft[m.key] ?? m.value,
                estimated: m.estimated && !(m.key in draft),
              }}
              units={units}
              onChange={(value) => setDraft((d) => ({ ...d, [m.key]: value }))}
            />
          ))}
      </div>

      {save.error && (
        <p role="alert" className="mt-2 text-sm text-error">
          {save.error instanceof Error ? save.error.message : "Saving didn't complete."}
        </p>
      )}

      <Button
        className="mt-6"
        onClick={() => save.mutate()}
        disabled={Object.keys(draft).length === 0}
        loading={save.isPending}
      >
        Save changes
      </Button>
    </div>
  );
}
