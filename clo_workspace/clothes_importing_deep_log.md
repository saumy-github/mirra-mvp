# Clothes Importing Deep Log

## Scope
This document is a deep incident log for why garment pieces are still not placed around the avatar in CLO, even though automation reports successful arrangement.

Date: 2026-03-16
Branch: `clothplacement`
Pipeline entrypoint: `clo_workspace/plugins/clo_automation_client.py`

## Latest Run Evidence (from terminal)
1. Patterns load correctly.
- `[5] Verifying pattern count ... Patterns in CLO scene: 4 (expected 4)`

2. Pattern metadata is incomplete.
- `[6] Pattern 0: 0 (? edges)` for all 4 pieces.

3. Arrangement slot API is unavailable in-session.
- `[6b] No slots returned ...`
- Slot recovery attempt (`simulate(1)` then re-query) still did not return slots.

4. Fallback arrangement commands are accepted and read back as different values.
- Stage 7 verify shows different `ArrangementOffsetX/Y/Z` and `ArrangementOrientation` per pattern.
- Example: pattern 0 `10,80,80,ori=0` vs pattern 1 `90,80,80,ori=180`.

5. Visual result in CLO still shows stacking/not-around-avatar behavior.
- User observed pieces still at same location (foot-level / in front), despite different reported arrangement values.

## Confirmed Facts
1. Command queue + server are healthy.
- Health check, import, seams, simulate all execute without API exceptions.

2. Arrangement values are being written at API level.
- `/pattern-arrangements` readback reflects requested values.

3. Visual placement does not follow arrangement metadata in this CLO state.
- API state and viewport state are diverging.

## Tracked Issues (Confirmed, Ordered)

1. Arrangement slots are often unavailable at runtime.
- Evidence: `[6b] No slots returned ...` and repeated empty slot behavior.
- References:
	- `clo_workspace/clothes_importing_deep_log.md:18`
	- `clo_workspace/clothes_importing_deep_log.md:44`
	- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py:28`
	- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py:39`
- Impact: no reliable body-anchor context for placement.

2. Pipeline continues in degraded mode instead of failing.
- Evidence: deep log calls for hard fail when slots are missing, but current step 7 still applies fallback spread offsets.
- References:
	- `clo_workspace/clothes_importing_deep_log.md:148`
	- `clo_workspace/clothes_importing_deep_log.md:169`
	- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py:20`
	- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py:26`
- Impact: false-positive progress into fabric/seam/sim even when placement trust is low.

3. API readback and viewport behavior diverge.
- Evidence: offsets/orientation differ per piece in readback while visual result is still stacked.
- References:
	- `clo_workspace/clothes_importing_deep_log.md:21`
	- `clo_workspace/clothes_importing_deep_log.md:25`
	- `clo_workspace/plugins/RestPlugin.cpp:425`
	- `clo_workspace/plugins/RestPlugin.cpp:449`
	- `clo_workspace/plugins/RestPlugin.cpp:644`
	- `clo_workspace/plugins/RestPlugin.cpp:648`
	- `clo_workspace/plugins/RestPlugin.cpp:654`
- Impact: "reported arranged" does not guarantee physically separated panels.

4. Pattern info parsing is likely mismatched.
- Evidence: stage 6 shows `Pattern 0: 0 (? edges)` while parser assumes `info.name` and `info.line_count`.
- References:
	- `clo_workspace/clothes_importing_deep_log.md:15`
	- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py:13`
	- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py:14`
	- `clo_workspace/plugins/RestPlugin.cpp:290`
- Impact: observability gap; hard to validate geometry readiness.

5. Success semantics are weak in later stages.
- Evidence:
	- Step 7 fails only for identical fingerprints/missing verify payload, but still allows degraded placement path.
	- Step 9 does not gate on individual seam failures and returns true after queue wait.
	- Pattern count verification only fails at zero, not mismatch with expected count.
- References:
	- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py:71`
	- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py:78`
	- `clo_workspace/plugins/clo_automation_steps/step_09_create_seams.py:16`
	- `clo_workspace/plugins/clo_automation_steps/step_09_create_seams.py:29`
	- `clo_workspace/plugins/clo_automation_steps/step_05_verify_patterns.py:9`
- Impact: pipeline can proceed with partially invalid state.

6. Unit/semantic ambiguity around arrangement inputs.
- Evidence:
	- Route comments mention centimetres.
	- Arrangement offset comments mention millimetres.
	- Python payload uses `position.offset` for depth (`z`) rather than explicit `z`.
- References:
	- `clo_workspace/plugins/RestPlugin.cpp:352`
	- `clo_workspace/plugins/RestPlugin.cpp:364`
	- `clo_workspace/plugins/clo_automation_steps/client.py:68`
- Impact: tuning mistakes and inconsistent interpretation are likely.

7. Orientation handling may be semantically wrong for CLO API.
- Evidence:
	- Plugin comments label orientation as enum.
	- Python fallback sends values such as 180/270 like degrees.
- References:
	- `clo_workspace/plugins/RestPlugin.cpp:361`
	- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py:21`
- Impact: if SDK expects enum codes, these values may be ignored or misinterpreted.

8. Plugin-version observability is too weak.
- Evidence: health endpoint reports static `version: 1.0`, no build hash/timestamp endpoint.
- References:
	- `clo_workspace/plugins/RestPlugin.cpp:87`
- Impact: hard to confirm which plugin binary is actually loaded.

9. Runtime execution model depends on Win32 timer callback behavior.
- Evidence: queue draining depends on `SetTimer` while `DoFunctionContinuously` is empty.
- References:
	- `clo_workspace/plugins/RestPlugin.cpp:734`
	- `clo_workspace/plugins/RestPlugin.cpp:774`
- Impact: potential timing-related divergence where commands look accepted but visual updates lag or fail.

## Main Root-Cause Candidates (Ranked)
1. Missing live arrangement slots is the primary blocker.
- Without valid slot anchors, placement intent is not tied to avatar body regions.

2. Arrangement metadata updates are not equivalent to guaranteed viewport/world transform in this SDK path.
- Current verification reads metadata, not true 3D panel centroids.

3. Degraded-mode pipeline behavior masks placement failure.
- Pipeline continues into seams/simulation, making placement failure look non-fatal.

4. Arrangement parameter semantics are likely mismatched (units + orientation).
- Especially orientation enum vs degree-style values and mixed cm/mm guidance.

5. Observability gaps prevent definitive diagnosis in one run.
- No bbox/world-transform endpoint, uncertain pattern-info schema, and no plugin build identity endpoint.

## Direct Assessment: Is Plugin/SDK Usage Part of the Issue?
Yes, likely in two concrete ways:
1. SDK capability/behavior mismatch: current arrangement APIs can persist metadata without forcing visible placement in this CLO session.
2. Plugin usage semantics mismatch: fallback mode, orientation/unit assumptions, and weak stage gates produce a success-looking run when placement is actually invalid.

## Gaps in Current Observability
1. No endpoint for actual world-space transform/centroid of each pattern piece.
2. No endpoint for per-pattern bbox in 3D after arrangement.
3. No plugin version hash endpoint to confirm exact loaded DLL.

## Recommended Fix Sequence (Do in order)

### Phase 1: Stop misleading success (quick)
1. In stage 7, if `has_live_slots == False`, fail by default and stop pipeline before seams.
2. Add clear terminal message: `Placement not trustworthy: arrangement slots unavailable in CLO session.`

### Phase 2: Improve diagnostics (quick-medium)
1. Add `/debug/pattern-bbox` endpoint in plugin using `GetBoundingBoxOfPattern`.
2. Print bbox in step 6 and after step 7.
3. Add `/version` endpoint with build timestamp/commit string.

### Phase 3: Recover stable around-avatar placement (medium)
1. Prefer slot-based mode only when `/arrangement-list` returns real slots.
2. If slots absent, run deterministic recovery routine:
- `simulate(1)`
- small wait
- re-query slots 3-5 times
- if still absent: hard fail (unless explicit override)

### Phase 4: Verify seam map only after placement is valid (quick)
1. Gate step 9 on placement validity.
2. Do not stitch/simulate stacked panels.

## Immediate Action Items
1. Add hard fail in `step_07_arrange_patterns.py` when `ctx.has_live_slots` is false (default behavior).
2. Add plugin `/version` endpoint and print it in stage 1 health check.
3. Add debug endpoint for bbox and log it in stage 6 and 7.
4. Update `clo_workspace/README.md` troubleshooting section with this degraded-mode rule.

## File-Level Change Targets
1. `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py`
2. `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py`
3. `clo_workspace/plugins/RestPlugin.cpp`
4. `clo_workspace/plugins/clo_automation_steps/client.py`
5. `clo_workspace/README.md`

## Definition of Done for Placement
Placement is considered fixed only if all are true:
1. `/arrangement-list` returns valid slots in-session OR explicit alternative placement API proves distinct 3D positions.
2. Stage 7 verify shows distinct per-pattern placement values.
3. Visual CLO viewport shows front/back/sleeves around torso/arms (not stacked at foot/in front).
4. Pipeline blocks with clear error when these conditions are not met.

## Phase 1 Solution Framework

### Problem We Are Solving
- **Core issue**: Garment pieces are not reliably placed around the avatar in CLO, even though automation reports successful arrangement.
- **Observable symptom**: Stage 6 diagnostics are misleading because they read CLO metadata as if it were geometry truth.
- **Hidden consequence**: This creates false confidence and allows later steps to continue when placement is not trustworthy.

### What Is NOT the Core Problem
- **DXF generation is not failing functionally**: CLO imports 4 patterns successfully; POLYLINE entities are valid.
- **REST plugin transport is not corrupting payloads**: Plugin mostly forwards SDK responses without transformation; readback divergence comes from SDK behavior, not plugin interference.
- **Seam creation logic is not driven by Stage 6 metadata**: Seams use predefined maps (step_09), so Stage 6 is not the seam root cause.

### What We Are Fixing First (Scope: Phase 1)
1. **Observability and truthfulness of Stage 6**: Make raw CLO responses inspectable.
2. **Placement validity gating before downstream steps**: Fail fast when placement context is invalid.
3. **Plugin visibility features**: Reduce ambiguity in live runs with build identity and optional verbose logging.

### How We Will Solve It

#### Stage 6 Raw Payload Visibility
- Add a debug toggle (environment variable or config flag: `DEBUG_STAGE6_RAW`).
- Print full `/patterns/{index}` payload to terminal when enabled.
- Optionally save payload snapshots to file for diffing across runs (e.g., `stage_6_payloads/run_{timestamp}.json`).
- **Goal**: Prove exactly what CLO returns vs what parser assumes.

#### Stage 6 Parser Hardening
- Stop assuming fixed keys like `name` and `line_count` unless present in response.
- Treat missing or unknown schema keys as diagnostic warning, not inferred geometry.
- Add explicit fallback for missing fields (e.g., `name = info.get("name", f"pattern_{idx}")`).
- **Goal**: Avoid overinterpreting limited metadata and silent failures.

#### Placement Truth Gates
- If live arrangement slots are unavailable (`ctx.has_live_slots == False`), fail fast by default before seams/simulation.
- Add explicit-override flag (e.g., `ALLOW_DEGRADED_PLACEMENT=1`) for runs that knowingly continue in degraded mode.
- Keep degraded mode explicit in logs, not silent.
- **Goal**: Prevent false-positive "success" runs when placement confidence is low.

#### Plugin Observability (Not Root Cause, But Critical Support)
- Add `/version` endpoint in RestPlugin.cpp with build identity information (e.g., build timestamp, commit hash, or static version + compile date).
- Add optional verbose/raw logging mode for metadata pass-through (e.g., log all `/patterns/{index}` and `/arrangement-list` responses).
- Print plugin version and diagnostic mode in Stage 1 health check.
- **Goal**: Confirm exact DLL/session identity and eliminate stale-binary confusion.

### Success Criteria for Phase 1

1. **Inspectable raw payloads**: Team can view full CLO `/patterns/{index}` and `/arrangement-list` responses in logs or files during/after Stage 6 execution.
2. **Clear pipeline failure states**: Pipeline explicitly fails (with clear message) when placement context is invalid, instead of continuing silently into seams/simulation.
3. **Run-level identification**: Every run can identify plugin build/version and diagnostic mode (raw logging on/off, degraded placement allowed/denied) from early logs.
4. **Confident architecture decision**: Team has definitive payload data to decide whether CLO metadata is sufficient for placement or if geometry must come from DXF as source of truth.

### Implementation Dependencies
- No changes to seam logic or broader architecture.
- Does not require DXF re-export or CLO SDK upgrades.
- All changes confined to automation steps (Python) and plugin observability (C++ REST endpoint).
- Hard fail gate can be overridden with explicit environment flag for existing degraded-mode workflows.
