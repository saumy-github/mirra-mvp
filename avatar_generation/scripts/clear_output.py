#!/usr/bin/env python3
"""Clear all generated files from the avatar_generation/output directory."""

import shutil
import sys
from pathlib import Path


def clear_output_folder():
    """Remove all generated run folders from the output directory."""
    step_dir = Path(__file__).resolve().parents[1]
    output_dir = step_dir / 'output'

    if not output_dir.exists():
        print(f"Directory does not exist: {output_dir}")
        return 0

    entries = [entry for entry in output_dir.iterdir() if entry.name != '.gitkeep']

    if not entries:
        print("Output folder is already empty")
        return 0

    print(f"\nFound {len(entries)} entries in output folder:")
    for entry in sorted(entries):
        if entry.is_dir():
            print(f"  - {entry.name}/")
        else:
            size_kb = entry.stat().st_size / 1024
            print(f"  - {entry.name} ({size_kb:.1f} KB)")

    print(f"\nThis will delete all generated Step 1 outputs from:")
    print(f"  {output_dir}")
    response = input("\nProceed? [y/N]: ").strip().lower()

    if response not in ['y', 'yes']:
        print("Cancelled")
        return 1

    deleted_count = 0
    for entry in entries:
        try:
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
            deleted_count += 1
        except Exception as error:
            print(f"Error deleting {entry.name}: {error}")

    print(f"\nDeleted {deleted_count} entries from output folder")
    return 0


if __name__ == "__main__":
    sys.exit(clear_output_folder())
