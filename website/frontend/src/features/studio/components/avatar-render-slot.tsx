import { motion } from "motion/react";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { AvatarFigure, type StageLayer } from "./avatar-figure";
import { isRenderableAsset } from "../lib/assets";
import type { OutfitPiece } from "../types";

const SLOT_TRANSITION = { duration: 0.42, ease: [0.22, 0.8, 0.24, 1] as const };

/**
 * Where the backend's try-on output goes.
 *
 * One job: hold a correctly proportioned, correctly placed space for a
 * rendered figure, and look composed while that space is empty. When the
 * avatar/garment pipeline starts returning real assets, `isRenderableAsset`
 * turns true and the composed figure renders here with no layout change.
 *
 * Until then it shows a neutral mannequin — never a mocked-up try-on.
 */
export function AvatarRenderSlot({
  previewAssetUrl,
  pieces,
  zoom,
  alt,
}: {
  previewAssetUrl: string;
  pieces: OutfitPiece[];
  zoom: number;
  alt: string;
}) {
  const reduceMotion = useReducedMotion();

  const layers: StageLayer[] = pieces
    .filter((piece) => isRenderableAsset(piece.assetUrl))
    .map((piece) => ({
      category: piece.category,
      assetUrl: piece.assetUrl,
      key: `${piece.category}-${piece.variantPublicId}`,
    }));

  const hasRender = isRenderableAsset(previewAssetUrl) || layers.length > 0;

  return (
    <motion.div
      className="flex h-full w-full items-center justify-center will-change-transform"
      animate={{ scale: zoom }}
      transition={reduceMotion ? { duration: 0.01 } : { duration: 0.32, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {hasRender ? (
        <AvatarFigure
          previewAssetUrl={previewAssetUrl}
          layers={layers}
          glow={false}
          className="h-full max-h-[min(64vh,720px)]"
          alt={alt}
        />
      ) : (
        <motion.div
          className="flex h-full max-h-[min(64vh,720px)] flex-col items-center justify-center"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={reduceMotion ? { duration: 0.01 } : SLOT_TRANSITION}
          role="img"
          aria-label={alt}
        >
          <span className="flex min-h-52 min-w-0 flex-1 items-center justify-center">
            <Mannequin className="h-full w-auto" />
          </span>
          <p className="mt-6 text-center text-[11px] leading-relaxed tracking-[0.08em] text-ash">
            See yourself before you decide.
          </p>
        </motion.div>
      )}
    </motion.div>
  );
}

/** A neutral form: no face, no styling, no implied body type beyond posture. */
function Mannequin({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 470" className={className} aria-hidden>
      <defs>
        <linearGradient id="mirra-mannequin" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#eae5dc" />
          <stop offset="100%" stopColor="#dbd4c9" />
        </linearGradient>
      </defs>

      <ellipse cx="110" cy="452" rx="56" ry="6" fill="rgba(23,19,15,0.05)" />

      <g fill="url(#mirra-mannequin)">
        <ellipse cx="110" cy="46" rx="19" ry="23" />
        <path
          d="M78 86 C78 79 84 76 92 75 L128 75 C136 76 142 79 142 86
             L137 152 C136 164 138 176 139 188 L140 226
             C140 234 134 238 126 238 L94 238 C86 238 80 234 80 226
             L81 188 C82 176 84 164 83 152 Z"
        />
      </g>

      <g fill="none" stroke="url(#mirra-mannequin)" strokeLinecap="round" strokeLinejoin="round">
        <path d="M110 64 v14" strokeWidth="17" />
        <path d="M80 92 C68 114 62 158 64 204" strokeWidth="15" />
        <path d="M140 92 C152 114 158 158 156 204" strokeWidth="15" />
        <path d="M97 234 C93 300 92 372 95 428" strokeWidth="25" />
        <path d="M123 234 C127 300 128 372 125 428" strokeWidth="25" />
      </g>
    </svg>
  );
}
