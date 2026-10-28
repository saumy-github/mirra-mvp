// Real business sessions for the dashboard.
//
// `session.ts` is a persona switcher over the in-memory demo store, and every
// dashboard page reads its tenant from there. Rather than rewrite all of them,
// a signed-in business account is *mirrored* into that store: its backend
// user id, its real workspace (tenant id from /api/v1/merchant) and its role.
// Pages that are already server-backed (Digitise, capture, pipeline, Shopify)
// then call the real API with the real tenant id, and the demo-only pages
// render this tenant's (empty) demo data instead of someone else's.
//
// Auth is the shared backend session (same JWT/refresh cookie as /auth and
// /business sign-in); there is no separate merchant login.
import { getRuntimeProvider, type ShopperAccount } from "@/integrations/mirra-api";
import { merchantApi, type Workspace } from "./merchant-api";
import { signIn } from "./session";
import { updateDb } from "./store";
import type { BrandRole, Tenant, TenantStatus } from "./types";

export type LiveBootstrap =
  | { status: "signed_out" }
  | { status: "no_workspace"; account: ShopperAccount }
  | { status: "ready"; tenantId: string };

/** Live tenant id → the caller's backend role there (owner/admin/editor/viewer/qa). */
const LIVE_TENANTS = new Map<string, string>();

/** True for a tenant that exists in the backend (vs the seeded demo tenants). */
export function isLiveTenant(tenantId: string | undefined | null): boolean {
  return !!tenantId && LIVE_TENANTS.has(tenantId);
}

// Mirrors ROLE_PERMISSIONS in backend/src/merchant/service.py; the server still enforces it.
const BACKEND_PERMISSIONS: Record<string, string[]> = {
  owner: ["catalogue.edit", "catalogue.publish", "settings.edit", "qa.review"],
  admin: ["catalogue.edit", "catalogue.publish", "settings.edit"],
  editor: ["catalogue.edit"],
  viewer: [],
  qa: ["qa.review"],
};

export type LivePermission = "catalogue.edit" | "catalogue.publish" | "settings.edit" | "qa.review";

export function liveCan(tenantId: string | undefined | null, permission: LivePermission): boolean {
  const role = tenantId ? LIVE_TENANTS.get(tenantId) : undefined;
  return !!role && (BACKEND_PERMISSIONS[role] ?? []).includes(permission);
}

const ROLE_MAP: Record<string, BrandRole> = {
  owner: "brand_owner",
  admin: "brand_merchandiser",
  editor: "brand_merchandiser",
  viewer: "brand_viewer",
  qa: "brand_viewer",
};

const STATUS_MAP: Record<string, TenantStatus> = {
  trialing: "trial",
  active: "active",
  suspended: "suspended",
  cancelled: "cancelled",
};

export async function bootstrapLiveSession(): Promise<LiveBootstrap> {
  const account = await getRuntimeProvider().getCurrentShopper();
  if (!account || account.isGuest) return { status: "signed_out" };
  const workspaces = await merchantApi.listWorkspaces();
  if (workspaces.length === 0) return { status: "no_workspace", account };
  adoptWorkspace(account, workspaces[0]);
  return { status: "ready", tenantId: workspaces[0].tenantId };
}

export async function createLiveWorkspace(
  account: ShopperAccount,
  input: { name: string; storeUrl?: string },
): Promise<Workspace> {
  const workspace = await merchantApi.createWorkspace(input);
  adoptWorkspace(account, workspace);
  return workspace;
}

/** Mirror the backend workspace into the dashboard store and sign in as it. */
export function adoptWorkspace(account: ShopperAccount, ws: Workspace) {
  LIVE_TENANTS.set(ws.tenantId, ws.role ?? "viewer");
  updateDb((db) => {
    const user = {
      id: account.shopperId,
      name: account.displayName || account.email,
      email: account.email,
    };
    const u = db.users.findIndex((x) => x.id === user.id);
    if (u >= 0) db.users[u] = { ...db.users[u], ...user };
    else db.users.push(user);

    const existing = db.tenants.find((t) => t.id === ws.tenantId);
    const tenant = tenantFromWorkspace(ws, existing);
    if (existing) Object.assign(existing, tenant);
    else db.tenants.push(tenant);

    const role = ROLE_MAP[ws.role ?? ""] ?? "brand_viewer";
    db.memberships = db.memberships.filter((m) => m.userId !== user.id);
    db.memberships.push({ userId: user.id, tenantId: ws.tenantId, role, status: "active" });
  });
  signIn(account.shopperId);
}

/** Refresh the mirrored tenant after a server-side change (e.g. Shopify connected). */
export function refreshWorkspace(ws: Workspace) {
  updateDb((db) => {
    const existing = db.tenants.find((t) => t.id === ws.tenantId);
    if (existing) Object.assign(existing, tenantFromWorkspace(ws, existing));
  });
}

function tenantFromWorkspace(ws: Workspace, existing?: Tenant): Tenant {
  const shopifyConnected = ws.shopify.connected;
  return {
    // Demo-only fields (billing, theme, notes…) have no backend yet; keep any
    // the merchant already set in this session, otherwise neutral defaults.
    billing: { planId: "pilot", interval: "monthly", addOns: [], paymentStatus: "trialing" },
    theme: {
      brandColor: "#141414",
      accentColor: "#8A7A66",
      logoText: ws.name.toUpperCase(),
      welcomeHeadline: "See it on you before it ships.",
    },
    defaults: {
      soldOutPolicy: "keep_tryon",
      hideColourwayWhenAllSoldOut: false,
      brandSizeCharts: [],
    },
    healthScore: 100,
    churnRisk: "low",
    accountNotes: [],
    salesLed: false,
    createdAt: new Date().toISOString(),
    previewToken: `pvt_${ws.slug}`,
    ...existing,
    // Backend-owned fields always win.
    id: ws.tenantId,
    slug: ws.slug,
    name: ws.name,
    storeUrl: ws.storeUrl,
    status: STATUS_MAP[ws.status] ?? "trial",
    // The backend has no launch gate: a published garment serves unless the
    // workspace is suspended or cancelled, which `status` already carries.
    launchStatus: "live",
    storeOwnershipVerified: shopifyConnected,
    domain: {
      subdomain: `${ws.slug}.vto.mirra.com`,
      customDomain: ws.shopify.customDomain || undefined,
    },
    onboarding: {
      storeVerified: shopifyConnected,
      storeUrlConfirmed: Boolean(ws.storeUrl || ws.shopify.storeDomain),
      shopifyConnected,
      // Plans, billing and terms are not part of the pilot backend; they must
      // not gate a real workspace out of its own portal.
      teamInvited: true,
      planChosen: true,
      termsAccepted: true,
      billingEntered: true,
      activated: true,
      checklistReviewed: true,
    },
  };
}
