import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import type { AvatarProfile, TryOnState } from "@/integrations/mirra-api/types";
import { Spinner } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { AvatarFigure, type StageLayer } from "./avatar-figure";
import type { OutfitLayer } from "@/stores/studio-store";

const STAGE_SPRING = {
  type: "spring" as const,
  stiffness: 400,
  damping: 40,
  mass: 0.9,
};

/**
 * The avatar stage — the studio's centrepiece. Quiet, private, and honest:
 * every engine state renders explicitly, and the figure is never slimmed
 * or beautified.
 */
export function AvatarStage({
  avatar,
  layers,
  tryOnState,
  failureReason,
  onRetry,
  onMakeSignatureLook,
  canMakeLook,
}: {
  avatar: AvatarProfile;
  layers: Partial<Record<string, OutfitLayer>>;
  tryOnState: TryOnState;
  failureReason: string | null;
  onRetry: () => void;
  onMakeSignatureLook: () => void;
  canMakeLook: boolean;
}) {
  const [zoom, setZoom] = useState(1);
  const reduceMotion = useReducedMotion();

  const stageLayers: StageLayer[] = Object.values(layers)
    .filter((l): l is OutfitLayer => !!l)
    .map((l) => ({
      category: l.category,
      assetUrl: l.assetUrl,
      key: `${l.category}-${l.variantPublicId}`,
    }));

  const worn = Object.values(layers).filter((l): l is OutfitLayer => !!l);
  const altText =
    worn.length === 0
      ? "Your avatar wearing base layers only."
      : `Your avatar wearing ${worn
          .map((l) => `${l.name}${l.size ? ` in size ${l.size}` : ""}`)
          .join(", ")}. Rendering state: ${tryOnState}.`;

  const busy =
    tryOnState === "requesting" || tryOnState === "processing" || tryOnState === "restoring";

  return (
    <div className="relative isolate flex h-full min-h-107.5 flex-1 flex-col items-center overflow-hidden rounded-3xl border border-white/80 bg-[radial-gradient(circle_at_50%_44%,rgba(255,255,255,0.94)_0%,rgba(251,250,247,0.84)_42%,rgba(237,234,227,0.62)_100%)] shadow-[0_1px_1px_rgba(33,31,28,0.03),0_24px_65px_-48px_rgba(33,31,28,0.52)] sm:min-h-125 lg:min-h-0">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-[14%] bottom-[11%] h-[8%] rounded-[50%] bg-ink/6 blur-2xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-linear-to-b from-white/60 to-transparent"
      />

      {/* Quiet Mirra presence + signature look action */}
      <div className="relative z-20 flex w-full items-center justify-between gap-3 px-3 pt-3 sm:px-4 sm:pt-4">
        <span className="rounded-full border border-white/80 bg-paper/55 px-3 py-2 font-mono text-[9px] font-medium tracking-[0.16em] text-muted uppercase shadow-sm backdrop-blur-xl sm:text-[10px]">
          Mirra Studio
        </span>
        <motion.button
          type="button"
          onClick={onMakeSignatureLook}
          disabled={!canMakeLook}
          aria-label="Make Signature Look"
          className="flex min-h-11 items-center gap-2 rounded-full border border-white/90 bg-paper/72 px-2.5 py-2 font-mono text-[9px] font-medium tracking-[0.11em] text-ink uppercase shadow-[0_8px_24px_-18px_rgba(33,31,28,0.58)] backdrop-blur-xl transition-colors hover:bg-paper disabled:cursor-not-allowed disabled:opacity-40 sm:px-4 sm:text-[10px] sm:tracking-[0.14em]"
          whileTap={reduceMotion || !canMakeLook ? undefined : { scale: 0.96 }}
          whileHover={reduceMotion || !canMakeLook ? undefined : { y: -1 }}
          transition={STAGE_SPRING}
        >
          <span
            aria-hidden
            className="flex size-5 items-center justify-center rounded-full bg-ink text-[10px] text-canvas"
          >
            ✦
          </span>
          <span className="hidden whitespace-nowrap sm:inline">Make Signature Look</span>
        </motion.button>
      </div>

      {/* Figure */}
      <div className="relative flex min-h-75 w-full flex-1 items-center justify-center overflow-hidden px-3">
        <motion.div
          className="flex h-full items-center justify-center will-change-transform"
          animate={{ scale: zoom }}
          transition={reduceMotion ? { duration: 0.01 } : STAGE_SPRING}
        >
          <AvatarFigure
            previewAssetUrl={avatar.previewAssetUrl}
            layers={stageLayers}
            className="h-full max-h-[min(58vh,680px)] min-h-70 sm:min-h-85"
            alt={altText}
          />
        </motion.div>

        {/* Engine states */}
        <AnimatePresence initial={false} mode="wait">
          {busy && (
            <motion.div
              key="busy"
              className="absolute inset-x-3 bottom-3 mx-auto flex min-h-11 w-fit items-center justify-center gap-2.5 rounded-full border border-white/90 bg-paper/72 px-4 py-2 text-center shadow-[0_12px_30px_-20px_rgba(33,31,28,0.55)] backdrop-blur-xl sm:bottom-5"
              role="status"
              aria-live="polite"
              initial={reduceMotion ? false : { opacity: 0, y: 8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 8, scale: 0.96 }}
              transition={reduceMotion ? { duration: 0.01 } : STAGE_SPRING}
            >
              <Spinner className="size-3.5 text-muted" />
              <span className="font-mono text-[9px] font-medium tracking-[0.16em] text-muted uppercase sm:text-[10px]">
                {tryOnState === "restoring" ? "Restoring look" : "Draping garment"}
              </span>
            </motion.div>
          )}
          {tryOnState === "unsupported" && (
            <StageNotice
              key="unsupported"
              title="Not available for try-on"
              body={failureReason ?? "This piece can't be draped yet."}
            />
          )}
          {tryOnState === "failed" && (
            <StageNotice
              key="failed"
              title="The mirror hesitated"
              body={failureReason ?? "The try-on couldn't be completed."}
              action={{ label: "Try again", onClick: onRetry }}
            />
          )}
        </AnimatePresence>
      </div>

      {/* Footer row: avatar id + view controls */}
      <div className="relative z-20 flex w-full items-center justify-between gap-2 px-3 pb-3 sm:px-4 sm:pb-4">
        <span className="truncate rounded-full bg-paper/38 px-2 py-1 font-mono text-[8px] tracking-[0.13em] text-muted uppercase backdrop-blur-sm sm:text-[9px]">
          Avatar ID: {avatar.avatarLabel}
        </span>
        <div
          className="flex gap-1 rounded-[14px] border border-white/80 bg-paper/62 p-1 shadow-[0_8px_24px_-20px_rgba(33,31,28,0.6)] backdrop-blur-xl"
          role="group"
          aria-label="View controls"
        >
          <StageControl
            label="Zoom out"
            onClick={() => setZoom((z) => Math.max(0.75, +(z - 0.125).toFixed(3)))}
          >
            −
          </StageControl>
          <StageControl label="Reset view" onClick={() => setZoom(1)}>
            <svg
              width="13"
              height="13"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.35"
              aria-hidden
            >
              <path d="M5 2.5H2.5V5M11 2.5h2.5V5M5 13.5H2.5V11M11 13.5h2.5V11" />
            </svg>
          </StageControl>
          <StageControl
            label="Zoom in"
            onClick={() => setZoom((z) => Math.min(1.5, +(z + 0.125).toFixed(3)))}
          >
            +
          </StageControl>
        </div>
      </div>
    </div>
  );
}

function StageControl({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="flex size-9 items-center justify-center rounded-field text-sm font-medium text-ink-soft transition-colors hover:bg-paper hover:text-ink sm:size-10"
      whileTap={reduceMotion ? undefined : { scale: 0.9 }}
      transition={STAGE_SPRING}
    >
      {children}
    </motion.button>
  );
}

function StageNotice({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: { label: string; onClick: () => void };
}) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      role="status"
      className="absolute inset-x-3 bottom-3 mx-auto w-fit max-w-xs rounded-card border border-white/90 bg-paper/78 px-5 py-4 text-center shadow-[0_18px_44px_-25px_rgba(33,31,28,0.6)] backdrop-blur-2xl sm:bottom-5"
      initial={reduceMotion ? false : { opacity: 0, y: 10, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 10, scale: 0.96 }}
      transition={reduceMotion ? { duration: 0.01 } : STAGE_SPRING}
    >
      <p className="text-[13px] font-medium text-ink">{title}</p>
      <p className="mt-1 text-xs leading-relaxed text-muted">{body}</p>
      {action && (
        <motion.button
          type="button"
          onClick={action.onClick}
          className="mt-2 min-h-10 rounded-full px-4 text-xs font-medium underline"
          whileTap={reduceMotion ? undefined : { scale: 0.95 }}
          transition={STAGE_SPRING}
        >
          {action.label}
        </motion.button>
      )}
    </motion.div>
  );
}
