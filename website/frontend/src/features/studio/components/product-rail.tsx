import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion } from "motion/react";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { PublicProduct } from "@/integrations/mirra-api/types";
import { Skeleton } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { PinchCarousel } from "./pinch-carousel";
import { StudioThumbnail } from "./studio-thumbnail";

const RAIL_SPRING = {
  type: "spring" as const,
  stiffness: 460,
  damping: 38,
  mass: 0.75,
};

/**
 * A bounded, three-garment merchant rail. The centred garment is the current
 * selection while its neighbours remain visible as direct navigation targets.
 */
export function ProductRail({
  activeProductId,
  onSelect,
  onCollectionEmptyChange,
}: {
  activeProductId: string | null;
  onSelect: (product: PublicProduct) => void;
  onCollectionEmptyChange?: (empty: boolean) => void;
}) {
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [cursor, setCursor] = useState<string | undefined>(undefined);
  const [categories, setCategories] = useState<string[]>([]);
  const [desktopRail, setDesktopRail] = useState(() =>
    typeof window === "undefined" ? true : window.matchMedia("(min-width: 1024px)").matches,
  );
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const query = window.matchMedia("(min-width: 1024px)");
    const update = () => setDesktopRail(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);

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
    if (!data?.categories.length) return;
    setCategories((current) => [...new Set([...current, ...data.categories])]);
  }, [data?.categories]);

  useEffect(() => {
    if (!data || isError) return;
    onCollectionEmptyChange?.(data.items.length === 0);
  }, [data, isError, onCollectionEmptyChange]);

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
      className="order-2 flex h-48 min-h-0 w-full shrink-0 flex-col overflow-hidden border border-line/80 bg-paper lg:order-1 lg:h-full lg:w-36"
    >
      <div className="flex min-h-10 items-center gap-3 border-b border-line/70 px-3 lg:block lg:min-h-0 lg:border-b-0 lg:px-3 lg:pt-3 lg:pb-1">
        <p className="shrink-0 font-mono text-[10px] font-semibold tracking-[0.14em] text-muted uppercase">
          Collection
        </p>
        <div className="rail-scroll flex min-w-0 flex-1 gap-1 overflow-x-auto lg:mt-2 lg:max-h-32 lg:flex-col lg:overflow-y-auto lg:px-0 lg:pb-1">
          {[undefined, ...categories].map((cat) => {
            const selected = category === cat;
            const label = cat ?? "All";
            return (
              <motion.button
                key={label}
                type="button"
                onClick={() => {
                  setCategory(cat);
                  setCursor(undefined);
                }}
                aria-pressed={selected}
                className={`relative min-h-8 shrink-0 overflow-hidden rounded-full px-2.5 py-1.5 text-left text-[10px] font-medium lg:w-full ${
                  selected ? "text-canvas" : "text-muted hover:bg-surface hover:text-ink"
                }`}
                whileTap={reduceMotion ? undefined : { scale: 0.96 }}
                transition={RAIL_SPRING}
              >
                {selected && (
                  <motion.span
                    layoutId="active-category"
                    aria-hidden
                    className="absolute inset-0 rounded-full bg-ink"
                    transition={RAIL_SPRING}
                  />
                )}
                <span className="relative z-10 block truncate">{label}</span>
              </motion.button>
            );
          })}
        </div>
      </div>

      <div className="relative min-h-0 flex-1">
        {isLoading && (
          <div
            aria-label="Loading garments"
            className="absolute inset-0 flex flex-row items-center justify-center gap-2 lg:flex-col"
          >
            {[0, 1, 2].map((index) => (
              <div key={index}>
                <Skeleton className="h-20 w-18 rounded-xl lg:h-27 lg:w-23" />
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

        {data &&
          !isError &&
          (data.items.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center px-4 text-center">
              <p className="max-w-36 text-xs leading-5 text-muted">
                No pieces match this collection.
              </p>
            </div>
          ) : (
            <PinchCarousel
              items={data.items}
              getKey={(product) => product.publicProductId}
              getLabel={(product) => product.name}
              axis={desktopRail ? "y" : "x"}
              activeKey={activeProductId ?? undefined}
              onActiveChange={(product) => onSelect(product)}
              ariaLabel="Garment collection"
              stride={desktopRail ? 116 : 112}
              debounceMs={250}
              className="h-full outline-none focus-visible:ring-2 focus-visible:ring-ink/55 focus-visible:ring-inset"
              viewportClassName="min-h-0!"
              renderItem={(product, { active }) => {
                const eligible = product.tryOnEligible;
                const processing = product.variants.every(
                  (variant) => variant.assetStatus === "processing",
                );

                return (
                  <motion.button
                    type="button"
                    onClick={() => onSelect(product)}
                    tabIndex={active ? 0 : -1}
                    aria-label={`${product.name}${!eligible ? " (try-on unavailable)" : processing ? " (asset preparing)" : ""}`}
                    aria-current={active ? "true" : undefined}
                    title={product.name}
                    className={`group relative flex h-20 w-18 flex-col overflow-hidden rounded-xl border bg-paper p-1.5 text-left outline-none focus-visible:ring-2 focus-visible:ring-ink lg:h-27 lg:w-23 ${
                      active ? "border-transparent" : "border-line/70"
                    }`}
                    whileTap={reduceMotion ? undefined : { scale: 0.95 }}
                    transition={RAIL_SPRING}
                  >
                    {active && (
                      <motion.span
                        layoutId="active-garment"
                        aria-hidden
                        className="pointer-events-none absolute inset-0 rounded-xl border-2 border-ink"
                        transition={RAIL_SPRING}
                      />
                    )}
                    <StudioThumbnail
                      src={product.thumbnailUrl}
                      label={product.name}
                      className={`min-h-0 w-full flex-1 rounded-lg object-contain transition-transform duration-200 motion-reduce:transition-none ${
                        active ? "group-hover:scale-[1.025]" : ""
                      } ${!eligible ? "opacity-45" : ""}`}
                    />
                    <span className="relative z-10 mt-1 hidden w-full truncate px-0.5 text-[10px] font-semibold text-ink lg:block">
                      {product.name}
                    </span>
                    {!eligible && (
                      <span className="absolute inset-x-1.5 bottom-1.5 z-10 rounded-md bg-paper/95 py-0.5 text-center text-[8px] font-medium text-muted">
                        View only
                      </span>
                    )}
                    {eligible && processing && (
                      <span className="absolute inset-x-1.5 bottom-1.5 z-10 rounded-md bg-paper/95 py-0.5 text-center text-[8px] font-medium text-muted">
                        Preparing
                      </span>
                    )}
                  </motion.button>
                );
              }}
            />
          ))}
      </div>

      {data && (data.nextCursor || cursor) && (
        <div className="flex items-center justify-between border-t border-line/70 bg-paper px-2 py-1 text-[9px] text-muted">
          <motion.button
            type="button"
            disabled={!cursor}
            onClick={() => setCursor(undefined)}
            className="min-h-11 rounded-(--radius-compact) px-2 disabled:opacity-30"
            aria-label="First garment page"
            whileTap={reduceMotion ? undefined : { scale: 0.94 }}
            transition={RAIL_SPRING}
          >
            {desktopRail ? "↑ first" : "← first"}
          </motion.button>
          <motion.button
            type="button"
            disabled={!data.nextCursor}
            onClick={() => setCursor(data.nextCursor ?? undefined)}
            className="min-h-11 rounded-(--radius-compact) px-2 disabled:opacity-30"
            aria-label="More garments"
            whileTap={reduceMotion ? undefined : { scale: 0.94 }}
            transition={RAIL_SPRING}
          >
            {desktopRail ? "more ↓" : "more →"}
          </motion.button>
        </div>
      )}
    </nav>
  );
}
