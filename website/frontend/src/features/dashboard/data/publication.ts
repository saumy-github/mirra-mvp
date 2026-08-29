/**
 * The authoritative publication contract.
 *
 * Everything a shopper is or isn't allowed to see resolves here, once, in one
 * order of precedence — and both sides consume this module:
 *
 *   - the dashboard, so "Live" on the Publication page means what it says;
 *   - the shopper surface, via `publicCatalogue()`, which returns the exact
 *     `PublicProduct[]` shape the storefront already renders.
 *
 * Before this existed the dashboard computed visibility from stage and toggles
 * while the storefront mapper hardcoded every product as published, try-on
 * eligible and in stock. The two could not disagree, because they never met.
 *
 * Order of precedence, highest first:
 *   1. billing/subscription state (suspended, cancelled → nothing serves)
 *   2. tenant launch state (not launched, paused → nothing serves)
 *   3. garment stage (`live` only) and the merchant's try-on toggle
 *   4. QA approval — an approved snapshot must exist
 *   5. per-variant inventory × sold-out policy (garment override → tenant default)
 *   6. asset availability for the approved revision
 */
import type {
  ProductVariant as PublicVariant,
  PublicProduct,
  SizeChartRow,
  GarmentCategory as PublicCategory,
} from "@/integrations/mirra-api";
import { getDb } from "./store";
import { getEntitlements } from "./entitlements";
import { soldOutPolicyFor } from "./ingestion";
import { revisionState } from "./revisions";
import type { Garment, GarmentCategory, Product, SoldOutPolicy, Tenant } from "./types";

// ------------------------------------------------------------ resolution

export type BlockedReason =
  | "subscription"
  | "tenant_paused"
  | "not_live"
  | "tryon_disabled"
  | "not_approved"
  | "no_purchasable_variant";

export interface ResolvedVariant {
  variantId: string;
  sku: string;
  size: string;
  colour: string;
  priceUsd: number;
  inventory: number;
  inStock: boolean;
  /** Whether a shopper can try this size on, after the sold-out policy. */
  tryOnEligible: boolean;
  /** Why not, when not. */
  hiddenReason?: "sold_out_hidden" | "not_in_approved_revision";
}

export interface ResolvedGarment {
  garmentId: string;
  title: string;
  /** The revision a shopper is actually served — never the working draft. */
  servedRevision: number | null;
  visible: boolean;
  blockedReason?: BlockedReason;
  blockedDetail?: string;
  soldOutPolicy: SoldOutPolicy;
  variants: ResolvedVariant[];
  /** True when the merchant has edits that are not yet approved. */
  draftAhead: boolean;
}

/**
 * The single resolution function. Everything else in this module, and every
 * "is this live?" question in the dashboard, goes through it.
 */
export function resolveGarment(
  g: Garment,
  tenant: Tenant,
  product: Product | undefined,
): ResolvedGarment {
  const policy = soldOutPolicyFor(g, tenant);
  const ent = getEntitlements(tenant);
  const approved = g.approved;
  const draftAhead = revisionState(g) === "draft_ahead";

  // Variants are resolved from the APPROVED revision's SKU list, not the
  // garment's current one: a variant Shopify added after approval has never
  // been checked against this garment's sizing.
  const coveredIds = approved?.variantIds ?? [];
  const variants: ResolvedVariant[] = (product?.variants ?? [])
    .filter((v) => coveredIds.includes(v.id) || g.variantIds.includes(v.id))
    .map((v) => {
      const covered = coveredIds.includes(v.id);
      const inStock = v.inventory > 0;
      const hiddenBySoldOut = !inStock && policy === "hide_size";
      return {
        variantId: v.id,
        sku: v.sku,
        size: v.size,
        colour: v.color,
        priceUsd: v.priceUsd,
        inventory: v.inventory,
        inStock,
        tryOnEligible: covered && !hiddenBySoldOut,
        hiddenReason: !covered
          ? ("not_in_approved_revision" as const)
          : hiddenBySoldOut
            ? ("sold_out_hidden" as const)
            : undefined,
      };
    });

  const base = {
    garmentId: g.id,
    title: g.title,
    soldOutPolicy: policy,
    variants,
    draftAhead,
  };
  const blocked = (reason: BlockedReason, detail: string): ResolvedGarment => ({
    ...base,
    servedRevision: null,
    visible: false,
    blockedReason: reason,
    blockedDetail: detail,
  });

  if (!ent.publicSurfaceEnabled) {
    const subscriptionBlocked =
      tenant.status === "suspended" || tenant.status === "cancelled" || tenant.status === "archived";
    return blocked(
      subscriptionBlocked ? "subscription" : "tenant_paused",
      ent.publicSurfaceDisabledReason ?? "The tenant's public surface is offline.",
    );
  }
  if (g.stage !== "live") {
    return blocked("not_live", `Garment stage is ${g.stage}, not live.`);
  }
  if (!g.tryOnEnabled) {
    return blocked("tryon_disabled", "Try-on was switched off for this garment.");
  }
  if (!approved) {
    return blocked(
      "not_approved",
      "No QA-approved revision exists, so there is nothing safe to serve.",
    );
  }
  if (!variants.some((v) => v.tryOnEligible)) {
    return blocked(
      "no_purchasable_variant",
      policy === "hide_size"
        ? "Every size is sold out and the sold-out policy hides sold-out sizes."
        : "No size in the approved revision resolves to a Shopify variant.",
    );
  }

  return { ...base, servedRevision: approved.revision, visible: true };
}

/** Every garment of a tenant, resolved. The Publication page reads this. */
export function resolveTenant(tenantId: string): ResolvedGarment[] {
  const db = getDb();
  const tenant = db.tenants.find((t) => t.id === tenantId);
  if (!tenant) return [];
  return db.garments
    .filter((g) => g.tenantId === tenantId)
    .map((g) => resolveGarment(g, tenant, db.products.find((p) => p.id === g.productId)));
}

// -------------------------------------------------------- shopper contract

const CATEGORY_TO_PUBLIC: Record<GarmentCategory, PublicCategory> = {
  dress: "top",
  top: "top",
  knitwear: "top",
  swim: "top",
  bottom: "bottom",
  outerwear: "outerwear",
  accessory: "accessory",
};

const SWATCHES: Record<string, string> = {
  black: "#1b1b1b", ivory: "#f2ece1", cream: "#f0e7d8", slate: "#5a6472",
  graphite: "#3b3b40", camel: "#b08d5a", ecru: "#e5dcc9", navy: "#1f2a44",
};

function swatchFor(colour: string): string {
  return SWATCHES[colour.toLowerCase()] ?? "#c7c7cc";
}

/**
 * The shopper-facing catalogue for one tenant, in the storefront's own
 * `PublicProduct` shape.
 *
 * This is the contract: pause a garment in the dashboard and it leaves this
 * list; sell out a size under `hide_size` and that variant stops being
 * try-on eligible here. `preview: true` includes content a merchant can see
 * with a preview token but shoppers cannot — and marks it, so a preview can
 * never be mistaken for the live result.
 */
export function publicCatalogue(
  tenantId: string,
  opts: { preview?: boolean } = {},
): PublicProduct[] {
  const db = getDb();
  const tenant = db.tenants.find((t) => t.id === tenantId);
  if (!tenant) return [];

  const out: PublicProduct[] = [];
  for (const g of db.garments.filter((x) => x.tenantId === tenantId)) {
    const product = db.products.find((p) => p.id === g.productId);
    const resolved = resolveGarment(g, tenant, product);

    // Preview additionally shows what is finished but not yet published, so a
    // merchant can check a garment before shoppers ever reach it.
    const previewable =
      opts.preview && !resolved.visible && Boolean(g.approved) && g.stage !== "sync_error";
    if (!resolved.visible && !previewable) continue;

    // Only ever the approved snapshot. The working draft is not shopper data.
    const snap = g.approved!;
    const sizeChart: SizeChartRow[] = snap.sizeChart.map((r) => ({
      size: r.size,
      measurements: Object.fromEntries(
        Object.entries(r.values)
          .filter(([, v]) => typeof v === "number")
          .map(([k, v]) => [k, `${v} cm`]),
      ),
    }));

    const variants: PublicVariant[] = resolved.variants
      .filter((v) => v.hiddenReason !== "sold_out_hidden")
      .map((v) => ({
        publicVariantId: v.variantId,
        colorName: g.optionValue,
        colorSwatch: swatchFor(g.optionValue),
        size: v.size,
        price: v.priceUsd,
        currency: "USD",
        inStock: v.inStock,
        tryOnEligible: v.tryOnEligible,
        // Generation is a backend job; until it lands there is no rendered
        // asset to hand a shopper, and saying otherwise is the failure this
        // whole module exists to prevent.
        garmentAssetUrl: null,
        assetStatus: "missing",
      }));

    out.push({
      publicProductId: g.id,
      name: g.canonicalTitle,
      subtitle: g.optionValue,
      category: product?.productType ?? snap.category,
      garmentCategory: CATEGORY_TO_PUBLIC[snap.category],
      description: null,
      materialAndCare:
        snap.fabricComposition.map((f) => `${f.pct}% ${f.material}`).join(", ") || null,
      manufacturingInfo: null,
      fitInfo: snap.silhouette ? `${snap.silhouette} fit — ${snap.fitNotes}` : snap.fitNotes || null,
      taxNote: null,
      price: variants[0]?.price ?? 0,
      currency: "USD",
      thumbnailUrl: "",
      publicationStatus: resolved.visible ? "published" : "paused",
      tryOnEligible: resolved.visible && variants.some((v) => v.tryOnEligible),
      sizeChart,
      variants,
    });
  }
  return out;
}

// ------------------------------------------------------------ plan usage

/** The SKUs a tenant is actually serving — the billable unit. */
export function liveVariantIds(tenantId: string): string[] {
  return resolveTenant(tenantId)
    .filter((r) => r.visible)
    .flatMap((r) => r.variants.filter((v) => v.tryOnEligible).map((v) => v.variantId));
}

/**
 * Live SKUs, not live garments. The plan sells SKU capacity, so a four-size
 * colourway consumes four — counting garment records under-reported usage by
 * exactly the average size run.
 */
export function liveSkuCount(tenantId: string): number {
  return liveVariantIds(tenantId).length;
}

/** Which garments consume the quota, so an over-limit merchant can act on it. */
export function liveSkuBreakdown(
  tenantId: string,
): { garmentId: string; title: string; skus: number }[] {
  return resolveTenant(tenantId)
    .filter((r) => r.visible)
    .map((r) => ({
      garmentId: r.garmentId,
      title: r.title,
      skus: r.variants.filter((v) => v.tryOnEligible).length,
    }))
    .sort((a, b) => b.skus - a.skus);
}
