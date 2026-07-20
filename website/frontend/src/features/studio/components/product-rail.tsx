import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { PublicProduct } from "@/integrations/mirra-api/types";
import { Skeleton } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { PinchCarousel } from "./pinch-carousel";

const RAIL_SPRING = {
  type: "spring" as const,
  stiffness: 460,
  damping: 38,
  mass: 0.75,
};

/**
 * A bounded, three-garment merchant rail. The centred garment is the current
 * selection; its two neighbours remain deliberately hazy until they snap in.
 */
export function ProductRail({
  activeProductId,
  onSelect,
}: {
  activeProductId: string | null;
  onSelect: (product: PublicProduct) => void;
}) {
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const reduceMotion = useReducedMotion();

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["rail", category ?? "all", cursor ?? "0"],
    queryFn: () =>
      getRuntimeProvider().listProducts({
        category,
        cursor,
        limit: 10,
      }),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!activeProductId || !data?.items[0]) return;
    const activeIsVisible = data.items.some(
      (product) => product.publicProductId === activeProductId,
    );
    if (!activeIsVisible) onSelect(data.items[0]);
  }, [activeProductId, data, onSelect]);

  return (
    <nav
      aria-label="Store garments"
      className="flex h-full min-h-0 w-22 shrink-0 flex-col overflow-hidden rounded-(--radius-panel) border border-white/80 bg-paper/55 shadow-[0_1px_1px_rgba(33,31,28,0.04),0_18px_45px_-32px_rgba(33,31,28,0.45)] backdrop-blur-2xl sm:w-26 lg:w-28"
    >
      <div className="px-2.5 pt-3 pb-1">
        <p className="truncate font-mono text-[8px] font-medium tracking-[0.16em] text-faint uppercase sm:text-[9px]">
          Collection
        </p>
      </div>

      <div className="rail-scroll flex max-h-28 flex-col gap-1 overflow-y-auto px-1.5 pb-1 sm:max-h-33">
        {(data?.categories ?? []).map((cat) => {
          const selected = category === cat;
          return (
            <motion.button
              key={cat}
              type="button"
              onClick={() => {
                setCategory(cat === category ? undefined : cat);
                setCursor(undefined);
              }}
              aria-pressed={selected}
              className={`relative min-h-8 overflow-hidden rounded-(--radius-compact) px-2 py-1.5 text-left font-mono text-[8px] font-medium tracking-widest uppercase sm:text-[9px] ${
                selected ? "text-canvas" : "text-muted hover:text-ink"
              }`}
              whileTap={reduceMotion ? undefined : { scale: 0.96 }}
              transition={RAIL_SPRING}
            >
              {selected && (
                <motion.span
                  layoutId="active-category"
                  aria-hidden
                  className="absolute inset-0 rounded-(--radius-compact) bg-ink"
                  transition={RAIL_SPRING}
                />
              )}
              <span className="relative z-10 block truncate">{cat}</span>
            </motion.button>
          );
        })}
      </div>

      <div className="relative min-h-0 flex-1">
        {isLoading && (
          <div
            aria-label="Loading garments"
            className="absolute inset-0 flex flex-col items-center justify-center gap-2"
          >
            {[0.42, 1, 0.42].map((opacity, index) => (
              <div
                key={index}
                style={{
                  opacity,
                  filter: index === 1 ? "none" : "blur(3px)",
                }}
              >
                <Skeleton className="aspect-5/6 w-18 rounded-(--radius-compact) sm:w-20.5" />
              </div>
            ))}
          </div>
        )}

        {isError && (
          <div className="absolute inset-0 flex flex-col items-center justify-center px-2 text-center">
            <p className="text-[10px] leading-snug text-muted">Couldn&apos;t load garments.</p>
            <motion.button
              type="button"
              onClick={() => refetch()}
              className="mt-2 min-h-9 rounded-(--radius-compact) px-2 text-[11px] font-medium underline"
              whileTap={reduceMotion ? undefined : { scale: 0.95 }}
              transition={RAIL_SPRING}
            >
              Retry
            </motion.button>
          </div>
        )}

        {data && !isError && (
          <PinchCarousel
            items={data.items}
            getKey={(product) => product.publicProductId}
            getLabel={(product) => product.name}
            axis="y"
            activeKey={activeProductId ?? undefined}
            onActiveChange={(product) => onSelect(product)}
            ariaLabel="Garment collection"
            stride={98}
            debounceMs={250}
            className="h-full outline-none focus-visible:ring-2 focus-visible:ring-ink/55 focus-visible:ring-inset"
            viewportClassName="min-h-0!"
            renderItem={(product, { active }) => {
              const eligible = product.tryOnEligible;
              const processing = product.variants.every(
                (variant) => variant.assetStatus === "processing",
              );

              return (
                <button
                  type="button"
                  onClick={() => onSelect(product)}
                  tabIndex={active ? 0 : -1}
                  aria-label={`${product.name}${!eligible ? " (try-on unavailable)" : processing ? " (asset preparing)" : ""}`}
                  aria-current={active ? "true" : undefined}
                  title={product.name}
                  className={`group relative block aspect-5/6 w-18 overflow-hidden rounded-(--radius-compact) border p-1 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ink sm:w-20.5 ${
                    active
                      ? "border-ink/85 bg-paper shadow-[0_14px_30px_-20px_rgba(33,31,28,0.62)]"
                      : "border-white/75 bg-paper/64"
                  }`}
                >
                  <img
                    src={product.thumbnailUrl}
                    alt=""
                    draggable={false}
                    className={`size-full object-contain transition-transform duration-300 motion-reduce:transition-none ${
                      active ? "group-hover:scale-[1.025]" : ""
                    } ${!eligible ? "opacity-45" : ""}`}
                  />
                  {active && (
                    <span
                      aria-hidden
                      className="absolute top-1.5 left-1.5 z-10 size-2 rounded-full border border-white/80 bg-ok shadow-sm"
                    />
                  )}
                  {!eligible && (
                    <span className="absolute inset-x-1 bottom-1 z-10 rounded-b-[5px] bg-mist/90 py-1 text-center font-mono text-[7px] tracking-wider text-muted uppercase backdrop-blur-sm">
                      view only
                    </span>
                  )}
                  {eligible && processing && (
                    <span className="absolute inset-x-1 bottom-1 z-10 rounded-b-[5px] bg-mist/90 py-1 text-center font-mono text-[7px] tracking-wider text-muted uppercase backdrop-blur-sm">
                      preparing
                    </span>
                  )}
                </button>
              );
            }}
          />
        )}
      </div>

      {data && (data.nextCursor || cursor) && (
        <div className="flex items-center justify-between border-t border-white/70 bg-paper/45 px-1.5 py-1.5 font-mono text-[8px] text-muted sm:text-[9px]">
          <motion.button
            type="button"
            disabled={!cursor}
            onClick={() => setCursor(undefined)}
            className="min-h-9 rounded-(--radius-compact) px-1.5 disabled:opacity-30"
            aria-label="First garment page"
            whileTap={reduceMotion ? undefined : { scale: 0.94 }}
            transition={RAIL_SPRING}
          >
            ↑ first
          </motion.button>
          <motion.button
            type="button"
            disabled={!data.nextCursor}
            onClick={() => setCursor(data.nextCursor ?? undefined)}
            className="min-h-9 rounded-(--radius-compact) px-1.5 disabled:opacity-30"
            aria-label="More garments"
            whileTap={reduceMotion ? undefined : { scale: 0.94 }}
            transition={RAIL_SPRING}
          >
            more ↓
          </motion.button>
        </div>
      )}
    </nav>
  );
}
