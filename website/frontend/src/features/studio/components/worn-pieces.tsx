import type { GarmentCategory, OutfitPiece } from "../types";

/**
 * The rest of the outfit currently on the figure. Pieces held by a Signature
 * Look carry a lock the shopper can release — that release is the only way a
 * locked base comes off, so it stays visible rather than hidden in a menu.
 */
export function WornPieces({
  pieces,
  onUnlock,
}: {
  pieces: OutfitPiece[];
  onUnlock: (category: GarmentCategory) => void;
}) {
  if (pieces.length === 0) return null;

  return (
    <section aria-labelledby="worn-pieces-heading">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="worn-pieces-heading" className="eyebrow">
          Also on your avatar
        </h2>
        <span className="text-[10px] tracking-[0.1em] text-ash uppercase">
          {pieces.length} paired
        </span>
      </div>

      <ul className="mt-3.5 flex gap-2.5">
        {pieces.map((piece) => (
          <li key={piece.category} className="relative">
            <span
              title={piece.name}
              className="block size-16 overflow-hidden rounded-thumb border border-hairline bg-bone"
            >
              <img
                src={piece.thumbnailUrl}
                alt={piece.name}
                draggable={false}
                className="size-full object-cover select-none"
              />
            </span>
            {piece.locked && (
              <button
                type="button"
                onClick={() => onUnlock(piece.category)}
                aria-label={`Unlock ${piece.name}, kept by your Signature Look`}
                title="Kept by your Signature Look — release"
                className="absolute -top-1.5 -right-1.5 flex size-6 items-center justify-center rounded-full border border-hairline bg-vellum text-graphite transition-colors hover:border-graphite"
              >
                <svg
                  width="9"
                  height="9"
                  viewBox="0 0 12 12"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.1"
                  strokeLinecap="round"
                  aria-hidden
                >
                  <rect x="2.5" y="5.5" width="7" height="5" rx="1" />
                  <path d="M4.2 5.5V4a1.8 1.8 0 0 1 3.6 0" />
                </svg>
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
