import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import type { SignatureLook } from "@/integrations/mirra-api/types";
import type { HangerEntry } from "@/lib/hanger";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { Skeleton } from "@/components/ui/misc";
import { StudioThumbnail } from "./studio-thumbnail";

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
  historyState,
  looksLoading,
  looksError,
  onRestore,
  onApplyLook,
  onRemoveLook,
}: {
  entries: HangerEntry[];
  currentRenderId: string | null;
  looks: SignatureLook[];
  appliedLookId: string | null;
  historyState: "idle" | "loading" | "ready" | "error";
  looksLoading: boolean;
  looksError: boolean;
  onRestore: (entry: HangerEntry) => void;
  onApplyLook: (look: SignatureLook) => void;
  onRemoveLook: (look: SignatureLook) => void;
}) {
  const reduceMotion = useReducedMotion();
  const quietEmpty =
    entries.length === 0 &&
    looks.length === 0 &&
    (historyState === "ready" || historyState === "idle") &&
    !looksLoading &&
    !looksError;

  if (quietEmpty) {
    return (
      <LayoutGroup id="studio-hanger">
        <motion.footer
          layout
          className="relative z-20 grid shrink-0 grid-cols-1 gap-2 border-t border-line/80 bg-canvas px-5 py-3 text-xs lg:grid-cols-[minmax(0,1fr)_20rem] lg:gap-8"
          transition={reduceMotion ? { duration: 0.01 } : HANGER_SPRING}
        >
          <div className="flex min-w-0 items-center justify-between gap-4">
            <p className="shrink-0 font-semibold text-ink">Recent try-ons</p>
            <p className="truncate text-muted">Starts after your first preview</p>
          </div>
          <div className="flex min-w-0 items-center justify-between gap-4">
            <p className="shrink-0 font-semibold text-ink">Saved looks</p>
            <p className="truncate text-muted">Save the outfit when it feels right</p>
          </div>
        </motion.footer>
      </LayoutGroup>
    );
  }

  return (
    <LayoutGroup id="studio-hanger">
      <footer className="relative z-20 grid shrink-0 grid-cols-1 gap-3 border-t border-line/80 bg-canvas px-4 py-3 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-center lg:gap-8 lg:px-5">
        {/* Hanger entries */}
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="mb-2 flex items-center justify-between gap-3 px-1">
            <p className="text-xs font-semibold tracking-[-0.01em] text-ink">Recent try-ons</p>
            <p className="text-xs text-muted">
              {historyState === "loading"
                ? "Restoring…"
                : historyState === "error"
                  ? "Unavailable"
                  : entries.length === 0
                    ? "Starts after your first try-on"
                    : `${entries.length} ${entries.length === 1 ? "piece" : "pieces"}`}
            </p>
          </div>
          <ul
            aria-label="The Hanger — looks you've tried this session"
            aria-busy={historyState === "loading"}
            className={`rail-scroll flex items-center gap-2.5 overflow-x-auto px-1 pb-1 ${
              entries.length > 0 || historyState === "loading" ? "min-h-18" : "min-h-7"
            }`}
          >
            {historyState === "loading" && entries.length === 0 && (
              <li className="flex gap-2" aria-hidden>
                <Skeleton className="h-17.5 w-15.5 rounded-[14px]" />
                <Skeleton className="h-17.5 w-15.5 rounded-[14px] opacity-65" />
              </li>
            )}
            {historyState === "error" && entries.length === 0 && (
              <li className="text-xs leading-5 text-muted">
                Recent try-ons couldn&apos;t be restored. New previews will still appear here.
              </li>
            )}
            {(historyState === "ready" || historyState === "idle") && entries.length === 0 && (
              <li className="text-xs leading-5 text-muted">
                Change a garment or size; successful previews stay within reach here.
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
                      <StudioThumbnail
                        src={entry.thumbnailUrl}
                        label={entry.productName}
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

        {/* Signature looks */}
        <div className="flex min-w-0 items-center gap-3 lg:flex-col lg:items-start lg:gap-2">
          <div className="flex shrink-0 items-center gap-2 lg:w-full lg:justify-between">
            <p className="text-xs font-semibold tracking-[-0.01em] text-ink">Saved looks</p>
            {looksLoading && <span className="text-xs text-muted">Loading…</span>}
          </div>
          <div className="min-w-0 flex-1 lg:w-full">
            <ul
              aria-label="Your Signature Looks"
              aria-busy={looksLoading}
              className="rail-scroll flex min-w-0 items-center gap-2 overflow-x-auto px-1 pb-1"
            >
              {looksLoading && looks.length === 0 && (
                <li className="flex gap-2" aria-hidden>
                  <Skeleton className="size-14 rounded-full" />
                  <Skeleton className="size-14 rounded-full opacity-65" />
                </li>
              )}
              {looksError && looks.length === 0 && (
                <li className="flex h-7 items-center text-xs text-muted">
                  Saved looks are temporarily unavailable.
                </li>
              )}
              {!looksLoading && !looksError && looks.length === 0 && (
                <li className="flex h-12 items-center text-xs text-muted">
                  Save the outfit on the stage when it feels right.
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
                        <StudioThumbnail
                          src={look.thumbnailUrl}
                          label={look.name}
                          className="h-full w-full rounded-full"
                        />
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
        </div>
      </footer>
    </LayoutGroup>
  );
}
