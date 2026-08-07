/**
 * The fitting room's own vocabulary.
 *
 * The wire contract lives in `@/integrations/mirra-api/types` — this module
 * is the UI-facing layer on top of it: aliases where the wire type is already
 * right, and the few concepts the room needs that the catalogue endpoint
 * doesn't model yet (a merchant, a resolved size option, a try-on asset).
 *
 * Nothing here is specific to a demo product. Components take these types,
 * never a hardcoded piece.
 */

import type {
  AssetStatus,
  GarmentCategory,
  ProductVariant,
  PublicProduct,
} from "@/integrations/mirra-api/types";
import type { HangerEntry, OutfitLayer } from "@/lib/hanger";
import type { StudioCartItem } from "@/stores/studio-store";

export type {
  AssetStatus,
  GarmentCategory,
  ProductVariant,
  SignatureLook,
  SignatureLookLayer,
  TryOnState,
} from "@/integrations/mirra-api/types";

/**
 * The store whose catalogue is being browsed. The pilot serves a single
 * merchant, so the catalogue endpoint doesn't return one yet — every consumer
 * treats it as optional and the UI simply omits merchant chrome when absent.
 * Mirra is not a marketplace in this flow: recommendations never cross
 * merchants (see `sameMerchant`).
 */
export interface Merchant {
  merchantId: string;
  name: string;
  /** Short label for the header, e.g. "Atelier Noir". Falls back to `name`. */
  displayName?: string;
  logoUrl?: string | null;
}

/** A catalogue product as the room consumes it. */
export type Product = PublicProduct & {
  merchantId?: string | null;
  merchant?: Merchant | null;
};

/** One selectable size, resolved against a chosen colour. */
export interface SizeOption {
  size: string;
  variant: ProductVariant;
  inStock: boolean;
}

/** How a variant's availability is presented. */
export type InventoryStatus = "in-stock" | "low-stock" | "out-of-stock";

/**
 * A garment asset the try-on engine can drape. `status` is the engine's, not
 * the catalogue's — a published product may still be "processing".
 */
export interface TryOnAsset {
  assetUrl: string | null;
  status: AssetStatus;
  category: GarmentCategory;
}

/** One garment currently on the avatar. */
export type OutfitPiece = OutfitLayer;

/** One entry in The Hanger — a previously rendered look, restorable. */
export type HangerItem = HangerEntry;

/** One line in the local bag. */
export type CartItem = StudioCartItem;

// ── helpers ───────────────────────────────────────────────────────────

export function inventoryStatusOf(variant: ProductVariant | null): InventoryStatus {
  if (!variant) return "out-of-stock";
  return variant.inStock ? "in-stock" : "out-of-stock";
}

/**
 * True when two products belong to the same store. With no merchant on either
 * side we're inside a single-merchant catalogue, which is still "same".
 */
export function sameMerchant(a: Product, b: Product): boolean {
  if (!a.merchantId && !b.merchantId) return true;
  return a.merchantId === b.merchantId;
}

/** The distinct colours of a product, first variant per colour. */
export function colorsOf(product: Product): ProductVariant[] {
  const seen = new Map<string, ProductVariant>();
  for (const variant of product.variants) {
    if (!seen.has(variant.colorName)) seen.set(variant.colorName, variant);
  }
  return [...seen.values()];
}

/** The sizes available in a given colour, in catalogue order. */
export function sizeOptionsOf(product: Product, colorName: string | null): SizeOption[] {
  const color = colorName ?? product.variants[0]?.colorName;
  return product.variants
    .filter((variant) => variant.colorName === color)
    .map((variant) => ({ size: variant.size, variant, inStock: variant.inStock }));
}

/** The full outfit's total, used by the tray when more than one piece is worn. */
export function lookTotal(pieces: OutfitPiece[]): number {
  return pieces.reduce((sum, piece) => sum + piece.price, 0);
}
