import { AnimatePresence, motion } from "motion/react";
import type { CaptureSession } from "@/integrations/mirra-api/types";
import { PulseDot } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { MATERIAL_SPRING } from "@/lib/motion-presets";

/**
 * Right-hand synchronisation column of the QR screen. Text mirrors the real
 * capture-session state — no invented progress.
 */
const STATE_COPY: Record<CaptureSession["state"], { label: string; detail: string }> = {
  created: {
    label: "PREPARING",
    detail: "Creating a private, one-time connection for your phone.",
  },
  qr_ready: {
    label: "AWAITING SYNC",
    detail: "Open Camera on your phone and scan the code to begin.",
  },
  paired: {
    label: "PHONE CONNECTED",
    detail: "Your phone is linked. Continue there for the guided capture.",
  },
  consent_pending: {
    label: "CONSENT REQUESTED",
    detail: "Review what will be captured, then approve on your phone.",
  },
  capturing: {
    label: "CAPTURE IN PROGRESS",
    detail: "Follow the pose guides on your phone. This window will update live.",
  },
  uploading: {
    label: "RECEIVING PHOTOS",
    detail: "Your photographs are arriving over the encrypted connection.",
  },
  uploaded: {
    label: "CAPTURE COMPLETE",
    detail: "All required photographs arrived safely.",
  },
  processing: {
    label: "PREPARING PROFILE",
    detail: "Your secure capture is now becoming an avatar.",
  },
  completed: { label: "PROFILE SYNCHRONIZED", detail: "Your avatar is ready." },
  expired: {
    label: "SESSION EXPIRED",
    detail: "The one-time pairing code expired. Create a fresh one to continue.",
  },
  cancelled: {
    label: "SESSION CANCELLED",
    detail: "Pairing was cancelled. No new photographs will be received.",
  },
  failed: {
    label: "SOMETHING WENT WRONG",
    detail: "The capture could not be completed. A fresh link usually resolves it.",
  },
};

const JOURNEY_STEP: Record<CaptureSession["state"], number> = {
  created: 1,
  qr_ready: 1,
  paired: 2,
  consent_pending: 2,
  capturing: 3,
  uploading: 3,
  uploaded: 3,
  processing: 4,
  completed: 4,
  expired: 1,
  cancelled: 1,
  failed: 1,
};

export function SyncStatus({
  session,
  onRestart,
  onCancel,
}: {
  session: CaptureSession;
  onRestart: () => void;
  onCancel: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const copy = STATE_COPY[session.state];
  const active = !["expired", "cancelled", "failed", "completed"].includes(session.state);
  const error = ["expired", "cancelled", "failed"].includes(session.state);
  const uploadedCount = session.uploadedStepIds.length;
  const requiredCount = session.steps.filter((s) => s.required).length;
  const journeyStep = JOURNEY_STEP[session.state];

  return (
    <section className="flex w-full max-w-md flex-col items-center text-center" aria-live="polite">
      <div className="mb-9 flex items-center gap-2" aria-label={`Step ${journeyStep} of 4`}>
        {["Pair", "Connect", "Capture", "Create"].map((label, index) => {
          const step = index + 1;
          const complete = step < journeyStep;
          const current = step === journeyStep;
          return (
            <div key={label} className="flex items-center gap-2">
              <motion.span
                animate={{
                  width: current ? 30 : 7,
                  backgroundColor:
                    complete || current
                      ? error
                        ? "var(--color-error)"
                        : "var(--color-ink)"
                      : "var(--color-line-strong)",
                }}
                transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
                className="h-1.75 rounded-full"
                aria-hidden
              />
              <span className="sr-only">
                {label}: {complete ? "complete" : current ? "current" : "upcoming"}
              </span>
            </div>
          );
        })}
      </div>

      <AnimatePresence mode="popLayout" initial={false}>
        <motion.div
          key={session.state}
          initial={
            reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, y: 12, filter: "blur(8px)" }
          }
          animate={{ opacity: 1, scale: 1, y: 0, filter: "blur(0px)" }}
          exit={
            reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, y: 12, filter: "blur(8px)" }
          }
          transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
          className="flex w-full flex-col items-center"
        >
          <div
            className={`relative flex size-20 items-center justify-center rounded-[1.7rem] border bg-white/72 shadow-[0_18px_48px_-32px_rgba(33,31,28,.55)] backdrop-blur-xl ${
              error ? "border-error/20 text-error" : "border-white text-ink"
            }`}
          >
            <div className="absolute inset-2 rounded-[1.25rem] border border-line/75" />
            <PulseDot active={active} />
          </div>

          <p
            className={`mono-tag mt-7 text-[10px]! tracking-[0.28em]! ${error ? "text-error" : "text-ink"}`}
          >
            {copy.label}
          </p>
          <h1 className="mt-3 text-[1.75rem] leading-[1.08] font-semibold tracking-[-0.03em] text-balance text-ink">
            {session.state === "qr_ready"
              ? "Create your personal fit"
              : session.state === "capturing" || session.state === "uploading"
                ? "Stay with your phone"
                : session.state === "paired" || session.state === "consent_pending"
                  ? "Connection made"
                  : session.state === "uploaded" || session.state === "processing"
                    ? "We have what we need"
                    : error
                      ? "Let's reconnect"
                      : "Getting things ready"}
          </h1>
          <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted">{copy.detail}</p>

          {(session.state === "capturing" || session.state === "uploading") && (
            <div className="mt-6 w-full max-w-xs rounded-2xl border border-line bg-surface/80 px-4 py-3.5">
              <div className="flex items-center justify-between text-[11px] font-medium text-ink-soft">
                <span>Guided photographs</span>
                <span className="font-mono">
                  {uploadedCount} / {requiredCount}
                </span>
              </div>
              <div
                className="mt-3 grid gap-1.5"
                style={{
                  gridTemplateColumns: `repeat(${Math.max(requiredCount, 1)}, minmax(0, 1fr))`,
                }}
              >
                {Array.from({ length: Math.max(requiredCount, 1) }).map((_, index) => (
                  <motion.span
                    key={index}
                    initial={false}
                    animate={{
                      backgroundColor:
                        index < uploadedCount ? "var(--color-ink)" : "var(--color-line)",
                    }}
                    transition={reduceMotion ? { duration: 0.16 } : MATERIAL_SPRING}
                    className="h-1.5 rounded-full"
                  />
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </AnimatePresence>

      <div className="mt-9 w-full rounded-[1.4rem] border border-line/80 bg-white/55 p-4 text-left shadow-[0_14px_45px_-38px_rgba(33,31,28,.45)] backdrop-blur-xl">
        <div className="flex gap-3">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-mist text-ink-soft">
            <svg viewBox="0 0 18 18" className="size-4" fill="none" aria-hidden>
              <path
                d="M9 1.8 14.5 3.8v3.9c0 3.4-2 6.2-5.5 7.8-3.5-1.6-5.5-4.4-5.5-7.8V3.8L9 1.8Z"
                stroke="currentColor"
                strokeLinejoin="round"
              />
              <path d="m6.4 8.8 1.5 1.5 3.5-3.5" stroke="currentColor" strokeLinecap="round" />
            </svg>
          </span>
          <div>
            <p className="text-xs font-semibold text-ink">Your capture stays yours</p>
            <p className="mt-1 text-[11px] leading-relaxed text-muted">
              Photographs are encrypted in transit and used only to build your avatar. They are
              never shown to anyone else.
            </p>
          </div>
        </div>
      </div>

      {(session.state === "expired" ||
        session.state === "failed" ||
        session.state === "cancelled") && (
        <motion.button
          type="button"
          onClick={onRestart}
          whileTap={reduceMotion ? undefined : { scale: 0.98 }}
          transition={MATERIAL_SPRING}
          className="mt-7 min-h-11 rounded-full bg-ink px-6 py-2.5 text-sm font-medium text-canvas shadow-sm hover:bg-black"
        >
          Generate a fresh code
        </motion.button>
      )}

      {active && session.state !== "processing" && (
        <motion.button
          type="button"
          onClick={onCancel}
          whileTap={reduceMotion ? undefined : { scale: 0.97 }}
          transition={MATERIAL_SPRING}
          className="mt-6 min-h-10 px-4 text-xs font-medium text-muted hover:text-ink"
        >
          Cancel pairing
        </motion.button>
      )}
    </section>
  );
}
