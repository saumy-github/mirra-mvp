import type { TryOnState } from "../types";

type Tone = "available" | "working" | "unavailable";

const COPY: Record<TryOnState, { label: string; tone: Tone }> = {
  idle: { label: "Try-on ready when you are", tone: "working" },
  requesting: { label: "Try-on in progress", tone: "working" },
  processing: { label: "Try-on in progress", tone: "working" },
  restoring: { label: "Restoring your last look", tone: "working" },
  ready: { label: "Try-on available on your avatar", tone: "available" },
  cached: { label: "Try-on available on your avatar", tone: "available" },
  unsupported: { label: "Try-on not available for this piece", tone: "unavailable" },
  failed: { label: "Try-on didn't complete", tone: "unavailable" },
};

const DOT: Record<Tone, string> = {
  available: "bg-verdigris",
  working: "bg-hairline-strong",
  unavailable: "bg-ash",
};

/**
 * A single quiet line, not an alert bar: whether this piece can go on the
 * shopper's own avatar right now.
 */
export function FitAvailability({ tryOnState }: { tryOnState: TryOnState }) {
  const { label, tone } = COPY[tryOnState];

  return (
    <p
      aria-live="polite"
      className="flex items-center gap-2.5 text-[10px] tracking-[0.14em] text-slate uppercase"
    >
      <span aria-hidden className={`size-1.5 shrink-0 rounded-full ${DOT[tone]}`} />
      {label}
    </p>
  );
}
