"""
Canonical Step 2 runner for product ingestion.

This runner is cloth-folder driven and MongoDB-backed:
  - cloth images come from product_ingestion/input/<cloth_id>/
  - size and cloth metadata come from the sizes collection via size_id

Canonical output layout:
  product_ingestion/output/<cloth_id>-<size_id>-<run_number>/
    image_info/
      base_garment.png
      colors.json
      extraction_metadata.json
      graphic_diffuse.png
    panels/
      dxf/
      svg/
      panel_metadata.json
    run_summary.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

_HERE = Path(__file__).parent.resolve()
_ROOT = _HERE.parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mirra_measurements.db import get_sizes_collection  # noqa: E402
from generate_patterns_clo3d import GarmentMeasurements  # noqa: E402
from view_selection import list_cloth_images, select_primary_image  # noqa: E402
from segmentation import run_segmentation  # noqa: E402
from colour_extraction import extract_colours  # noqa: E402
from design_extraction import extract_design, make_empty_graphic_like  # noqa: E402
from panel_generation import generate_panels  # noqa: E402
from run_manifest import get_next_product_run_dir  # noqa: E402


def list_cloth_dirs(input_root: Path) -> list[Path]:
    """List cloth folders under the canonical input root."""
    if not input_root.exists():
        return []
    return sorted(path for path in input_root.iterdir() if path.is_dir() and path.name.startswith("c_"))


def load_size_doc(size_id: str) -> dict:
    """Load one size document from MongoDB."""
    collection = get_sizes_collection()
    doc = collection.find_one({"size_id": size_id}, {"_id": 0})
    if doc is None:
        raise ValueError(f"size_id '{size_id}' was not found in the sizes collection.")
    return doc


def list_size_docs_for_cloth(cloth_id: str) -> list[dict]:
    """List size documents for a specific cloth_id."""
    collection = get_sizes_collection()
    return list(collection.find({}, {"_id": 0}).sort("size_id", 1))


def prompt_for_cloth_id(input_root: Path) -> str:
    """Prompt the user to select a cloth_id from the available input folders."""
    cloth_dirs = list_cloth_dirs(input_root)
    if not cloth_dirs:
        raise RuntimeError(f"No cloth folders were found under {input_root}")

    print("\nAvailable cloth folders:")
    for cloth_dir in cloth_dirs:
        image_count = len(list_cloth_images(cloth_dir))
        print(f"  {cloth_dir.name:<8} images={image_count}")

    cloth_id = input("\nEnter cloth_id to ingest: ").strip()
    if not cloth_id:
        raise ValueError("No cloth_id entered.")
    return cloth_id


def prompt_for_size_doc(cloth_id: str) -> dict:
    """Prompt the user to select a size document for the chosen cloth."""
    size_docs = list_size_docs_for_cloth(cloth_id)
    if not size_docs:
        raise RuntimeError("The sizes collection is empty. Seed it first: python -m mirra_measurements.seed_sizes")

    print(f"\nAvailable sizes for {cloth_id}:")
    print(f"  {'size_id':<8} {'fit':<10} {'cloth_label':<20} {'half_chest':>11} {'length':>8}")
    print("  " + "-" * 68)
    for doc in size_docs:
        print(
            f"  {doc['size_id']:<8} "
            f"{doc.get('fit_type', 'n/a'):<10} "
            # f"{doc.get('cloth_label', 'n/a'):<20} "
            f"{doc['half_chest_width_cm']:>9.1f}cm "
            f"{doc['garment_length_cm']:>6.1f}cm"
        )

    size_id = input("\nEnter size_id to use: ").strip()
    if not size_id:
        raise ValueError("No size_id entered.")
    return load_size_doc(size_id)


def validate_cloth_and_size(cloth_id: str, cloth_dir: Path, size_doc: dict) -> None:
    """Ensure the selected cloth folder and size document agree."""
    if not cloth_dir.exists():
        raise FileNotFoundError(f"Cloth folder not found: {cloth_dir}")
    return


def write_colors_json(output_path: Path, colour_result) -> Path:
    """Write colors.json into image_info/."""
    payload = {
        "base_colour_hex": colour_result.base_colour_hex,
        "palette": [entry.to_dict() for entry in colour_result.palette],
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def write_extraction_metadata(
    output_path: Path,
    cloth_id: str,
    size_id: str,
    cloth_dir: Path,
    selection,
    segmentation_result,
    transparent_bg_ok: bool,
    colour_result,
    colour_hex_ok: bool,
    design_result,
    generated_files: dict,
) -> Path:
    """Write image_info/extraction_metadata.json."""
    payload = {
        "timestamp": datetime.now().isoformat(),
        "cloth_id": cloth_id,
        "size_id": size_id,
        "input_folder": str(cloth_dir),
        "view_selection": selection.to_dict(),
        "segmentation": {
            "valid": segmentation_result.is_valid,
            "method": segmentation_result.method,
            "area_percent": round(segmentation_result.area_percent, 2),
            "message": segmentation_result.message,
            "transparent_background_ok": transparent_bg_ok,
        },
        "colour": None,
        "design": None,
        "generated_files": generated_files,
    }

    if colour_result is not None:
        payload["colour"] = {
            "success": colour_result.success,
            "base_colour_hex": colour_result.base_colour_hex,
            "valid_hex": colour_hex_ok,
            "message": colour_result.message,
            "palette": [entry.to_dict() for entry in colour_result.palette],
        }

    if design_result is not None:
        payload["design"] = {
            "has_design": design_result.has_design,
            "coverage_percent": round(design_result.design_coverage_percent, 2),
            "message": design_result.message,
        }

    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def build_run_summary(
    run_dir: Path,
    cloth_dir: Path,
    size_doc: dict,
    selection,
    image_outputs: dict,
    panel_result,
    image_status: str,
) -> dict:
    """Build the canonical run_summary.json payload."""
    return {
        "timestamp": datetime.now().isoformat(),
        "run_id": run_dir.name,
        "cloth_id": cloth_dir.name,
        "size_id": size_doc["size_id"],
        "input_folder": str(cloth_dir),
        "selected_image": str(selection.selected_image),
        "selection_reason": selection.selection_reason,
        "size_doc": size_doc,
        "image_info": {
            "status": image_status,
            "directory": str(run_dir / "image_info"),
            **image_outputs,
        },
        "panels": {
            "status": "success",
            "directory": str(panel_result.panels_dir),
            "dxf_dir": str(panel_result.dxf_dir),
            "svg_dir": str(panel_result.svg_dir),
            "panel_metadata": str(panel_result.metadata_path),
            "panel_names": panel_result.panel_names,
        },
    }


def run_product_ingestion(args) -> int:
    """Execute the canonical product ingestion flow."""
    input_root = Path(args.input_root).resolve()
    output_root = Path(args.output).resolve()

    cloth_id = args.cloth_id or prompt_for_cloth_id(input_root)
    cloth_dir = input_root / cloth_id

    size_doc = load_size_doc(args.size_id) if args.size_id else prompt_for_size_doc(cloth_id)
    validate_cloth_and_size(cloth_id, cloth_dir, size_doc)

    size_id = size_doc["size_id"]
    run_dir = get_next_product_run_dir(cloth_id, size_id, output_root)
    image_info_dir = run_dir / "image_info"
    panels_dir = run_dir / "panels"
    image_info_dir.mkdir(parents=True, exist_ok=True)
    panels_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 72)
    print("PRODUCT INGESTION")
    print("=" * 72)
    print(f"Cloth folder : {cloth_dir}")
    print(f"Size ID      : {size_id}")
    print(f"Run folder   : {run_dir}")

    print("\n[1/5] View selection")
    selection = select_primary_image(cloth_dir, skip_clip=args.skip_clip)
    print(f"  Selected image : {selection.selected_image.name}")
    print(f"  Reason         : {selection.selection_reason}")

    print("\n[2/5] Segmentation")
    segmentation_result, transparent_bg_ok = run_segmentation(selection.selected_image)
    image_outputs = {
        "base_garment": None,
        "colors_json": None,
        "graphic_diffuse": None,
        "extraction_metadata": None,
    }
    colour_result = None
    colour_hex_ok = False
    design_result = None
    image_status = "failed"

    if segmentation_result.is_valid and segmentation_result.rgba_image is not None:
        base_garment_path = image_info_dir / "base_garment.png"
        Image.fromarray(segmentation_result.rgba_image).save(base_garment_path)
        image_outputs["base_garment"] = str(base_garment_path)
        print(f"  Wrote base garment : {base_garment_path.name}")

        print("\n[3/5] Colour extraction")
        colour_result, colour_hex_ok = extract_colours(segmentation_result.rgba_image)
        if colour_result.success:
            colors_json_path = write_colors_json(image_info_dir / "colors.json", colour_result)
            image_outputs["colors_json"] = str(colors_json_path)
            print(f"  Wrote colors json  : {colors_json_path.name}")
            print(f"  Base colour        : {colour_result.base_colour_hex}")
        else:
            print(f"  Colour extraction failed: {colour_result.message}")

        print("\n[4/5] Design extraction")
        design_result = extract_design(segmentation_result.rgba_image)
        graphic_path = image_info_dir / "graphic_diffuse.png"
        if design_result.has_design and design_result.graphic_image is not None:
            Image.fromarray(design_result.graphic_image).save(graphic_path)
            print(f"  Wrote diffuse map  : {graphic_path.name}")
        else:
            Image.fromarray(make_empty_graphic_like(segmentation_result.rgba_image)).save(graphic_path)
            print(f"  Wrote empty diffuse: {graphic_path.name}")
        image_outputs["graphic_diffuse"] = str(graphic_path)
        image_status = "success"
    else:
        print(f"  Segmentation failed: {segmentation_result.message}")

    extraction_metadata_path = write_extraction_metadata(
        image_info_dir / "extraction_metadata.json",
        cloth_id=cloth_id,
        size_id=size_id,
        cloth_dir=cloth_dir,
        selection=selection,
        segmentation_result=segmentation_result,
        transparent_bg_ok=transparent_bg_ok,
        colour_result=colour_result,
        colour_hex_ok=colour_hex_ok,
        design_result=design_result,
        generated_files=image_outputs,
    )
    image_outputs["extraction_metadata"] = str(extraction_metadata_path)

    print("\n[5/5] Panel generation")
    measurements = GarmentMeasurements.from_sizes_db(size_id)
    panel_result = generate_panels(measurements, panels_dir)

    run_summary = build_run_summary(
        run_dir=run_dir,
        cloth_dir=cloth_dir,
        size_doc=size_doc,
        selection=selection,
        image_outputs=image_outputs,
        panel_result=panel_result,
        image_status=image_status,
    )
    run_summary_path = run_dir / "run_summary.json"
    run_summary_path.write_text(json.dumps(run_summary, indent=2, default=str), encoding="utf-8")

    print("\n" + "=" * 72)
    print("PRODUCT INGESTION COMPLETE")
    print("=" * 72)
    print(f"Run summary : {run_summary_path}")
    print(f"Panels DXF  : {panel_result.dxf_dir}")
    print(f"Panels SVG  : {panel_result.svg_dir}")
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the canonical Step 2 runner."""
    parser = argparse.ArgumentParser(
        description="Canonical Step 2 runner for product ingestion.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_product_ingestion.py
  python run_product_ingestion.py --cloth-id c_001 --size-id s_001

Expected input:
  product_ingestion/input/
    c_001/
      image_1.jpg
      image_2.jpg
""",
    )
    parser.add_argument(
        "--cloth-id",
        type=str,
        default=None,
        help="Cloth folder ID under product_ingestion/input (for example: c_001).",
    )
    parser.add_argument(
        "--size-id",
        type=str,
        default=None,
        help="MongoDB size_id from the sizes collection (for example: s_001).",
    )
    parser.add_argument(
        "--input-root",
        default=str(_HERE / "input"),
        help="Input root containing cloth folders (default: product_ingestion/input).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(_HERE / "output"),
        help="Output root for canonical run folders (default: product_ingestion/output).",
    )
    parser.add_argument(
        "--skip-clip",
        action="store_true",
        help="Skip CLIP view selection and use the first image in the cloth folder.",
    )
    return parser


def main():
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        return run_product_ingestion(args)
    except KeyboardInterrupt:
        print("\n\nPipeline cancelled by user")
        return 130
    except Exception as err:
        print(f"\nUnexpected error: {err}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    import sys
    sys.exit(main())
