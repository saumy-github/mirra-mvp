import { describe, expect, it } from "vitest";
import { onboardingStudioDestination, postAuthDestination, signupDestination } from "./post-auth";

describe("shopper navigation", () => {
  it("keeps new signup out of Profile", () => {
    expect(signupDestination()).toBe("/onboarding/qr");
    expect(signupDestination("/profile")).toBe("/onboarding/qr");
    expect(signupDestination("/profile/avatar")).toBe("/onboarding/qr");
    expect(signupDestination("/studio?product=coat")).toBe(
      "/onboarding/qr?next=%2Fstudio%3Fproduct%3Dcoat",
    );
  });
  it("returns to Studio after setup while preserving a safe product URL", () => {
    expect(onboardingStudioDestination("/studio?product=coat")).toBe("/studio?product=coat");
    for (const path of [
      undefined,
      "/",
      "/profile",
      "https://example.com",
      "//example.com",
      "javascript:alert(1)",
    ]) {
      expect(onboardingStudioDestination(path)).toBe("/studio");
    }
  });
  it("allows the standalone QR page through authentication", () => {
    expect(postAuthDestination("/onboarding/qr")).toBe("/onboarding/qr");
    expect(postAuthDestination()).toBe("/studio");
  });
});
