import type { GarmentCategory, TryOnRender } from "@/integrations/mirra-api/types";

/**
 * The Hanger — the session's try-on history rail. An LRU of previously
 * rendered looks so returning to an earlier garment restores the cached
 * result instead of re-running the engine.
 */

export type HangerEntryStatus = "current" | "cached" | "expired" | "failed";

/** One garment worn on the figure (shared by the studio store and Hanger). */
export interface OutfitLayer {
  category: GarmentCategory;
  productPublicId: string;
  variantPublicId: string;
  assetUrl: string;
  thumbnailUrl: string;
  name: string;
  price: number;
  size: string | null;
  /** Locked by an applied Signature Look. */
  locked: boolean;
}

export interface HangerEntry {
  id: string;
  productPublicId: string;
  variantPublicId: string;
  size: string | null;
  layers: TryOnRender["layers"];
  avatarProfileVersion: number;
  tryOnSessionId: string;
  renderId: string;
  renderedAssetUrl: string | null;
  thumbnailUrl: string;
  productName: string;
  generatedAt: string;
  engineVersion: string;
  status: HangerEntryStatus;
  /**
   * Full outfit snapshot (client-side enrichment of `layers`) so a restore
   * can rebuild the product panel and totals without re-fetching.
   */
  outfit?: Partial<Record<GarmentCategory, OutfitLayer>>;
}

export const DEFAULT_HANGER_CAPACITY = 10;

/** Push an entry, most-recent first, evicting the least recent past capacity. */
export function pushHangerEntry(
  entries: HangerEntry[],
  entry: HangerEntry,
  capacity: number = DEFAULT_HANGER_CAPACITY,
): HangerEntry[] {
  const deduped = entries.filter((e) => e.id !== entry.id);
  return [entry, ...deduped].slice(0, capacity);
}

/** Move a restored entry to the front (LRU touch). */
export function touchHangerEntry(entries: HangerEntry[], id: string): HangerEntry[] {
  const hit = entries.find((e) => e.id === id);
  if (!hit) return entries;
  return [hit, ...entries.filter((e) => e.id !== id)];
}

/**
 * A cached result is only restorable when it was rendered for the same
 * avatar version with a compatible engine; otherwise it must be re-rendered.
 */
export function isEntryRestorable(
  entry: Pick<HangerEntry, "avatarProfileVersion" | "engineVersion" | "status">,
  current: { avatarProfileVersion: number; engineVersion: string },
): boolean {
  if (entry.status === "failed") return false;
  if (entry.avatarProfileVersion !== current.avatarProfileVersion) return false;
  if (entry.engineVersion !== current.engineVersion) return false;
  return true;
}

export function hangerEntryId(
  productPublicId: string,
  variantPublicId: string,
  size: string | null,
  layers: TryOnRender["layers"],
): string {
  const layerSig = Object.entries(layers)
    .map(([cat, l]) => `${cat}:${l?.variantPublicId ?? ""}`)
    .sort()
    .join("|");
  return `${productPublicId}::${variantPublicId}::${size ?? "-"}::${layerSig}`;
}

/**
 * Signature-look compatibility. Locked layers stay on while compatible
 * products are tried; the active product may only replace its own category,
 * and only when that layer isn't locked by the user.
 */
export function signatureLookCompatibility(
  lookCategories: GarmentCategory[],
  lockedCategories: GarmentCategory[],
  productCategory: GarmentCategory,
): { compatible: boolean; reason: "replaces_layer" | "adds_layer" | "layer_locked" } {
  if (lockedCategories.includes(productCategory)) {
    return { compatible: false, reason: "layer_locked" };
  }
  if (lookCategories.includes(productCategory)) {
    return { compatible: true, reason: "replaces_layer" };
  }
  return { compatible: true, reason: "adds_layer" };
}
