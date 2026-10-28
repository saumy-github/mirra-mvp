import { Link } from "react-router-dom";

const legalLink = "font-medium text-neutral-800 underline underline-offset-2 hover:text-black";

/** Explicit agreement before an account is created (doc 06). */
export function ConsentCheckbox({
  checked,
  onChange,
  invalid,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  invalid?: boolean;
}) {
  return (
    <label
      className={`flex w-full items-start gap-2.5 text-left text-xs leading-5 ${
        invalid ? "text-error" : "text-neutral-600"
      }`}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        aria-invalid={invalid || undefined}
        className="mt-0.5 size-4 shrink-0 accent-black"
      />
      <span>
        I agree to Mirra’s{" "}
        <Link to="/terms" target="_blank" className={legalLink}>
          Terms
        </Link>{" "}
        and{" "}
        <Link to="/privacy" target="_blank" className={legalLink}>
          Privacy Policy
        </Link>
        .
      </span>
    </label>
  );
}

/** Sign-in can also create a Google account, so the terms are stated there too. */
export function ConsentNote() {
  return (
    <p className="mt-4 text-center text-[11px] leading-5 text-neutral-500">
      By continuing you agree to Mirra’s{" "}
      <Link to="/terms" target="_blank" className={legalLink}>
        Terms
      </Link>{" "}
      and{" "}
      <Link to="/privacy" target="_blank" className={legalLink}>
        Privacy Policy
      </Link>
      .
    </p>
  );
}
