import { useCallback, useEffect, useRef, useState } from "react";
import { Skeleton } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { Product } from "../types";

/**
 * The garment scroller. Vertical in the rail, horizontal when the room
 * collapses to one column. Selection is a hairline outline and nothing else —
 * no glow, no scale, no badge unless the garment genuinely can't be worn.
 */
export function ProductThumbnailRail({
  products,
  activeProductId,
  onSelect,
  loading,
  error,
  onRetry,
}: {
  products: Product[];
  activeProductId: string | null;
  onSelect: (product: Product) => void;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  const scrollerRef = useRef<HTMLUListElement>(null);
  const reduceMotion = useReducedMotion();
  const [atStart, setAtStart] = useState(true);
  const [atEnd, setAtEnd] = useState(false);

  const syncEdges = useCallback(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const vertical = el.scrollHeight > el.clientHeight;
    const pos = vertical ? el.scrollTop : el.scrollLeft;
    const max = vertical ? el.scrollHeight - el.clientHeight : el.scrollWidth - el.clientWidth;
    setAtStart(pos <= 2);
    setAtEnd(pos >= max - 2);
  }, []);

  useEffect(() => {
    syncEdges();
  }, [products, syncEdges]);

  const step = useCallback(
    (direction: -1 | 1) => {
      const el = scrollerRef.current;
      if (!el) return;
      const first = el.querySelector("li");
      const stride = first ? first.getBoundingClientRect().height + 10 : 116;
      el.scrollBy({
        top: stride * direction,
        behavior: reduceMotion ? "auto" : "smooth",
      });
    },
    [reduceMotion],
  );

  if (error) {
    return (
      <div className="px-1 py-6 text-left">
        <p className="text-[12px] leading-relaxed text-slate">The collection didn&apos;t load.</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 text-[11px] tracking-[0.08em] text-graphite underline underline-offset-4"
        >
          Try again
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex gap-2.5 px-1 lg:flex-col">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="aspect-4/5 w-20 rounded-thumb lg:w-full" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <RailStep
        direction={-1}
        disabled={atStart}
        onClick={() => step(-1)}
        label="Scroll to earlier garments"
      />

      <ul
        ref={scrollerRef}
        onScroll={syncEdges}
        aria-label="Garments in this collection"
        className="no-scrollbar -mx-1 flex min-h-0 snap-x snap-mandatory gap-2.5 overflow-x-auto overflow-y-hidden px-1 py-1 lg:mx-0 lg:flex-1 lg:snap-y lg:flex-col lg:overflow-x-hidden lg:overflow-y-auto lg:px-0"
      >
        {products.map((product) => {
          const active = product.publicProductId === activeProductId;
          const preparing = product.variants.every((v) => v.assetStatus === "processing");

          return (
            <li key={product.publicProductId} className="shrink-0 snap-start lg:w-full">
              <button
                type="button"
                onClick={() => onSelect(product)}
                aria-current={active ? "true" : undefined}
                title={product.name}
                className={`lift-1 relative block aspect-4/5 w-20 overflow-hidden rounded-thumb border bg-bone lg:w-full ${
                  active ? "border-graphite" : "border-hairline hover:border-hairline-strong"
                }`}
              >
                <img
                  src={product.thumbnailUrl}
                  alt={product.name}
                  draggable={false}
                  className={`size-full object-cover select-none ${
                    product.tryOnEligible ? "" : "opacity-55"
                  }`}
                />
                {(!product.tryOnEligible || preparing) && (
                  <span className="absolute inset-x-0 bottom-0 bg-vellum/92 py-1 text-center text-[8px] tracking-[0.14em] text-ash uppercase">
                    {product.tryOnEligible ? "Preparing" : "View only"}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>

      <RailStep
        direction={1}
        disabled={atEnd}
        onClick={() => step(1)}
        label="Scroll to later garments"
      />
    </div>
  );
}

/** A thin chevron affordance — desktop only; the row scrolls by touch below lg. */
function RailStep({
  direction,
  disabled,
  onClick,
  label,
}: {
  direction: -1 | 1;
  disabled: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className="hidden h-7 w-full shrink-0 items-center justify-center text-ash transition-colors hover:text-graphite disabled:pointer-events-none disabled:opacity-25 lg:flex"
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden
        style={{ transform: `rotate(${direction === -1 ? -90 : 90}deg)` }}
      >
        <path d="m9 5 7 7-7 7" />
      </svg>
    </button>
  );
}
