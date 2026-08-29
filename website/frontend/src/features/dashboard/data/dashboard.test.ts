/**
 * The dashboard's safety properties, as tests.
 *
 * Everything here is a rule that used to be enforced only by a screen, or not
 * at all: a garment reaching QA, a chart being "complete", a Sales user
 * reaching an Owner control, an edit after approval changing what a shopper
 * sees. Those are exactly the things a UI refactor breaks without noticing.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

// The session layer reads localStorage; the store's HMR hook reads import.meta.
const store = new Map<string, string>();
vi.stubGlobal("window", {
  localStorage: {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
  },
});

import { getDb, resetDb } from "./store";
import { signIn, signOut, startViewAs } from "./session";
import { can, canInternal } from "./rbac";
import { MERCHANT_TRANSITIONS, canMerchantMove, requirements } from "./ingestion";
import { validateChart, parseChart, toCm, gradeFromRules, blankRows } from "./size-chart";
import { bumpRevision, revisionState, snapshot } from "./revisions";
import { publicCatalogue, resolveGarment, liveSkuCount } from "./publication";
import { dailyMetrics, totals, windowStart } from "./queries";
import {
  completeGenerationAction,
  qaDecisionAction,
  setGarmentStageAction,
  submitForMerchantReviewAction,
  updateGarmentAction,
} from "./actions";
import type { Garment, SizeRow } from "./types";

const ATELIER = "t_atelier";

function db() {
  return getDb();
}
function tenant() {
  return db().tenants.find((t) => t.id === ATELIER)!;
}
function firstLive(): Garment {
  return db().garments.find((g) => g.tenantId === ATELIER && g.stage === "live")!;
}
function productFor(g: Garment) {
  return db().products.find((p) => p.id === g.productId);
}

beforeEach(() => {
  store.clear();
  resetDb();
  signIn("u_owner");
});

// --------------------------------------------------------------- lifecycle

describe("garment lifecycle", () => {
  it("routes needs_data to QA only through the merchant's own review", () => {
    expect(canMerchantMove("needs_data", "in_qa")).toBe(false);
    expect(canMerchantMove("needs_data", "merchant_review")).toBe(true);
    expect(canMerchantMove("merchant_review", "in_qa")).toBe(true);
  });

  it("never lets a merchant grant themselves QA approval", () => {
    expect(MERCHANT_TRANSITIONS.in_qa).toEqual([]);
    const g = db().garments.find((x) => x.stage === "in_qa")!;
    const res = setGarmentStageAction(g.id, "ready");
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/only the mirra qa team/i);
  });

  it("a complete garment can actually reach QA — the dead end is gone", () => {
    const g = firstLive();
    // Walk it back to needs_data the way generation leaves it.
    g.stage = "needs_data";
    expect(requirements(g, productFor(g)).filter((r) => r.blocking && !r.complete)).toEqual([]);

    expect(submitForMerchantReviewAction(g.id).ok).toBe(true);
    expect(g.stage).toBe("merchant_review");
    expect(setGarmentStageAction(g.id, "in_qa").ok).toBe(true);
    expect(g.stage).toBe("in_qa");
  });

  it("refuses to send an incomplete garment to review, and says what's missing", () => {
    const g = db().garments.find((x) => x.stage === "needs_data")!;
    const res = submitForMerchantReviewAction(g.id);
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/still missing/i);
  });

  it("generation lands a finished garment in review, not back in needs_data", () => {
    const g = firstLive();
    g.stage = "processing";
    expect(completeGenerationAction(g.id).ok).toBe(true);
    expect(g.stage).toBe("merchant_review");
    expect(g.assetRevision).toBe(g.sourceRevision);
  });
});

// -------------------------------------------------------------- validation

describe("size chart validation", () => {
  const sizes = ["S", "M", "L"];

  it("rejects a chart with rows but no usable measurements", () => {
    const empty: SizeRow[] = sizes.map((size) => ({ size, values: {} }));
    const v = validateChart(empty, "top", sizes);
    expect(v.valid).toBe(false);
    expect(v.issues.every((i) => i.problem === "missing")).toBe(true);
  });

  it("flags a size a Shopify variant needs but the chart omits", () => {
    const rows = blankRows(["S", "M"], "top").map((r) => ({
      size: r.size,
      values: { chest: 50, shoulder: 42, length: 68, sleeve: 60, armhole: 22 },
    }));
    expect(validateChart(rows, "top", sizes).missingSizes).toEqual(["L"]);
  });

  it("catches inches typed into a centimetre column", () => {
    const rows = [{ size: "S", values: { chest: 20, shoulder: 16, length: 27, sleeve: 24, armhole: 9 } }];
    const v = validateChart(rows, "top", ["S"]);
    expect(v.issues.some((i) => i.problem === "implausible")).toBe(true);
  });

  it("converts units on the way in", () => {
    expect(toCm(20, "in")).toBe(50.8);
    expect(toCm(50, "cm")).toBe(50);
  });

  it("parses a real CSV and reports what it could not map", () => {
    const csv = "Size,Chest,Shoulder,Length,Sleeve,Fabric\nS,49,41,68,60,cotton\nM,52,43,70,61,cotton";
    const parsed = parseChart(csv, "top", "cm");
    expect("error" in parsed).toBe(false);
    if ("error" in parsed) return;
    expect(parsed.rowCount).toBe(2);
    expect(parsed.rows[0].values.chest).toBe(49);
    expect(parsed.unmappedColumns).toContain("Fabric");
    // The category needs an armhole and the file had no column for it.
    expect(parsed.unmatchedFields).toContain("Armhole");
  });

  it("leaves a blank cell blank rather than inventing a zero", () => {
    const parsed = parseChart("Size,Chest,Shoulder\nS,49,\nM,52,43", "top", "cm");
    if ("error" in parsed) throw new Error(parsed.error);
    expect(parsed.rows[0].values.shoulder).toBeUndefined();
  });

  it("grades from rules only where a rule exists", () => {
    const ref: SizeRow = { size: "M", values: { chest: 52, shoulder: 43 } };
    const graded = gradeFromRules(ref, ["S", "M", "L"], { chest: 4 });
    expect(graded.find((r) => r.size === "S")!.values.chest).toBe(48);
    expect(graded.find((r) => r.size === "L")!.values.chest).toBe(56);
    // No rule for shoulder means no honest way to grade it.
    expect(graded.find((r) => r.size === "L")!.values.shoulder).toBeUndefined();
  });

  it("treats an unusable chart as an incomplete requirement", () => {
    const g = firstLive();
    g.sizeChart = g.sizeChart.map((r) => ({ ...r, values: {} }));
    const sizing = requirements(g, productFor(g)).find((r) => r.key === "sizing")!;
    expect(sizing.complete).toBe(false);
  });
});

// ----------------------------------------------------------- authorization

describe("authorization", () => {
  it("gives each brand role only its own capabilities", () => {
    expect(can("brand_viewer", "catalogue.view")).toBe(true);
    expect(can("brand_viewer", "publication.manage")).toBe(false);
    expect(can("brand_merchandiser", "billing.manage")).toBe(false);
    expect(can("brand_owner", "billing.manage")).toBe(true);
  });

  it("does not treat internal roles as blanket brand access", () => {
    // This shortcut is what let console access imply tenant control.
    expect(can("mirra_admin", "publication.manage")).toBe(false);
    expect(can("mirra_sales", "catalogue.view")).toBe(false);
  });

  it("keeps Sales out of tenant lifecycle, support and QA", () => {
    expect(canInternal("mirra_sales", "console.leads.manage")).toBe(true);
    expect(canInternal("mirra_sales", "console.tenants.manage")).toBe(false);
    expect(canInternal("mirra_sales", "console.support.manage")).toBe(false);
    expect(canInternal("mirra_sales", "console.qa.decide")).toBe(false);
    expect(canInternal("mirra_sales", "viewas.elevate")).toBe(false);
  });

  it("view-as never grants more than the seat it impersonates", async () => {
    signOut();
    signIn("u_sales");
    const sales = db().users.find((u) => u.id === "u_sales")!;
    startViewAs(sales, ATELIER, "Demo walkthrough for a prospect");

    const { getSession } = await import("./session");
    const s = getSession()!;
    // Read-only by default — and never `brand_owner`, whatever the console rank.
    expect(s.role).toBe("brand_viewer");
    expect(can(s.role, "publication.manage")).toBe(false);
    expect(can(s.role, "billing.manage")).toBe(false);
  });

  it("blocks a read-only support session from taking a page offline", () => {
    signOut();
    signIn("u_support");
    const support = db().users.find((u) => u.id === "u_support")!;
    startViewAs(support, ATELIER, "Investigating ticket tk_1");
    const g = firstLive();
    const res = setGarmentStageAction(g.id, "paused");
    expect(res.ok).toBe(false);
  });

  it("only elevates to a Merchandiser seat, never an Owner one", async () => {
    signOut();
    signIn("u_admin");
    const admin = db().users.find((u) => u.id === "u_admin")!;
    startViewAs(admin, ATELIER, "Fixing a broken size chart", "write");
    const { getSession } = await import("./session");
    const s = getSession()!;
    expect(s.role).toBe("brand_merchandiser");
    expect(can(s.role, "catalogue.edit")).toBe(true);
    expect(can(s.role, "billing.manage")).toBe(false);
    expect(can(s.role, "team.manage")).toBe(false);
  });

  it("requires a reason to enter a workspace", () => {
    signOut();
    signIn("u_admin");
    const admin = db().users.find((u) => u.id === "u_admin")!;
    expect(() => startViewAs(admin, ATELIER, "x")).toThrow(/REASON/);
  });
});

// ------------------------------------------------------------- revisioning

describe("revision safety", () => {
  it("marks a garment's draft as ahead once it is edited after approval", () => {
    const g = firstLive();
    expect(revisionState(g)).toBe("current");
    bumpRevision(g);
    expect(revisionState(g)).toBe("draft_ahead");
  });

  it("returns anything mid-flight to needs_data when its inputs change", () => {
    const g = firstLive();
    g.stage = "in_qa";
    expect(bumpRevision(g).invalidatedStage).toBe("in_qa");
    expect(g.stage).toBe("needs_data");
  });

  it("keeps serving the approved revision after a live garment is edited", () => {
    const g = firstLive();
    const approvedChest = g.approved!.sizeChart[0]?.values.chest ?? g.approved!.sizeChart[0]?.values.bust;

    // A category change is a try-on-relevant edit made on a live garment.
    const form = new FormData();
    form.set("category", g.category === "top" ? "outerwear" : "top");
    form.set("fitNotes", g.fitNotes);
    form.set("careNotes", g.careNotes);
    expect(updateGarmentAction(g.id, form).ok).toBe(true);

    // The working record changed; what shoppers get did not.
    expect(revisionState(g)).toBe("draft_ahead");
    expect(g.sizeChart).toEqual([]); // incompatible chart dropped, not reinterpreted
    const served = g.approved!.sizeChart[0];
    expect(served.values.chest ?? served.values.bust).toBe(approvedChest);

    const resolved = resolveGarment(g, tenant(), productFor(g));
    expect(resolved.visible).toBe(true);
    expect(resolved.servedRevision).toBe(g.approved!.revision);
    expect(resolved.servedRevision).toBeLessThan(g.sourceRevision);
  });

  it("QA approval freezes the revision it actually checked", () => {
    signOut();
    signIn("u_admin");
    const g = db().garments.find((x) => x.stage === "in_qa")!;
    const at = g.sourceRevision;
    expect(qaDecisionAction(g.id, "pass").ok).toBe(true);
    expect(g.stage).toBe("ready");
    expect(g.approved!.revision).toBe(at);
  });

  it("refuses a QA rejection with no actionable finding", () => {
    signOut();
    signIn("u_admin");
    const g = db().garments.find((x) => x.stage === "in_qa")!;
    const res = qaDecisionAction(g.id, "fail", []);
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/finding/i);
  });

  it("records structured findings against the revision they were raised on", () => {
    signOut();
    signIn("u_admin");
    const g = db().garments.find((x) => x.stage === "in_qa")!;
    const rev = g.sourceRevision;
    qaDecisionAction(g.id, "fail", [
      {
        area: "capture",
        severity: "blocker",
        view: "left",
        detail: "The lower hem is outside the frame.",
        instruction: "Reshoot the left view with the whole garment in frame.",
      },
    ]);
    expect(g.stage).toBe("needs_data");
    expect(g.qaFindings[0].revision).toBe(rev);
    expect(g.qaFindings[0].instruction).toMatch(/reshoot/i);
  });

  it("will not publish a garment that has never been approved", () => {
    const g = db().garments.find((x) => x.tenantId === ATELIER && x.stage === "needs_data")!;
    g.stage = "ready";
    g.approved = undefined;
    const res = setGarmentStageAction(g.id, "live");
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/no qa-approved revision/i);
  });
});

// ------------------------------------------------- publication contract

describe("publication contract", () => {
  it("pausing a garment removes it from the shopper catalogue", () => {
    const g = firstLive();
    expect(publicCatalogue(ATELIER).some((p) => p.publicProductId === g.id)).toBe(true);
    expect(setGarmentStageAction(g.id, "paused").ok).toBe(true);
    expect(publicCatalogue(ATELIER).some((p) => p.publicProductId === g.id)).toBe(false);
  });

  it("pausing the whole page empties the catalogue", () => {
    expect(publicCatalogue(ATELIER).length).toBeGreaterThan(0);
    tenant().launchStatus = "paused";
    expect(publicCatalogue(ATELIER)).toEqual([]);
  });

  it("a suspended subscription serves nothing, whatever the garment says", () => {
    const g = firstLive();
    tenant().status = "suspended";
    const resolved = resolveGarment(g, tenant(), productFor(g));
    expect(resolved.visible).toBe(false);
    expect(resolved.blockedReason).toBe("subscription");
  });

  it("honours the sold-out policy per variant", () => {
    const g = firstLive();
    const product = productFor(g)!;
    const covered = product.variants.filter((v) => g.approved!.variantIds.includes(v.id));
    covered[0].inventory = 0;

    tenant().defaults.soldOutPolicy = "keep_tryon";
    let sizes = publicCatalogue(ATELIER).find((p) => p.publicProductId === g.id)!.variants;
    expect(sizes.some((v) => v.size === covered[0].size)).toBe(true);

    // Per-garment override beats the store default.
    g.soldOutPolicy = "hide_size";
    sizes = publicCatalogue(ATELIER).find((p) => p.publicProductId === g.id)!.variants;
    expect(sizes.some((v) => v.size === covered[0].size)).toBe(false);
  });

  it("hides a garment entirely when every covered size is gone under hide_size", () => {
    const g = firstLive();
    const product = productFor(g)!;
    for (const v of product.variants) v.inventory = 0;
    g.soldOutPolicy = "hide_size";
    const resolved = resolveGarment(g, tenant(), product);
    expect(resolved.visible).toBe(false);
    expect(resolved.blockedReason).toBe("no_purchasable_variant");
  });

  it("never serves a variant the approved revision doesn't cover", () => {
    const g = firstLive();
    const product = productFor(g)!;
    const extra = { ...product.variants[0], id: "v_new_after_approval", sku: "NEW-1", size: "XXL" };
    product.variants.push(extra);
    g.variantIds.push(extra.id);
    const resolved = resolveGarment(g, tenant(), product);
    const added = resolved.variants.find((v) => v.variantId === extra.id)!;
    expect(added.tryOnEligible).toBe(false);
    expect(added.hiddenReason).toBe("not_in_approved_revision");
  });

  it("counts live SKUs by variant, not by garment", () => {
    const visible = publicCatalogue(ATELIER);
    const skus = visible.reduce((n, p) => n + p.variants.filter((v) => v.tryOnEligible).length, 0);
    expect(liveSkuCount(ATELIER)).toBe(skus);
    expect(liveSkuCount(ATELIER)).toBeGreaterThan(visible.length);
  });

  it("enforces the plan's SKU limit in SKUs", () => {
    const g = db().garments.find((x) => x.tenantId === ATELIER && x.stage === "ready")
      ?? db().garments.find((x) => x.tenantId === ATELIER && x.stage === "paused")!;
    g.stage = "ready";
    g.approved = g.approved ?? snapshot(g, "test");
    const plan = db().plans.find((p) => p.id === tenant().billing.planId)!;
    plan.skuLimit = liveSkuCount(ATELIER); // exactly full
    const res = setGarmentStageAction(g.id, "live");
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/plan limit/i);
  });

  it("serves the approved snapshot's material, not the working record's", () => {
    const g = firstLive();
    const approvedMaterial = g.approved!.fabricComposition.map((f) => `${f.pct}% ${f.material}`).join(", ");
    g.fabricComposition = [{ material: "Polyester", pct: 100 }];
    const p = publicCatalogue(ATELIER).find((x) => x.publicProductId === g.id)!;
    expect(p.materialAndCare).toBe(approvedMaterial);
    expect(p.materialAndCare).not.toContain("Polyester");
  });
});

// ------------------------------------------------------------------ dates

describe("reporting windows", () => {
  it("uses one window for the totals and the series", () => {
    const t = tenant();
    const days = 30;
    const series = dailyMetrics(t, days);
    const sum = series.reduce((n, m) => n + m.counts.session_start, 0);
    expect(totals(t, days).sessionStarts).toBe(sum);
  });

  it("shrinks when the window shrinks", () => {
    const t = tenant();
    expect(totals(t, 7).pageViews).toBeLessThanOrEqual(totals(t, 30).pageViews);
  });

  it("reports the window it used rather than leaving it implied", () => {
    const t = totals(tenant(), 7);
    expect(t.days).toBe(7);
    expect(t.from.getTime()).toBe(windowStart(7).getTime());
  });

  it("excludes events older than the window", () => {
    const t = tenant();
    const before = totals(t, 30).pageViews;
    db().analyticsEvents.push({
      id: "ae_old", tenantId: ATELIER, type: "page_view", source: "public",
      at: new Date(Date.now() - 400 * 86_400_000).toISOString(),
    });
    expect(totals(t, 30).pageViews).toBe(before);
  });
});
