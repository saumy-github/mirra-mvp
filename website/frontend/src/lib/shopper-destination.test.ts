import { describe, expect, it } from "vitest";
import { shopperDestination, oauthDestination } from "./shopper-destination";
describe("returning shopper routing", () => {
  it("opens Studio without fetching avatar or unfinished setup state", () => {
    expect(shopperDestination()).toBe("/studio");
    expect(shopperDestination("/studio?product=coat")).toBe("/studio?product=coat");
  });
  it("does not repeat onboarding when switching from signup to sign-in", () => {
    expect(shopperDestination("/onboarding/qr")).toBe("/studio");
    expect(shopperDestination("/onboarding/qr?next=%2Fstudio%3Fproduct%3Dcoat")).toBe(
      "/studio?product=coat",
    );
  });
  it("preserves an explicit profile destination and rejects external redirects", () => {
    expect(shopperDestination("/profile/avatar")).toBe("/profile/avatar");
    expect(shopperDestination("//example.com")).toBe("/studio");
    expect(shopperDestination("/onboarding/qr?next=https%3A%2F%2Fexample.com")).toBe("/studio");
  });
  it("starts Google onboarding only when the backend created a new account", () => {
    const next = "/onboarding/qr?next=%2Fstudio%3Fproduct%3Dcoat";
    expect(oauthDestination(next, true)).toBe(next);
    expect(oauthDestination(next, false)).toBe("/studio?product=coat");
    expect(oauthDestination("/profile", true)).toBe("/onboarding/qr");
  });
});
