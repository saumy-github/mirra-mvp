import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { FabricBrandBadge, FabricPanel } from "@/components/ui/fabric-panel";
import { MirraMark } from "@/components/ui/logo";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import "./auth.css";

/**
 * Split-screen auth composition: quiet fabric visual on the left,
 * focused form on the right.
 */
export function AuthShell({
  children,
  topRightAction,
}: {
  children: ReactNode;
  topRightAction?: ReactNode;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <main className="auth-shell safe-screen relative grid min-h-dvh grid-cols-1 overflow-x-clip bg-canvas lg:h-dvh lg:grid-cols-[1.08fr_0.92fr] lg:overflow-hidden">
      <motion.aside
        className="auth-shell__visual hidden h-dvh p-3 lg:block"
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -18, scale: 0.99 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        transition={
          reduceMotion
            ? { duration: 0.16 }
            : { type: "spring", stiffness: 240, damping: 30, mass: 1 }
        }
      >
        <div className="auth-shell__visual-frame h-full overflow-hidden rounded-[28px] shadow-[0_28px_80px_-44px_rgba(62,52,43,0.42)]">
          <FabricPanel>
            <FabricBrandBadge />
          </FabricPanel>
        </div>
      </motion.aside>

      <section className="auth-shell__content relative min-h-dvh overflow-x-clip lg:h-dvh lg:min-h-0 lg:overflow-y-auto">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 h-72 bg-[radial-gradient(circle_at_50%_-20%,rgba(255,255,255,0.95),transparent_68%)] lg:hidden"
        />

        <div className="auth-shell__content-inner relative mx-auto flex min-h-dvh w-full max-w-170 flex-col px-5 pt-24 pb-5 sm:px-8 lg:min-h-full lg:max-w-none lg:px-12 lg:pt-24 lg:pb-6">
          <div className="auth-shell__brand absolute inset-x-0 top-7 flex items-center justify-center lg:top-9">
            <Link to="/" aria-label="Mirra home" className="inline-flex transition-opacity hover:opacity-80">
              <MirraMark size={38} alt="Mirra" />
            </Link>
          </div>

          {topRightAction && (
            <div className="auth-shell__top-action absolute top-5.5 right-4 z-20 sm:right-6 lg:top-8 lg:right-8">
              {topRightAction}
            </div>
          )}

          <motion.div
            className="auth-shell__panel my-auto w-full max-w-107.5 self-center rounded-[26px] border border-white/85 bg-[rgba(248,248,250,0.88)] px-6 py-7 shadow-[0_1px_0_rgba(255,255,255,0.92)_inset,0_22px_64px_-30px_rgba(0,0,0,0.32)] backdrop-blur-[34px] sm:px-9 sm:py-9 lg:rounded-none lg:border-0 lg:bg-transparent lg:px-0 lg:py-0 lg:shadow-none lg:backdrop-blur-none"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 18, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={
              reduceMotion
                ? { duration: 0.16 }
                : {
                    type: "spring",
                    stiffness: 300,
                    damping: 32,
                    mass: 0.85,
                    delay: 0.04,
                  }
            }
          >
            {children}
          </motion.div>

          <p className="auth-shell__privacy mt-6 flex shrink-0 items-center justify-center gap-2 text-center text-[11px] text-faint">
            <svg
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.7"
              aria-hidden
            >
              <rect x="5" y="10" width="14" height="10" rx="3" />
              <path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10" />
            </svg>
            Private by design · Your photos are never shown to anyone else
          </p>
        </div>
      </section>
    </main>
  );
}

export function AuthHeading({
  pill,
  title,
  subtitle,
}: {
  pill: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="auth-heading mb-6 text-center">
      <span className="auth-heading__pill inline-flex min-h-7 items-center rounded-full border border-line bg-paper/80 px-3.5 py-1 text-xs font-medium text-ink-soft shadow-[0_1px_0_rgba(255,255,255,0.9)_inset]">
        {pill}
      </span>
      <h1 className="auth-heading__title mt-4 text-[clamp(1.8rem,4vw,2.35rem)] leading-[1.08] font-semibold tracking-[-0.035em] text-ink">
        {title}
      </h1>
      <p className="auth-heading__subtitle mx-auto mt-2 max-w-sm text-sm leading-relaxed text-muted">
        {subtitle}
      </p>
    </div>
  );
}
