import { AnimatePresence, motion } from "motion/react";
import type { GarmentCategory } from "@/integrations/mirra-api/types";
import { useReducedMotion } from "@/hooks/use-reduced-motion";

export interface StageLayer {
  category: GarmentCategory | "base";
  assetUrl: string;
  key: string;
}

/** Layer stacking order on the figure, back to front. */
const ORDER: Record<string, number> = {
  base: 0,
  bottom: 1,
  footwear: 2,
  top: 3,
  outerwear: 4,
  accessory: 5,
};

const FIGURE_SPRING = {
  type: "spring" as const,
  stiffness: 360,
  damping: 38,
  mass: 0.9,
};

/**
 * The composed avatar figure: the mannequin plus garment layers, all drawn
 * in one shared 400×800 space. Never slimmed, never beautified.
 *
 * This is "demo mode" — flat image layering, not a physics simulation. Real
 * 3D rendering (React Three Fiber + GLB assets from the CLO3D pipeline, per
 * website/frontend-structure-plan.md) is future work once those assets
 * exist; this component is the honest placeholder for that, matching the
 * source app's own DemoModeNotice pattern.
 */
export function AvatarFigure({
  previewAssetUrl,
  layers,
  glow = true,
  className = "",
  alt,
}: {
  previewAssetUrl: string;
  layers: StageLayer[];
  glow?: boolean;
  className?: string;
  alt: string;
}) {
  const reduceMotion = useReducedMotion();
  const sorted = [...layers].sort((a, b) => (ORDER[a.category] ?? 9) - (ORDER[b.category] ?? 9));

  return (
    <motion.div
      layout
      className={`relative isolate aspect-1/2 ${className}`}
      role="img"
      aria-label={alt}
      transition={reduceMotion ? { duration: 0 } : FIGURE_SPRING}
    >
      {glow && (
        <>
          <div
            aria-hidden
            className="absolute bottom-[-1.5%] left-1/2 h-[5%] w-[72%] -translate-x-1/2 rounded-[50%] bg-ink/15 blur-xl"
          />
          <div
            aria-hidden
            className="absolute top-1/2 left-1/2 -z-10 h-[74%] w-[145%] -translate-x-1/2 -translate-y-1/2 rounded-[50%] blur-3xl"
            style={{
              background:
                "radial-gradient(closest-side, rgba(233,221,214,0.86) 0%, rgba(233,221,214,0.28) 46%, rgba(233,221,214,0) 75%)",
            }}
          />
        </>
      )}
      <img
        src={previewAssetUrl}
        alt=""
        className="absolute inset-0 h-full w-full object-contain select-none"
        draggable={false}
        decoding="async"
      />
      <AnimatePresence initial={false} mode="popLayout">
        {sorted.map((layer) => (
          <motion.img
            key={layer.key}
            layout
            src={layer.assetUrl}
            alt=""
            draggable={false}
            decoding="async"
            className="absolute inset-0 h-full w-full object-contain select-none"
            initial={reduceMotion ? false : { opacity: 0, scale: 0.985 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 1.008 }}
            transition={reduceMotion ? { duration: 0.01 } : FIGURE_SPRING}
          />
        ))}
      </AnimatePresence>
    </motion.div>
  );
}
