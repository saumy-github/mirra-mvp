// Write-side of the dashboard prototype.
//
// These were Next server actions ("use server" + `redirect` + `revalidatePath`).
// In the SPA they are plain synchronous functions: the store notifies its
// subscribers, so no revalidation is needed, and the handful that used to
// redirect now RETURN the path for the caller to hand to `useNavigate`.
//
// Signatures are otherwise unchanged, including the `FormData` ones — React 19
// supports `<form action={fn}>` on the client, so the JSX that submits them
// came across untouched.
import { getDb, newId, updateDb, resetDb } from "./store";
import { requireSession, signIn, signOut, startViewAs, stopViewAs, type ViewAsMode } from "./session";
import { can, canInternal } from "./rbac";
import { canTransitionTenant } from "./lifecycle";
import { canMerchantMove, requirements, STAGE_META } from "./ingestion";
import { getEntitlements, missingRequirements } from "./entitlements";
import { liveSkuCount } from "./publication";
import { bumpRevision, snapshot } from "./revisions";
import { audit, billingEvent, slugify } from "./util";
import { dashPath } from "../routes";
import { CAPTURE_VIEWS } from "./types";
import type {
  BrandRole,
  CadAsset,
  CaptureMethod,
  CaptureView,
  DetailShotKind,
  FabricSource,
  Garment,
  GarmentAttributes,
  GarmentBehaviour,
  GarmentCategory,
  GarmentStage,
  GradingSource,
  LeadStatus,
  Measurement,
  Product,
  QaFinding,
  Silhouette,
  SizeChartKind,
  SizeRow,
  SizeSource,
  SoldOutPolicy,
  TenantStatus,
  TicketStatus,
} from "./types";

const nowIso = () => new Date().toISOString();

/**
 * Every mutation returns one of these rather than throwing or returning void.
 *
 * The prototype's actions were fire-and-forget: a rejected transition or a
 * plan-limit refusal produced a button that appeared to do nothing. Callers
 * now always have something to render.
 */
export type ActionResult = { ok: true; message?: string } | { ok: false; error: string };

export const ok = (message?: string): ActionResult => ({ ok: true, message });
export const fail = (error: string): ActionResult => ({ ok: false, error });

// ------------------------------------------------------------------ session

/** @returns the path to navigate to after signing in. */
export function signInAction(formData: FormData): string {
  const userId = String(formData.get("userId"));
  signIn(userId);
  const user = getDb().users.find((u) => u.id === userId);
  return user?.internalRole ? dashPath.admin : dashPath.portal;
}

/** @returns the path to navigate to after signing out. */
export function signOutAction(): string {
  signOut();
  return dashPath.login;
}

export function resetDemoAction() {
  resetDb();
}

// --------------------------------------------------------------------- CRM

export function updateLeadStatusAction(leadId: string, status: LeadStatus): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.leads.manage")) return fail("Not allowed.");
  updateDb((db) => {
    const lead = db.leads.find((l) => l.id === leadId);
    if (lead) lead.status = status;
  });
  audit({ actorId: s.user.id, actorName: s.user.name, action: "lead.status_change", target: leadId, detail: status });
  return ok();
}

/** Invite an approved lead: creates the tenant shell in `onboarding` and a brand owner user. */
export function inviteLeadAction(leadId: string): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.leads.manage")) return fail("Not allowed.");
  updateDb((db) => {
    const lead = db.leads.find((l) => l.id === leadId);
    if (!lead || lead.tenantId) return;
    const slug = slugify(lead.company);
    const tenantId = newId("t");
    db.tenants.push({
      id: tenantId,
      slug,
      name: lead.company,
      storeUrl: lead.storeUrl,
      storeOwnershipVerified: false,
      status: "onboarding",
      launchStatus: "not_launched",
      salesLed: lead.source !== "early_access",
      billing: { planId: "boutique", interval: "monthly", addOns: [], paymentStatus: "none" },
      theme: {
        brandColor: "#1a1a2e", accentColor: "#7c6cf0",
        logoText: lead.company, welcomeHeadline: "Try it on, virtually.",
      },
      defaults: {
        soldOutPolicy: "keep_tryon",
        hideColourwayWhenAllSoldOut: false,
        brandSizeCharts: [],
      },
      onboarding: {
        storeVerified: false, storeUrlConfirmed: false, shopifyConnected: false,
        teamInvited: false, planChosen: false, termsAccepted: false,
        billingEntered: false, activated: false, checklistReviewed: false,
      },
      healthScore: 50,
      churnRisk: "medium",
      accountNotes: [],
      domain: { subdomain: `${slug}.vto.mirra.com` },
      createdAt: nowIso(),
      previewToken: `pvt_${slug}_${newId("").slice(1, 7)}`,
    });
    const userId = newId("u");
    db.users.push({ id: userId, name: lead.contactName, email: lead.email });
    db.memberships.push({ userId, tenantId, role: "brand_owner", status: "active" });
    lead.status = "invited";
    lead.tenantId = tenantId;
  });
  audit({ actorId: s.user.id, actorName: s.user.name, action: "lead.invite", target: leadId });
  return ok("Workspace created and the owner invited.");
}

// -------------------------------------------------------------- onboarding

/** The agreement a merchant is actually accepting, by version. */
export const AGREEMENT = {
  version: "2026-06-01",
  documents: [
    { title: "Mirra Services Agreement", href: "/legal/services-agreement" },
    { title: "Data Processing Addendum", href: "/legal/dpa" },
  ],
};

export function completeOnboardingStepAction(step: string, formData: FormData): ActionResult {
  const s = requireSession();
  if (!s.tenant) return fail("No workspace selected.");
  const tenantId = s.tenant.id;
  const actor = s.user;

  const result = updateDb((db): ActionResult => {
    const t = db.tenants.find((x) => x.id === tenantId)!;
    switch (step) {
      case "store": {
        const url = String(formData.get("storeUrl") || "").trim();
        // A URL that isn't a URL cannot be a store, and "verified" has to mean
        // something happened rather than that a button was pressed.
        if (!/^https?:\/\/[^\s.]+\.[^\s]{2,}$/i.test(url)) {
          return fail("Enter your storefront URL, including https://");
        }
        t.storeUrl = url;
        // Ownership check: the prototype trusted a meta-tag claim; production
        // matches the Shopify OAuth shop domain, with a DNS TXT fallback.
        t.storeOwnershipVerified = true;
        t.onboarding.storeUrlConfirmed = true;
        t.onboarding.storeVerified = true;
        return ok();
      }
      case "shopify":
        t.onboarding.shopifyConnected = true;
        db.syncRuns.unshift({
          id: newId("sr"), tenantId, trigger: "manual", startedAt: nowIso(),
          finishedAt: nowIso(), status: "success",
          itemsSynced: db.products.filter((p) => p.tenantId === tenantId).length,
          failures: [],
        });
        return ok();
      case "team":
        t.onboarding.teamInvited = true;
        return ok();
      case "plan": {
        const planId = String(formData.get("planId")) as typeof t.billing.planId;
        const interval = String(formData.get("interval")) as "monthly" | "annual";
        if (!db.plans.some((p) => p.id === planId)) return fail("Choose a plan to continue.");
        t.billing.planId = planId;
        t.billing.interval = interval;
        t.onboarding.planChosen = true;
        return ok();
      }
      case "terms": {
        // Evidence, not a boolean: which version, accepted by whom, when.
        t.agreement = {
          documentVersion: AGREEMENT.version,
          acceptedAt: nowIso(),
          acceptedByUserId: actor.id,
          acceptedByName: actor.name,
          documents: AGREEMENT.documents,
        };
        t.onboarding.termsAccepted = true;
        return ok();
      }
      case "billing":
        t.billing.paymentStatus = "trialing";
        t.onboarding.billingEntered = true;
        return ok();
      case "activate": {
        // Every earlier step is a precondition, so activation can't be reached
        // by deep link or by a stale form on a half-finished workspace.
        const o = t.onboarding;
        if (!o.storeVerified || !o.shopifyConnected || !o.planChosen || !o.termsAccepted || !o.billingEntered) {
          return fail("Finish the earlier steps before activating.");
        }
        const plan = db.plans.find((p) => p.id === t.billing.planId)!;
        if (plan.trialDays > 0 && t.billing.paymentStatus === "trialing") {
          t.status = "trial";
          const ends = new Date(); ends.setDate(ends.getDate() + plan.trialDays);
          t.billing.trialEndsAt = ends.toISOString();
        } else {
          t.status = "active";
          t.billing.paymentStatus = "paid";
          const renew = new Date();
          renew.setMonth(renew.getMonth() + (t.billing.interval === "annual" ? 12 : 1));
          t.billing.renewalDate = renew.toISOString();
        }
        t.onboarding.activated = true;
        t.launchStatus = "preview";
        return ok();
      }
      case "checklist":
        t.onboarding.checklistReviewed = true;
        return ok();
      default:
        return fail("Unknown step.");
    }
  });

  if (!result.ok) return result;
  if (step === "activate") {
    billingEvent({ tenantId, type: "subscription_created", detail: "Activated via onboarding" });
    audit({ tenantId, actorId: actor.id, actorName: actor.name, action: "tenant.provision", target: s.tenant.name, detail: "Subdomain provisioned, entitlements attached" });
  } else {
    audit({ tenantId, actorId: actor.id, actorName: actor.name, action: `onboarding.${step}`, target: s.tenant.name });
  }
  return result;
}

/**
 * Reopen a completed onboarding step. Getting a store URL wrong and having no
 * way back to it is a support ticket that should never have existed.
 */
export function reopenOnboardingStepAction(step: string): ActionResult {
  const s = requireSession();
  if (!s.tenant) return fail("No workspace selected.");
  if (s.tenant.onboarding.activated && (step === "plan" || step === "billing" || step === "activate")) {
    return fail("Plan and billing are managed from the Billing page once you're activated.");
  }
  const tenantId = s.tenant.id;
  updateDb((db) => {
    const o = db.tenants.find((x) => x.id === tenantId)!.onboarding;
    const flags: Record<string, (keyof typeof o)[]> = {
      store: ["storeVerified", "storeUrlConfirmed"],
      shopify: ["shopifyConnected"],
      team: ["teamInvited"],
      plan: ["planChosen"],
      terms: ["termsAccepted"],
      billing: ["billingEntered"],
      checklist: ["checklistReviewed"],
    };
    for (const f of flags[step] ?? []) o[f] = false;
  });
  audit({ tenantId, actorId: s.user.id, actorName: s.user.name, action: "onboarding.reopen", target: step });
  return ok();
}

// ------------------------------------------------------------- publication

/**
 * Move a garment through the merchant-owned part of the stage machine.
 *
 * `in_qa → ready` is deliberately absent: that transition belongs to Mirra QA,
 * not to the brand. The prototype let merchants set "QA passed" from a
 * dropdown, which made the gate meaningless.
 */
export function setGarmentStageAction(garmentId: string, to: GarmentStage): ActionResult {
  const s = requireSession();
  if (!s.tenant) return fail("No workspace selected.");
  if (!can(s.role, "publication.manage")) {
    return fail(
      s.impersonating
        ? "This is a read-only support session — publication is the brand's to control."
        : "Your role can't change what shoppers see.",
    );
  }
  const tenant = s.tenant;
  const db = getDb();
  const g = db.garments.find((x) => x.id === garmentId && x.tenantId === tenant.id);
  if (!g) return fail("Garment not found in this workspace.");

  if (!canMerchantMove(g.stage, to)) {
    return fail(
      to === "ready"
        ? "Only the Mirra QA team can mark a garment ready."
        : `Can't move from ${STAGE_META[g.stage].label} to ${STAGE_META[to].label}.`,
    );
  }
  if (to === "in_qa") {
    const missing = missingRequirements(g);
    if (missing.length > 0) return fail(`Still missing: ${missing.join(", ")}`);
    if (!g.variantMappingConfirmed) return fail("Confirm the size → variant mapping first.");
  }
  if (to === "live") {
    // Publishing serves an approved snapshot. Without one there is nothing
    // safe to put in front of a shopper, whatever the stage says.
    if (!g.approved) return fail("This garment has no QA-approved revision to publish.");
    const ent = getEntitlements(tenant);
    const addingSkus = g.approved.variantIds.length;
    const used = liveSkuCount(tenant.id);
    if (used + addingSkus > ent.skuLimit) {
      return fail(
        `Plan limit reached — ${used} of ${ent.skuLimit} live SKUs used, and this garment needs ${addingSkus} more. Pause another garment or add SKU capacity.`,
      );
    }
  }

  updateDb(() => {
    if (to === "live") {
      g.publishedAt = nowIso();
      g.tryOnEnabled = true;
      g.scheduledGoLive = undefined;
    }
    if (to === "paused") g.tryOnEnabled = false;
    g.stage = to;
    g.updatedBy = s.user.name;
    g.updatedAt = nowIso();
  });
  audit({
    tenantId: tenant.id,
    actorId: s.user.id,
    actorName: s.user.name,
    action: `garment.${to}`,
    target: g.title,
    detail: g.approved ? `Revision ${g.approved.revision}` : undefined,
  });
  return ok(`${g.title} is now ${STAGE_META[to].label.toLowerCase()}.`);
}

export function toggleTryOnAction(garmentId: string, enabled: boolean): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "publication.manage")) return fail("Not allowed.");
  const tenant = s.tenant;
  let title = garmentId;
  const done = updateDb((db) => {
    const g = db.garments.find((x) => x.id === garmentId && x.tenantId === tenant.id);
    if (!g || g.stage !== "live") return false;
    title = g.title;
    g.tryOnEnabled = enabled;
    return true;
  });
  if (!done) return fail("Try-on can only be switched on a live garment.");
  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: enabled ? "garment.tryon_enable" : "garment.tryon_disable", target: title,
  });
  return ok();
}

/**
 * Bulk actions preflight every item and report exactly what was skipped and
 * why. Offering "Publish" over a mixed selection and silently dropping the
 * two-thirds that couldn't move is worse than refusing.
 */
export interface BulkPreflight {
  eligible: string[];
  skipped: { id: string; title: string; reason: string }[];
}

export function preflightBulkStage(garmentIds: string[], to: GarmentStage): BulkPreflight {
  const s = requireSession();
  const db = getDb();
  const eligible: string[] = [];
  const skipped: BulkPreflight["skipped"] = [];
  let projectedSkus = s.tenant ? liveSkuCount(s.tenant.id) : 0;
  const limit = s.tenant ? getEntitlements(s.tenant).skuLimit : 0;

  for (const id of garmentIds) {
    const g = db.garments.find((x) => x.id === id);
    if (!g) {
      skipped.push({ id, title: id, reason: "Not found" });
      continue;
    }
    if (!canMerchantMove(g.stage, to)) {
      skipped.push({ id, title: g.title, reason: `Is ${STAGE_META[g.stage].label}` });
      continue;
    }
    if (to === "in_qa") {
      const missing = missingRequirements(g);
      if (missing.length) {
        skipped.push({ id, title: g.title, reason: `Missing ${missing.join(", ")}` });
        continue;
      }
    }
    if (to === "live") {
      if (!g.approved) {
        skipped.push({ id, title: g.title, reason: "No QA-approved revision" });
        continue;
      }
      if (projectedSkus + g.approved.variantIds.length > limit) {
        skipped.push({ id, title: g.title, reason: "Would exceed the plan's SKU limit" });
        continue;
      }
      projectedSkus += g.approved.variantIds.length;
    }
    eligible.push(id);
  }
  return { eligible, skipped };
}

export function bulkStageAction(garmentIds: string[], to: GarmentStage) {
  const { eligible, skipped } = preflightBulkStage(garmentIds, to);
  const failed: { id: string; title: string; reason: string }[] = [];
  let applied = 0;
  for (const id of eligible) {
    const r = setGarmentStageAction(id, to);
    if (r.ok) applied += 1;
    else failed.push({ id, title: id, reason: r.error });
  }
  return { applied, skipped: [...skipped, ...failed] };
}

/**
 * The other side of the QA gate. Only Mirra staff with `console.qa.decide`
 * move a garment out of `in_qa`.
 *
 * Passing freezes a snapshot of the exact revision that was checked — that
 * snapshot, and only that snapshot, is what shoppers are ever served. Failing
 * records structured findings a merchant can act on rather than a sentence in
 * an audit log nobody reads.
 */
export function qaDecisionAction(
  garmentId: string,
  decision: "pass" | "fail",
  findings: Omit<QaFinding, "id" | "raisedBy" | "raisedAt" | "revision">[] = [],
  note?: string,
): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.qa.decide")) {
    return fail("Only Mirra QA can decide this.");
  }
  if (decision === "fail" && findings.length === 0) {
    return fail("A rejection needs at least one finding the merchant can act on.");
  }
  const db = getDb();
  const g = db.garments.find((x) => x.id === garmentId);
  if (!g) return fail("Garment not found.");
  if (g.stage !== "in_qa") return fail("This garment isn't with QA.");

  updateDb(() => {
    const at = nowIso();
    if (decision === "pass") {
      g.approved = snapshot(g, s.user.name);
      g.stage = "ready";
      for (const f of g.qaFindings) if (!f.resolvedAt) { f.resolvedAt = at; f.resolvedBy = s.user.name; }
    } else {
      g.stage = "needs_data";
      g.qaFindings.push(
        ...findings.map((f) => ({
          ...f,
          id: newId("qf"),
          raisedBy: s.user.name,
          raisedAt: at,
          revision: g.sourceRevision,
        })),
      );
    }
    g.qaHistory.unshift({
      at, by: s.user.name, decision, revision: g.sourceRevision, note,
      findingCount: decision === "fail" ? findings.length : 0,
    });
    g.updatedBy = `${s.user.name} (Mirra QA)`;
    g.updatedAt = at;
  });

  audit({
    tenantId: g.tenantId,
    actorId: s.user.id,
    actorName: s.user.name,
    action: decision === "pass" ? "garment.qa_pass" : "garment.qa_fail",
    target: g.title,
    detail:
      decision === "pass"
        ? `Approved revision ${g.sourceRevision}`
        : `${findings.length} finding(s) against revision ${g.sourceRevision}${note ? ` · ${note}` : ""}`,
  });
  return ok(decision === "pass" ? "Passed QA — the brand can publish it." : "Sent back with findings.");
}

/** The merchant says a finding is dealt with; QA still has to agree. */
export function resolveQaFindingAction(garmentId: string, findingId: string): ActionResult {
  return editGarment(garmentId, { action: "garment.qa_finding_resolve", detail: findingId }, (g) => {
    const f = g.qaFindings.find((x) => x.id === findingId);
    if (f) {
      f.resolvedAt = nowIso();
      f.resolvedBy = "merchant";
    }
  });
}

// ------------------------------------------------------------- scheduling

/**
 * Scheduled go-live. Publication advertised this for months with no control
 * behind it; it is now a real field with a real sweep.
 */
export function scheduleGoLiveAction(garmentId: string, whenIso: string | undefined): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "publication.manage")) return fail("Not allowed.");
  if (!getEntitlements(s.tenant).scheduledGoLive) {
    return fail("Scheduled go-lives are part of the Atelier plan.");
  }
  if (whenIso) {
    const when = new Date(whenIso);
    if (Number.isNaN(when.getTime())) return fail("That isn't a valid date and time.");
    if (when.getTime() < Date.now()) return fail("Pick a time in the future.");
    const g = getDb().garments.find((x) => x.id === garmentId);
    if (g && g.stage !== "ready") return fail("Only a QA-passed garment can be scheduled.");
  }
  return editGarment(
    garmentId,
    { action: whenIso ? "garment.schedule" : "garment.schedule_cancel", detail: whenIso },
    (g) => {
      g.scheduledGoLive = whenIso;
    },
  );
}

/**
 * Publish anything whose scheduled time has passed. Called when a merchant
 * opens Publication; in production this is a job, which is the only part of
 * this that changes.
 */
export function runDueSchedulesAction(tenantId: string): string[] {
  const db = getDb();
  const due = db.garments.filter(
    (g) =>
      g.tenantId === tenantId &&
      g.stage === "ready" &&
      g.scheduledGoLive &&
      new Date(g.scheduledGoLive).getTime() <= Date.now(),
  );
  const published: string[] = [];
  for (const g of due) {
    const r = setGarmentStageAction(g.id, "live");
    if (r.ok) published.push(g.title);
    else {
      updateDb(() => {
        g.scheduledGoLive = undefined;
      });
      audit({
        tenantId, actorId: "system", actorName: "Mirra scheduler",
        action: "garment.schedule_failed", target: g.title, detail: r.error,
      });
    }
  }
  return published;
}

/** Per-garment override of the store-wide sold-out policy. */
export function setSoldOutPolicyAction(
  garmentId: string,
  policy: SoldOutPolicy | undefined,
): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "publication.manage")) return fail("Not allowed.");
  const tenant = s.tenant;
  let title = garmentId;
  const done = updateDb((db) => {
    const g = db.garments.find((x) => x.id === garmentId && x.tenantId === tenant.id);
    if (!g) return false;
    title = g.title;
    g.soldOutPolicy = policy;
    return true;
  });
  if (!done) return fail("Garment not found.");
  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: "garment.sold_out_policy", target: title,
    detail: policy ?? "Follows the store default",
  });
  return ok();
}

export function setStoreSoldOutPolicyAction(policy: SoldOutPolicy): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "settings.manage")) return fail("Not allowed.");
  const tenantId = s.tenant.id;
  updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenantId);
    if (t) t.defaults.soldOutPolicy = policy;
  });
  audit({ tenantId, actorId: s.user.id, actorName: s.user.name, action: "settings.sold_out_policy", target: policy });
  return ok("Sold-out policy updated.");
}

export function setColourwaySoldOutPolicyAction(hide: boolean): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "settings.manage")) return fail("Not allowed.");
  const tenantId = s.tenant.id;
  updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenantId);
    if (t) t.defaults.hideColourwayWhenAllSoldOut = hide;
  });
  audit({
    tenantId, actorId: s.user.id, actorName: s.user.name,
    action: "settings.colourway_sold_out", target: hide ? "hide" : "keep",
  });
  return ok();
}

/**
 * Impact of a page-wide publication change, so a merchant is told what a
 * single click is about to do to shoppers before it does it.
 */
export function launchImpact(tenantId: string): { liveGarments: number; liveSkus: number } {
  const db = getDb();
  return {
    liveGarments: db.garments.filter((g) => g.tenantId === tenantId && g.stage === "live").length,
    liveSkus: liveSkuCount(tenantId),
  };
}

export function setTenantLaunchAction(launch: "live" | "paused" | "preview"): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "publication.manage")) {
    return fail(
      s.impersonating
        ? "Taking a customer's page offline is not something a support session may do."
        : "Your role can't change the page's launch state.",
    );
  }
  const tenant = s.tenant;
  const impact = launchImpact(tenant.id);
  updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenant.id)!;
    t.launchStatus = launch;
  });
  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: `tenant.launch_${launch}`, target: tenant.name,
    detail: `${impact.liveGarments} live garments · ${impact.liveSkus} SKUs affected`,
  });
  return ok(
    launch === "paused"
      ? `Page paused — ${impact.liveSkus} SKUs are no longer reachable by shoppers.`
      : `Page is ${launch}.`,
  );
}

// --------------------------------------------------------------- ingestion

interface EditOptions {
  /**
   * Set on every mutation that changes what try-on is built from — capture,
   * reference sample, sizing, material, category, blocks.
   *
   * These bump `sourceRevision`, which strands the generated asset and drops
   * anything mid-flight back to `needs_data`. QA approved a revision; a newer
   * revision has not been approved by anyone.
   */
  affectsTryOn?: boolean;
  /** Audit action name. Ingestion edits used to be entirely unlogged. */
  action: string;
  detail?: string;
}

function editGarment(
  garmentId: string,
  opts: EditOptions,
  fn: (g: Garment) => void,
): ActionResult {
  const s = requireSession();
  if (!s.tenant) return fail("No workspace selected.");
  if (!can(s.role, "catalogue.edit")) {
    return fail(
      s.impersonating
        ? "This is a read-only support session. Ask an admin to elevate it if a change is genuinely needed."
        : "Your role can view this garment but not edit it.",
    );
  }
  const tenantId = s.tenant.id;
  let invalidated: string | null = null;
  let title = garmentId;

  const found = updateDb((db) => {
    const g = db.garments.find((x) => x.id === garmentId && x.tenantId === tenantId);
    if (!g) return false;
    title = g.title;
    fn(g);
    if (opts.affectsTryOn) {
      const res = bumpRevision(g);
      if (res.invalidatedStage) invalidated = res.invalidatedStage;
      // Findings were raised against the revision that just became history.
      for (const f of g.qaFindings) if (!f.resolvedAt) f.resolvedAt = undefined;
    }
    g.updatedBy = s.user.name;
    g.updatedAt = nowIso();
    return true;
  });
  if (!found) return fail("Garment not found in this workspace.");

  audit({
    tenantId,
    actorId: s.user.id,
    actorName: s.user.name,
    action: opts.action,
    target: title,
    detail: [opts.detail, invalidated ? `Returned from ${invalidated} — approval no longer applies` : null]
      .filter(Boolean)
      .join(" · ") || undefined,
  });
  return invalidated
    ? ok(`Saved. This garment left ${STAGE_META[invalidated as GarmentStage].label} because the change needs re-approval.`)
    : ok();
}

/** Create the try-on garment for one colourway of a synced Shopify product. */
export function createGarmentAction(productId: string, colour: string): string | null {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "catalogue.edit")) throw new Error("FORBIDDEN");
  const tenant = s.tenant;
  return updateDb((db) => {
    const product = db.products.find((p) => p.id === productId && p.tenantId === tenant.id);
    if (!product) return null;
    const existing = db.garments.find(
      (g) => g.productId === productId && g.colour === colour && g.tenantId === tenant.id,
    );
    if (existing) return existing.id;

    const variants = product.variants.filter((v) => v.color === colour);
    const sizes = [...new Set(variants.map((v) => v.size))];
    const id = newId("g");
    db.garments.push({
      id,
      tenantId: tenant.id,
      productId,
      variantIds: variants.map((v) => v.id),
      title: `${product.title} — ${colour}`,
      canonicalTitle: product.title,
      category: categoryFromProductType(product.productType),
      optionValue: colour,
      colour,
      capture: { views: {}, accepted: [], issues: [], details: [] },
      sameConstructionAcrossSizes: null,
      constructionBlocks: [{ id: "b_standard", label: "Standard", sizes }],
      sizeChart: [],
      gradingUnverified: false,
      fabricComposition: [],
      liningComposition: [],
      fabricConfirmed: false,
      attributes: { stretch: "low", drape: "moderate", opacity: "opaque", thickness: "mid" },
      attributesSuggested: false,
      fitCriticalAreas: [],
      behaviours: [],
      fitNotes: "",
      careNotes: "",
      tags: [],
      collections: [],
      stage: "draft",
      variantMappingConfirmed: false,
      tryOnEnabled: false,
      sourceRevision: 1,
      qaFindings: [],
      qaHistory: [],
      updatedBy: s.user.name,
      updatedAt: nowIso(),
    });
    return id;
  });
}

/** Best-effort mapping from the Shopify product type to a Mirra category. */
function categoryFromProductType(productType: string): GarmentCategory {
  const t = productType.toLowerCase();
  if (t.includes("dress")) return "dress";
  if (t.includes("swim")) return "swim";
  if (t.includes("knit")) return "knitwear";
  if (t.includes("outer") || t.includes("coat") || t.includes("jacket")) return "outerwear";
  if (t.includes("trouser") || t.includes("bottom") || t.includes("pant") || t.includes("skirt")) return "bottom";
  if (t.includes("accessor") || t.includes("scarf")) return "accessory";
  return "top";
}

/**
 * Resolve a pasted Shopify product URL, handle or ID against the synced
 * catalogue. This is how identity is established before anything else: the
 * merchant names the listing, Mirra confirms it exists in the connected store.
 */
export function resolveShopifyProduct(
  tenantId: string,
  input: string,
): { product?: Product; error?: string } {
  const raw = input.trim();
  if (!raw) return { error: "Paste the Shopify product URL." };

  const products = getDb().products.filter((p) => p.tenantId === tenantId);
  const handle = raw
    .replace(/[?#].*$/, "")
    .replace(/\/$/, "")
    .split("/")
    .pop()!
    .toLowerCase();

  const product =
    products.find((p) => p.handle === handle) ??
    products.find((p) => p.shopifyId === raw) ??
    products.find((p) => p.onlineStoreUrl === raw) ??
    products.find((p) => p.title.toLowerCase() === raw.toLowerCase());

  if (!product) {
    return {
      error:
        "No product in your connected store matches that link. Check it belongs to this store, or re-run a Shopify sync.",
    };
  }
  return { product };
}

/**
 * Record the name the merchant confirmed. The canonical Shopify title is never
 * overwritten — if what they typed differs, the divergence is stored so the UI
 * can flag it rather than quietly creating a garment that doesn't match the
 * listing it claims to be.
 */
export function setMerchantTitleAction(garmentId: string, merchantTitle: string): ActionResult {
  return editGarment(garmentId, { action: "garment.title_confirm" }, (g) => {
    g.merchantTitle = merchantTitle.trim() || undefined;
  });
}

/** Adopt the canonical Shopify title, clearing any flagged mismatch. */
export function acceptCanonicalTitleAction(garmentId: string): ActionResult {
  return editGarment(garmentId, { action: "garment.title_adopt_canonical" }, (g) => {
    g.merchantTitle = undefined;
  });
}

/** How images are arriving. `cad` skips the four photographic views entirely. */
export function setCaptureMethodAction(garmentId: string, method: CaptureMethod): ActionResult {
  return editGarment(garmentId, { action: "garment.capture_method", detail: method, affectsTryOn: true }, (g) => {
    g.capture.method = method;
    if (method !== "cad") g.capture.cadAsset = undefined;
  });
}

export function attachCadAssetAction(garmentId: string, asset: CadAsset): ActionResult {
  return editGarment(garmentId, { action: "garment.cad_attach", detail: asset.filename, affectsTryOn: true }, (g) => {
    g.capture.method = "cad";
    g.capture.cadAsset = asset;
    // A valid 3D asset supersedes photographic reconstruction.
    g.capture.issues = [];
  });
}

/** The merchant has checked every generated size against its Shopify variant. */
export function confirmVariantMappingAction(garmentId: string, confirmed: boolean): ActionResult {
  return editGarment(garmentId, { action: "garment.variant_mapping_confirm" }, (g) => {
    g.variantMappingConfirmed = confirmed;
  });
}

/** Step 1 — which physical sample is being digitised. */
export function setReferenceSizeAction(garmentId: string, size: string): ActionResult {
  return editGarment(garmentId, { action: "garment.reference_size", detail: `Size ${size}`, affectsTryOn: true }, (g) => {
    g.referenceSize = size;
    const standard = g.constructionBlocks[0];
    if (standard) standard.referenceSize = size;
  });
}

/**
 * Step 2 — whether every size shares one pattern.
 *
 * "Yes" is the normal answer and the whole point: photographing 6 sizes × 5
 * colours would make ingestion unadoptable. One sample plus graded
 * measurements produces every digital size.
 */
export function setConstructionAction(garmentId: string, same: boolean, extraBlockSizes: string[] = []): ActionResult {
  return editGarment(garmentId, { action: "garment.construction_blocks", affectsTryOn: true }, (g) => {
    g.sameConstructionAcrossSizes = same;
    const allSizes = g.constructionBlocks.flatMap((b) => b.sizes);
    if (same || extraBlockSizes.length === 0) {
      g.constructionBlocks = [
        { id: "b_standard", label: "Standard", sizes: allSizes, referenceSize: g.referenceSize },
      ];
      return;
    }
    const standardSizes = allSizes.filter((s) => !extraBlockSizes.includes(s));
    g.constructionBlocks = [
      { id: "b_standard", label: "Standard block", sizes: standardSizes, referenceSize: g.referenceSize },
      { id: "b_extended", label: "Alternate block", sizes: extraBlockSizes },
    ];
  });
}

/** Step 3 — a capture arrived and passed or failed validation. */
export function recordCaptureAction(
  garmentId: string,
  view: CaptureView,
  outcome: { accepted: true } | { accepted: false; message: string },
  method: CaptureMethod = "phone",
): ActionResult {
  return editGarment(garmentId, { action: outcome.accepted ? "garment.capture_accept" : "garment.capture_reject", detail: view, affectsTryOn: true }, (g) => {
    g.capture.method = method;
    g.capture.issues = g.capture.issues.filter((i) => i.view !== view);
    if (outcome.accepted) {
      g.capture.views[view] = `${view}.jpg`;
      if (!g.capture.accepted.includes(view)) g.capture.accepted.push(view);
    } else {
      delete g.capture.views[view];
      g.capture.accepted = g.capture.accepted.filter((v) => v !== view);
      g.capture.issues.push({ view, message: outcome.message });
    }
  });
}

export function addDetailShotAction(garmentId: string, kind: DetailShotKind, label: string): ActionResult {
  return editGarment(garmentId, { action: "garment.detail_shot", detail: label }, (g) => {
    g.capture.details.push({ kind, label });
  });
}

/**
 * Kick off digital-garment generation. The merchant is explicitly not made to
 * wait — they continue with sizing and material while this runs.
 */
export function startGenerationAction(garmentId: string): ActionResult {
  const g = getDb().garments.find((x) => x.id === garmentId);
  if (!g) return fail("Garment not found.");
  const hasSource =
    g.capture.method === "cad"
      ? Boolean(g.capture.cadAsset)
      : g.capture.accepted.length === CAPTURE_VIEWS.length;
  if (!hasSource) return fail("Generation needs a complete capture set or a validated 3D asset.");
  if (g.stage !== "draft" && g.stage !== "needs_data") {
    return fail(`Generation can't start from ${STAGE_META[g.stage].label}.`);
  }
  return editGarment(garmentId, { action: "garment.generation_start" }, (gg) => {
    gg.stage = "processing";
  });
}

/**
 * The pipeline finished.
 *
 * Where this used to dump every garment back into `needs_data` — leaving a
 * complete garment with no route to QA at all — it now records the revision
 * the asset was built from and moves a garment that has everything it needs
 * into the merchant's own review step. That review is the missing rung the
 * lifecycle was always designed around.
 */
export function completeGenerationAction(garmentId: string): ActionResult {
  const db = getDb();
  const g = db.garments.find((x) => x.id === garmentId);
  if (!g) return fail("Garment not found.");
  if (g.stage !== "processing") return fail("This garment is not generating.");
  const product = db.products.find((p) => p.id === g.productId);
  const outstanding = requirements(g, product).filter((r) => r.blocking && !r.complete);

  return editGarment(
    garmentId,
    {
      action: "garment.generation_complete",
      detail: outstanding.length ? `${outstanding.length} requirement(s) outstanding` : "Ready for your review",
    },
    (gg) => {
      // The asset describes the revision that was current when it was built.
      gg.assetRevision = gg.sourceRevision;
      gg.stage = outstanding.length === 0 ? "merchant_review" : "needs_data";
    },
  );
}

/**
 * The merchant has everything and is ready to look at it themselves.
 *
 * `needs_data → merchant_review` is the transition nothing in the prototype
 * ever performed, which is why a finished garment could not reach QA.
 */
export function submitForMerchantReviewAction(garmentId: string): ActionResult {
  const db = getDb();
  const g = db.garments.find((x) => x.id === garmentId);
  if (!g) return fail("Garment not found.");
  if (!canMerchantMove(g.stage, "merchant_review")) {
    return fail(`Can't move from ${STAGE_META[g.stage].label} to review.`);
  }
  const missing = missingRequirements(g);
  if (missing.length > 0) return fail(`Still missing: ${missing.join(", ")}`);
  return editGarment(garmentId, { action: "garment.merchant_review" }, (gg) => {
    gg.stage = "merchant_review";
  });
}

/**
 * What Mirra can already find, before asking the merchant to type anything.
 *
 * A brand's composition usually exists somewhere — the Shopify description, a
 * structured metafield, a saved brand profile. Asking for it first is wasted
 * work and invites a different answer than the listing shows.
 */
export function findExistingComposition(
  garmentId: string,
): { composition: { material: string; pct: number }[]; source: FabricSource; label: string } | null {
  const db = getDb();
  const g = db.garments.find((x) => x.id === garmentId);
  if (!g) return null;

  // A sibling colourway of the same product is the most reliable source.
  const sibling = db.garments.find(
    (x) => x.productId === g.productId && x.id !== g.id && x.fabricConfirmed && x.fabricComposition.length > 0,
  );
  if (sibling) {
    return {
      composition: sibling.fabricComposition.map((f) => ({ ...f })),
      source: "brand_profile",
      label: `${sibling.title} (same product)`,
    };
  }

  const product = db.products.find((p) => p.id === g.productId);
  if (product) {
    // Stands in for parsing the Shopify description / metafield.
    const known: Record<string, { material: string; pct: number }[]> = {
      Dress: [{ material: "Silk", pct: 92 }, { material: "Elastane", pct: 8 }],
      Knitwear: [{ material: "Cashmere", pct: 100 }],
      Bottom: [{ material: "Wool", pct: 70 }, { material: "Polyamide", pct: 30 }],
    };
    const composition = known[product.productType];
    if (composition) {
      return { composition, source: "metafield", label: "Shopify metafield" };
    }
  }
  return null;
}

/** Step 4 — material, with provenance recorded. */
export function setFabricAction(
  garmentId: string,
  composition: { material: string; pct: number }[],
  source: FabricSource,
  lining: { material: string; pct: number }[] = [],
): ActionResult {
  return editGarment(
    garmentId,
    {
      action: "garment.material",
      detail: composition.map((c) => `${c.pct}% ${c.material}`).join(", "),
      affectsTryOn: true,
    },
    (g) => {
      g.fabricComposition = composition;
      g.liningComposition = lining;
      g.fabricSource = source;
      g.fabricConfirmed = true;
      // Suggest simulation behaviour from the composition rather than making a
      // merchant reason like a textile engineer. They confirm or correct.
      g.attributes = suggestAttributes(composition);
      g.attributesSuggested = true;
    },
  );
}

export function confirmAttributesAction(garmentId: string, attributes: GarmentAttributes): ActionResult {
  return editGarment(garmentId, { action: "garment.material_behaviour", affectsTryOn: true }, (g) => {
    g.attributes = attributes;
    g.attributesSuggested = false;
  });
}

/** Cheap heuristics — good enough to save typing, always merchant-confirmed. */
export function suggestAttributes(
  composition: { material: string; pct: number }[],
): GarmentAttributes {
  const has = (name: string) =>
    composition.some((c) => c.material.toLowerCase().includes(name));
  const elastanePct =
    composition.find((c) => /elastane|spandex|lycra/i.test(c.material))?.pct ?? 0;

  return {
    stretch: elastanePct >= 12 ? "high" : elastanePct >= 4 ? "medium" : has("wool") || has("jersey") ? "low" : "none",
    drape: has("silk") || has("viscose") || has("modal") ? "fluid" : has("denim") || has("canvas") || has("wool") ? "structured" : "moderate",
    opacity: has("silk") || has("chiffon") || has("mesh") ? "semi" : "opaque",
    thickness: has("cashmere") || has("mohair") || has("wool") ? "mid" : has("canvas") || has("denim") ? "heavy" : "light",
  };
}

/** Step 5 — sizing, always with a recorded source. */
export function setSizeChartAction(
  garmentId: string,
  rows: SizeRow[],
  source: SizeSource,
  kind: SizeChartKind,
  grading: GradingSource,
): ActionResult {
  return editGarment(
    garmentId,
    { action: "garment.size_chart", detail: `${rows.length} sizes from ${source}`, affectsTryOn: true },
    (g) => {
      g.sizeChart = rows;
      g.sizeSource = source;
      g.sizeChartKind = kind;
      g.gradingSource = grading;
      // Sizes inferred from a single sample are a draft. Mirra must not quietly
      // present them as measured.
      g.gradingUnverified = grading === "estimated";
    },
  );
}

export function verifyGradingAction(garmentId: string): ActionResult {
  return editGarment(garmentId, { action: "garment.grading_verified", affectsTryOn: true }, (g) => {
    g.gradingUnverified = false;
  });
}

/** Auto-measure the reference sample. Needs a physical scale to be meaningful. */
export function autoMeasureAction(
  garmentId: string,
  calibration: "card" | "known_dimension" | "depth",
  values: Measurement[],
): ActionResult {
  return editGarment(garmentId, { action: "garment.auto_measure", detail: calibration, affectsTryOn: true }, (g) => {
    g.autoMeasurements = { calibration, sizeLabel: g.referenceSize ?? "—", values };
  });
}

/** Step 6 — structured fit, with the readable note generated from it. */
export function setFitAction(
  garmentId: string,
  silhouette: Silhouette,
  behaviours: GarmentBehaviour[],
  fitCriticalAreas: string[],
  notes: string,
): ActionResult {
  return editGarment(garmentId, { action: "garment.fit", detail: silhouette, affectsTryOn: true }, (g) => {
    g.silhouette = silhouette;
    g.behaviours = behaviours;
    g.fitCriticalAreas = fitCriticalAreas;
    g.fitNotes = notes;
  });
}

/**
 * Reuse a sibling colourway's work. Same cut and fabric means only new colour
 * imagery is needed; same cut with different fabric keeps geometry and grading
 * but starts a fresh material profile.
 */
export function reuseColourwayAction(
  garmentId: string,
  sourceGarmentId: string,
  mode: "same_cut_and_fabric" | "same_cut_new_fabric",
) {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "catalogue.edit")) throw new Error("FORBIDDEN");
  const tenantId = s.tenant.id;
  updateDb((db) => {
    const g = db.garments.find((x) => x.id === garmentId && x.tenantId === tenantId);
    const src = db.garments.find((x) => x.id === sourceGarmentId && x.tenantId === tenantId);
    if (!g || !src) return;

    g.referenceSize = src.referenceSize;
    g.sameConstructionAcrossSizes = src.sameConstructionAcrossSizes;
    g.constructionBlocks = src.constructionBlocks.map((b) => ({ ...b }));
    g.sizeChart = src.sizeChart.map((r) => ({ ...r, values: { ...r.values } }));
    g.sizeSource = src.sizeSource;
    g.sizeChartKind = src.sizeChartKind;
    g.gradingSource = src.gradingSource;
    g.gradingUnverified = src.gradingUnverified;
    g.silhouette = src.silhouette;
    g.behaviours = [...src.behaviours];
    g.fitCriticalAreas = [...src.fitCriticalAreas];
    g.fitNotes = src.fitNotes;
    g.reusedFromGarmentId = src.id;

    if (mode === "same_cut_and_fabric") {
      g.fabricComposition = src.fabricComposition.map((f) => ({ ...f }));
      g.fabricSource = src.fabricSource;
      g.fabricConfirmed = src.fabricConfirmed;
      g.attributes = { ...src.attributes };
      g.attributesSuggested = src.attributesSuggested;
    }
    g.updatedBy = s.user.name;
    g.updatedAt = nowIso();
  });
}

// ---------------------------------------------------------------- garments

/**
 * The garment summary page's own edit form.
 *
 * Category is here and changing it is consequential: a dress and a trouser do
 * not share measurement fields, so a chart carried across categories is a set
 * of numbers labelled with keys the new category never asks for. The chart is
 * dropped rather than silently reinterpreted, and — because this is
 * try-on-relevant — the edit bumps the revision, which is what stops the
 * change reaching shoppers before QA sees it.
 */
export function updateGarmentAction(garmentId: string, formData: FormData): ActionResult {
  const db = getDb();
  const before = db.garments.find((x) => x.id === garmentId);
  if (!before) return fail("Garment not found.");
  const nextCategory = (formData.get("category") as GarmentCategory) ?? before.category;
  const categoryChanged = nextCategory !== before.category;
  const attrs = ["stretch", "drape", "opacity", "thickness"] as const;
  const attrChanged = attrs.some((a) => {
    const v = formData.get(a);
    return v && String(v) !== before.attributes[a];
  });

  return editGarment(
    garmentId,
    {
      action: "garment.update",
      detail: categoryChanged ? `Category ${before.category} → ${nextCategory}` : undefined,
      // Notes are copy; category and behaviour drive the simulation.
      affectsTryOn: categoryChanged || attrChanged,
    },
    (g) => {
      g.fitNotes = String(formData.get("fitNotes") ?? g.fitNotes);
      g.careNotes = String(formData.get("careNotes") ?? g.careNotes);
      g.category = nextCategory;
      for (const a of attrs) {
        const v = formData.get(a);
        if (v) {
          // Narrow per key rather than casting the whole object to a string map.
          (g.attributes[a] as string) = String(v);
          g.attributesSuggested = false;
        }
      }
      if (categoryChanged && g.sizeChart.length > 0) {
        g.sizeChart = [];
        g.sizeSource = undefined;
        g.sizeChartKind = undefined;
        g.gradingSource = undefined;
        g.gradingUnverified = false;
      }
    },
  );
}

// -------------------------------------------------------------- catalogue

export interface SyncDelta {
  productId: string;
  title: string;
  kind: "new" | "updated" | "failing" | "conflict";
  detail: string;
  /** Garments whose data depends on this product. */
  affectedGarmentIds: string[];
}

/**
 * What a sync would change, before it changes anything.
 *
 * "Sync now" used to flip pending rows to synced and leave every failing row
 * exactly as it was, so the one button on the page could never fix the one
 * problem the page reported. Merchants get the delta first, then decide.
 */
export function previewSync(tenantId: string): SyncDelta[] {
  const db = getDb();
  const garmentsFor = (productId: string) =>
    db.garments.filter((g) => g.tenantId === tenantId && g.productId === productId).map((g) => g.id);

  return db.products
    .filter((p) => p.tenantId === tenantId)
    .flatMap((p): SyncDelta[] => {
      const affected = garmentsFor(p.id);
      if (p.syncStatus === "error") {
        return [{
          productId: p.id, title: p.title, kind: "failing",
          detail: p.syncError ?? "Last sync failed.", affectedGarmentIds: affected,
        }];
      }
      if (p.syncStatus === "pending") {
        return [{
          productId: p.id, title: p.title, kind: affected.length ? "updated" : "new",
          detail: affected.length
            ? `${p.variants.length} variants will be re-read; ${affected.length} garment(s) depend on this product.`
            : `${p.variants.length} variants will be imported.`,
          affectedGarmentIds: affected,
        }];
      }
      // A digitised garment whose approved revision references SKUs Shopify no
      // longer returns is a conflict, not an update: applying it silently
      // would strand shoppers on sizes that cannot be bought.
      const conflicts: SyncDelta[] = [];
      for (const gid of affected) {
        const g = db.garments.find((x) => x.id === gid)!;
        const missing = (g.approved?.variantIds ?? g.variantIds).filter(
          (vid) => !p.variants.some((v) => v.id === vid),
        );
        if (missing.length > 0) {
          conflicts.push({
            productId: p.id, title: p.title, kind: "conflict",
            detail: `${missing.length} SKU(s) used by "${g.title}" no longer exist in Shopify.`,
            affectedGarmentIds: [gid],
          });
        }
      }
      return conflicts;
    });
}

/**
 * Run a sync. Failing products are retried and cleared on success; conflicts
 * are recorded for a human rather than applied.
 */
export function triggerSyncAction(opts: { retryFailed?: boolean } = {}): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "catalogue.edit")) return fail("Not allowed.");
  const tenant = s.tenant;
  const deltas = previewSync(tenant.id);

  const summary = updateDb((db) => {
    const items = db.products.filter((p) => p.tenantId === tenant.id);
    const failures: { item: string; error: string; productId: string }[] = [];
    let synced = 0;

    for (const p of items) {
      if (p.syncStatus === "pending") {
        p.syncStatus = "synced";
        p.lastSyncedAt = nowIso();
        synced += 1;
      } else if (p.syncStatus === "error") {
        if (!opts.retryFailed) {
          failures.push({ item: p.title, error: p.syncError ?? "Unknown error", productId: p.id });
          continue;
        }
        // A retry either fixes it or reports the same reason again — it never
        // leaves the row untouched while claiming the run succeeded.
        if (p.syncError?.includes("404")) {
          failures.push({
            item: p.title,
            error: `${p.syncError} — still failing. Re-upload the image in Shopify, then retry.`,
            productId: p.id,
          });
        } else {
          p.syncStatus = "synced";
          p.syncError = undefined;
          p.lastSyncedAt = nowIso();
          synced += 1;
        }
      } else {
        synced += 1;
      }
    }

    const conflicts = deltas
      .filter((d) => d.kind === "conflict")
      .map((d) => ({
        kind: "variant_removed" as const,
        productId: d.productId,
        productTitle: d.title,
        detail: d.detail,
        affectedGarmentIds: d.affectedGarmentIds,
      }));

    db.syncRuns.unshift({
      id: newId("sr"),
      tenantId: tenant.id,
      trigger: "manual",
      startedAt: nowIso(),
      finishedAt: nowIso(),
      status: failures.length || conflicts.length ? "partial" : "success",
      itemsSynced: synced,
      failures,
      conflicts,
    });
    return { failures: failures.length, conflicts: conflicts.length, synced };
  });

  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: "catalogue.sync", target: tenant.name,
    detail: `${summary.synced} synced · ${summary.failures} failed · ${summary.conflicts} conflict(s)`,
  });
  if (summary.failures || summary.conflicts) {
    return fail(
      `Synced ${summary.synced}. ${summary.failures} still failing, ${summary.conflicts} conflict(s) need a decision.`,
    );
  }
  return ok(`Synced ${summary.synced} products.`);
}

/** Acknowledge a conflict so it stops blocking the run's status. */
export function resolveSyncConflictAction(runId: string, productId: string): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "catalogue.edit")) return fail("Not allowed.");
  const tenantId = s.tenant.id;
  updateDb((db) => {
    const run = db.syncRuns.find((r) => r.id === runId && r.tenantId === tenantId);
    const c = run?.conflicts?.find((x) => x.productId === productId);
    if (c) c.resolvedAt = nowIso();
  });
  audit({
    tenantId, actorId: s.user.id, actorName: s.user.name,
    action: "catalogue.sync_conflict_resolve", target: productId,
  });
  return ok("Conflict acknowledged.");
}

// ----------------------------------------------------------------- billing

/**
 * What cancelling actually costs, computed before the merchant confirms.
 * A destructive action that can't tell you its blast radius shouldn't be one
 * click away from a button labelled "Cancel subscription".
 */
export function cancellationImpact(tenantId: string) {
  const db = getDb();
  const garments = db.garments.filter((g) => g.tenantId === tenantId);
  const grace = new Date();
  grace.setDate(grace.getDate() + 60);
  return {
    liveGarments: garments.filter((g) => g.stage === "live").length,
    liveSkus: liveSkuCount(tenantId),
    totalGarments: garments.length,
    seats: db.memberships.filter((m) => m.tenantId === tenantId).length,
    dataDeletedAfter: grace.toISOString(),
  };
}

export function requestCancellationAction(formData: FormData): ActionResult {
  const s = requireSession();
  if (!s.tenant) return fail("No workspace selected.");
  if (!can(s.role, "billing.manage")) {
    return fail(
      s.impersonating
        ? "Cancelling a customer's subscription is never something a support session may do."
        : "Only Owner and Finance roles can change the subscription.",
    );
  }
  const tenant = s.tenant;
  const reason = String(formData.get("reason") || "");
  if (!reason.trim()) return fail("Tell us why you're leaving so we can confirm the cancellation.");
  // Typed confirmation, not a second button: the click that takes a storefront
  // offline should require reading the sentence next to it.
  const confirmation = String(formData.get("confirmation") || "").trim().toUpperCase();
  if (confirmation !== "CANCEL") {
    return fail('Type CANCEL to confirm — this takes your try-on page offline immediately.');
  }
  const impact = cancellationImpact(tenant.id);

  const moved = updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenant.id)!;
    if (!canTransitionTenant(t.status, "cancelled")) return false;
    t.status = "cancelled";
    t.launchStatus = "paused";
    t.billing.paymentStatus = "cancelled";
    t.billing.cancellationDate = nowIso();
    t.billing.cancellationReason = reason;
    t.graceUntil = impact.dataDeletedAfter; // data preserved 60 days, then archived
    return true;
  });
  if (!moved) return fail(`A ${tenant.status} subscription can't be cancelled from here — contact support.`);

  billingEvent({ tenantId: tenant.id, type: "cancellation_requested", detail: reason });
  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: "tenant.cancel", target: tenant.name,
    detail: `${reason} · ${impact.liveSkus} SKUs taken offline · reactivate before ${fmtDay(impact.dataDeletedAfter)}`,
  });
  return ok(`Cancelled. ${impact.liveSkus} SKUs are offline; everything is recoverable until ${fmtDay(impact.dataDeletedAfter)}.`);
}

function fmtDay(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

/**
 * Reactivation depends on a payment succeeding, which is the provider's
 * answer, not ours. Until billing is wired the tenant comes back in `past_due`
 * with the page live under the dunning grace — never silently marked `paid`.
 */
export function reactivateAction(): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "billing.manage")) return fail("Not allowed.");
  const tenant = s.tenant;
  const moved = updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenant.id)!;
    if (!canTransitionTenant(t.status, "active")) return false;
    t.status = "active";
    t.launchStatus = "live";
    t.billing.paymentStatus = "past_due";
    t.billing.cancellationDate = undefined;
    t.billing.cancellationReason = undefined;
    t.graceUntil = undefined;
    const renew = new Date();
    renew.setMonth(renew.getMonth() + (t.billing.interval === "annual" ? 12 : 1));
    t.billing.renewalDate = renew.toISOString();
    return true;
  });
  if (!moved) return fail("This subscription can't be reactivated from the portal — contact support.");
  billingEvent({ tenantId: tenant.id, type: "reactivated", detail: "Reactivated from portal — awaiting payment confirmation" });
  audit({ tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name, action: "tenant.reactivate", target: tenant.name });
  return ok("Your page is back online. Billing stays 'past due' until the payment provider confirms a successful charge.");
}

// -------------------------------------------------------------------- team

/**
 * Seat management against the in-memory store. Invitations are real records
 * with an expiry rather than a boolean somewhere — an invited seat counts
 * against the plan and cannot sign in until it is accepted.
 */
export function inviteMemberAction(formData: FormData): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "team.manage")) return fail("Only an Owner can manage seats.");
  const tenant = s.tenant;
  const email = String(formData.get("email") || "").trim().toLowerCase();
  const name = String(formData.get("name") || "").trim();
  const role = String(formData.get("role") || "brand_viewer") as BrandRole;
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fail("Enter a valid email address.");

  const db = getDb();
  const ent = getEntitlements(tenant);
  const seats = db.memberships.filter((m) => m.tenantId === tenant.id && m.status !== "expired");
  if (seats.length >= ent.seatLimit) {
    return fail(`Your plan includes ${ent.seatLimit} seats and all are in use. Remove a seat or upgrade.`);
  }
  if (seats.some((m) => db.users.find((u) => u.id === m.userId)?.email === email)) {
    return fail("That person already has a seat in this workspace.");
  }

  updateDb((d) => {
    let user = d.users.find((u) => u.email === email);
    if (!user) {
      user = { id: newId("u"), name: name || email.split("@")[0], email };
      d.users.push(user);
    }
    const expires = new Date();
    expires.setDate(expires.getDate() + 7); // invitations expire after 7 days
    d.memberships.push({
      userId: user.id, tenantId: tenant.id, role,
      status: "invited", invitedAt: nowIso(), invitedBy: s.user.name,
      expiresAt: expires.toISOString(),
    });
  });
  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: "team.invite", target: email, detail: role,
  });
  return ok(`Invitation created for ${email}. It expires in 7 days.`);
}

export function setMemberRoleAction(userId: string, role: BrandRole): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "team.manage")) return fail("Only an Owner can change roles.");
  const tenant = s.tenant;
  const db = getDb();
  const owners = db.memberships.filter(
    (m) => m.tenantId === tenant.id && m.role === "brand_owner" && m.status === "active",
  );
  const target = db.memberships.find((m) => m.tenantId === tenant.id && m.userId === userId);
  if (!target) return fail("That person isn't in this workspace.");
  // A workspace with no owner cannot manage its own billing or seats again.
  if (target.role === "brand_owner" && role !== "brand_owner" && owners.length <= 1) {
    return fail("This is the last Owner — promote someone else first.");
  }
  updateDb(() => {
    target.role = role;
  });
  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: "team.role_change", target: db.users.find((u) => u.id === userId)?.name ?? userId, detail: role,
  });
  return ok("Role updated.");
}

export function removeMemberAction(userId: string): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "team.manage")) return fail("Only an Owner can remove seats.");
  const tenant = s.tenant;
  const db = getDb();
  const target = db.memberships.find((m) => m.tenantId === tenant.id && m.userId === userId);
  if (!target) return fail("That person isn't in this workspace.");
  if (userId === s.user.id) return fail("You can't remove your own seat.");
  const owners = db.memberships.filter(
    (m) => m.tenantId === tenant.id && m.role === "brand_owner" && m.status === "active",
  );
  if (target.role === "brand_owner" && owners.length <= 1) {
    return fail("This is the last Owner — promote someone else first.");
  }
  const name = db.users.find((u) => u.id === userId)?.name ?? userId;
  updateDb((d) => {
    d.memberships = d.memberships.filter(
      (m) => !(m.tenantId === tenant.id && m.userId === userId),
    );
  });
  audit({ tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name, action: "team.remove", target: name });
  return ok(`${name} no longer has access.`);
}

// ------------------------------------------------------------ brand charts

/**
 * Brand size charts are versioned, never edited in place: a garment sized from
 * v2 must not start claiming v3's numbers because someone fixed a typo.
 */
export function saveBrandChartAction(
  chart: { id?: string; label: string; category: GarmentCategory | "all"; kind: SizeChartKind; rows: SizeRow[] },
): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "settings.manage")) return fail("Only an Owner can manage brand charts.");
  const tenant = s.tenant;
  if (!chart.label.trim()) return fail("Give the chart a name.");
  if (chart.rows.length === 0) return fail("A chart needs at least one size.");

  updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenant.id)!;
    const existing = chart.id ? t.defaults.brandSizeCharts.find((c) => c.id === chart.id) : undefined;
    const version = existing ? existing.version + 1 : 1;
    const id = newId("bsc");
    if (existing) {
      existing.archived = true;
      existing.supersededById = id;
    }
    t.defaults.brandSizeCharts.push({
      id,
      label: chart.label.trim(),
      category: chart.category,
      kind: chart.kind,
      sizes: chart.rows.map((r) => r.size),
      rows: chart.rows,
      version,
      updatedAt: nowIso(),
      updatedBy: s.user.name,
    });
  });
  audit({
    tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name,
    action: chart.id ? "settings.brand_chart_version" : "settings.brand_chart_create",
    target: chart.label,
  });
  return ok(chart.id ? "Published a new version of the chart." : "Brand chart created.");
}

export function archiveBrandChartAction(chartId: string): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "settings.manage")) return fail("Not allowed.");
  const tenant = s.tenant;
  updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenant.id)!;
    const c = t.defaults.brandSizeCharts.find((x) => x.id === chartId);
    if (c) c.archived = true;
  });
  audit({ tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name, action: "settings.brand_chart_archive", target: chartId });
  return ok("Archived. Garments already sized from it keep their numbers.");
}

// ----------------------------------------------------------------- support

export function createTicketAction(formData: FormData): ActionResult {
  const s = requireSession();
  if (!s.tenant || !can(s.role, "support.create")) return fail("Not allowed.");
  const tenant = s.tenant;
  const subject = String(formData.get("subject") || "").trim();
  const body = String(formData.get("body") || "").trim();
  if (!subject || !body) return fail("A subject and a description are both needed.");
  updateDb((db) => {
    db.tickets.unshift({
      id: newId("tk"),
      tenantId: tenant.id,
      subject,
      category: (formData.get("category") as "onboarding") ?? "other",
      priority: (formData.get("priority") as "normal") ?? "normal",
      status: "open",
      createdById: s.user.id,
      createdAt: nowIso(),
      messages: [{ at: nowIso(), from: s.user.name, internal: false, body }],
    });
  });
  audit({ tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name, action: "support.ticket_open", target: subject });
  return ok("Ticket opened — we'll reply within your SLA.");
}

export function escalateTicketAction(ticketId: string): ActionResult {
  const s = requireSession();
  if (!s.tenant) return fail("Not allowed.");
  const tenant = s.tenant;
  const done = updateDb((db) => {
    const t = db.tickets.find((x) => x.id === ticketId && x.tenantId === tenant.id);
    if (!t || t.status === "resolved") return false;
    t.status = "escalated";
    t.priority = "urgent";
    return true;
  });
  if (!done) return fail("That ticket can't be escalated.");
  audit({ tenantId: tenant.id, actorId: s.user.id, actorName: s.user.name, action: "support.escalate", target: ticketId });
  return ok("Escalated — this pages our on-call engineer.");
}

/** Staff: pick up, reply to and close tickets from the internal queue. */
export function assignTicketAction(ticketId: string, assigneeId: string | undefined): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.support.manage")) return fail("Not allowed.");
  updateDb((db) => {
    const t = db.tickets.find((x) => x.id === ticketId);
    if (t) t.assigneeId = assigneeId;
  });
  return ok(assigneeId ? "Assigned." : "Unassigned.");
}

export function replyToTicketAction(ticketId: string, body: string, internal = false): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.support.manage")) return fail("Not allowed.");
  if (!body.trim()) return fail("Write a reply first.");
  const done = updateDb((db) => {
    const t = db.tickets.find((x) => x.id === ticketId);
    if (!t) return false;
    t.messages.push({ at: nowIso(), from: s.user.name, internal, body: body.trim() });
    if (!internal && t.status === "open") t.status = "pending";
    return true;
  });
  if (!done) return fail("Ticket not found.");
  return ok(internal ? "Internal note added." : "Reply sent.");
}

export function setTicketStatusAction(ticketId: string, status: TicketStatus): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.support.manage")) return fail("Not allowed.");
  const db = getDb();
  const t = db.tickets.find((x) => x.id === ticketId);
  if (!t) return fail("Ticket not found.");
  updateDb(() => {
    t.status = status;
  });
  audit({
    tenantId: t.tenantId, actorId: s.user.id, actorName: s.user.name,
    action: "support.status_change", target: t.subject, detail: status,
  });
  return ok(`Ticket marked ${status}.`);
}

// ------------------------------------------------------------ admin console

export function adminTenantTransitionAction(
  tenantId: string,
  to: TenantStatus,
  reason: string,
): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.tenants.manage")) {
    return fail("Tenant lifecycle overrides are Admin-only.");
  }
  if (reason.trim().length < 4) return fail("A reason is required and is audit-logged.");
  const db = getDb();
  const t = db.tenants.find((x) => x.id === tenantId);
  if (!t) return fail("Tenant not found.");
  if (!canTransitionTenant(t.status, to)) return fail(`Can't move a ${t.status} tenant to ${to}.`);

  updateDb(() => {
    t.status = to;
    if (to === "suspended") { t.suspendedAt = nowIso(); t.launchStatus = "paused"; }
    if (to === "active") {
      t.suspendedAt = undefined;
      t.billing.paymentStatus = "paid";
      if (t.launchStatus === "paused") t.launchStatus = "live";
    }
    if (to === "archived") t.launchStatus = "not_launched";
  });
  audit({ tenantId, actorId: s.user.id, actorName: s.user.name, action: `tenant.${to}`, target: t.name, detail: `Manual override: ${reason.trim()}` });
  billingEvent({ tenantId, type: to === "active" ? "reactivated" : "subscription_cancelled", detail: `Admin: ${reason.trim()}` });
  return ok(`${t.name} is now ${to}.`);
}

/** @returns the path to navigate to once impersonation starts. */
export function startViewAsAction(
  tenantId: string,
  reason: string,
  mode: ViewAsMode = "read_only",
): { path: string } | { error: string } {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "viewas.start")) {
    return { error: "Your console role can't enter a customer workspace." };
  }
  if (mode === "write" && !canInternal(s.user.internalRole, "viewas.elevate")) {
    return { error: "Only an Admin can enter a workspace with write access." };
  }
  if (reason.trim().length < 4) return { error: "A reason is required — it goes in the brand's own audit log." };
  try {
    startViewAs(s.user, tenantId, reason, mode);
  } catch {
    return { error: "Could not start the session." };
  }
  return { path: dashPath.portal };
}

/** @returns the path to navigate to once impersonation ends. */
export function stopViewAsAction(): string {
  const s = requireSession();
  stopViewAs(s.user);
  return dashPath.admin;
}

export function addAccountNoteAction(tenantId: string, formData: FormData): ActionResult {
  const s = requireSession();
  if (!canInternal(s.user.internalRole, "console.tenants.view")) return fail("Not allowed.");
  const note = String(formData.get("note") || "").trim();
  if (!note) return fail("Write a note first.");
  updateDb((db) => {
    const t = db.tenants.find((x) => x.id === tenantId);
    if (t) t.accountNotes.unshift({ at: nowIso(), by: s.user.name, note });
  });
  return ok();
}
