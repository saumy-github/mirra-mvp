import { useId } from "react";
import { motion, useMotionValue, useSpring } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { MirraMark } from "./logo";

/**
 * The quiet "silk" visual used on the left of split-screen compositions
 * (auth, QR pairing). Pure CSS/SVG — no photographic assets — layered warm
 * gradients under a thin 3×3 grid.
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
  const reduceMotion = useReducedMotion();
  const grainId = useId().replace(/:/g, "");
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const x = useSpring(rawX, { stiffness: 120, damping: 24, mass: 0.9 });
  const y = useSpring(rawY, { stiffness: 120, damping: 24, mass: 0.9 });

  return (
    <div
      className={`relative h-full min-h-120 overflow-hidden bg-[#ebe6dc] ${className}`}
      onPointerMove={(event) => {
        if (reduceMotion) return;
        const rect = event.currentTarget.getBoundingClientRect();
        rawX.set(((event.clientX - rect.left) / rect.width - 0.5) * 11);
        rawY.set(((event.clientY - rect.top) / rect.height - 0.5) * 9);
      }}
      onPointerLeave={() => {
        rawX.set(0);
        rawY.set(0);
      }}
    >
      {/* Silk folds — soft blurred forms */}
      <motion.div
        className="absolute -inset-5 will-change-transform"
        aria-hidden
        style={reduceMotion ? undefined : { x, y, scale: 1.025 }}
      >
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(90% 60% at 12% 15%, #fff 0%, transparent 56%)," +
              "radial-gradient(68% 56% at 82% 11%, #f7efe3 0%, transparent 62%)," +
              "radial-gradient(88% 72% at 74% 80%, #ded4c5 0%, transparent 60%)," +
              "radial-gradient(62% 48% at 28% 88%, #fffdf8 0%, transparent 62%)," +
              "linear-gradient(148deg, #f8f5ef 0%, #e8e0d2 49%, #f4efe6 100%)",
          }}
        />
        <div className="absolute top-10 -left-24 h-107.5 w-142.5 rotate-[-18deg] rounded-[50%] bg-white/65 blur-3xl" />
        <div className="absolute top-[30%] -right-35 h-97.5 w-135 rotate-24 rounded-[50%] bg-[#dbcfbc]/55 blur-3xl" />
        <div className="absolute -bottom-30 left-[20%] h-95 w-160 rotate-[8deg] rounded-[50%] bg-white/55 blur-3xl" />
        <div className="absolute top-[42%] left-[36%] h-57.5 w-87.5 rotate-[-30deg] rounded-[50%] bg-[#eee3d1]/70 blur-2xl" />

        <span className="absolute bottom-[16%] left-[10%] size-24 rounded-full bg-[radial-gradient(circle_at_34%_26%,#fff_0%,#f2eee6_42%,#cfc5b7_100%)] shadow-[0_20px_35px_-22px_rgba(74,62,50,0.7)]" />
        <span className="absolute bottom-[9%] left-[28%] size-14 rounded-full bg-[radial-gradient(circle_at_34%_26%,#fff_0%,#eee9df_45%,#cbbfae_100%)] shadow-[0_16px_30px_-20px_rgba(74,62,50,0.65)]" />
        <svg
          className="absolute top-[3%] right-[4%] h-[58%] w-[31%] text-[#a48b6c]/65"
          viewBox="0 0 180 480"
          fill="none"
        >
          <path
            d="M126 474C118 355 112 267 93 184C80 128 60 77 29 19"
            stroke="currentColor"
            strokeWidth="1.4"
          />
          <path
            d="M93 185C116 150 138 124 167 103M77 128C94 95 113 66 140 39M107 254C129 232 148 217 172 207"
            stroke="currentColor"
            strokeWidth="1"
          />
          {[
            [29, 19],
            [20, 27],
            [39, 31],
            [140, 39],
            [132, 50],
            [151, 52],
            [167, 103],
            [155, 111],
            [174, 117],
            [172, 207],
            [158, 215],
            [177, 221],
          ].map(([cx, cy], index) => (
            <circle key={index} cx={cx} cy={cy} r="4.5" fill="currentColor" opacity="0.7" />
          ))}
        </svg>

        {/* Grain */}
        <svg className="absolute inset-0 h-full w-full opacity-5 mix-blend-multiply">
          <filter id={grainId}>
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" />
          </filter>
          <rect width="100%" height="100%" filter={`url(#${grainId})`} />
        </svg>
        {/* Thin 3×3 grid */}
        <div className="absolute inset-0 grid grid-cols-3 grid-rows-3">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="border-[0.5px] border-white/72" />
          ))}
        </div>
      </motion.div>

      {children && (
        <div className="relative z-10 flex h-full items-center justify-center p-8">{children}</div>
      )}

      {footer && (
        <div className="absolute inset-x-0 bottom-0 z-10 bg-ink/85 py-1.5 text-center">
          <span className="font-mono text-[10px] tracking-[0.22em] text-canvas/80 uppercase">
            {footer}
          </span>
        </div>
      )}
    </div>
  );
}

/** Default center content for the auth screen: frosted mark + wordmark. */
export function FabricBrandBadge() {
  return (
    <div className="flex flex-col items-center text-center">
      <motion.div
        className="glass flex size-40 items-center justify-center rounded-[36px] text-white"
        initial={{ scale: 0.94, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 220, damping: 25, mass: 0.95 }}
      >
        <MirraMark size={74} strokeWidth={1.05} className="drop-shadow-sm" />
      </motion.div>
      <p className="mt-8 text-lg font-medium tracking-[0.58em] text-[#777064] uppercase">MIRRA</p>
      <p className="mt-2 text-sm font-medium text-[#8a8275]">A fitting room made for you</p>
      <div className="glass mt-6 flex items-center gap-2 rounded-full px-3.5 py-2 text-[11px] font-medium text-[#70695f]">
        <span className="size-1.5 rounded-full bg-ok" />
        Private, encrypted avatar creation
      </div>
    </div>
  );
}
