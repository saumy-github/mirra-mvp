import { useState } from "react";
import type { PhotoMeasurementField } from "@/integrations/mirra-api";
import type { UnitSystem } from "@/lib/units";
import {
  reviewChanged,
  reviewCorrections,
  reviewFields,
  reviewInput,
  reviewSlider,
  type MeasurementBaseline,
  type MeasurementEdits,
} from "./measurement-review";

export function useMeasurementReview(baseline: MeasurementBaseline, includeOptionalWeight = true) {
  const [units, setUnits] = useState<UnitSystem>("metric");
  const [edits, setEdits] = useState<MeasurementEdits>({});
  const [validation, setValidation] = useState<string | null>(null);
  const fields = reviewFields(baseline, includeOptionalWeight);

  function setInput(key: PhotoMeasurementField, text: string) {
    setEdits((previous) => ({ ...previous, [key]: reviewInput(text, key, units) }));
    setValidation(null);
  }

  function setSlider(key: PhotoMeasurementField, value: number) {
    setEdits((previous) => ({ ...previous, [key]: reviewSlider(value, key, units) }));
    setValidation(null);
  }

  function resetField(key: PhotoMeasurementField) {
    setEdits((previous) => {
      const next = { ...previous };
      delete next[key];
      return next;
    });
    setValidation(null);
  }

  function resetAll() {
    setEdits({});
    setValidation(null);
  }

  function corrections() {
    const result = reviewCorrections(baseline, edits, includeOptionalWeight);
    setValidation(result.error);
    return result.corrections;
  }

  return {
    baseline,
    edits,
    fields,
    units,
    setUnits,
    setInput,
    setSlider,
    resetField,
    resetAll,
    corrections,
    validation,
    changedCount: fields.filter((field) => reviewChanged(baseline, edits, field.key)).length,
  };
}

export type MeasurementReviewControls = ReturnType<typeof useMeasurementReview>;
