"""
MIRRA Pattern Importer - CLO3D Python Plugin

This plugin automates pattern import and basic setup in CLO3D.
Works within CLO3D's Python Script Editor (doesn't require external API).

USAGE:
1. Open CLO3D
2. Main Menu → Edit → Python Script
3. Load this file or drag & drop into CLO3D
4. Configure avatar_path and pattern_path variables
5. Run script

REQUIREMENTS:
- CLO3D (any version with Python scripting)
- DXF pattern files
- OBJ avatar file

NOTE: This uses CLO's internal Python API (different from REST API).
Check CLO documentation for available API functions.
"""

import CLO
import os
from pathlib import Path

# =============================================================================
# CONFIGURATION
# =============================================================================

# Paths
REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "clo_workspace"
AVATAR_PATH = WORKSPACE / "user_m_001_patterns" / "user_m_001_001_avatar.obj"

# Dynamically resolve the latest generated run folder under output/
_PATTERNS_BASE = REPO_ROOT / "2d_patterned_garment_generation_clo3d" / "output"


def _get_latest_patterns_dir() -> Path:
    """Returns patterns_dxf dir from the most recent run folder under output/."""
    if not _PATTERNS_BASE.exists():
        return _PATTERNS_BASE / "patterns_dxf"
    runs = sorted(
        [d for d in _PATTERNS_BASE.iterdir() if d.is_dir() and d.name.startswith("run_")],
        key=lambda d: int(d.name.split("_")[1]) if len(d.name.split("_")) > 1 and d.name.split("_")[1].isdigit() else 0
    )
    return (runs[-1] / "patterns_dxf") if runs else (_PATTERNS_BASE / "patterns_dxf")


PATTERN_DIR = _get_latest_patterns_dir()

# Pattern files
PATTERN_FILES = [
    "front_panel.dxf",
    "back_panel.dxf", 
    "sleeve_left.dxf",
    "sleeve_right.dxf"
]

# Fabric settings
FABRIC_TYPE = "Cotton Medium"  # CLO fabric preset
FABRIC_COLOR = (255, 255, 255)  # White (R, G, B)

# Seam configuration (which patterns to sew together)
SEAM_PAIRS = [
    # (pattern1_name, edge1, pattern2_name, edge2)
    ("front_panel", "shoulder_left", "back_panel", "shoulder_left"),
    ("front_panel", "shoulder_right", "back_panel", "shoulder_right"),
    ("front_panel", "side_left", "back_panel", "side_left"),
    ("front_panel", "side_right", "back_panel", "side_right"),
    ("sleeve_left", "cap", "body", "armhole_left"),
    ("sleeve_right", "cap", "body", "armhole_right"),
    ("sleeve_left", "underarm", "sleeve_left", "underarm"),  # Close sleeve
    ("sleeve_right", "underarm", "sleeve_right", "underarm"),  # Close sleeve
]

# =============================================================================
# MAIN AUTOMATION SCRIPT
# =============================================================================

def log(message):
    """Print log message."""
    print(f"[MIRRA] {message}")


def create_new_project():
    """Create a new CLO project."""
    try:
        CLO.NewProject()
        log("✓ New project created")
        return True
    except Exception as e:
        log(f"✗ Failed to create project: {e}")
        return False


def import_avatar(avatar_path):
    """Import OBJ avatar into CLO."""
    try:
        if not os.path.exists(avatar_path):
            log(f"✗ Avatar file not found: {avatar_path}")
            return False
        
        # CLO API function for importing avatar (check CLO docs for exact function)
        # This is a placeholder - actual function may differ
        CLO.ImportAvatar(str(avatar_path))
        log(f"✓ Avatar imported: {avatar_path.name}")
        return True
    except Exception as e:
        log(f"✗ Failed to import avatar: {e}")
        log(f"  Check CLO Python API documentation for correct import function")
        return False


def import_pattern(dxf_path, pattern_name):
    """Import DXF pattern file."""
    try:
        if not os.path.exists(dxf_path):
            log(f"✗ Pattern file not found: {dxf_path}")
            return False
        
        # CLO API function for importing pattern (check CLO docs)
        # This is a placeholder - actual function may differ
        CLO.ImportPattern(str(dxf_path))
        log(f"✓ Pattern imported: {pattern_name}")
        return True
    except Exception as e:
        log(f"✗ Failed to import pattern {pattern_name}: {e}")
        return False


def apply_fabric(pattern_name, fabric_type, color):
    """Apply fabric properties to pattern."""
    try:
        # Get pattern piece by name
        pattern = CLO.GetPatternByName(pattern_name)
        
        if pattern is None:
            log(f"⚠ Pattern not found: {pattern_name}")
            return False
        
        # Apply fabric preset
        fabric = CLO.GetFabricPreset(fabric_type)
        pattern.SetFabric(fabric)
        
        # Apply color
        pattern.SetColor(color[0], color[1], color[2])
        
        log(f"✓ Fabric applied to {pattern_name}")
        return True
    except Exception as e:
        log(f"✗ Failed to apply fabric to {pattern_name}: {e}")
        return False


def create_seam(pattern1, edge1, pattern2, edge2):
    """Create seam between two pattern edges."""
    try:
        # Get pattern pieces
        p1 = CLO.GetPatternByName(pattern1)
        p2 = CLO.GetPatternByName(pattern2)
        
        if p1 is None or p2 is None:
            log(f"⚠ Pattern not found for seam: {pattern1} or {pattern2}")
            return False
        
        # Create seam (check CLO docs for exact function)
        CLO.CreateSeam(p1, edge1, p2, edge2)
        log(f"✓ Seam created: {pattern1}.{edge1} ↔ {pattern2}.{edge2}")
        return True
    except Exception as e:
        log(f"✗ Failed to create seam: {e}")
        return False


def run_simulation(quality="high", frames=120):
    """Run cloth simulation."""
    try:
        log(f"Running simulation ({quality} quality, {frames} frames)...")
        
        # Set simulation parameters
        CLO.SetSimulationQuality(quality)
        CLO.SetSimulationFrames(frames)
        
        # Run simulation
        CLO.RunSimulation()
        
        log("✓ Simulation complete")
        return True
    except Exception as e:
        log(f"✗ Simulation failed: {e}")
        return False


def export_result(output_path, format="glb"):
    """Export final garment."""
    try:
        # Export garment (check CLO docs for export function)
        CLO.Export(str(output_path), format=format)
        log(f"✓ Exported to: {output_path}")
        return True
    except Exception as e:
        log(f"✗ Export failed: {e}")
        return False


def main():
    """Main automation workflow."""
    log("=" * 60)
    log("MIRRA Pattern Automation Plugin")
    log("=" * 60)
    
    # Step 1: Create new project
    log("\n[Step 1] Creating new project...")
    if not create_new_project():
        log("✗ Automation failed at project creation")
        return
    
    # Step 2: Import avatar
    log("\n[Step 2] Importing avatar...")
    if not import_avatar(AVATAR_PATH):
        log("⚠ Avatar import failed - continuing without avatar")
    
    # Step 3: Import patterns
    log("\n[Step 3] Importing patterns...")
    imported_count = 0
    for pattern_file in PATTERN_FILES:
        pattern_path = PATTERN_DIR / pattern_file
        pattern_name = pattern_file.replace(".dxf", "")
        if import_pattern(pattern_path, pattern_name):
            imported_count += 1
    
    log(f"  Imported {imported_count}/{len(PATTERN_FILES)} patterns")
    
    if imported_count == 0:
        log("✗ No patterns imported - stopping")
        return
    
    # Step 4: Apply fabric properties
    log("\n[Step 4] Applying fabric properties...")
    for pattern_file in PATTERN_FILES:
        pattern_name = pattern_file.replace(".dxf", "")
        apply_fabric(pattern_name, FABRIC_TYPE, FABRIC_COLOR)
    
    # Step 5: Create seams
    log("\n[Step 5] Creating seams...")
    seam_count = 0
    for p1, e1, p2, e2 in SEAM_PAIRS:
        if create_seam(p1, e1, p2, e2):
            seam_count += 1
    
    log(f"  Created {seam_count}/{len(SEAM_PAIRS)} seams")
    
    # Step 6: Run simulation
    log("\n[Step 6] Running simulation...")
    run_simulation(quality="high", frames=120)
    
    # Step 7: Export result
    log("\n[Step 7] Exporting result...")
    output_path = WORKSPACE / "exports" / "mirra_tshirt_output.glb"
    export_result(output_path, format="glb")
    
    log("\n" + "=" * 60)
    log("✓ Automation complete!")
    log("=" * 60)
    log(f"\nOutput saved to: {output_path}")


# =============================================================================
# MANUAL TESTING FUNCTIONS
# =============================================================================

def test_import_single_pattern():
    """Test importing a single pattern (for debugging)."""
    log("Testing single pattern import...")
    pattern_path = PATTERN_DIR / "front_panel.dxf"
    import_pattern(pattern_path, "front_panel")


def test_list_available_fabrics():
    """List available fabric presets in CLO."""
    try:
        fabrics = CLO.GetFabricPresets()
        log("Available fabrics:")
        for fabric in fabrics:
            log(f"  - {fabric}")
    except Exception as e:
        log(f"✗ Could not list fabrics: {e}")


def test_api_functions():
    """Test which CLO API functions are available."""
    log("Available CLO API functions:")
    for attr in dir(CLO):
        if not attr.startswith("_"):
            log(f"  - CLO.{attr}")


# =============================================================================
# RUN SCRIPT
# =============================================================================

if __name__ == "__main__":
    # Run main automation
    main()
    
    # Uncomment for testing individual functions:
    # test_api_functions()
    # test_list_available_fabrics()
    # test_import_single_pattern()
