"""
Quick test runner for segmentation.py only.

Usage:
    cd product_ingestion
    python test_segmentation.py --input <folder_with_images>

Output is saved to:
    product_ingestion/seg_test_output/<image_name>.png
"""

import argparse
import sys
from pathlib import Path

from PIL import Image

_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from segmentation import run_segmentation

SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    parser = argparse.ArgumentParser(description="Test segmentation on a folder of images.")
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Folder containing input images (e.g. input/c_001)",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(_HERE / "seg_test_output"),
        help="Folder to write RGBA PNGs into (default: seg_test_output/)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in SUPPORTED)
    if not images:
        print(f"No supported images found in: {input_dir}")
        sys.exit(1)

    print(f"Found {len(images)} image(s) in {input_dir}")
    print(f"Outputs → {output_dir}\n")

    for img_path in images:
        print(f"[{img_path.name}]")
        result, transparent_ok = run_segmentation(img_path)

        print(f"  method          : {result.method}")
        print(f"  valid           : {result.is_valid}")
        print(f"  area            : {result.area_percent:.1f}%")
        print(f"  transparent bg  : {transparent_ok}")
        print(f"  message         : {result.message}")

        if result.rgba_image is not None:
            out_path = output_dir / f"{img_path.stem}_seg.png"
            Image.fromarray(result.rgba_image).save(out_path)
            print(f"  saved           : {out_path.name}")
        print()


if __name__ == "__main__":
    main()
