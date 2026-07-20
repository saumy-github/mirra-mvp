import { forwardRef, useId, useState, type InputHTMLAttributes } from "react";

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** Visually hide the label (still announced to screen readers). */
  hideLabel?: boolean;
  error?: string | null;
  hint?: string;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, hideLabel, error, hint, id, className = "", type, ...rest },
  ref,
) {
  const autoId = useId();
  const fieldId = id ?? autoId;
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;
  const [revealed, setRevealed] = useState(false);
  const isPassword = type === "password";

  return (
    <div className="w-full">
      <label
        htmlFor={fieldId}
        className={hideLabel ? "sr-only" : "mb-2 block text-[13px] font-semibold text-ink-soft"}
      >
        {label}
      </label>
      <div
        className={
          "group relative rounded-[14px] border bg-paper/90 shadow-[0_1px_0_rgba(255,255,255,0.9)_inset] " +
          "transition-[border-color,box-shadow,background-color] duration-200 focus-within:border-blue/65 " +
          "focus-within:bg-paper focus-within:shadow-[0_0_0_4px_rgba(0,113,227,0.1)] " +
          (error ? "border-error" : "border-line-strong")
        }
      >
        <input
          ref={ref}
          id={fieldId}
          type={isPassword && revealed ? "text" : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={
            "h-12.5 w-full rounded-[14px] border-0 bg-transparent px-4 text-base text-ink " +
            "placeholder:text-faint focus:outline-none " +
            (isPassword ? "pr-11 " : "") +
            className
          }
          {...rest}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? "Hide password" : "Show password"}
            className="pressable absolute top-1/2 right-2 flex size-9 -translate-y-1/2 items-center justify-center rounded-full text-muted hover:bg-mist hover:text-ink"
            tabIndex={-1}
          >
            <EyeIcon off={!revealed} />
          </button>
        )}
      </div>
      {hint && !error && (
        <p id={`${fieldId}-hint`} className="mt-1.5 text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${fieldId}-error`} role="alert" className="mt-1.5 text-xs text-error">
          {error}
        </p>
      )}
    </div>
  );
});

function EyeIcon({ off }: { off: boolean }) {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      aria-hidden
    >
      <path d="M2 12s3.5-6.5 10-6.5S22 12 22 12s-3.5 6.5-10 6.5S2 12 2 12Z" />
      <circle cx="12" cy="12" r="2.6" />
      {off && <path d="M4 20 20 4" />}
    </svg>
  );
}
