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
        <label
          htmlFor={id}
          className="pt-1 text-[13px] font-medium tracking-[-0.01em] text-graphite"
        >
          {field.label}
          {field.estimated && (
            <span className="ml-3 text-[10px] tracking-[0.14em] text-ash uppercase">Estimated</span>
          )}
        </label>
        <div className="flex items-center gap-1 rounded-panel-sm border border-hairline p-1">
          <button
            type="button"
            aria-label={`Decrease ${field.label}`}
            onClick={() => onChange(toMetric(Math.max(displayMin, displayValue - displayStep)))}
            className="flex size-8 items-center justify-center text-lg leading-none text-ash transition-colors hover:text-graphite"
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
            className="w-12 appearance-none bg-transparent text-right text-[15px] font-medium text-graphite tabular-nums focus:outline-none"
          />
          <span className="w-6 text-[11px] text-ash">{displayUnit}</span>
          <button
            type="button"
            aria-label={`Increase ${field.label}`}
            onClick={() => onChange(toMetric(Math.min(displayMax, displayValue + displayStep)))}
            className="flex size-8 items-center justify-center text-lg leading-none text-ash transition-colors hover:text-graphite"
          >
            +
          </button>
        </div>
      </div>
      <div className="relative mt-5 flex h-7 items-center">
        <span
          className="pointer-events-none absolute inset-x-0 h-px bg-hairline-strong"
          aria-hidden
        />
        <span
          className="pointer-events-none absolute left-0 h-px bg-graphite"
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
      <div className="flex justify-between text-[10px] text-ash tabular-nums">
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
