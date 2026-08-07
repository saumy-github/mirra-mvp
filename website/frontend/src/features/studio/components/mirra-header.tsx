import { Link } from "react-router-dom";
import { MirraMark } from "@/components/ui/logo";
import type { Merchant } from "../types";

/**
 * The room's frame, not a navbar: a thin rule, the mark, and two quiet
 * controls. No pills, no icon containers, no elevation.
 */
export function MirraHeader({
  accountInitial,
  profileImageUrl,
  cartCount,
  merchant,
  onCartOpen,
}: {
  accountInitial: string;
  profileImageUrl: string | null;
  cartCount: number;
  /** Rendered only when the catalogue is served on behalf of a store. */
  merchant?: Merchant | null;
  onCartOpen: () => void;
}) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-hairline bg-vellum px-5 lg:h-[4.5rem] lg:px-8">
      <div className="flex min-w-0 items-center gap-3.5">
        <MirraMark size={24} strokeWidth={1.15} className="shrink-0 text-graphite" />
        <span className="min-w-0">
          <span className="block text-[13px] leading-none font-medium tracking-[0.34em] text-graphite">
            MIRRA
          </span>
          <span className="mt-1.5 hidden text-[10px] leading-none tracking-[0.16em] text-ash uppercase sm:block">
            Virtual fitting room
          </span>
        </span>

        {merchant && (
          <>
            <span aria-hidden className="mx-1 hidden h-5 w-px bg-hairline md:block" />
            <span className="hidden truncate text-[11px] tracking-[0.06em] text-slate md:block">
              For {merchant.displayName ?? merchant.name}
            </span>
          </>
        )}
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onCartOpen}
          aria-label={`Open cart, ${cartCount} ${cartCount === 1 ? "item" : "items"}`}
          className="lift-1 relative flex size-10 items-center justify-center text-slate hover:text-graphite"
        >
          <svg
            width="19"
            height="19"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M5.6 8h12.8l-1 12.2H6.6L5.6 8Z" />
            <path d="M9.2 8V6.2a2.8 2.8 0 0 1 5.6 0V8" />
          </svg>
          {cartCount > 0 && (
            <span
              aria-hidden
              className="absolute top-1 right-0.5 min-w-4 rounded-full bg-graphite px-1 text-center text-[9px] leading-4 font-medium text-vellum"
            >
              {cartCount > 99 ? "99+" : cartCount}
            </span>
          )}
        </button>

        <Link
          to="/profile"
          aria-label="Your Mirra profile"
          className="lift-1 relative flex size-9 items-center justify-center overflow-hidden rounded-full border border-hairline-strong text-[11px] font-medium text-slate hover:border-graphite hover:text-graphite"
        >
          {profileImageUrl ? (
            <img
              src={profileImageUrl}
              alt=""
              draggable={false}
              className="size-full object-cover select-none"
            />
          ) : (
            accountInitial
          )}
        </Link>
      </div>
    </header>
  );
}
