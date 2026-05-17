 Plan 013: Step-1 CLO Digital Twin - Apply Measurements and Save Avatar

## Overview

This plan is for **Step-1 only**: create a proper digital twin by starting from
`clo_avatar_generation/input/base-1.avt`, loading that avatar into CLO,
applying measurement values to the loaded avatar, and saving the modified
result as the user's reusable body asset.

For this plan, success is simple:

1. the avatar loads into CLO
2. the avatar dimensions change based on the provided measurements
3. the final result can be saved

This plan is restricted to:

- `clo_avatar_generation/`
- `clo_workspace/`

This plan does **not** include:

- `product_ingestion/`
- macOS plugin work
- Step-3 VTO assembly

## Current Grounded Findings

- The base avatar input is `clo_avatar_generation/input/base-1.avt`.
- The first controlled measurement source for this plan should be a JSON file
  shaped like the current MongoDB document for `u_001`.
- The current Step-1 run folder format is `output/<user_id>-<run_id>`, for
  example `clo_avatar_generation/output/u_001-004`.
- The `u_001-004` folder is a Step-1 folder, not a VTO folder, but it is
  currently too flat and hard to inspect.
- The Windows plugin already exposes:
  - native avatar import
  - avatar measurement import
  - project save
- The Windows plugin does **not** currently expose a dedicated direct
  "save avatar as `.avt`" endpoint.
- The current Step-1 failure happens at measurement application, so the first
  real blocker is proving how measurement values should be applied to a loaded
  avatar using the current Windows plugin.
- The current save strategy should start by keeping **both**:
  - `.zprj`
  - `.avt`
  so they can later be compared manually for storage quality and completeness.

## Implementation Sequence

The work should be done in this order:

1. confirm the exact current Step-1 and Windows-plugin behavior
2. make the first JSON-driven measurement-apply path work on a loaded avatar
3. save both `.zprj` and `.avt` for the modified avatar
4. clean the Step-1 run-folder layout so the artifacts are easier to inspect
5. only then expand field coverage and later add women-avatar support

## Phases

### Phase 1: Audit the Current Step-1 Runtime and Windows Plugin

**Goal**: Remove ambiguity about what already works, what fails, and whether
the current blocker is in the Step-1 implementation or the Windows plugin.

**Steps**:

1. Trace the current Step-1 runtime from `run_avatar.py` through the pipeline
   steps used for base-avatar import, measurement apply, and save.
2. Map every file in `clo_avatar_generation/output/u_001-004` to the step that
   generated it so the current run folder becomes understandable.
3. Confirm exactly how the Windows plugin handles:
   - `.avt` import
   - measurement import for a loaded avatar
   - project save
   - extracted avatar artifacts after save
4. Decide whether the first failure is caused by:
   - the CSV bridge format
   - the runtime call sequence
   - missing plugin behavior
   - or insufficient plugin diagnostics
5. Record the current Step-1 success boundary:
   - base avatar import works
   - measurement apply fails
   - save is currently skipped after failed apply

**Artifacts / Evidence To Confirm In This Phase**:

- `import_result.json`
  Confirm base avatar import currently succeeds.
- `apply_result.json`
  Confirm measurement application currently fails and capture the exact failure.
- `save_outputs.json`
  Confirm save is skipped after failed apply in the current flow.
- `output.json`
  Confirm the current Step-1 artifact manifest is accurate.
- `run_summary.json`
  Confirm the recorded failing step is `step_08_apply_measurements`.

**Files To Review / Likely Touch In This Phase**:

- `clo_avatar_generation/run_avatar.py`
  Review how the Step-1 workflow is started and reported to the user.
- `clo_avatar_generation/avatar_runtime/pipeline.py`
  Review the current step order, failure behavior, and output manifest.
- `clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py`
  Review the current base-avatar import path.
- `clo_avatar_generation/avatar_runtime/step_08_apply_measurements.py`
  Review the current measurement-apply path.
- `clo_avatar_generation/avatar_runtime/step_11_save_outputs.py`
  Review the current save behavior and gating.
- `clo_avatar_generation/output/u_001-004/*`
  Use this run folder as the concrete artifact reference during the audit.
- `clo_workspace/windows/RestPlugin_windows.cpp`
  Review only the Windows plugin endpoints and command handlers relevant to
  import, apply, and save.

**Phase Exit Condition**:

- We can clearly state what Step-1 already does, what the plugin already
  supports, and what exact gap Phase 2 must solve.

### Phase 2: Make Measurement Application Work on the Loaded Avatar

**Goal**: Get one reliable path where the avatar loaded from `base-1.avt`
actually changes inside CLO from supplied measurement values.

**Steps**:

1. Keep the base avatar fixed to `clo_avatar_generation/input/base-1.avt` while
   debugging the first working path.
2. Use a temporary JSON measurement source that mirrors the current Mongo-style
   structure for `u_001`.
3. Treat that JSON file as the active schema-tuning surface for Step-1:
   - change the JSON shape as needed to match what CLO actually needs
   - compare the JSON shape against the CLO-facing bridge schema
   - iterate back and forth until the JSON and CLO schema relationship is
     stable
   - only after that, align Mongo usage to the finalized JSON shape
4. Keep the first implementation target small:
   - male only
   - first proven subset of measurements only
   - no women-avatar expansion yet
   - test one field at a time before combining fields
5. Tighten how Step-1 accepts the measurement input used for debugging so the
   apply behavior can be reproduced cleanly.
6. Refine the Step-1 field contract so the current supported fields, field
   order, and deferred fields are explicit.
7. Rework normalization and bridge generation so the payload sent to CLO is
   fully traceable from Mirra field to CLO field.
8. Improve apply-step diagnostics so the runtime records:
   - exact bridge artifact used
   - exact template path used
   - plugin response
   - native-debug evidence
9. If the runtime is correct but the plugin behavior is insufficient, change
   the Windows plugin only in the measurement-apply path.
10. Use a one-field-at-a-time progression:
   - start with one field
   - confirm that field applies successfully
   - move to the next field only after the previous one is proven
11. Stop Phase 2 only when one loaded avatar can be changed successfully.

**Artifacts To Produce / Verify In This Phase**:

- `clo_avatar_generation/input/u_001.measurements.json`
  Temporary JSON source file for schema iteration, initially close to the
  MongoDB structure for `u_001`.
- `input.json`
  Must record that the run used the JSON measurement source.
- `target_measurements.json`
  Must show the normalized field set selected from the JSON source and the
  currently active field filter.
- `clo_payload.json`
  Must describe the exact runtime payload strategy used for this apply attempt.
- `clo_payload.bridge.csv`
  Must contain the exact CLO-facing bridge data actually sent.
- `clo_payload_manifest.json`
  Must document bridge headers, values, and schema status.
- `apply_result.json`
  Must capture the request, debug evidence, final apply result, and which field
  was isolated for that run.

**Files To Change In This Phase**:

- `clo_avatar_generation/input/u_001.measurements.json`
  Add the first controlled JSON measurement fixture, shaped like the current
  `u_001` Mongo document and used for schema iteration.
- `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`
  Switch Step-1 to support the JSON-first measurement source for the current
  phase and preserve the JSON-to-CLO schema iteration loop.
- `clo_avatar_generation/schema/step1_field_contract.json`
  Define the first proven Step-1 measurement subset and keep the current
  male-only scope explicit.
- `clo_avatar_generation/avatar_runtime/field_contract.py`
  Add helpers so runtime field order and active scope come from the contract.
- `clo_avatar_generation/avatar_runtime/step_05_normalize_targets.py`
  Refine how Mirra fields map into CLO targets for the first working path and
  support one-field-at-a-time execution.
- `clo_avatar_generation/avatar_runtime/step_06_build_payloads.py`
  Rework the CLO bridge artifact and manifest so the runtime can prove exactly
  what was sent to CLO.
- `clo_avatar_generation/run_avatar.py`
  Add a way to run Phase-2 with one active field at a time.
- `clo_avatar_generation/avatar_runtime/client.py`
  Tighten plugin-call behavior and queue wait handling for import/apply testing.
- `clo_avatar_generation/avatar_runtime/step_08_apply_measurements.py`
  Improve the apply request path and the captured diagnostics.

**Conditional File In This Phase**:

- `clo_workspace/windows/RestPlugin_windows.cpp`
  Change only if the current Windows measurement-import behavior is the actual
  blocker after the runtime side is made clear.

**Phase Exit Condition**:

- One Step-1 run can load `base-1.avt` and successfully apply measurement
  values to the avatar already loaded in CLO.
- `apply_result.json.success` is `true`.
- `apply_result.json.request_result.success` is `true`.
- `apply_result.json.native_debug.measurement_import.success` is `true`.
- `run_summary.json` records `step_08_apply_measurements` as successful.
- The current run clearly records which isolated field was under test.

### Phase 3: Save the Modified Avatar as the Step-1 Output

**Goal**: After measurement application succeeds, save the modified avatar as
the reusable digital twin for that user.

**Steps**:

1. Start by storing **both** save formats for each successful Step-1 run:
   - `result_project.zprj`
   - `result_avatar.avt`
2. Use the initial save implementation to produce both artifacts even if the
   `.avt` comes from extraction rather than a direct plugin save endpoint.
3. Make the saved avatar output explicit in the runtime state and final output
   manifest.
4. Keep save gated behind successful measurement application.
5. If `.zprj` extraction is not sufficient, add a Windows plugin path for
   direct avatar-specific save/export.
6. Preserve both saved artifacts so they can be manually compared for:
   - file size
   - information completeness
   - suitability for long-term storage
7. Remove one of the two formats later only after manual review proves the
   other is sufficient.

**Artifacts To Produce / Verify In This Phase**:

- `save_outputs.json`
  Must record the save result and both saved artifact paths when successful.
- `result_project.zprj`
  Must exist after a successful save.
- `result_avatar.avt`
  Must exist after a successful save, whether by extraction or direct save.
- `output.json`
  Must expose both `saved_project` and `saved_avatar`.

**Files To Change In This Phase**:

- `clo_avatar_generation/avatar_runtime/step_11_save_outputs.py`
  Refine how save works, how extracted artifacts are handled, and how the final
  saved avatar is selected.
- `clo_avatar_generation/avatar_runtime/context.py`
  Track saved project path, saved avatar path, and save diagnostics explicitly.
- `clo_avatar_generation/avatar_runtime/pipeline.py`
  Surface the final saved-avatar state clearly in `run_summary.json` and
  `output.json`.

**Conditional File In This Phase**:

- `clo_workspace/windows/RestPlugin_windows.cpp`
  Change only if direct avatar save/export is needed beyond current `.zprj`
  export and extraction.

**Phase Exit Condition**:

- One Step-1 run can import the base avatar, apply measurements, and finish
  with a saved reusable avatar artifact.
- `save_outputs.json.save_result.success` is `true`.
- `result_project.zprj` exists in the run output.
- `result_avatar.avt` exists in the run output.
- `output.json.artifacts.saved_project` is not `null`.
- `output.json.artifacts.saved_avatar` is not `null`.

### Phase 4: Clean Up the Step-1 Run Folder Structure

**Goal**: Make Step-1 outputs easier to inspect so the run folder clearly shows
what happened at each stage.

**Steps**:

1. Keep the run identity format `<user_id>-<run_number>`, such as `u_001-004`.
2. Split the flat Step-1 artifact layout into clearer groups for:
   - input and run contract
   - source measurements
   - normalized measurements
   - CLO payloads
   - import/apply diagnostics
   - saved outputs
3. Keep standalone experiment reports separate from Step-1 run folders.
4. Update the Step-1 output manifest so it points clearly to the final saved
   avatar and related artifacts.
5. Update the runner output so the most important Step-1 artifact paths are easy
   to find after each run.

**Target Artifact Layout After This Phase**:

- `contract/input.json`
- `source/u_001.measurements.json`
- `measurements/target_measurements.json`
- `payloads/clo_payload.json`
- `payloads/clo_payload.bridge.csv`
- `payloads/clo_payload_manifest.json`
- `diagnostics/import_result.json`
- `diagnostics/apply_result.json`
- `diagnostics/readback_measurements.json`
- `diagnostics/error_report.json`
- `saved/save_outputs.json`
- `saved/result_project.zprj`
- `saved/result_avatar.avt`
- `run_summary.json`
- `output.json`

**Files To Change In This Phase**:

- `clo_avatar_generation/avatar_runtime/step_02_run_setup.py`
  Initialize the revised artifact layout.
- `clo_avatar_generation/avatar_runtime/context.py`
  Support clearer artifact grouping and artifact lookup.
- `clo_avatar_generation/avatar_runtime/pipeline.py`
  Update output-manifest writing to match the new layout.
- `clo_avatar_generation/avatar_runtime/run_manifest.py`
  Adjust run-folder helpers only if needed for the clearer layout.
- `clo_avatar_generation/run_avatar.py`
  Print the revised run outputs more clearly.

**Phase Exit Condition**:

- A Step-1 run folder is easy to inspect and clearly separates contract,
  payload, diagnostics, and final saved-output artifacts.
- `output.json` points to the grouped artifact locations instead of the current
  flat layout.

### Phase 5: Expand Beyond the First Working Male Path

**Goal**: Only after import, apply, and save are working, expand field coverage
and later support women avatars.

**Steps**:

1. Expand the male field set beyond the first proven subset.
2. Mark each field as:
   - proven
   - tentative
   - deferred
3. Add readback and error reporting only after the achieved-value source is
   trustworthy.
4. Add women-avatar support only after:
   - a supported female base avatar is defined
   - the field mappings are defined
   - the same import, apply, and save path is proven for that workflow
5. After the JSON shape is finalized through the JSON-to-CLO iteration loop,
   align Mongo usage to the same finalized structure.
6. Keep unsupported fields explicitly deferred instead of guessed.

**Files To Change In This Phase**:

- `clo_avatar_generation/schema/step1_field_contract.json`
  Expand supported fields in a controlled way and later add female scope.
- `clo_avatar_generation/avatar_runtime/field_contract.py`
  Support expanded and gender-specific field groups.
- `clo_avatar_generation/avatar_runtime/step_05_normalize_targets.py`
  Extend mappings only after the first working path is stable.
- `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`
  Switch from the temporary JSON-first path toward the finalized Mongo-backed
  shape once the JSON structure is stable.

**Conditional Files In This Phase**:

- `clo_avatar_generation/avatar_runtime/step_09_readback.py`
  Change only after there is a trustworthy achieved-value source.
- `clo_avatar_generation/avatar_runtime/step_10_compute_error.py`
  Change only after readback is real enough for requested-vs-achieved output.

**Phase Exit Condition**:

- The Step-1 system has a stable base workflow and can safely grow beyond the
  first working male digital-twin path.

## Dependencies

- CLO must be running with the Windows plugin from `clo_workspace/windows/`.
- The base avatar for this plan is `clo_avatar_generation/input/base-1.avt`.
- The first manual test case for this plan is:
  - base avatar: `clo_avatar_generation/input/base-1.avt`
  - measurement source: `clo_avatar_generation/input/u_001.measurements.json`
  - measurement identity: `u_001`
- The Step-1 runtime in `clo_avatar_generation/avatar_runtime/` remains the
  main implementation path.
- This plan depends on Windows plugin behavior only. The macOS plugin is
  intentionally out of scope here.
- If a new limitation or risky blocker is discovered during execution, it must
  be surfaced and approved before the plan is widened.

## Expected Outcomes

- A clear answer on whether the current Windows plugin already supports
  applying measurements to a loaded avatar and where it currently fails.
- A clear answer on whether direct avatar save support must be added to the
  Windows plugin.
- One working Step-1 path where a base avatar is imported, changed, and saved.
- Both `result_project.zprj` and `result_avatar.avt` are produced for manual
  comparison before one storage format is chosen.
- A cleaner Step-1 run folder that is easier to inspect than the current flat
  `u_001-004` layout.
- A stable base for later field expansion and women-avatar support.

## Manual Verification Checklist

- Start CLO with the Windows plugin from `clo_workspace/windows/`.
- Run Step-1 against:
  - `clo_avatar_generation/input/base-1.avt`
  - `clo_avatar_generation/input/u_001.measurements.json`
- Confirm the avatar loads successfully into CLO.
- Confirm the avatar visibly changes after measurement application.
- Confirm the final result can be saved.
- Confirm both artifacts exist:
  - `result_project.zprj`
  - `result_avatar.avt`
- Manually compare both save formats for:
  - file size
  - completeness
  - suitability for storage
- Confirm the run folder clearly shows:
  - the input contract
  - the apply diagnostics
  - the final saved avatar/project artifacts
