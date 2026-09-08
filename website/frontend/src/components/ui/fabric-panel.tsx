import { useId } from "react";
import { motion, useMotionValue, useSpring } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

/**
 * The 6-card bento grid over a warm silk aesthetic on the visual side of Auth.
 * Uses the official Mirra logo assets from /brand/ (sourced from logo_assets_mirra).
 */
export function FabricPanel({
  className = "",
  customBackgroundSrc,
}: {
  children?: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
  customBackgroundSrc?: string;
}) {
  const reduceMotion = useReducedMotion();
  const grainId = useId().replace(/:/g, "");
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const x = useSpring(rawX, { stiffness: 100, damping: 26, mass: 0.9 });
  const y = useSpring(rawY, { stiffness: 100, damping: 26, mass: 0.9 });

  return (
    <div
      className={`relative h-full w-full overflow-hidden bg-[#ded8ce] ${className}`}
      onPointerMove={(event) => {
        if (reduceMotion) return;
        const rect = event.currentTarget.getBoundingClientRect();
        rawX.set(((event.clientX - rect.left) / rect.width - 0.5) * 12);
        rawY.set(((event.clientY - rect.top) / rect.height - 0.5) * 10);
      }}
      onPointerLeave={() => {
        rawX.set(0);
        rawY.set(0);
      }}
    >
      {/* Background Visual Layer: User Image or Procedural Silk & Mirra Brand Accents */}
      <motion.div
        className="absolute -inset-4 will-change-transform"
        aria-hidden
        style={reduceMotion ? undefined : { x, y, scale: 1.03 }}
      >
        {customBackgroundSrc ? (
          <img
            src={customBackgroundSrc}
            alt=""
            className="h-full w-full object-cover object-center"
          />
        ) : (
          <div className="relative h-full w-full bg-[#f2ece3]">
            {/* Luminous Satin & Caustics */}
            <div
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(100% 70% at 18% 18%, #ffffff 0%, transparent 60%)," +
                  "radial-gradient(70% 60% at 85% 15%, #f9f4ed 0%, transparent 65%)," +
                  "radial-gradient(90% 80% at 75% 82%, #d7cca8 0%, transparent 58%)," +
                  "radial-gradient(65% 50% at 25% 85%, #fdfbf7 0%, transparent 60%)," +
                  "linear-gradient(142deg, #fbf8f2 0%, #e6ddce 48%, #ede5d8 100%)",
              }}
            />

            {/* Blurred silk folds */}
            <div className="absolute -top-12 -left-20 h-120 w-160 rotate-[-16deg] rounded-[50%] bg-white/70 blur-3xl" />
            <div className="absolute top-[28%] -right-28 h-110 w-150 rotate-20 rounded-[50%] bg-[#d9cdb8]/60 blur-3xl" />
            <div className="absolute -bottom-24 left-[15%] h-110 w-170 rotate-6 rounded-[50%] bg-white/60 blur-3xl" />
            <div className="absolute top-[40%] left-[32%] h-70 w-100 rotate-[-25deg] rounded-[50%] bg-[#f1e8d9]/80 blur-2xl" />

            {/* Smooth polished pebbles */}
            <div className="absolute bottom-[18%] left-[8%] size-28 rounded-full bg-[radial-gradient(circle_at_32%_24%,#ffffff_0%,#f0ebe2_45%,#c8beae_100%)] shadow-[0_24px_45px_-20px_rgba(70,58,45,0.45)]" />
            <div className="absolute bottom-[10%] left-[26%] size-16 rounded-full bg-[radial-gradient(circle_at_35%_25%,#ffffff_0%,#eee7dc_45%,#c5b8a6_100%)] shadow-[0_18px_35px_-16px_rgba(70,58,45,0.4)]" />
            <div className="absolute bottom-[24%] right-[12%] size-32 rounded-full bg-[radial-gradient(circle_at_30%_25%,#ffffff_0%,#ede5d6_40%,#c2b5a1_100%)] shadow-[0_28px_50px_-22px_rgba(70,58,45,0.38)]" />

            {/* Right Side: Official Mirra Brand Logo Asset (Replaces the tree) */}
            <div className="pointer-events-none absolute top-[12%] right-[10%] select-none opacity-40">
              <img
                src="/brand/Mirra-logo-dark.png"
                alt=""
                className="size-36 object-contain drop-shadow-md"
              />
            </div>

            {/* Glass caustics bowl outline */}
            <div className="absolute top-[48%] -left-12 size-56 rounded-full border border-white/70 bg-linear-to-br from-white/40 via-white/10 to-transparent shadow-[inset_0_0_24px_rgba(255,255,255,0.6)] backdrop-blur-xs" />

            {/* Micro grain */}
            <svg className="absolute inset-0 h-full w-full opacity-4 mix-blend-multiply">
              <filter id={grainId}>
                <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" />
              </filter>
              <rect width="100%" height="100%" filter={`url(#${grainId})`} />
            </svg>
          </div>
        )}
      </motion.div>

      {/* 3x2 Bento Glass Grid Overlays */}
      <div className="relative z-10 grid h-full w-full grid-cols-3 grid-rows-2 gap-3 p-3">
        {/* Top Left */}
        <div className="rounded-[20px] border border-white/55 bg-white/10 backdrop-blur-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)] transition-all duration-300 hover:bg-white/15" />

        {/* Top Center */}
        <div className="rounded-[20px] border border-white/55 bg-white/10 backdrop-blur-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)] transition-all duration-300 hover:bg-white/15" />

        {/* Top Right */}
        <div className="rounded-[20px] border border-white/55 bg-white/10 backdrop-blur-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)] transition-all duration-300 hover:bg-white/15" />

        {/* Bottom Left */}
        <div className="rounded-[20px] border border-white/55 bg-white/10 backdrop-blur-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)] transition-all duration-300 hover:bg-white/15" />

        {/* Bottom Center - Hero Glass Emblem Card */}
        <div className="relative flex flex-col items-center justify-center overflow-hidden rounded-[20px] border border-white/70 bg-white/15 p-6 text-center shadow-[0_8px_32px_rgba(0,0,0,0.08),inset_0_1px_2px_rgba(255,255,255,0.8)] backdrop-blur-[2px]">
          {/* Official Mirra Logo Asset */}
          <div className="relative mb-4 flex size-20 items-center justify-center rounded-2xl border border-white/80 bg-linear-to-b from-white/70 via-white/30 to-white/10 p-2.5 shadow-[0_12px_28px_rgba(0,0,0,0.06),inset_0_1px_2px_rgba(255,255,255,0.9)] backdrop-blur-md">
            <img
              src="/brand/Mirra-logo-light.png"
              alt="Mirra"
              className="size-full object-contain drop-shadow-[0_2px_6px_rgba(255,255,255,0.7)]"
            />
          </div>

          <span className="font-sans text-sm font-semibold tracking-[0.42em] text-white uppercase drop-shadow-sm">
            M I R R A
          </span>
          <p className="mt-1 text-[11px] font-normal tracking-wide text-white/90 drop-shadow-xs">
            Design without limits.
          </p>
        </div>

        {/* Bottom Right */}
        <div className="rounded-[20px] border border-white/55 bg-white/10 backdrop-blur-[1px] shadow-[inset_0_1px_1px_rgba(255,255,255,0.6)] transition-all duration-300 hover:bg-white/15" />
      </div>
    </div>
  );
}

export function FabricBrandBadge() {
  return null;
}
