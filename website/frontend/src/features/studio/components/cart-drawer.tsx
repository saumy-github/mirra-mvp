import { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
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
  onSetQuantity: (variantPublicId: string, quantity: number) => void;
  onRemove: (variantPublicId: string) => void;
  onCheckout: () => void;
  checkoutBusy: boolean;
  checkoutError: string | null;
}

/**
 * Local multi-item bag. The merchant handoff happens only when checkout is
 * explicitly committed by the shopper.
 */
export function CartDrawer({
  open,
  onClose,
  items,
  onSetQuantity,
  onRemove,
  onCheckout,
  checkoutBusy,
  checkoutError,
}: CartDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const reduceMotion = useReducedMotion();

  const itemCount = items.reduce((total, item) => total + item.quantity, 0);
  const subtotal = items.reduce((total, item) => total + item.unitPrice * item.quantity, 0);

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
            className="absolute inset-0 bg-graphite/20"
            onPointerDown={onClose}
          />

          <motion.div
            ref={drawerRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby="cart-drawer-title"
            aria-describedby="cart-drawer-summary"
            tabIndex={-1}
            className="absolute inset-y-0 right-0 flex h-dvh w-full max-w-107.5 flex-col overflow-hidden border-l border-hairline bg-vellum text-graphite"
            style={{ transformOrigin: "top right" }}
            initial={enter}
            animate={{ opacity: 1, x: 0, scale: 1, filter: "blur(0px)" }}
            exit={exit}
            transition={transition}
          >
            <header className="relative flex min-h-19 shrink-0 items-center justify-between gap-4 px-5">
              <div className="min-w-0">
                <p className="eyebrow truncate">Mirra</p>
                <h2
                  id="cart-drawer-title"
                  className="mt-2.5 text-[22px] leading-none font-medium tracking-[-0.02em]"
                >
                  Your cart
                </h2>
              </div>

              <motion.button
                ref={closeButtonRef}
                type="button"
                onClick={onClose}
                aria-label="Close shopping cart"
                className="flex size-10 shrink-0 items-center justify-center rounded-panel-sm border border-hairline text-slate transition-colors hover:border-graphite hover:text-graphite"
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
                className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-hairline"
              />
            </header>

            <p id="cart-drawer-summary" className="sr-only">
              {itemCount === 0
                ? "Your shopping cart is empty."
                : `${itemCount} ${itemCount === 1 ? "item" : "items"} in your shopping cart.`}
            </p>

            {items.length === 0 ? (
              <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-8 pb-20 text-center">
                <span
                  aria-hidden
                  className="flex size-14 items-center justify-center rounded-panel-sm border border-hairline text-ash"
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
                    <path d="M5.5 8.5h13l-1 11h-11l-1-11Z" />
                    <path d="M9 8.5V6.8a3 3 0 0 1 6 0v1.7" />
                  </svg>
                </span>
                <h3 className="mt-5 text-lg font-medium tracking-[-0.02em]">Your cart is ready</h3>
                <p className="mt-2 max-w-67.5 text-[13px] leading-relaxed text-slate">
                  Add pieces as you style. They will stay here until you are ready to check out.
                </p>
              </div>
            ) : (
              <div className="rail-scroll min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-2 sm:px-5">
                <motion.ul layout className="divide-y divide-hairline">
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
                        <div className="h-27 overflow-hidden rounded-thumb border border-hairline bg-bone">
                          <img src={item.thumbnailUrl} alt="" className="size-full object-cover" />
                        </div>

                        <div className="flex min-w-0 flex-col">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <h3 className="line-clamp-2 text-[13px] leading-snug font-medium tracking-[-0.012em]">
                                {item.productName}
                              </h3>
                              <p className="mt-1.5 truncate text-[11px] text-slate">
                                {item.colorName} · Size {item.size}
                              </p>
                            </div>
                            <p className="shrink-0 text-[13px] font-medium tracking-[-0.01em] tabular-nums">
                              {formatPrice(item.unitPrice * item.quantity, item.currency)}
                            </p>
                          </div>

                          <div className="mt-auto flex items-end justify-between gap-3 pt-3">
                            <div
                              className="flex h-9 items-center rounded-panel-sm border border-hairline p-0.5"
                              aria-label={`Quantity for ${item.productName}`}
                            >
                              <motion.button
                                type="button"
                                onClick={() =>
                                  onSetQuantity(item.variantPublicId, item.quantity - 1)
                                }
                                disabled={item.quantity <= 1}
                                aria-label={`Decrease ${item.productName} quantity`}
                                className="flex size-8 items-center justify-center text-base leading-none text-slate transition-colors hover:text-graphite disabled:opacity-30"
                                whileTap={
                                  reduceMotion || item.quantity <= 1 ? undefined : { scale: 0.86 }
                                }
                                transition={CONTROL_SPRING}
                              >
                                −
                              </motion.button>
                              <output
                                aria-live="polite"
                                className="min-w-7 text-center text-[11px] font-medium tabular-nums"
                              >
                                {item.quantity}
                              </output>
                              <motion.button
                                type="button"
                                onClick={() =>
                                  onSetQuantity(item.variantPublicId, item.quantity + 1)
                                }
                                disabled={item.quantity >= 10}
                                aria-label={`Increase ${item.productName} quantity`}
                                className="flex size-8 items-center justify-center text-base leading-none text-slate transition-colors hover:text-graphite disabled:opacity-30"
                                whileTap={
                                  reduceMotion || item.quantity >= 10 ? undefined : { scale: 0.86 }
                                }
                                transition={CONTROL_SPRING}
                              >
                                +
                              </motion.button>
                            </div>

                            <motion.button
                              type="button"
                              onClick={() => onRemove(item.variantPublicId)}
                              className="min-h-9 px-2 text-[10px] tracking-[0.12em] text-ash uppercase transition-colors hover:text-graphite"
                              whileTap={reduceMotion ? undefined : { scale: 0.94 }}
                              transition={CONTROL_SPRING}
                              aria-label={`Remove ${item.productName} from cart`}
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

            <footer className="relative shrink-0 border-t border-hairline px-5 pt-5 pb-[max(1.25rem,env(safe-area-inset-bottom))]">
              <span
                aria-hidden
                className="pointer-events-none absolute inset-x-0 top-0 h-8 -translate-y-full bg-linear-to-t from-vellum to-transparent"
              />

              <div className="flex items-baseline justify-between gap-4">
                <div>
                  <p className="eyebrow">Subtotal</p>
                  <p className="mt-2 text-[11px] leading-relaxed text-ash">
                    Shipping and taxes calculated at checkout
                  </p>
                </div>
                <p className="text-xl font-medium tracking-[-0.02em] tabular-nums">
                  {formatPrice(subtotal, items[0]?.currency ?? "INR")}
                </p>
              </div>

              {checkoutError && (
                <p
                  role="alert"
                  className="mt-3 border border-error/25 px-3 py-2.5 text-xs leading-relaxed text-error"
                >
                  {checkoutError}
                </p>
              )}

              <button
                type="button"
                onClick={onCheckout}
                disabled={items.length === 0 || checkoutBusy}
                aria-busy={checkoutBusy || undefined}
                className="lift-1 mt-5 flex h-14 w-full items-center justify-center rounded-panel-sm bg-graphite text-[13px] font-medium tracking-[0.14em] text-vellum uppercase hover:bg-black disabled:pointer-events-none disabled:opacity-40"
              >
                {checkoutBusy ? "Preparing checkout…" : "Checkout"}
              </button>
              <p className="mt-3 text-center text-[10px] leading-relaxed text-ash">
                Your cart is saved for this session.
              </p>
            </footer>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
