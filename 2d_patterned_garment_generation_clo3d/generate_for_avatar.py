"""
Quick script to generate patterns for a specific avatar.
Automatically finds the latest avatar measurements and generates patterns.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from generate_patterns_clo3d import (
    AvatarMeasurements,
    GarmentMeasurements,
    DynamicPatternGenerator
)


def find_latest_avatar_measurements(avatar_dir: Path) -> Path:
    """Find the most recent avatar measurements JSON file."""
    json_files = list(avatar_dir.glob("*_measurements.json"))
    if not json_files:
        raise FileNotFoundError(f"No measurements JSON files found in {avatar_dir}")
    
    # Sort by modification time, return most recent
    json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return json_files[0]


def main():
    print("\n" + "="*60)
    print("GENERATE PATTERNS FOR AVATAR")
    print("="*60)
    
    # Paths
    project_root = Path(__file__).parent.parent
    avatar_dir = project_root / "pipeline_star" / "generated" / "clo_avatars"
    output_dir = Path(__file__).parent / "output"
    
    # Find latest avatar measurements
    try:
        measurements_file = find_latest_avatar_measurements(avatar_dir)
        print(f"\n📁 Found avatar measurements: {measurements_file.name}")
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print(f"\nPlease run the avatar generation pipeline first:")
        print(f"  python pipeline_star/run_avatar_pipeline.py")
        return
    
    # Load avatar measurements
    avatar = AvatarMeasurements.from_json(str(measurements_file))
    print(f"✓ Loaded avatar: {avatar.user_id}")
    print(f"  Height: {avatar.height_cm:.1f} cm")
    print(f"  Chest: {avatar.chest_circumference_cm:.1f} cm")
    print(f"  Shoulder: {avatar.shoulder_width_cm:.1f} cm")
    print(f"  Gender: {avatar.gender}")
    
    # Ask for fit preference
    print(f"\n👕 Select fit type:")
    print(f"  1. Slim fit (4cm ease)")
    print(f"  2. Regular fit (8cm ease) [default]")
    print(f"  3. Relaxed fit (12cm ease)")
    
    choice = input("\nEnter choice (1-3) or press Enter for default: ").strip()
    fit_map = {'1': 'slim', '2': 'regular', '3': 'relaxed', '': 'regular'}
    fit_type = fit_map.get(choice, 'regular')
    
    print(f"\n✓ Selected: {fit_type.upper()} fit")
    
    # Calculate garment measurements
    garment = GarmentMeasurements.from_avatar(avatar, fit_type=fit_type)
    
    # Generate patterns
    generator = DynamicPatternGenerator(garment)
    generator.generate_all(str(output_dir))
    
    print("\n" + "="*60)
    print("✅ PATTERNS READY FOR CLO3D")
    print("="*60)
    print(f"\nPattern files location:")
    print(f"  {generator.last_run_path / 'patterns_dxf'}")
    print(f"\nAvatar file location:")
    print(f"  {avatar_dir}")
    print(f"\nNext: Import both avatar and patterns into CLO3D!")
    print()


if __name__ == "__main__":
    main()
