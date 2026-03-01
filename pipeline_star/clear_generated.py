#!/usr/bin/env python3
"""Clear all generated files from the pipeline_star/generated directory."""

import os
import sys
from pathlib import Path


def clear_generated_folder():
    """Remove all files from the generated directory."""
    script_dir = Path(__file__).parent
    generated_dir = script_dir / 'generated'
    
    if not generated_dir.exists():
        print(f"✓ Directory does not exist: {generated_dir}")
        return 0
    
    # Count files (excluding .gitkeep)
    files = [f for f in generated_dir.glob('*') if f.is_file() and f.name != '.gitkeep']
    file_count = len(files)
    
    if file_count == 0:
        print("✓ Generated folder is already empty")
        return 0
    
    # Show what will be deleted
    print(f"\n🗑️  Found {file_count} files in generated folder:")
    for file_path in sorted(files):
        size_kb = file_path.stat().st_size / 1024
        print(f"  - {file_path.name} ({size_kb:.1f} KB)")
    
    # Ask for confirmation
    print(f"\n⚠️  This will delete all {file_count} files from:")
    print(f"   {generated_dir}")
    response = input("\nProceed? [y/N]: ").strip().lower()
    
    if response not in ['y', 'yes']:
        print("❌ Cancelled")
        return 1
    
    # Delete files
    deleted_count = 0
    for file_path in files:
        try:
            file_path.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"❌ Error deleting {file_path.name}: {e}")
    
    print(f"\n✅ Deleted {deleted_count} files from generated folder")
    return 0


if __name__ == "__main__":
    sys.exit(clear_generated_folder())
