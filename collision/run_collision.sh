#!/bin/bash
#
# Run Garment Fitting & Collision Simulation
# ==========================================
# This script launches Blender to run the garment fitting pipeline.
#
# Requirements:
# - Blender 3.0+ installed
# - On macOS: Blender is in /Applications
#
# Usage:
#     ./run_collision.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║      Garment Fitting & Collision Simulation               ║"
echo "╚══════════════════════════════════════════════════════════╝"

# Find Blender executable
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    BLENDER="blender"
else
    # Windows or fallback
    BLENDER="blender"
fi

# Allow override via environment variable
if [ -n "${BLENDER_PATH}" ]; then
    BLENDER="${BLENDER_PATH}"
fi

# Check if Blender exists
if ! command -v "$BLENDER" &> /dev/null && [ ! -f "$BLENDER" ]; then
    echo "❌ Blender not found!"
    echo ""
    echo "Please install Blender from: https://www.blender.org/download/"
    echo ""
    echo "Or set the BLENDER_PATH environment variable:"
    echo "  BLENDER_PATH=/path/to/blender ./run_collision.sh"
    exit 1
fi

echo ""
echo "📁 Working directory: ${SCRIPT_DIR}"
echo "🔧 Using Blender: ${BLENDER}"
echo ""

# Check for input files
if [ ! -f "${SCRIPT_DIR}/input/garment.blend" ]; then
    echo "❌ Missing input file: input/garment.blend"
    exit 1
fi

if [ ! -f "${SCRIPT_DIR}/input/avatar.glb" ]; then
    echo "❌ Missing input file: input/avatar.glb"
    exit 1
fi

echo "✅ Input files found:"
echo "   - input/garment.blend"
echo "   - input/avatar.glb"
echo ""

echo "🚀 Starting Blender simulation..."
echo "   This may take a few minutes..."
echo ""

# Run Blender in background mode
"$BLENDER" -b --python "${SCRIPT_DIR}/run_collision.py"

echo ""
echo "✅ Simulation complete!"
echo "📦 Output: ${SCRIPT_DIR}/output/fitted_garment.glb"
