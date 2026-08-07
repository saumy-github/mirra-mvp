"""
Direct photo-to-atlas face projection.

Replaces reconstruct.py (3DDFA_V2 BFM mesh reconstruction) and bake.py (UV
texture bake) entirely. The best face texture is the user's actual photo —
this fits a single perspective homography from matched MediaPipe landmarks
and warps the real photo pixels straight into the CLO avatar UV atlas.

No 3D reconstruction, no BFM/FLAME model, no UV bake — only MediaPipe
landmarks + OpenCV homography.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .detect import FACE_OVAL_INDICES

# Anatomically distributed landmarks used to fit the photo -> atlas
# homography. Deliberately more than the minimum needed so RANSAC (and the
# atlas-face-region check below) can drop unreliable correspondences — e.g.
# landmark 10 (forehead top) lands outside the calibrated face region in the
# base-1 UV template and is filtered out automatically.
CONTROL_LANDMARKS: list[int] = [
    234, 454, 152, 10,             # jaw left, jaw right, chin, forehead top
    116, 345,                      # left cheek, right cheek
    33, 133, 263, 362,             # left eye outer/inner, right eye outer/inner
    70, 300,                       # left brow outer, right brow outer
    4, 94, 129, 358,               # nose tip, nose base, left ala, right ala
    61, 291, 13, 14,               # mouth left, mouth right, upper/lower lip
    168, 6, 197,                   # nose bridge top/mid/lower
]

# Cheek landmarks — pure skin, no beard/eyes/shadow.
_CHEEK_LANDMARKS: list[int] = [116, 117, 118, 119, 120, 345, 346, 347, 348, 349]

# Side-photo cheek regions used for multi-view blending.
_LEFT_CHEEK_REGION: list[int] = [234, 116, 117, 118, 93, 132, 127, 162]
_RIGHT_CHEEK_REGION: list[int] = [454, 345, 346, 347, 361, 288, 397, 389]

# Calibrated CLO atlas face region for base-1 (same box bake.py used).
# Control points whose atlas position falls outside this box are dropped.
_ATLAS_FACE_X1, _ATLAS_FACE_Y1 = 450, 200
_ATLAS_FACE_X2, _ATLAS_FACE_Y2 = 1550, 1150

_MIN_CONTROL_POINTS = 8
_MIN_INLIERS = 6
_SIDE_BLEND_WEIGHT = 0.4


def extract_skin_tone(
    photo_bgr: np.ndarray,
    landmarks_px: list[tuple[int, int]],
) -> dict | None:
    """
    Measure the user's skin tone from cheek landmarks.

    Samples 20x20 patches around each cheek landmark — avoids beard, hair,
    shadows. Fully automatic: no hardcoded skin-tone values, works for any
    skin tone.
    """
    h, w = photo_bgr.shape[:2]
    pixels: list[np.ndarray] = []
    for idx in _CHEEK_LANDMARKS:
        if idx >= len(landmarks_px):
            continue
        cx, cy = landmarks_px[idx]
        patch = photo_bgr[max(0, cy - 10):cy + 10, max(0, cx - 10):cx + 10]
        if patch.size > 0:
            pixels.append(patch.reshape(-1, 3))
    if not pixels:
        return None

    all_px = np.vstack(pixels).astype(np.uint8)
    lab = cv2.cvtColor(
        all_px.reshape(1, -1, 3), cv2.COLOR_BGR2LAB
    ).reshape(-1, 3).astype(np.float32)
    return {
        "L": float(np.median(lab[:, 0])),
        "A": float(np.median(lab[:, 1])),
        "B": float(np.median(lab[:, 2])),
        "bgr": tuple(map(int, np.median(all_px, axis=0))),
    }


def _oval_points(landmarks_px: list[tuple[int, int]]) -> np.ndarray:
    return np.array([landmarks_px[i] for i in FACE_OVAL_INDICES], dtype=np.float32)


def _build_control_points(
    landmarks_px: list[tuple[int, int]],
    uv_all_px: list[list[int]],
    atlas_w: int,
    atlas_h: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Match photo-space landmarks to atlas-space landmarks, dropping bad correspondences."""
    src_pts, dst_pts = [], []
    for idx in CONTROL_LANDMARKS:
        if idx >= len(landmarks_px) or idx >= len(uv_all_px):
            continue
        dst_x, dst_y = uv_all_px[idx]
        if not (0 <= dst_x < atlas_w and 0 <= dst_y < atlas_h):
            print(f"  [project] SKIP landmark {idx} — dst [{dst_x},{dst_y}] outside atlas bounds")
            continue
        if not (_ATLAS_FACE_X1 < dst_x < _ATLAS_FACE_X2 and _ATLAS_FACE_Y1 < dst_y < _ATLAS_FACE_Y2):
            print(f"  [project] SKIP landmark {idx} — dst [{dst_x},{dst_y}] outside face region")
            continue
        src_pts.append(landmarks_px[idx])
        dst_pts.append([dst_x, dst_y])
    return np.array(src_pts, dtype=np.float32), np.array(dst_pts, dtype=np.float32)


def _compute_homography(
    landmarks_px: list[tuple[int, int]],
    uv_all_px: list[list[int]],
    atlas_w: int,
    atlas_h: int,
) -> tuple[np.ndarray | None, int, int]:
    """Fit a photo -> atlas homography from matched landmarks. Returns (H, n_control, n_inliers)."""
    src_pts, dst_pts = _build_control_points(landmarks_px, uv_all_px, atlas_w, atlas_h)
    if len(src_pts) < _MIN_CONTROL_POINTS:
        return None, len(src_pts), 0

    H, mask = cv2.findHomography(
        src_pts, dst_pts,
        method=cv2.RANSAC,
        ransacReprojThreshold=15.0,
        confidence=0.999,
    )
    if H is None:
        return None, len(src_pts), 0
    return H, len(src_pts), int(mask.sum())


def _region_mask_in_atlas(
    landmarks_px: list[tuple[int, int]],
    region_indices: list[int],
    H: np.ndarray,
    atlas_w: int,
    atlas_h: int,
) -> np.ndarray:
    """Warp a photo-space landmark region into a feathered atlas-space alpha mask."""
    pts = np.array(
        [landmarks_px[i] for i in region_indices if i < len(landmarks_px)],
        dtype=np.float32,
    )
    if len(pts) < 3:
        return np.zeros((atlas_h, atlas_w), dtype=np.float32)
    warped = cv2.perspectiveTransform(pts.reshape(-1, 1, 2), H).reshape(-1, 2)
    mask = np.zeros((atlas_h, atlas_w), dtype=np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(warped.astype(np.int32)), 255)
    return cv2.GaussianBlur(mask.astype(np.float32), (41, 41), 0) / 255.0


def _mean_L(img_bgr: np.ndarray, mask: np.ndarray) -> float:
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    return float(np.mean(lab[:, :, 0][mask > 0]))


def _match_lab_tone(source: np.ndarray, target: np.ndarray, region: np.ndarray) -> np.ndarray:
    """
    Shift `source`'s LAB stats to match `target`'s, measured over `region`.

    Side photos are shot under different white balance/exposure than the
    front photo, so a raw blend leaves a visible seam at the blend boundary.
    Matching tone in the blend region first (L: scale, A/B: shift — same
    approach as extract_skin_tone/apply_skin_tone) removes that seam.
    """
    if not region.any():
        return source
    src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float32)
    tgt_lab = cv2.cvtColor(target, cv2.COLOR_BGR2LAB).astype(np.float32)
    for c in range(3):
        src_med = np.median(src_lab[:, :, c][region])
        tgt_med = np.median(tgt_lab[:, :, c][region])
        if c == 0:
            scale = tgt_med / (src_med + 1e-6)
            src_lab[:, :, c] = np.clip(src_lab[:, :, c] * scale, 0, 255)
        else:
            src_lab[:, :, c] = np.clip(src_lab[:, :, c] + (tgt_med - src_med), 0, 255)
    return cv2.cvtColor(np.clip(src_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def _blend_side_photo(
    warped_photo: np.ndarray,
    side_photo: np.ndarray,
    side_landmarks: dict,
    region_indices: list[int],
    uv_all_px: list[list[int]],
    atlas_w: int,
    atlas_h: int,
    label: str,
) -> np.ndarray:
    """Blend a 45deg side photo onto its cheek region in atlas space, if reliable."""
    if not side_landmarks.get("detected"):
        print(f"  [project] {label} photo skipped — no face detected")
        return warped_photo

    H_side, n_side, inliers_side = _compute_homography(
        side_landmarks["landmarks_px"], uv_all_px, atlas_w, atlas_h
    )
    if H_side is None or inliers_side < _MIN_INLIERS:
        print(f"  [project] {label} photo skipped — insufficient homography "
              f"(inliers {inliers_side}/{n_side})")
        return warped_photo

    warped_side = cv2.warpPerspective(
        side_photo, H_side, (atlas_w, atlas_h), flags=cv2.INTER_LANCZOS4
    )
    region_mask = _region_mask_in_atlas(
        side_landmarks["landmarks_px"], region_indices, H_side, atlas_w, atlas_h
    )
    alpha = region_mask * _SIDE_BLEND_WEIGHT

    # Side photos carry different white balance/exposure than the front photo —
    # match tone in the blend region first, or the seam shows.
    warped_side = _match_lab_tone(warped_side, warped_photo, region_mask > 0.3)

    print(f"  [project] {label} photo blended (inliers {inliers_side}/{n_side})")
    return (
        warped_side.astype(np.float32) * alpha[:, :, np.newaxis]
        + warped_photo.astype(np.float32) * (1.0 - alpha[:, :, np.newaxis])
    ).astype(np.uint8)


def project_face(
    front_photo: np.ndarray,
    front_landmarks: dict,
    clo_atlas: np.ndarray,
    clo_uv_map: dict,
    left_photo: np.ndarray | None = None,
    left_landmarks: dict | None = None,
    right_photo: np.ndarray | None = None,
    right_landmarks: dict | None = None,
    output_dir: str = "/tmp/mirra_project",
) -> dict:
    """
    Project the user's actual photo pixels directly into the CLO avatar UV atlas.

    Args:
        front_photo     : BGR photo array — required
        front_landmarks : detect.detect() output for front_photo
        clo_atlas       : (2048, 2048, 3) BGR — CLO avatar face texture
        clo_uv_map      : parsed base-N-face-uv.json (uses "all_478_landmark_pixels")
        left_photo, right_photo         : optional 45deg BGR photo arrays
        left_landmarks, right_landmarks : detect.detect() output for the side photos
        output_dir      : directory for projected_atlas.jpg / debug_projection.jpg

    Returns dict:
        success, atlas, atlas_path, face_mask, homography,
        control_points, inliers, reprojection_error_mean, l_drift, skin_tone
    On failure: success=False, error, stage.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    atlas_h, atlas_w = clo_atlas.shape[:2]
    uv_all_px = clo_uv_map["all_478_landmark_pixels"]

    if not front_landmarks.get("detected"):
        return {"success": False, "error": "No face detected in front photo", "stage": "detection"}
    landmarks_px = front_landmarks["landmarks_px"]
    img_h, img_w = front_photo.shape[:2]

    # ── Stage 1: face crop (diagnostic — the warp itself uses the full photo) ─
    oval_photo = _oval_points(landmarks_px)
    x1 = max(0, int(np.min(oval_photo[:, 0])))
    y1 = max(0, int(np.min(oval_photo[:, 1])))
    x2 = min(img_w, int(np.max(oval_photo[:, 0])))
    y2 = min(img_h, int(np.max(oval_photo[:, 1])))
    print(f"  [project] Face crop: {x2-x1}x{y2-y1}px from {img_w}x{img_h} photo")

    # ── Stage 2: face mask in photo space — no background/hair/ears ─────────
    face_mask_photo = np.zeros((img_h, img_w), dtype=np.uint8)
    cv2.fillConvexPoly(face_mask_photo, cv2.convexHull(oval_photo.astype(np.int32)), 255)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    face_mask_photo = cv2.erode(face_mask_photo, kernel)

    # ── Stage 3+4: control points + homography ───────────────────────────────
    try:
        H, n_control, inliers = _compute_homography(landmarks_px, uv_all_px, atlas_w, atlas_h)
        print(f"  [project] Control points: {n_control} valid / {len(CONTROL_LANDMARKS)} total")
        if H is None:
            return {
                "success": False,
                "error": f"Only {n_control} valid control points (need >= {_MIN_CONTROL_POINTS})",
                "stage": "control_points",
            }
        print(f"  [project] Homography inliers: {inliers} / {n_control}")
        if inliers < _MIN_INLIERS:
            return {
                "success": False,
                "error": f"Only {inliers} homography inliers (need >= {_MIN_INLIERS})",
                "stage": "homography",
            }

        src_pts, dst_pts = _build_control_points(landmarks_px, uv_all_px, atlas_w, atlas_h)
        src_h = np.column_stack([src_pts, np.ones(len(src_pts))])
        proj = (H @ src_h.T).T
        proj = proj[:, :2] / proj[:, 2:3]
        errors = np.linalg.norm(proj - dst_pts, axis=1)
        print(f"  [project] Reprojection error — mean:{errors.mean():.1f}px max:{errors.max():.1f}px")
    except Exception as e:
        return {"success": False, "error": str(e), "stage": "homography"}

    # ── Stage 5: warp photo + mask into atlas space ───────────────────────────
    try:
        warped_photo = cv2.warpPerspective(
            front_photo, H, (atlas_w, atlas_h),
            flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0),
        )
        warped_mask = cv2.warpPerspective(
            face_mask_photo, H, (atlas_w, atlas_h),
            flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0,
        )
        warped_mask_feathered = cv2.GaussianBlur(warped_mask.astype(np.float32), (41, 41), 0) / 255.0
    except Exception as e:
        return {"success": False, "error": str(e), "stage": "warp"}

    # ── Stage 6: measure skin tone from the source photo ──────────────────────
    skin_tone = extract_skin_tone(front_photo, landmarks_px)
    if skin_tone is None:
        return {"success": False, "error": "Could not measure skin tone — cheek landmarks missing", "stage": "skin_tone"}
    print(f"  [project] Skin tone — L:{skin_tone['L']:.1f} A:{skin_tone['A']:.1f} B:{skin_tone['B']:.1f}")

    # ── Stage 7: multi-view blend — side photos cover cheek depth/jaw ─────────
    if left_photo is not None and left_landmarks is not None:
        warped_photo = _blend_side_photo(
            warped_photo, left_photo, left_landmarks, _LEFT_CHEEK_REGION,
            uv_all_px, atlas_w, atlas_h, "Left",
        )
    if right_photo is not None and right_landmarks is not None:
        warped_photo = _blend_side_photo(
            warped_photo, right_photo, right_landmarks, _RIGHT_CHEEK_REGION,
            uv_all_px, atlas_w, atlas_h, "Right",
        )

    # ── Stage 8: match warped texture to the measured skin tone ───────────────
    face_px = warped_mask > 128
    warped_lab = cv2.cvtColor(warped_photo, cv2.COLOR_BGR2LAB).astype(np.float32)
    current_L = np.median(warped_lab[:, :, 0][face_px])
    current_A = np.median(warped_lab[:, :, 1][face_px])
    current_B = np.median(warped_lab[:, :, 2][face_px])
    L_scale = skin_tone["L"] / (current_L + 1e-6)
    warped_lab[:, :, 0][face_px] = np.clip(warped_lab[:, :, 0][face_px] * L_scale, 0, 255)
    warped_lab[:, :, 1][face_px] = np.clip(warped_lab[:, :, 1][face_px] + (skin_tone["A"] - current_A), 0, 255)
    warped_lab[:, :, 2][face_px] = np.clip(warped_lab[:, :, 2][face_px] + (skin_tone["B"] - current_B), 0, 255)
    warped_photo = cv2.cvtColor(np.clip(warped_lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)

    # ── Stage 9: blend into the CLO atlas ──────────────────────────────────────
    atlas_out = clo_atlas.copy()
    base_color = np.array(skin_tone["bgr"], dtype=np.uint8)
    atlas_out[warped_mask > 128] = base_color
    alpha = warped_mask_feathered[:, :, np.newaxis]
    atlas_out = (
        warped_photo.astype(np.float32) * alpha + atlas_out.astype(np.float32) * (1.0 - alpha)
    ).astype(np.uint8)

    M = cv2.moments(warped_mask)
    if M["m00"] > 0:
        cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
        try:
            atlas_out = cv2.seamlessClone(
                warped_photo, atlas_out, warped_mask, (cx, cy), cv2.NORMAL_CLONE
            )
            print("  [project] Poisson blend applied")
        except cv2.error as e:
            print(f"  [project] Poisson skipped: {e} — using alpha blend")

    # ── Stage 10: L-drift check, correction, save ──────────────────────────────
    drift = _mean_L(atlas_out, warped_mask) - skin_tone["L"]
    print(f"  [project] L drift: {drift:+.1f} (pass if < 8.0)")
    if abs(drift) > 8.0:
        lab = cv2.cvtColor(atlas_out, cv2.COLOR_BGR2LAB).astype(np.float32)
        l, a, b = cv2.split(lab)
        scale = skin_tone["L"] / (_mean_L(atlas_out, warped_mask) + 1e-6)
        l[warped_mask > 0] = np.clip(l[warped_mask > 0] * scale, 0, 255)
        atlas_out = cv2.cvtColor(
            cv2.merge([l.astype(np.uint8), a.astype(np.uint8), b.astype(np.uint8)]),
            cv2.COLOR_LAB2BGR,
        )
        drift = _mean_L(atlas_out, warped_mask) - skin_tone["L"]
        print(f"  [project] Drift corrected → {drift:+.1f}")

    atlas_path = out_dir / "projected_atlas.jpg"
    cv2.imwrite(str(atlas_path), atlas_out)

    debug = atlas_out.copy()
    for pt in dst_pts.astype(int):
        cv2.circle(debug, tuple(pt), 5, (0, 255, 0), -1)
    cv2.imwrite(str(out_dir / "debug_projection.jpg"), debug)
    print(f"  [project] Saved: {atlas_path}")

    return {
        "success": True,
        "atlas": atlas_out,
        "atlas_path": str(atlas_path),
        "face_mask": warped_mask,
        "homography": H,
        "control_points": n_control,
        "inliers": inliers,
        "reprojection_error_mean": float(errors.mean()),
        "l_drift": float(drift),
        "skin_tone": skin_tone,
    }


# ── Smoke test ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    from .avt_face import extract_base_texture
    from .detect import detect

    _face_dir = Path(__file__).parent
    _input_dir = Path(__file__).parents[1] / "input" / "face" / "u_001"
    _avt = Path(__file__).parents[1] / "input" / "base-1.avt"

    front_path = _input_dir / "front.jpg"
    left_path = _input_dir / "left.jpg"
    right_path = _input_dir / "right.jpg"

    front = cv2.imread(str(front_path))
    left = cv2.imread(str(left_path)) if left_path.exists() else None
    right = cv2.imread(str(right_path)) if right_path.exists() else None

    front_lm = detect(front_path)
    left_lm = detect(left_path) if left_path.exists() else None
    right_lm = detect(right_path) if right_path.exists() else None

    atlas = extract_base_texture(_avt)
    uv_map = json.loads((_face_dir / "templates" / "base-1-face-uv.json").read_text(encoding="utf-8"))

    result = project_face(
        front_photo=front,
        front_landmarks=front_lm,
        clo_atlas=atlas,
        clo_uv_map=uv_map,
        left_photo=left,
        left_landmarks=left_lm,
        right_photo=right,
        right_landmarks=right_lm,
        output_dir="/tmp/mirra_project_test",
    )

    print(f"Success:              {result['success']}")
    if not result["success"]:
        print(f"Error:                {result['error']} @ {result['stage']}")
    else:
        print(f"Control points:       {result['control_points']}")
        print(f"Inliers:              {result['inliers']}")
        print(f"Reprojection error:   {result['reprojection_error_mean']:.1f}px")
        print(f"L drift:              {result['l_drift']:+.1f}")
        print(f"Skin tone L:          {result['skin_tone']['L']:.1f}")
        print()
        print("Open these to inspect:")
        print("  /tmp/mirra_project_test/projected_atlas.jpg")
        print("  /tmp/mirra_project_test/debug_projection.jpg")
