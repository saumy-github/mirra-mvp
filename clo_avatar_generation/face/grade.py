"""
Final color grade pass applied to the face region of the UV texture.

Applied after all compositing (warp, blend, beard, hair) is done:
  - Saturation +15% in HSV space (face region only)
  - Hue +5° toward warm orange-red
  - Brightness -8% to match medium-dark complexion
  - Bilateral filter (d=9, sigmaColor=75) to smooth texture seams
    without losing skin pore/beard detail
"""

from __future__ import annotations

import cv2
import numpy as np


def apply_color_grade(
    texture: np.ndarray,
    face_mask: np.ndarray,
) -> np.ndarray:
    """
    Apply final color grade to face region only.

    Args:
        texture   : (H, W, 3) BGR — fully composited UV texture
        face_mask : (H, W) uint8   — 255 inside face oval

    Returns:
        (H, W, 3) uint8 BGR — graded texture
    """
    face = face_mask > 0
    if not face.any():
        return texture.copy()

    result = texture.copy()

    # ── HSV adjustments (face region only) ───────────────────────────────────
    hsv = cv2.cvtColor(result, cv2.COLOR_BGR2HSV).astype(np.float32)

    # Saturation +15%
    hsv[:, :, 1][face] = np.clip(hsv[:, :, 1][face] * 1.15, 0, 255)

    # Hue +5° toward warm orange-red (cv2 hue range is 0–180, so 5° = 2.5 units)
    hsv[:, :, 0][face] = (hsv[:, :, 0][face] + 2.5) % 180

    # Brightness -8%
    hsv[:, :, 2][face] = np.clip(hsv[:, :, 2][face] * 0.92, 0, 255)

    result = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # ── Bilateral filter to smooth seams (face region only) ──────────────────
    filtered = cv2.bilateralFilter(result, d=9, sigmaColor=75, sigmaSpace=75)
    mask_3ch = np.stack([face_mask, face_mask, face_mask], axis=-1)
    result = np.where(mask_3ch > 0, filtered, result).astype(np.uint8)

    return result
