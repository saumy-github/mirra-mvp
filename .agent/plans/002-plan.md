# Plan 002 - MVP Step-2: 2D to 3D Clothing Asset Pipeline Implementation

## Overview

This plan implements the complete 2D to 3D clothing asset pipeline for t-shirts as defined in MVP-Step-2B. The existing codebase in `2D_to_3D_tshirt/minimal_pipeline` already has a 6-step pipeline that extracts design, color, and generates patterns from images. This plan focuses on refining, debugging, and completing the implementation to match MVP-Step-2B requirements.

**Scope**: T-shirts only, manually provided images and metadata, size-aware 3D asset generation with realistic fit behavior.

## Phases

### Phase 1 - Pipeline Audit & Documentation

**Goal**: Understand what's already implemented and identify gaps against MVP-Step-2B requirements.

**Steps**:

1. Document the current 6-step pipeline functionality in detail
2. Compare existing implementation against MVP-Step-2B document requirements
3. Identify what's working, what's broken, and what's missing
4. Create a gap analysis document
5. Review output file formats and data structures

### Phase 2 - Fix Critical Bugs

**Goal**: Resolve blocking issues preventing the pipeline from completing successfully.

**Steps**:

1. Fix the seam matching problem between Step 4 (pattern generation) and Step 5 (Blender sewing)
2. Ensure pattern piece names in SVG files match the names expected in seams.json
3. Verify cloth simulation completes without errors
4. Test Step 6 (texture application) and fix any issues
5. Ensure the complete pipeline runs end-to-end without manual intervention

### Phase 3 - Size-Aware Asset Generation

**Goal**: Implement the ability to generate multiple size variants (XS, S, M, L, XL) from a single t-shirt image.

**Steps**:

1. Create a size measurements database/configuration file with standard sizes
2. Modify Step 4 (pattern generation) to accept size as a parameter
3. Implement size-specific geometry generation (not just uniform scaling)
4. Add size metadata to output 3D assets
5. Test pipeline with all 5 sizes and verify distinct geometries

### Phase 4 - Rigid Sizing & Fit Assessment

**Goal**: Ensure garments maintain their actual size and provide fit feedback when placed on digital twins.

**Steps**:

1. Review and adjust Blender cloth simulation settings to prevent auto-fitting
2. Add constraints to maintain garment dimensions during simulation
3. Implement fit assessment logic (compare garment vs digital twin measurements)
4. Generate fit messages (too small, too large, good fit)
5. Add visual indicators for fit issues in the 3D asset

### Phase 5 - Asset Package & Storage

**Goal**: Create complete, reusable 3D asset packages and define storage structure.

**Steps**:

1. Define the complete asset package format (geometry, textures, metadata, physics config)
2. Implement asset metadata generation (JSON format as per MVP-Step-2B)
3. Create a standardized directory structure for storing assets
4. Add asset export functionality (save .blend, .obj/.fbx, textures)
5. Implement asset naming convention and version tracking

### Phase 6 - Integration & Testing

**Goal**: Ensure the pipeline produces assets ready for Step 3 (Virtual Try-On).

**Steps**:

1. Test complete pipeline with 10-20 sample t-shirt images
2. Validate asset quality (color fidelity, design accuracy, size correctness)
3. Verify assets can be loaded and placed on digital twins from Step 1
4. Document the asset ingestion workflow
5. Create user-facing documentation for manual image input process

## Dependencies

### Required

- Python virtual environment with all dependencies installed
- Blender 5.0+ installed and accessible
- Input t-shirt images (front view minimum, back optional)
- Size measurement specifications

### From Step 1

- digital twin body measurements (for fit assessment)
- digital twin 3D models (for cloth simulation testing)

## Expected Outcomes

### Deliverables

1. **Working end-to-end pipeline** that converts 2D t-shirt images to complete 3D assets
2. **Size-aware assets** with 5 size variants (XS, S, M, L, XL)
3. **Realistic fit behavior** (no auto-stretch/compression)
4. **Complete asset packages** including:
   - 3D geometry files
   - Color and design textures
   - Physics configuration
   - Metadata (size, measurements, fit profile)
5. **Asset storage structure** ready for virtual inventory

### Success Criteria

- ✅ Pipeline runs without errors for all 5 sizes
- ✅ Generated assets maintain visual fidelity (color, design from source images)
- ✅ Each size has distinct geometry (not just scaled)
- ✅ Garments maintain rigid sizing during simulation
- ✅ Fit assessment generates accurate messages
- ✅ Assets are stored in organized, reusable format
- ✅ 10-20 sample t-shirts successfully processed

## Manual Verification Checklist

After execution, verify:

1. **Pipeline Execution**:
   - [ ] Run complete pipeline on a sample t-shirt image
   - [ ] Verify no errors in Steps 1-6
   - [ ] Check all output directories have expected files

2. **Visual Quality**:
   - [ ] Open generated 3D asset in Blender
   - [ ] Verify fabric color matches source image
   - [ ] Verify design/print is correctly applied
   - [ ] Check for mesh quality (no holes, proper topology)

3. **Size Variants**:
   - [ ] Generate assets for all 5 sizes from same image
   - [ ] Load all 5 in Blender side-by-side
   - [ ] Visually confirm different dimensions (not uniform scaling)
   - [ ] Check metadata JSON files have correct measurements

4. **Fit Behavior**:
   - [ ] Place small size on large digital twin - should look tight
   - [ ] Place large size on small digital twin - should look loose
   - [ ] Verify no automatic stretching to fit body

5. **Asset Package**:
   - [ ] Verify all required files present (geometry, textures, metadata)
   - [ ] Check file naming follows convention
   - [ ] Confirm JSON metadata is valid and complete

6. **Documentation**:
   - [ ] Review generated documentation for clarity
   - [ ] Verify workflow instructions are accurate
   - [ ] Check that manual input process is documented
