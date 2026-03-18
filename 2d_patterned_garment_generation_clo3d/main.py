"""
main.py — Full CLO3D Garment Pipeline
=======================================

Runs both pipelines in sequence:

  STAGE A  →  T-Shirt Appearance Extraction
               (segmentation → view selection → colour → graphic)

  STAGE B  →  2D Pattern Generation
               (measurements → DXF/SVG pattern pieces)

All outputs are saved into a single combined run folder so everything
needed for CLO3D is in one place.

Usage:
  # Default: prompts for garment ID from DB
  python main.py input_images/

  # Specify garment ID directly
  python main.py input_images/ --garment-id 003

  # Manual measurements
  python main.py input_images/ --manual --height 178 --chest 100 --shoulder 45
"""

import sys
import json
import time
import shutil
import argparse
from pathlib import Path
from datetime import datetime

# Ensure this folder is importable
_HERE = Path(__file__).parent.resolve()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from tshirt_extractor import TShirtExtractor, run_view_selection
from generate_patterns_clo3d import (
    AvatarMeasurements,
    GarmentMeasurements,
    DynamicPatternGenerator,
    HAS_DB,
)

# Optionally import DB helpers for interactive garment listing
try:
    from mirra_measurements.db import get_garments_collection
    _HAS_GARMENTS_DB = HAS_DB
except (ImportError, AttributeError, FileNotFoundError):
    _HAS_GARMENTS_DB = False


# ─────────────────────────────────────────────────────────────
#  Combined output directory
# ─────────────────────────────────────────────────────────────

def get_next_pipeline_dir(base_dir: str, prefix: str = "pipeline_run_") -> Path:
    """
    Create the next auto-numbered pipeline folder:
      pipeline_run_001, pipeline_run_002, …
    """
    base = Path(base_dir).resolve()
    base.mkdir(parents=True, exist_ok=True)

    existing_nums = []
    for d in base.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            suffix = d.name[len(prefix):]
            if suffix.isdigit():
                if any(d.iterdir()):          # skip empty dirs from failed runs
                    existing_nums.append(int(suffix))

    next_num = (max(existing_nums) + 1) if existing_nums else 1
    run_dir = base / f"{prefix}{next_num:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


# ─────────────────────────────────────────────────────────────
#  Interactive garment selection
# ─────────────────────────────────────────────────────────────

def prompt_garment_id() -> str:
    """
    List all garments in the DB and let the user pick one interactively.
    Returns the chosen garment_id string.
    """
    col = get_garments_collection()
    all_garments = list(col.find({}, {"_id": 0}).sort("garment_id", 1))

    if not all_garments:
        raise RuntimeError(
            "The garments collection is empty. Seed it first:\n"
            "  python -m mirra_measurements.seed_garments"
        )

    print(f"\n  Available garments in DB:\n")
    print(f"  {'ID':<6} {'Fit Type':<12} {'Half Chest':>11} {'Length':>8} {'Shoulder':>10} {'Sleeve':>8}")
    print("  " + "─" * 62)
    for g in all_garments:
        print(
            f"    {g['garment_id']:<4} "
            f"{g['fit_type']:<12} "
            f"{g['half_chest_width_cm']:>9.1f}cm "
            f"{g['garment_length_cm']:>6.1f}cm "
            f"{g['shoulder_width_cm']:>8.1f}cm "
            f"{g['sleeve_length_cm']:>6.1f}cm"
        )
    print()

    garment_id = input("  Enter garment_id to use: ").strip()
    if not garment_id:
        raise ValueError("No garment_id entered.")
    return garment_id


# ─────────────────────────────────────────────────────────────
#  Main orchestrator
# ─────────────────────────────────────────────────────────────

def run_full_pipeline(args):
    t_start = time.time()

    # ── Resolve combined output directory ────────────────────
    output_base = Path(args.output).resolve()
    run_dir = get_next_pipeline_dir(str(output_base))

    appearance_dir = run_dir / "appearance"
    appearance_dir.mkdir(exist_ok=True)

    patterns_dir = run_dir / "patterns"
    patterns_dir.mkdir(exist_ok=True)

    print("\n" + "█" * 60)
    print("  FULL CLO3D GARMENT PIPELINE")
    print("█" * 60)
    print(f"  Input images : {args.input_folder}")
    print(f"  Output       : {run_dir}")
    print(f"  Timestamp    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # ═════════════════════════════════════════════════════════
    #  STAGE A — Appearance Extraction
    # ═════════════════════════════════════════════════════════
    print("▓" * 60)
    print("  STAGE A: T-SHIRT APPEARANCE EXTRACTION")
    print("▓" * 60)

    extractor = TShirtExtractor()

    # If --skip-clip, disable CLIP routing
    if args.skip_clip:
        import tshirt_extractor
        tshirt_extractor.run_view_selection = lambda d: []
        print("  ℹ️  CLIP view selection skipped (--skip-clip)\n")

    extraction_result = extractor.run(
        input_folder=args.input_folder,
        output_base=str(appearance_dir),
    )

    # The extractor creates ext001/ inside appearance/ — find it
    ext_dirs = sorted(appearance_dir.iterdir())
    ext_dir = ext_dirs[0] if ext_dirs else appearance_dir

    stage_a_ok = (
        extraction_result.segmentation is not None
        and extraction_result.segmentation.is_valid
    )

    if not stage_a_ok:
        print("\n  ❌ Stage A failed — cannot produce base garment")
        print("     Pattern generation will still run if measurements are provided.\n")

    # ═════════════════════════════════════════════════════════
    #  STAGE B — Pattern Generation
    # ═════════════════════════════════════════════════════════
    print("\n" + "▓" * 60)
    print("  STAGE B: 2D PATTERN GENERATION")
    print("▓" * 60)

    garment = None
    garment_source = ""

    # ── Input mode routing ───────────────────────────────────
    # Priority: --garment-id  >  --avatar  >  --manual  >  interactive DB prompt
    if args.garment_id:
        # Mode 1: explicit garment ID from CLI
        garment_source = f"garments DB (id={args.garment_id})"
        try:
            garment = GarmentMeasurements.from_garments_db(args.garment_id)
            print(f"\n  ✓ Loaded from garments DB: {args.garment_id}")
        except Exception as e:
            print(f"\n  ❌ DB load failed: {e}")

    elif args.avatar:
        # Mode 2: from avatar JSON
        garment_source = f"avatar JSON ({args.avatar})"
        try:
            avatar = AvatarMeasurements.from_json(args.avatar)
            garment = GarmentMeasurements.from_avatar(avatar, fit_type=args.fit)
            print(f"\n  ✓ Loaded from avatar JSON: {avatar.user_id}")
        except Exception as e:
            print(f"\n  ❌ Avatar JSON load failed: {e}")

    elif args.manual:
        # Mode 3: explicit manual measurements
        garment_source = "manual measurements"
        avatar = AvatarMeasurements(
            height_cm=args.height,
            chest_circumference_cm=args.chest,
            waist_circumference_cm=args.waist,
            hip_circumference_cm=args.hip,
            shoulder_width_cm=args.shoulder,
            gender=args.gender,
            user_id="manual_input",
        )
        garment = GarmentMeasurements.from_avatar(avatar, fit_type=args.fit)
        print(f"\n  ✓ Using manual measurements")
        print(f"    Height={args.height}cm  Chest={args.chest}cm  "
              f"Shoulder={args.shoulder}cm  Fit={args.fit}")

    else:
        # Mode 4 (DEFAULT): interactive — list garments from DB and prompt
        if _HAS_GARMENTS_DB:
            print(f"\n  🗄️  Loading from garments collection …")
            try:
                garment_id = prompt_garment_id()
                garment = GarmentMeasurements.from_garments_db(garment_id)
                garment_source = f"garments DB (id={garment_id})"
                print(f"\n  ✓ Loaded from garments DB: {garment_id}")
            except (RuntimeError, ValueError) as e:
                print(f"\n  ❌ {e}")
            except Exception as e:
                print(f"\n  ❌ DB error: {e}")
        else:
            # DB not available — fall back to manual with defaults
            print(f"\n  ℹ️  Database not available — using default manual measurements")
            print(f"      (install pymongo + python-dotenv to enable DB mode,")
            print(f"       or pass --manual / --garment-id / --avatar)")
            garment_source = "manual measurements (default)"
            avatar = AvatarMeasurements(
                height_cm=args.height,
                chest_circumference_cm=args.chest,
                waist_circumference_cm=args.waist,
                hip_circumference_cm=args.hip,
                shoulder_width_cm=args.shoulder,
                gender=args.gender,
                user_id="manual_input",
            )
            garment = GarmentMeasurements.from_avatar(avatar, fit_type=args.fit)
            print(f"      Height={args.height}cm  Chest={args.chest}cm  "
                  f"Shoulder={args.shoulder}cm  Fit={args.fit}")

    stage_b_ok = False
    pattern_run_dir = None

    if garment is not None:
        print(f"\n  Garment dimensions:")
        print(f"    Half chest : {garment.half_chest_width:.1f} cm")
        print(f"    Length     : {garment.garment_length:.1f} cm")
        print(f"    Shoulder   : {garment.shoulder_width:.1f} cm")
        print(f"    Sleeve     : {garment.sleeve_length:.1f} cm")
        print(f"    Fit type   : {garment.fit_type}")
        print()

        generator = DynamicPatternGenerator(garment)
        generator.generate_all(str(patterns_dir))

        pattern_run_dir = generator.last_run_path
        stage_b_ok = True

        # Try to save to DB (non-fatal if unavailable)
        try:
            generator.save_to_db(garment_id=pattern_run_dir.name)
        except Exception:
            pass
    else:
        print("\n  ❌ No measurements available — skipping pattern generation")
        print("     Provide --height/--chest/--shoulder or --garment-id or --avatar")

    # ═════════════════════════════════════════════════════════
    #  COMBINED SUMMARY
    # ═════════════════════════════════════════════════════════
    elapsed = time.time() - t_start

    # Save combined pipeline metadata
    combined_meta = {
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": round(elapsed, 2),
        "pipeline_version": "1.0",
        "stage_a": {
            "status": "success" if stage_a_ok else "failed",
            "output_dir": str(ext_dir),
            "base_garment": extraction_result.base_garment_path or None,
            "graphic_diffuse": extraction_result.graphic_diffuse_path or None,
            "base_colour_hex": (
                extraction_result.colour.base_colour_hex
                if extraction_result.colour and extraction_result.colour.success
                else None
            ),
            "colors_json": extraction_result.colors_json_path or None,
        },
        "stage_b": {
            "status": "success" if stage_b_ok else "skipped",
            "source": garment_source,
            "output_dir": str(pattern_run_dir) if pattern_run_dir else None,
            "fit_type": garment.fit_type if garment else None,
        },
        "clo3d_integration": {
            "patterns_dxf": str(pattern_run_dir / "patterns_dxf") if pattern_run_dir else None,
            "base_colour": (
                extraction_result.colour.base_colour_hex
                if extraction_result.colour and extraction_result.colour.success
                else None
            ),
            "graphic_texture": extraction_result.graphic_diffuse_path or None,
        },
    }
    meta_path = run_dir / "pipeline_result.json"
    with open(meta_path, "w") as f:
        json.dump(combined_meta, f, indent=2)

    # ── Print summary ────────────────────────────────────────
    print("\n" + "█" * 60)
    print("  ✅  FULL PIPELINE COMPLETE")
    print("█" * 60)

    print(f"\n  📂 Output directory: {run_dir}")
    print(f"  ⏱  Total time: {elapsed:.1f}s")

    print(f"\n  STAGE A — Appearance Extraction: {'✅ SUCCESS' if stage_a_ok else '❌ FAILED'}")
    if stage_a_ok:
        hex_code = extraction_result.colour.base_colour_hex if extraction_result.colour else "N/A"
        print(f"    • base_garment.png     → {ext_dir / 'base_garment.png'}")
        print(f"    • graphic_diffuse.png  → {ext_dir / 'graphic_diffuse.png'}")
        print(f"    • colors.json          → {ext_dir / 'colors.json'}")
        print(f"    • Base colour          → {hex_code}")

    print(f"\n  STAGE B — Pattern Generation:    {'✅ SUCCESS' if stage_b_ok else '⏭ SKIPPED'}")
    if stage_b_ok:
        print(f"    • DXF patterns         → {pattern_run_dir / 'patterns_dxf'}")
        print(f"    • SVG previews         → {pattern_run_dir / 'patterns_svg'}")
        print(f"    • Metadata             → {pattern_run_dir / 'pattern_metadata.json'}")

    print(f"\n  📋 Pipeline result       → {meta_path}")

    print(f"\n  🎯 CLO3D Next Steps:")
    print(f"    1. Open CLO3D")
    print(f"    2. Import avatar  → Avatar > Import Avatar")
    if stage_b_ok:
        print(f"    3. Import patterns → File > Import > DXF/AAMA")
        print(f"       Select all .dxf files from: {pattern_run_dir / 'patterns_dxf'}")
    if stage_a_ok:
        hex_code = extraction_result.colour.base_colour_hex if extraction_result.colour else "N/A"
        print(f"    4. Apply base colour ({hex_code}) → Fabric Colour")
        print(f"    5. Apply graphic_diffuse.png → Diffuse Texture Map")
    print(f"    6. Sew seams → Simulate → Done! 🎉")
    print()

    return 0 if (stage_a_ok or stage_b_ok) else 1


# ─────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Full CLO3D Garment Pipeline — Appearance + Patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Runs the T-shirt appearance extraction and 2D pattern generation
pipelines in sequence. All outputs are saved into a single combined
run folder.

By default, the script will list all garments in the database and
prompt you to choose one for pattern generation.

Examples:
  # Default: interactive garment selection from DB
  python main.py input_images/

  # Specify garment ID directly (skips interactive prompt)
  python main.py input_images/ --garment-id 003

  # Manual measurements instead of DB
  python main.py input_images/ --manual --height 178 --chest 100 --shoulder 45

  # From avatar JSON
  python main.py input_images/ --avatar measurements.json

  # Skip CLIP (faster, uses first image)
  python main.py input_images/ --skip-clip

Output:
  output/pipeline_run_001/
  ├── appearance/ext001/
  │   ├── base_garment.png
  │   ├── graphic_diffuse.png
  │   ├── colors.json
  │   └── extraction_metadata.json
  ├── patterns/run_001/
  │   ├── patterns_dxf/
  │   ├── patterns_svg/
  │   └── pattern_metadata.json
  └── pipeline_result.json
        """,
    )

    # ── Required: input images folder ────────────────────────
    parser.add_argument(
        "input_folder",
        help="Directory with 1–10 T-shirt images (jpg, png, etc.)",
    )

    # ── Output ───────────────────────────────────────────────
    parser.add_argument(
        "-o", "--output",
        default=str(_HERE / "output"),
        help="Base output directory (default: output/ in module folder)",
    )

    # ── Appearance options ───────────────────────────────────
    parser.add_argument(
        "--skip-clip", action="store_true",
        help="Skip CLIP view selection (faster — uses first image)",
    )

    # ── Pattern source (choose one) ─────────────────────────
    source_group = parser.add_argument_group(
        "Pattern measurements",
        "Choose a source for body/garment measurements. "
        "Default: interactive garment selection from DB."
    )
    source_group.add_argument(
        "--garment-id", type=str, default=None,
        help="Load garment from DB by ID (e.g. 003) — skips interactive prompt",
    )
    source_group.add_argument(
        "--avatar", type=str, default=None,
        help="Path to avatar measurements JSON file",
    )
    source_group.add_argument(
        "--manual", action="store_true",
        help="Use manual body measurements (specify with --height/--chest/etc.)",
    )

    # ── Manual measurements ──────────────────────────────────
    manual_group = parser.add_argument_group("Manual body measurements (only used with --manual)")
    manual_group.add_argument("--height",   type=float, default=175.0, help="Body height cm (default: 175)")
    manual_group.add_argument("--chest",    type=float, default=100.0, help="Chest circumference cm (default: 100)")
    manual_group.add_argument("--waist",    type=float, default=85.0,  help="Waist circumference cm (default: 85)")
    manual_group.add_argument("--hip",      type=float, default=98.0,  help="Hip circumference cm (default: 98)")
    manual_group.add_argument("--shoulder", type=float, default=45.0,  help="Shoulder width cm (default: 45)")
    manual_group.add_argument("--gender",   type=str,   default="male", choices=["male", "female"])
    manual_group.add_argument(
        "--fit", type=str, default="regular",
        choices=["slim", "regular", "relaxed"],
        help="Fit type (default: regular)",
    )

    args = parser.parse_args()
    exit_code = run_full_pipeline(args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
