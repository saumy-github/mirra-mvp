"""
Poisson-blend a warped user face into the avatar's base face texture.

Pipeline:
  1. Reinhard color transfer (70% source / 30% target) — preserves South Asian warm skin tone
  2. seamlessClone MIXED_CLONE — blends with texture detail preserved
  3. Eye artifact repair — blends 60% back toward source at eye landmark positions
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


# Left/right eye landmark indices used for artifact repair (Problem 2)
_LEFT_EYE_REPAIR  = [33, 133, 160, 144]
_RIGHT_EYE_REPAIR = [362, 263, 387, 373]
_EYE_REPAIR_RADIUS = 12
_EYE_BLEND_BACK    = 0.60   # blend 60% back toward source


def _match_skin_tone(
    source_face: np.ndarray,
    target_face: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    """
    Reinhard color transfer in LAB space with 70/30 source/target weighting.

    Uses 70% source LAB statistics + 30% target statistics so the user's
    warm medium-dark South Asian brown skin is preserved rather than being
    pulled toward the base avatar's lighter complexion.
    """
    if not (mask > 0).any():
        return source_face.copy()

    source_lab = cv2.cvtColor(source_face, cv2.COLOR_BGR2LAB).astype(np.float32)
    target_lab = cv2.cvtColor(target_face, cv2.COLOR_BGR2LAB).astype(np.float32)

    src_mean, src_std = [], []
    tgt_mean, tgt_std = [], []

    for i in range(3):  # L, A, B channels
        src_pixels = source_lab[:, :, i][mask > 0]
        tgt_pixels = target_lab[:, :, i][mask > 0]
        src_mean.append(src_pixels.mean())
        src_std.append(src_pixels.std())
        tgt_mean.append(tgt_pixels.mean())
        tgt_std.append(tgt_pixels.std())

    # 90% source / 10% target — strongly preserves user skin tone (South Asian warm brown)
    # L_out = (L_src - mean_src) * (std_tgt/std_src)*0.1
    #       + (L_src - mean_src) * 0.9 + mean_src
    corrected = source_lab.copy()
    for i in range(3):
        centred = source_lab[:, :, i] - src_mean[i]
        scaled_tgt = centred * (tgt_std[i] / (src_std[i] + 1e-6))   # full Reinhard
        corrected[:, :, i] = centred * 0.9 + scaled_tgt * 0.1 + src_mean[i]

    corrected = np.clip(corrected, 0, 255).astype(np.uint8)
    return cv2.cvtColor(corrected, cv2.COLOR_LAB2BGR)


def _repair_eye_artifacts(
    blended: np.ndarray,
    source_in_uv: np.ndarray,
    uv_landmarks: list[list[int]],
) -> np.ndarray:
    """
    Repair dark eye-area artifacts left by Poisson blending.

    At each eye landmark, within a 12px feathered radius, blends 60% of the
    original warped source back over the Poisson result. This removes the dark
    blotch that appears when eye-region UV coordinates are slightly off.
    """
    result = blended.copy()
    h, w = blended.shape[:2]

    for idx in _LEFT_EYE_REPAIR + _RIGHT_EYE_REPAIR:
        if idx >= len(uv_landmarks):
            continue
        cx, cy = int(uv_landmarks[idx][0]), int(uv_landmarks[idx][1])

        if cx <= 0 or cy <= 0 or cx >= w or cy >= h:
            continue

        # Build a soft circular weight mask
        r = _EYE_REPAIR_RADIUS
        y1, y2 = max(0, cy - r), min(h, cy + r + 1)
        x1, x2 = max(0, cx - r), min(w, cx + r + 1)

        patch_h, patch_w = y2 - y1, x2 - x1
        yy, xx = np.ogrid[:patch_h, :patch_w]
        dist = np.sqrt((yy - (cy - y1)) ** 2 + (xx - (cx - x1)) ** 2)
        soft_mask = np.clip(1.0 - dist / r, 0, 1).astype(np.float32)
        soft_mask = soft_mask[:, :, np.newaxis] * _EYE_BLEND_BACK

        b_patch  = blended[y1:y2, x1:x2].astype(np.float32)
        s_patch  = source_in_uv[y1:y2, x1:x2].astype(np.float32)
        repaired = b_patch * (1 - soft_mask) + s_patch * soft_mask
        result[y1:y2, x1:x2] = np.clip(repaired, 0, 255).astype(np.uint8)

    return result


def blend(
    face_in_uv: np.ndarray,
    face_mask: np.ndarray,
    base_texture_path: Path,
    uv_landmarks: list[list[int]] | None = None,
) -> np.ndarray:
    """
    Full face blend pipeline:
      1. Reinhard 70/30 color transfer — preserve source skin tone
      2. seamlessClone MIXED_CLONE
      3. Eye artifact repair (if uv_landmarks provided)

    Args:
        face_in_uv       : (H, W, 3) BGR — user face warped to UV space
        face_mask        : (H, W) uint8   — 255 inside face oval
        base_texture_path: path to original MV2_Jinho_01_face.jpg
        uv_landmarks     : 478 UV-space pixel positions for eye repair

    Returns:
        (H, W, 3) uint8 BGR — personalized face texture
    """
    base = cv2.imread(str(base_texture_path))
    if base is None:
        raise FileNotFoundError(f"Cannot read base texture: {base_texture_path}")

    h, w = base.shape[:2]

    if face_in_uv.shape[:2] != (h, w):
        face_in_uv = cv2.resize(face_in_uv, (w, h))
    if face_mask.shape[:2] != (h, w):
        face_mask = cv2.resize(face_mask, (w, h), interpolation=cv2.INTER_NEAREST)

    ys, xs = np.where(face_mask > 0)
    if len(xs) == 0:
        return base.copy()

    # Step 1 — Reinhard 90/10 color transfer (preserves source skin tone)
    corrected = _match_skin_tone(face_in_uv, base, face_mask)

    # Debug: L-channel mean before blend
    src_lab   = cv2.cvtColor(corrected, cv2.COLOR_BGR2LAB)
    src_L_mean = float(src_lab[:, :, 0][face_mask > 0].mean())
    print(f"[blend] L-mean before seamlessClone: {src_L_mean:.1f}")

    # Step 2 — Poisson blend (MIXED_CLONE preserves texture detail)
    cx, cy  = int(np.mean(xs)), int(np.mean(ys))
    blended = cv2.seamlessClone(corrected, base, face_mask, (cx, cy), cv2.MIXED_CLONE)

    # Step 3 — L-channel brightness correction
    # Poisson blending can pull lightness toward the target (lighter avatar).
    # If output L-mean drifts > 8 units above source, pull it back.
    out_lab   = cv2.cvtColor(blended, cv2.COLOR_BGR2LAB)
    l, a, b_ch = cv2.split(out_lab)
    out_L_mean = float(l[face_mask > 0].astype(np.float32).mean())
    print(f"[blend] L-mean after  seamlessClone: {out_L_mean:.1f}  (drift={out_L_mean-src_L_mean:+.1f})")

    if out_L_mean > src_L_mean + 8:
        correction = out_L_mean - src_L_mean
        # Use feathered mask weight (0.0–1.0) so correction fades at oval boundary
        # — prevents a hard darkened ring where the mask edge is
        mask_weight = face_mask.astype(np.float32) / 255.0
        l_f = l.astype(np.float32)
        l_f = l_f - correction * mask_weight
        l   = np.clip(l_f, 0, 255).astype(np.uint8)
        blended = cv2.cvtColor(cv2.merge([l, a, b_ch]), cv2.COLOR_LAB2BGR)
        print(f"[blend] L-channel corrected by -{correction:.1f} (feathered) to preserve skin tone")

    # Step 4 — Eye artifact repair
    if uv_landmarks is not None:
        blended = _repair_eye_artifacts(blended, corrected, uv_landmarks)

    return blended
