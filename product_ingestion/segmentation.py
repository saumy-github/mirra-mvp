"""Step 2 of product_ingestion: segmentation."""

from __future__ import annotations

from pathlib import Path

from tshirt_extractor import GarmentSegmentor, SegmentationResult, validate_transparent_bg


def run_segmentation(image_path: str | Path) -> tuple[SegmentationResult, bool]:
    """Segment the selected cloth image and report edge transparency validity."""
    segmentor = GarmentSegmentor()
    result = segmentor.segment(str(image_path))
    transparent_bg_ok = bool(result.rgba_image is not None and validate_transparent_bg(result.rgba_image))
    return result, transparent_bg_ok
