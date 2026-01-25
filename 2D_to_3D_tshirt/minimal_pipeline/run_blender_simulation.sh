#!/bin/bash
# ============================================================
# Run Blender Sewing Simulation
# ============================================================
#
# This script launches Blender with the sewing pipeline.
#
# PREREQUISITES:
# - Blender 3.0+ installed
# - On macOS: Blender is in /Applications
#
# USAGE:
#   Interactive mode (opens Blender UI):
#     ./run_blender_simulation.sh
#
#   Automated bake mode (no UI, exports files):
#     ./run_blender_simulation.sh --bake
#
# ============================================================

# Parse arguments
AUTO_BAKE=false
BACKGROUND=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --bake|--auto)
            AUTO_BAKE=true
            BACKGROUND=true
            shift
            ;;
        --background|-b)
            BACKGROUND=true
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Find Blender executable
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    BLENDER="blender"
else
    # Windows (Git Bash)
    BLENDER="blender"
fi

# Check if Blender exists
if ! command -v "$BLENDER" &> /dev/null && [ ! -f "$BLENDER" ]; then
    echo "❌ Blender not found!"
    echo ""
    echo "Please install Blender from: https://www.blender.org/download/"
    echo ""
    echo "Or specify the path manually:"
    echo "  BLENDER=/path/to/blender ./run_blender_simulation.sh"
    exit 1
fi

echo "=============================================="
echo "  Blender Sewing Simulation"
echo "=============================================="
echo ""

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$AUTO_BAKE" = true ]; then
    echo "MODE: Automated Bake + Export"
    echo ""
    echo "This will:"
    echo "  1. Set up cloth simulation with sewing springs"
    echo "  2. Create anatomical avatar with collision"
    echo "  3. Bake 150 frames (may take several minutes)"
    echo "  4. Export OBJ, FBX, GLB files"
    echo ""
    echo "Starting Blender in background..."
    echo ""
    
    # Run in background with auto-bake
    export MIRRA_AUTO_BAKE=true
    export MIRRA_AUTO_EXPORT=true
    "$BLENDER" -b --python "${SCRIPT_DIR}/step5_blender_sewing.py"
    
    echo ""
    echo "=============================================="
    echo "  Simulation Complete!"
    echo "=============================================="
    echo ""
    echo "Output files in: ${SCRIPT_DIR}/pattern_output/exports/"
    echo "  - TShirt_Garment_Static.obj"
    echo "  - TShirt_Garment_Static.fbx"
    echo "  - TShirt_Garment_Static.glb"
    echo ""
else
    echo "MODE: Interactive"
    echo ""
    echo "AFTER BLENDER OPENS:"
    echo "  1. Press SPACEBAR to run simulation"
    echo "  2. Watch sewing springs pull seams together!"
    echo "  3. Observe cloth draping over avatar"
    echo "  4. Save your result with File > Save As"
    echo ""
    echo "For automated baking, run:"
    echo "  ./run_blender_simulation.sh --bake"
    echo ""
    echo "Starting Blender..."
    echo ""
    
    # Run with UI
    "$BLENDER" --python "${SCRIPT_DIR}/step5_blender_sewing.py"
fi
