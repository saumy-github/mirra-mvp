import { Box3, Mesh, Object3D, SkinnedMesh, Vector3 } from "three";

/**
 * Where to put the shopper's face mesh (backend `faces`, face_reconstruction/)
 * on an avatar or try-on GLB. The avatar comes from CLO with no landmarks, so
 * the head is found from the geometry itself:
 *
 *   nose      the front-most point at nose height, near the body's centre line
 *   forward   which way the toes point (heels are short, toes long)
 *   width     the head's width at cheek height
 *
 * and the face is placed nose-tip on nose-tip, slightly proud of the skin so
 * the stock face never shows through, shrunk only if it is wider than the head.
 * Pure functions over a point list, so they are unit-tested without WebGL.
 */

export type Vec3 = [number, number, number];

export interface FaceInfo {
  /** Nose tip in the face mesh's own frame (metres, +Z out of the face). */
  noseTip: Vec3;
  widthM: number;
}

export interface HeadAnchor {
  nose: Vec3;
  /** +1 when the avatar faces +Z, -1 when it faces -Z. */
  forward: 1 | -1;
  headWidth: number;
}

export interface FacePlacement {
  position: Vec3;
  yaw: number;
  scale: number;
}

// Fractions of total height, measured down from the top of the head.
const NOSE_BAND = [0.045, 0.1] as const;
const CHEEK_BAND = [0.055, 0.085] as const;
const FEET_BAND = 0.04; // from the floor up
const CENTRE_LINE_M = 0.06; // the nose is within this of the body's centre line
const SKIN_OFFSET_M = 0.004;

function percentile(sorted: number[], p: number) {
  if (!sorted.length) return NaN;
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(p * (sorted.length - 1))))];
}

export function findHeadAnchor(points: Vec3[]): HeadAnchor | null {
  if (points.length < 100) return null;
  let minY = Infinity;
  let maxY = -Infinity;
  for (const p of points) {
    if (p[1] < minY) minY = p[1];
    if (p[1] > maxY) maxY = p[1];
  }
  const h = maxY - minY;
  if (!(h > 0.5)) return null; // not a full body (or not in metres)

  const inBand = (p: Vec3, band: readonly [number, number]) =>
    p[1] <= maxY - band[0] * h && p[1] >= maxY - band[1] * h;

  const feet = points.filter((p) => p[1] <= minY + FEET_BAND * h);
  const feetZ = feet.map((p) => p[2]).sort((a, b) => a - b);
  const zMid = percentile(feetZ, 0.5);
  const forward: 1 | -1 = percentile(feetZ, 0.99) - zMid >= zMid - percentile(feetZ, 0.01) ? 1 : -1;

  const head = points.filter((p) => inBand(p, NOSE_BAND));
  if (head.length < 20) return null;
  const xs = head.map((p) => p[0]).sort((a, b) => a - b);
  const cx = percentile(xs, 0.5);
  let nose: Vec3 | null = null;
  for (const p of head) {
    if (Math.abs(p[0] - cx) > CENTRE_LINE_M) continue;
    if (!nose || p[2] * forward > nose[2] * forward) nose = p;
  }
  if (!nose) return null;

  const cheeks = points
    .filter((p) => inBand(p, CHEEK_BAND) && Math.abs(p[0] - cx) < 0.15)
    .map((p) => p[0])
    .sort((a, b) => a - b);
  const headWidth = percentile(cheeks, 0.97) - percentile(cheeks, 0.03);
  return { nose, forward, headWidth: Number.isFinite(headWidth) ? headWidth : 0.15 };
}

export function placeFace(anchor: HeadAnchor, face: FaceInfo): FacePlacement {
  const yaw = anchor.forward === 1 ? 0 : Math.PI;
  // Never enlarge (the face is already at its measured size); shrink only if
  // it would overhang the avatar's head.
  const scale =
    anchor.headWidth > 0 ? Math.min(1, Math.max(0.75, (0.95 * anchor.headWidth) / face.widthM)) : 1;
  const [nx, ny, nz] = face.noseTip;
  const rotated: Vec3 = anchor.forward === 1 ? [nx, ny, nz] : [-nx, ny, -nz];
  return {
    position: [
      anchor.nose[0] - scale * rotated[0],
      anchor.nose[1] - scale * rotated[1],
      anchor.nose[2] - scale * rotated[2] + anchor.forward * SKIN_OFFSET_M,
    ],
    yaw,
    scale,
  };
}

/** World-space vertex positions of every mesh under `root` (skinning applied),
 * subsampled to at most `maxPoints`. */
export function collectWorldPoints(root: Object3D, maxPoints = 80_000): Vec3[] {
  root.updateMatrixWorld(true);
  const meshes: Mesh[] = [];
  let total = 0;
  root.traverse((o) => {
    const m = o as Mesh;
    if (m.isMesh && m.geometry?.attributes.position) {
      meshes.push(m);
      total += m.geometry.attributes.position.count;
    }
  });
  const stride = Math.max(1, Math.ceil(total / maxPoints));
  const out: Vec3[] = [];
  const v = new Vector3();
  for (const m of meshes) {
    const pos = m.geometry.attributes.position;
    const skinned = (m as SkinnedMesh).isSkinnedMesh ? (m as SkinnedMesh) : null;
    for (let i = 0; i < pos.count; i += stride) {
      v.fromBufferAttribute(pos, i);
      if (skinned) skinned.applyBoneTransform(i, v);
      v.applyMatrix4(m.matrixWorld);
      out.push([v.x, v.y, v.z]);
    }
  }
  return out;
}

/** Convenience for the viewer: anchor from a loaded avatar scene, or null. */
export function headAnchorFor(root: Object3D): HeadAnchor | null {
  const box = new Box3().setFromObject(root);
  if (box.isEmpty()) return null;
  return findHeadAnchor(collectWorldPoints(root));
}
