"""
COMPLETE PIPELINE DIAGNOSTIC
============================
Checks all stages of the 2D to 3D T-shirt pipeline
Run this BEFORE starting the Blender simulation

This will verify:
1. Input images exist and are valid
2. Segmentation outputs are present
3. Design extraction worked
4. Color extraction succeeded  
5. Pattern SVGs were generated
6. Pattern metadata is correct
7. Blender simulation prerequisites
"""

import cv2
import numpy as np
from pathlib import Path
import json
import os

print("=" * 80)
print("COMPLETE PIPELINE DIAGNOSTIC - 2D TO 3D T-SHIRT")
print("=" * 80)

# ============================================
# STEP 1: CHECK INPUT IMAGES
# ============================================
print("\n" + "=" * 80)
print("STEP 1: INPUT IMAGES CHECK")
print("=" * 80)

input_dir = Path("input_images")
front_path = input_dir / "front.png"
back_path = input_dir / "back.png"

if not input_dir.exists():
    print(f"❌ FATAL: Input directory missing: {input_dir}")
else:
    print(f"✓ Input directory exists: {input_dir}")
    
    if not front_path.exists():
        print(f"❌ CRITICAL: Front image missing: {front_path}")
    else:
        img = cv2.imread(str(front_path))
        if img is None:
            print(f"❌ ERROR: Cannot read front image")
        else:
            h, w = img.shape[:2]
            print(f"✓ Front image OK: {w}x{h} pixels")
            print(f"  File size: {front_path.stat().st_size / 1024:.1f} KB")
    
    if back_path.exists():
        img = cv2.imread(str(back_path))
        if img is None:
            print(f"⚠ Back image exists but cannot be read")
        else:
            h, w = img.shape[:2]
            print(f"✓ Back image OK: {w}x{h} pixels")
    else:
        print(f"⚠ Back image not found (optional)")

# ============================================
# STEP 2: CHECK SEGMENTATION OUTPUT
# ============================================
print("\n" + "=" * 80)
print("STEP 2: SEGMENTATION OUTPUT CHECK")
print("=" * 80)

seg_dir = Path("segmentation_output")

if not seg_dir.exists():
    print(f"❌ FATAL: Segmentation not run - {seg_dir} missing")
    print("   Run: step1_segmentation.py first")
else:
    print(f"✓ Segmentation directory exists")
    
    # Check front mask
    front_mask_path = seg_dir / "front_mask.png"
    if not front_mask_path.exists():
        print(f"❌ Front mask missing: {front_mask_path}")
    else:
        mask = cv2.imread(str(front_mask_path), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            print(f"❌ Cannot read front mask")
        else:
            white_pixels = np.sum(mask == 255)
            total_pixels = mask.shape[0] * mask.shape[1]
            percentage = (white_pixels / total_pixels) * 100
            print(f"✓ Front mask OK")
            print(f"  Garment coverage: {percentage:.1f}%")
            
            if percentage < 10:
                print(f"  ⚠ WARNING: Very low garment coverage!")
            elif percentage > 80:
                print(f"  ⚠ WARNING: Very high coverage - segmentation may have failed")
    
    # Check front masked
    front_masked_path = seg_dir / "front_masked.png"
    if not front_masked_path.exists():
        print(f"⚠ Front masked image missing: {front_masked_path}")
    else:
        print(f"✓ Front masked image exists")

# ============================================
# STEP 3: CHECK DESIGN EXTRACTION
# ============================================
print("\n" + "=" * 80)
print("STEP 3: DESIGN EXTRACTION CHECK")
print("=" * 80)

design_dir = Path("design_output")

if not design_dir.exists():
    print(f"❌ Design extraction not run - {design_dir} missing")
    print("   Run: step2_design_extraction.py")
else:
    print(f"✓ Design directory exists")
    
    # Check front design
    front_design_path = design_dir / "front_design_mask.png"
    if not front_design_path.exists():
        print(f"⚠ Front design mask missing: {front_design_path}")
    else:
        design = cv2.imread(str(front_design_path), cv2.IMREAD_GRAYSCALE)
        if design is None:
            print(f"❌ Cannot read design mask")
        else:
            white_pixels = np.sum(design == 255)
            total_pixels = design.shape[0] * design.shape[1]
            percentage = (white_pixels / total_pixels) * 100
            print(f"✓ Front design mask OK")
            print(f"  Design coverage: {percentage:.1f}%")
            
            if percentage < 1:
                print(f"  ⚠ No design detected (plain garment)")
            elif percentage > 50:
                print(f"  ⚠ Very large design area - check accuracy")

# ============================================
# STEP 4: CHECK COLOR EXTRACTION
# ============================================
print("\n" + "=" * 80)
print("STEP 4: COLOR EXTRACTION CHECK")
print("=" * 80)

color_dir = Path("color_output")

if not color_dir.exists():
    print(f"❌ Color extraction not run - {color_dir} missing")
    print("   Run: step3_color_extraction.py")
else:
    print(f"✓ Color directory exists")
    
    # Check metadata
    metadata_path = color_dir / "color_metadata.json"
    if not metadata_path.exists():
        print(f"⚠ Color metadata missing: {metadata_path}")
    else:
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            fabric_color = metadata.get("fabric_color", {})
            print(f"✓ Color metadata loaded")
            print(f"  Fabric RGB: {fabric_color.get('rgb')}")
            print(f"  Fabric HEX: {fabric_color.get('hex')}")
            
            # Check if plausible
            rgb = fabric_color.get('rgb', [0, 0, 0])
            if rgb == [0, 0, 0]:
                print(f"  ⚠ Pure black - may be incorrect")
            elif rgb == [255, 255, 255]:
                print(f"  ⚠ Pure white - may be incorrect")
            else:
                print(f"  ✓ Plausible fabric color detected")
                
        except json.JSONDecodeError:
            print(f"❌ Cannot parse color metadata JSON")
        except Exception as e:
            print(f"❌ Error reading color metadata: {e}")

# ============================================
# STEP 5: CHECK PATTERN GENERATION
# ============================================
print("\n" + "=" * 80)
print("STEP 5: PATTERN GENERATION CHECK")
print("=" * 80)

pattern_dir = Path("pattern_output")

if not pattern_dir.exists():
    print(f"❌ FATAL: Pattern generation not run - {pattern_dir} missing")
    print("   Run: step4_pattern_generation.py")
else:
    print(f"✓ Pattern directory exists")
    
    # Check metadata
    metadata_path = pattern_dir / "pattern_metadata.json"
    if not metadata_path.exists():
        print(f"❌ CRITICAL: Pattern metadata missing!")
        print(f"   Blender needs this file: {metadata_path}")
    else:
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            measurements = metadata.get("measurements", {})
            print(f"✓ Pattern metadata loaded")
            print(f"\nMeasurements:")
            for key, value in measurements.items():
                print(f"  {key}: {value} cm")
            
            # Check if reasonable
            chest = measurements.get("chest_flat", 0)
            length = measurements.get("body_length", 0)
            
            if chest < 30 or chest > 100:
                print(f"  ⚠ Chest measurement seems unusual: {chest} cm")
            if length < 40 or length > 120:
                print(f"  ⚠ Length measurement seems unusual: {length} cm")
                
        except json.JSONDecodeError:
            print(f"❌ Cannot parse pattern metadata JSON")
        except Exception as e:
            print(f"❌ Error reading pattern metadata: {e}")
    
    # Check SVG files
    svg_files = list(pattern_dir.glob("*.svg"))
    if not svg_files:
        print(f"❌ CRITICAL: No SVG pattern files found!")
        print(f"   Expected: front_pattern.svg, back_pattern.svg, sleeve_pattern.svg")
    else:
        print(f"\n✓ Found {len(svg_files)} SVG pattern files:")
        for svg in svg_files:
            size_kb = svg.stat().st_size / 1024
            print(f"  - {svg.name} ({size_kb:.1f} KB)")
            
            # Check file size
            if size_kb < 1:
                print(f"    ⚠ Very small file - may be empty")
            elif size_kb > 500:
                print(f"    ⚠ Very large file - may have too much detail")
    
    # Check for seam definitions
    seam_path = pattern_dir / "seam_definitions.json"
    if seam_path.exists():
        print(f"\n✓ Seam definitions file exists")
        try:
            with open(seam_path, 'r') as f:
                seams = json.load(f)
            print(f"  Number of seams defined: {len(seams.get('seams', []))}")
        except:
            print(f"  ⚠ Cannot read seam definitions")
    else:
        print(f"\n⚠ Seam definitions missing (will use defaults in Blender)")

# ============================================
# STEP 6: BLENDER PREREQUISITES
# ============================================
print("\n" + "=" * 80)
print("STEP 6: BLENDER PREREQUISITES CHECK")
print("=" * 80)

# Check if Blender script exists
blender_script = Path("step5_blender_sewing.py")
if not blender_script.exists():
    print(f"❌ CRITICAL: Blender script missing: {blender_script}")
else:
    print(f"✓ Blender script exists")

# Check if diagnostic script exists
diagnostic_script = Path("blender_diagnostic.py")
if diagnostic_script.exists():
    print(f"✓ Diagnostic script available")
else:
    print(f"⚠ Diagnostic script missing (optional)")

# Check Blender installation
blender_path = Path(r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe")
if not blender_path.exists():
    print(f"⚠ Blender not found at: {blender_path}")
    print(f"  Please install Blender 5.0 or update path in scripts")
else:
    print(f"✓ Blender found: {blender_path}")

# ============================================
# FINAL SUMMARY
# ============================================
print("\n" + "=" * 80)
print("DIAGNOSTIC SUMMARY")
print("=" * 80)

issues = []

if not front_path.exists():
    issues.append("❌ CRITICAL: Front image missing")

if not seg_dir.exists():
    issues.append("❌ FATAL: Run step1_segmentation.py first")

if not pattern_dir.exists():
    issues.append("❌ FATAL: Run step4_pattern_generation.py first")
elif not (pattern_dir / "pattern_metadata.json").exists():
    issues.append("❌ CRITICAL: Pattern metadata missing")
elif not list(pattern_dir.glob("*.svg")):
    issues.append("❌ CRITICAL: No SVG pattern files")

if not blender_script.exists():
    issues.append("❌ CRITICAL: Blender script missing")

if issues:
    print("\n🚨 ISSUES FOUND:\n")
    for issue in issues:
        print(f"  {issue}")
    print("\n❌ CANNOT PROCEED TO BLENDER SIMULATION")
    print("   Fix the issues above first")
else:
    print("\n✅ ALL CHECKS PASSED")
    print("\n🚀 READY FOR BLENDER SIMULATION")
    print("\nNext steps:")
    print("  1. Run: run_complete_pipeline.bat")
    print("     OR")
    print("  2. Open Blender manually:")
    print("     blender --python step5_blender_sewing.py")
    print("\n  3. Press SPACEBAR in Blender to run simulation")
    print("\n  4. If simulation doesn't work:")
    print("     - Run blender_diagnostic.py in Blender console")
    print("     - Check for mesh faces, gravity, cloth modifier")

print("\n" + "=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)
