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

describe("photo measurement", () => {
  const capture = {
    captureId: "pm_1",
    state: "ready",
    stageLabel: "Your measurements are ready to review",
    heightCm: 168,
    weightKg: null,
    gender: "female",
    profile: {
      height_cm: 168,
      waist_circumference_cm: 70.5,
      bust_circumference_cm: 90,
      weight_kg: null,
      body_shape_type: "hourglass",
      skin_tone_hex: "#C8A08A",
    },
    measurements: { waist: 70.5 },
    warnings: ["side: arm appears to touch the torso"],
    failureReason: null,
    createdAt: "2026-10-04T00:00:00Z",
    completedAt: "2026-10-04T00:00:05Z",
    appliedAt: null,
  };

  it("uploads both photos with the form fields the backend expects", async () => {
    const postMultipart = vi.fn(async (_path: string, _schema: unknown, _form: FormData) => ({
      capture: { ...capture, state: "queued", profile: null },
    }));
    const provider = new HttpRuntimeProvider({ postMultipart } as unknown as MirraHttpClient);
    const front = new File(["f"], "front.jpg", { type: "image/jpeg" });
    const side = new File(["s"], "side.jpg", { type: "image/jpeg" });

    const started = await provider.startPhotoMeasurement({
      front,
      side,
      heightCm: 168,
      gender: "female",
      weightKg: null,
      shoeSoleCm: 3,
    });

    const [path, , form] = postMultipart.mock.calls[0];
    expect(path).toBe("/photo-measurements");
    expect(form.get("front")).toBeInstanceOf(File);
    expect(form.get("side")).toBeInstanceOf(File);
    expect(form.get("height_cm")).toBe("168");
    expect(form.get("gender")).toBe("female");
    expect(form.get("shoe_sole_cm")).toBe("3");
    expect(form.has("weight_kg")).toBe(false);
    expect(started.state).toBe("queued");
    expect(started.profile).toBeNull();
  });

  it("maps a ready capture into numeric fields plus shape and skin tone", async () => {
    const get = vi.fn(async () => ({ capture }));
    const provider = new HttpRuntimeProvider({ get } as unknown as MirraHttpClient);

    const result = await provider.getPhotoMeasurement("pm_1");

    expect(result.profile?.waist_circumference_cm).toBe(70.5);
    expect(result.profile?.weight_kg).toBeNull();
    expect(result.bodyShapeType).toBe("hourglass");
    expect(result.skinToneHex).toBe("#C8A08A");
    expect(result.warnings).toHaveLength(1);
  });

  it("applies corrections, then returns the refreshed profile", async () => {
    const post = vi.fn(async () => ({
      measurements: { height_cm: 168, waist_circumference_cm: 72 },
      capture: { ...capture, state: "applied" },
    }));
    const get = vi.fn(async (path: string) => {
      if (path === "/avatars/profile") return { profile: null };
      if (path === "/user-measurements/me")
        return { measurements: { height_cm: 168, waist_circumference_cm: 72 } };
      throw new Error(path);
    });
    const provider = new HttpRuntimeProvider({ post, get } as unknown as MirraHttpClient);

    const profile = await provider.applyPhotoMeasurement("pm_1", { waist_circumference_cm: 72 });

    expect(post).toHaveBeenCalledWith("/photo-measurements/pm_1/apply", expect.anything(), {
      overrides: { waist_circumference_cm: 72 },
    });
    expect(profile.measurements.find((f) => f.key === "waist")?.value).toBe(72);
  });
});
