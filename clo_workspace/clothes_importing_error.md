# Clothes Importing Error - Coordinate/Arrangement Issues

This note captures issues currently causing garments to import or arrange away from the avatar instead of around it.

## High-impact issues

1. No arrangement slots are returned, so pattern-slot binding is skipped.
- Evidence from run output: `No slots returned ... Matched slots - front:-1 back:-1 sleeve_L:-1 sleeve_R:-1`.
- Code path: `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py`.
- Impact: stage 7 sends `arrangement_index=-1` for all pieces, so CLO body-slot placement is not used.

2. `SetArrangement(...)` is explicitly bypassed when slot is `-1`.
- Code path: `clo_workspace/plugins/RestPlugin.cpp` (arrange handling in `ProcessCommandQueue`).
- Current behavior:
  - If `cmd.param4 >= 0`, call `PATTERN_API->SetArrangement(pattern, slot)`.
  - Else skip it and only call `SetArrangementPosition(...)`.
- Impact: pieces are offset without a valid avatar anchor slot, so they do not reliably land around body front/back/sleeves.

3. Arrangement endpoint always reports success even if CLO calls fail.
- Code path: `clo_workspace/plugins/RestPlugin.cpp` in `arrange-pattern` command processing.
- `result.success = true` is set unconditionally after placement calls.
- Impact: pipeline logs look successful (`Pattern arrangement queued` / success lines) even when real placement did not happen correctly.

## Medium-impact issues

4. Slot matching logic is text-search based and fragile.
- Code path: `clo_workspace/plugins/clo_automation_steps/helpers.py` (`find_slot`).
- It matches by keywords in stringified slot dict values.
- Impact: CLO naming differences or localization can miss/mis-map slots, causing wrong body part mapping or `-1` fallback.

5. No fallback mapping when `/arrangement-list` is empty.
- Code path: `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py` and `step_07_arrange_patterns.py`.
- Current behavior: empty slots lead directly to all `-1` indices.
- Impact: arrangement has no deterministic fallback around avatar.

6. Coordinate semantics are inconsistent in comments and API naming.
- Code path: `clo_workspace/plugins/RestPlugin.cpp` and Python client payload.
- C++ comments mention both cm and mm in different places; JSON uses `position.offset` for depth (`z`) rather than explicit `z`.
- Impact: easy to tune wrong values and misinterpret what axis/depth is being applied.

7. Placement precision is truncated to integers.
- Code path: `clo_workspace/plugins/RestPlugin.cpp`.
- `SetArrangementPosition` receives `(int)cmd.floatParam1/2/3`.
- Impact: fine-grained offsets are lost; not the main root cause, but reduces placement control.

## Additional warning signs seen in logs

8. Pattern info appears incomplete (`0 (? edges)`).
- Evidence from run output: each pattern printed as `Pattern N: 0  (? edges)`.
- Related code path: `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py`.
- Impact: suggests pattern metadata retrieval is not as expected, which can correlate with unstable arrangement metadata/state.

## Why this causes the observed problem now

The biggest blocker is slot resolution failing and all pieces being arranged with `slot=-1`.
Without valid `SetArrangement` anchors, offsets are not applied in a reliable avatar-relative frame, so garments do not appear around the body correctly.

## Files involved

- `clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py`
- `clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py`
- `clo_workspace/plugins/clo_automation_steps/helpers.py`
- `clo_workspace/plugins/RestPlugin.cpp`
