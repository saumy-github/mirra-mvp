import { formatPrice } from "@/lib/format";

/**
 * The Hanger's right end. Two totals, kept visually distinct because they buy
 * different things: the selected piece on its own, and — when more than one
 * garment is on the figure — the whole styled outfit.
 */
export function CartSummary({
  currency,
  selectedPiecePrice,
  outfitPrice,
  outfitPieceCount,
  cartCount,
  busy,
  disabled,
  onAddSelected,
  onBuyTheLook,
  onViewCart,
}: {
  currency: string;
  selectedPiecePrice: number;
  outfitPrice: number;
  outfitPieceCount: number;
  cartCount: number;
  busy: boolean;
  disabled: boolean;
  onAddSelected: () => void;
  onBuyTheLook: () => void;
  onViewCart: () => void;
}) {
  const hasOutfit = outfitPieceCount > 1;

  return (
    <div className="flex shrink-0 items-center gap-6">
      <div className="hidden text-right sm:block">
        <p className="eyebrow">
          {hasOutfit ? `The look · ${outfitPieceCount} pieces` : "Selected piece"}
        </p>
        <p className="mt-2 text-[1.05rem] leading-none font-medium tracking-[-0.01em] text-graphite tabular-nums">
          {formatPrice(hasOutfit ? outfitPrice : selectedPiecePrice, currency)}
        </p>
        {hasOutfit && (
          <p className="mt-1.5 text-[11px] text-ash tabular-nums">
            Selected piece {formatPrice(selectedPiecePrice, currency)}
          </p>
        )}
      </div>

      <div className="flex items-center gap-3">
        {hasOutfit && (
          <button
            type="button"
            onClick={onBuyTheLook}
            disabled={busy}
            className="lift-1 h-12 rounded-panel-sm border border-graphite px-5 text-[11px] font-medium tracking-[0.14em] text-graphite uppercase hover:bg-bone disabled:pointer-events-none disabled:opacity-40"
          >
            Buy the look
          </button>
        )}

        <button
          type="button"
          onClick={onAddSelected}
          disabled={disabled || busy}
          className="lift-1 h-12 rounded-panel-sm bg-graphite px-6 text-[11px] font-medium tracking-[0.14em] text-vellum uppercase hover:bg-black disabled:pointer-events-none disabled:opacity-40"
        >
          Add to cart
        </button>

        {cartCount > 0 && (
          <button
            type="button"
            onClick={onViewCart}
            className="hidden text-[10px] tracking-[0.14em] text-ash uppercase transition-colors hover:text-graphite lg:block"
          >
            View cart ({cartCount})
          </button>
        )}
      </div>
    </div>
  );
}
