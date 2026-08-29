import type { BrandRole, InternalRole, Role } from "./types";

// Capability-based RBAC. UI and actions both check capabilities, never raw
// roles, so adding org-aware roles later is additive.
export type Capability =
  | "catalogue.view"
  | "catalogue.edit"
  | "publication.manage"
  | "team.view"
  | "team.manage"
  | "billing.view"
  | "billing.manage"
  | "support.create"
  | "analytics.view"
  | "settings.view"
  | "settings.manage"
  | "audit.view";

const BRAND_GRANTS: Record<BrandRole, Capability[]> = {
  brand_owner: [
    "catalogue.view", "catalogue.edit", "publication.manage", "team.view", "team.manage",
    "billing.view", "billing.manage", "support.create", "analytics.view",
    "settings.view", "settings.manage", "audit.view",
  ],
  brand_merchandiser: [
    "catalogue.view", "catalogue.edit", "publication.manage", "team.view",
    "support.create", "analytics.view", "settings.view",
  ],
  brand_finance: ["billing.view", "billing.manage", "support.create", "analytics.view", "team.view"],
  brand_viewer: ["catalogue.view", "analytics.view", "audit.view"],
};

/**
 * Brand capability check.
 *
 * Internal roles are deliberately NOT short-circuited to `true` here. Staff
 * enter a workspace through view-as, which hands them an explicit brand role
 * (read-only by default) — see `session.effectiveRole`. Granting every
 * internal role blanket brand access was how a Sales user reached "pause the
 * tenant page" and "cancel the subscription".
 */
export function can(role: Role | null, cap: Capability): boolean {
  if (!role) return false;
  if (role === "mirra_admin" || role === "mirra_sales" || role === "mirra_support") return false;
  return BRAND_GRANTS[role]?.includes(cap) ?? false;
}

// ------------------------------------------------------------ staff console

/**
 * What Mirra staff can do in the internal console. Separate from brand
 * capabilities on purpose: they are different systems with different blast
 * radii, and conflating them is what let console access imply tenant control.
 */
export type InternalCapability =
  | "console.tenants.view"
  | "console.tenants.manage" // suspend, reactivate, archive — lifecycle overrides
  | "console.leads.view"
  | "console.leads.manage"
  | "console.support.view"
  | "console.support.manage" // assign, reply, change status
  | "console.sync.view"
  | "console.sync.manage" // retry, resolve conflicts
  | "console.churn.view"
  | "console.qa.decide"
  | "viewas.start"
  | "viewas.elevate"; // enter a workspace with write access

const INTERNAL_GRANTS: Record<InternalRole, InternalCapability[]> = {
  mirra_admin: [
    "console.tenants.view", "console.tenants.manage",
    "console.leads.view", "console.leads.manage",
    "console.support.view", "console.support.manage",
    "console.sync.view", "console.sync.manage",
    "console.churn.view", "console.qa.decide",
    "viewas.start", "viewas.elevate",
  ],
  mirra_support: [
    "console.tenants.view",
    "console.leads.view",
    "console.support.view", "console.support.manage",
    "console.sync.view", "console.sync.manage",
    "console.churn.view", "console.qa.decide",
    "viewas.start",
  ],
  // Sales qualify and convert leads. They do not operate tenants, touch
  // support, retry syncs, decide QA, or write inside a customer workspace.
  mirra_sales: [
    "console.tenants.view",
    "console.leads.view", "console.leads.manage",
    "console.churn.view",
    "viewas.start",
  ],
};

export function canInternal(role: InternalRole | undefined, cap: InternalCapability): boolean {
  if (!role) return false;
  return INTERNAL_GRANTS[role].includes(cap);
}

export const ROLE_LABELS: Record<Role, string> = {
  mirra_admin: "Mirra Admin",
  mirra_sales: "Mirra Sales",
  mirra_support: "Mirra Support",
  brand_owner: "Owner",
  brand_merchandiser: "Merchandiser",
  brand_finance: "Finance",
  brand_viewer: "Viewer",
};
