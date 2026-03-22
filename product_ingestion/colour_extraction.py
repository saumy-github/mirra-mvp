"""Step 3 of product_ingestion: colour extraction (K-Means in LAB).

Determines the dominant garment colour using K-Means clustering
in the perceptually uniform LAB colour space.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional

import numpy as np
import cv2

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


@dataclass
class ColorInfo:
    """Information about a single extracted colour."""
    rgb: Tuple[int, int, int]
    lab: Tuple[float, float, float]
    hex_code: str
    percentage: float

    def to_dict(self) -> dict:
        return {
            "rgb": list(self.rgb),
            "lab": [round(v, 2) for v in self.lab],
            "hex": self.hex_code,
            "percentage": round(self.percentage, 2),
        }


@dataclass
class ColourResult:
    """Result from Stage 3: Colour Extraction."""
    base_colour_hex: str = "#000000"
    palette: List[ColorInfo] = field(default_factory=list)
    success: bool = False
    message: str = ""


class ColourExtractor:
    """
    Determines the dominant garment colour using K-Means clustering
    in the perceptually uniform LAB colour space.
    """

    def __init__(self, n_clusters: int = 5, max_samples: int = 50_000):
        self.n_clusters = n_clusters
        self.max_samples = max_samples

    def extract(self, rgba_image: np.ndarray) -> ColourResult:
        """
        Extract dominant colour and palette from an RGBA garment image.

        Picks the **mid-lightness** cluster as the base colour to avoid
        shadow/highlight bias on fabric photos.
        """
        if not HAS_SKLEARN:
            return ColourResult(success=False, message="scikit-learn not installed")

        if rgba_image is None or rgba_image.shape[2] < 4:
            return ColourResult(success=False, message="Invalid RGBA image")

        # Extract non-transparent pixels
        alpha = rgba_image[:, :, 3]
        mask = alpha > 10
        rgb_pixels = rgba_image[:, :, :3][mask]   # shape (N, 3)

        if len(rgb_pixels) < self.n_clusters:
            return ColourResult(success=False, message="Not enough opaque pixels")

        # Subsample for performance
        if len(rgb_pixels) > self.max_samples:
            idx = np.random.default_rng(42).choice(len(rgb_pixels), self.max_samples, replace=False)
            rgb_pixels = rgb_pixels[idx]

        # Convert to LAB
        pixels_for_cv = rgb_pixels.reshape(-1, 1, 3).astype(np.uint8)
        lab_pixels = cv2.cvtColor(pixels_for_cv, cv2.COLOR_RGB2LAB).reshape(-1, 3).astype(np.float32)

        # K-Means clustering
        kmeans = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(lab_pixels)

        # Build palette
        palette: List[ColorInfo] = []
        total = len(labels)
        for i in range(self.n_clusters):
            cluster_mask = labels == i
            pct = float(np.sum(cluster_mask) / total * 100)

            lab_center = kmeans.cluster_centers_[i]
            mean_rgb = np.mean(rgb_pixels[cluster_mask], axis=0).astype(int)
            hex_code = "#{:02x}{:02x}{:02x}".format(*mean_rgb)

            palette.append(ColorInfo(
                rgb=tuple(int(v) for v in mean_rgb),
                lab=tuple(float(v) for v in lab_center),
                hex_code=hex_code,
                percentage=pct,
            ))

        # Sort by L* (lightness) to pick mid-lightness cluster
        palette.sort(key=lambda c: c.lab[0])

        # Mid-lightness selection: pick the middle cluster
        mid_idx = len(palette) // 2
        base_colour = palette[mid_idx]

        # Re-sort by percentage for the output palette
        palette.sort(key=lambda c: c.percentage, reverse=True)

        return ColourResult(
            base_colour_hex=base_colour.hex_code,
            palette=palette,
            success=True,
            message="OK",
        )


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

