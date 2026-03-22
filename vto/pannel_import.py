"""
Pannel Importer - CLO3D Python Plugin

This script automates pattern import and basic setup in CLO3D. It's a
lightweight, in-CLO alternative to the REST-based orchestration. It exists
to provide a quick way to test imports and seams inside the CLO Python
editor when the REST plugin approach is not available.

Changes vs original:
- Renamed to `pannel_import.py` per request.
- Only applies fabric and creates seams for patterns that were successfully
  imported (prevents attempts to operate on missing pieces).
- Skips seam creation when a referenced pattern is not present.

USAGE: (inside CLO's Python Script Editor)
  - Configure `AVATAR_PATH` (optional) and `PATTERN_DIR` if needed
  - Run the script
"""

import CLO
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from avatar_generation.run_manifest import get_latest_avatar_obj_path
from product_ingestion.run_manifest import get_latest_panels_dxf_dir


# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
WORKSPACE = REPO_ROOT / "clo_workspace"
try:
    AVATAR_PATH = Path(get_latest_avatar_obj_path())
except FileNotFoundError:
    AVATAR_PATH = REPO_ROOT / "avatar_generation" / "output" / "u_001-001" / "avatar.obj"


def _get_latest_patterns_dir() -> Path:
    """Returns panels/dxf from the latest canonical product_ingestion run."""
    try:
        return Path(get_latest_panels_dxf_dir())
    except FileNotFoundError:
        return REPO_ROOT / "product_ingestion" / "output" / "panels" / "dxf"


PATTERN_DIR = _get_latest_patterns_dir()

# Pattern files (base filenames)
PATTERN_FILES = [
    "front_panel.dxf",
    "back_panel.dxf",
    "sleeve_left.dxf",
    "sleeve_right.dxf",
]

# Fabric settings
FABRIC_TYPE = "Cotton Medium"
FABRIC_COLOR = (255, 255, 255)

# Seam configuration (which patterns to sew together). Only seams where both
# pattern names were successfully imported will be attempted.
SEAM_PAIRS = [
    ("front_panel", "shoulder_left", "back_panel", "shoulder_left"),
    ("front_panel", "shoulder_right", "back_panel", "shoulder_right"),
    ("front_panel", "side_left", "back_panel", "side_left"),
    ("front_panel", "side_right", "back_panel", "side_right"),
    ("sleeve_left", "cap", "body", "armhole_left"),
    ("sleeve_right", "cap", "body", "armhole_right"),
]


# =============================================================================
# HELPERS
# =============================================================================

def log(message):
    print(f"[PANNEL] {message}")


def create_new_project():
    try:
        CLO.NewProject()
        log("✓ New project created")
        return True
    except Exception as e:
        log(f"✗ Failed to create project: {e}")
        return False


def import_avatar(avatar_path):
    try:
        if not os.path.exists(avatar_path):
            log(f"✗ Avatar file not found: {avatar_path}")
            return False

        CLO.ImportAvatar(str(avatar_path))
        log(f"✓ Avatar imported: {Path(avatar_path).name}")
        return True
    except Exception as e:
        log(f"✗ Failed to import avatar: {e}")
        return False


def import_pattern(dxf_path, pattern_name):
    try:
        if not os.path.exists(dxf_path):
            log(f"✗ Pattern file not found: {dxf_path}")
            return False

        CLO.ImportPattern(str(dxf_path))
        log(f"✓ Pattern imported: {pattern_name}")
        return True
    except Exception as e:
        log(f"✗ Failed to import pattern {pattern_name}: {e}")
        return False


def apply_fabric(pattern_name, fabric_type, color):
    try:
        pattern = CLO.GetPatternByName(pattern_name)
        if pattern is None:
            log(f"⚠ Pattern not found (skip fabric): {pattern_name}")
            return False

        fabric = CLO.GetFabricPreset(fabric_type)
        pattern.SetFabric(fabric)
        pattern.SetColor(color[0], color[1], color[2])
        log(f"✓ Fabric applied to {pattern_name}")
        return True
    except Exception as e:
        log(f"✗ Failed to apply fabric to {pattern_name}: {e}")
        return False


def create_seam(pattern1, edge1, pattern2, edge2):
    try:
        p1 = CLO.GetPatternByName(pattern1)
        p2 = CLO.GetPatternByName(pattern2)
        if p1 is None or p2 is None:
            log(f"⚠ Pattern not found for seam (skip): {pattern1} or {pattern2}")
            return False

        CLO.CreateSeam(p1, edge1, p2, edge2)
        log(f"✓ Seam created: {pattern1}.{edge1} ↔ {pattern2}.{edge2}")
        return True
    except Exception as e:
        log(f"✗ Failed to create seam: {e}")
        return False


def run_simulation(quality="high", frames=120):
    try:
        log(f"Running simulation ({quality} quality, {frames} frames)...")
        CLO.SetSimulationQuality(quality)
        CLO.SetSimulationFrames(frames)
        CLO.RunSimulation()
        log("✓ Simulation complete")
        return True
    except Exception as e:
        log(f"✗ Simulation failed: {e}")
        return False


def export_result(output_path, format="glb"):
    try:
        CLO.Export(str(output_path), format=format)
        log(f"✓ Exported to: {output_path}")
        return True
    except Exception as e:
        log(f"✗ Export failed: {e}")
        return False


# =============================================================================
# MAIN WORKFLOW
# =============================================================================

def main():
    log("=" * 60)
    log("Pannel Import Automation")
    log("=" * 60)

    log("\n[1] Creating new project...")
    if not create_new_project():
        log("✗ Automation failed at project creation")
        return

    log("\n[2] Importing avatar...")
    if not import_avatar(AVATAR_PATH):
        log("⚠ Avatar import failed - continuing without avatar")

    log("\n[3] Importing patterns...")
    imported = []
    for pattern_file in PATTERN_FILES:
        path = PATTERN_DIR / pattern_file
        name = Path(pattern_file).stem
        if import_pattern(path, name):
            imported.append(name)

    log(f"  Imported {len(imported)}/{len(PATTERN_FILES)} patterns")
    if not imported:
        log("✗ No patterns imported - stopping")
        return

    log("\n[4] Applying fabric properties to imported patterns...")
    for name in imported:
        apply_fabric(name, FABRIC_TYPE, FABRIC_COLOR)

    log("\n[5] Creating seams (only for imported patterns)...")
    seam_count = 0
    for p1, e1, p2, e2 in SEAM_PAIRS:
        if p1 in imported and p2 in imported:
            if create_seam(p1, e1, p2, e2):
                seam_count += 1
        else:
            log(f"  Skipping seam for missing pattern(s): {p1}, {p2}")

    log(f"  Created {seam_count}/{len(SEAM_PAIRS)} seams")

    log("\n[6] Running simulation...")
    run_simulation(quality="high", frames=120)

    log("\n[7] Exporting result...")
    output_path = WORKSPACE / "exports" / "pannel_output.glb"
    export_result(output_path, format="glb")

    log("\n" + "=" * 60)
    log("✓ Automation complete!")
    log("=" * 60)
    log(f"\nOutput saved to: {output_path}")


if __name__ == "__main__":
    main()
