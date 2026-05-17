# Plan 008: Isolate `clo_avatar_generation` From the Rest of the Repo

## Overview

This plan cleans the current `clo_avatar_generation/` lane and turns it into a self-contained pipeline.

The goal is simple:

1. `clo_avatar_generation/` should generate or load the CLO-based avatar.
2. It should use garment panels from `product_ingestion/output/.../panels/dxf`.
3. It should run the full virtual try-on flow from inside its own folder.
4. It may read inputs from other folders, but it should not require future code changes in those folders.

The target final command for this lane is:

```powershell
python -m clo_avatar_generation.run_clo_vto
```

This plan treats `clo_avatar_generation/` as its own removable product lane, not just a set of helpers around `vto/`.

---

## Main Decision

Instead of continuing to borrow runtime code from `vto/`, this plan will copy the required VTO pipeline files into `clo_avatar_generation/` and keep all further CLO-native logic there.

That means:

1. `clo_avatar_generation/` becomes the owner of its own VTO flow.
2. The current `vto/` flow remains available as the old baseline.
3. `clo_avatar_generation/` can still read:
   - the CLO avatar file it owns
   - the panel output from `product_ingestion/`
4. But it should not depend on future edits in `vto/`.

---

## Boundary Rules

These rules are the core of this plan.

1. From this point onward, no new code changes should be required in:
   - `vto/`
   - `avatar_generation/`
   - `product_ingestion/`
   - `mirra_measurements/`
2. `clo_avatar_generation/` may read files from those folders, but must own its own runtime logic.
3. The current plugin changes that already exist may stay as they are.
4. New work should avoid further cross-folder runtime changes unless absolutely blocked and separately approved.
5. Any VTO step that is needed for the CLO-native path should be copied into `clo_avatar_generation/` and maintained there.
6. The CLO-native lane must preserve the behavior of the useful fixes already made in the current step files.
7. The final active command for this lane should remain:
   - `python -m clo_avatar_generation.run_clo_vto`

Design implication:

- `clo_avatar_generation/` becomes an isolated execution lane with its own pipeline files, step files, runner, context, and helpers.

---

## Why This Plan Is Needed

Right now the CLO-native lane works, but it is still partially mixed with code from `vto/`.

Examples of the current mixing:

1. `run_vto_with_clo_avatar.py` uses helpers from `vto/clo_automation_steps/`
2. `native_vto_pipeline.py` reuses many existing VTO step modules
3. the CLO-native lane is therefore still coupled to the behavior of the old VTO folder

This is a problem because:

1. the folder is harder to understand
2. cleanup later becomes harder
3. future VTO changes can accidentally affect the CLO-native lane
4. the experimental lane is not truly self-contained

---

## Current Desired End State

After this plan is done, `clo_avatar_generation/` should contain:

1. avatar-side logic for CLO-native avatar use
2. copied and adjusted VTO pipeline code
3. its own context and client wrappers
4. its own step modules
5. its own reports and outputs
6. one stable entry command:
   - `python -m clo_avatar_generation.run_clo_vto`

The old `vto/` folder should remain untouched and usable as a separate baseline path.

---

## What `run_clo_vto` Should Mean After This Plan

The command:

```powershell
python -m clo_avatar_generation.run_clo_vto
```

should become the main entrypoint for the isolated CLO-native lane.

Its responsibility should be:

1. find or accept the CLO-native avatar file
2. optionally apply measurement data if available
3. read the latest or chosen garment panel directory from `product_ingestion/output`
4. run the copied local VTO steps from inside `clo_avatar_generation/`
5. write its report back into `clo_avatar_generation/output/`

This command should no longer be only the old comparison harness.

---

## What Must Be Copied From `vto/`

For this plan, Step 3 virtual try-on should stop depending on the live `vto/` runtime files.

The following kinds of files should be copied into `clo_avatar_generation/` in a new local VTO sub-structure:

1. runner or pipeline entry logic
2. context creation
3. REST client wrapper if needed
4. helper utilities
5. seam helpers
6. all step modules used by the CLO-native flow

The copied versions should then be edited only inside `clo_avatar_generation/`.

Important rule:

- the useful fixes already made for this lane must be preserved in the copied versions

Examples of behavior that must not be lost:

1. improved slot reading
2. slot fallback handling
3. arrangement debugging
4. native avatar import behavior
5. current seam and panel handling that already works

---

## Proposed Folder Shape

The exact names can be adjusted during coding, but the isolated structure should move toward something like:

```plain
clo_avatar_generation/
  README.md
  run_clo_avatar.py
  run_clo_vto.py
  resize_avatar.py
  native_vto/
    client.py
    context.py
    helpers.py
    seams.py
    pipeline.py
    step_01_health.py
    step_02_new_project.py
    step_03_import_avatar.py
    step_04_import_patterns.py
    step_05_verify_patterns.py
    step_06_read_edges_and_slots.py
    step_07_arrange_patterns.py
    step_08_apply_fabric.py
    step_09_create_seams.py
    step_10_simulate.py
    step_11_export_note.py
  adapters/
  schema/
  research/
  output/
  avt_templates/
```

This structure makes the ownership very clear:

1. avatar generation and resizing stay in this folder
2. native VTO runtime stays in this folder
3. output and reports stay in this folder

Additional cleanup rule for the top level:

1. keep the root of `clo_avatar_generation/` small and obvious
2. the root should contain only the active entry commands and a small number of supporting files
3. copied runtime code should move under `native_vto/`
4. non-runtime findings and phase material should move under `research/`

---

## Cleanup Decisions Locked By This Plan

The following cleanup decisions are part of this plan and should be treated as requirements.

### 1. Split the folder into clear zones

`clo_avatar_generation/` should be organized into three clear areas:

1. active runtime
   - example: `native_vto/`, `adapters/`, active runners
2. research/reference
   - use a `research/` folder
3. generated artifacts
   - `output/`
   - `avt_templates/` for reusable input avatar files

This is intended to make the folder readable without needing to remember which files are code and which are planning material.

### 2. Reduce runner confusion at the folder root

The root entrypoint story must be simplified.

After cleanup, the intended visible commands should be:

1. `run_clo_avatar.py`
2. `run_clo_vto.py`

Older or overlapping runner files should not remain presented as equally active entrypoints.

They should either:

1. become internal helpers
2. move under `research/` or another clearly non-primary area
3. or be retired later if no longer needed

### 3. Move non-runtime planning and investigation material into `research/`

Files that are mainly research, planning, comparison, or schema investigation should not stay mixed into the runtime root.

This includes things like:

1. phase notes
2. mapping notes
3. measurement inventory research
4. role-decision or comparison helpers if they are not part of the active command path

This plan prefers the folder name:

- `research/`

instead of continuing to grow `reference_docs/` as the main non-runtime bucket.

### 4. Separate reusable avatar inputs from generated outputs

Reusable avatar template assets should not stay mixed together with generated reports and temporary CSV outputs.

The cleanup direction is:

1. keep reusable `.avt` inputs under `avt_templates/`
2. keep generated reports and temporary measurement files under `output/`

This will make the folder easier to scan and will clarify which files are:

1. stable inputs
2. generated artifacts

### 5. Use the folder README to explain the active flow

Instead of creating a separate flow note file, the root README of `clo_avatar_generation/` should clearly document:

1. the main command
2. required inputs
3. output location
4. which files or subfolders are part of the active runtime
5. which areas are research-only

This keeps the “how to use this folder” explanation in the most obvious place.

---

## What The New Isolated Lane Will Still Read From Other Folders

This plan still allows input reading from other repo folders.

That includes:

1. garment panel outputs from:
   - `product_ingestion/output/.../panels/dxf`
2. optional garment metadata if needed later
3. the already-built REST plugin endpoints

This is acceptable because those are inputs and boundaries, not runtime code dependencies.

---

## What Should Stop Happening

After this plan is done, the CLO-native lane should no longer:

1. import step modules from `vto/clo_automation_steps/`
2. import helper functions from `vto/`
3. rely on `vto/run_vto.py`
4. require edits in `vto/` whenever the CLO-native lane changes

---

## Phase Plan

## Phase 1: Audit and Freeze the Current Working Behavior

**Goal**: identify exactly what current behavior must be preserved before copying files.

**Steps**:

1. List the current active CLO-native run path:
   - `run_vto_with_clo_avatar.py`
   - `native_vto_pipeline.py`
   - native avatar import step
   - native slot-reading wrapper
2. List every dependency pulled from `vto/`.
3. Record which fixes must survive the move.
4. Mark older scaffold files that are not part of the active runtime.

**Deliverable**:

- one clear dependency map of the current mixed flow

---

## Phase 2: Create a Local Native VTO Runtime Inside `clo_avatar_generation/`

**Goal**: establish a copied local VTO runtime owned entirely by `clo_avatar_generation/`.

**Steps**:

1. Create a new subfolder for the copied VTO runtime.
2. Copy the required VTO files from `vto/clo_automation_steps/`.
3. Rename or reorganize them only inside the new folder.
4. Update imports so the copied files only refer to local siblings or approved input boundaries.

**Deliverable**:

- a local native VTO runtime tree inside `clo_avatar_generation/`

---

## Phase 3: Merge The Existing CLO-Native Fixes Into The Copied Runtime

**Goal**: preserve the current working CLO-native behavior in the new copied step files.

**Steps**:

1. Move the current native avatar import logic into the copied Step 3.
2. Move the current native slot/debug logic into the copied Step 6.
3. Preserve the slot fallback behavior that currently keeps the flow usable.
4. Preserve the seam and arrangement fixes already present in the current path.
5. Ensure the copied runtime can still work with the current plugin endpoints.

**Deliverable**:

- copied step files that behave like the current working native lane

---

## Phase 4: Rewrite `run_clo_vto.py` To Be The Main Isolated Command

**Goal**: make `run_clo_vto.py` the real main runner for this lane.

**Steps**:

1. Replace the old comparison-only behavior in `run_clo_vto.py`.
2. Make it:
   - locate the CLO avatar
   - locate or accept garment panels
   - call the copied local pipeline
   - write reports to `clo_avatar_generation/output/`
3. Keep the interface simple for repeated testing.

**Target command**:

```powershell
python -m clo_avatar_generation.run_clo_vto
```

**Deliverable**:

- one stable main command for the isolated lane

---

## Phase 5: Keep `run_clo_avatar.py` As The Avatar-Side Entry

**Goal**: keep the avatar-side command separate from the full VTO command.

**Steps**:

1. Decide whether `run_clo_avatar.py` remains:
   - a setup command
   - a template-resolution command
   - or a direct avatar-preparation command
2. Keep it focused on the avatar side only.
3. Do not overload it with full VTO responsibility.

**Deliverable**:

- clean separation between avatar prep and full try-on run

---

## Phase 6: Clean The Folder And Mark Archiveable Files

**Goal**: make the folder understandable once the isolated runtime exists.

**Steps**:

1. Group files into:
   - active runtime
   - research/reference
   - older scaffold/archive candidates
2. Identify files that are not part of the new active command path.
3. Move archiveable files into a clearly named archive or legacy area if desired.
4. Keep runtime outputs and cache files out of the conceptual source structure.

**Deliverable**:

- one clean active path
- one clear list of non-runtime or archiveable files

---

## Phase 7: Verify Isolation

**Goal**: prove that the CLO-native lane no longer depends on `vto/` runtime code.

**Checks**:

1. `run_clo_vto.py` should execute without importing `vto/clo_automation_steps/...`
2. the local copied step files should handle:
   - native avatar import
   - pattern import
   - slot resolution
   - arrangement
   - seam creation
   - simulation
3. the lane should still read garment inputs from `product_ingestion/output`
4. no new code changes should be needed in `vto/`

**Deliverable**:

- isolated CLO-native lane confirmed

---

## Expected Benefits

If this plan is completed well, we get:

1. a cleaner mental model
2. easier deletion later if needed
3. less accidental breakage from `vto/` changes
4. one obvious command for the CLO-native lane
5. a proper experimental lane instead of a mixed dependency chain

---

## Main Risks

1. Copying VTO files may create temporary duplication.
2. Bug fixes made later in `vto/` will not automatically reach the copied native lane.
3. If we copy too early without auditing, we may freeze accidental problems into the new lane.
4. The folder may still contain older scaffolding after the main command becomes isolated.

These are acceptable risks because the goal here is isolation, not maximum deduplication.

---

## Success Definition

This plan is successful when:

1. the command
   - `python -m clo_avatar_generation.run_clo_vto`
   runs the CLO-native lane
2. the lane uses a CLO-based avatar from this folder
3. the lane uses garment outputs from `product_ingestion/output`
4. the lane no longer imports runtime logic from `vto/`
5. no further code changes are needed in other repo folders for the CLO-native lane to evolve

---

## Immediate First Slice

The first coding slice for this plan should be:

1. audit the current active CLO-native path
2. create `clo_avatar_generation/native_vto/`
3. copy the required files from `vto/clo_automation_steps/`
4. merge the native Step 3 and Step 6 behavior there
5. repoint `run_clo_vto.py` to the copied local pipeline

That is the smallest move that creates real isolation without trying to redesign everything at once.
