import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { FabricPanel } from "@/components/ui/fabric-panel";
import { MirraMark } from "@/components/ui/logo";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import "./auth.css";

/**
 * Split-screen luxury auth composition matching the exact pixel mockup:
 * 6-card bento grid visual on the left, pure minimalist form on the right.
 */
export function AuthShell({
  children,
  topRightAction,
  customBackgroundSrc,
}: {
  children: ReactNode;
  topRightAction?: ReactNode;
  customBackgroundSrc?: string;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <main className="auth-shell safe-screen relative grid min-h-dvh grid-cols-1 overflow-x-clip bg-white lg:h-dvh lg:grid-cols-[1.08fr_0.92fr] lg:overflow-hidden">
      {/* Left Visual Aside */}
      <motion.aside
        className="auth-shell__visual hidden h-dvh p-3 lg:block"
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -16, scale: 0.99 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        transition={
          reduceMotion
            ? { duration: 0.16 }
            : { type: "spring", stiffness: 240, damping: 30, mass: 1 }
        }
      >
        <div className="auth-shell__visual-frame h-full overflow-hidden rounded-[26px] shadow-[0_20px_60px_-30px_rgba(0,0,0,0.18)]">
          <FabricPanel customBackgroundSrc={customBackgroundSrc} />
        </div>
      </motion.aside>

      {/* Right Content Section */}
      <section className="auth-shell__content relative flex min-h-dvh flex-col justify-center overflow-x-clip bg-white px-6 py-12 sm:px-10 lg:h-dvh lg:min-h-0 lg:overflow-y-auto lg:px-14">
        {topRightAction && (
          <div className="auth-shell__top-action absolute top-6 right-6 z-20">
            {topRightAction}
          </div>
        )}

        <div className="mx-auto flex w-full max-w-95 flex-col items-center">
          {/* Top Logo Emblem from logo_assets_mirra */}
          <Link
            to="/"
            aria-label="Mirra home"
            className="mb-7 inline-flex transition-opacity hover:opacity-75"
          >
            <MirraMark size={38} variant="dark" alt="Mirra" />
          </Link>

          {/* Form Content */}
          <div className="w-full">{children}</div>
        </div>
      </section>
    </main>
  );
}

export function AuthHeading({
  pill = "Create your unique design",
  title = "Sign up account",
  subtitle = "Enter your personal data to create your account",
}: {
  pill?: string;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="auth-heading mb-6 flex flex-col items-center text-center">
      {pill && (
        <span className="inline-flex items-center rounded-full border border-black/8 bg-neutral-50 px-3.5 py-1 text-[11px] font-medium tracking-wide text-neutral-600 shadow-[0_1px_1px_rgba(0,0,0,0.03)]">
          {pill}
        </span>
      )}
      <h1 className="mt-3.5 text-2xl font-bold tracking-tight text-neutral-900 sm:text-[26px]">
        {title}
      </h1>
      <p className="mt-1.5 text-xs text-neutral-500">
        {subtitle}
      </p>
    </div>
  );
}
