import { useEffect } from "react";
import { motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

/**
 * Quiet success state once the backend confirms the avatar is ready:
 * a reflective ripple around a drawn check-mark, "Profile synchronized",
 * then an automatic (but interruptible) continue.
 */
export function SynchronizedState({ onContinue }: { onContinue: () => void }) {
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const t = setTimeout(onContinue, reduceMotion ? 1200 : 2600);
    return () => clearTimeout(t);
  }, [onContinue, reduceMotion]);

  return (
    <motion.section
      initial={
        reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.92, y: 14, filter: "blur(10px)" }
      }
      animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
      transition={reduceMotion ? { duration: 0.18 } : MATERIAL_SPRING}
      className="flex w-full max-w-md flex-col items-center text-center"
      role="status"
      aria-live="assertive"
    >
      <div className="relative flex size-36 items-center justify-center">
        {!reduceMotion && (
          <>
            <motion.span
              className="absolute inset-0 rounded-[2.8rem] border border-white bg-white/32 shadow-[0_26px_70px_-45px_rgba(33,31,28,.65)] backdrop-blur-2xl"
              initial={{ scale: 0.68, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={MATERIAL_SPRING}
            />
            <motion.span
              className="absolute inset-3 rounded-[2.3rem] border border-ok/25"
              initial={{ scale: 0.72, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ ...MATERIAL_SPRING, delay: 0.06 }}
            />
          </>
        )}
        <motion.span
          className="absolute inset-7 rounded-full border border-ok/30 bg-ok/8"
          initial={reduceMotion ? undefined : { scale: 0.65, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={reduceMotion ? { duration: 0.16 } : { ...MATERIAL_SPRING, delay: 0.11 }}
        />
        <svg viewBox="0 0 48 48" className="relative size-14 text-ok" fill="none" aria-hidden>
          <motion.path
            d="M14 25.5 21 32 34 17"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            initial={reduceMotion ? undefined : { pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={reduceMotion ? { duration: 0.16 } : { ...MATERIAL_SPRING, delay: 0.16 }}
          />
        </svg>
      </div>

      <p className="mono-tag mt-7 text-[10px]! tracking-[0.28em]! text-ok">PROFILE SYNCHRONIZED</p>
      <h1 className="mt-3 text-[2rem] leading-[1.05] font-semibold tracking-[-0.04em] text-ink">
        Your avatar is ready
      </h1>
      <p className="mt-3 max-w-xs text-sm leading-relaxed text-muted">
        Next, you can review every measurement before entering the fitting room.
      </p>

      <div className="mt-7 flex items-center gap-2 rounded-full border border-line/75 bg-white/55 px-4 py-2 text-[11px] text-ink-soft backdrop-blur-xl">
        <motion.span
          className="size-1.5 rounded-full bg-ok"
          animate={reduceMotion ? undefined : { opacity: [0.45, 1, 0.45] }}
          transition={
            reduceMotion ? undefined : { duration: 1.4, repeat: Infinity, ease: "easeInOut" }
          }
          aria-hidden
        />
        Taking you to measurement review…
      </div>

      <motion.button
        type="button"
        onClick={onContinue}
        whileTap={reduceMotion ? undefined : { scale: 0.98 }}
        transition={MATERIAL_SPRING}
        className="mt-7 min-h-11 rounded-full bg-ink px-7 py-2.5 text-sm font-medium text-canvas shadow-sm hover:bg-black"
      >
        Continue now
      </motion.button>
    </motion.section>
  );
}
