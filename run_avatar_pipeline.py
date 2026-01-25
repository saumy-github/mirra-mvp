#!/usr/bin/env python3
"""Interactive CLI wrapper for avatar generation pipeline."""

import sys
import os
import subprocess
from typing import Optional

# Add workspace root to path for imports
workspace_root = os.path.dirname(os.path.abspath(__file__))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)


def get_next_run_number(user_id: str) -> int:
    """Auto-detect next available run number for a user by scanning generated folder."""
    generated_dir = os.path.join(workspace_root, 'pipeline_star', 'generated')
    
    if not os.path.exists(generated_dir):
        return 1
    
    max_number = 0
    prefix = f"inputs-{user_id}-"
    
    for filename in os.listdir(generated_dir):
        if filename.startswith(prefix) and filename.endswith('.json'):
            try:
                # Extract number from "inputs-user_m_001-003.json"
                number_str = filename[len(prefix):-5]  # Remove prefix and .json
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
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False


def main():
    """Interactive CLI entry point."""
    print("\n🎯 Avatar Generation Pipeline")
    print("━" * 50)
    
    try:
        # Get user_id
        user_id = input("\nEnter user_id: ").strip()
        
        if not user_id:
            print("❌ Error: user_id cannot be empty")
            return 1
        
        # Validate user exists
        print(f"Checking database for {user_id}...")
        if not validate_user_exists(user_id):
            print(f"❌ Error: No measurements found for user_id: {user_id}")
            return 1
        
        print(f"✓ Found user in database")
        
        # Get next run number
        next_number = get_next_run_number(user_id)
        print(f"\nNext available run number: {next_number:03d}")
        
        # Ask for confirmation
        response = input(f"Use run number {next_number:03d}? [Y/n]: ").strip().lower()
        
        if response and response not in ['y', 'yes']:
            custom_number = input("Enter custom run number: ").strip()
            try:
                next_number = int(custom_number)
                if next_number < 1:
                    print("❌ Error: Run number must be positive")
                    return 1
            except ValueError:
                print("❌ Error: Invalid run number")
                return 1
        
        # Run the pipeline
        print(f"\n🚀 Starting avatar generation for {user_id}-{next_number:03d}...")
        print("━" * 50)
        
        cmd = [
            sys.executable,
            os.path.join(workspace_root, 'pipeline_star', 'first.py'),
            '--user_id', user_id,
            '--mode', 'generate_avatar',
            '--run_number', str(next_number)
        ]
        
        result = subprocess.run(cmd)
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Pipeline cancelled by user")
        return 130
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
