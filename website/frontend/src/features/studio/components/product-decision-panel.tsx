import { motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { formatPrice } from "@/lib/format";
import {
  colorsOf,
  sizeOptionsOf,
  type GarmentCategory,
  type OutfitPiece,
  type Product,
  type ProductVariant,
  type TryOnState,
} from "../types";
import { useCompleteTheLook } from "../hooks/use-complete-the-look";
import { VariantSelector } from "./variant-selector";
import { SizeSelector } from "./size-selector";
import { FitAvailability } from "./fit-availability";
import { ProductDetailsAccordion } from "./product-details-accordion";
import { CompleteTheLook } from "./complete-the-look";
import { WornPieces } from "./worn-pieces";

/**
 * Right region: the decision. Name, price, availability, the two choices
 * that change the fit, then one dark button. Everything else is folded below
 * the fold so this reads as a page from a lookbook, not a form.
 */
export function ProductDecisionPanel({
  product,
  activeVariant,
  activeColor,
  tryOnState,
  otherPieces,
  addToCartBusy,
  onColorChange,
  onSizeChange,
  onAddToCart,
  onSelectProduct,
  onAddProduct,
  onUnlockPiece,
}: {
  product: Product;
  activeVariant: ProductVariant | null;
  activeColor: string | null;
  tryOnState: TryOnState;
  otherPieces: OutfitPiece[];
  addToCartBusy: boolean;
  onColorChange: (color: string) => void;
  onSizeChange: (size: string) => void;
  onAddToCart: () => void;
  onSelectProduct: (product: Product) => void;
  onAddProduct: (product: Product) => void;
  onUnlockPiece: (category: GarmentCategory) => void;
}) {
  const reduceMotion = useReducedMotion();
  const { suggestions } = useCompleteTheLook(product);

  const colors = colorsOf(product);
  const sizes = sizeOptionsOf(product, activeColor ?? colors[0]?.colorName ?? null);
  const price = activeVariant?.price ?? product.price;
  const currency = activeVariant?.currency ?? product.currency;
  const outOfStock = activeVariant ? !activeVariant.inStock : false;

  return (
    <aside
      aria-label="Selected piece"
      className="quiet-scroll flex flex-1 flex-col border-t border-hairline bg-vellum px-5 pt-7 pb-8 lg:min-h-0 lg:overflow-y-auto lg:border-t-0 lg:border-l lg:px-8 lg:py-9"
    >
      <motion.header
        key={product.publicProductId}
        initial={reduceMotion ? false : { opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={
          reduceMotion ? { duration: 0.01 } : { duration: 0.34, ease: [0.22, 0.8, 0.24, 1] }
        }
      >
        <p className="eyebrow">Selected piece</p>

        <h1 className="mt-3.5 text-[clamp(1.75rem,2.2vw,2.25rem)] leading-[1.1] font-medium tracking-[-0.02em] text-graphite">
          {product.name}
        </h1>

        {product.subtitle && (
          <p className="mt-3 max-w-md text-[13px] leading-relaxed text-slate">{product.subtitle}</p>
        )}

        <div className="mt-5 flex items-baseline justify-between gap-4">
          <p className="text-[1.4rem] leading-none font-medium tracking-[-0.01em] text-graphite">
            {formatPrice(price, currency)}
          </p>
          <p className="text-[10px] tracking-[0.14em] text-ash uppercase">
            {activeVariant?.inStock ? "In stock" : "Out of stock"}
          </p>
        </div>

        {product.taxNote && <p className="mt-2 text-[11px] text-ash">{product.taxNote}</p>}
      </motion.header>

      <div className="mt-9 space-y-9">
        <VariantSelector
          variants={colors}
          activeColor={activeColor ?? colors[0]?.colorName ?? null}
          onChange={onColorChange}
        />

        <SizeSelector
          options={sizes}
          activeSize={activeVariant?.size ?? null}
          sizeChart={product.sizeChart}
          onChange={onSizeChange}
        />

        <FitAvailability tryOnState={tryOnState} />
      </div>

      {/* Sticky on small screens so the decision is always one tap away. */}
      <div className="sticky bottom-0 z-10 -mx-5 mt-7 border-t border-hairline bg-vellum px-5 py-4 lg:static lg:mx-0 lg:border-t-0 lg:bg-transparent lg:p-0">
        <button
          type="button"
          onClick={onAddToCart}
          disabled={outOfStock || !activeVariant || addToCartBusy}
          className="lift-1 flex h-14 w-full items-center justify-center gap-2.5 rounded-panel-sm bg-graphite text-[13px] font-medium tracking-[0.14em] text-vellum uppercase hover:bg-black disabled:pointer-events-none disabled:opacity-40"
        >
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.3"
            strokeLinejoin="round"
            aria-hidden
          >
            <path d="M5.6 8h12.8l-1 12.2H6.6L5.6 8Z" />
            <path d="M9.2 8V6.2a2.8 2.8 0 0 1 5.6 0V8" />
          </svg>
          {addToCartBusy ? "Adding…" : "Add to cart"}
        </button>

        {outOfStock && (
          <p className="mt-3 text-center text-[11px] text-slate">
            This size is sold out — try another.
          </p>
        )}
      </div>

      <div className="mt-9 space-y-9">
        <WornPieces pieces={otherPieces} onUnlock={onUnlockPiece} />

        <ProductDetailsAccordion product={product} />

        <CompleteTheLook products={suggestions} onSelect={onSelectProduct} onAdd={onAddProduct} />
      </div>
    </aside>
  );
}
