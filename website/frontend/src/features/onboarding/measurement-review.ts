import type { PhotoMeasurementField } from "@/integrations/mirra-api";
import type { UnitSystem } from "@/lib/units";
import { REVIEW_FIELDS } from "./setup-utils";

export type MeasurementBaseline = Partial<Record<PhotoMeasurementField, number | null>>;
export interface MeasurementEdit {
  metric: number | null;
  text: string;
  units: UnitSystem;
}
export type MeasurementEdits = Partial<Record<PhotoMeasurementField, MeasurementEdit>>;

const POUNDS_PER_KG = 2.2046226218;

export function reviewFields(baseline: MeasurementBaseline, includeOptionalWeight = true) {
  return REVIEW_FIELDS.filter(
    (field) => baseline[field.key] != null || (field.key === "weight_kg" && includeOptionalWeight),
  );
}

export function reviewUnit(key: PhotoMeasurementField, units: UnitSystem) {
  return key === "weight_kg"
    ? units === "metric"
      ? "kg"
      : "lb"
    : units === "metric"
      ? "cm"
      : "in";
}

export function toReviewUnits(metric: number, key: PhotoMeasurementField, units: UnitSystem) {
  return units === "metric" ? metric : key === "weight_kg" ? metric * POUNDS_PER_KG : metric / 2.54;
}

export function fromReviewUnits(value: number, key: PhotoMeasurementField, units: UnitSystem) {
  return units === "metric" ? value : key === "weight_kg" ? value / POUNDS_PER_KG : value * 2.54;
}

export function reviewValue(
  metric: number | null | undefined,
  key: PhotoMeasurementField,
  units: UnitSystem,
) {
  if (metric == null || !Number.isFinite(metric)) return "";
  return String(Math.round(toReviewUnits(metric, key, units) * 100) / 100);
}

export function reviewInput(
  text: string,
  key: PhotoMeasurementField,
  units: UnitSystem,
): MeasurementEdit {
  return {
    metric: text.trim() ? fromReviewUnits(Number(text), key, units) : null,
    text,
    units,
  };
}

export function reviewSlider(
  value: number,
  key: PhotoMeasurementField,
  units: UnitSystem,
): MeasurementEdit {
  // Every slider step is 0.1 cm / kg, including when the display is imperial.
  const metric = Math.round(fromReviewUnits(value, key, units) * 10) / 10;
  return { metric, text: reviewValue(metric, key, units), units };
}

export function reviewDisplay(
  baseline: MeasurementBaseline,
  edits: MeasurementEdits,
  key: PhotoMeasurementField,
  units: UnitSystem,
) {
  const edit = edits[key];
  // Switching units only changes the display. Never convert a rounded display
  // back into the metric draft: repeated switches would accumulate fit error.
  return edit?.units === units
    ? edit.text
    : reviewValue(edit ? edit.metric : baseline[key], key, units);
}

export function reviewChanged(
  baseline: MeasurementBaseline,
  edits: MeasurementEdits,
  key: PhotoMeasurementField,
) {
  const edit = edits[key];
  if (!edit) return false;
  const initial = baseline[key] ?? null;
  return initial == null || edit.metric == null
    ? initial !== edit.metric
    : !Number.isFinite(edit.metric) || Math.abs(initial - edit.metric) > 1e-8;
}

export function reviewCorrections(
  baseline: MeasurementBaseline,
  edits: MeasurementEdits,
  includeOptionalWeight = true,
):
  | { corrections: Partial<Record<PhotoMeasurementField, number>>; error: null }
  | { corrections: null; error: string } {
  const corrections: Partial<Record<PhotoMeasurementField, number>> = {};
  for (const field of reviewFields(baseline, includeOptionalWeight)) {
    const edit = edits[field.key];
    if (!edit) continue;
    if (edit.metric == null) {
      if (field.key === "weight_kg" && baseline.weight_kg == null) continue;
      return { corrections: null, error: `Enter your ${field.label.toLowerCase()}.` };
    }
    if (!Number.isFinite(edit.metric) || edit.metric < field.min || edit.metric > field.max) {
      return {
        corrections: null,
        error: `Check your ${field.label.toLowerCase()} — that value is outside the supported range.`,
      };
    }
    if (reviewChanged(baseline, edits, field.key)) corrections[field.key] = edit.metric;
  }
  return { corrections, error: null };
}
