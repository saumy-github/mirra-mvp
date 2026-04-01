# 009 Plan: CLO Avatar Step-1 Generation Workflow

## Purpose

Create a new Step-1-style workflow inside `clo_avatar_generation/` that behaves
like the existing Mirra pipelines:

1. it starts from a user id
2. it creates a numbered run folder
3. it saves clear run artifacts
4. it records step success/failure cleanly
5. it can be rerun and debugged easily

This workflow is not the VTO workflow. Its job is to generate or resize a
CLO-native avatar from a fixed base avatar using user measurements.

The current target is:

1. male only
2. one locked base avatar template at first
3. no focus yet on head simplification, hand details below wrist, feet below
   ankle, or crotch realism work

## Core Decision Already Locked

The Step-1 CLO workflow should use this high-level direction:

1. load one fixed base CLO avatar first
2. send user-specific measurement data to CLO
3. let CLO resize the loaded base avatar
4. read back the result
5. save the resized avatar and error artifacts

This means the primary workflow is:

`base avatar -> measurement payload -> CLO resize -> error report -> saved user run`

not:

`build a finished custom avatar outside CLO first -> import finished avatar every time`

## Existing Pipeline Patterns To Mirror

### From `avatar_generation`

The new workflow should mirror these patterns:

1. interactive CLI runner
2. user id selection from MongoDB
3. per-user run numbering using `<user_id>-<run_number>`
4. run folder creation before heavy work begins
5. saved artifacts like:
   - `input.json`
   - `output.json`
   - other run-specific files
6. `KeyboardInterrupt` handling with clean exit code `130`

### From `vto`

The new workflow should mirror these patterns:

1. step-by-step execution
2. step success/failure recording
3. early stop on failed gate
4. writing `run_summary.json`
5. prompt defaults where pressing Enter chooses the latest available run or
   the recommended default

## Target Folder Ownership

All new runtime code for this workflow should stay inside `clo_avatar_generation/`.

It may read from:

1. MongoDB through the same measurement access pattern already used in
   `avatar_generation`
2. fixed local CLO avatar templates
3. existing plugin endpoints

It should not require new runtime edits in:

1. `avatar_generation/`
2. `vto/`
3. `product_ingestion/`

## Target Run Command

The official interactive runner for this workflow is locked as:

`python -m clo_avatar_generation.run_avatar`

This should behave similarly to:

1. `avatar_generation/run_avatar.py`
2. `vto/run_vto.py`

Working plan:

1. a root runner under `clo_avatar_generation/`
2. a modular step pipeline under a dedicated subfolder

## Target Run Folder Rule

Because `clo_avatar_generation/output` was renamed, the run artifacts for this
workflow should live under:

`clo_avatar_generation/research_files/`

The run folder naming should follow the same per-user numbering style as
`avatar_generation`:

`<user_id>-<run_number>`

Example:

`u_001-001`

## Expected Artifacts Per Run

Each run should create and preserve enough data to debug the full measurement
application path.

Minimum artifacts:

1. `input.json`
   - the runner inputs
   - selected base avatar
   - run metadata
2. `mongo_snapshot.json`
   - raw or cleaned user measurements fetched for this run
3. `target_measurements.json`
   - the normalized measurement values the workflow intends to apply
4. `clo_payload.*`
   - the exact file or files prepared for CLO
5. `apply_result.json`
   - result of sending data to CLO
6. `readback_measurements.json`
   - resulting values read back from CLO or derived from saved artifacts
7. `error_report.json`
   - requested vs achieved values and per-field error
8. `output.json`
   - final top-level run result summary
9. `run_summary.json`
   - step-by-step status summary
10. saved avatar artifacts
   - at minimum `.avt`
   - preferably `.avs`
   - optionally `.arr`, `.iks`, `.mea` if they are useful in the same run

## Proposed Workflow Steps

### Step 1: Health Check

Goal:

1. confirm CLO plugin is reachable
2. confirm required native-avatar capabilities exist

Checks:

1. `/health`
2. `/capabilities`

Failure behavior:

1. stop immediately
2. write failed `run_summary.json`

### Step 2: Resolve Run Identity

Goal:

1. choose user id
2. determine next run number
3. create the run folder

Behavior:

1. fetch user document from MongoDB using the same approach as
   `avatar_generation`
2. if previous runs exist for that user, next number should auto-increment
3. pressing Enter should accept the default/recommended values

### Step 3: Fetch Measurement Source

Goal:

1. fetch user measurements from MongoDB
2. save a local snapshot for reproducibility

Artifacts:

1. `mongo_snapshot.json`

Notes:

1. after fetch, the pipeline should work from local saved data
2. this makes reruns reproducible

### Step 4: Resolve Base Avatar

Goal:

1. choose the fixed base male avatar template for the run

Behavior:

1. default to one locked base `.avt`
2. pressing Enter should select the current default base avatar
3. base avatar choice must be recorded in `input.json`

Locked default for coding:

1. `clo_avatar_generation/input/base-1.avt`

Candidate saved artifacts to keep with the base avatar:

1. `.avt`
2. `.arr`
3. `.iks`
4. optional baseline `.avs`

### Step 5: Normalize Measurement Targets

Goal:

1. convert Mirra user data into the set of fields we want CLO to follow

Artifacts:

1. `target_measurements.json`

This file should contain:

1. width driver and value
2. height driver and value
3. detailed body fields
4. ignored fields explicitly marked as ignored or out of scope
5. unit = `cm`
6. values rounded to 2 decimal places before sending to CLO

The normalization layer should also decide:

1. which user values are direct
2. which values are derived
3. which values are intentionally not sent yet

The first version should keep all outgoing numeric body values in:

1. centimeters
2. rounded to 2 decimal places

### Step 6: Build CLO Payloads

Goal:

1. build the machine-readable payload that CLO will consume
2. build a human-readable payload that Mirra can inspect

Artifacts:

1. human-readable JSON payload
2. CLO-facing payload file

Locked direction:

1. human-readable run payload should stay as JSON
2. the preferred CLO-facing payload should be an avatar size file path or
   avatar-size-oriented bridge based on `.avs`

Implementation note:

1. do not plan around CSV as the primary product contract
2. if direct `.avs` application is not possible through the plugin/SDK, then an
   internal bridge format may be introduced later, but the human-readable run
   contract should remain JSON-first

This step must preserve the exact file sent to CLO for each run.

This step should also read from one central field-definition source so the list
of values sent to CLO is defined in one place for both humans and code.

### Step 7: Load Base Avatar Into CLO

Goal:

1. open a fresh CLO project
2. import the chosen base `.avt`

Behavior:

1. use the existing native avatar plugin route
2. verify import success before attempting measurement application

### Step 8: Apply Measurements

Goal:

1. send the measurement payload to CLO
2. resize the loaded base avatar

Behavior:

1. use the plugin route we decide to standardize
2. record both request payload and API/plugin result

Current plan note:

1. assume the first implementation attempts to apply all target values together
2. if CLO behavior later proves sensitive to the order of value application,
   then ordering rules will be decided at that point

Artifacts:

1. `apply_result.json`

### Step 9: Read Back Result

Goal:

1. capture the resulting avatar state after CLO applies the size changes

Possible readback sources:

1. plugin/API readback if it can be implemented
2. saved resulting `.avs`
3. saved resulting `.avt`
4. manually decoded or derived size snapshot if needed

Artifacts:

1. `readback_measurements.json`

### Step 10: Compute Error

Goal:

1. compare requested values against resulting values

Artifacts:

1. `error_report.json`

The report should separate:

1. measurement error
2. skipped fields
3. unsupported fields
4. pipeline/application failures

Preferred strategy:

1. compute error through plugin/API readback if possible
2. if not possible, save `.avs` and `.avt`, then derive error from those saved
   outputs and write the result into `error_report.json`

### Step 11: Save Avatar Outputs

Goal:

1. persist the resulting avatar for later VTO use

Target saved outputs:

1. resized `.avt`
2. resized `.avs`
3. optional `.arr`
4. optional `.iks`

### Step 12: Finalize Run Summary

Goal:

1. write final top-level outputs
2. record completed or failed status

Artifacts:

1. `output.json`
2. `run_summary.json`

## Pipeline Structure To Implement

Recommended structure:

1. one interactive runner at `clo_avatar_generation/`
2. one dedicated modular workflow package, similar to `vto/clo_automation_steps`
3. one central schema/config file that defines which values are sent to CLO

Suggested internal layout:

1. `clo_avatar_generation/avatar_runtime/`
2. `clo_avatar_generation/avatar_runtime/context.py`
3. `clo_avatar_generation/avatar_runtime/pipeline.py`
4. `clo_avatar_generation/schema/step1_field_contract.json`
4. step modules:
   - `step_01_health.py`
   - `step_02_run_setup.py`
   - `step_03_fetch_measurements.py`
   - `step_04_resolve_base_avatar.py`
   - `step_05_normalize_targets.py`
   - `step_06_build_payloads.py`
   - `step_07_import_base_avatar.py`
   - `step_08_apply_measurements.py`
   - `step_09_readback.py`
   - `step_10_compute_error.py`
   - `step_11_save_outputs.py`

## Step Success / Failure Rules

The workflow should follow the same discipline as the normal VTO pipeline:

1. each step returns success or failure
2. each step result is appended to `run_summary.json`
3. if a required step fails, the pipeline stops
4. the final run status is either:
   - `initialized`
   - `completed`
   - `failed`
5. exception text should be preserved when possible

## CLI Behavior Rules

The runner should behave like the other Mirra pipelines:

1. prompt for `user_id`
2. fetch and validate that user from MongoDB
3. auto-detect next run number
4. pressing Enter accepts the default value
5. where an existing run/template must be selected, pressing Enter should
   choose the latest or the current default
6. support `KeyboardInterrupt`
7. on interrupt, exit cleanly with code `130`

Default choices:

1. pressing Enter should accept the latest run where relevant
2. pressing Enter should accept the locked base avatar where relevant

## Out-Of-Scope For This First Version

These should not block the first working version:

1. female workflow
2. exact head/face fidelity logic
3. hands below wrist
4. feet below ankle
5. crotch realism work
6. long-term caching strategy for many avatar families

## Phase Plan

### Phase 1: Runner And Run Folder Scaffolding

Build:

1. interactive runner
2. user id selection
3. next run number logic
4. `research_files/<user_id>-<run_number>/`
5. `input.json`
6. `run_summary.json`

### Phase 2: Mongo Fetch And Measurement Snapshot

Build:

1. Mongo fetch using the same pattern as `avatar_generation`
2. local saved measurement snapshot
3. normalized target skeleton JSON

### Phase 3: Base Avatar Resolution

Build:

1. fixed male base avatar selection
2. storage of base asset metadata in the run
3. import step wiring to CLO
4. use `clo_avatar_generation/input/base-1.avt` as the initial coding target

### Phase 4: Payload Builder

Build:

1. human-readable payload JSON
2. CLO-facing payload file
3. artifact saving for both
4. central field-definition file hookup

### Phase 5: Measurement Application

Build:

1. send payload through the plugin
2. capture apply result
3. stop cleanly if apply fails

### Phase 6: Readback And Error Analysis

Build:

1. read back resulting state
2. compare requested vs achieved values
3. write error report

### Phase 7: Save Final Avatar Outputs

Build:

1. save resulting `.avt`
2. save resulting `.avs`
3. optional companion files
4. finalize `output.json`

## Current Locked Decisions

These are now decided for implementation:

1. official entrypoint:
   `python -m clo_avatar_generation.run_avatar`
2. fixed male base avatar:
   `clo_avatar_generation/input/base-1.avt`
3. human-readable run contract:
   JSON
4. preferred CLO-facing direction:
   `.avs`-oriented size application path
5. output values should be stored and prepared in:
   centimeters
6. values sent to CLO should be rounded to:
   2 decimal places
7. preferred error strategy:
   plugin/API readback first, saved `.avs` / `.avt` fallback

## Remaining Decision Gates

These still need to be finalized during implementation:

1. the exact plugin/API route used to apply `.avs`-oriented size changes
2. the exact readback implementation for resulting avatar values
3. the final version-1 field list to send to CLO
4. whether any internal fallback bridge is required if direct `.avs` application
   is not possible
