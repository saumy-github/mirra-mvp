"""
Vision Pipeline — Single-Image Appearance Extraction
=====================================================

Convenience wrapper around tshirt_extractor stages for processing
a **single pre-routed** front image.

Runs three sub-steps:
  1. Garment Segmentation  (RMBG-1.4)
  2. Base Colour Extraction (LAB K-Means)
  3. Graphic Flattening     (Edge + Contour + Contrast)

Usage:
  python vision_pipeline.py routed/front_img.png -o output/vision_001
"""

import sys
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from PIL import Image

_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from tshirt_extractor import (
    GarmentSegmentor,
    ColourExtractor,
    DesignExtractor,
    ColourResult,
    DesignResult,
    validate_hex,
    validate_transparent_bg,
)


@dataclass
class VisionResult:
    """Result from the vision pipeline."""
    base_garment_path: str = ""
    graphic_diffuse_map: str = ""
    base_color_hex: str = "#000000"
    colors_json_path: str = ""
    result_json_path: str = ""
    success: bool = False


class VisionPipeline:
    """
    Three-step vision pipeline for a single garment image.

    Steps:
      1. segment()   — Isolate garment from background
      2. extract_colour() — K-Means LAB → HEX
      3. extract_graphic() — Edge + Contour → diffuse map
    """

    def __init__(self):
        self.segmentor = GarmentSegmentor()
        self.colour_extractor = ColourExtractor()
        self.design_extractor = DesignExtractor()

    def run_full_vision_track(
        self,
        image_path: str,
        output_dir: str,
    ) -> VisionResult:
        """
        Run full vision track on a single image.

        Args:
            image_path: Path to a garment image (ideally the routed front image)
            output_dir: Directory to save output files

        Returns:
            VisionResult with paths to all generated files
        """
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        result = VisionResult()

        print("\n" + "=" * 50)
        print("VISION PIPELINE")
        print("=" * 50)
        print(f"  Input:  {image_path}")
        print(f"  Output: {out}")

        # ── Step 1: Segmentation ─────────────────────────────
        print(f"\n  Step 1: Garment Segmentation")
        seg = self.segmentor.segment(image_path)

        if not seg.is_valid:
            print(f"    ❌ Failed: {seg.message}")
            return result

        print(f"    ✓ Method: {seg.method}  Area: {seg.area_percent:.1f}%")

        garment_path = out / "base_garment.png"
        Image.fromarray(seg.rgba_image).save(str(garment_path))
        result.base_garment_path = str(garment_path)
        print(f"    ✓ Saved: base_garment.png")

        # ── Step 2: Colour Extraction ────────────────────────
        print(f"\n  Step 2: Base Colour Extraction")
        colour = self.colour_extractor.extract(seg.rgba_image)

        if colour.success:
            result.base_color_hex = colour.base_colour_hex
            print(f"    ✓ Base colour: {colour.base_colour_hex}")

            colors_data = {
                "base_colour_hex": colour.base_colour_hex,
                "palette": [c.to_dict() for c in colour.palette],
            }
            colors_path = out / "colors.json"
            with open(colors_path, "w") as f:
                json.dump(colors_data, f, indent=2)
            result.colors_json_path = str(colors_path)
        else:
            print(f"    ❌ Failed: {colour.message}")

        # ── Step 3: Graphic Extraction ───────────────────────
        print(f"\n  Step 3: Graphic Extraction")
        design = self.design_extractor.extract(seg.rgba_image)

        if design.has_design and design.graphic_image is not None:
            graphic_path = out / "graphic_diffuse.png"
            Image.fromarray(design.graphic_image).save(str(graphic_path))
            result.graphic_diffuse_map = str(graphic_path)
            print(f"    ✓ {design.message}")
            print(f"    ✓ Saved: graphic_diffuse.png")
        else:
            print(f"    ℹ️  {design.message}")
            # Save empty transparent
            h, w = seg.rgba_image.shape[:2]
            empty = np.zeros((h, w, 4), dtype=np.uint8)
            graphic_path = out / "graphic_diffuse.png"
            Image.fromarray(empty).save(str(graphic_path))
            result.graphic_diffuse_map = str(graphic_path)

        # ── Save pipeline result ─────────────────────────────
        vision_result = {
            "base_garment": result.base_garment_path,
            "graphic_diffuse": result.graphic_diffuse_map,
            "base_color_hex": result.base_color_hex,
            "segmentation": {
                "method": seg.method,
                "area_percent": round(seg.area_percent, 2),
            },
            "colour": {
                "success": colour.success,
                "hex": colour.base_colour_hex if colour.success else None,
                "palette_size": len(colour.palette) if colour.success else 0,
            },
            "design": {
                "has_design": design.has_design,
                "coverage_percent": round(design.design_coverage_percent, 2),
                "message": design.message,
            },
        }
        result_path = out / "vision_result.json"
        with open(result_path, "w") as f:
            json.dump(vision_result, f, indent=2)
        result.result_json_path = str(result_path)

        result.success = True
        print(f"\n  ✅ Vision pipeline complete")
        return result


# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Vision Pipeline — single-image appearance extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python vision_pipeline.py output/routed/front_img.png -o output/vision_001
  python vision_pipeline.py my_tshirt.jpg -o output/vision_002
        """,
    )
    parser.add_argument("image", help="Path to garment image")
    parser.add_argument("-o", "--output", default="output/vision_001", help="Output directory")

    args = parser.parse_args()

    pipeline = VisionPipeline()
    result = pipeline.run_full_vision_track(args.image, args.output)

    if result.success:
        print(f"\nBase colour: {result.base_color_hex}")
        print(f"Graphic:     {result.graphic_diffuse_map}")
    else:
        print("\n❌ Pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
