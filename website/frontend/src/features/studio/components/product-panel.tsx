import { useMemo, useState } from "react";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import type { PublicProduct, ProductVariant, TryOnState } from "@/integrations/mirra-api/types";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { Button } from "@/components/ui/button";
import { formatPrice } from "@/lib/format";
import type { OutfitLayer } from "@/stores/studio-store";
import { PANEL_SPRING } from "@/lib/motion-presets";
import { CuratedLookRail } from "./curated-look-rail";

/**
 * Right-hand product panel — the merchant's product, verbatim from the
 * shared backend. Missing data is omitted or shown as deliberately
 * unavailable; nothing is invented.
 */
export function ProductPanel({
  product,
  activeColor,
  activeSize,
  tryOnState,
  otherLayers,
  onColorChange,
  onSizeChange,
  onAddToCart,
  onUnlockLayer,
  addToCartBusy,
  cartNotice,
}: {
  product: PublicProduct;
  activeColor: string | null;
  activeSize: string | null;
  tryOnState: TryOnState;
  otherLayers: OutfitLayer[];
  onColorChange: (color: string) => void;
  onSizeChange: (size: string) => void;
  onAddToCart: () => void;
  onUnlockLayer: (category: OutfitLayer["category"]) => void;
  addToCartBusy: boolean;
  cartNotice: string | null;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [chartOpen, setChartOpen] = useState(false);
  const reduceMotion = useReducedMotion();

  const colors = useMemo(() => {
    const seen = new Map<string, ProductVariant>();
    for (const v of product.variants) if (!seen.has(v.colorName)) seen.set(v.colorName, v);
    return [...seen.values()];
  }, [product]);

  const sizes = useMemo(
    () => product.variants.filter((v) => v.colorName === (activeColor ?? colors[0]?.colorName)),
    [product, activeColor, colors],
  );

  const activeVariant =
    sizes.find((v) => v.size === activeSize) ?? sizes.find((v) => v.inStock) ?? sizes[0] ?? null;

  const price = activeVariant?.price ?? product.price;
  const outOfStock = activeVariant ? !activeVariant.inStock : false;

  return (
    <LayoutGroup id={`product-panel-${product.publicProductId}`}>
      <aside className="rail-scroll flex h-auto max-h-[52dvh] flex-col overflow-y-auto overscroll-contain rounded-t-[28px] border-t border-white/80 bg-paper/82 px-5 pt-6 pb-8 shadow-[0_-18px_50px_-42px_rgba(33,31,28,0.58)] backdrop-blur-2xl sm:px-7 lg:h-full lg:max-h-none lg:rounded-none lg:border-t-0 lg:px-9 lg:py-8 lg:shadow-none">
        <motion.div
          key={product.publicProductId}
          initial={reduceMotion ? false : { opacity: 0.45, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          transition={reduceMotion ? { duration: 0.01 } : PANEL_SPRING}
        >
          <p className="font-mono text-[9px] font-medium tracking-[0.17em] text-faint uppercase">
            Selected piece
          </p>
          <h1 className="mt-2 text-[clamp(1.55rem,3vw,2rem)] leading-[1.08] font-semibold tracking-[-0.028em] text-ink">
            {product.name}
          </h1>
          {product.subtitle && (
            <p className="mt-1.5 text-sm leading-relaxed text-muted">{product.subtitle}</p>
          )}
        </motion.div>

        <div className="mt-5 flex items-end justify-between gap-4">
          <div>
            <p className="text-xl font-semibold tracking-[-0.018em]">
              {formatPrice(price, product.currency)}
            </p>
            {product.taxNote && <p className="mt-1 text-xs text-muted">{product.taxNote}</p>}
          </div>
          <span className="rounded-full border border-line/80 bg-surface px-2.5 py-1 font-mono text-[8px] tracking-[0.13em] text-muted uppercase">
            {activeVariant?.inStock ? "In stock" : "Availability"}
          </span>
        </div>

        {/* Colour variants */}
        {colors.length > 0 && (
          <fieldset className="mt-6">
            <legend className="font-mono text-[10px] font-medium tracking-[0.16em] text-ink-soft uppercase">
              Shop by variant
            </legend>
            <div className="mt-3 flex flex-wrap gap-2.5">
              {colors.map((v) => {
                const selected = (activeColor ?? colors[0].colorName) === v.colorName;
                return (
                  <motion.button
                    key={v.colorName}
                    type="button"
                    onClick={() => onColorChange(v.colorName)}
                    aria-pressed={selected}
                    aria-label={`Colour ${v.colorName}`}
                    title={v.colorName}
                    className="relative flex size-12 items-center justify-center rounded-full border border-line/80 bg-surface/70"
                    whileTap={reduceMotion ? undefined : { scale: 0.91 }}
                    transition={PANEL_SPRING}
                  >
                    {selected && (
                      <motion.span
                        layoutId="active-colour"
                        aria-hidden
                        className="pointer-events-none absolute inset-0 rounded-full border-2 border-ink shadow-[0_6px_18px_-12px_rgba(33,31,28,0.55)]"
                        transition={PANEL_SPRING}
                      />
                    )}
                    <span
                      className="size-9 rounded-full border border-black/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.5)]"
                      style={{ background: v.colorSwatch }}
                    />
                  </motion.button>
                );
              })}
            </div>
            <AnimatePresence initial={false} mode="popLayout">
              <motion.p
                key={activeColor ?? colors[0]?.colorName}
                className="mt-2 text-xs text-muted"
                initial={reduceMotion ? false : { opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                exit={reduceMotion ? undefined : { opacity: 0, x: 4 }}
                transition={reduceMotion ? { duration: 0.01 } : PANEL_SPRING}
              >
                {activeColor ?? colors[0]?.colorName}
              </motion.p>
            </AnimatePresence>
          </fieldset>
        )}

        {/* Sizes */}
        {sizes.length > 0 && (
          <fieldset className="mt-6">
            <legend className="font-mono text-[10px] font-medium tracking-[0.16em] text-ink-soft uppercase">
              Select size
            </legend>
            <div className="mt-3 flex flex-wrap gap-2.5">
              {sizes.map((v) => {
                const selected = activeVariant?.publicVariantId === v.publicVariantId;
                return (
                  <motion.button
                    key={v.publicVariantId}
                    type="button"
                    disabled={!v.inStock}
                    onClick={() => onSizeChange(v.size)}
                    aria-pressed={selected}
                    aria-label={`Size ${v.size}${!v.inStock ? " — out of stock" : ""}`}
                    className={`relative flex min-h-12 min-w-12 items-center justify-center overflow-hidden rounded-[13px] border px-3 text-sm font-medium ${
                      v.inStock
                        ? selected
                          ? "border-transparent text-canvas"
                          : "border-line bg-paper text-ink hover:border-line-strong"
                        : "border-line bg-mist/70 text-faint line-through"
                    }`}
                    whileTap={reduceMotion || !v.inStock ? undefined : { scale: 0.92 }}
                    transition={PANEL_SPRING}
                  >
                    {selected && (
                      <motion.span
                        layoutId="active-size"
                        aria-hidden
                        className="absolute inset-0 rounded-[13px] bg-ink"
                        transition={PANEL_SPRING}
                      />
                    )}
                    <span className="relative z-10">{v.size}</span>
                  </motion.button>
                );
              })}
            </div>
            {outOfStock && (
              <p className="mt-2 text-xs text-error">This option is currently out of stock.</p>
            )}
            {product.sizeChart && (
              <motion.button
                type="button"
                onClick={() => setChartOpen((o) => !o)}
                className="mt-2 min-h-11 rounded-full px-2 text-xs font-medium text-muted underline hover:text-ink"
                whileTap={reduceMotion ? undefined : { scale: 0.96 }}
                transition={PANEL_SPRING}
                aria-expanded={chartOpen}
              >
                {chartOpen ? "Hide size chart" : "Size chart"}
              </motion.button>
            )}
            <AnimatePresence initial={false}>
              {chartOpen && product.sizeChart && (
                <motion.div
                  className="mt-2 overflow-hidden"
                  initial={reduceMotion ? false : { opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={reduceMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
                  transition={reduceMotion ? { duration: 0.01 } : PANEL_SPRING}
                >
                  <div className="rail-scroll overflow-x-auto rounded-[14px] border border-line bg-surface/80">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-mist/70 font-mono tracking-wider text-muted uppercase">
                        <tr>
                          <th className="px-3 py-2.5">Size</th>
                          {Object.keys(product.sizeChart[0].measurements).map((k) => (
                            <th key={k} className="px-3 py-2.5">
                              {k}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {product.sizeChart.map((row) => (
                          <tr key={row.size} className="border-t border-line">
                            <td className="px-3 py-2.5 font-medium">{row.size}</td>
                            {Object.values(row.measurements).map((v, i) => (
                              <td key={i} className="px-3 py-2.5 text-ink-soft">
                                {v}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </fieldset>
        )}

        {/* Try-on status (screen-reader friendly) */}
        <div className="mt-5 flex min-h-10 items-center gap-2 rounded-[13px] bg-surface/80 px-3 py-2">
          <motion.span
            aria-hidden
            className={`size-2 rounded-full ${
              tryOnState === "ready" || tryOnState === "cached"
                ? "bg-ok"
                : tryOnState === "failed" || tryOnState === "unsupported"
                  ? "bg-error"
                  : "bg-silver"
            }`}
            animate={
              reduceMotion || !["requesting", "processing", "restoring"].includes(tryOnState)
                ? undefined
                : { scale: [1, 1.45, 1], opacity: [0.65, 1, 0.65] }
            }
            transition={{
              duration: 1.4,
              repeat: Number.POSITIVE_INFINITY,
              ease: "easeInOut",
            }}
          />
          <p
            className="font-mono text-[9px] font-medium tracking-[0.14em] text-muted uppercase"
            aria-live="polite"
          >
            Try-on:{" "}
            {tryOnState === "ready" || tryOnState === "cached"
              ? "on your avatar"
              : tryOnState === "requesting" ||
                  tryOnState === "processing" ||
                  tryOnState === "restoring"
                ? "in progress"
                : tryOnState === "unsupported"
                  ? "not available for this piece"
                  : tryOnState === "failed"
                    ? "didn't complete"
                    : "idle"}
          </p>
        </div>

        {/* Add to cart */}
        <div className="mt-4">
          <motion.div
            className="rounded-(--radius-control)"
            whileTap={
              reduceMotion || outOfStock || !activeVariant || addToCartBusy
                ? undefined
                : { scale: 0.975 }
            }
            transition={PANEL_SPRING}
          >
            <Button
              variant="studio-dark"
              size="lg"
              className="h-13! w-full rounded-(--radius-control)! shadow-[0_12px_28px_-18px_rgba(33,31,28,0.7)]"
              onClick={onAddToCart}
              disabled={outOfStock || !activeVariant}
              loading={addToCartBusy}
            >
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                aria-hidden
              >
                <path d="M6 8h12l-1 12H7L6 8Z" />
                <path d="M9 8V6a3 3 0 0 1 6 0v2" />
              </svg>
              Add to cart
            </Button>
          </motion.div>
          {cartNotice && (
            <motion.p
              role="status"
              className="mt-2 flex items-center gap-2 rounded-(--radius-compact) bg-ok/10 px-3 py-2 text-xs text-ok"
              initial={reduceMotion ? false : { opacity: 0, y: -3 }}
              animate={{ opacity: 1, y: 0 }}
              transition={reduceMotion ? { duration: 0.01 } : PANEL_SPRING}
            >
              <span
                aria-hidden
                className="flex size-4 items-center justify-center rounded-full bg-ok text-[9px] text-white"
              >
                ✓
              </span>
              {cartNotice}
            </motion.p>
          )}
        </div>

        {/* Product details accordion */}
        <div className="mt-6 border-t border-line/80 pt-2">
          <motion.button
            type="button"
            onClick={() => setDetailsOpen((o) => !o)}
            aria-expanded={detailsOpen}
            className="flex min-h-12 w-full items-center justify-between rounded-xl px-1 py-3 font-mono text-[10px] font-medium tracking-[0.16em] text-ink uppercase"
            whileTap={reduceMotion ? undefined : { scale: 0.985 }}
            transition={PANEL_SPRING}
          >
            Product details
            <motion.span
              aria-hidden
              className="flex size-8 items-center justify-center rounded-full bg-surface text-sm"
              animate={{ rotate: detailsOpen ? 90 : 0 }}
              transition={reduceMotion ? { duration: 0.01 } : PANEL_SPRING}
            >
              ▸
            </motion.span>
          </motion.button>
          <AnimatePresence initial={false}>
            {detailsOpen && (
              <motion.dl
                className="space-y-4 overflow-hidden pb-4 text-sm leading-relaxed text-ink-soft"
                initial={reduceMotion ? false : { opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
                transition={reduceMotion ? { duration: 0.01 } : PANEL_SPRING}
              >
                {product.description && <Detail label="About">{product.description}</Detail>}
                {product.materialAndCare && (
                  <Detail label="Material & care">{product.materialAndCare}</Detail>
                )}
                {product.fitInfo && <Detail label="Fit">{product.fitInfo}</Detail>}
                {product.manufacturingInfo && (
                  <Detail label="Made">{product.manufacturingInfo}</Detail>
                )}
                {!product.description &&
                  !product.materialAndCare &&
                  !product.fitInfo &&
                  !product.manufacturingInfo && (
                    <p className="text-xs text-faint">
                      The store hasn&apos;t provided further details for this piece.
                    </p>
                  )}
              </motion.dl>
            )}
          </AnimatePresence>
        </div>

        {/* The curated look — everything else currently on the avatar */}
        {otherLayers.length > 0 && (
          <motion.div
            layout
            className="mt-5 border-t border-line/80 pt-5"
            transition={PANEL_SPRING}
          >
            <div className="flex items-end justify-between gap-3">
              <p className="font-mono text-[10px] font-medium tracking-[0.17em] text-ink-soft uppercase">
                The curated <span className="text-xs tracking-normal normal-case italic">Look</span>
              </p>
              <span className="text-[10px] text-faint">{otherLayers.length} paired</span>
            </div>
            <CuratedLookRail layers={otherLayers} onUnlockLayer={onUnlockLayer} />
          </motion.div>
        )}
      </aside>
    </LayoutGroup>
  );
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="font-mono text-[10px] tracking-[0.16em] text-faint uppercase">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}
