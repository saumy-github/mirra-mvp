export function Spinner({ className = "size-5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2.5" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function OrDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="flex items-center gap-4 text-xs text-muted" role="separator">
      <span className="h-px flex-1 bg-line" />
      {label}
      <span className="h-px flex-1 bg-line" />
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-mist ${className}`} aria-hidden />;
}

/** The small pulsing status dot from the QR reference screen. */
export function PulseDot({ active = true, label }: { active?: boolean; label?: string }) {
  return (
    <span className="relative inline-flex size-4 items-center justify-center" aria-hidden={!label}>
      {active && (
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-silver opacity-60 motion-reduce:hidden" />
      )}
      <span className="relative inline-flex size-2.5 rounded-full border-2 border-silver bg-ink-soft" />
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}

/** Honest badge shown wherever demo engines stand in for real ones. */
export function DemoModeNotice({ subject }: { subject: string }) {
  return (
    <p className="mono-tag rounded-md border border-line bg-mist/60 px-2.5 py-1.5 text-[11px] leading-relaxed tracking-normal! normal-case!">
      Demo mode — {subject} is simulated for development. No real body analysis or cloth physics
      runs here.
    </p>
  );
}
