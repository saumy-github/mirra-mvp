"""Landmarks from 1-3 photos -> one metric face mesh with a photo texture.

    per view: pixel landmarks -> y-up / z-towards-camera frame -> metric scale
              (iris diameter) -> rigid alignment onto the canonical face
    fuse:     per-vertex weighted mean, weighted by how squarely each view saw it
    texture:  every canonical triangle warped from each photo into the UV atlas,
              weighted by facing; side views colour-matched to the front;
              alpha feathered towards the mesh edge so it blends onto a head

Everything here is numpy/OpenCV on the observations, so it is tested without
running MediaPipe (see tests/).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from . import canonical as C
from .landmarks import FaceObservation

N = 468                      # mesh vertices; landmarks 468-477 are irises
ATLAS = 1024
FEATHER_PX = 40              # alpha ramp width at the atlas edge
MIN_FACING = 0.3             # texture only from triangles a photo sees at < ~70°; the
                             # rest (face rim) is filled from neighbouring skin, not background
MAX_DEPTH_GAIN = 0.15        # monocular depth: keep relief within ±15% of an average face


@dataclass
class FaceReconstruction:
    vertices: np.ndarray                 # (468, 3) metres, canonical frame (+Y up, +Z out of the face)
    texture: np.ndarray                  # (ATLAS, ATLAS, 4) RGBA uint8
    skin_tone_hex: str | None
    scale_source: str                    # "iris" | "canonical"
    views: list[str]
    warnings: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ geometry


def _to_camera_frame(points: np.ndarray) -> np.ndarray:
    """Image pixels (y down, z away from camera) -> y up, z towards the camera."""
    return np.stack([points[:, 0], -points[:, 1], -points[:, 2]], 1)


def _iris_diameter_px(points: np.ndarray) -> float | None:
    if len(points) < 478:
        return None
    ds = []
    for iris in (C.RIGHT_IRIS, C.LEFT_IRIS):
        b = points[list(iris[1:]), :2]
        ds += [np.linalg.norm(b[0] - b[2]), np.linalg.norm(b[1] - b[3])]
    d = float(np.median(ds))
    return d if d > 1 else None


def _kabsch(src: np.ndarray, dst: np.ndarray, with_scale: bool):
    """Best (s, R, t) with dst ≈ s R src + t."""
    mu_s, mu_d = src.mean(0), dst.mean(0)
    a, b = src - mu_s, dst - mu_d
    u, sig, vt = np.linalg.svd(a.T @ b)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    corr = np.diag([1, 1, d])
    r = vt.T @ corr @ u.T
    s = float((sig * np.diag(corr)).sum() / (a ** 2).sum()) if with_scale else 1.0
    return s, r, mu_d - s * r @ mu_s


def align_view(points: np.ndarray, warnings: list[str], view: str):
    """One view's landmarks in canonical-frame centimetres.

    Returns (aligned (468,3) cm, rotation R camera->canonical, cm_per_px, source)."""
    canon = C.load().vertices
    cam = _to_camera_frame(points[:N])
    s_proc, _, _ = _kabsch(cam, canon, with_scale=True)       # cm per px if this face were canonical-sized
    iris = _iris_diameter_px(points)
    source = "canonical"
    cm_per_px = s_proc
    if iris is not None and view == "front":
        s_iris = C.IRIS_DIAMETER_CM / iris
        # The iris is ~1-2 px wide error on a small photo; trust it only when
        # it gives a plausible head (within 25% of an average face).
        if 0.75 <= s_iris / s_proc <= 1.25:
            cm_per_px, source = s_iris, "iris"
        else:
            warnings.append(f"{view}: iris size implausible, using average face scale")
    _, r, t = _kabsch(cam * cm_per_px, canon, with_scale=False)
    aligned = (cam * cm_per_px) @ r.T + t
    # Single-photo depth is the least reliable axis (an in-plane-rotated or
    # wide-angle photo inflates it). Keep the person's relief, bounded.
    za, zc = aligned[:, 2] - aligned[:, 2].mean(), canon[:, 2] - canon[:, 2].mean()
    gain = float((za * zc).sum() / (zc * zc).sum())
    bounded = min(max(gain, 1 - MAX_DEPTH_GAIN), 1 + MAX_DEPTH_GAIN)
    if gain > 0 and abs(bounded - gain) > 1e-6:
        aligned[:, 2] = aligned[:, 2].mean() + za * (bounded / gain)
        warnings.append(f"{view}: depth relief {gain:.2f}x an average face, limited to {bounded:.2f}x")
    return aligned, r, cm_per_px, source


def vertex_normals(v: np.ndarray, f: np.ndarray) -> np.ndarray:
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    n = np.zeros_like(v)
    for k in range(3):
        np.add.at(n, f[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def _orient_faces(v: np.ndarray, f: np.ndarray) -> np.ndarray:
    """Make triangle winding give outward (+Z-ish, away from the head centre) normals."""
    fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
    centre = v.mean(0) - np.array([0.0, 0.0, 6.0])        # a point inside the head
    outward = ((v[f].mean(1) - centre) * fn).sum(1) > 0
    f = f.copy()
    f[~outward] = f[~outward][:, [0, 2, 1]]
    return f


# ------------------------------------------------------------------- texture


def _warp_triangle(src_img, src_tri, dst, dst_w, dst_tri, weight):
    """Accumulate weight * src triangle into dst (float RGB) and dst_w."""
    r = cv2.boundingRect(np.float32(dst_tri))
    x, y, w, h = r
    if w <= 0 or h <= 0:
        return
    x2, y2 = min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    x, y = max(x, 0), max(y, 0)
    w, h = x2 - x, y2 - y
    if w <= 0 or h <= 0:
        return
    sr = cv2.boundingRect(np.float32(src_tri))
    sx, sy, sw, sh = sr
    sx, sy = max(sx, 0), max(sy, 0)
    sw = min(sw, src_img.shape[1] - sx)
    sh = min(sh, src_img.shape[0] - sy)
    if sw <= 1 or sh <= 1:
        return
    patch = src_img[sy:sy + sh, sx:sx + sw]
    m = cv2.getAffineTransform(np.float32(src_tri - [sx, sy]), np.float32(dst_tri - [x, y]))
    warped = cv2.warpAffine(patch, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    mask = np.zeros((h, w), np.float32)
    cv2.fillConvexPoly(mask, np.int32(np.round(dst_tri - [x, y])), 1.0, lineType=cv2.LINE_8)
    mw = mask * weight
    dst[y:y + h, x:x + w] += warped.astype(np.float32) * mw[..., None]
    dst_w[y:y + h, x:x + w] += mw


def _bake_view(obs: FaceObservation, facing: np.ndarray, size: int):
    canon = C.load()
    uv_px = np.stack([canon.uvs[:, 0] * (size - 1), (1 - canon.uvs[:, 1]) * (size - 1)], 1)
    img_px = obs.points[:N, :2]
    acc = np.zeros((size, size, 3), np.float32)
    wsum = np.zeros((size, size), np.float32)
    for t, (f, fu) in enumerate(zip(canon.faces, canon.face_uvs)):
        if facing[t] < MIN_FACING:
            continue
        _warp_triangle(obs.image, img_px[f], acc, wsum, uv_px[fu], facing[t] ** 2)
    return acc, wsum


def _triangle_facing(points: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """cos(angle) between each triangle's outward normal and the camera direction."""
    cam = _to_camera_frame(points[:N])
    fn = np.cross(cam[faces[:, 1]] - cam[faces[:, 0]], cam[faces[:, 2]] - cam[faces[:, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    return np.clip(fn[:, 2], 0, 1)          # camera looks down -Z in this frame


def bake_texture(observations: list[FaceObservation], faces: np.ndarray, size: int = ATLAS):
    """Blend all views into one atlas. Returns (RGBA uint8, coverage mask)."""
    layers = []
    for obs in observations:
        acc, w = _bake_view(obs, _triangle_facing(obs.points, faces), size)
        layers.append((obs.view, acc, w))

    # Lighting differs between photos: scale each side view's colour to the
    # front view's over the texels both of them saw well.
    front = next((l for l in layers if l[0] == "front"), layers[0])
    f_rgb = front[1] / np.maximum(front[2], 1e-6)[..., None]
    for i, (view, acc, w) in enumerate(layers):
        if acc is front[1]:
            continue
        both = (w > 0.2) & (front[2] > 0.2)
        if both.sum() > 500:
            rgb = acc / np.maximum(w, 1e-6)[..., None]
            gain = f_rgb[both].mean(0) / np.maximum(rgb[both].mean(0), 1.0)
            layers[i] = (view, acc * np.clip(gain, 0.6, 1.6), w)

    acc = sum(l[1] for l in layers)
    wsum = sum(l[2] for l in layers)
    covered = wsum > 1e-4
    rgb = np.zeros((size, size, 3), np.float32)
    rgb[covered] = acc[covered] / wsum[covered][:, None]

    # Fill uncovered texels by dilation so bilinear sampling at seams never
    # pulls in black.
    rgb8 = np.clip(rgb, 0, 255).astype(np.uint8)
    hole = (~covered).astype(np.uint8)
    if covered.any():
        rgb8 = cv2.inpaint(rgb8, hole, 3, cv2.INPAINT_TELEA)
        # Inpainting streaks across large rim areas; soften only what was filled.
        soft = cv2.GaussianBlur(rgb8, (0, 0), 12)
        fill = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 4)[..., None]
        rgb8 = (rgb8 * (1 - fill) + soft * fill).astype(np.uint8)

    # Alpha: opaque inside, ramping to 0 over FEATHER_PX at the outer edge of
    # the mesh's UV footprint (holes inside it — eyes, mouth — stay opaque).
    canon = C.load()
    footprint = np.zeros((size, size), np.uint8)
    uv_px = np.stack([canon.uvs[:, 0] * (size - 1), (1 - canon.uvs[:, 1]) * (size - 1)], 1)
    for fu in canon.face_uvs:
        cv2.fillConvexPoly(footprint, np.int32(np.round(uv_px[fu])), 1)
    contours, _ = cv2.findContours(footprint, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    solid = np.zeros_like(footprint)
    cv2.drawContours(solid, contours, -1, 1, thickness=cv2.FILLED)
    dist = cv2.distanceTransform(solid, cv2.DIST_L2, 5)
    alpha = np.clip(dist / FEATHER_PX, 0, 1)
    alpha = alpha * alpha * (3 - 2 * alpha)                   # smoothstep
    rgba = np.dstack([rgb8, (alpha * 255).astype(np.uint8)])
    return rgba, covered


def skin_tone(observations: list[FaceObservation]) -> str | None:
    """Median colour of both cheeks in the front photo."""
    obs = next((o for o in observations if o.view == "front"), observations[0])
    h, w = obs.image.shape[:2]
    face_w = np.linalg.norm(obs.points[C.LEFT_FACE_EDGE, :2] - obs.points[C.RIGHT_FACE_EDGE, :2])
    r = max(2, int(0.06 * face_w))
    px = []
    for idx in (C.LEFT_CHEEK, C.RIGHT_CHEEK):
        cx, cy = obs.points[idx, :2].astype(int)
        px.append(obs.image[max(cy - r, 0):min(cy + r, h), max(cx - r, 0):min(cx + r, w)].reshape(-1, 3))
    px = np.concatenate(px)
    if len(px) < 10:
        return None
    rr, gg, bb = np.median(px, 0).astype(int)
    return f"#{rr:02X}{gg:02X}{bb:02X}"


# --------------------------------------------------------------------- fuse


def reconstruct(observations: list[FaceObservation]) -> FaceReconstruction:
    if not observations:
        raise ValueError("at least one face photo is required")
    observations = sorted(observations, key=lambda o: o.view != "front")
    canon = C.load()
    faces = _orient_faces(canon.vertices, canon.faces)
    warnings: list[str] = []

    shapes, weights, source = [], [], "canonical"
    for obs in observations:
        aligned, r, _, src = align_view(obs.points, warnings, obs.view)
        if obs.view == "front" or len(observations) == 1:
            source = src
        # How squarely this camera saw each vertex: canonical normals rotated
        # back into the camera frame, z component.
        n_cam = vertex_normals(aligned, faces) @ r          # canonical -> camera (R is orthonormal)
        weights.append(np.clip(n_cam[:, 2], 0.05, 1.0))
        shapes.append(aligned)

    # Side views were scaled to an average face (no reliable iris); rescale
    # them to the front view's metric size before averaging.
    ref = shapes[0]
    for i in range(1, len(shapes)):
        s, r, t = _kabsch(shapes[i], ref, with_scale=True)
        shapes[i] = s * shapes[i] @ r.T + t
    w = np.stack(weights)[..., None]
    fused_cm = (np.stack(shapes) * w).sum(0) / w.sum(0)

    texture, covered = bake_texture(observations, faces)
    if covered.mean() < 0.2:
        warnings.append("little of the face texture could be recovered; retake the front photo closer")

    return FaceReconstruction(
        vertices=fused_cm / 100.0,
        texture=texture,
        skin_tone_hex=skin_tone(observations),
        scale_source=source,
        views=[o.view for o in observations],
        warnings=warnings,
    )
