import { useEffect, useRef, useState } from "react";
import { buttonClass } from "./styles";

/**
 * A read-only URL with a copy control — the merchant flow hands out a
 * company URL and a per-garment URL, so copying them correctly is a real task
 * rather than decoration.
 *
 * Feedback is a word ("Copied"), not a colour change, and it is announced to
 * assistive tech. Failure is reported rather than silently looking successful.
 */
export function CopyField({ label, value }: { label: string; value: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setState("copied");
    } catch {
      // Clipboard is unavailable over plain http or without permission —
      // say so instead of pretending it worked. The value stays selectable.
      setState("failed");
    }
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setState("idle"), 2500);
  };

  return (
    <div>
      <div className="mb-1.5 text-xs font-medium text-ink">{label}</div>
      <div className="flex items-center gap-2">
        <code className="min-w-0 flex-1 truncate rounded-lg border border-line bg-stone-50 px-2.5 py-1.5 text-xs text-stone-700">
          {value}
        </code>
        <button type="button" onClick={copy} className={buttonClass("secondary", "sm")}>
          Copy
        </button>
      </div>
      <p aria-live="polite" className="mt-1 min-h-4 text-xs text-muted">
        {state === "copied" && "Copied to clipboard"}
        {state === "failed" && "Couldn't copy — select the text and copy manually"}
      </p>
    </div>
  );
}
