import { useId } from "react";
import { motion } from "motion/react";
import type { MeasurementField } from "@/integrations/mirra-api/types";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cmToInches, inchesToCm, lbToKg, type UnitSystem } from "@/lib/units";

/**
 * One measurement control: mono label, live value readout, slider + numeric
 * entry. Values are stored metric; imperial is a display conversion.
 * Estimated values are marked, never judged.
 */
export function MeasurementRow({
  field,
  units,
  onChange,
}: {
  field: MeasurementField;
  units: UnitSystem;
  onChange: (value: number) => void;
}) {
  const id = useId();
  const reduceMotion = useReducedMotion();
  const imperial = units === "imperial";
  const isWeight = field.unit === "kg";

  const displayValue = imperial
    ? isWeight
      ? Math.round(field.value * 2.20462)
      : cmToInches(field.value)
    : field.value;
  const displayUnit = imperial ? (isWeight ? "lb" : "in") : field.unit;
  const displayMin = imperial
    ? isWeight
      ? Math.round(field.min * 2.20462)
      : cmToInches(field.min)
    : field.min;
  const displayMax = imperial
    ? isWeight
      ? Math.round(field.max * 2.20462)
      : cmToInches(field.max)
    : field.max;
  const displayStep = imperial ? (isWeight ? 1 : 0.5) : field.step;
  const percent = ((displayValue - displayMin) / (displayMax - displayMin)) * 100;

  function toMetric(v: number): number {
    if (!imperial) return v;
    return isWeight ? lbToKg(v) : inchesToCm(v);
  }

  return (
    <motion.div
      className="py-5 sm:py-6"
      initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={
        reduceMotion ? { duration: 0.14 } : { type: "spring", stiffness: 330, damping: 32 }
      }
    >
      <div className="flex items-start justify-between gap-4">
        <label htmlFor={id} className="pt-1 text-sm font-semibold tracking-[-0.01em] text-ink">
          {field.label}
          {field.estimated && (
            <span className="ml-2 inline-flex rounded-full bg-mist px-2 py-0.5 text-[10px] font-medium tracking-normal text-muted normal-case">
              estimated
            </span>
          )}
        </label>
        <div className="flex items-center gap-1 rounded-xl border border-line bg-paper p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]">
          <button
            type="button"
            aria-label={`Decrease ${field.label}`}
            onClick={() => onChange(toMetric(Math.max(displayMin, displayValue - displayStep)))}
            className="pressable flex size-8 items-center justify-center rounded-[9px] text-lg leading-none text-muted hover:bg-mist hover:text-ink"
          >
            −
          </button>
          <input
            type="number"
            aria-label={`${field.label} in ${displayUnit}`}
            value={displayValue}
            min={displayMin}
            max={displayMax}
            step={displayStep}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (!Number.isNaN(v)) onChange(toMetric(v));
            }}
            className="w-12 appearance-none bg-transparent text-right text-[15px] font-semibold text-ink tabular-nums focus:outline-none"
          />
          <span className="w-6 text-xs font-medium text-muted">{displayUnit}</span>
          <button
            type="button"
            aria-label={`Increase ${field.label}`}
            onClick={() => onChange(toMetric(Math.min(displayMax, displayValue + displayStep)))}
            className="pressable flex size-8 items-center justify-center rounded-[9px] text-lg leading-none text-muted hover:bg-mist hover:text-ink"
          >
            +
          </button>
        </div>
      </div>
      <div className="relative mt-5 flex h-7 items-center">
        <span
          className="pointer-events-none absolute inset-x-0 h-0.75 rounded-full bg-line"
          aria-hidden
        />
        <span
          className="pointer-events-none absolute left-0 h-0.75 rounded-full bg-ink"
          style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
          aria-hidden
        />
        <input
          id={id}
          type="range"
          value={displayValue}
          min={displayMin}
          max={displayMax}
          step={displayStep}
          onChange={(e) => onChange(toMetric(Number(e.target.value)))}
          aria-valuetext={`${displayValue} ${displayUnit}`}
          className="range-thumb absolute inset-x-0 h-7 w-full cursor-pointer appearance-none bg-transparent"
        />
      </div>
      <div className="flex justify-between text-[10px] font-medium text-faint tabular-nums">
        <span>
          {displayMin} {displayUnit}
        </span>
        <span>
          {displayMax} {displayUnit}
        </span>
      </div>
    </motion.div>
  );
}
