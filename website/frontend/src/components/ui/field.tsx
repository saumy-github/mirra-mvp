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
      <label htmlFor={fieldId} className={hideLabel ? "sr-only" : "eyebrow mb-2.5 block"}>
        {label}
      </label>
      {/* A ruled line, not a box: the field is the baseline it sits on. */}
      <div
        className={
          "group relative border-b transition-colors duration-200 focus-within:border-graphite " +
          (error ? "border-error" : "border-hairline-strong")
        }
      >
        <input
          ref={ref}
          id={fieldId}
          type={isPassword && revealed ? "text" : type}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={
            "h-12 w-full border-0 bg-transparent px-0 text-[15px] text-graphite " +
            "placeholder:text-ash focus:outline-none " +
            (isPassword ? "pr-10 " : "") +
            className
          }
          {...rest}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((v) => !v)}
            aria-label={revealed ? "Hide password" : "Show password"}
            className="absolute top-1/2 right-0 flex size-9 -translate-y-1/2 items-center justify-center text-ash transition-colors hover:text-graphite"
            tabIndex={-1}
          >
            <EyeIcon off={!revealed} />
          </button>
        )}
      </div>
      {hint && !error && (
        <p id={`${fieldId}-hint`} className="mt-2 text-[11px] text-ash">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${fieldId}-error`} role="alert" className="mt-2 text-[11px] text-error">
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
