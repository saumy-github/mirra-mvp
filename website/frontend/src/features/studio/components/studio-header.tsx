import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { MirraMark, MirraWordmark } from "@/components/ui/logo";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { CONTROL_SPRING } from "@/lib/motion-presets";

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
    <header className="relative z-30 flex h-16 shrink-0 items-center justify-between px-4 sm:px-5">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 border-b border-white/70 bg-canvas/80 shadow-[0_10px_30px_-28px_rgba(33,31,28,0.55)] backdrop-blur-2xl supports-backdrop-filter:bg-canvas/65"
      />

      <div className="relative flex min-w-0 items-center gap-3">
        <MirraMark size={26} className="text-ink" />
        <span className="min-w-0">
          <MirraWordmark className="block text-[11px] tracking-[0.3em] text-ink" />
          <span className="hidden text-[10px] font-medium tracking-[0.04em] text-muted sm:block">
            Virtual fitting room
          </span>
        </span>
      </div>

      <div className="relative flex items-center gap-2">
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
