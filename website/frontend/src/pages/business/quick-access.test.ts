import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const storage = new Map<string, string>();
const fetchSpy = vi.fn();

beforeEach(() => {
  vi.resetModules();
  vi.stubEnv("DEV", true);
  storage.clear();
  fetchSpy.mockReset();
  vi.stubGlobal("fetch", fetchSpy);
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => void storage.set(key, value),
      removeItem: (key: string) => void storage.delete(key),
    },
  });
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("temporary business Quick Access", () => {
  it("opens an active brand owner workspace without a backend guest login", async () => {
    const { enterBusinessDemo } = await import("./quick-access");
    expect(await enterBusinessDemo()).toBe("/dashboard/portal");

    const { getSession } = await import("@/features/dashboard/data/session");
    expect(getSession()).toMatchObject({
      user: { id: "u_owner" },
      tenant: { id: "t_atelier", onboarding: { activated: true } },
      role: "brand_owner",
      isInternal: false,
      impersonating: false,
    });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it.each([
    ["/dashboard/portal/garments?stage=live#list", "/dashboard/portal/garments?stage=live#list"],
    ["/dashboard/start?demo=1", "/dashboard/portal?demo=1"],
    ["/studio", "/dashboard/portal"],
    ["/dashboard/admin", "/dashboard/portal"],
    ["https://example.com/dashboard/portal", "/dashboard/portal"],
    ["//example.com/dashboard/portal", "/dashboard/portal"],
  ])("keeps the business redirect safe for %s", async (next, expected) => {
    const { enterBusinessDemo } = await import("./quick-access");
    expect(await enterBusinessDemo(next)).toBe(expected);
  });

  it("restores the demo workspace after a reload and clears it on sign-out", async () => {
    const { enterBusinessDemo } = await import("./quick-access");
    await enterBusinessDemo();
    vi.resetModules();

    const { getSession, signOut } = await import("@/features/dashboard/data/session");
    expect(getSession()?.tenant?.id).toBe("t_atelier");
    signOut();
    expect(getSession()).toBeNull();
    expect(storage.has("mirra.dashboard.session")).toBe(false);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("disables Quick Access in production without establishing a session", async () => {
    vi.stubEnv("DEV", false);
    const { businessQuickAccessEnabled, enterBusinessDemo } = await import("./quick-access");
    expect(businessQuickAccessEnabled).toBe(false);
    await expect(enterBusinessDemo()).rejects.toThrow("only available in development");
    expect(storage.size).toBe(0);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
