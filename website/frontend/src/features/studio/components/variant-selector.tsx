import type { ProductVariant } from "../types";

/**
 * Colour swatches. Selection is a thin ring held off the swatch — the ring
 * does the work, so the swatch itself stays a clean disc of the actual colour.
 */
export function VariantSelector({
  variants,
  activeColor,
  onChange,
}: {
  variants: ProductVariant[];
  activeColor: string | null;
  onChange: (colorName: string) => void;
}) {
  if (variants.length === 0) return null;
  const selectedName = activeColor ?? variants[0].colorName;

  return (
    <fieldset>
      <legend className="eyebrow">Shop by variant</legend>

      <div className="mt-3.5 flex flex-wrap items-center gap-3">
        {variants.map((variant) => {
          const selected = variant.colorName === selectedName;
          return (
            <button
              key={variant.colorName}
              type="button"
              onClick={() => onChange(variant.colorName)}
              aria-pressed={selected}
              aria-label={`Colour ${variant.colorName}`}
              title={variant.colorName}
              className={`flex size-9 items-center justify-center rounded-full border transition-colors duration-200 ${
                selected ? "border-graphite" : "border-transparent hover:border-hairline-strong"
              }`}
            >
              <span
                className="size-7 rounded-full border border-black/10"
                style={{ background: variant.colorSwatch }}
              />
            </button>
          );
        })}
      </div>

      <p className="mt-3 text-[11px] tracking-[0.1em] text-slate uppercase">{selectedName}</p>
    </fieldset>
  );
}
