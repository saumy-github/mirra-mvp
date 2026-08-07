export function Spinner({ className = "size-5" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.18" strokeWidth="1.5" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function OrDivider({ label = "or" }: { label?: string }) {
  return (
    <div className="eyebrow flex items-center gap-4" role="separator">
      <span className="h-px flex-1 bg-hairline" />
      {label}
      <span className="h-px flex-1 bg-hairline" />
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-mist ${className}`} aria-hidden />;
}

/** The small pulsing status dot from the QR reference screen. */
export function PulseDot({ active = true, label }: { active?: boolean; label?: string }) {
  return (
    <span className="relative inline-flex size-3 items-center justify-center" aria-hidden={!label}>
      {active && (
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-hairline-strong opacity-70 motion-reduce:hidden" />
      )}
      <span className="relative inline-flex size-1.5 rounded-full bg-graphite" />
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}

/** Honest note shown wherever demo engines stand in for real ones. */
export function DemoModeNotice({ subject }: { subject: string }) {
  return (
    <p className="border-t border-hairline pt-3 text-[11px] leading-relaxed text-ash">
      Demo mode — {subject} is simulated for development. No real body analysis or cloth physics
      runs here.
    </p>
  );
}
