# Plan 001: digital twin Generation Pipeline - Interactive CLI & Bug Fixes

## Overview

Improve the existing digital twin generation pipeline to make it user-friendly with an interactive CLI, fix critical measurement bugs, and enhance error reporting. The pipeline already has working Phase 0-3 (validation, inputs/values creation, GLB export), but needs usability improvements and bug fixes.

## Current State

✅ **Working Components:**

- Phase 0: Golden user accounts defined (`mirra_measurements/golden_users.py`)
- Phase 1: MongoDB measurement validation (complete data requirements + range checks)
- Phase 2A: Inputs JSON creation (`pipeline_star/mapping_layer.py`)
- Phase 2B: Beta fitting with STAR (`pipeline_star/fit_betas.py`)
- Phase 2C: Values JSON creation with fit report and status
- Phase 3: GLB export (`pipeline_star/digital twin_exporter.py`)

❌ **Known Issues:**

- Shoulder width measurement has 61.7% error (see `001-probs.md`)
- CLI requires command-line arguments (not user-friendly)
- Failed runs lack visual feedback in terminal
- No auto-increment for run numbers

## Phases

### Phase 1: Create Interactive CLI Wrapper

**Goal**: Replace command-line argument workflow with an interactive user prompt

**Steps**:

1. Create `run_digital twin_pipeline.py` in project root that wraps `pipeline_star/first.py`
2. Implement interactive user_id input prompt with validation
3. Auto-detect next available run number by scanning `pipeline_star/generated/` folder
4. Display the next run number to user and ask for confirmation or custom number
5. Call `first.py` with the collected arguments in `generate_digital twin` mode
6. Handle keyboard interrupts gracefully

**Expected Behavior**:

```plain
$ python run_digital twin_pipeline.py

🎯 digital twin Generation Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Enter user_id: user_m_001
✓ Found user in database

Next available run number: 002
Use run number 002? [Y/n]: _
```

---

### Phase 2: Enhance Terminal Feedback for Failed Runs

**Goal**: Provide clear visual feedback when digital twin generation fails the 2% tolerance gate

**Steps**:

1. Modify `pipeline_star/first.py` in the `generate_digital twin` mode section
2. After status determination (line ~298), add conditional formatting
3. If status is "failed", print a red cross (❌) with a clear failure message
4. Display which measurements failed the tolerance gate with their error percentages
5. Remind user that GLB was still exported for debugging
6. If status is "passed", print a green checkmark (✅) with success message

**Expected Output (Failed)**:

```plain
❌ digital twin GENERATION FAILED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The following measurements exceeded 2% tolerance:
  • Shoulder Width: 61.71% error
  • Waist: 14.03% error
  • Chest: 7.53% error

GLB file exported for debugging: user_m_001-001.glb
Review the values JSON for detailed fit report.
```

**Expected Output (Passed)**:

```plain
✅ digital twin GENERATION SUCCESSFUL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
All measurements within 2% tolerance
Ready for Blender import: user_m_001-001.glb
```

---

### Phase 3: Investigate Shoulder Width Measurement Bug

**Goal**: Identify why shoulder width has 61.7% error and determine fix strategy

**Steps**:

1. Review `pipeline_star/mesh_measure.py` to understand how shoulder width is calculated
2. Check if shoulder measurement landmarks are correct for STAR mesh anatomy
3. Create a test script to visualize shoulder measurement points on the mesh
4. Compare the predicted shoulder width calculation vs MongoDB target
5. Document findings in `001-probs.md` under the existing shoulder width entry
6. Determine if this is a measurement logic bug or a STAR model limitation
7. If fixable, propose solution; if STAR limitation, document as known limitation in `001-flag.md`

**Note**: This is investigative work - the actual fix may be deferred based on findings.

---

---

## Manual Verification Checklist

**Important**: At the end of execution, you will verify these items manually. I will only list what you need to check. I will NOT verify automatically unless you specifically ask me to.

**Items to Verify**:

1. Run `python run_digital twin_pipeline.py` - confirm interactive prompt appears
2. Enter `user_m_001` - confirm it finds the user in database
3. Confirm auto-detected run number is correct (should be next available)
4. Let the pipeline complete - check terminal output for clear success/failure message
5. Check that 3 files were created in `pipeline_star/generated/`:
   - `inputs-user_m_001-00X.json`
   - `values-user_m_001-00X.json`
   - `user_m_001-00X.glb`
6. Open Blender and import the GLB file - verify it loads without errors
7. Visually inspect the digital twin mesh in Blender for basic correctness
8. Repeat test with `user_m_002`, `user_f_001`, `user_f_002` (optional extended test)

---

## Dependencies

- Existing pipeline code in `pipeline_star/first.py` must remain functional
- MongoDB connection (`mirra_measurements/db.py`) must be working
- STAR model and dependencies must be installed

## Expected Outcomes

When this plan is complete:

1. Users can run `python run_digital twin_pipeline.py` and be guided through digital twin generation
2. Failed runs show clear, color-coded error messages
3. Run numbers auto-increment without manual specification
4. Shoulder width bug is documented with investigation findings
5. All 4 golden users have been tested successfully
