/**
 * Revision safety.
 *
 * The rule this module exists to enforce: **QA approves a revision, not a
 * garment.** Every edit to something try-on depends on — the capture set, the
 * reference sample, the size chart, the material, the category, the
 * construction blocks — bumps `sourceRevision`. QA freezes a snapshot of the
 * revision it passed. The public surface serves that snapshot and nothing
 * else.
 *
 * So a merchant can change a live garment's category at 4pm without a shopper
 * silently receiving an asset approved for a different product. The change
 * becomes a draft revision that has to be regenerated, reviewed and re-passed
 * before it can reach anyone.
 */
import type { Garment, GarmentSnapshot, GarmentStage } from "./types";

/** Stages where an upstream edit must send the garment back for rework. */
const UNAPPROVED_AFTER_EDIT: GarmentStage[] = ["merchant_review", "in_qa", "ready"];

export type RevisionState =
  /** Nothing has ever been approved. */
  | "never_approved"
  /** What QA approved is what the garment currently says. */
  | "current"
  /** There are edits after the approved revision — shoppers see the older one. */
  | "draft_ahead";

export function revisionState(g: Garment): RevisionState {
  if (!g.approved) return "never_approved";
  return g.approved.revision === g.sourceRevision ? "current" : "draft_ahead";
}

/** True when the generated asset was built from the garment's current data. */
export function assetIsCurrent(g: Garment): boolean {
  return g.assetRevision !== undefined && g.assetRevision === g.sourceRevision;
}

export interface RevisionNotice {
  tone: "info" | "warn";
  headline: string;
  detail: string;
}

/** What to tell the merchant about the gap between draft and approved. */
export function revisionNotice(g: Garment): RevisionNotice | null {
  const state = revisionState(g);
  if (state !== "draft_ahead" || !g.approved) return null;
  const serving = g.stage === "live";
  return {
    tone: serving ? "warn" : "info",
    headline: serving
      ? `Shoppers are seeing revision ${g.approved.revision}, not your latest edits.`
      : `Draft revision ${g.sourceRevision} is ahead of the approved revision ${g.approved.revision}.`,
    detail: serving
      ? "Your changes since QA are held as a draft. Regenerate and resubmit to QA to publish them; the approved version keeps serving until then."
      : "Send the draft back through QA to make it the published version.",
  };
}

/**
 * Applied by `editGarment` whenever a mutation touches try-on-relevant data.
 *
 * The garment does not lose its approval — it keeps serving the snapshot — but
 * the asset is marked stale and anything mid-flight (review, QA, ready) drops
 * back to `needs_data`, because approval of an older revision cannot carry
 * forward to a newer one.
 */
export function bumpRevision(g: Garment): { invalidatedStage: GarmentStage | null } {
  g.sourceRevision += 1;
  // The asset was built from the previous revision, so it no longer describes
  // this garment. `assetRevision` is left as-is (it records what was built),
  // and `assetIsCurrent` now reports false.
  if (UNAPPROVED_AFTER_EDIT.includes(g.stage)) {
    const from = g.stage;
    g.stage = "needs_data";
    return { invalidatedStage: from };
  }
  return { invalidatedStage: null };
}

/** Freeze everything QA just approved. This is what shoppers will be served. */
export function snapshot(g: Garment, approvedBy: string): GarmentSnapshot {
  return {
    revision: g.sourceRevision,
    assetRevision: g.assetRevision ?? g.sourceRevision,
    approvedAt: new Date().toISOString(),
    approvedBy,
    category: g.category,
    referenceSize: g.referenceSize,
    captureAccepted: [...g.capture.accepted],
    sizeChart: g.sizeChart.map((r) => ({ size: r.size, values: { ...r.values } })),
    sizeChartKind: g.sizeChartKind,
    sizeSource: g.sizeSource,
    fabricComposition: g.fabricComposition.map((f) => ({ ...f })),
    attributes: { ...g.attributes },
    silhouette: g.silhouette,
    fitNotes: g.fitNotes,
    variantIds: [...g.variantIds],
  };
}

/**
 * SKUs the approved revision covers. A variant Shopify added after approval is
 * deliberately not covered — nobody checked how the garment sizes onto it.
 */
export function approvedVariantIds(g: Garment): string[] {
  return g.approved?.variantIds ?? [];
}
