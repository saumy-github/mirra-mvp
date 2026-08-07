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
          className="fixed inset-0 z-0 border-0 bg-graphite/20"
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
            className="quiet-scroll relative z-10 max-h-[calc(100dvh-1rem)] overflow-y-auto border border-b-0 border-hairline bg-vellum px-6 pt-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:border-b sm:p-8"
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
                  className="flex size-10 shrink-0 items-center justify-center rounded-panel-sm border border-hairline text-sm text-slate"
                >
                  ✦
                </span>
                <div className="min-w-0">
                  <p className="eyebrow">Signature Look</p>
                  <h2 className="mt-2.5 text-xl leading-tight font-medium tracking-[-0.02em] text-graphite">
                    Keep this outfit as a base
                  </h2>
                </div>
              </div>
              <motion.button
                type="button"
                onClick={onClose}
                aria-label="Close Signature Look"
                className="flex size-10 shrink-0 items-center justify-center rounded-panel-sm border border-hairline text-lg text-slate transition-colors hover:border-graphite hover:text-graphite"
                whileTap={reduceMotion ? undefined : { scale: 0.9 }}
                transition={SHEET_SPRING}
              >
                ×
              </motion.button>
            </div>

            <p className="mt-5 text-[13px] leading-relaxed text-slate">
              {layerNames.length > 0
                ? `Locks ${layerNames.join(" + ")} so new pieces are tried over garments you actually wear.`
                : "Locks the current outfit as your styling base."}
            </p>

            {layerNames.length > 0 && (
              <div
                className="quiet-scroll mt-4 flex gap-2 overflow-x-auto pb-1"
                aria-label="Garments in this look"
              >
                {layerNames.map((layerName) => (
                  <span
                    key={layerName}
                    className="shrink-0 rounded-panel-sm border border-hairline px-3 py-1.5 text-[11px] text-slate"
                  >
                    {layerName}
                  </span>
                ))}
              </div>
            )}

            <label className="eyebrow mt-7 block" htmlFor="look-name">
              Look name
            </label>
            <input
              id="look-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Everyday Denim"
              maxLength={60}
              className="mt-3 h-12 w-full rounded-panel-sm border border-hairline-strong bg-chalk px-4 text-[14px] transition-colors placeholder:text-ash focus-visible:border-graphite"
              autoFocus
            />
            <label className="mt-3 flex min-h-12 cursor-pointer items-center gap-3 rounded-panel-sm border border-hairline px-3.5 py-2.5 text-sm text-slate">
              <input
                type="checkbox"
                checked={asDefault}
                onChange={(e) => setAsDefault(e.target.checked)}
                className="size-4 shrink-0 accent-graphite"
              />
              <span>
                <span className="block text-[13px] font-medium text-graphite">
                  Use as my default base
                </span>
                <span className="mt-1 block text-[11px] leading-snug text-ash">
                  Apply automatically on future visits
                </span>
              </span>
            </label>
            <div className="mt-7 grid grid-cols-2 gap-3">
              <motion.button
                type="button"
                onClick={onClose}
                className="h-13 rounded-panel-sm border border-hairline-strong text-[11px] font-medium tracking-[0.14em] text-slate uppercase transition-colors hover:border-graphite hover:text-graphite"
                whileTap={reduceMotion ? undefined : { scale: 0.97 }}
                transition={SHEET_SPRING}
              >
                Cancel
              </motion.button>
              <motion.button
                type="submit"
                disabled={busy || !name.trim()}
                className="h-13 rounded-panel-sm bg-graphite text-[11px] font-medium tracking-[0.14em] text-vellum uppercase transition-colors hover:bg-black disabled:cursor-not-allowed disabled:opacity-40"
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
