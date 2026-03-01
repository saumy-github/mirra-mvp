# Plan 003: digital twin Shoulder Width Measurement Fix

## Overview

Fix the shoulder width measurement issue in digital twin generation by distinguishing between anatomical shoulder width (DB field) from the mesh-measured width (new field).

## Problem

**Current Issue**:

- Database stores: `shoulder_width_cm: 45.0` (anatomical: shoulder joint to shoulder joint)
- Pipeline calculates: `max_x - min_x` in horizontal band at 85% height
- This includes arms in A-pose, resulting in ~72.8 cm (61% error!)

**Root Cause**:

- The measurement method captures the widest X-range at shoulder height
- In A-pose, arms extend outward, inflating the measurement
- Both DB and pipeline define "full width" (not half), so it's not a half vs full issue

## Proposed Solution

### Use STAR Anatomical Landmarks

**Concept**:

- Keep `shoulder_width_cm` in DB as anatomical measurement (45.0 cm)
- Add new field: `shoulder_span_cm` or `arm_span_upper_cm` for actual mesh width
- Use STAR vertex indices for shoulder joint landmarks
- Calculate direct distance between left/right shoulder vertices

**Field Naming Options**:

1. Keep: `shoulder_width_cm` (anatomical) + Add: `upper_body_width_cm` (mesh measured)
2. Rename: `shoulder_width_anatomical_cm` vs `shoulder_width_pose_cm`
3. Keep: `shoulder_width_cm` (anatomical) + Add: `shoulder_span_mesh_cm`

## Phases

### Phase 1: Research STAR Landmarks

**Goal**: Understand STAR vertex topology and find shoulder joint indices

**Steps**:

1. Review STAR model documentation
2. Load STAR mesh and identify shoulder vertices
3. Visualize shoulder landmarks (left/right shoulder joints)
4. Document vertex indices

### Phase 2: Implement New Measurement

**Goal**: Create accurate shoulder width measurement using landmarks

**Steps**:

1. Create `extract_shoulder_landmarks()` function in `mesh_measure.py`
2. Use vertex indices to get left/right shoulder positions
3. Calculate Euclidean distance between shoulder points
4. Test on default mesh (should return ~45 cm for average male)

### Phase 3: Update Schema & Pipeline

**Goal**: Integrate new measurement into pipeline

**Steps**:

1. Add new field to `artifact_schema.py`
2. Update `mapping_layer.py` to handle both fields
3. Remove `shoulder_width_cm` from gated_fields in config
4. Update `fit_betas.py` to not optimize for shoulder_width
5. Document the change

### Phase 4: Verify & Update Documentation

**Goal**: Ensure fix works and document changes

**Steps**:

1. Re-generate user_m_001 digital twin
2. Verify shoulder measurement is accurate
3. Document in 003-flag.md if any limitations remain
4. Update any relevant docs

## Dependencies

- STAR model documentation/topology knowledge
- Blender or mesh viewer for visualizing vertices

## Expected Outcomes

- ✅ Accurate anatomical shoulder width measurement
- ✅ digital twin proportions match intended measurements
- ✅ Clear separation between anatomical vs pose-dependent measurements
- ✅ Reduced fitting errors (from 61% to <5%)

## Manual Verification Checklist

After implementation:

1. Generate new digital twin with shoulder_width_cm = 45.0
2. Measure actual shoulder width on generated mesh
3. Verify error is < 5%
4. Check that other measurements (chest, waist, hip) still fit correctly
5. Visualize digital twin proportions look realistic
