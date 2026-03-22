#!/usr/bin/env python3
"""Interactive CLI wrapper for avatar generation pipeline."""

import sys
import os
import subprocess

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


def validate_user_exists(user_id: str) -> bool:
    """Check if user exists in MongoDB."""
    try:
        from mirra_measurements.db import get_measurements_collection
        collection = get_measurements_collection()
        doc = collection.find_one({"user_id": user_id})
        return doc is not None
    except Exception as error:
        print(f"Error checking database: {error}")
        return False


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
        if not validate_user_exists(user_id):
            print(f"Error: No measurements found for user_id: {user_id}")
            return 1

        print("Found user in database")
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
