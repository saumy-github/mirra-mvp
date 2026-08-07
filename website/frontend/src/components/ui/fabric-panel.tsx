import { MirraMark } from "./logo";

/**
 * The quiet panel used on the left of split-screen compositions (auth, QR
 * pairing, avatar generation).
 *
 * It used to be a stack of blurred gradient blobs behind frosted glass. It's
 * now what a fitting-room wall actually looks like: a flat bone field ruled
 * into a grid of hairlines, with a single fold of light across it. The
 * structure *is* the decoration.
 */
export function FabricPanel({
  children,
  footer,
  className = "",
}: {
  children?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`relative flex h-full min-h-120 flex-col overflow-hidden bg-bone ${className}`}>
      {/* The rule grid: four columns, six rows, hairlines only. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 grid grid-cols-4 grid-rows-6"
      >
        {Array.from({ length: 24 }).map((_, index) => (
          <div key={index} className="border-t border-l border-hairline/70" />
        ))}
      </div>

      {/* One soft fold of light, top-left to bottom-right. Nothing else. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "linear-gradient(152deg, rgba(255,255,255,0.75) 0%, rgba(255,255,255,0) 42%, rgba(216,208,196,0.28) 100%)",
        }}
      />

      {children && (
        <div className="relative z-10 flex flex-1 items-center justify-center p-10">{children}</div>
      )}

      {footer && (
        <div className="relative z-10 border-t border-hairline px-8 py-4 text-center">
          <span className="eyebrow">{footer}</span>
        </div>
      )}
    </div>
  );
}

/** Default centre content for the auth screen: the mark, set on the grid. */
export function FabricBrandBadge() {
  return (
    <div className="flex flex-col items-center text-center">
      <MirraMark size={64} strokeWidth={0.9} className="text-graphite" />
      <p className="mt-10 text-[13px] tracking-[0.52em] text-graphite uppercase">Mirra</p>
      <span aria-hidden className="mt-8 h-px w-10 bg-hairline-strong" />
      <p className="mt-8 max-w-55 text-[12px] leading-relaxed text-slate">
        A fitting room made for you
      </p>
      <p className="eyebrow mt-6">Private, encrypted avatar creation</p>
    </div>
  );
}
