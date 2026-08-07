import { motion } from "motion/react";
import type { ReactNode } from "react";
import { FabricBrandBadge, FabricPanel } from "@/components/ui/fabric-panel";
import { MirraMark } from "@/components/ui/logo";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

/**
 * Split-screen auth: the ruled bone panel on the left, the form on the right.
 * Both halves are full-bleed regions divided by a single hairline — the form
 * is not a card floating on a background, it *is* the right-hand region.
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
    <main className="safe-screen relative grid min-h-dvh grid-cols-1 overflow-x-clip bg-vellum lg:h-dvh lg:grid-cols-[1.05fr_0.95fr] lg:overflow-hidden">
      <aside className="hidden h-dvh border-r border-hairline lg:block">
        <FabricPanel>
          <FabricBrandBadge />
        </FabricPanel>
      </aside>

      <section className="relative flex min-h-dvh flex-col overflow-x-clip lg:h-dvh lg:min-h-0 lg:overflow-y-auto">
        <header className="flex shrink-0 items-center justify-between gap-4 border-b border-hairline px-5 py-5 sm:px-8 lg:px-12">
          <div className="flex items-center gap-3">
            <MirraMark size={22} strokeWidth={1.15} className="text-graphite" />
            <span className="text-[11px] tracking-[0.34em] text-graphite uppercase">Mirra</span>
          </div>
          {topRightAction}
        </header>

        <motion.div
          className="mx-auto flex w-full max-w-125 flex-1 flex-col justify-center px-5 py-12 sm:px-8 lg:px-12"
          initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={
            reduceMotion ? { duration: 0.16 } : { duration: 0.45, ease: [0.22, 0.8, 0.24, 1] }
          }
        >
          {children}
        </motion.div>

        <p className="flex shrink-0 items-center justify-center gap-2.5 border-t border-hairline px-5 py-4 text-center text-[11px] text-ash">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            aria-hidden
          >
            <rect x="5" y="10" width="14" height="10" rx="2" />
            <path d="M8.5 10V7.5a3.5 3.5 0 0 1 7 0V10" />
          </svg>
          Private by design · Your photos are never shown to anyone else
        </p>
      </section>
    </main>
  );
}

/**
 * The heading block. The eyebrow replaces the old pill — a label, not a badge.
 */
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
    <div className="mb-10">
      <p className="eyebrow">{pill}</p>
      <h1 className="mt-5 text-[clamp(1.9rem,3.4vw,2.5rem)] leading-[1.06] font-medium tracking-[-0.03em] text-graphite">
        {title}
      </h1>
      <p className="mt-4 max-w-sm text-[14px] leading-relaxed text-slate">{subtitle}</p>
    </div>
  );
}
