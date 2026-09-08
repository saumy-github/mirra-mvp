import { useMemo, useState } from "react";
import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import type { PublicProduct, ProductVariant, TryOnState } from "@/integrations/mirra-api/types";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { Button } from "@/components/ui/button";
import { formatPrice } from "@/lib/format";
import type { OutfitLayer } from "@/stores/studio-store";
import { PANEL_SPRING } from "@/lib/motion-presets";
import { CuratedLookRail } from "./curated-look-rail";
import { StudioThumbnail } from "./studio-thumbnail";

/**
 * Right-hand product panel — the merchant's product, verbatim from the
 * shared backend. Missing data is omitted or shown as deliberately
 * unavailable; nothing is invented.
 */
export function ProductPanel({
  product,
  activeColor,
  activeSize,
  otherLayers,
  onColorChange,
  onSizeChange,
  onAddToShortlist,
  onUnlockLayer,
  tryOnState,
  tryOnFailureReason,
  onRetryTryOn,
  showPreviewFeedback,
  addToShortlistBusy,
  shortlistNotice,
}: {
  product: PublicProduct;
  activeColor: string | null;
  activeSize: string | null;
  otherLayers: OutfitLayer[];
  onColorChange: (color: string) => void;
  onSizeChange: (size: string) => void;
  onAddToShortlist: () => void;
  onUnlockLayer: (category: OutfitLayer["category"]) => void;
  tryOnState: TryOnState;
  tryOnFailureReason: string | null;
  onRetryTryOn: () => void;
  showPreviewFeedback: boolean;
  addToShortlistBusy: boolean;
  shortlistNotice: string | null;
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
  const priceAvailable = Number.isFinite(price) && price > 0;
  const outOfStock = activeVariant ? !activeVariant.inStock : false;
  const sizeChart = product.sizeChart ?? [];
  const sizeChartColumns = sizeChart[0] ? Object.keys(sizeChart[0].measurements) : [];

  return (
    <LayoutGroup id={`product-panel-${product.publicProductId}`}>
      <aside className="rail-scroll flex h-auto flex-col bg-paper px-5 py-7 sm:px-7 lg:h-full lg:min-h-0 lg:overflow-y-auto lg:overscroll-contain lg:px-8 lg:py-8">
        <motion.div
          key={product.publicProductId}
          className="grid grid-cols-[72px_minmax(0,1fr)] gap-4 border-b border-line/80 pb-6"
          initial={reduceMotion ? false : { opacity: 0.45, x: 8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={reduceMotion ? { duration: 0.01 } : PANEL_SPRING}
        >
          <div className="h-24 overflow-hidden rounded-xl border border-line/70 bg-surface p-1.5">
            <StudioThumbnail
              src={product.thumbnailUrl}
              label={product.name}
              className="size-full rounded-lg"
            />
          </div>
          <div className="min-w-0 pt-0.5">
            <p className="text-[11px] font-medium text-muted">Selected piece</p>
            <h1 className="mt-1 line-clamp-2 text-[clamp(1.3rem,2vw,1.65rem)] leading-[1.08] font-semibold tracking-[-0.035em] text-ink">
              {product.name}
            </h1>
            {product.subtitle && (
              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted">
                {product.subtitle}
              </p>
            )}
            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1">
              <p className="text-[15px] font-semibold tracking-[-0.02em]">
                {priceAvailable ? formatPrice(price, product.currency) : "Price unavailable"}
              </p>
              <span className="flex items-center gap-1.5 text-[11px] font-medium text-muted">
                <span
                  aria-hidden
                  className={`size-1.5 rounded-full ${activeVariant?.inStock ? "bg-ok" : "bg-error"}`}
                />
                {activeVariant?.inStock ? "In stock" : "Out of stock"}
              </span>
            </div>
          </div>
          {(product.taxNote || !priceAvailable) && (
            <p className="col-span-2 text-[11px] leading-relaxed text-muted">
              {priceAvailable
                ? product.taxNote
                : "Commerce pricing has not been connected for this piece yet."}
            </p>
          )}
        </motion.div>

        {/* Colour variants */}
        {colors.length > 0 && (
          <fieldset className="mt-6">
            <legend className="text-sm font-semibold tracking-[-0.01em] text-ink">Colour</legend>
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
                    className="relative flex size-11 items-center justify-center rounded-full border border-line/80 bg-surface/70"
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
                      className="size-8 rounded-full border border-black/10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.5)]"
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
            <legend className="text-sm font-semibold tracking-[-0.01em] text-ink">Size</legend>
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
            {sizeChart.length > 0 && (
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
              {chartOpen && sizeChart.length > 0 && (
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
                          {sizeChartColumns.map((k) => (
                            <th key={k} className="px-3 py-2.5">
                              {k}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {sizeChart.map((row) => (
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

        {showPreviewFeedback && (tryOnState === "unsupported" || tryOnState === "failed") && (
          <div
            role={tryOnState === "failed" ? "alert" : "status"}
            className="mt-6 rounded-[14px] border border-line bg-surface/75 px-4 py-3"
          >
            <p className="text-xs font-semibold text-ink">
              {tryOnState === "failed" ? "Preview couldn't update" : "Preview unavailable"}
            </p>
            <p className="mt-1 text-xs leading-5 text-muted">
              {tryOnFailureReason ??
                (tryOnState === "failed"
                  ? "The fitting preview couldn't be completed."
                  : "This piece can't be shown on your avatar yet.")}
            </p>
            {tryOnState === "failed" && (
              <motion.button
                type="button"
                onClick={onRetryTryOn}
                className="mt-2 min-h-10 rounded-full text-xs font-semibold text-ink underline decoration-line-strong underline-offset-4"
                whileTap={reduceMotion ? undefined : { scale: 0.95 }}
                transition={PANEL_SPRING}
              >
                Try preview again
              </motion.button>
            )}
          </div>
        )}

        {/* Add to shortlist */}
        <div className="mt-6">
          <motion.div
            className="rounded-(--radius-control)"
            whileTap={
              reduceMotion || outOfStock || !activeVariant || addToShortlistBusy
                ? undefined
                : { scale: 0.975 }
            }
            transition={PANEL_SPRING}
          >
            <Button
              variant="studio-dark"
              size="lg"
              className="h-13! w-full rounded-(--radius-control)! shadow-[0_12px_28px_-18px_rgba(33,31,28,0.7)]"
              onClick={onAddToShortlist}
              disabled={outOfStock || !activeVariant}
              loading={addToShortlistBusy}
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
                <path d="M6.5 4.5h11v15l-5.5-3.4-5.5 3.4v-15Z" />
              </svg>
              Add to shortlist
            </Button>
          </motion.div>
          {shortlistNotice && (
            <motion.p
              role="status"
              className="mt-3 flex items-center gap-2 text-xs font-medium text-ok"
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
              {shortlistNotice}
            </motion.p>
          )}
        </div>

        {/* Product details accordion */}
        <div className="mt-7">
          <motion.button
            type="button"
            onClick={() => setDetailsOpen((o) => !o)}
            aria-expanded={detailsOpen}
            className="flex min-h-12 w-full items-center justify-between rounded-xl px-1 py-3 text-[13px] font-semibold text-ink"
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
          <motion.div layout className="mt-7" transition={PANEL_SPRING}>
            <div className="flex items-end justify-between gap-3">
              <p className="text-[13px] font-semibold tracking-[-0.01em] text-ink">
                Paired with this look
              </p>
              <span className="text-xs text-muted">{otherLayers.length} paired</span>
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
      <dt className="text-xs font-semibold text-muted">{label}</dt>
      <dd className="mt-1">{children}</dd>
    </div>
  );
}
