import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { HangerItem } from "../types";

const ITEM_TRANSITION = { duration: 0.3, ease: [0.22, 0.8, 0.24, 1] as const };

/**
 * The Hanger's left half: this session's try-ons as a contact sheet.
 *
 * These aren't shopping cards — each thumbnail is a cached render, so
 * returning to one restores it without putting the engine to work again.
 */
export function RecentTryOns({
  entries,
  currentRenderId,
  onRestore,
  onRemove,
}: {
  entries: HangerItem[];
  currentRenderId: string | null;
  onRestore: (entry: HangerItem) => void;
  onRemove: (entry: HangerItem) => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div className="flex min-w-0 flex-col">
      <p className="eyebrow shrink-0">
        The Hanger{entries.length > 0 ? ` (${entries.length})` : ""}
      </p>

      <ul
        aria-label="Looks you've tried this session"
        className="quiet-scroll mt-3.5 flex min-h-19 items-center gap-2.5 overflow-x-auto pb-1"
      >
        {entries.length === 0 && (
          <li className="flex h-18 items-center pr-2 text-[10px] tracking-[0.12em] text-ash uppercase">
            Your tried pieces will wait here
          </li>
        )}

        <AnimatePresence initial={false} mode="popLayout">
          {entries.map((entry) => {
            const current = entry.renderId === currentRenderId;
            const stale = entry.status === "expired" || entry.status === "failed";

            return (
              <motion.li
                key={entry.id}
                layout="position"
                className="group relative shrink-0"
                initial={reduceMotion ? false : { opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={reduceMotion ? { opacity: 0 } : { opacity: 0, x: 6 }}
                transition={reduceMotion ? { duration: 0.01 } : ITEM_TRANSITION}
              >
                <button
                  type="button"
                  onClick={() => onRestore(entry)}
                  aria-current={current ? "true" : undefined}
                  title={`${entry.productName}${entry.size ? ` · ${entry.size}` : ""}${
                    stale ? ` (${entry.status})` : ""
                  }`}
                  aria-label={`Return to ${entry.productName}${
                    entry.size ? `, size ${entry.size}` : ""
                  }${current ? " (currently worn)" : ""}`}
                  className={`lift-1 block h-18 w-15 overflow-hidden rounded-thumb border bg-bone ${
                    current ? "border-graphite" : "border-hairline hover:border-hairline-strong"
                  } ${stale ? "opacity-45" : ""}`}
                >
                  <img
                    src={entry.thumbnailUrl}
                    alt=""
                    draggable={false}
                    className="size-full object-cover select-none"
                  />
                </button>

                <button
                  type="button"
                  onClick={() => onRemove(entry)}
                  aria-label={`Remove ${entry.productName} from The Hanger`}
                  className="absolute -top-1.5 -right-1.5 flex size-5 items-center justify-center rounded-full border border-hairline bg-vellum text-ash opacity-0 transition-opacity group-hover:opacity-100 hover:text-graphite focus-visible:opacity-100"
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
      </ul>
    </div>
  );
}
