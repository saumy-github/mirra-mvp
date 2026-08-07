"""
Hair pass: extract hair from photo + colorize avatar's hair texture.

Two separate outputs:
  A) hair_main.jpg replacement — colorized to match user's hair
  B) (future) hair sprite composite onto rendered output

MediaPipe's face mesh stops at the hairline. This module:
  1. Detects top-of-forehead landmarks (10, 338, 297, 332, 284) as hairline boundary
  2. Estimates hair volume from photo silhouette above that line
  3. Samples dominant hair color from the extracted region
  4. Colorizes avatar's hair_main.jpg texture to match
  5. For sprite composite: loads/generates a voluminous curly black hair sprite
     anchored to the forehead landmark positions
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import cv2
import numpy as np


# Hairline boundary landmarks (top of forehead)
_HAIRLINE_INDICES: list[int] = [10, 338, 297, 332, 284, 251, 21, 54, 103, 67, 109]

_HAIR_TEXTURE_NAME = "hair_main.jpg"
_JPEG_QUALITY      = 92
_SPRITES_DIR       = Path(__file__).parent / "sprites"


# ── Hair color sampling ───────────────────────────────────────────────────────

def _sample_hair_color(
    photo: np.ndarray,
    landmarks_px: list[tuple[int, int]],
) -> np.ndarray | None:
    """
    Sample median hair color from the region above the hairline.

    Filters out background (high saturation, low value) to isolate actual hair pixels.
    Returns (3,) BGR float32 or None if insufficient hair pixels found.
    """
    h_img, w_img = photo.shape[:2]
    hairline_pts  = [landmarks_px[i] for i in _HAIRLINE_INDICES]
    hairline_y    = min(p[1] for p in hairline_pts)
    hairline_x_min = min(p[0] for p in hairline_pts)
    hairline_x_max = max(p[0] for p in hairline_pts)

    margin = int((hairline_x_max - hairline_x_min) * 0.25)
    x1 = max(0, hairline_x_min - margin)
    x2 = min(w_img, hairline_x_max + margin)
    y1 = max(0, hairline_y - int(hairline_y * 0.65))
    y2 = max(0, hairline_y - 8)

    if y2 <= y1 or x2 <= x1:
        return None

    region = photo[y1:y2, x1:x2]
    if region.size == 0:
        return None

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    not_bg = (hsv[:, :, 1] > 25) | (hsv[:, :, 2] < 170)
    if not_bg.sum() < 50:
        not_bg = np.ones(region.shape[:2], dtype=bool)

    pixels = region[not_bg]
    return None if len(pixels) == 0 else np.median(pixels, axis=0).astype(np.float32)


# ── Avatar hair texture colorization ─────────────────────────────────────────

def _colorize_texture(texture: np.ndarray, target_bgr: np.ndarray) -> np.ndarray:
    """
    LAB color transfer: shift avatar hair texture to match user's hair color
    while preserving shading highlights and shadow structure.
    """
    tex_lab = cv2.cvtColor(texture, cv2.COLOR_BGR2LAB).astype(np.float32)
    tgt_px  = target_bgr.reshape(1, 1, 3).astype(np.uint8)
    tgt_lab = cv2.cvtColor(tgt_px, cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]

    result = tex_lab.copy()
    result[:, :, 0] = np.clip(tex_lab[:, :, 0] + (tgt_lab[0] - tex_lab[:, :, 0].mean()) * 0.55, 0, 255)
    result[:, :, 1] = np.clip(tex_lab[:, :, 1] + (tgt_lab[1] - tex_lab[:, :, 1].mean()),          0, 255)
    result[:, :, 2] = np.clip(tex_lab[:, :, 2] + (tgt_lab[2] - tex_lab[:, :, 2].mean()),          0, 255)

    return cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_LAB2BGR)


# ── Hair sprite ───────────────────────────────────────────────────────────────

def _generate_hair_sprite(width: int, height: int) -> np.ndarray:
    """
    Procedurally generate a voluminous curly black hair sprite (BGRA).

    Produces a wide dome shape above the forehead with irregular curly edges
    to approximate voluminous medium-length curly black hair.
    """
    sprite = np.zeros((height, width, 4), dtype=np.uint8)
    alpha  = np.zeros((height, width), dtype=np.float32)

    cx = width  // 2
    cy = int(height * 0.55)           # centre of hair dome
    rx = max(1, int(width  * 0.52))   # horizontal radius
    ry = max(1, int(height * 0.60))   # vertical radius (tall for volume)

    cv2.ellipse(alpha, (cx, cy), (rx, ry), 0, 180, 360, 1.0, -1)  # upper half dome

    # Add irregular curly bumps around the silhouette
    rng = np.random.default_rng(seed=7)
    n_bumps = 18
    for angle_deg in np.linspace(185, 355, n_bumps):
        angle = np.deg2rad(angle_deg)
        bx = int(cx + (rx + rng.integers(8, 28)) * np.cos(angle))
        by = int(cy + (ry + rng.integers(5, 20)) * np.sin(angle))
        brad = rng.integers(12, 26)
        cv2.circle(alpha, (bx, by), brad, 1.0, -1)

    # Feather edges for soft silhouette
    alpha = cv2.GaussianBlur(alpha, (21, 21), 7)
    alpha = np.clip(alpha, 0, 1)

    # Near-black hair color with slight warmth
    sprite[:, :, 0] = 18   # B
    sprite[:, :, 1] = 14   # G
    sprite[:, :, 2] = 22   # R — slight warm
    sprite[:, :, 3] = (alpha * 245).astype(np.uint8)

    return sprite


def _load_or_generate_hair_sprite(width: int, height: int) -> np.ndarray:
    """
    Use a pre-made hair sprite PNG if available, otherwise generate one.
    Place a custom sprite at: clo_avatar_generation/face/sprites/hair.png
    """
    candidate = _SPRITES_DIR / "hair.png"
    if candidate.exists():
        img = cv2.imread(str(candidate), cv2.IMREAD_UNCHANGED)
        if img is not None and img.shape[2] == 4:
            return cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
    return _generate_hair_sprite(width, height)


# ── Public API ────────────────────────────────────────────────────────────────

def extract_hair_texture(avt_path: Path) -> np.ndarray | None:
    """Read hair_main.jpg from .avt and return as BGR array."""
    raw = avt_path.read_bytes()
    zs  = raw.find(b"PK\x03\x04")
    if zs < 0:
        return None
    try:
        with zipfile.ZipFile(io.BytesIO(raw[zs:]), "r") as z:
            if _HAIR_TEXTURE_NAME not in z.namelist():
                return None
            arr = np.frombuffer(z.read(_HAIR_TEXTURE_NAME), dtype=np.uint8)
            return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def build_personalized_hair(
    photo_path: Path,
    landmarks: dict,
    source_avt: Path,
) -> np.ndarray | None:
    """
    Colorize the avatar's hair_main.jpg to match the user's hair color.

    Returns (H, W, 3) uint8 BGR colorized hair texture, or None on failure.
    """
    if not landmarks["detected"]:
        return None
    photo = cv2.imread(str(photo_path))
    if photo is None:
        return None
    texture = extract_hair_texture(source_avt)
    if texture is None:
        return None
    color = _sample_hair_color(photo, landmarks["landmarks_px"])
    if color is None:
        return None
    return _colorize_texture(texture, color)


def composite_hair_on_uv(
    uv_texture: np.ndarray,
    landmarks: dict,
    uv_all_px: list[list[int]],
) -> np.ndarray:
    """
    Composite a voluminous curly hair sprite onto the UV face texture,
    anchored to the top-of-forehead landmark positions.

    This updates the UV texture image so hair appears correctly when
    the texture is applied to the 3D head mesh.

    Args:
        uv_texture  : (H, W, 3) BGR — current face UV texture
        landmarks   : output of detect.detect()
        uv_all_px   : all 478 UV landmark positions (from template)

    Returns:
        (H, W, 3) BGR — UV texture with hair composited
    """
    if not landmarks["detected"]:
        return uv_texture

    uv_h, uv_w = uv_texture.shape[:2]

    # Hairline boundary in UV space
    hairline_uv = [uv_all_px[i] for i in _HAIRLINE_INDICES]
    hairline_y  = min(p[1] for p in hairline_uv)
    hairline_x1 = min(p[0] for p in hairline_uv)
    hairline_x2 = max(p[0] for p in hairline_uv)

    face_w = hairline_x2 - hairline_x1
    if face_w <= 0:
        return uv_texture

    # Sprite size: same width as face, height = 70% of face width (voluminous)
    sprite_w = int(face_w * 1.15)
    sprite_h = int(face_w * 0.70)
    sprite_x1 = max(0, hairline_x1 - int(face_w * 0.075))
    sprite_y1 = max(0, hairline_y - sprite_h)
    sprite_x2 = min(uv_w, sprite_x1 + sprite_w)
    sprite_y2 = min(uv_h, sprite_y1 + sprite_h)

    actual_w = sprite_x2 - sprite_x1
    actual_h = sprite_y2 - sprite_y1
    if actual_w <= 0 or actual_h <= 0:
        return uv_texture

    sprite = _load_or_generate_hair_sprite(actual_w, actual_h)
    result = uv_texture.copy()
    alpha  = sprite[:actual_h, :actual_w, 3].astype(np.float32) / 255.0

    for c in range(3):
        src = result[sprite_y1:sprite_y2, sprite_x1:sprite_x2, c].astype(np.float32)
        dst = sprite[:actual_h, :actual_w, c].astype(np.float32)
        result[sprite_y1:sprite_y2, sprite_x1:sprite_x2, c] = np.clip(
            src * (1 - alpha) + dst * alpha, 0, 255
        ).astype(np.uint8)

    return result
