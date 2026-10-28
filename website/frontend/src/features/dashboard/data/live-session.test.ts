/** A real workspace mirrored into the dashboard must not look like the demo. */
import { describe, expect, it, vi } from "vitest";

const store = new Map<string, string>();
vi.stubGlobal("window", {
  localStorage: {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
    removeItem: (k: string) => void store.delete(k),
  },
});

import { adoptWorkspace, isLiveTenant, liveCan } from "./live-session";
import { getSession } from "./session";
import { getEntitlements } from "./entitlements";
import { PORTAL_NAV } from "../components/nav-items";
import type { ShopperAccount } from "@/integrations/mirra-api";
import type { Workspace } from "./merchant-api";

const account = { shopperId: "u_real", email: "a@brand.com", displayName: "Ana", isGuest: false } as ShopperAccount;
const workspace = (role: string): Workspace => ({
  tenantId: `mt_${role}`,
  role,
  slug: "brand",
  name: "Brand",
  storeUrl: "",
  status: "trialing",
  shopify: {
    connected: false,
    storeDomain: "",
    customDomain: "",
    scopes: [],
    connectedAt: null,
    lastSyncAt: null,
    lastSyncError: "",
  },
});

describe("live workspace", () => {
  it("is signed in as itself and not reported offline", () => {
    adoptWorkspace(account, workspace("owner"));
    const session = getSession();
    expect(session?.tenant?.id).toBe("mt_owner");
    expect(isLiveTenant("mt_owner")).toBe(true);
    // The backend has no launch gate, so the shell's "offline" banner must not show.
    expect(getEntitlements(session!.tenant!).publicSurfaceEnabled).toBe(true);
  });

  it("follows the backend's role permissions, including the QA seat", () => {
    adoptWorkspace(account, workspace("editor"));
    expect(liveCan("mt_editor", "catalogue.edit")).toBe(true);
    expect(liveCan("mt_editor", "catalogue.publish")).toBe(false);
    adoptWorkspace(account, workspace("qa"));
    expect(liveCan("mt_qa", "qa.review")).toBe(true);
    expect(liveCan("mt_qa", "catalogue.edit")).toBe(false);
    expect(liveCan("t_demo", "catalogue.edit")).toBe(false);
  });

  it("has one entry point for garments", () => {
    expect(PORTAL_NAV.filter((n) => n.href.includes("/digitise"))).toHaveLength(0);
  });
});
