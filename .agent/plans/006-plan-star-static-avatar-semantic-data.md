# Plan 006: STAR Static Avatar Semantic Data Path

## Overview

This plan keeps the current STAR-based avatar pipeline as the body-generation foundation and solves the CLO placement issue by adding static semantic data around the avatar instead of waiting for CLO to infer native arrangement slots from a raw imported mesh.

The key idea is:

1. Keep generating the user-specific STAR mesh.
2. Keep the avatar static for now.
3. Add enough body landmarks, anchor points, and body-region metadata so our own VTO pipeline can place front, back, and sleeve panels in a more informed way.
4. Treat CLO arrangement slots as optional, not mandatory.

This plan is intentionally incremental. We will add files one by one so we do not over-engineer the avatar before proving which data actually improves panel placement and simulation.

---

## Why This Plan Exists

The current issue is not that the avatar mesh cannot be imported into CLO. The issue is that the imported STAR OBJ is treated like a mesh avatar with weak or missing semantic arrangement support, so the pipeline falls back to generic offsets.

From the current repo state:

1. `avatar_generation/` already creates a user-specific STAR mesh and exports:
   - `avatar.obj`
   - `avatar.glb`
   - `measurements.json`
2. `measurements.json` currently stores copied measurement values, scale notes, and mesh bounds, but not semantic body anchors.
3. `vto/clo_automation_steps/step_06_read_edges_and_slots.py` tries to obtain arrangement slots from CLO, but slot responses are often empty or generic for the imported avatar.
4. `vto/clo_automation_steps/step_07_arrange_patterns.py` already has a degraded fallback mode that directly offsets panels without slot indices.
5. This means the pipeline already contains the seed of the correct fallback architecture, but it is missing avatar-side semantic data.

So the right STAR-path question is not:

"How do we make CLO fully understand our custom mesh as a native avatar?"

It is:

"What minimum extra data should our STAR pipeline export so our own code can place panels much better around a static body?"

---

## What We Already Have in the Repo

### Step 1: Avatar generation

Relevant files:

- `avatar_generation/first.py`
- `avatar_generation/run_avatar.py`
- `avatar_generation/fit_betas.py`
- `avatar_generation/star_runner.py`
- `avatar_generation/mesh_measure.py`
- `avatar_generation/avatar_exporter_clo.py`

Current fitted target fields:

- `height_cm`
- `shoulder_width_cm`
- `chest_circumference_cm`
- `waist_circumference_cm`
- `hip_circumference_cm`

Current export payload for CLO:

- `avatar.obj`
- `measurements.json`

Current `measurements.json` includes:

- copied user measurements
- units
- scale factor
- mesh bounds
- mesh vertex and face counts

What it does not include:

- named body joints
- shoulder / neck / underarm anchor points
- torso front/back centers
- sleeve anchor points
- body planes such as chest line, waist line, hip line
- per-anchor confidence or derivation method
- direct placement hints for `front_panel`, `back_panel`, `sleeve_left`, `sleeve_right`

### Step 3: VTO / CLO orchestration

Relevant files:

- `vto/clo_automation_steps/step_03_import_avatar.py`
- `vto/clo_automation_steps/step_05_verify_patterns.py`
- `vto/clo_automation_steps/step_06_read_edges_and_slots.py`
- `vto/clo_automation_steps/step_07_arrange_patterns.py`
- `clo_workspace/plugins/RestPlugin.cpp`

Current use of avatar-side metadata:

1. `step_03_import_avatar.py` uses `measurements.json` only to infer import scale.
2. `step_05_verify_patterns.py` uses `measurements.json` for rough scale diagnostics.
3. No current step uses exported avatar landmarks or semantic anchor data because that data does not exist yet.

---

## Goal of This Plan

Export enough static semantic avatar data so the VTO pipeline can compute much better direct panel placement without depending on CLO-native slots.

Important constraint:

- We are not solving movement or animation in this plan.
- We are not trying to turn the STAR avatar into a full CLO-native avatar.
- We are only solving the initial placement problem well enough for cleaner arrangement and downstream simulation.

---

## Data We Eventually Need

This is the full target data set for the STAR path. We will not add it all at once.

### 1. Coordinate and pose metadata

Needed because every later anchor depends on a locked coordinate frame.

Fields:

- units
- world up-axis
- forward-axis
- left-right axis
- pose mode (`tpose` / `apose`)
- scale used during mesh generation
- mesh centroid
- mesh bounding box

### 2. Joint landmarks

Needed because shoulder, neck, pelvis, and arm anchors should not be inferred from random bbox points.

Initial joints to export:

- pelvis
- neck
- left_collar
- right_collar
- left_shoulder
- right_shoulder
- left_elbow
- right_elbow
- left_wrist
- right_wrist
- left_hip
- right_hip

Why this is already feasible:

- the repo already uses the STAR joint regressor for shoulder measurement in `mesh_measure.py`
- `avatar_generation/tests/inspect_star_joints.py` confirms the standard STAR/SMPL joint layout

### 3. Body-region planes and scalar guides

Needed because panel placement depends on body levels, not only individual points.

Initial scalar guides:

- shoulder_line_y
- underarm_line_y
- chest_line_y
- waist_line_y
- hip_line_y
- neck_base_y

### 4. Body extents at important levels

Needed because front/back spacing should depend on torso thickness and width, not fixed offsets.

Initial extents:

- chest width
- chest depth
- waist width
- waist depth
- hip width
- hip depth

### 5. Placement anchors

These are the most important new outputs for solving the current issue.

Initial anchors:

- `front_torso_anchor`
- `back_torso_anchor`
- `left_sleeve_anchor`
- `right_sleeve_anchor`
- `center_front_neck_base`
- `center_back_neck_base`
- `left_underarm_proxy`
- `right_underarm_proxy`

### 6. Orientation hints

Needed because an anchor point without a direction still leads to weak placement.

Initial orientation hints:

- torso forward vector
- torso up vector
- left arm outward vector
- right arm outward vector
- front panel recommended normal
- back panel recommended normal
- left sleeve recommended normal
- right sleeve recommended normal

### 7. Confidence and derivation metadata

Needed so we know whether an anchor came from:

- STAR joint regressor
- mesh band computation
- bbox projection
- heuristic fallback

This prevents hidden guesswork.

---

## Files To Add, In the Order We Should Add Them

We should add these files one by one.

### File 1: `avatar_semantics.json`

This is the first and most important file.

It should contain:

- run and version info
- coordinate frame info
- pose info
- bbox / centroid
- joint landmarks
- body planes
- core placement anchors
- orientation hints
- confidence / derivation method

Why first:

- it is enough to begin improving placement
- it avoids adding multiple files before we know what actually helps
- it gives a single contract the VTO step can read immediately

### File 2: `avatar_placement_hints.json`

Add this only after File 1 is wired into VTO.

It should contain:

- piece-level recommended placement targets for `front_panel`, `back_panel`, `sleeve_left`, `sleeve_right`
- recommended offsets
- recommended orientation angles
- per-piece fallback priority order
- piece-to-anchor mapping

Why separate from File 1:

- `avatar_semantics.json` should stay body-centric
- `avatar_placement_hints.json` can evolve with garment classes without redefining the avatar core contract

### File 3: `avatar_cross_sections.json`

Only add this if direct placement still needs better spacing.

It should contain:

- chest / waist / hip band outlines or sampled section data
- front-most / back-most / left-most / right-most points by level
- optional local sleeve / upper-arm section summaries

Why later:

- this is useful, but not the first proof point
- it is more detailed than we need for the first placement improvement

### File 4: `avatar_semantic_debug.json`

Add only if debugging becomes difficult.

It should contain:

- intermediate values used to derive anchors
- warnings on missing joints or weak landmarks
- fallback reason logging

---

## Recommended Execution Order

1. Lock the semantic contract first.
2. Add `avatar_semantics.json` only.
3. Update VTO to consume that file before asking CLO for semantic slots.
4. Switch panel placement from fixed offsets to anchor-informed direct offsets.
5. Test on a small number of users and shirts.
6. Add `avatar_placement_hints.json` only if the first file proves useful.
7. Add section-level or debug files only if evidence shows they are needed.

---

## Phase Plan

## Phase 1: Lock the Static Avatar Semantic Contract

**Goal**: Define the exact semantic body data we need from STAR for static garment placement.

**Steps**:

1. Freeze the current scope: static avatar only, no movement work in this plan.
2. Freeze the coordinate assumptions used throughout the repo:
   - STAR mesh in meters before export
   - CLO OBJ export in centimeters
   - current import scale logic in `step_03_import_avatar.py`
3. Lock the first anchor vocabulary:
   - front torso
   - back torso
   - left sleeve
   - right sleeve
   - neck base
   - underarm proxies
4. Decide the first version number for the semantic contract so later iterations do not silently break readers.
5. Document which anchors come from exact model joints and which are mesh-derived heuristics.

**Deliverable**:

- written contract for `avatar_semantics.json`

## Phase 2: Add `avatar_semantics.json` to Step 1

**Goal**: export a first semantic sidecar from the STAR pipeline.

**Likely code areas**:

- `avatar_generation/avatar_exporter_clo.py`
- `avatar_generation/star_runner.py`
- `avatar_generation/mesh_measure.py`
- new helper modules for semantic extraction

**Steps**:

1. Add a helper that computes STAR joints from the joint regressor.
2. Add a helper that derives torso planes and torso extents.
3. Add a helper that derives body anchors from joints plus section-level geometry.
4. Write `avatar_semantics.json` into the run folder next to `avatar.obj` and `measurements.json`.
5. Keep existing files untouched so the current VTO flow still runs.
6. Add version and validation fields so the file can be safely read later.

**Proposed minimal schema**:

```json
{
  "schema_version": 1,
  "run_id": "u_001-001",
  "units": "centimeters",
  "pose": "tpose",
  "axes": {
    "up": [0, 1, 0],
    "forward": [0, 0, 1],
    "right": [1, 0, 0]
  },
  "bbox_cm": {
    "min": [-20.1, 0.0, -11.8],
    "max": [20.1, 178.0, 11.8]
  },
  "joints_cm": {
    "left_shoulder": [-18.2, 146.4, 0.5],
    "right_shoulder": [18.2, 146.4, 0.5]
  },
  "body_levels_cm": {
    "neck_base_y": 145.0,
    "chest_y": 132.0,
    "waist_y": 103.0,
    "hip_y": 92.0,
    "underarm_y": 124.0
  },
  "anchors_cm": {
    "front_torso_anchor": [0.0, 132.0, 9.1],
    "back_torso_anchor": [0.0, 132.0, -9.1],
    "left_sleeve_anchor": [-27.0, 126.0, 0.0],
    "right_sleeve_anchor": [27.0, 126.0, 0.0]
  },
  "orientation_vectors": {
    "torso_forward": [0, 0, 1],
    "left_arm_outward": [-1, 0, 0],
    "right_arm_outward": [1, 0, 0]
  }
}
```

## Phase 3: Use STAR Semantics in VTO Before CLO Slots

**Goal**: make the VTO pipeline use our own semantic avatar data for placement instead of relying first on CLO-native slots.

**Likely code areas**:

- `vto/clo_automation_steps/context.py`
- `vto/clo_automation_steps/step_06_read_edges_and_slots.py`
- `vto/clo_automation_steps/step_07_arrange_patterns.py`

**Steps**:

1. Load `avatar_semantics.json` into `PipelineContext`.
2. Add a new internal placement mode:
   - `star_semantic_direct`
3. In Step 6, detect semantic sidecar availability before treating empty CLO slots as a blocker.
4. In Step 7, compute panel offsets from anchors instead of using the current hardcoded degraded spread.
5. Keep the current CLO slot path intact so both approaches can be compared on the same repo.
6. Record which placement provider was used into the pipeline report.

**Important design rule**:

- Do not remove current slot logic yet.
- Add STAR semantic placement as a first-class provider beside:
  - CLO slot placement
  - current degraded fixed-offset placement

## Phase 4: Add `avatar_placement_hints.json` Only If Needed

**Goal**: separate body semantics from garment-placement policy.

**Why it may become necessary**:

- body anchors tell us where the body is
- they do not by themselves encode garment-category-specific spacing policy

**Steps**:

1. Add a second optional sidecar for panel-placement hints.
2. Start with t-shirt-only hints because the current product pipeline is t-shirt oriented.
3. Store:
   - piece-to-anchor mapping
   - recommended extra gap from body
   - orientation defaults
   - fallback order if an anchor is missing
4. Make VTO use this file only if present; otherwise derive from `avatar_semantics.json`.

## Phase 5: Add Cross-Section Data Only If Spacing Still Fails

**Goal**: improve direct placement when torso depth or sleeve spacing is still wrong.

**Steps**:

1. Add cross-section summaries at chest, waist, hip, and upper-arm levels.
2. Use these values to compute front/back spacing more accurately.
3. Use section widths and depths to reduce early pattern-avatar collisions.

## Phase 6: Evaluate the STAR Path Against the CLO-Native Path

**Goal**: make this a comparable candidate rather than a permanent assumption.

**Evaluation criteria**:

1. Avatar measurement fidelity
2. Initial panel placement quality
3. Number of panel-avatar collisions before simulation
4. Seam pull-in quality after sewing
5. Simulation stability
6. Engineering complexity
7. Dependency on CLO-native hidden behavior
8. Long-term maintainability

---

## What We Should Explicitly Not Add Yet

To keep this path lean, do not add these in the first rollout:

1. Full rigging or skin weights
2. Motion files
3. FBX export
4. Per-vertex semantic labels
5. Dozens of garment-specific anchor variants
6. CLO-native arrangement point files
7. Automatic body retopology changes

Those can come later only if the placement problem proves impossible to solve with the static semantic sidecar approach.

---

## Expected Benefits

1. Keeps the current STAR fitting work relevant.
2. Solves the immediate arrangement problem without waiting for CLO-native avatar adoption.
3. Reduces dependency on fragile slot-name matching.
4. Makes placement logic explicit and debuggable.
5. Preserves future flexibility if the final user-facing avatar remains STAR-based.

---

## Main Risks

1. Anchor quality may still be approximate because the current measurement model is sparse.
2. We may still need garment-category-specific placement policy after body anchors are added.
3. If the body-semantic extraction is weak, we can overcomplicate the avatar side without matching CLO-native reliability.

---

## Recommended First Slice

If we execute this plan, the first slice should be:

1. add `avatar_semantics.json`
2. export joints + body levels + four main anchors
3. wire VTO to use it for `front_panel`, `back_panel`, `sleeve_left`, `sleeve_right`
4. compare against the current degraded offset placement on the same avatar and shirt

That is the smallest meaningful proof point for the STAR path.

---

## Repo Files Most Relevant to This Plan

- `avatar_generation/first.py`
- `avatar_generation/avatar_exporter_clo.py`
- `avatar_generation/fit_betas.py`
- `avatar_generation/mesh_measure.py`
- `avatar_generation/star_runner.py`
- `avatar_generation/tests/inspect_star_joints.py`
- `vto/clo_automation_steps/context.py`
- `vto/clo_automation_steps/step_03_import_avatar.py`
- `vto/clo_automation_steps/step_05_verify_patterns.py`
- `vto/clo_automation_steps/step_06_read_edges_and_slots.py`
- `vto/clo_automation_steps/step_07_arrange_patterns.py`
