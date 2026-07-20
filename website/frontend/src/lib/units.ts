/** Metric ⇄ imperial conversion for measurement display. Values are stored metric. */

export type UnitSystem = "metric" | "imperial";

export function cmToDisplay(cm: number, system: UnitSystem): { value: string; unit: string } {
  if (system === "metric") return { value: cm.toFixed(0), unit: "cm" };
  const totalInches = cm / 2.54;
  const feet = Math.floor(totalInches / 12);
  const inches = Math.round(totalInches % 12);
  return { value: `${feet}′ ${inches}″`, unit: "ft/in" };
}

export function cmToInches(cm: number): number {
  return Math.round((cm / 2.54) * 10) / 10;
}
export function inchesToCm(inches: number): number {
  return Math.round(inches * 2.54 * 10) / 10;
}

export function kgToDisplay(kg: number, system: UnitSystem): { value: string; unit: string } {
  if (system === "metric") return { value: kg.toFixed(0), unit: "kg" };
  return { value: (kg * 2.20462).toFixed(0), unit: "lb" };
}
export function lbToKg(lb: number): number {
  return Math.round((lb / 2.20462) * 10) / 10;
}

export function clampMeasurement(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.min(max, Math.max(min, value));
}

export function isValidMeasurement(value: number, min: number, max: number): boolean {
  return !Number.isNaN(value) && value >= min && value <= max;
}
