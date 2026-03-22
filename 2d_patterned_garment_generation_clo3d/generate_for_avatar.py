"""
Quick script to generate patterns for a specific avatar.

Two modes:
  1. DB mode (default): fetches the latest avatar measurements from MongoDB
     (same 'measurements' collection written by the avatar pipeline).
  2. File mode (--file): reads the most recent measurements.json from
     avatar_generation/output/<run_id>/ on disk.

Results are always saved to the garments collection in MongoDB
(when pymongo is available) in addition to the local DXF / SVG files.
"""
import sys
from pathlib import Path
from typing import Optional

# Ensure this folder is importable regardless of cwd
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
# Also add repo root so generate_patterns_clo3d can resolve sibling packages
_ROOT = _HERE.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from generate_patterns_clo3d import (
    AvatarMeasurements,
    GarmentMeasurements,
    DynamicPatternGenerator,
    HAS_DB,
)
from avatar_generation.run_manifest import get_latest_measurements_json_path


def find_latest_avatar_measurements(user_id: Optional[str] = None) -> Path:
    """Find the latest avatar measurements JSON file from Step 1 output."""
    return Path(get_latest_measurements_json_path(user_id))


def load_avatar_from_db(user_id: str = None) -> AvatarMeasurements:
    """
    Load avatar measurements from MongoDB.

    If user_id is given, fetch that specific document.
    If user_id is None, fetch the most recently created document
    (latest by 'created_at').

    Raises RuntimeError if DB is unavailable, ValueError if not found.
    """
    if not HAS_DB:
        raise RuntimeError(
            "pymongo is not installed. Cannot load from the database.\n"
            "Install it with: pip install pymongo python-dotenv\n"
            "Or run with --file to use a local JSON instead."
        )

    from mirra_measurements.db import get_avatar_collection
    collection = get_avatar_collection()

    if user_id:
        doc = collection.find_one({"user_id": user_id})
        if doc is None:
            raise ValueError(
                f"No measurements found for user_id='{user_id}' "
                f"in collection '{collection.name}'."
            )
    else:
        # Most recently inserted document
        doc = collection.find_one(sort=[("created_at", -1)])
        if doc is None:
            raise ValueError(
                f"The '{collection.name}' collection is empty. "
                "Run the avatar pipeline first or use --file."
            )

    return AvatarMeasurements(
        height_cm=doc.get("height_cm", 175.0),
        chest_circumference_cm=doc.get("chest_circumference_cm", 100.0),
        waist_circumference_cm=doc.get("waist_circumference_cm", 85.0),
        hip_circumference_cm=doc.get("hip_circumference_cm", 98.0),
        shoulder_width_cm=doc.get("shoulder_width_cm", 45.0),
        gender=doc.get("gender", "male"),
        user_id=doc.get("user_id", "unknown"),
    )


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate 2D garment patterns for an avatar and save to DB.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # DB mode — latest avatar in MongoDB (default):
  python generate_for_avatar.py

  # DB mode — specific user:
  python generate_for_avatar.py --user-id u_001

  # File mode — use local JSON instead of DB:
  python generate_for_avatar.py --file

  # Choose fit up-front without interactive prompt:
  python generate_for_avatar.py --user-id u_001 --fit slim
        """,
    )
    parser.add_argument(
        "--user-id", type=str, default=None,
        help="Load a specific avatar by user_id from MongoDB (DB mode only)"
    )
    parser.add_argument(
        "--file", action="store_true",
        help="Use the latest avatar_generation/output/<run_id>/measurements.json instead of MongoDB"
    )
    parser.add_argument(
        "--fit", type=str, choices=["slim", "regular", "relaxed"], default=None,
        help="Fit type (skips the interactive prompt when provided)"
    )
    args = parser.parse_args()

    print("\n" + "="*60)
    print("GENERATE PATTERNS FOR AVATAR")
    print("="*60)

    output_dir = Path(__file__).parent / "output"

    # ------------------------------------------------------------------
    # 1. Load avatar measurements
    # ------------------------------------------------------------------
    avatar = None

    if args.file:
        # --- File mode ---
        try:
            measurements_file = find_latest_avatar_measurements(args.user_id)
            print(f"\n📁 File mode — found: {measurements_file.name}")
            avatar = AvatarMeasurements.from_json(str(measurements_file))
        except FileNotFoundError as e:
            print(f"\n❌ Error: {e}")
            print("Please run the avatar generation pipeline first:")
            print("  python avatar_generation/run_avatar.py")
            return
    else:
        # --- DB mode (default) ---
        print(f"\n🗄️  DB mode — reading from 'measurements' collection in mirratest")
        try:
            avatar = load_avatar_from_db(user_id=args.user_id)
        except RuntimeError as e:
            # pymongo missing — fall back to file automatically
            print(f"\n⚠️  {e}")
            print("\nFalling back to file mode …")
            try:
                measurements_file = find_latest_avatar_measurements(args.user_id)
                print(f"📁 Found: {measurements_file.name}")
                avatar = AvatarMeasurements.from_json(str(measurements_file))
            except FileNotFoundError as e2:
                print(f"\n❌ Error: {e2}")
                return
        except ValueError as e:
            print(f"\n❌ Error: {e}")
            return

    print(f"✓ Loaded avatar : {avatar.user_id}  ({avatar.gender})")
    print(f"  Height         : {avatar.height_cm:.1f} cm")
    print(f"  Chest          : {avatar.chest_circumference_cm:.1f} cm")
    print(f"  Shoulder       : {avatar.shoulder_width_cm:.1f} cm")

    # ------------------------------------------------------------------
    # 2. Choose fit type
    # ------------------------------------------------------------------
    if args.fit:
        fit_type = args.fit
        print(f"\n👕 Fit type      : {fit_type.upper()} (from --fit flag)")
    else:
        print(f"\n👕 Select fit type:")
        print(f"  1. Slim fit    (4 cm ease)")
        print(f"  2. Regular fit (8 cm ease) [default]")
        print(f"  3. Relaxed fit (12 cm ease)")
        choice   = input("\nEnter choice (1-3) or press Enter for default: ").strip()
        fit_map  = {"1": "slim", "2": "regular", "3": "relaxed", "": "regular"}
        fit_type = fit_map.get(choice, "regular")
        print(f"\n✓ Selected: {fit_type.upper()} fit")

    # ------------------------------------------------------------------
    # 3. Calculate garment measurements & generate patterns
    # ------------------------------------------------------------------
    garment   = GarmentMeasurements.from_avatar(avatar, fit_type=fit_type)
    generator = DynamicPatternGenerator(garment)
    generator.generate_all(str(output_dir))

    # ------------------------------------------------------------------
    # 4. Save results to garments collection
    # ------------------------------------------------------------------
    print("\n💾 Saving garment record to database …")
    generator.save_to_db(
        garment_id=generator.last_run_path.name,   # e.g. "run_001"
    )

    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print("✅ PATTERNS READY FOR CLO3D")
    print("="*60)
    print(f"\nDXF pattern files  : {generator.last_run_path / 'patterns_dxf'}")
    print(f"SVG preview files  : {generator.last_run_path / 'patterns_svg'}")
    print(f"DB collection      : mirratest › garments")
    print(f"\nNext steps:")
    print(f"  1. Open CLO3D")
    print(f"  2. Import avatar  → Avatar › Import Avatar")
    print(f"  3. Import patterns → File › Import › DXF/AAMA (select all 4 .dxf files)")
    print(f"  4. Sew seams and simulate!")
    print()


if __name__ == "__main__":
    main()
