import { describe, expect, it, vi } from "vitest";
import { MirraHttpClient } from "./client";
import { MirraApiError } from "./errors";
import { HttpRuntimeProvider } from "./http-runtime-provider";

describe("saved fit profile recovery", () => {
  it("keeps measurements available before the first avatar job after a reload", async () => {
    const get = vi.fn(async (path: string) => {
      if (path === "/avatars/profile") return { profile: null };
      if (path === "/user-measurements/me") {
        return {
          measurements: {
            height_cm: 182,
            weight_kg: 74,
            units_preference: "imperial",
            createdAt: "2026-09-01T00:00:00Z",
            updatedAt: "2026-09-30T00:00:00Z",
          },
        };
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    const provider = new HttpRuntimeProvider({ get } as unknown as MirraHttpClient);

    const profile = await provider.getAvatarProfile();

    expect(get.mock.calls.map(([path]) => path)).toEqual([
      "/avatars/profile",
      "/user-measurements/me",
    ]);
    expect(profile?.version).toBe(0);
    expect(profile?.measurements.find((field) => field.key === "height")?.value).toBe(182);
    expect(profile?.unitsPreference).toBe("imperial");
    expect(profile?.updatedAt).toBe("2026-09-30T00:00:00Z");
  });

  it("returns an empty setup state only when no measurements are saved", async () => {
    const get = vi.fn(async (path: string) => {
      if (path === "/avatars/profile") return { profile: null };
      throw new MirraApiError("product_not_found", "Not found", 404);
    });
    const provider = new HttpRuntimeProvider({ get } as unknown as MirraHttpClient);

    await expect(provider.getAvatarProfile()).resolves.toBeNull();
  });
});
