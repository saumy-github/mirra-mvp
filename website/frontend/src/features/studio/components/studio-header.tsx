import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { MirraLogo } from "@/components/ui/logo";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { CONTROL_SPRING } from "@/lib/motion-presets";

const STUDIO_NAV = [
  { to: "/studio", label: "Studio", shortLabel: "Studio", current: true },
  { to: "/profile/measurements", label: "Fit profile", shortLabel: "Fit", current: false },
  {
    to: "/profile/signature-looks",
    label: "Saved looks",
    shortLabel: "Looks",
    current: false,
  },
] as const;

/**
 * Studio chrome. Adapted from user-side's merchant-branded header (which
 * rendered the tenant's logo/theme) — standalone has no merchant, so this
 * is just the Mirra mark.
 */
export function StudioHeader({
  accountInitial,
  profileImageUrl,
  cartCount,
  onCartOpen,
}: {
  accountInitial: string;
  profileImageUrl: string | null;
  cartCount: number;
  onCartOpen: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const press = reduceMotion ? undefined : { scale: 0.94 };

  return (
    <header className="relative z-30 flex h-16 shrink-0 items-center gap-2 px-3 sm:gap-4 sm:px-5">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-canvas/80 shadow-[0_12px_32px_-25px_rgba(33,31,28,0.45)] backdrop-blur-2xl supports-backdrop-filter:bg-canvas/65"
      />

      <Link
        to="/studio"
        aria-label="Mirra Studio"
        className="relative flex shrink-0 items-center rounded-lg px-1 py-1"
      >
        <MirraLogo alt="" height={30} className="sm:h-8" />
      </Link>

      <nav
        aria-label="App sections"
        className="rail-scroll relative flex min-w-0 flex-1 items-center justify-center gap-0.5 overflow-x-auto rounded-full bg-paper/48 p-1 backdrop-blur-xl sm:flex-initial sm:gap-1"
      >
        {STUDIO_NAV.map((item) => (
          <motion.div
            key={item.to}
            className="shrink-0 rounded-full"
            whileTap={reduceMotion ? undefined : { scale: 0.96 }}
            transition={CONTROL_SPRING}
          >
            <Link
              to={item.to}
              aria-label={item.label}
              aria-current={item.current ? "page" : undefined}
              className={`relative flex min-h-9 items-center justify-center overflow-hidden rounded-full px-2.5 text-xs font-semibold transition-colors sm:px-3.5 ${
                item.current ? "text-canvas" : "text-muted hover:bg-paper/70 hover:text-ink"
              }`}
            >
              {item.current && (
                <motion.span
                  layoutId="studio-navigation-selection"
                  aria-hidden
                  className="absolute inset-0 rounded-full bg-ink shadow-[0_8px_20px_-14px_rgba(33,31,28,0.75)]"
                  transition={reduceMotion ? { duration: 0.01 } : CONTROL_SPRING}
                />
              )}
              <span className="relative z-10 sm:hidden">{item.shortLabel}</span>
              <span className="relative z-10 hidden sm:inline">{item.label}</span>
            </Link>
          </motion.div>
        ))}
      </nav>

      <div className="relative ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
        <motion.button
          type="button"
          onClick={onCartOpen}
          aria-label={`Open cart, ${cartCount} ${cartCount === 1 ? "item" : "items"}`}
          className="relative flex size-11 items-center justify-center rounded-(--radius-control) border border-white/80 bg-paper/76 text-ink-soft shadow-[0_1px_1px_rgba(33,31,28,0.05),0_8px_20px_-16px_rgba(33,31,28,0.55)] backdrop-blur-xl transition-colors hover:bg-paper hover:text-ink"
          whileTap={press}
          whileHover={reduceMotion ? undefined : { y: -1 }}
          transition={CONTROL_SPRING}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            aria-hidden
          >
            <path d="M6 8h12l-1 12H7L6 8Z" />
            <path d="M9 8V6a3 3 0 0 1 6 0v2" />
          </svg>
          {cartCount > 0 && (
            <motion.span
              key={cartCount}
              aria-hidden
              className="absolute -top-1.5 -right-1.5 flex min-w-5 items-center justify-center rounded-full border-2 border-canvas bg-ink px-1 text-[9px] leading-4 font-semibold text-canvas"
              initial={reduceMotion ? false : { scale: 0.65, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={CONTROL_SPRING}
            >
              {cartCount > 99 ? "99+" : cartCount}
            </motion.span>
          )}
        </motion.button>
        <motion.div
          className="rounded-full border border-transparent"
          whileTap={press}
          whileHover={reduceMotion ? undefined : { y: -1 }}
          transition={CONTROL_SPRING}
        >
          <Link
            to="/profile"
            aria-label="Your Mirra profile"
            className="relative flex size-11 items-center justify-center overflow-hidden rounded-full border border-white/90 bg-paper/82 text-sm font-semibold text-ink shadow-[0_1px_1px_rgba(33,31,28,0.05),0_8px_20px_-16px_rgba(33,31,28,0.55),inset_0_0_0_1px_rgba(29,29,31,0.06)] backdrop-blur-xl transition-colors hover:bg-paper"
          >
            {profileImageUrl ? (
              <img
                src={profileImageUrl}
                alt=""
                draggable={false}
                className="absolute top-[-4%] left-1/2 h-[390%] max-w-none -translate-x-1/2 select-none"
              />
            ) : (
              accountInitial
            )}
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0 rounded-full bg-linear-to-b from-white/24 via-transparent to-ink/6"
            />
            <span
              aria-hidden
              className="absolute right-0.5 bottom-0.5 size-2.5 rounded-full border-2 border-paper bg-ok"
            />
          </Link>
        </motion.div>
      </div>
    </header>
  );
}
