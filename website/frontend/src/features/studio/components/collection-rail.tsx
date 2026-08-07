import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRuntimeProvider } from "@/integrations/mirra-api";
import type { Product } from "../types";
import { ProductThumbnailRail } from "./product-thumbnail-rail";

/**
 * Left region: the merchant's collection. Categories as a plain editorial
 * list, then the garment scroller. Part of the frame — no card, no float.
 */
export function CollectionRail({
  activeProductId,
  onSelect,
}: {
  activeProductId: string | null;
  onSelect: (product: Product) => void;
}) {
  const [category, setCategory] = useState<string | undefined>(undefined);
  const [cursor, setCursor] = useState<string | undefined>(undefined);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["rail", category ?? "all", cursor ?? "0"],
    queryFn: () => getRuntimeProvider().listProducts({ category, cursor, limit: 10 }),
    staleTime: 60_000,
  });

  // If the selected piece isn't in the visible page, fall to the first one.
  useEffect(() => {
    if (!activeProductId || !data?.items[0]) return;
    const visible = data.items.some((p) => p.publicProductId === activeProductId);
    if (!visible) onSelect(data.items[0]);
  }, [activeProductId, data, onSelect]);

  return (
    <nav
      aria-label="Collection"
      className="flex min-h-0 flex-1 flex-col border-b border-hairline bg-vellum px-5 py-5 lg:border-r lg:border-b-0 lg:px-6 lg:py-7"
    >
      <p className="eyebrow">Collection</p>

      <ul className="no-scrollbar mt-4 flex gap-5 overflow-x-auto lg:mt-5 lg:flex-col lg:gap-0 lg:overflow-visible">
        {(data?.categories ?? []).map((cat) => {
          const selected = category === cat;
          return (
            <li key={cat} className="shrink-0">
              <button
                type="button"
                onClick={() => {
                  setCategory(selected ? undefined : cat);
                  setCursor(undefined);
                }}
                aria-pressed={selected}
                className={`relative block py-1.5 text-left text-[11px] tracking-[0.14em] whitespace-nowrap uppercase transition-colors lg:py-[7px] ${
                  selected ? "font-medium text-graphite" : "text-slate hover:text-graphite"
                }`}
              >
                <span
                  aria-hidden
                  className={`absolute top-1/2 -left-3 hidden size-[3px] -translate-y-1/2 rounded-full bg-graphite lg:block ${
                    selected ? "opacity-100" : "opacity-0"
                  }`}
                />
                {cat}
              </button>
            </li>
          );
        })}
      </ul>

      <span aria-hidden className="mt-5 hidden h-px w-8 bg-hairline-strong lg:block" />

      <div className="mt-4 flex min-h-0 flex-1 flex-col lg:mt-6">
        <ProductThumbnailRail
          products={data?.items ?? []}
          activeProductId={activeProductId}
          onSelect={onSelect}
          loading={isLoading}
          error={isError}
          onRetry={() => void refetch()}
        />
      </div>

      {data && (data.nextCursor || cursor) && (
        <div className="mt-3 flex items-center justify-between text-[10px] tracking-[0.12em] text-ash uppercase">
          <button
            type="button"
            disabled={!cursor}
            onClick={() => setCursor(undefined)}
            className="py-1 transition-colors hover:text-graphite disabled:pointer-events-none disabled:opacity-30"
          >
            First
          </button>
          <button
            type="button"
            disabled={!data.nextCursor}
            onClick={() => setCursor(data.nextCursor ?? undefined)}
            className="py-1 transition-colors hover:text-graphite disabled:pointer-events-none disabled:opacity-30"
          >
            More
          </button>
        </div>
      )}
    </nav>
  );
}
