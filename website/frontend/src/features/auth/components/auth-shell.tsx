import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import "./auth.css";

/**
 * Full-screen luxury auth composition:
 * - Desktop (lg+): Full-length screen split (52/48) with high-res visual on left and minimalist form on right.
 * - Tablet/Mobile: Responsive full-height layout with visual header banner and mobile-optimized touch controls.
 * - Official Mirra brand logos in both visual banner and form header.
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
  const visualSrc = customBackgroundSrc || "/brand/Neon%20Heart%20TV%20at%20Sunset.png";

  return (
    <main className="auth-shell safe-screen relative min-h-dvh w-full bg-white lg:h-dvh lg:overflow-hidden grid grid-cols-1 lg:grid-cols-[1.08fr_0.92fr]">
      {/* Left Visual Section (Full-length screen on desktop) */}
      <motion.aside
        className="auth-shell__visual hidden h-full p-3 sm:p-4 lg:p-4 xl:p-5 lg:block select-none"
        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, x: -16, scale: 0.99 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        transition={
          reduceMotion
            ? { duration: 0.16 }
            : { type: "spring", stiffness: 240, damping: 30, mass: 1 }
        }
      >
        <div className="relative h-full w-full overflow-hidden rounded-3xl lg:rounded-4xl shadow-[0_20px_50px_-20px_rgba(0,0,0,0.14)] bg-neutral-900">
          <img
            src={visualSrc}
            alt="Mirra visual"
            className="absolute inset-0 h-full w-full object-cover object-center"
          />

          {/* Top-Left Mirra Logo overlay */}
          <Link
            to="/"
            aria-label="Mirra home"
            className="absolute top-6 left-6 sm:top-8 sm:left-8 z-10 transition-opacity hover:opacity-80"
          >
            <img
              src="/brand/mirra-logo-dark-long.png"
              alt="Mirra"
              className="h-7 w-auto object-contain"
            />
          </Link>
        </div>
      </motion.aside>

      {/* Right Content Section (Scrollable on small viewports, centered in 100dvh on desktop) */}
      <section className="auth-shell__content relative flex min-h-dvh flex-col justify-center overflow-x-clip px-5 py-8 sm:px-10 md:px-14 lg:h-dvh lg:min-h-0 lg:overflow-y-auto lg:px-12 xl:px-16 bg-white">
        {topRightAction && (
          <div className="auth-shell__top-action absolute top-6 right-6 z-20">
            {topRightAction}
          </div>
        )}

        {/* Mobile/Tablet Visual Header Banner (< lg) */}
        <div className="block lg:hidden w-full max-w-95 mx-auto mb-6">
          <div className="relative h-44 sm:h-52 w-full overflow-hidden rounded-2xl shadow-sm bg-neutral-900">
            <img
              src={visualSrc}
              alt="Mirra visual"
              className="absolute inset-0 h-full w-full object-cover object-center"
            />
            <Link
              to="/"
              aria-label="Mirra home"
              className="absolute top-4 left-4 z-10 transition-opacity hover:opacity-80"
            >
              <img
                src="/brand/mirra-logo-dark-long.png"
                alt="Mirra"
                className="h-6 w-auto object-contain"
              />
            </Link>
          </div>
        </div>

        <div className="mx-auto flex w-full max-w-90 sm:max-w-95 flex-col items-center my-auto">
          {/* Top Center Logo Emblem */}
          <Link
            to="/"
            aria-label="Mirra home"
            className="mb-6 flex items-center justify-center transition-opacity hover:opacity-75"
          >
            <img
              src="/brand/mirra-logo-dark-long.png"
              alt="Mirra"
              className="h-8 w-auto object-contain sm:h-9"
            />
          </Link>

          {/* Form Content */}
          <div className="w-full">{children}</div>
        </div>
      </section>
    </main>
  );
}

export function AuthHeading({
  pill,
  title = "Welcome back",
  subtitle = "Continue to your account",
}: {
  pill?: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="auth-heading mb-6 flex flex-col items-center text-center">
      {pill && (
        <span className="mb-2 inline-flex items-center rounded-full border border-black/8 bg-neutral-50 px-3 py-0.5 text-[11px] font-medium tracking-wide text-neutral-600 shadow-[0_1px_1px_rgba(0,0,0,0.03)]">
          {pill}
        </span>
      )}
      <h1 className="auth-serif-heading text-3xl sm:text-[34px] font-normal leading-tight text-neutral-900">
        {title}
      </h1>
      {subtitle && (
        <p className="mt-1.5 text-xs sm:text-[13px] text-neutral-500 font-normal">
          {subtitle}
        </p>
      )}
    </div>
  );
}


