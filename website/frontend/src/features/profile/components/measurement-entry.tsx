import { useState } from "react";
import { MeasurementForm } from "./measurement-form";
import { PhotoMeasurementFlow } from "./photo-measurement";
import type { AvatarProfile } from "@/integrations/mirra-api/types";

type Method = "photos" | "manual";

/**
 * First-time measurement entry: measure from two photos, or type the numbers
 * in. Both end in the same saved measurements (user_measurements), so
 * everything after this — avatar generation, try-on — is unchanged.
 */
export function MeasurementEntry({
  onSaved,
}: {
  onSaved?: (profile: AvatarProfile, method: Method) => void;
}) {
  const [method, setMethod] = useState<Method>("photos");

  return (
    <div>
      <div
        className="mb-6 flex rounded-full border border-line bg-paper p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]"
        role="tablist"
        aria-label="How to add your measurements"
      >
        {(
          [
            ["photos", "From photos"],
            ["manual", "Enter manually"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            aria-selected={method === key}
            onClick={() => setMethod(key)}
            className={`min-h-10 flex-1 rounded-full px-3 text-sm font-semibold whitespace-nowrap ${
              method === key ? "bg-ink text-canvas" : "text-muted hover:text-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {method === "photos" ? (
        <PhotoMeasurementFlow onSaved={(profile) => onSaved?.(profile, "photos")} />
      ) : (
        <MeasurementForm onSaved={(profile) => onSaved?.(profile, "manual")} />
      )}
    </div>
  );
}
