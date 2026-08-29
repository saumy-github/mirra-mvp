import { useEffect, useId, useRef, useState } from "react";
import { motion } from "motion/react";
import type { MeasurementField } from "@/integrations/mirra-api/types";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { cmToInches, inchesToCm, lbToKg, type UnitSystem } from "@/lib/units";

type FieldFeedback = {
  tone: "error" | "status";
  message: string;
};

/**
 * One measurement control: mono label, live value readout, slider + numeric
 * entry. Values are stored metric; imperial is a display conversion.
 * Estimated values are marked, never judged.
 */
export function MeasurementRow({
  field,
  units,
  onChange,
  onValidityChange,
  showBounds = true,
}: {
  field: MeasurementField;
  units: UnitSystem;
  onChange: (value: number) => void;
  onValidityChange?: (valid: boolean) => void;
  showBounds?: boolean;
}) {
  const id = useId();
  const labelId = `${id}-label`;
  const valueLabelId = `${id}-value-label`;
  const hintId = `${id}-hint`;
  const feedbackId = `${id}-feedback`;
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
  const rangeValue = Number.isFinite(displayValue)
    ? Math.min(displayMax, Math.max(displayMin, displayValue))
    : displayMin;
  const percent = ((rangeValue - displayMin) / (displayMax - displayMin)) * 100;
  const editing = useRef(false);
  const previousUnits = useRef(units);
  const [inputValue, setInputValue] = useState(() => formatDisplayValue(displayValue));
  const [feedback, setFeedback] = useState<FieldFeedback | null>(() => {
    const message = validationMessage(displayValue, displayMin, displayMax, displayUnit);
    return message ? { tone: "error", message } : null;
  });

  useEffect(() => {
    const unitsChanged = previousUnits.current !== units;
    if (!editing.current || unitsChanged) setInputValue(formatDisplayValue(displayValue));
    if (unitsChanged) setFeedback(null);
    previousUnits.current = units;
  }, [displayValue, units]);

  function toMetric(v: number): number {
    if (!imperial) return v;
    return isWeight ? lbToKg(v) : inchesToCm(v);
  }

  function updateMetricValue(value: number) {
    const metricValue = Math.min(field.max, Math.max(field.min, toMetric(value)));
    onChange(metricValue);
  }

  function handleInputValue(rawValue: string) {
    setInputValue(rawValue);
    const numericValue = rawValue.trim() === "" ? Number.NaN : Number(rawValue);
    const message = validationMessage(numericValue, displayMin, displayMax, displayUnit);

    if (message) {
      setFeedback({ tone: "error", message });
      onValidityChange?.(false);
      return;
    }

    setFeedback(null);
    onValidityChange?.(true);
    updateMetricValue(numericValue);
  }

  function commitDisplayValue(value: number) {
    if (!Number.isFinite(value)) {
      const message = `Enter a number between ${formatDisplayValue(displayMin)} and ${formatDisplayValue(
        displayMax,
      )} ${displayUnit}.`;
      setFeedback({ tone: "error", message });
      onValidityChange?.(false);
      return;
    }

    const clampedValue = Math.min(displayMax, Math.max(displayMin, value));
    const normalizedValue = Number(clampedValue.toFixed(1));
    setInputValue(formatDisplayValue(normalizedValue));
    updateMetricValue(normalizedValue);
    onValidityChange?.(true);

    if (clampedValue !== value) {
      setFeedback({
        tone: "status",
        message: `Adjusted to ${formatDisplayValue(normalizedValue)} ${displayUnit}, the nearest supported value.`,
      });
    } else {
      setFeedback(null);
    }
  }

  const describedBy = `${hintId}${feedback ? ` ${feedbackId}` : ""}`;
  const invalid = feedback?.tone === "error";

  return (
    <motion.fieldset
      className={`min-w-0 border-0 p-0 ${showBounds ? "py-4 sm:py-4.5" : ""}`}
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 330, damping: 32 }}
    >
      <legend
        id={labelId}
        className={
          showBounds
            ? "text-sm font-medium tracking-[-0.01em] text-ink"
            : "text-[14px] font-medium tracking-[-0.015em] text-[#20211f]"
        }
      >
        {field.label}
        {field.estimated && (
          <span
            className={
              showBounds
                ? "ml-2 inline-flex rounded-full bg-mist px-2 py-0.5 text-[10px] font-medium tracking-normal text-muted normal-case"
                : "ml-2 inline-flex bg-[#eeece7] px-1.5 py-0.5 text-[9px] font-medium tracking-[0.015em] text-[#777872]"
            }
          >
            estimated
          </span>
        )}
      </legend>

      <div className="mt-2.5 flex justify-end">
        <div
          role="group"
          aria-label={`Set ${field.label}`}
          className={
            showBounds
              ? "flex items-center gap-1 rounded-xl border border-line bg-surface p-1 shadow-[0_1px_0_rgba(255,255,255,0.8)_inset]"
              : "flex items-center gap-1 self-end rounded-xl border border-[#d6d3cd] bg-[#faf9f6] p-1 sm:self-auto"
          }
        >
          <button
            type="button"
            aria-label={`Decrease ${field.label}`}
            disabled={rangeValue <= displayMin}
            onClick={() => commitDisplayValue(Math.max(displayMin, rangeValue - displayStep))}
            className={
              showBounds
                ? "pressable flex size-11 items-center justify-center rounded-[9px] text-lg leading-none text-muted hover:bg-mist hover:text-ink focus-visible:ring-2 focus-visible:ring-ink/30 disabled:opacity-30 sm:size-9"
                : "pressable flex size-11 items-center justify-center rounded-[9px] text-lg leading-none text-[#777872] hover:bg-[#e8e5df] hover:text-[#20211f] focus-visible:ring-2 focus-visible:ring-[#20211f]/30 disabled:opacity-30 sm:size-9"
            }
          >
            −
          </button>
          <span id={valueLabelId} className="sr-only">
            Value
          </span>
          <input
            type="number"
            inputMode="decimal"
            value={inputValue}
            min={displayMin}
            max={displayMax}
            step={displayStep}
            required
            aria-labelledby={`${labelId} ${valueLabelId}`}
            aria-describedby={describedBy}
            aria-invalid={invalid || undefined}
            onFocus={() => {
              editing.current = true;
            }}
            onChange={(event) => handleInputValue(event.currentTarget.value)}
            onBlur={() => {
              editing.current = false;
              const numericValue = inputValue.trim() === "" ? Number.NaN : Number(inputValue);
              commitDisplayValue(numericValue);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                event.currentTarget.blur();
              }
              if (event.key === "Escape") {
                setInputValue(formatDisplayValue(displayValue));
                setFeedback(null);
                onValidityChange?.(true);
                event.currentTarget.blur();
              }
            }}
            className={
              showBounds
                ? "w-14 appearance-none rounded-md bg-transparent px-1 text-right text-[15px] font-medium text-ink tabular-nums focus:outline-none focus-visible:ring-2 focus-visible:ring-ink/30"
                : "w-16 appearance-none rounded-md bg-transparent px-1 text-right text-[14px] font-medium tracking-[-0.01em] text-[#20211f] tabular-nums focus:outline-none focus-visible:ring-2 focus-visible:ring-[#20211f]/30"
            }
          />
          <span
            className={
              showBounds
                ? "w-6 text-xs font-medium text-muted"
                : "w-8 px-1 text-[10px] font-medium text-[#777872]"
            }
          >
            {displayUnit}
          </span>
          <button
            type="button"
            aria-label={`Increase ${field.label}`}
            disabled={rangeValue >= displayMax}
            onClick={() => commitDisplayValue(Math.min(displayMax, rangeValue + displayStep))}
            className={
              showBounds
                ? "pressable flex size-11 items-center justify-center rounded-[9px] text-lg leading-none text-muted hover:bg-mist hover:text-ink focus-visible:ring-2 focus-visible:ring-ink/30 disabled:opacity-30 sm:size-9"
                : "pressable flex size-11 items-center justify-center rounded-[9px] text-lg leading-none text-[#777872] hover:bg-[#e8e5df] hover:text-[#20211f] focus-visible:ring-2 focus-visible:ring-[#20211f]/30 disabled:opacity-30 sm:size-9"
            }
          >
            +
          </button>
        </div>
      </div>
      <div
        className={
          showBounds
            ? "relative mt-3.5 flex h-11 items-center"
            : "relative mt-3 flex h-11 items-center"
        }
      >
        <span
          className={
            showBounds
              ? "pointer-events-none absolute inset-x-0 h-0.75 rounded-full bg-line"
              : "pointer-events-none absolute inset-x-0 h-px rounded-full bg-[#cdcac4]"
          }
          aria-hidden
        />
        <span
          className={
            showBounds
              ? "pointer-events-none absolute left-0 h-0.75 rounded-full bg-ink"
              : "pointer-events-none absolute left-0 h-0.5 rounded-full bg-[#20211f]"
          }
          style={{ width: `${Math.max(0, Math.min(100, percent))}%` }}
          aria-hidden
        />
        <input
          id={id}
          type="range"
          value={rangeValue}
          min={displayMin}
          max={displayMax}
          step={displayStep}
          aria-labelledby={labelId}
          aria-describedby={describedBy}
          aria-invalid={invalid || undefined}
          aria-valuetext={`${rangeValue} ${displayUnit}`}
          onChange={(event) => {
            const value = Number(event.currentTarget.value);
            setInputValue(formatDisplayValue(value));
            setFeedback(null);
            onValidityChange?.(true);
            updateMetricValue(value);
          }}
          className="range-thumb absolute inset-x-0 h-11 w-full cursor-pointer appearance-none rounded-full bg-transparent focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#20211f]/45"
        />
      </div>
      {showBounds && (
        <div className="flex justify-between text-[10px] font-medium text-faint tabular-nums">
          <span>
            {displayMin} {displayUnit}
          </span>
          <span>
            {displayMax} {displayUnit}
          </span>
        </div>
      )}

      <p id={hintId} className="mt-1.5 text-[11px] leading-4 text-[#777872]">
        {showBounds
          ? "Drag the slider or enter a value."
          : `Accepted range: ${formatDisplayValue(displayMin)}–${formatDisplayValue(
              displayMax,
            )} ${displayUnit}.`}
      </p>
      {feedback && (
        <p
          id={feedbackId}
          role={feedback.tone === "error" ? "alert" : "status"}
          className={`mt-1 text-[11px] leading-4 ${
            feedback.tone === "error" ? "text-error" : "text-[#4f6c57]"
          }`}
        >
          {feedback.message}
        </p>
      )}
    </motion.fieldset>
  );
}

function formatDisplayValue(value: number): string {
  if (!Number.isFinite(value)) return "";
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(1)));
}

function validationMessage(value: number, min: number, max: number, unit: string): string | null {
  if (!Number.isFinite(value)) {
    return `Enter a number between ${formatDisplayValue(min)} and ${formatDisplayValue(max)} ${unit}.`;
  }
  if (value < min || value > max) {
    return `Use a value from ${formatDisplayValue(min)} to ${formatDisplayValue(max)} ${unit}.`;
  }
  return null;
}
