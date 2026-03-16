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

## High-Probability Root Causes

### A) Arrangement metadata is not bound to active avatar arrangement context
Confidence: High

Why:
- `GetArrangementList()` is empty repeatedly.
- Without live arrangement anchors, CLO may store arrangement fields but not apply them spatially as expected.

Where:
- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py`
- `clo_workspace/plugins/RestPlugin.cpp` (`/arrangement-list`, arrange command)

Fix direction:
- Treat empty arrangement-list as hard degraded mode.
- Add explicit degraded-mode behavior that does not rely on arrangement placement for final visual positioning.

### B) CLO applies arrangement fields but viewport keeps imported pattern stack transform
Confidence: High

Why:
- Readback shows different arrangement values, but rendered pieces remain overlapped.
- Suggests arrangement fields are metadata or deferred, not immediate placement driver in this SDK path.

Where:
- `clo_workspace/plugins/RestPlugin.cpp` (`SetArrangementPosition`, `SetArrangementOrientation` path)

Fix direction:
- Introduce alternative placement APIs if available (none obvious in current `PatternAPIInterface.h` for direct 3D world translation).
- If unavailable, enforce slot-based curved arrangement only after slots are proven available.
- Abort early when slots are unavailable (do not continue to seam/simulate as if placement succeeded).

### C) Pattern info endpoint likely not providing expected structure
Confidence: Medium-High

Why:
- Stage 6 always prints `name=0, line_count=?`.
- Indicates `GetPatternInformation` JSON shape is different than assumed, or parse fallback path is wrong.

Where:
- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py`
- `clo_workspace/plugins/RestPlugin.cpp` (`/patterns/{index}`)

Fix direction:
- Log raw payload from `/patterns/{index}` during debugging.
- Update parser keys in stage 6.
- Use this as diagnostic quality gate (if metadata is malformed, arrangement may also be unreliable).

### D) False-positive success semantics in Python stage progression
Confidence: Medium

Why:
- Pipeline proceeds to seams/simulation even when spatial placement is visibly wrong.
- Current checks only verify arrangement metadata uniqueness, not true around-avatar placement.

Where:
- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py`

Fix direction:
- Add strict gate: if `has_live_slots == False`, fail pipeline unless user explicitly sets `ALLOW_DEGRADED_PLACEMENT=1`.
- Print explicit failure reason and stop before seams.

## Medium-Probability Root Causes

### E) CLO plugin menu/session state not fully refreshed after DLL replacement
Confidence: Medium

Why:
- CLO can keep stale plugin state across sessions if not fully restarted.
- Behavior mismatch (API accepted but viewport unchanged) can happen with stale runtime state.

Fix direction:
- Ensure full CLO process restart after DLL copy.
- Verify only one `RestPlugin.dll` in active plugin path.
- Add plugin startup banner with build timestamp/version endpoint.

### F) DXF import orientation/anchor defaults causing same landing zone before arrangement
Confidence: Medium

Why:
- DXFs may import with identical local transforms and same arrangement pivot semantics.

Fix direction:
- Add post-import diagnostics endpoint for pattern bounding boxes if SDK exposes it (`GetBoundingBoxOfPattern`).
- Print bbox for each piece and compare.

### G) Arrangement value domain/range mismatch for this CLO version
Confidence: Medium

Why:
- SDK docs are sparse around exact numeric domains of arrangement offset fields.
- Values may be normalized or interpreted relative to same anchor.

Fix direction:
- Sweep a small grid of arrangement values for one pattern and inspect viewport effect manually.
- Record which axes actually move geometry in this version.

## Lower-Probability Causes
1. Multi-avatar/body context confusion after `new-project`.
2. Hidden garment/pattern piece locking or pinning state.
3. Auto-arrangement overrides by CLO on simulate start.

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
