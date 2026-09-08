import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "motion/react";
import type { AvatarProfile, TryOnState } from "@/integrations/mirra-api/types";
import { Spinner } from "@/components/ui/misc";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { GlbViewer } from "@/features/profile/components/avatar-glb-viewer";
import { getRuntimeProvider } from "@/integrations/mirra-api";
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
  onMakeSignatureLook,
  canMakeLook,
  tryOnSessionId,
  renderSessionId,
  renderId,
  onAvatarViewStateChange,
}: {
  avatar: AvatarProfile;
  layers: Partial<Record<string, OutfitLayer>>;
  tryOnState: TryOnState;
  onMakeSignatureLook: () => void;
  canMakeLook: boolean;
  tryOnSessionId: string | null;
  renderSessionId: string | null;
  renderId: string | null;
  onAvatarViewStateChange: (state: "loading" | "ready" | "error") => void;
}) {
  const [lastReadyRender, setLastReadyRender] = useState<{
    sessionId: string;
    renderId: string;
  } | null>(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    setLastReadyRender(null);
  }, [tryOnSessionId]);

  useEffect(() => {
    if (renderId && renderSessionId && (tryOnState === "ready" || tryOnState === "cached")) {
      setLastReadyRender({ sessionId: renderSessionId, renderId });
    } else if (tryOnState === "idle" || tryOnState === "failed" || tryOnState === "unsupported") {
      setLastReadyRender(null);
    }
  }, [renderId, renderSessionId, tryOnState]);

  // A finished render's GLB holds avatar and garment together — the plugin
  // exports with bExportAvatar always on. Keep the last completed preview only
  // while its replacement is processing; terminal failures return to the
  // plain avatar rather than mislabelling an old outfit as the new selection.
  const currentReadyRender =
    renderId && renderSessionId && (tryOnState === "ready" || tryOnState === "cached")
      ? { sessionId: renderSessionId, renderId }
      : null;
  const busy =
    tryOnState === "requesting" || tryOnState === "processing" || tryOnState === "restoring";
  const displayRender = currentReadyRender ?? (busy ? lastReadyRender : null);
  const showRender = !!displayRender;

  const worn = Object.values(layers).filter((l): l is OutfitLayer => !!l);
  const stageLabel =
    !showRender || worn.length === 0
      ? "Your avatar, wearing nothing yet."
      : `Your avatar wearing ${worn
          .map((l) => `${l.name}${l.size ? ` in size ${l.size}` : ""}`)
          .join(", ")}. Rendering state: ${tryOnState}.`;

  return (
    <div className="relative isolate order-1 flex h-full min-h-107.5 flex-1 flex-col items-center overflow-hidden rounded-[20px] border border-line/80 bg-[radial-gradient(circle_at_50%_42%,rgba(255,255,255,0.98)_0%,rgba(250,249,246,0.94)_48%,rgba(235,232,225,0.78)_100%)] sm:min-h-125 lg:order-2 lg:min-h-0">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-[14%] bottom-[11%] h-[8%] rounded-[50%] bg-ink/6 blur-2xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-linear-to-b from-white/60 to-transparent"
      />

      {/* The only stage-level action appears after a successful preview. */}
      <div className="relative z-20 flex min-h-15 w-full items-center justify-end px-3 pt-3 sm:px-4 sm:pt-4">
        <AnimatePresence initial={false}>
          {canMakeLook && (
            <motion.button
              type="button"
              onClick={onMakeSignatureLook}
              aria-label="Save this outfit as a look"
              className="flex min-h-11 items-center gap-2 rounded-full border border-white/90 bg-paper/72 px-2.5 py-2 font-mono text-[9px] font-medium tracking-[0.11em] text-ink uppercase shadow-[0_8px_24px_-18px_rgba(33,31,28,0.58)] backdrop-blur-xl transition-colors hover:bg-paper sm:px-4 sm:text-[10px] sm:tracking-[0.14em]"
              initial={reduceMotion ? false : { opacity: 0, scale: 0.94, x: 6 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.94, x: 6 }}
              whileTap={reduceMotion ? undefined : { scale: 0.96 }}
              whileHover={reduceMotion ? undefined : { y: -1 }}
              transition={reduceMotion ? { duration: 0.12 } : STAGE_SPRING}
            >
              <span
                aria-hidden
                className="flex size-5 items-center justify-center rounded-full bg-ink text-[10px] text-canvas"
              >
                ✦
              </span>
              <span className="whitespace-nowrap">Save look</span>
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* Figure */}
      <div className="relative flex min-h-75 w-full flex-1 items-center justify-center overflow-hidden px-3">
        <span className="sr-only" aria-live="polite">
          {stageLabel}
        </span>
        <AnimatePresence initial={false} mode="popLayout">
          <motion.div
            key={
              showRender ? `try-on-${displayRender.sessionId}-${displayRender.renderId}` : "avatar"
            }
            className="flex h-full w-full items-center justify-center will-change-transform"
            initial={reduceMotion ? false : { opacity: 0, y: 8, scale: 0.985 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6, scale: 0.99 }}
            transition={reduceMotion ? { duration: 0.12 } : STAGE_SPRING}
          >
            {showRender ? (
              <GlbViewer
                queryKey={["tryon-render-glb", displayRender.sessionId, displayRender.renderId]}
                fetchGlb={() =>
                  getRuntimeProvider().getTryOnRenderGlb(
                    displayRender.sessionId,
                    displayRender.renderId,
                  )
                }
                className="h-full max-h-[min(64vh,720px)] min-h-70 w-full rounded-none! border-0! bg-transparent! sm:min-h-85"
                emptyMessage="This try-on's 3D model isn't available."
                retryLabel="Retry 3D view"
              />
            ) : (
              <GlbViewer
                queryKey={["account", "avatar-glb"]}
                fetchGlb={() =>
                  getRuntimeProvider()
                    .getAvatarGlb()
                    .then((r) => r.blob)
                }
                className="h-full max-h-[min(64vh,720px)] min-h-70 w-full rounded-none! border-0! bg-transparent! sm:min-h-85"
                emptyMessage="Your 3D avatar isn't available."
                fallbackImageUrl={avatar.previewAssetUrl}
                retryLabel="Retry 3D view"
                onLoadStateChange={onAvatarViewStateChange}
              />
            )}
          </motion.div>
        </AnimatePresence>

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
                {tryOnState === "restoring"
                  ? "Restoring saved look"
                  : lastReadyRender
                    ? "Updating · previous look shown"
                    : "Draping garment"}
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="relative z-20 flex w-full justify-end px-3 pb-3 sm:px-4 sm:pb-4">
        <Link
          to="/profile/avatar"
          className="min-h-10 shrink-0 rounded-full bg-paper/55 px-3 py-2 text-[10px] font-medium text-muted backdrop-blur-sm transition-colors hover:bg-paper hover:text-ink"
        >
          Edit avatar
        </Link>
      </div>
    </div>
  );
}
