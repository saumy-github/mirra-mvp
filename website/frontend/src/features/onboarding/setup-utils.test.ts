import { describe, expect, it } from "vitest";
import { rememberCaptureLink, storedCaptureLink } from "./setup-utils";

function memory() {
  const data = new Map<string, string>();
  return {
    getItem: (k: string) => data.get(k) ?? null,
    setItem: (k: string, v: string) => void data.set(k, v),
  };
}

describe("capture link reuse", () => {
  const now = Date.parse("2026-10-06T10:00:00Z");

  it("reuses a stored link until shortly before it expires", () => {
    const storage = memory();
    rememberCaptureLink("p1", { token: "abc", expiresAt: "2026-10-06T10:20:00Z" }, storage);
    expect(storedCaptureLink("p1", now, storage)).toEqual({
      token: "abc",
      expiresAt: "2026-10-06T10:20:00Z",
    });
    // Inside the one-minute margin the link is treated as expired.
    expect(storedCaptureLink("p1", Date.parse("2026-10-06T10:19:30Z"), storage)).toBeNull();
  });

  it("keeps pairings separate and ignores links without a token", () => {
    const storage = memory();
    rememberCaptureLink("p1", { expiresAt: "2026-10-06T10:20:00Z" }, storage);
    expect(storedCaptureLink("p1", now, storage)).toBeNull();
    rememberCaptureLink("p2", { token: "xyz", expiresAt: "2026-10-06T10:20:00Z" }, storage);
    expect(storedCaptureLink("p1", now, storage)).toBeNull();
    expect(storedCaptureLink("p2", now, storage)?.token).toBe("xyz");
  });

  it("survives corrupt or missing storage", () => {
    const storage = memory();
    storage.setItem("mirra-capture-link-p1", "{not json");
    expect(storedCaptureLink("p1", now, storage)).toBeNull();
    expect(storedCaptureLink("p1", now, undefined)).toBeNull();
  });
});
