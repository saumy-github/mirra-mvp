#!/bin/bash
# ============================================================
# T-SHIRT PIPELINE - Complete Runner
# ============================================================
#
# This script runs the entire T-shirt pipeline:
# Steps 1-4: Python (image processing + pattern generation)
# Steps 5-6: Blender (sewing simulation + texturing)
#
# USAGE:
#   ./run_pipeline.sh [front_image] [back_image]
#
# EXAMPLE:
#   ./run_pipeline.sh input_images/front.png input_images/back.png
#
# ============================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Python executable (from venv)
PYTHON="../.venv/bin/python"

# Blender executable
if [[ "$OSTYPE" == "darwin"* ]]; then
    BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
else
    BLENDER="blender"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║     T-SHIRT IMAGE TO 3D GARMENT PIPELINE                ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║  Step 1: Segment T-shirt from background                ║"
echo "║  Step 2: Extract printed design                         ║"
echo "║  Step 3: Extract fabric color                           ║"
echo "║  Step 4: Generate sewing patterns                       ║"
echo "║  Step 5: Sew panels in Blender                          ║"
echo "║  Step 6: Apply color and design                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check for input images
if [ -n "$1" ]; then
    echo "Using front image: $1"
    # Update the path in step1 script (simplified - in production use config file)
fi

# ============================================================
# PYTHON STEPS (1-4)
# ============================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 1: Segmentation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$PYTHON step1_segmentation.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 2: Design Extraction"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$PYTHON step2_design_extraction.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 3: Color Extraction"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$PYTHON step3_color_extraction.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEP 4: Pattern Generation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
$PYTHON step4_pattern_generation.py

# ============================================================
# BLENDER STEPS (5-6)
# ============================================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STEPS 5-6: Blender Simulation & Texturing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Launching Blender..."
echo "The simulation will run automatically."
echo ""

# Run Blender in background mode for automated processing
# Or interactive mode if you want to see the simulation
$BLENDER --python step5_blender_sewing.py --python step6_apply_texture.py

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║               PIPELINE COMPLETE! ✅                     ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
