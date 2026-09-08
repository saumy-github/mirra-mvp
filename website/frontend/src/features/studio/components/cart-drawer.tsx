import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { StudioThumbnail } from "./studio-thumbnail";
import { formatPrice } from "@/lib/format";
import type { StudioCartItem } from "@/stores/studio-store";
import { CONTROL_SPRING } from "@/lib/motion-presets";

const DRAWER_SPRING = {
  type: "spring" as const,
  stiffness: 440,
  damping: 42,
  mass: 0.88,
};

const FOCUSABLE_SELECTOR = [
  "button:not([disabled])",
  "[href]",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export interface CartDrawerProps {
  open: boolean;
  onClose: () => void;
  items: StudioCartItem[];
  onRemove: (variantPublicId: string) => void;
}

/** A local comparison shortlist. It deliberately makes no checkout promise. */
export function CartDrawer({ open, onClose, items, onRemove }: CartDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const reduceMotion = useReducedMotion();

  const itemCount = items.length;

  useEffect(() => {
    if (!open) return;

    returnFocusRef.current =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusFrame = window.requestAnimationFrame(() => {
      closeButtonRef.current?.focus();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab") return;

      const drawer = drawerRef.current;
      if (!drawer) return;

      const focusable = Array.from(drawer.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
        (element) => !element.hasAttribute("disabled"),
      );

      if (focusable.length === 0) {
        event.preventDefault();
        drawer.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      returnFocusRef.current?.focus();
    };
  }, [open, onClose]);

  const enter = reduceMotion
    ? { opacity: 0 }
    : { opacity: 0, x: 34, scale: 0.985, filter: "blur(5px)" };
  const exit = reduceMotion
    ? { opacity: 0 }
    : { opacity: 0, x: 34, scale: 0.985, filter: "blur(5px)" };
  const transition = reduceMotion ? { duration: 0.14 } : DRAWER_SPRING;

  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.div
          key="cart-drawer-layer"
          className="fixed inset-0 z-50"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0.12 : 0.2 }}
        >
          <motion.div
            aria-hidden
            className="absolute inset-0 bg-ink/24 backdrop-blur-[2px]"
            onPointerDown={onClose}
          />

          <motion.div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="shortlist-drawer-title"
            aria-describedby="shortlist-drawer-summary"
            tabIndex={-1}
            className="glass-heavy absolute inset-y-0 right-0 flex h-dvh w-full max-w-107.5 flex-col overflow-hidden border-y-0 border-r-0 text-ink sm:inset-y-3 sm:right-3 sm:h-[calc(100dvh-1.5rem)] sm:rounded-xl sm:border"
            style={{ transformOrigin: "top right" }}
            initial={enter}
            animate={{ opacity: 1, x: 0, scale: 1, filter: "blur(0px)" }}
            exit={exit}
            transition={transition}
          >
            <header className="relative flex min-h-19 shrink-0 items-center justify-between gap-4 px-5">
              <div className="min-w-0">
                <p className="truncate font-mono text-[9px] font-medium tracking-[0.16em] text-muted uppercase">
                  Mirra
                </p>
                <h2
                  id="shortlist-drawer-title"
                  className="mt-1 text-[22px] leading-none font-semibold tracking-tight"
                >
                  Your shortlist
                </h2>
              </div>

              <motion.button
                ref={closeButtonRef}
                type="button"
                onClick={onClose}
                aria-label="Close shortlist"
                className="flex size-11 shrink-0 items-center justify-center rounded-field border border-line/80 bg-paper/70 text-ink-soft shadow-[0_1px_1px_rgba(33,31,28,0.04)] transition-colors hover:bg-paper hover:text-ink"
                whileHover={reduceMotion ? undefined : { y: -1 }}
                whileTap={reduceMotion ? undefined : { scale: 0.92 }}
                transition={CONTROL_SPRING}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  aria-hidden
                >
                  <path d="m7 7 10 10M17 7 7 17" />
                </svg>
              </motion.button>

              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-5 bottom-0 h-px bg-linear-to-r from-transparent via-line-strong/80 to-transparent"
              />
            </header>

            <p id="shortlist-drawer-summary" className="sr-only">
              {itemCount === 0
                ? "Your shortlist is empty."
                : `${itemCount} ${itemCount === 1 ? "piece" : "pieces"} in your shortlist.`}
            </p>

            {items.length === 0 ? (
              <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-8 pb-20 text-center">
                <span
                  aria-hidden
                  className="flex size-14 items-center justify-center rounded-xl border border-line bg-paper/65 text-muted shadow-[0_12px_30px_-24px_rgba(33,31,28,0.5)]"
                >
                  <svg
                    width="23"
                    height="23"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M6.5 4.5h11v15l-5.5-3.4-5.5 3.4v-15Z" />
                  </svg>
                </span>
                <h3 className="mt-5 text-lg font-semibold tracking-[-0.02em]">
                  Your shortlist is empty
                </h3>
                <p className="mt-2 max-w-67.5 text-sm leading-relaxed text-muted">
                  Keep pieces here while you compare colours, sizes, and try-on results.
                </p>
              </div>
            ) : (
              <div className="rail-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-2 sm:px-5">
                <motion.ul layout className="divide-y divide-line/80">
                  <AnimatePresence initial={false} mode="popLayout">
                    {items.map((item) => (
                      <motion.li
                        layout
                        key={item.variantPublicId}
                        className="grid grid-cols-[88px_minmax(0,1fr)] gap-4 py-5"
                        initial={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8, scale: 0.985 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 14, scale: 0.98 }}
                        transition={transition}
                      >
                        <div className="h-27 overflow-hidden rounded-field border border-line/80 bg-surface">
                          <StudioThumbnail
                            src={item.thumbnailUrl}
                            label={item.productName}
                            fit="cover"
                            className="size-full"
                          />
                        </div>

                        <div className="flex min-w-0 flex-col">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <h3 className="line-clamp-2 text-sm leading-snug font-semibold tracking-[-0.012em]">
                                {item.productName}
                              </h3>
                              <p className="mt-1 truncate text-xs text-muted">
                                {item.colorName} · Size {item.size}
                              </p>
                            </div>
                            <p className="shrink-0 text-[13px] font-semibold tracking-[-0.01em]">
                              {item.unitPrice > 0
                                ? formatPrice(item.unitPrice, item.currency)
                                : "Price unavailable"}
                            </p>
                          </div>

                          <div className="mt-auto flex justify-end pt-3">
                            <motion.button
                              type="button"
                              onClick={() => onRemove(item.variantPublicId)}
                              className="min-h-9 rounded-lg px-2 text-[11px] font-medium text-muted underline decoration-line-strong underline-offset-4 transition-colors hover:text-error"
                              whileTap={reduceMotion ? undefined : { scale: 0.94 }}
                              transition={CONTROL_SPRING}
                              aria-label={`Remove ${item.productName} from shortlist`}
                            >
                              Remove
                            </motion.button>
                          </div>
                        </div>
                      </motion.li>
                    ))}
                  </AnimatePresence>
                </motion.ul>
              </div>
            )}

            <footer className="relative shrink-0 border-t border-line/80 bg-paper px-5 pt-4 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 top-0 h-8 -translate-y-full bg-linear-to-t from-paper/45 to-transparent"
              />

              <p className="text-xs leading-5 text-muted">
                This is a comparison list, not a shopping cart. Pieces remain here for this visit
                while you keep styling.
              </p>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
