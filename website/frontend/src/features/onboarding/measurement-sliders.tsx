import { RotateCcw } from "lucide-react";
import { useId } from "react";
import {
  reviewChanged,
  reviewDisplay,
  reviewUnit,
  reviewValue,
  toReviewUnits,
} from "./measurement-review";
import type { MeasurementReviewControls } from "./use-measurement-review";
import "./measurement-sliders.css";

export function MeasurementSliders({
  review,
  disabled = false,
}: {
  review: MeasurementReviewControls;
  disabled?: boolean;
}) {
  const id = useId();
  return (
    <div className="measurement-adjustments">
      {review.fields.map((field) => {
        const initial = review.baseline[field.key];
        const metric = review.edits[field.key] ? review.edits[field.key]!.metric : initial;
        const unit = reviewUnit(field.key, review.units);
        const changed = reviewChanged(review.baseline, review.edits, field.key);
        const input = `${id}-${field.key}`;
        const slider = `${input}-slider`;
        const note = `${input}-note`;
        const bounded = Math.max(field.min, Math.min(field.max, metric ?? field.min));
        return (
          <div className="measurement-adjustment" key={field.key} data-adjusted={changed}>
            <div className="measurement-adjustment-heading">
              <label htmlFor={input}>
                {field.label}
                {initial == null && <small>Optional</small>}
              </label>
              <span className="measurement-adjustment-value">
                <input
                  id={input}
                  aria-label={`${field.label} ${unit}`}
                  aria-describedby={changed || metric == null ? note : undefined}
                  type="number"
                  inputMode="decimal"
                  step="any"
                  value={reviewDisplay(review.baseline, review.edits, field.key, review.units)}
                  onChange={(event) => review.setInput(field.key, event.target.value)}
                  placeholder="—"
                  disabled={disabled}
                />
                <span aria-hidden="true">{unit}</span>
              </span>
            </div>
            <div className="measurement-adjustment-track">
              {metric == null ? (
                <p id={note}>Enter a value to fine-tune it.</p>
              ) : (
                <input
                  id={slider}
                  type="range"
                  aria-label={`Adjust ${field.label.toLowerCase()}`}
                  aria-valuetext={`${reviewValue(metric, field.key, review.units)} ${unit}`}
                  min={toReviewUnits(field.min, field.key, review.units)}
                  max={toReviewUnits(field.max, field.key, review.units)}
                  step={toReviewUnits(0.1, field.key, review.units)}
                  value={toReviewUnits(
                    Number.isFinite(bounded) ? bounded : field.min,
                    field.key,
                    review.units,
                  )}
                  onChange={(event) => review.setSlider(field.key, Number(event.target.value))}
                  disabled={disabled}
                />
              )}
              <button
                type="button"
                className="measurement-reset"
                data-hidden={!changed}
                aria-hidden={!changed}
                tabIndex={changed ? 0 : -1}
                aria-label={`Reset ${field.label.toLowerCase()} to starting value`}
                title={`Reset ${field.label.toLowerCase()}`}
                onClick={() => review.resetField(field.key)}
                disabled={disabled || !changed}
              >
                <RotateCcw size={14} strokeWidth={1.5} />
              </button>
            </div>
            {changed && metric != null && (
              <p className="measurement-original" id={note}>
                {initial == null
                  ? "Added by you"
                  : `Starting value ${reviewValue(initial, field.key, review.units)} ${unit}`}
                <span>Adjusted</span>
              </p>
            )}
          </div>
        );
      })}
      {review.changedCount > 0 && (
        <div className="measurement-adjustments-footer">
          <span>
            {review.changedCount} {review.changedCount === 1 ? "adjustment" : "adjustments"}
          </span>
          <button type="button" onClick={review.resetAll} disabled={disabled}>
            Reset all
          </button>
        </div>
      )}
    </div>
  );
}
