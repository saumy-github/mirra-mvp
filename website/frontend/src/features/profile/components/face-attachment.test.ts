import { describe, expect, it } from "vitest";
import { findHeadAnchor, placeFace, type Vec3 } from "./face-attachment";

/** A crude standing body: an elliptical column (head/torso/legs), a nose
 * bump at 1.66 m and feet with toes towards `forward`. */
function body(forward: 1 | -1, height = 1.78): Vec3[] {
  const pts: Vec3[] = [];
  for (let y = 0.05; y <= height; y += 0.005) {
    const head = y > height - 0.24;
    const r = head ? 0.075 : 0.16;
    for (let a = 0; a < Math.PI * 2; a += Math.PI / 24) {
      pts.push([r * Math.cos(a), y, 0.8 * r * Math.sin(a)]);
    }
  }
  const noseY = height - 0.115;
  for (let dy = -0.02; dy <= 0.02; dy += 0.005)
    pts.push([0, noseY + dy, forward * (0.06 + 0.025 - Math.abs(dy))]);
  for (let z = -0.05; z <= 0.2; z += 0.005) {
    pts.push([0.1, 0.01, forward * z], [-0.1, 0.01, forward * z]);
  }
  return pts;
}

describe("face attachment", () => {
  it("finds the nose and which way the avatar faces", () => {
    for (const forward of [1, -1] as const) {
      const anchor = findHeadAnchor(body(forward))!;
      expect(anchor.forward).toBe(forward);
      expect(anchor.nose[1]).toBeCloseTo(1.78 - 0.115, 2);
      expect(anchor.nose[2] * forward).toBeCloseTo(0.085, 3);
      expect(anchor.headWidth).toBeGreaterThan(0.12);
      expect(anchor.headWidth).toBeLessThan(0.16);
    }
  });

  it("puts the face's nose tip just in front of the avatar's", () => {
    const face = { noseTip: [0, -0.006, 0.082] as Vec3, widthM: 0.139 };
    for (const forward of [1, -1] as const) {
      const anchor = findHeadAnchor(body(forward))!;
      const p = placeFace(anchor, face);
      const rotated = forward === 1 ? face.noseTip : ([0, -0.006, -0.082] as Vec3);
      const worldNose = rotated.map((c, i) => p.position[i] + p.scale * c);
      expect(worldNose[1]).toBeCloseTo(anchor.nose[1], 4);
      expect((worldNose[2] - anchor.nose[2]) * forward).toBeCloseTo(0.004, 4);
      expect(p.yaw).toBe(forward === 1 ? 0 : Math.PI);
    }
  });

  it("shrinks a face wider than the head, never enlarges one", () => {
    const anchor = { nose: [0, 1.6, 0.1] as Vec3, forward: 1 as const, headWidth: 0.12 };
    expect(placeFace(anchor, { noseTip: [0, 0, 0.08], widthM: 0.16 }).scale).toBeCloseTo(0.75, 2);
    expect(
      placeFace({ ...anchor, headWidth: 0.3 }, { noseTip: [0, 0, 0.08], widthM: 0.14 }).scale,
    ).toBe(1);
  });

  it("refuses things that are not a full standing body", () => {
    expect(findHeadAnchor([])).toBeNull();
    expect(findHeadAnchor(body(1, 0.3))).toBeNull();
  });
});
