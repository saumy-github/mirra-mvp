"""Step 3 of product_ingestion: colour extraction."""

from __future__ import annotations

from tshirt_extractor import ColourExtractor, ColourResult, validate_hex


def extract_colours(rgba_image) -> tuple[ColourResult, bool]:
    """Extract base colour + palette and report HEX validity."""
    extractor = ColourExtractor()
    result = extractor.extract(rgba_image)
    return result, bool(result.success and validate_hex(result.base_colour_hex))
