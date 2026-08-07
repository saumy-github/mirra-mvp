import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Spinner } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import type { AvatarProfile } from "@/integrations/mirra-api/types";
import type { OutfitPiece, TryOnState } from "../types";
import { AvatarRenderSlot } from "./avatar-render-slot";
import { StageControls } from "./stage-controls";

const NOTICE_TRANSITION = { duration: 0.28, ease: [0.22, 0.8, 0.24, 1] as const };

/**
 * The centre region: a bone-white room with the figure in it. Every piece of
 * chrome sits at a corner so the middle stays empty and the garment is the
 * only thing worth looking at.
 */
export function TryOnStage({
  avatar,
  pieces,
  tryOnState,
  failureReason,
  onRetry,
  onMakeSignatureLook,
  canMakeLook,
}: {
  avatar: AvatarProfile;
  pieces: OutfitPiece[];
  tryOnState: TryOnState;
  failureReason: string | null;
  onRetry: () => void;
  onMakeSignatureLook: () => void;
  canMakeLook: boolean;
}) {
  const [zoom, setZoom] = useState(1);
  const reduceMotion = useReducedMotion();

  const busy =
    tryOnState === "requesting" || tryOnState === "processing" || tryOnState === "restoring";

  const alt =
    pieces.length === 0
      ? "Your avatar, wearing nothing yet."
      : `Your avatar wearing ${pieces
          .map((p) => `${p.name}${p.size ? ` in size ${p.size}` : ""}`)
          .join(", ")}. Rendering state: ${tryOnState}.`;

  return (
    <section
      aria-label="Try-on stage"
      className="relative flex min-h-[26rem] flex-1 flex-col bg-bone px-5 py-5 lg:min-h-0 lg:px-8 lg:py-7"
    >
      {/* Top corners */}
      <div className="flex shrink-0 items-start justify-between gap-4">
        <p className="eyebrow eyebrow-strong">Mirra Studio</p>
        <button
          type="button"
          onClick={onMakeSignatureLook}
          disabled={!canMakeLook}
          className="lift-1 flex items-center gap-2 text-[10px] tracking-[0.16em] text-slate uppercase hover:text-graphite disabled:pointer-events-none disabled:opacity-35"
        >
          <svg
            width="11"
            height="11"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.1"
            strokeLinecap="round"
            aria-hidden
          >
            <path d="M6 1.5v9M1.5 6h9" />
          </svg>
          Make signature look
        </button>
      </div>

      {/* The figure */}
      <div className="relative flex min-h-0 flex-1 items-center justify-center py-6">
        <AvatarRenderSlot
          previewAssetUrl={avatar.previewAssetUrl}
          pieces={pieces}
          zoom={zoom}
          alt={alt}
        />

        <AnimatePresence initial={false} mode="wait">
          {busy && (
            <motion.p
              key="busy"
              role="status"
              aria-live="polite"
              className="absolute bottom-0 flex items-center gap-2.5 text-[10px] tracking-[0.16em] text-ash uppercase"
              initial={reduceMotion ? false : { opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 4 }}
              transition={reduceMotion ? { duration: 0.01 } : NOTICE_TRANSITION}
            >
              <Spinner className="size-3 text-ash" />
              {tryOnState === "restoring" ? "Restoring look" : "Draping garment"}
            </motion.p>
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

      {/* Bottom corners */}
      <div className="flex shrink-0 items-end justify-between gap-4">
        <p className="eyebrow">Avatar ID — {avatar.avatarLabel}</p>
        <StageControls zoom={zoom} onZoomChange={setZoom} />
      </div>
    </section>
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
      className="absolute bottom-0 max-w-xs border border-hairline bg-vellum px-5 py-4 text-center"
      initial={reduceMotion ? false : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: 6 }}
      transition={reduceMotion ? { duration: 0.01 } : NOTICE_TRANSITION}
    >
      <p className="text-[13px] font-medium text-graphite">{title}</p>
      <p className="mt-1.5 text-xs leading-relaxed text-slate">{body}</p>
      {action && (
        <button
          type="button"
          onClick={action.onClick}
          className="mt-3 text-[11px] tracking-[0.1em] text-graphite underline underline-offset-4"
        >
          {action.label}
        </button>
      )}
    </motion.div>
  );
}
