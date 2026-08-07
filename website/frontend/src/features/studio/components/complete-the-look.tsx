import { formatPrice } from "@/lib/format";
import type { Product } from "../types";

/**
 * Two or three pieces from the same store that pair with the selection.
 * Tapping one takes it to the stage; "Add" puts it straight in the bag.
 */
export function CompleteTheLook({
  products,
  onSelect,
  onAdd,
}: {
  products: Product[];
  onSelect: (product: Product) => void;
  onAdd: (product: Product) => void;
}) {
  if (products.length === 0) return null;

  return (
    <section aria-labelledby="complete-the-look-heading">
      <h2 id="complete-the-look-heading" className="eyebrow">
        Complete the look
      </h2>

      <ul className="mt-4 space-y-3">
        {products.map((product) => (
          <li key={product.publicProductId} className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => onSelect(product)}
              className="lift-1 flex min-w-0 flex-1 items-center gap-4 text-left"
              aria-label={`Try ${product.name}`}
            >
              <span className="block size-14 shrink-0 overflow-hidden rounded-thumb border border-hairline bg-bone">
                <img
                  src={product.thumbnailUrl}
                  alt=""
                  draggable={false}
                  className="size-full object-cover select-none"
                />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-medium text-graphite">
                  {product.name}
                </span>
                <span className="mt-1 block text-[12px] text-slate">
                  {formatPrice(product.price, product.currency)}
                </span>
              </span>
            </button>

            <button
              type="button"
              onClick={() => onAdd(product)}
              className="shrink-0 text-[10px] tracking-[0.14em] text-ash uppercase transition-colors hover:text-graphite"
              aria-label={`Add ${product.name} to cart`}
            >
              Add
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
