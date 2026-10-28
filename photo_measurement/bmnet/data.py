"""Silhouette canonicalisation and scalar features: the network's input preprocessing.

`canonical_view` is the single preprocessing used for training AND inference, so a
MediaPipe mask from a phone photo and a BodyM mask go through identical maths. The
training dataset and loop live in the R&D repo (for_measurements, mirra_avatar/bmnet).
"""
from __future__ import annotations

import math
import random

import cv2
import numpy as np

VIEW_H, VIEW_W = 384, 192          # per-view tensor size (person fills 90% of the height)
FILL = 0.90

# The 14 BodyM measurements, in a fixed order. Units: cm.
TARGETS = ["ankle", "arm-length", "bicep", "calf", "chest", "forearm", "height", "hip",
           "leg-length", "shoulder-breadth", "shoulder-to-crotch", "thigh", "waist", "wrist"]


def canonical_view(mask: np.ndarray, rng: random.Random | None = None) -> np.ndarray:
    """bool HxW person mask -> float32 VIEW_HxVIEW_W in [0,1], person centred, scaled so
    head-to-foot spans FILL of the height (camera distance and framing removed;
    absolute scale comes from the height input instead). With `rng`, applies random
    segmentation/camera noise for training."""
    m = mask.astype(np.uint8)
    if rng is not None:
        m = _augment(m, rng)
    ys, xs = np.nonzero(m)
    if ys.size == 0:
        raise ValueError("empty mask")
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    crop = m[y0:y1, x0:x1].astype(np.float32)
    scale = FILL * VIEW_H / crop.shape[0]
    if rng is not None:
        scale *= rng.uniform(0.97, 1.03)
    new_w = max(1, round(crop.shape[1] * scale))
    new_h = max(1, round(crop.shape[0] * scale))
    if new_w > VIEW_W:  # very wide pose: shrink to fit (keeps aspect)
        scale *= VIEW_W / new_w
        new_w, new_h = VIEW_W, max(1, round(crop.shape[0] * scale))
    small = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
    out = np.zeros((VIEW_H, VIEW_W), np.float32)
    oy = (VIEW_H - new_h) // 2 + (rng.randint(-4, 4) if rng else 0)
    ox = (VIEW_W - new_w) // 2 + (rng.randint(-4, 4) if rng else 0)
    oy, ox = int(np.clip(oy, 0, VIEW_H - new_h)), int(np.clip(ox, 0, VIEW_W - new_w))
    out[oy:oy + new_h, ox:ox + new_w] = small
    return out


def _augment(m: np.ndarray, rng: random.Random) -> np.ndarray:
    """Make BodyM masks look like other segmenters' masks (e.g. MediaPipe on a phone
    photo): boundary bias, ragged edges, slight camera roll/perspective."""
    h, w = m.shape
    # boundary bias: segmenters systematically grow or shrink the person a little
    k = rng.choice([0, 0, 1, 2, 3, 4, 5])
    if k:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
        m = cv2.dilate(m, kernel) if rng.random() < 0.5 else cv2.erode(m, kernel)
    # camera roll, horizontal stretch (lens / distance), slight shear
    if rng.random() < 0.8:
        ang = rng.uniform(-3, 3)
        sx = rng.uniform(0.96, 1.04)
        sh = rng.uniform(-0.03, 0.03)
        a = math.radians(ang)
        M = np.array([[sx * math.cos(a), -math.sin(a) + sh, 0],
                      [sx * math.sin(a), math.cos(a), 0]], np.float32)
        c = np.array([w / 2, h / 2], np.float32)
        M[:, 2] = c - M[:, :2] @ c
        m = cv2.warpAffine(m, M, (w, h), flags=cv2.INTER_NEAREST)
    # ragged / soft edges: blur then re-threshold at a random level
    if rng.random() < 0.6:
        s = rng.uniform(1.0, 4.0)
        b = cv2.GaussianBlur(m.astype(np.float32), (0, 0), s)
        m = (b > rng.uniform(0.35, 0.65)).astype(np.uint8)
    return m


N_SCALARS = 5


def scalar_features(height_cm: float, weight_kg: float | None, gender: str | None) -> np.ndarray:
    """Normalised height, weight, BMI, sex (+1 male, -1 female, 0 unknown) and a
    weight-known flag. Weight and sex are optional at inference time."""
    g = {"male": 1.0, "female": -1.0}.get((gender or "").lower(), 0.0)
    if weight_kg is None:
        w = bmi = 0.0
        known = 0.0
    else:
        w = (weight_kg - 75) / 15
        bmi = (weight_kg / (height_cm / 100) ** 2 - 25) / 5
        known = 1.0
    return np.array([(height_cm - 170) / 10, w, bmi, g, known], np.float32)
