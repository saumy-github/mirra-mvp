import type { TenantStatus } from "./types";

// ------------------------------------------------------ tenant lifecycle FSM
// lead → onboarding → trial → active ⇄ past_due → suspended → cancelled → archived
// with reactivation paths back to active. Transitions are the only way status
// changes; provisioning/deprovisioning side-effects hang off transitions.

export const TENANT_TRANSITIONS: Record<TenantStatus, TenantStatus[]> = {
  lead: ["onboarding"],
  onboarding: ["trial", "active", "cancelled"],
  trial: ["active", "cancelled", "suspended"],
  active: ["past_due", "cancelled"],
  past_due: ["active", "suspended"],
  suspended: ["active", "cancelled"],
  cancelled: ["active", "archived"], // reactivation within grace period
  archived: [],
};

export function canTransitionTenant(from: TenantStatus, to: TenantStatus): boolean {
  return TENANT_TRANSITIONS[from]?.includes(to) ?? false;
}

export const TENANT_STATUS_META: Record<
  TenantStatus,
  { label: string; tone: "neutral" | "info" | "success" | "warn" | "danger" }
> = {
  lead: { label: "Lead", tone: "neutral" },
  onboarding: { label: "Onboarding", tone: "info" },
  trial: { label: "Trial", tone: "info" },
  active: { label: "Active", tone: "success" },
  past_due: { label: "Past due", tone: "warn" },
  suspended: { label: "Suspended", tone: "danger" },
  cancelled: { label: "Cancelled", tone: "danger" },
  archived: { label: "Archived", tone: "neutral" },
};

// The garment lifecycle moved to `ingestion.ts` as a single `GarmentStage`
// machine — see STAGE_META and MERCHANT_TRANSITIONS there. This module is now
// only the tenant/subscription FSM.
