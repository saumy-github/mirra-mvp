import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import type { SignatureLook } from "@/integrations/mirra-api/types";
import type { HangerEntry } from "@/lib/hanger";
import { formatPrice } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

const HANGER_SPRING = {
  type: "spring" as const,
  stiffness: 440,
  damping: 40,
  mass: 0.85,
};

/**
 * The Hanger — this session's try-on history rail (not a shopping carousel).
 * Selecting an entry restores its cached render without re-running the
 * engine. Signature Looks sit beside it, visually related but distinct.
 */
export function HangerBar({
  entries,
  currentRenderId,
  looks,
  appliedLookId,
  currency,
  checkoutPrice,
  onRestore,
  onApplyLook,
  onRemoveLook,
  onDirectCheckout,
  checkoutBusy,
  checkoutDisabled,
}: {
  entries: HangerEntry[];
  currentRenderId: string | null;
  looks: SignatureLook[];
  appliedLookId: string | null;
  currency: string;
  checkoutPrice: number;
  onRestore: (entry: HangerEntry) => void;
  onApplyLook: (look: SignatureLook) => void;
  onRemoveLook: (look: SignatureLook) => void;
  onDirectCheckout: () => void;
  checkoutBusy: boolean;
  checkoutDisabled: boolean;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <LayoutGroup id="studio-hanger">
      <footer className="relative z-20 flex h-46 shrink-0 flex-col gap-3 border-t border-white/70 bg-canvas/82 px-3 py-3 shadow-[0_-18px_44px_-40px_rgba(33,31,28,0.62)] backdrop-blur-2xl supports-backdrop-filter:bg-canvas/68 lg:h-32 lg:flex-row lg:items-center lg:gap-4 lg:px-5">
        {/* Hanger entries */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="mb-1.5 flex items-center justify-between gap-3 px-1">
            <p className="font-mono text-[9px] font-semibold tracking-[0.17em] text-ink-soft uppercase">
              The Hanger
            </p>
            <p className="text-[9px] text-faint">
              {entries.length === 0 ? "Try-ons appear here" : `${entries.length} recent`}
            </p>
          </div>
          <ul
            aria-label="The Hanger — looks you've tried this session"
            className="rail-scroll flex min-h-18 items-center gap-2.5 overflow-x-auto px-1 pb-1"
          >
            {entries.length === 0 && (
              <li className="flex min-h-17 min-w-55 items-center gap-3 rounded-2xl border border-dashed border-line-strong/80 bg-paper/35 px-4">
                <span
                  aria-hidden
                  className="flex size-9 items-center justify-center rounded-full bg-paper/80 text-base text-muted shadow-sm"
                >
                  +
                </span>
                <span className="font-mono text-[9px] leading-relaxed tracking-[0.12em] text-faint uppercase">
                  The Hanger — your tried looks will wait here
                </span>
              </li>
            )}
            <AnimatePresence initial={false} mode="popLayout">
              {entries.map((entry) => {
                const isCurrent = entry.renderId === currentRenderId;
                return (
                  <motion.li
                    layout="position"
                    key={entry.id}
                    className="shrink-0"
                    initial={reduceMotion ? false : { opacity: 0, x: -10, scale: 0.94 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 8, scale: 0.94 }}
                    transition={reduceMotion ? { duration: 0.01 } : HANGER_SPRING}
                  >
                    <motion.button
                      layout
                      type="button"
                      onClick={() => onRestore(entry)}
                      title={`${entry.productName}${entry.size ? ` · ${entry.size}` : ""}${
                        entry.status === "expired" ? " (expired — will re-render)" : ""
                      }`}
                      aria-label={`Return to ${entry.productName}${entry.size ? `, size ${entry.size}` : ""}${
                        isCurrent
                          ? " (current look)"
                          : entry.status === "expired"
                            ? " (expired result)"
                            : " (saved result)"
                      }`}
                      aria-current={isCurrent ? "true" : undefined}
                      className={`relative block h-17.5 w-15.5 overflow-hidden rounded-[15px] border p-1.5 ${
                        isCurrent
                          ? "border-transparent bg-paper shadow-[0_10px_24px_-17px_rgba(33,31,28,0.62)]"
                          : "border-white/80 bg-paper/62 hover:bg-paper"
                      } ${entry.status === "expired" ? "opacity-55" : ""} ${
                        entry.status === "failed" ? "opacity-45" : ""
                      }`}
                      whileTap={reduceMotion ? undefined : { scale: 0.91 }}
                      whileHover={reduceMotion ? undefined : { y: -2 }}
                      transition={HANGER_SPRING}
                    >
                      {isCurrent && (
                        <motion.span
                          layoutId="active-hanger-entry"
                          aria-hidden
                          className="pointer-events-none absolute inset-0 z-20 rounded-[15px] border-2 border-ink"
                          transition={HANGER_SPRING}
                        />
                      )}
                      <img
                        src={entry.thumbnailUrl}
                        alt=""
                        className="h-full w-full object-contain"
                      />
                      {isCurrent && (
                        <span
                          aria-hidden
                          className="absolute top-2 left-2 z-30 size-2 rounded-full border border-white/80 bg-ok"
                        />
                      )}
                      {(entry.status === "expired" || entry.status === "failed") && (
                        <span
                          aria-hidden
                          className="absolute inset-x-1 bottom-1 z-30 rounded-b-[9px] bg-mist/92 py-0.5 text-center font-mono text-[7px] text-muted uppercase backdrop-blur-sm"
                        >
                          {entry.status}
                        </span>
                      )}
                    </motion.button>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>
        </div>

        <div className="flex min-w-0 items-center gap-3 lg:contents">
          {/* Divider */}
          <span aria-hidden className="h-12 w-px shrink-0 bg-line-strong/70" />

          {/* Signature looks */}
          <div className="flex min-w-0 flex-1 items-center gap-2.5 lg:flex-initial lg:flex-col lg:items-start lg:gap-1.5">
            <p className="hidden font-mono text-[8px] font-semibold tracking-[0.14em] whitespace-nowrap text-muted uppercase sm:block">
              Signature looks
            </p>
            <ul
              aria-label="Your Signature Looks"
              className="rail-scroll flex min-w-0 items-center gap-2 overflow-x-auto p-1"
            >
              {looks.length === 0 && (
                <li className="flex h-12 max-w-31.5 items-center font-mono text-[8px] leading-snug tracking-[0.12em] text-faint uppercase">
                  No signature looks yet
                </li>
              )}
              <AnimatePresence initial={false} mode="popLayout">
                {looks.map((look) => {
                  const selected = appliedLookId === look.lookId;
                  return (
                    <motion.li
                      layout
                      key={look.lookId}
                      className="group relative shrink-0"
                      initial={reduceMotion ? false : { opacity: 0, scale: 0.88 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.88 }}
                      transition={reduceMotion ? { duration: 0.01 } : HANGER_SPRING}
                    >
                      <motion.button
                        type="button"
                        onClick={() => onApplyLook(look)}
                        title={`${look.name}${look.isDefault ? " (default)" : ""}`}
                        aria-label={`Apply Signature Look: ${look.name}`}
                        aria-pressed={selected}
                        className="relative flex size-14 items-center justify-center overflow-hidden rounded-full border border-white/90 bg-paper/70 p-2 shadow-[0_7px_18px_-15px_rgba(33,31,28,0.55)]"
                        whileTap={reduceMotion ? undefined : { scale: 0.9 }}
                        transition={HANGER_SPRING}
                      >
                        {selected && (
                          <motion.span
                            layoutId="active-signature-look"
                            aria-hidden
                            className="pointer-events-none absolute inset-0 z-20 rounded-full border-2 border-ink"
                            transition={HANGER_SPRING}
                          />
                        )}
                        {look.thumbnailUrl ? (
                          <img
                            src={look.thumbnailUrl}
                            alt=""
                            className="h-full w-full object-contain"
                          />
                        ) : (
                          <span className="text-xs font-medium text-muted">
                            {look.name.slice(0, 2)}
                          </span>
                        )}
                        {look.isDefault && (
                          <span
                            aria-hidden
                            className="absolute right-1 bottom-1 z-30 size-2 rounded-full border border-white bg-ok"
                          />
                        )}
                      </motion.button>
                      <motion.button
                        type="button"
                        onClick={() => onRemoveLook(look)}
                        aria-label={`Remove Signature Look: ${look.name}`}
                        className="absolute -top-1.5 -right-1.5 flex size-8 items-center justify-center rounded-full border border-white/90 bg-paper/95 text-xs text-muted opacity-100 shadow-sm transition-colors hover:text-error sm:opacity-0 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100"
                        whileTap={reduceMotion ? undefined : { scale: 0.88 }}
                        transition={HANGER_SPRING}
                      >
                        ×
                      </motion.button>
                    </motion.li>
                  );
                })}
              </AnimatePresence>
            </ul>
          </div>

          {/* One-click handoff for the selected product */}
          <span aria-hidden className="h-12 w-px shrink-0 bg-line-strong/70" />
          <div className="flex shrink-0 items-center gap-2.5">
            <div className="hidden text-right sm:block">
              <p className="font-mono text-[8px] font-medium tracking-[0.15em] text-muted uppercase">
                Selected piece
              </p>
              <p className="text-base font-semibold tracking-[-0.015em]">
                {formatPrice(checkoutPrice, currency)}
              </p>
            </div>
            <motion.div
              className="rounded-(--radius-compact)"
              whileTap={
                reduceMotion || checkoutBusy || checkoutDisabled ? undefined : { scale: 0.96 }
              }
              transition={HANGER_SPRING}
            >
              <Button
                variant="studio-dark"
                className="h-12 rounded-(--radius-compact)! px-4 shadow-[0_10px_24px_-18px_rgba(33,31,28,0.72)]"
                onClick={onDirectCheckout}
                loading={checkoutBusy}
                disabled={checkoutDisabled}
                title="Add this piece to your cart"
              >
                Add to cart
              </Button>
            </motion.div>
          </div>
        </div>
      </footer>
    </LayoutGroup>
  );
}
