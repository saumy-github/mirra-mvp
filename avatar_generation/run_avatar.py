#!/usr/bin/env python3
"""Interactive CLI wrapper for avatar generation pipeline."""

import sys
import os
import subprocess
from typing import Any, Dict, Optional

# Add workspace root to path for imports
workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)


def get_next_run_number(user_id: str) -> int:
    """Auto-detect next available run number for a user by scanning output folders."""
    output_dir = os.path.join(os.path.dirname(__file__), 'output')

    if not os.path.exists(output_dir):
        return 1

    max_number = 0
    prefix = f"{user_id}-"

    for entry in os.listdir(output_dir):
        run_dir = os.path.join(output_dir, entry)
        if not os.path.isdir(run_dir) or not entry.startswith(prefix):
            continue
        try:
            _, number_str = entry.rsplit('-', 1)
            number = int(number_str)
            max_number = max(max_number, number)
        except ValueError:
            continue

    return max_number + 1


def get_user_doc(user_id: str) -> Optional[Dict[str, Any]]:
    """Return the measurement document for a user, if present."""
    try:
        from mirra_measurements.db import get_measurements_collection
        collection = get_measurements_collection()
        return collection.find_one({"user_id": user_id})
    except Exception as error:
        print(f"Error checking database: {error}")
        return None


def validate_star_setup(gender: str) -> bool:
    """Validate local STAR dependency and model files before launching pipeline."""
    star_repo_root = os.path.join(workspace_root, 'libs', 'star')
    star_package_dir = os.path.join(star_repo_root, 'star')

    if not os.path.isdir(star_repo_root) or not os.path.isdir(star_package_dir):
        print("Error: STAR library not found in libs/star")
        print("Run: git submodule update --init --recursive")
        print("Then: pip install -e libs/star")
        return False

    required_model = os.path.join(
        workspace_root,
        'models',
        'star_1_1',
        gender,
        'model.npz',
    )
    if not os.path.exists(required_model):
        print(f"Error: Missing STAR model file for gender '{gender}':")
        print(f"  {required_model}")
        print("Download STAR model files and place them under models/star_1_1/<gender>/model.npz")
        print("See setup docs: avatar_generation/SETUP.md")
        return False

    return True


def main():
    """Interactive CLI entry point."""
    print("\nAvatar Generation Pipeline")
    print("-" * 50)

    try:
        user_id = input("\nEnter user_id: ").strip()

        if not user_id:
            print("Error: user_id cannot be empty")
            return 1

        print(f"Checking database for {user_id}...")
        user_doc = get_user_doc(user_id)
        if not user_doc:
            print(f"Error: No measurements found for user_id: {user_id}")
            if user_id.startswith('s_'):
                print("Hint: avatar generation expects measurement user IDs like u_001, not size IDs like s_001.")
            return 1

        print("Found user in database")

        gender = str(user_doc.get('gender', '')).strip().lower()
        if gender not in ('male', 'female', 'neutral'):
            print(f"Error: Invalid or missing gender in user document: {gender!r}")
            return 1

        if not validate_star_setup(gender):
            return 1

        next_number = get_next_run_number(user_id)
        print(f"\nNext available run number: {next_number:03d}")

        response = input(f"Use run number {next_number:03d}? [Y/n]: ").strip().lower()

        if response and response not in ['y', 'yes']:
            custom_number = input("Enter custom run number: ").strip()
            try:
                next_number = int(custom_number)
                if next_number < 1:
                    print("Error: Run number must be positive")
                    return 1
            except ValueError:
                print("Error: Invalid run number")
                return 1

        pose = input("Select pose [tpose/apose] (default: tpose): ").strip().lower()
        if not pose:
            pose = 'tpose'
        if pose not in ['tpose', 'apose']:
            print("Error: Invalid pose. Use 'tpose' or 'apose'.")
            return 1

        print(f"\nStarting avatar generation for {user_id}-{next_number:03d} ({pose})...")
        print("-" * 50)

        cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), 'first.py'),
            '--user_id', user_id,
            '--mode', 'generate_avatar',
            '--run_number', str(next_number),
            '--pose', pose,
        ]

        result = subprocess.run(cmd)
        return result.returncode

    except KeyboardInterrupt:
        print("\n\nPipeline cancelled by user")
        return 130
    except Exception as error:
        print(f"\nUnexpected error: {error}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
