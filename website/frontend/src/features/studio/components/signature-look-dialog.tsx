import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { PANEL_SPRING as SHEET_SPRING } from "@/lib/motion-presets";

/** Small accessible dialog for naming a new Signature Look. */
export function SignatureLookDialog({
  open,
  onClose,
  onCreate,
  busy,
  layerNames,
}: {
  open: boolean;
  onClose: () => void;
  onCreate: (name: string, setAsDefault: boolean) => void;
  busy: boolean;
  layerNames: string[];
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [name, setName] = useState("");
  const [asDefault, setAsDefault] = useState(false);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setName("");
      setAsDefault(false);
      dialog.showModal();
    }
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className="fixed inset-x-0 top-auto bottom-0 m-0 max-h-[calc(100dvh-1rem)] w-full max-w-none overflow-visible border-0 bg-transparent p-0 text-ink sm:inset-0 sm:m-auto sm:w-[min(92vw,420px)]"
    >
      {open && (
        <button
          type="button"
          aria-label="Close dialog"
          onClick={onClose}
          className="fixed inset-0 z-0 border-0 bg-ink/25 backdrop-blur-[3px]"
        />
      )}
      <AnimatePresence
        initial={false}
        onExitComplete={() => {
          const dialog = ref.current;
          if (!open && dialog?.open) dialog.close();
        }}
      >
        {open && (
          <motion.form
            key="signature-look-sheet"
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) onCreate(name.trim(), asDefault);
            }}
            className="relative z-10 max-h-[calc(100dvh-1rem)] overflow-y-auto rounded-t-[28px] border border-b-0 border-white/85 bg-paper/88 px-5 pt-5 pb-[max(1.25rem,env(safe-area-inset-bottom))] shadow-[0_-24px_70px_-34px_rgba(33,31,28,0.62)] backdrop-blur-2xl sm:rounded-[26px] sm:border-b sm:p-6"
            style={{ transformOrigin: "bottom center" }}
            initial={
              reduceMotion
                ? { opacity: 0 }
                : { opacity: 0, y: 22, scale: 0.965, filter: "blur(7px)" }
            }
            animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
            exit={
              reduceMotion
                ? { opacity: 0 }
                : { opacity: 0, y: 22, scale: 0.965, filter: "blur(7px)" }
            }
            transition={reduceMotion ? { duration: 0.12 } : SHEET_SPRING}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex min-w-0 items-center gap-3">
                <span
                  aria-hidden
                  className="flex size-11 shrink-0 items-center justify-center rounded-[14px] bg-ink text-sm text-canvas shadow-[0_10px_24px_-17px_rgba(33,31,28,0.65)]"
                >
                  ✦
                </span>
                <div className="min-w-0">
                  <p className="font-mono text-[9px] font-medium tracking-[0.16em] text-muted uppercase">
                    Signature Look
                  </p>
                  <h2 className="mt-1 text-xl leading-tight font-semibold tracking-tight">
                    Keep this outfit as a base
                  </h2>
                </div>
              </div>
              <motion.button
                type="button"
                onClick={onClose}
                aria-label="Close Signature Look"
                className="flex size-11 shrink-0 items-center justify-center rounded-full bg-mist/70 text-lg text-muted transition-colors hover:bg-mist hover:text-ink"
                whileTap={reduceMotion ? undefined : { scale: 0.9 }}
                transition={SHEET_SPRING}
              >
                ×
              </motion.button>
            </div>

            <p className="mt-4 text-sm leading-relaxed text-muted">
              {layerNames.length > 0
                ? `Locks ${layerNames.join(" + ")} so new pieces are tried over garments you actually wear.`
                : "Locks the current outfit as your styling base."}
            </p>

            {layerNames.length > 0 && (
              <div
                className="rail-scroll mt-3 flex gap-2 overflow-x-auto pb-1"
                aria-label="Garments in this look"
              >
                {layerNames.map((layerName) => (
                  <span
                    key={layerName}
                    className="shrink-0 rounded-full border border-line bg-surface px-3 py-1.5 text-[11px] font-medium text-ink-soft"
                  >
                    {layerName}
                  </span>
                ))}
              </div>
            )}

            <label
              className="mt-5 block text-[13px] font-semibold text-ink-soft"
              htmlFor="look-name"
            >
              Look name
            </label>
            <input
              id="look-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Everyday Denim"
              maxLength={60}
              className="mt-2 h-12 w-full rounded-[14px] border border-line-strong bg-paper/85 px-4 text-[15px] shadow-[inset_0_1px_2px_rgba(33,31,28,0.03)] transition-colors placeholder:text-faint focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 focus-visible:ring-offset-2 focus-visible:ring-offset-paper"
              autoFocus
            />
            <label className="mt-3 flex min-h-12 cursor-pointer items-center gap-3 rounded-[14px] bg-surface/80 px-3.5 py-2 text-sm text-ink-soft">
              <input
                type="checkbox"
                checked={asDefault}
                onChange={(e) => setAsDefault(e.target.checked)}
                className="size-5 shrink-0 accent-ink"
              />
              <span>
                <span className="block font-medium text-ink">Use as my default base</span>
                <span className="mt-0.5 block text-[11px] leading-snug text-muted">
                  Apply automatically on future visits
                </span>
              </span>
            </label>
            <div className="mt-5 grid grid-cols-2 gap-2.5">
              <motion.button
                type="button"
                onClick={onClose}
                className="min-h-12 rounded-[14px] bg-mist/70 px-4 text-sm font-medium text-ink-soft transition-colors hover:bg-mist hover:text-ink"
                whileTap={reduceMotion ? undefined : { scale: 0.97 }}
                transition={SHEET_SPRING}
              >
                Cancel
              </motion.button>
              <motion.button
                type="submit"
                disabled={busy || !name.trim()}
                className="min-h-12 rounded-[14px] bg-ink px-5 text-sm font-semibold text-canvas shadow-[0_12px_28px_-18px_rgba(33,31,28,0.72)] disabled:cursor-not-allowed disabled:opacity-45"
                whileTap={reduceMotion || busy || !name.trim() ? undefined : { scale: 0.97 }}
                transition={SHEET_SPRING}
              >
                {busy ? "Saving…" : "Save look"}
              </motion.button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>
    </dialog>
  );
}
