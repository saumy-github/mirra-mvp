"""Step 4 of product_ingestion: design extraction.

Extracts logos, prints, or graphics from the segmented garment
using edge detection, contour analysis, and contrast filtering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import cv2


@dataclass
class DesignResult:
    """Result from Stage 4: Design Extraction."""
    graphic_image: Optional[np.ndarray] = None   # RGBA
    has_design: bool = False
    design_coverage_percent: float = 0.0
    message: str = ""


class DesignExtractor:
    """
    Extracts logos, prints, or graphics from the segmented garment
    using edge detection, contour analysis, and contrast filtering.
    """

    def __init__(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
        min_area_ratio: float = 0.01,    # 1% of garment
        max_area_ratio: float = 0.80,    # 80% of garment
        contrast_threshold: float = 0.25,
    ):
        self.canny_low = canny_low
        self.canny_high = canny_high
        self.min_area_ratio = min_area_ratio
        self.max_area_ratio = max_area_ratio
        self.contrast_threshold = contrast_threshold

    def extract(self, rgba_image: np.ndarray) -> DesignResult:
        """
        Detect and crop any graphic / print from the garment image.

        Pipeline:
          1. Mask out background
          2. Gaussian blur → Canny edge detection
          3. Morphological closing to join fragmented edges
          4. Contour filtering by area
          5. Contrast check (ensure graphic ≠ plain fabric)
          6. Bounding-box crop → transparent RGBA
        """
        if rgba_image is None or rgba_image.shape[2] < 4:
            return DesignResult(message="Invalid RGBA image")

        rgb = rgba_image[:, :, :3]
        alpha = rgba_image[:, :, 3]

        # Work only inside garment mask
        mask = (alpha > 10).astype(np.uint8) * 255
        garment_area = int(np.sum(mask > 0))
        if garment_area == 0:
            return DesignResult(message="Empty garment mask")

        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        gray_masked = cv2.bitwise_and(gray, gray, mask=mask)

        # ── Edge detection ───────────────────────────────────
        blurred = cv2.GaussianBlur(gray_masked, (5, 5), 0)
        edges = cv2.Canny(blurred, self.canny_low, self.canny_high)

        # Morphological closing to connect fragmented edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        edges_closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

        # ── Contour analysis ─────────────────────────────────
        contours, _ = cv2.findContours(edges_closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return DesignResult(message="No contours found — likely plain garment")

        # Filter contours by area
        min_area = garment_area * self.min_area_ratio
        max_area = garment_area * self.max_area_ratio

        valid_contours = [
            c for c in contours
            if min_area <= cv2.contourArea(c) <= max_area
        ]

        if not valid_contours:
            return DesignResult(message="No contours matched size criteria — likely plain garment")

        # Use the largest valid contour
        best_contour = max(valid_contours, key=cv2.contourArea)
        design_area = cv2.contourArea(best_contour)
        coverage = design_area / garment_area * 100

        # ── Contrast filtering ───────────────────────────────
        x, y, w, h = cv2.boundingRect(best_contour)

        # Ensure bounding box is within image bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, rgba_image.shape[1] - x)
        h = min(h, rgba_image.shape[0] - y)

        roi_gray = gray_masked[y:y+h, x:x+w]
        roi_mask = mask[y:y+h, x:x+w]
        roi_pixels = roi_gray[roi_mask > 0]

        if len(roi_pixels) < 10:
            return DesignResult(message="ROI too small for contrast analysis")

        # Check local contrast (std / mean) — high contrast = graphic
        local_std = float(np.std(roi_pixels))
        local_mean = float(np.mean(roi_pixels)) if np.mean(roi_pixels) > 0 else 1
        contrast_ratio = local_std / local_mean

        if contrast_ratio < self.contrast_threshold:
            return DesignResult(
                message=f"Low contrast ({contrast_ratio:.3f}) — likely fabric texture, not a graphic"
            )

        # ── Crop graphic as transparent RGBA ────────────────
        # Create a contour mask for just the graphic region
        graphic_mask = np.zeros_like(mask)
        cv2.drawContours(graphic_mask, [best_contour], -1, 255, -1)

        # Crop to bounding box
        crop_rgba = rgba_image[y:y+h, x:x+w].copy()
        crop_gm = graphic_mask[y:y+h, x:x+w]

        # Apply graphic contour mask to alpha channel
        crop_rgba[:, :, 3] = np.minimum(crop_rgba[:, :, 3], crop_gm)

        return DesignResult(
            graphic_image=crop_rgba,
            has_design=True,
            design_coverage_percent=coverage,
            message=f"Graphic found ({coverage:.1f}% of garment, contrast={contrast_ratio:.3f})",
        )


def make_empty_graphic_like(rgba_image):
    """Create an empty transparent RGBA image matching the segmented garment size."""
    height, width = rgba_image.shape[:2]
    return np.zeros((height, width, 4), dtype=np.uint8)


def extract_design(rgba_image) -> DesignResult:
    """Extract a graphic diffuse map from a segmented cloth image.

    Keeps the original module API used by the runner: returns a DesignResult.
    """
    extractor = DesignExtractor()
    return extractor.extract(rgba_image)

