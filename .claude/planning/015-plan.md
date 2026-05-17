# Step 1 MVP - Pipeline Cleanup Technical Plan

**Date**: 2026-05-16  
**Status**: In Planning Phase  
**Scope**: Pipeline cleanup, error calculation, file consolidation

---

## Current Implementation Status

### ✅ Completed
- Successfully modified one avatar's body dimensions
- 11-step pipeline architecture implemented
- CLO REST API integration functional
- Measurement mapping to CLO properties established
- Avatar export capability (.avt format)

### ⚠️ Known Issues

#### 1. Error Calculation Not Working
- **Issue**: Measurement accuracy error is not being computed and displayed
- **Impact**: Cannot validate whether applied measurements match target values
- **Required Output**: Per-measurement error calculation: `|(target - applied) / target| × 100`
- **Priority**: High (blocker for validation)

#### 2. File Proliferation & Redundancy
- **Current State**: Pipeline generates many intermediate files with overlapping information
- **Problem**: Difficult to track artifacts, bloated output directories, redundant data
- **Solution Approach**: Consolidate into unified logging structure
- **Target**: 
  - Single comprehensive log file (captures all execution steps)
  - `.avt` file (final avatar model)
  - `.zprj` file (CLO project, may be removed later)
  - Optional: `.mea` or metadata file if needed

#### 3. CLO Internal File Naming Issue
- **Issue**: Files saved internally within CLO have different names than what we specify
- **Impact**: Cannot guarantee file naming consistency across runs
- **Status**: Known blocker - approach TBD in future discussion
- **Options to Explore**:
  - Overwrite mechanism (force rename/replace)
  - Ensure consistency through CLO API constraints
  - Accept current naming and map/track externally

---

## Immediate Work (Phase 1: Pipeline Cleanup)

### Goal
Clean and stabilize the pipeline before expanding to face customization.

### Tasks

#### 1. Implement Error Calculation
- Compute per-measurement accuracy
- Store in unified log file
- Make error visible in output summary
- Formula: `|(target_value - applied_value) / target_value| × 100`

#### 2. File Consolidation
- Design unified log structure (JSON format recommended)
- Include:
  - Run metadata (user_id, run_id, timestamp, status)
  - Each step execution (step_name, success, duration, errors)
  - Input measurements (target values)
  - Applied measurements (actual values sent to CLO)
  - Computed errors (per-measurement accuracy)
  - Final status and warnings
- Delete redundant intermediate artifacts
- Keep only:
  - Single unified log file
  - `.avt` avatar export
  - `.zprj` CLO project (for now)

#### 3. Address CLO File Naming
- Document current behavior
- Decide on strategy (to be discussed later)
- Implement chosen approach

### Success Criteria
- Error values are computed and visible in output
- File count reduced from current state
- Unified log contains complete execution trace
- Avatar successfully exported with consistent naming

---

---


## Technical Architecture

### Current Pipeline (11 Steps)
1. Health check → CLO availability
2. Run setup → Initialize run directory and metadata
3. Fetch measurements → From MongoDB or JSON
4. Resolve base avatar → Validate and load base avatar file
5. Normalize targets → Format measurements for CLO
6. Build payloads → Create CLO command payloads
7. Import base avatar → Load into CLO project
8. Apply measurements → Apply measurement morphing
9. Readback → Verify applied measurements from CLO
10. Compute error → Calculate accuracy (currently broken)
11. Save outputs → Export avatar and logs

### Output Structure (Current vs. Target)

**Current**:
- Multiple JSON artifacts per step
- Redundant information across files
- Difficult to parse and validate

**Target**:
- Single unified log.json
  - Run metadata
  - Step-by-step execution trace
  - Input/output measurements
  - Error calculations
  - Final status
- avatar.avt (exported avatar)
- project.zprj (CLO project, optional for deletion)

### CLO Integration Points
- REST API: http://localhost:50505
- Endpoints used: import-avatar-avt, import-avatar-measurements, set-avatar-properties, export-avatar-avt
- Apply modes: avt_patch (binary), avatar_properties (CLO API), csv (measurement bridge)

---

## Measurement Mapping Reference

### Male Measurements (v1)
| Field | Unit | CLO Target | Apply Routes |
|-------|------|-----------|---|
| height_cm | cm | Total Height | avt_patch, avatar_properties, csv |
| weight_kg | kg | Weight | csv |
| shoulder_width_cm | cm | Across Shoulder (Curvilinear) | avt_patch, avatar_properties, csv |
| chest_circumference_cm | cm | Chest | avt_patch, avatar_properties, csv |
| waist_circumference_cm | cm | Waist | avt_patch, avatar_properties, csv |
| hip_circumference_cm | cm | Low Hip | avt_patch, avatar_properties, csv |
| leg_length_cm | cm | Inseam | avt_patch, avatar_properties, csv |

### Female Measurements (Deferred to Post-MVP)
- Bust, Under-Bust, Waist, Hip, Shoulder, Height, Weight, Leg Length
- Separate base avatar to be sourced

---

## File Structure After Cleanup

```
output/
  {user_id}/
    run_{number}/
      input.json                    (human-readable input)
      log.json                      (unified execution log)
      avatar.avt                    (exported avatar)
      project.zprj                  (CLO project - may be deleted later)
```

---

## Success Criteria

- [ ] Error calculation implemented and visible
- [ ] File count reduced to 4 essential artifacts
- [ ] Unified log contains complete execution trace
- [ ] Avatar exports successfully with correct dimensions

---

## Known Blockers & Risks

1. **CLO File Naming** (Blocker)
   - Files saved by CLO internally have different names
   - Impact: May affect file traceability and consistency
   - Resolution: TBD in detailed discussion

2. **Error Calculation** (High Priority)
   - Currently not computing accuracy
   - Needed to validate measurement correctness
   - May reveal underlying measurement mapping issues

3. **Measurement Value Precision** (TBD)
   - Not yet confirmed if current measurement values are optimal for CLO
   - May require iterative refinement based on error analysis
   - Focus: Get one avatar right before scaling

---

## Next Steps

1. **Immediate**: Fix error calculation in Step 10
2. **Short-term**: Consolidate output files into unified log
3. **Medium-term**: Address CLO file naming issue
4. **Validation**: Test with single avatar to ensure pipeline is stable

---

*Last updated: 2026-05-16*
