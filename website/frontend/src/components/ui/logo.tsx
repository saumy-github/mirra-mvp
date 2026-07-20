/** Mirra mark — a quiet tulip/M glyph, stroke only. */
export function MirraMark({
  className = "",
  size = 30,
  strokeWidth = 1.4,
}: {
  className?: string;
  size?: number;
  strokeWidth?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden
      className={className}
    >
      <path
        d="M16 5.5 25.5 10.5 C26.3 17.5 22.8 24.2 16 27 C9.2 24.2 5.7 17.5 6.5 10.5 Z"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
      />
      <path
        d="M11.5 9 16 16.5 20.5 9"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function MirraWordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-mono text-sm tracking-[0.42em] uppercase ${className}`}>MIRRA</span>
  );
}
