"""
Beard composite pass.

MediaPipe has no beard landmarks. This module:
  1. Uses jaw landmarks 234, 454, 152, 17 to define the beard bounding region
  2. Generates (or loads) a beard alpha PNG in near-black #1a0f08 with brown undertone
  3. Alpha-composites it onto the blended UV texture

Side-profile note: MediaPipe z-depth is estimated (2.5D), not measured.
For a kiosk build, add a second camera at 45° and average z across both views.
For mobile MVP, note this limitation in the pitch.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


# Beard bounding landmarks
_JAW_LEFT  = 234
_JAW_RIGHT = 454
_CHIN      = 152
_BELOW_LIP = 17

# Beard color: #1a0f08 = R=26, G=15, B=8 → BGR=(8,15,26), warm near-black brown
_BEARD_BGR = (8, 15, 26)

_SPRITES_DIR = Path(__file__).parent / "sprites"


def _generate_beard_sprite(width: int, height: int) -> np.ndarray:
    """
    Procedurally generate a beard alpha PNG (BGRA).

    Produces an elliptical beard shape with near-black #1a0f08 color,
    soft feathered edges, and subtle noise for a natural stubble texture.
    """
    sprite = np.zeros((height, width, 4), dtype=np.uint8)
    alpha  = np.zeros((height, width), dtype=np.float32)

    cx = width  // 2
    # Beard covers roughly the lower 80% of the bounding box (lips to chin)
    cy_beard    = int(height * 0.35)
    ax_beard    = max(1, width  // 2 - 4)
    ay_beard    = max(1, int(height * 0.65))

    # Main beard ellipse (lower half only)
    cv2.ellipse(alpha, (cx, cy_beard), (ax_beard, ay_beard), 0, 0, 180, 1.0, -1)

    # Mustache strip just above beard
    cy_mst = int(height * 0.08)
    cv2.ellipse(alpha, (cx, cy_mst), (max(1, width // 4), max(1, height // 9)), 0, 0, 180, 0.75, -1)

    # Feather edges
    ksize = max(3, (min(width, height) // 10) | 1)   # must be odd
    alpha = cv2.GaussianBlur(alpha, (ksize, ksize), ksize / 3)

    # Subtle noise for stubble texture
    noise = np.random.default_rng(seed=42).normal(0, 0.08, (height, width)).astype(np.float32)
    alpha = np.clip(alpha + noise * alpha, 0, 1)

    # Fill color + alpha
    sprite[:, :, 0] = _BEARD_BGR[0]
    sprite[:, :, 1] = _BEARD_BGR[1]
    sprite[:, :, 2] = _BEARD_BGR[2]
    sprite[:, :, 3] = (alpha * 210).astype(np.uint8)  # max ~82% opacity

    return sprite


def _load_or_generate_sprite(width: int, height: int) -> np.ndarray:
    """
    Use a pre-made beard sprite PNG if available, otherwise generate one.
    Place a custom sprite at: clo_avatar_generation/face/sprites/beard.png
    """
    candidate = _SPRITES_DIR / "beard.png"
    if candidate.exists():
        img = cv2.imread(str(candidate), cv2.IMREAD_UNCHANGED)
        if img is not None and img.shape[2] == 4:
            return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
    return _generate_beard_sprite(width, height)


def composite_beard(
    blended_uv: np.ndarray,
    photo_path: Path,
    landmarks: dict,
    uv_all_px: list[list[int]],
    uv_oval_px: list[list[int]],
) -> np.ndarray:
    """
    Alpha-composite a beard sprite onto the blended UV face texture.

    The sprite is sized and positioned using the jaw/chin UV landmark positions.

    Args:
        blended_uv  : (H, W, 3) BGR — result from blend.blend()
        photo_path  : front-facing user photo (used for beard presence check)
        landmarks   : output of detect.detect()
        uv_all_px   : all 478 UV landmark pixel positions (from template)
        uv_oval_px  : 36-point UV face oval (unused here, kept for API parity)

    Returns:
        (H, W, 3) BGR — blended_uv with beard composited on top
    """
    if not landmarks["detected"]:
        print("BEARD SKIPPED: no face detected")
        return blended_uv

    lm_px = landmarks["landmarks_px"]

    # Require only that the 4 jaw landmarks exist — no threshold check
    required = [_JAW_LEFT, _JAW_RIGHT, _CHIN, _BELOW_LIP]
    for idx in required:
        if idx >= len(lm_px):
            print(f"BEARD SKIPPED: jaw landmark {idx} missing")
            return blended_uv

    uv_h, uv_w = blended_uv.shape[:2]

    uv_jaw_l = uv_all_px[_JAW_LEFT]
    uv_jaw_r = uv_all_px[_JAW_RIGHT]
    uv_chin  = uv_all_px[_CHIN]
    uv_lip_b = uv_all_px[_BELOW_LIP]

    # Compute raw bbox then expand by 15% on all sides
    raw_x1 = uv_jaw_l[0]
    raw_x2 = uv_jaw_r[0]
    raw_y1 = uv_lip_b[1]
    raw_y2 = uv_chin[1] + (uv_chin[1] - uv_lip_b[1]) // 2

    if raw_x2 <= raw_x1 or raw_y2 <= raw_y1:
        print("BEARD SKIPPED: invalid jaw bbox (landmark positions degenerate)")
        return blended_uv

    pad_x = int((raw_x2 - raw_x1) * 0.15)
    pad_y = int((raw_y2 - raw_y1) * 0.15)
    bx1 = max(0,      raw_x1 - pad_x)
    bx2 = min(uv_w,   raw_x2 + pad_x)
    by1 = max(0,      raw_y1 - pad_y)
    by2 = min(uv_h,   raw_y2 + pad_y)

    bw, bh = bx2 - bx1, by2 - by1
    sprite = _load_or_generate_sprite(bw, bh)  # BGRA

    result = blended_uv.copy()
    alpha  = sprite[:, :, 3].astype(np.float32) / 255.0

    for c in range(3):
        src = result[by1:by2, bx1:bx2, c].astype(np.float32)
        dst = sprite[:, :, c].astype(np.float32)
        result[by1:by2, bx1:bx2, c] = np.clip(
            src * (1 - alpha) + dst * alpha, 0, 255
        ).astype(np.uint8)

    print(f"BEARD RENDERED: bbox=({bx1},{by1})→({bx2},{by2})  size={bw}×{bh}px")
    return result
