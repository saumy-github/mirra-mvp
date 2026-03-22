"""Step 4 of product_ingestion: design extraction."""

from __future__ import annotations

import numpy as np

from tshirt_extractor import DesignExtractor, DesignResult


def extract_design(rgba_image) -> DesignResult:
    """Extract a graphic diffuse map from a segmented cloth image."""
    extractor = DesignExtractor()
    return extractor.extract(rgba_image)


def make_empty_graphic_like(rgba_image):
    """Create an empty transparent RGBA image matching the segmented garment size."""
    height, width = rgba_image.shape[:2]
    return np.zeros((height, width, 4), dtype=np.uint8)
