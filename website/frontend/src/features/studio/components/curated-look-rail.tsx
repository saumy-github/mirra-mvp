import { motion } from "motion/react";
import type { OutfitLayer } from "@/stores/studio-store";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { PinchCarousel } from "./pinch-carousel";

const CONTROL_SPRING = {
  type: "spring" as const,
  stiffness: 480,
  damping: 38,
  mass: 0.72,
};

export function CuratedLookRail({
  layers,
  onUnlockLayer,
}: {
  layers: OutfitLayer[];
  onUnlockLayer: (category: OutfitLayer["category"]) => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <PinchCarousel
      items={layers}
      getKey={(layer) => layer.category}
      getLabel={(layer) => layer.name}
      axis="x"
      ariaLabel="The curated look"
      stride={102}
      debounceMs={240}
      className="mt-3 h-31 outline-none focus-visible:ring-2 focus-visible:ring-ink/50"
      viewportClassName="min-h-0! rounded-(--radius-control) border border-white/60"
      renderItem={(layer, { active }) => (
        <article
          className={`relative w-21 rounded-(--radius-compact) border bg-surface/82 p-1.5 text-center shadow-[0_10px_25px_-20px_rgba(33,31,28,0.48)] ${
            active ? "border-ink/65" : "border-white/80"
          }`}
        >
          <img
            src={layer.thumbnailUrl}
            alt=""
            draggable={false}
            className="mx-auto aspect-5/6 w-full object-contain"
          />
          <p className="mt-0.5 truncate text-[9px] font-medium text-muted" title={layer.name}>
            {layer.name}
          </p>
          {layer.locked && (
            <motion.button
              type="button"
              tabIndex={active ? 0 : -1}
              onClick={() => onUnlockLayer(layer.category)}
              aria-label={`Unlock ${layer.name} (kept by your Signature Look)`}
              title="Locked by your Signature Look — click to unlock"
              className="absolute top-1 right-1 flex size-8 items-center justify-center rounded-(--radius-compact) border border-white/40 bg-ink text-[9px] text-canvas shadow-sm"
              whileTap={reduceMotion ? undefined : { scale: 0.88 }}
              transition={CONTROL_SPRING}
            >
              <span aria-hidden>🔒</span>
            </motion.button>
          )}
        </article>
      )}
    />
  );
}
