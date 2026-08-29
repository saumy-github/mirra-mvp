import type { Garment, Plan, Tenant } from "./types";
import { getDb } from "./store";
import { requirements } from "./ingestion";

// Entitlements are derived from (plan × add-ons × billing state), never stored
// as loose flags. Billing state changes flow through here automatically.
export interface Entitlements {
  skuLimit: number;
  seatLimit: number;
  supportTier: Plan["supportTier"];
  customDomainAllowed: boolean;
  analyticsPlus: boolean;
  scheduledGoLive: boolean;
  bulkPublishing: boolean;
  /** Master switch: can the public try-on surface serve content right now? */
  publicSurfaceEnabled: boolean;
  publicSurfaceDisabledReason?: string;
}

export function getPlan(tenant: Tenant): Plan {
  const plan = getDb().plans.find((p) => p.id === tenant.billing.planId);
  if (!plan) throw new Error(`Unknown plan ${tenant.billing.planId}`);
  return plan;
}

export function getEntitlements(tenant: Tenant): Entitlements {
  const plan = getPlan(tenant);
  const addOns = tenant.billing.addOns;
  const skuLimit = plan.skuLimit + (addOns.includes("extra_sku_pack") ? 100 : 0);

  let publicSurfaceEnabled = true;
  let reason: string | undefined;
  switch (tenant.status) {
    case "lead":
    case "onboarding":
      publicSurfaceEnabled = false;
      reason = "Tenant has not activated a subscription yet.";
      break;
    case "suspended":
      publicSurfaceEnabled = false;
      reason = "Subscription suspended (payment past due).";
      break;
    case "cancelled":
    case "archived":
      publicSurfaceEnabled = false;
      reason = "Subscription cancelled.";
      break;
    case "past_due":
      // grace: keep serving while dunning runs; suspension flips this off
      publicSurfaceEnabled = true;
      break;
  }
  if (publicSurfaceEnabled && tenant.launchStatus === "paused") {
    publicSurfaceEnabled = false;
    reason = "Try-on experience paused by the brand.";
  }
  if (publicSurfaceEnabled && tenant.launchStatus === "not_launched") {
    publicSurfaceEnabled = false;
    reason = "Try-on experience not launched yet.";
  }

  return {
    skuLimit,
    seatLimit: plan.seatLimit,
    supportTier: addOns.includes("premium_support") ? "priority" : plan.supportTier,
    customDomainAllowed: plan.id === "enterprise" || addOns.includes("custom_domain"),
    analyticsPlus: plan.id === "enterprise" || addOns.includes("analytics_plus"),
    scheduledGoLive: plan.id === "atelier" || plan.id === "enterprise",
    bulkPublishing: plan.id !== "pilot",
    publicSurfaceEnabled,
    publicSurfaceDisabledReason: reason,
  };
}

/**
 * Requirements a garment must meet before it can go live, as merchant-readable
 * labels. The real definition lives in `ingestion.requirements` — this is the
 * flattened view the tables use.
 */
export function missingRequirements(g: Garment): string[] {
  const product = getDb().products.find((p) => p.id === g.productId);
  return requirements(g, product)
    .filter((r) => r.blocking && !r.complete)
    .map((r) => r.label);
}

/**
 * The billable unit is a live SKU, counted from variants — not garment
 * records. A four-size colourway consumes four, which is what the plan
 * language says and what a merchant is charged for.
 *
 * The count itself lives in `publication.ts`, because "live" is a publication
 * question and answering it in two places is how the dashboard and the
 * storefront drifted apart. Import `liveSkuCount` from there.
 */
