# T-Pose + Optional A-Pose Plan (Minimum Code Changes)

## Goal

Keep existing T-pose behavior unchanged and add an option to generate avatars in A-pose.

## Decision

- **Default pose remains T-pose** (current behavior).
- Add a **runtime pose option**: `tpose` or `apose`.
- Use thetas-only change for A-pose (shoulders), as suggested.

## Current state

- Pose vector is produced in [avatar_generation/pose_catalog.py](avatar_generation/pose_catalog.py).
- Main generation path consumes pose in [avatar_generation/first.py](avatar_generation/first.py).
- Current zero-theta output is STAR neutral T-pose.

## Minimal-change design

### 1) Pose catalog (primary change)

In [avatar_generation/pose_catalog.py](avatar_generation/pose_catalog.py):

- Keep current zero-theta function for T-pose.
- Add A-pose theta function by changing shoulder joints only.
- Add one selector helper, e.g. `get_pose_thetas(pose_name, pose_size)`.

Proposed A-pose initialization:

- `thetas = np.zeros(pose_size)`
- joint indices:
   - left shoulder = `16`
   - right shoulder = `17`
- axis-angle indexing: `thetas[j*3 : j*3+3]`
- start at ~35° adduction:
   - `thetas[16*3 + 2] = -rad(35)`
   - `thetas[17*3 + 2] = +rad(35)`

If arm direction is inverted in outputs, swap signs.

### 2) Pipeline entry option (small change)

In [avatar_generation/first.py](avatar_generation/first.py):

- Add CLI arg: `--pose` with choices `tpose|apose` and default `tpose`.
- Replace direct pose call with pose selector call.
- Keep all non-pose logic unchanged (fitting, postprocess, export).

In [avatar_generation/run_avatar.py](avatar_generation/run_avatar.py) (optional):

- Keep default non-interactive behavior as T-pose.
- Optionally prompt user for pose, default `tpose`.

### 3) Metadata update (small)

In [avatar_generation/pose_catalog.py](avatar_generation/pose_catalog.py):

- Return pose-specific metadata (`pose_name`, `description`) for both T and A.
- Ensure values JSON records selected pose accurately.

## Files to touch

1. [avatar_generation/pose_catalog.py](avatar_generation/pose_catalog.py) — add dual-pose theta helpers and metadata selector
2. [avatar_generation/first.py](avatar_generation/first.py) — add `--pose` and route theta selection
3. [avatar_generation/run_avatar.py](avatar_generation/run_avatar.py) — optional prompt/pass-through of pose

## Backward compatibility

- Existing commands without `--pose` continue to produce T-pose.
- No schema break required.
- Existing consumers of generated artifacts remain compatible.

## Validation checklist

1. Run default flow (no pose arg) and confirm T-pose output is unchanged.
2. Run with `--pose apose` and confirm arms are lowered (~30–40°).
3. Confirm generated artifacts still succeed:
    - inputs JSON structure unchanged
    - values JSON includes correct thetas/pose metadata
    - GLB and CLO OBJ exports complete

## Risk and mitigation

- Risk: wrong axis/sign makes arms rotate incorrectly.
   - Mitigation: sign flip first, then tune angle (`30°`, `35°`, `40°`).
- Risk: shoulder/torso intersection at higher adduction.
   - Mitigation: use conservative default (`35°`).

## Rollback

- Keep `--pose` interface.
- Temporarily map `apose` to zero-theta T-pose if needed.
- Full rollback is limited to [avatar_generation/pose_catalog.py](avatar_generation/pose_catalog.py) and CLI arg wiring.

