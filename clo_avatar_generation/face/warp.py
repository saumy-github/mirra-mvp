"""Warp a user's face photo into avatar UV texture space using triangulated warping."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from scipy.spatial import Delaunay


_TEMPLATES_DIR = Path(__file__).parent / "templates"

# ── Base warp indices (face oval + coarse interior anchors) ───────────────────
# Eye landmarks were previously excluded due to "third eye" artifacts caused by
# wrong UV positions (MediaPipe detecting on 2D texture image).
# Now that we use true UV coords from OBJ mesh projection they are added back
# via _validated_eye_indices() with bounds checking.
_BASE_WARP_INDICES: list[int] = [
    # Face oval — 35 boundary points
    # 10 excluded: bad UV projection in OBJ (lands at x=1940 instead of x≈1024 midline)
    338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
    # Eyebrows (inserted between forehead oval and nose — Delaunay stability)
    70, 107, 300, 336,
    # Eye corners + lids (added after brow validation)
    33, 133, 159, 145,    # left eye: outer, inner, upper lid, lower lid
    362, 263, 386, 374,   # right eye: outer, inner, upper lid, lower lid
    # Nose tip + bridge
    4, 6, 168,
    # Mouth corners + centre lip (0 excluded — bad UV projection in OBJ, lands at x=1983)
    61, 291, 17,
    # Chin
    152,
    # Mid-cheeks
    116, 345,
]
# Deduplicate, preserve order
_seen: set[int] = set()
_BASE_WARP_INDICES = [i for i in _BASE_WARP_INDICES if not (i in _seen or _seen.add(i))]  # type: ignore
del _seen

# Eye + brow landmark indices that get bounds-checked before use
_EYE_BROW_INDICES: list[int] = [70, 107, 300, 336, 33, 133, 159, 145, 362, 263, 386, 374]

# Post-warp eye protection: blend back toward pre-warp at these landmarks
_EYE_PROTECT_INDICES: list[int] = [33, 133, 159, 145, 362, 263, 386, 374]
_EYE_PROTECT_RADIUS  = 15
_EYE_PROTECT_BLEND   = 0.40   # 40% blended back toward pre-warp


def _validated_eye_indices(
    uv_all_px: list[list[int]],
    uv_w: int,
    uv_h: int,
) -> tuple[list[int], list[int]]:
    """
    Validate eye/brow landmarks against expected UV bounds.

    Valid ranges (fractions of texture size):
        X : [0.25, 0.75]  — face centre zone
        Y : [0.20, 0.60]  — eye height zone

    Returns:
        accepted : indices that passed validation
        rejected : indices that failed (logged as warnings)
    """
    x_lo, x_hi = 0.25 * uv_w, 0.75 * uv_w
    y_lo, y_hi = 0.20 * uv_h, 0.60 * uv_h

    accepted, rejected = [], []
    for idx in _EYE_BROW_INDICES:
        if idx >= len(uv_all_px):
            rejected.append(idx)
            continue
        px, py = uv_all_px[idx]
        if x_lo <= px <= x_hi and y_lo <= py <= y_hi:
            accepted.append(idx)
        else:
            rejected.append(idx)
    return accepted, rejected


def _apply_eye_protection(
    warped: np.ndarray,
    pre_warp: np.ndarray,
    uv_all_px: list[list[int]],
    valid_eye_indices: list[int],
) -> np.ndarray:
    """
    Blend 40% of pre-warp texture back at each valid eye landmark
    within a 15px feathered radius.

    Preserves natural eye shape if the warp slightly distorts the eye region.
    """
    result = warped.copy()
    h, w   = warped.shape[:2]
    r      = _EYE_PROTECT_RADIUS

    protect = [i for i in valid_eye_indices if i in _EYE_PROTECT_INDICES]
    for idx in protect:
        cx, cy = int(uv_all_px[idx][0]), int(uv_all_px[idx][1])
        y1, y2 = max(0, cy - r), min(h, cy + r + 1)
        x1, x2 = max(0, cx - r), min(w, cx + r + 1)
        ph, pw  = y2 - y1, x2 - x1

        yy, xx  = np.ogrid[:ph, :pw]
        dist    = np.sqrt((yy - (cy - y1))**2 + (xx - (cx - x1))**2)
        alpha   = (np.clip(1.0 - dist / r, 0, 1) * _EYE_PROTECT_BLEND).astype(np.float32)
        alpha3  = alpha[:, :, np.newaxis]

        w_patch = warped[y1:y2, x1:x2].astype(np.float32)
        p_patch = pre_warp[y1:y2, x1:x2].astype(np.float32)
        result[y1:y2, x1:x2] = np.clip(
            w_patch * (1 - alpha3) + p_patch * alpha3, 0, 255
        ).astype(np.uint8)

    return result


def save_eye_debug(
    avatar_name: str = "base-1",
    uv_template_path: Path | None = None,
    avt_path: Path | None = None,
    out_path: Path = Path("/tmp/debug_eye_landmarks.png"),
) -> None:
    """
    Save debug_eye_landmarks.png:
      green dot = landmark accepted (within UV bounds)
      red dot   = landmark rejected (outside bounds)
    """
    import io
    import zipfile

    if uv_template_path is None:
        uv_template_path = _TEMPLATES_DIR / f"{avatar_name}-face-uv.json"
    uv       = json.loads(uv_template_path.read_text(encoding="utf-8"))
    uv_w, uv_h = uv["texture_size"]
    uv_all_px  = uv["all_478_landmark_pixels"]

    # Load face texture as background
    if avt_path is None:
        avt_path = Path(__file__).parents[1] / "input" / "base-1.avt"
    raw = avt_path.read_bytes()
    zs  = raw.find(b"PK\x03\x04")
    with zipfile.ZipFile(io.BytesIO(raw[zs:]), "r") as z:
        canvas = cv2.imdecode(
            np.frombuffer(z.read("MV2_Jinho_01_face.jpg"), np.uint8),
            cv2.IMREAD_COLOR,
        )

    accepted, rejected = _validated_eye_indices(uv_all_px, uv_w, uv_h)

    names = {
        70: "brow_l_out", 107: "brow_l_in", 300: "brow_r_out", 336: "brow_r_in",
        33: "eye_l_out",  133: "eye_l_in",  159: "eye_l_top", 145: "eye_l_bot",
        362: "eye_r_out", 263: "eye_r_in",  386: "eye_r_top", 374: "eye_r_bot",
    }

    for idx in accepted:
        px, py = uv_all_px[idx]
        cv2.circle(canvas, (px, py), 14, (0, 220, 0), -1)
        cv2.putText(canvas, names.get(idx, str(idx)),
                    (px + 8, py - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 0), 1)

    for idx in rejected:
        px, py = uv_all_px[idx]
        cv2.circle(canvas, (px, py), 14, (0, 0, 220), -1)
        cv2.putText(canvas, names.get(idx, str(idx)),
                    (px + 8, py - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 220), 1)

    # Draw valid UV bounds box
    x_lo = int(0.25 * uv_w); x_hi = int(0.75 * uv_w)
    y_lo = int(0.20 * uv_h); y_hi = int(0.60 * uv_h)
    cv2.rectangle(canvas, (x_lo, y_lo), (x_hi, y_hi), (255, 200, 0), 3)
    cv2.putText(canvas, "valid bounds", (x_lo + 5, y_lo - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

    cv2.imwrite(str(out_path), canvas)
    print(f"Eye debug saved → {out_path}")
    print(f"  Accepted ({len(accepted)}): {accepted}")
    print(f"  Rejected ({len(rejected)}): {rejected}")
    if rejected:
        for idx in rejected:
            px, py = uv_all_px[idx]
            norm_x, norm_y = px / uv_w, py / uv_h
            print(f"    idx {idx}: UV=({px},{py}) norm=({norm_x:.2f},{norm_y:.2f}) — outside bounds")


def _warp_triangle(
    src_img: np.ndarray,
    src_tri: np.ndarray,
    dst_img: np.ndarray,
    dst_tri: np.ndarray,
) -> None:
    """Affine-warp a single triangle from src_img into dst_img (in-place)."""
    s_rect = cv2.boundingRect(src_tri.reshape(-1, 1, 2).astype(np.float32))
    d_rect = cv2.boundingRect(dst_tri.reshape(-1, 1, 2).astype(np.float32))
    sx, sy, sw, sh = s_rect
    dx, dy, dw, dh = d_rect

    if sw <= 0 or sh <= 0 or dw <= 0 or dh <= 0:
        return

    src_local = src_tri - np.array([sx, sy], dtype=np.float32)
    dst_local = dst_tri - np.array([dx, dy], dtype=np.float32)

    M = cv2.getAffineTransform(
        src_local.astype(np.float32),
        dst_local.astype(np.float32),
    )

    sh_img, sw_img = src_img.shape[:2]
    sx_c = max(0, sx);       sy_c = max(0, sy)
    ex_c = min(sw_img, sx + sw); ey_c = min(sh_img, sy + sh)
    if sx_c >= ex_c or sy_c >= ey_c:
        return

    src_crop = src_img[sy_c:ey_c, sx_c:ex_c]
    M[0, 2] += sx - sx_c
    M[1, 2] += sy - sy_c

    warped = cv2.warpAffine(
        src_crop, M, (dw, dh),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    tri_mask = np.zeros((dh, dw), dtype=np.uint8)
    cv2.fillConvexPoly(tri_mask, dst_local.astype(np.int32), 255)

    dh_img, dw_img = dst_img.shape[:2]
    dx_c = max(0, dx);        dy_c = max(0, dy)
    ex_d = min(dw_img, dx + dw); ey_d = min(dh_img, dy + dh)
    if dx_c >= ex_d or dy_c >= ey_d:
        return

    mx, my = dx_c - dx, dy_c - dy
    warped_clip = warped[my: my + (ey_d - dy_c), mx: mx + (ex_d - dx_c)]
    mask_clip   = tri_mask[my: my + (ey_d - dy_c), mx: mx + (ex_d - dx_c)]

    region = dst_img[dy_c:ey_d, dx_c:ex_d]
    region[mask_clip > 0] = warped_clip[mask_clip > 0]


def warp(
    image_path: Path,
    landmarks: dict,
    avatar_name: str = "base-1",
    uv_template_path: Path | None = None,
    flip_v: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Warp user's face photo into avatar UV texture space.

    Eye landmarks are now re-added with UV bounds validation.
    Each landmark is checked against valid UV bounds before being included
    in the Delaunay triangulation — prevents "third eye" artifacts if any
    landmark is outside the expected face region.
    Post-warp eye protection blends 40% back toward pre-warp at eye positions.

    Args:
        flip_v: Set True if the warped face appears upside-down (V-axis
                inverted in OBJ UV space vs image convention).

    Returns:
        face_in_uv : (H, W, 3) uint8 BGR — full atlas canvas with face placed
        face_mask  : (H, W)    uint8
    """
    if not landmarks["detected"]:
        raise ValueError("No face detected — cannot warp")

    if uv_template_path is None:
        uv_template_path = _TEMPLATES_DIR / f"{avatar_name}-face-uv.json"
    uv = json.loads(uv_template_path.read_text(encoding="utf-8"))

    uv_w, uv_h   = uv["texture_size"]
    uv_all_px    = uv["all_478_landmark_pixels"]
    uv_oval_px   = uv["face_oval_pixels"]

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")

    # ── Step 1: Compute face bbox from all landmark UV coords ─────────────────
    u_min = min(p[0] for p in uv_all_px)
    u_max = max(p[0] for p in uv_all_px)
    v_min = min(p[1] for p in uv_all_px)
    v_max = max(p[1] for p in uv_all_px)

    # Validate eye/brow landmarks against UV bounds
    valid_eye, skipped_eye = _validated_eye_indices(uv_all_px, uv_w, uv_h)
    if skipped_eye:
        print(f"[warp] Eye landmarks skipped (outside UV bounds): {skipped_eye}")

    # Build final index list: base indices + validated eye/brow indices
    # Eye/brow inserted between forehead oval and nose for Delaunay stability
    base_no_eye = [i for i in _BASE_WARP_INDICES if i not in _EYE_BROW_INDICES]
    oval_part  = base_no_eye[:35]   # 35 oval points (landmark 10 excluded — bad UV)
    rest_part  = base_no_eye[35:]
    final_indices = oval_part + valid_eye + rest_part

    # Deduplicate
    seen: set[int] = set()
    final_indices = [i for i in final_indices if not (i in seen or seen.add(i))]

    src_pts = np.array([landmarks["landmarks_px"][i] for i in final_indices], dtype=np.float32)
    dst_pts = np.array([uv_all_px[i]                for i in final_indices], dtype=np.float32)

    # ── Step 4 (optional): V-axis flip ───────────────────────────────────────
    # Apply when OBJ UV space has V=0 at bottom but image space has Y=0 at top.
    if flip_v:
        dst_pts[:, 1] = uv_h - 1 - dst_pts[:, 1]
        # Derive bounds from all 478 landmarks (consistent with u_min/u_max above)
        v_min = uv_h - 1 - max(p[1] for p in uv_all_px)
        v_max = uv_h - 1 - min(p[1] for p in uv_all_px)

    face_region_w = u_max - u_min
    face_region_h = v_max - v_min

    # ── Step 2: Remap dst_pts to face-region-local pixel coords ──────────────
    # Face only occupies a sub-region of the atlas; working in local space
    # avoids writing to a mostly-empty 2048×2048 canvas and makes the
    # coordinate math explicit.
    dst_pts_local = dst_pts - np.array([u_min, v_min], dtype=np.float32)

    tri = Delaunay(dst_pts_local)

    # Keep a copy of the base texture for eye protection
    import io, zipfile
    avt_path = uv_template_path.parents[2] / "input" / "base-1.avt"
    pre_warp  = np.zeros((uv_h, uv_w, 3), dtype=np.uint8)
    if avt_path.exists():
        raw = avt_path.read_bytes()
        zs  = raw.find(b"PK\x03\x04")
        with zipfile.ZipFile(io.BytesIO(raw[zs:]), "r") as z:
            pre_warp = cv2.imdecode(
                np.frombuffer(z.read("MV2_Jinho_01_face.jpg"), np.uint8),
                cv2.IMREAD_COLOR,
            )
        if pre_warp.shape[:2] != (uv_h, uv_w):
            pre_warp = cv2.resize(pre_warp, (uv_w, uv_h))

    # Warp into face-region canvas (not full atlas)
    face_canvas = np.zeros((face_region_h, face_region_w, 3), dtype=np.uint8)
    for simplex in tri.simplices:
        _warp_triangle(img, src_pts[simplex], face_canvas, dst_pts_local[simplex])

    # Eye protection — use face-local landmark coords against the cropped pre_warp
    uv_all_local = [
        [p[0] - u_min, (uv_h - 1 - p[1] if flip_v else p[1]) - v_min]
        for p in uv_all_px
    ]
    pre_warp_crop = pre_warp[v_min:v_max, u_min:u_max]
    if valid_eye:
        face_canvas = _apply_eye_protection(face_canvas, pre_warp_crop, uv_all_local, valid_eye)

    # ── Step 3: Write warped face back to atlas at correct position ───────────
    face_in_uv = np.zeros((uv_h, uv_w, 3), dtype=np.uint8)
    face_in_uv[v_min:v_max, u_min:u_max] = face_canvas

    # Face oval mask — soft feathered edges (90px Gaussian blur).
    # A hard eroded mask creates visible rectangular patches at the boundary.
    # The Gaussian feather gives a gradual 0→255 transition over ~90px.
    oval_np   = np.array(uv_oval_px, dtype=np.int32)
    face_mask_hard = np.zeros((uv_h, uv_w), dtype=np.uint8)
    cv2.fillPoly(face_mask_hard, [oval_np], 255)
    # Erode slightly to pull boundary inward before feathering
    k_erode   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    face_mask_hard = cv2.erode(face_mask_hard, k_erode, iterations=1)
    # Gaussian blur creates soft falloff at boundary (~90px half-width)
    face_mask = cv2.GaussianBlur(face_mask_hard, (91, 91), 30)

    return face_in_uv, face_mask


def warp_multi(
    front_photo: Path,
    front_landmarks: dict,
    left_photo: Path | None,        # kept for API compatibility — used only by morph.py
    left_landmarks: dict | None,    # kept for API compatibility — used only by morph.py
    right_photo: Path | None,       # kept for API compatibility — used only by morph.py
    right_landmarks: dict | None,   # kept for API compatibility — used only by morph.py
    avatar_name: str = "base-1",
    uv_template_path: Path | None = None,
    flip_v: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Texture warp using the front photo only.

    Side photos (left/right 45°) are accepted for API compatibility but are
    NOT used for texture compositing. Sigmoid blending of side photos created
    visible hard-edged patches at the cheek seam boundary. Side photo data
    is consumed exclusively by morph.py for Z-depth measurements.

    Returns:
        face_in_uv : (H, W, 3) uint8 BGR
        face_mask  : (H, W)    uint8   (soft Gaussian-feathered edges)
    """
    return warp(front_photo, front_landmarks, avatar_name, uv_template_path, flip_v=flip_v)
