import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { SignatureLook } from "../types";

const ITEM_TRANSITION = { duration: 0.3, ease: [0.22, 0.8, 0.24, 1] as const };

/**
 * The Hanger's centre: saved styling bases. A shopper who always wears the
 * same trousers keeps them here and tries everything else over them.
 */
export function SignatureLooks({
  looks,
  appliedLookId,
  canCreate,
  onApply,
  onRemove,
  onCreate,
}: {
  looks: SignatureLook[];
  appliedLookId: string | null;
  canCreate: boolean;
  onApply: (look: SignatureLook) => void;
  onRemove: (look: SignatureLook) => void;
  onCreate: () => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="flex min-w-0 flex-col">
      <p className="eyebrow shrink-0">
        Signature looks{looks.length > 0 ? ` (${looks.length})` : ""}
      </p>

      <ul
        aria-label="Your Signature Looks"
        className="quiet-scroll mt-3.5 flex min-h-19 items-center gap-3 overflow-x-auto pb-1"
      >
        {looks.length === 0 && (
          <li className="flex h-18 items-center pr-1 text-[10px] tracking-[0.12em] text-ash uppercase">
            No signature looks yet
          </li>
        )}

        <AnimatePresence initial={false} mode="popLayout">
          {looks.map((look) => {
            const applied = appliedLookId === look.lookId;
            return (
              <motion.li
                key={look.lookId}
                layout="position"
                className="group relative shrink-0"
                initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96 }}
                transition={reduceMotion ? { duration: 0.01 } : ITEM_TRANSITION}
              >
                <button
                  type="button"
                  onClick={() => onApply(look)}
                  aria-pressed={applied}
                  title={`${look.name}${look.isDefault ? " (default)" : ""}`}
                  aria-label={`Apply Signature Look: ${look.name}`}
                  className={`lift-1 flex size-15 items-center justify-center overflow-hidden rounded-full border bg-bone ${
                    applied ? "border-graphite" : "border-hairline hover:border-hairline-strong"
                  }`}
                >
                  {look.thumbnailUrl ? (
                    <img
                      src={look.thumbnailUrl}
                      alt=""
                      draggable={false}
                      className="size-full object-cover select-none"
                    />
                  ) : (
                    <span className="text-[11px] font-medium text-slate">
                      {look.name.slice(0, 2).toUpperCase()}
                    </span>
                  )}
                </button>

                {look.isDefault && (
                  <span
                    aria-hidden
                    title="Applied by default"
                    className="absolute right-0.5 bottom-0.5 size-2 rounded-full border border-vellum bg-verdigris"
                  />
                )}

                <button
                  type="button"
                  onClick={() => onRemove(look)}
                  aria-label={`Remove Signature Look: ${look.name}`}
                  className="absolute -top-1 -right-1 flex size-5 items-center justify-center rounded-full border border-hairline bg-vellum text-ash opacity-0 transition-opacity group-hover:opacity-100 hover:text-graphite focus-visible:opacity-100"
                >
                  <svg
                    width="8"
                    height="8"
                    viewBox="0 0 12 12"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    aria-hidden
                  >
                    <path d="m3 3 6 6M9 3l-6 6" />
                  </svg>
                </button>
              </motion.li>
            );
          })}
        </AnimatePresence>

        <li className="shrink-0">
          <button
            type="button"
            onClick={onCreate}
            disabled={!canCreate}
            title={
              canCreate
                ? "Save the current outfit as a Signature Look"
                : "Wear something first to save a look"
            }
            className="lift-1 flex size-15 items-center justify-center rounded-full border border-dashed border-hairline-strong text-ash transition-colors hover:border-graphite hover:text-graphite disabled:pointer-events-none disabled:opacity-35"
            aria-label="Create a new Signature Look"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 12 12"
              fill="none"
              stroke="currentColor"
              strokeWidth="1"
              strokeLinecap="round"
              aria-hidden
            >
              <path d="M6 1.5v9M1.5 6h9" />
            </svg>
          </button>
        </li>
      </ul>
    </div>
  );
}
