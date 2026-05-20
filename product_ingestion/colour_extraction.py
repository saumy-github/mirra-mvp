"""Step 3 of product_ingestion: colour extraction (K-Means in LAB).

Determines the dominant garment colour using K-Means clustering
in the perceptually uniform LAB colour space.

Improvements over the original:
  1. Float32 LAB conversion  — no precision loss from 8-bit rounding.
  2. Skin-tone exclusion     — HSV filter removes skin pixels before clustering
                                so they don't pollute garment colour.
  3. Adaptive K              — silhouette score picks the best K (2–8) instead
                                of always using K=5.
  4. Weighted voting         — base colour is the biggest cluster that isn't
                                near-white or near-black, instead of blindly
                                picking the mid-lightness cluster.
  5. CLO3D hex output        — a separate `clo3d_hex` field with uppercase hex
                                in "#RRGGBB" format compatible with CLO3D.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np
import cv2

try:
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# ─────────────────────────────────────────────────────────────────────────────
#  Skin-tone HSV range
# ─────────────────────────────────────────────────────────────────────────────
#  These cover the typical range of human skin tones in HSV space.
#  We use TWO ranges because skin can appear slightly reddish or yellowish.
#
#  Think of it as a colour filter:
#    - Hue 0–25   → reddish/orange skin
#    - Hue 330–360 → pinkish skin (wraps around)
#    - Saturation 20–170 → not too grey, not too vivid
#    - Value 80–255 → not too dark
#
#  Any pixel that falls inside these ranges gets removed before clustering.

_SKIN_LOWER_1 = np.array([0,   20,  80], dtype=np.uint8)
_SKIN_UPPER_1 = np.array([25, 170, 255], dtype=np.uint8)
_SKIN_LOWER_2 = np.array([165, 20,  80], dtype=np.uint8)   # 330°/2 = 165
_SKIN_UPPER_2 = np.array([180, 170, 255], dtype=np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
#  Data classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ColorInfo:
    """Information about a single extracted colour."""
    rgb: Tuple[int, int, int]
    lab: Tuple[float, float, float]
    hex_code: str          # lowercase "#rrggbb"
    clo3d_hex: str         # uppercase "#RRGGBB" — CLO3D compatible
    percentage: float

    def to_dict(self) -> dict:
        return {
            "rgb": list(self.rgb),
            "lab": [round(v, 2) for v in self.lab],
            "hex": self.hex_code,
            "clo3d_hex": self.clo3d_hex,
            "percentage": round(self.percentage, 2),
        }


@dataclass
class ColourResult:
    """Result from Stage 3: Colour Extraction."""
    base_colour_hex: str = "#000000"        # lowercase — existing API
    clo3d_base_hex: str = "#000000"         # uppercase — for CLO3D
    palette: List[ColorInfo] = field(default_factory=list)
    k_used: int = 0                         # how many clusters were used
    skin_pixels_removed: int = 0            # how many skin pixels were filtered out
    success: bool = False
    message: str = ""


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _rgb_to_hex_lower(rgb: Tuple[int, int, int]) -> str:
    """RGB → '#rrggbb' (lowercase, existing format)."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _rgb_to_hex_upper(rgb: Tuple[int, int, int]) -> str:
    """RGB → '#RRGGBB' (uppercase, CLO3D format)."""
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _is_near_white_or_black(lab: Tuple[float, float, float]) -> bool:
    """
    Check if a LAB colour is near-white or near-black.

    In LAB:
      L = 0   → pure black
      L = 100 → pure white

    We treat L < 15 as "near black" and L > 85 as "near white".
    These are typically shadows/highlights on the garment, not the actual
    fabric colour.
    """
    return lab[0] < 15.0 or lab[0] > 85.0


def _remove_skin_pixels(rgb_pixels: np.ndarray) -> tuple[np.ndarray, int]:
    """
    Remove pixels that look like skin.

    How it works:
      1. Convert RGB pixels to HSV colour space.
         (HSV separates colour (Hue) from brightness (Value), making it
          easier to identify skin tones regardless of lighting.)
      2. Check if each pixel's Hue/Saturation/Value falls within known
         skin-tone ranges.
      3. Remove those pixels.

    Returns the filtered pixels and the count of removed pixels.
    """
    # cv2.cvtColor needs a 2D image shape: (N, 1, 3)
    # cv2.inRange also needs the same shape to match the boundary arrays.
    hsv_2d = cv2.cvtColor(
        rgb_pixels.reshape(-1, 1, 3).astype(np.uint8),
        cv2.COLOR_RGB2HSV,
    )  # shape: (N, 1, 3) — keep this shape for inRange

    # Build a mask: True = skin pixel
    skin_mask_1 = cv2.inRange(hsv_2d, _SKIN_LOWER_1, _SKIN_UPPER_1).flatten().astype(bool)
    skin_mask_2 = cv2.inRange(hsv_2d, _SKIN_LOWER_2, _SKIN_UPPER_2).flatten().astype(bool)
    is_skin = skin_mask_1 | skin_mask_2

    removed = int(np.sum(is_skin))
    return rgb_pixels[~is_skin], removed


def _rgb_to_lab_float32(rgb_pixels: np.ndarray) -> np.ndarray:
    """
    Convert RGB pixels to LAB using float32 for better precision.

    The old code did:
      pixels.astype(np.uint8) → cv2.cvtColor → float32
    This loses precision because uint8 only has 256 levels.

    The new code:
      pixels → float32 [0..1] → cv2.cvtColor → LAB
    cv2 treats float32 input as [0..1] range and returns full-precision LAB.
    """
    pixels_f32 = rgb_pixels.astype(np.float32) / 255.0
    lab = cv2.cvtColor(
        pixels_f32.reshape(-1, 1, 3),
        cv2.COLOR_RGB2LAB,
    ).reshape(-1, 3)
    return lab


def _find_best_k(lab_pixels: np.ndarray, k_min: int = 2, k_max: int = 8) -> int:
    """
    Find the optimal number of clusters using the silhouette score.

    What is silhouette score?
      For each pixel, it measures:
        a) How similar it is to pixels in its own cluster.
        b) How different it is from pixels in the nearest other cluster.

      Score ranges from -1 to +1:
        +1  → clusters are well separated (good)
         0  → clusters overlap (meh)
        -1  → pixels are in the wrong cluster (bad)

    We try K = 2, 3, 4, ... 8 and pick the K with the highest score.
    This means a plain white t-shirt gets K=2 (white + shadow), while a
    tie-dye shirt might get K=7.

    To keep it fast, we subsample to 5000 pixels for the scoring step.
    """
    n = len(lab_pixels)
    if n < k_max:
        return min(n, k_min)

    # Subsample for speed — silhouette on 50k pixels is slow
    rng = np.random.default_rng(42)
    if n > 5000:
        sample_idx = rng.choice(n, 5000, replace=False)
        sample = lab_pixels[sample_idx]
    else:
        sample = lab_pixels

    best_k = k_min
    best_score = -1.0

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=5, max_iter=100)
        labels = km.fit_predict(sample)

        # silhouette_score needs at least 2 unique labels
        if len(set(labels)) < 2:
            continue

        score = silhouette_score(sample, labels, sample_size=min(2000, len(sample)))
        if score > best_score:
            best_score = score
            best_k = k

    return best_k


# ─────────────────────────────────────────────────────────────────────────────
#  Main extractor
# ─────────────────────────────────────────────────────────────────────────────

class ColourExtractor:
    """
    Determines the dominant garment colour using K-Means clustering
    in the perceptually uniform LAB colour space.

    Improvements:
      - Float32 LAB for better precision
      - Skin-tone pixels are excluded before clustering
      - Adaptive K (silhouette score picks 2–8)
      - Base colour = largest cluster that isn't near-white/near-black
    """

    def __init__(self, max_samples: int = 50_000):
        self.max_samples = max_samples

    def extract(self, rgba_image: np.ndarray) -> ColourResult:
        """
        Extract dominant colour and palette from an RGBA garment image.

        Pipeline:
          1. Grab non-transparent pixels (alpha > 10).
          2. Remove skin-tone pixels.
          3. Subsample to max_samples for speed.
          4. Convert RGB → LAB (float32 precision).
          5. Find optimal K via silhouette score.
          6. Run K-Means with optimal K.
          7. Build palette; pick base colour via weighted voting.
        """
        if not HAS_SKLEARN:
            return ColourResult(success=False, message="scikit-learn not installed")

        if rgba_image is None or rgba_image.shape[2] < 4:
            return ColourResult(success=False, message="Invalid RGBA image")

        # ── Step 1: extract non-transparent pixels ────────────────────────
        # Pixels with alpha <= 10 are background (from segmentation stage).
        alpha = rgba_image[:, :, 3]
        mask = alpha > 10
        rgb_pixels = rgba_image[:, :, :3][mask]   # shape (N, 3)

        if len(rgb_pixels) < 2:
            return ColourResult(success=False, message="Not enough opaque pixels")

        # ── Step 2: remove skin-tone pixels ───────────────────────────────
        # When segmentation isn't perfect (e.g. neck/arms visible), skin
        # pixels can pull the colour toward beige/brown.  We filter them
        # out so only fabric pixels remain.
        rgb_pixels, skin_removed = _remove_skin_pixels(rgb_pixels)

        if len(rgb_pixels) < 2:
            return ColourResult(
                success=False,
                message="All pixels were filtered as skin — check segmentation",
            )

        # ── Step 3: subsample for performance ─────────────────────────────
        if len(rgb_pixels) > self.max_samples:
            idx = np.random.default_rng(42).choice(
                len(rgb_pixels), self.max_samples, replace=False
            )
            rgb_pixels = rgb_pixels[idx]

        # ── Step 4: convert to LAB (float32 for precision) ────────────────
        lab_pixels = _rgb_to_lab_float32(rgb_pixels)

        # ── Step 5: find optimal K ────────────────────────────────────────
        best_k = _find_best_k(lab_pixels)

        # ── Step 6: run K-Means with optimal K ───────────────────────────
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(lab_pixels)

        # ── Step 7: build palette ─────────────────────────────────────────
        palette: List[ColorInfo] = []
        total = len(labels)

        for i in range(best_k):
            cluster_mask = labels == i
            pct = float(np.sum(cluster_mask) / total * 100)

            lab_center = kmeans.cluster_centers_[i]
            # Use mean of original RGB pixels in this cluster (more accurate
            # than converting the LAB center back, which can clip).
            mean_rgb = tuple(int(v) for v in np.mean(rgb_pixels[cluster_mask], axis=0))

            palette.append(ColorInfo(
                rgb=mean_rgb,
                lab=tuple(float(v) for v in lab_center),
                hex_code=_rgb_to_hex_lower(mean_rgb),
                clo3d_hex=_rgb_to_hex_upper(mean_rgb),
                percentage=pct,
            ))

        # ── Pick base colour via weighted voting ─────────────────────────
        # Sort by percentage (largest first).
        # Pick the first cluster that is NOT near-white and NOT near-black.
        # If every cluster is near-white/black (unlikely), just take the
        # biggest one.
        palette.sort(key=lambda c: c.percentage, reverse=True)

        base_colour = palette[0]  # default: biggest cluster
        for entry in palette:
            if not _is_near_white_or_black(entry.lab):
                base_colour = entry
                break

        return ColourResult(
            base_colour_hex=base_colour.hex_code,        # existing API
            clo3d_base_hex=base_colour.clo3d_hex,        # CLO3D output
            palette=palette,
            k_used=best_k,
            skin_pixels_removed=skin_removed,
            success=True,
            message="OK",
        )


# ─────────────────────────────────────────────────────────────────────────────
#  Public helpers (unchanged API)
# ─────────────────────────────────────────────────────────────────────────────

def validate_hex(hex_code: str) -> bool:
    """Validate a hex colour code."""
    if not hex_code.startswith("#") or len(hex_code) != 7:
        return False
    try:
        int(hex_code[1:], 16)
        return True
    except ValueError:
        return False


def extract_colours(rgba_image) -> tuple[ColourResult, bool]:
    """Extract base colour + palette and report HEX validity.

    Keeps the original module API used by the runner: returns (ColourResult, bool).
    """
    extractor = ColourExtractor()
    result = extractor.extract(rgba_image)
    return result, bool(result.success and validate_hex(result.base_colour_hex))
