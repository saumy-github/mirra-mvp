
# Plan 005: Code Structure Cleanup and Output Standardization

## Overview

Clean the codebase structure across the MVP without adding new functionality and without fixing the currently known product or pipeline problems. The purpose of this plan is to make the repository easier to understand, maintain, and extend later.

This plan will be built incrementally as we discuss each MVP step. Based on the decisions confirmed so far, the first locked area is **Step 1: avatar generation output structure cleanup**.

## Execution Warnings

1. Step 1 path and artifact migration must be done atomically. Renaming `pipeline_star`, moving from `generated/` to `output/`, changing run-folder structure, and changing artifact filenames cannot be rolled out partially without breaking current writers, run discovery, and downstream consumers.
2. Step 2 input-source cleanup must be done atomically. Avatar-driven and manual measurement paths must not be deleted until the MongoDB-only `size_id` flow fully replaces them in the active Step 2 runner and all downstream consumers are updated.
3. Step 2 and Step 3 path-contract cleanup must be done atomically. The current producer and consumer still disagree on where DXF outputs live, so partial rollout of the new folder structure can cause Step 3 to consume an older run or fail to find Step 2 outputs.
4. Step 3 path migration must be done atomically. The current CLO automation code still points to old Step 1 and Step 2 locations, so the `vto` split and new output contracts must be wired together before the old assumptions are removed.
5. Legacy commands and helper scripts must not be deleted early. They can only be removed after the full Step 1 to Step 3 virtual try-on flow is manually verified by the user under the cleaned structure.

## Recommended Execution Order

1. Execute Phase 1 first as one atomic Step 1 migration: rename the Step 1 folder, switch `generated/` to `output/`, update Step 1 run/artifact contracts, and update current downstream consumers of Step 1 artifacts in the same rollout.
2. Stop for Manual Verification Gate 1: the user manually runs and verifies the cleaned Step 1 pipeline before later cleanup continues.
3. Execute Phase 2 next so the database-facing size naming is cleaned before Step 2 active flows are rebuilt on top of it.
4. Execute Phase 3 after Phase 2 by first renaming the Step 2 folder and canonical runner, then switching the active Step 2 runner to the MongoDB-only `size_id` flow, then rolling out the new Step 2 output contract together with the Step 3 path resolver update, and only later retiring legacy overlap commands after manual verification.
5. Stop for Manual Verification Gate 2: the user manually runs and verifies the cleaned Step 2 pipeline as a standalone MVP step before Step 3 cleanup is finalized.
6. Execute Phase 4 after the Step 2 contract is stable by creating `vto/run_vto.py`, moving user-facing orchestration out of `clo_workspace`, and updating Step 3 runtime paths in the same migration slice.
7. Stop for Manual Verification Gate 3: the user manually runs and verifies the cleaned Step 3 flow using cleaned Step 1 and Step 2 outputs as inputs.
8. Execute Phase 5 last: retire or archive validated legacy commands, then clean repo docs, config leftovers, and shared-structure details so documentation reflects the final verified state.

## Confirmed Decisions So Far

1. This plan is a **code structure cleanup only** plan.
2. No new functionality will be added.
3. Existing known problems will remain as-is unless a cleanup change requires a path or reference update.
4. Zero-padded run numbers will be used everywhere in the repo whenever runs are created.
5. Step 1 database user IDs will move from `user_...` style to `u_...` style, and Step 1 output naming will follow that new format.
6. Step 1 codebase folder will be renamed from `pipeline_star` to `avatar_generation`.
7. Step 1 run folders will live directly under `avatar_generation/output/`.
8. All downstream consumers will be updated to use the new `output` path only.
9. The codebase may assume the database is already migrated to the new `u_...` user ID format.
10. The Step 2 pipeline folder will be renamed from `2d_patterned_garment_generation_clo3d` to `product_ingestion`.
11. The Step 2 garment identifier concept will be renamed to `size_id`.
12. Step 2 size IDs will use the new `s_...` format.
13. The database and `mirra_measurements` layer will be cleaned immediately after Step 1 so the rest of the repo can build on the renamed size model.
14. Existing generated files from the old system must not be deleted until the full Step 1 to Step 3 MVP flow is manually verified by the user.
15. Step 2 will not take cloth size or cloth metadata from avatar files, avatar database records, or avatar-derived inputs.
16. Step 2 will take cloth size and cloth metadata only from MongoDB.
17. The main Step 3 virtual try-on application code will move into a new `vto` folder.
18. `clo_workspace` will remain focused on the REST server and CLO3D connection/integration layer only.
19. The app-level term for flat 2D sewing pieces will be changed from `pattern` to `panel`.
20. CLO-native `pattern` terminology will be preserved only where it directly matches the CLO SDK or REST boundary.
21. Step 2 should prefer renaming its main user-facing runner to `run_product_ingestion.py` when the Step 2 folder is renamed to `product_ingestion`.
22. Step 3 should not only rename a file inside `clo_workspace`; instead, it should create `vto/run_vto.py` during the Step 3 split.
23. One-time or maintenance scripts should move into a dedicated `scripts/` folder inside the relevant step folder unless they remain the main user-facing runner.
24. Test and diagnostic helpers should move into a dedicated `tests/` folder inside the relevant step folder.
25. Obsolete planning or scratch markdown files that are not part of active docs should be removed during cleanup, including `A_POSE_CONVERSION_PLAN.md`.
26. Legacy scripts, legacy code paths, and legacy markdown/docs that are no longer needed should be deleted only after the full Step 1 to Step 3 virtual try-on flow is manually verified by the user.
27. Repo-wide cleanup of `README.md`, `SETUP.md`, and other markdown docs should happen after the legacy-code deletion phase so the documentation reflects the final cleaned structure.
28. The `libs/` folder should contain only submodule pointers or external repositories.
29. The `models/` folder should contain heavy model assets and tool model files only.
30. Shared reusable helper code that can be used across multiple steps should live in `utils/`.
31. The `config/` folder should be deleted if it is not needed, or moved under the CLO integration area if its remaining contents are CLO-specific.
32. The Step 2 producer command and the Step 3 CLO consumer command should remain separate commands. They are sequential pipeline stages with shared file contracts, not one duplicated command.
33. The canonical Step 2 user command should be the renamed root orchestrator `run_product_ingestion.py`.
34. `generate_for_avatar.py` should be treated as a legacy Step 2 overlap command to retire later after manual verification of the cleaned flow.
35. `generate_patterns_clo3d.py` may remain temporarily as a lower-level Stage B helper during transition, but it should not remain the primary user-facing Step 2 command.
36. The canonical Step 3 user command after the split should be `vto/run_vto.py`.
37. `mirra_pattern_importer.py` should be treated as an experimental alternate Step 3 approach to archive or retire later unless the team explicitly decides to keep it for non-primary experimentation.
38. Step 1 and Step 2 are independent MVP steps and should be treated as separate standalone pipelines during manual verification.
39. Step 3 is the first stage that depends on both earlier MVP steps together: it consumes Step 1 avatar output and Step 2 panel DXF output as inputs.
40. Step 1 root runner should be renamed from `run_avatar_pipeline.py` to `run_avatar.py`.
41. Step 3 should not use a dedicated `input/` folder for now; it should select already-generated Step 1 and Step 2 outputs directly.
42. `vto/run_vto.py` should support both behaviors for selecting Step 1 and Step 2 source runs: use the latest available run by default, or let the user explicitly provide the desired run numbers.
43. Step 3 output folder names should include both selected source runs plus a VTO rerun number so rerunning the same avatar-plus-product combination does not collide with previous Step 3 runs.
44. The locked Step 3 output folder naming format should be `<avatar_run>__<product_run>__<vto_run_number>`.
45. Example Step 3 output folder name: `u_001-001__c_001-s_001-001__001`.
46. Every Step 3 run folder should include a structured JSON file describing the selected avatar run, selected Step 2 run, and any relevant run-selection metadata.
47. The CLO REST server and plugin contract must remain stable during this cleanup. Moving the user-facing Step 3 runner into `vto/` must not break the current REST server startup flow, port usage, queue-drain behavior, or supported plugin endpoints.
48. Step 3 cleanup should move orchestration responsibility out of `clo_workspace`, but should not change the fundamental role of `RestPlugin.cpp`, the REST queue architecture, or the plugin-side endpoint contract unless a separate later discussion explicitly approves it.

## Phases

### Phase 1: Step 1 Output Structure Cleanup

**Goal**: Standardize Step 1 avatar pipeline outputs so each run is self-contained, easier to inspect, and easier for Step 2 and Step 3 to consume later.

**Execution order inside this phase**: rename the Step 1 folder and output contract first, update current readers of Step 1 artifacts in the same rollout, then clean supporting scripts and docs.

**Steps**:

1. Rename the Step 1 codebase folder from `pipeline_star` to `avatar_generation` and rename the Step 1 root output directory from `generated` to `output`.
2. Update all Step 1 internal and downstream path references to use `avatar_generation/output/` instead of `pipeline_star/generated/`.
3. Change Step 1 run discovery logic to use zero-padded run numbers only.
4. Change the Step 1 run folder naming format to `<user_id>-<run_number>`.
5. Use the new Step 1 run folder pattern like `u_001-001`, `u_001-002`, and so on.
6. Add or preserve a code comment documenting the run folder naming formula as `<user_id>-<run number>`.
7. Store each Step 1 run in its own self-contained folder so it is immediately clear which user the run belongs to and which generation number it is.
8. Flatten the Step 1 run contents so all current run artifacts sit directly inside the run folder.
9. Rename the Step 1 inputs artifact file to `input.json`.
10. Rename the Step 1 values artifact file to `output.json`.
11. Rename the Step 1 GLB artifact file to `avatar.glb`.
12. Keep the Step 1 OBJ artifact for now and rename it to `avatar.obj`.
13. Keep the Step 1 measurement handoff JSON for now and rename it to `measurements.json`.
14. Remove the human-readable `.txt` export file from the Step 1 run outputs.
15. Update Step 2 and Step 3 references that consume Step 1 artifacts so they point to the new Step 1 output structure and filenames only.
16. Keep `measurements.json` for now, but note it as a candidate for future removal if later confirmation shows it is not needed.
17. Update measurement seed data, golden-user references, and related examples/docs to use the new `u_...` user ID format.
18. Keep `run_avatar.py` as the root entrypoint of the Step 1 folder after the folder is renamed to `avatar_generation`.
19. Move one-time or maintenance scripts such as output-clearing helpers into `avatar_generation/scripts/` if they are still needed after cleanup.
20. Move Step 1 test and diagnostic helpers such as shoulder-diagnosis scripts into `avatar_generation/tests/`.
21. Remove `A_POSE_CONVERSION_PLAN.md` from Step 1 during the legacy cleanup phase.

**Expected Step 1 Run Structure**:

```plain
avatar_generation/output/
  u_001-001/
    input.json
    output.json
    avatar.glb
    avatar.obj
    measurements.json
```

### Phase 2: Database and `mirra_measurements` Cleanup

**Goal**: Clean the database-facing naming and support layer so the repo consistently uses `size` terminology instead of `garment` terminology before Step 2 and Step 3 structural cleanup continues.

**Steps**:

1. Rename the garments model concept to the size model throughout the database support layer.
2. Rename `garment_model.py` to `size_model.py`.
3. Rename `seed_garments.py` to `seed_sizes.py`.
4. Update imports, helper names, script names, and references everywhere so they use `size` terminology consistently.
5. Replace database field naming from `garment_id` to `size_id`.
6. Update stored ID values from legacy naming to `s_001`, `s_002`, and so on.
7. Keep `garment_length_cm` as-is and do not rename that measurement field.
8. Update the database collection naming and access layer so the repo has a dedicated `sizes` section using the cleaned size schema.
9. Update README files, examples, prompts, and seed scripts so they match the renamed size model and `size_id` field.
10. Update all Step 2 and Step 3 code that reads from the old garments naming so it consumes the cleaned size naming instead.
11. Update app-level docs and examples to align later terminology changes from `pattern` to `panel` wherever they refer to flat sewing pieces rather than database fields or CLO-native APIs.

### Manual Verification Gate 1: Step 1

**Goal**: Pause after the cleaned Step 1 migration so the user can manually run and verify Step 1 as a standalone MVP step before later cleanup continues.

**Checks**:

1. Run the cleaned Step 1 pipeline manually.
2. Confirm the cleaned Step 1 command and folder rename work in practice.
3. Confirm the new Step 1 output folder structure and filenames are correct.
4. Confirm the cleaned Step 1 run can be inspected without relying on old `generated/` layout assumptions.
5. Do not delete Step 1 legacy helpers or docs that are still needed until this manual check passes.

### Phase 3: Step 2 Structural Cleanup

**Goal**: Reorganize Step 2 into a clearer pipeline structure with corrected stage ordering, clearer naming, and a self-contained run-folder layout.

**Execution order inside this phase**: rename the Step 2 folder and canonical runner first, make the active runner use MongoDB-only `size_id` sourcing next, roll out the new output contract together with Step 3 resolver updates, and only then retire legacy overlap commands after manual verification.

**Steps**:

1. Apply the finalized Step 2 cleanup decisions by renaming the Step 2 folder to `product_ingestion` and preferring the renamed canonical runner `run_product_ingestion.py`.
2. Correct the documented and implemented Step 2 processing order so it consistently follows:
   - view selection
   - segmentation
   - colour extraction
   - design extraction
3. Split the four Step 2 image-processing stages into four separate files, one file per process.
4. Separate DXF generation and SVG generation into different dedicated files.
5. Consolidate the panel-generation helpers into one single panel-generation file instead of keeping them scattered across multiple generation files.
6. Update Step 2 input handling so the input root contains cloth folders like `c_001`, `c_002`, where each folder contains multiple images of a single cloth item.
7. Use `size_id` consistently across Step 2 after the database cleanup phase.
8. Make MongoDB the only active source of Step 2 cloth size and cloth metadata in the canonical Step 2 runner.
9. After the MongoDB-only flow is working in the active Step 2 runner, remove all Step 2 code paths that calculate or derive size data from avatar JSON files, avatar output files, avatar measurement documents, or manual avatar-measurement input.
10. After the active runner no longer depends on them, remove Step 2 scripts, flags, helper classes, prompts, and README examples that exist only to build patterns from avatar measurements.
11. Rename app-level Step 2 references from `pattern` to `panel` wherever they refer to flat 2D sewing pieces, generated garment pieces, or their output bundles.
12. Use singular `panel` and plural `panels` according to context instead of applying one blanket rename everywhere.
13. Keep CLO-facing `pattern` terms only at the thin integration boundary where Step 2 must match CLO SDK or REST concepts.
14. Apply the Step 2 terminology change in a safe order so internal app naming is cleaned first and any CLO-facing adapter names are updated last, avoiding pipeline breakage during the transition.
15. Standardize Step 2 run folder naming to `<cloth_id>-<size_id>-<run_number>`.
16. Use zero-padded run numbers for Step 2 run folders, for example `c_001-s_001-001`.
17. Make the Step 2 run number increment per `cloth_id + size_id` pair.
18. Create the new Step 2 run folder directly under `product_ingestion/output/` using the finalized layout before removing any legacy writers.
19. Keep the Step 2 run folder internally split into two top-level sections only: `image_info/` and `panels/`.
20. Keep `image_info/` flat and write the image-derived artifacts directly into that folder instead of creating per-stage subfolders.
21. Preserve the current useful Step 2 image-derived artifacts inside `image_info/`, including `base_garment.png`, `colors.json`, `extraction_metadata.json`, and `graphic_diffuse.png`.
22. Store generated flat-piece outputs under `panels/`.
23. Keep DXF outputs under `panels/dxf/`.
24. Keep SVG outputs under `panels/svg/`.
25. Rename `pattern_metadata.json` to `panel_metadata.json` at the app layer and store it directly under `panels/`.
26. Rename `pipeline_result.json` to `run_summary.json` and store it at the Step 2 run-folder root.
27. Make the Step 2 write order match the actual pipeline flow so artifacts are created in sequence without location drift: image extraction outputs first, then panel outputs, then the run summary.
28. Fully remove the old nested Step 2 output structure such as `pipeline_run_001/.../run_001/...` only after the new structure is in place and verified through the new flow.
29. Update Step 2 prompts, CLI examples, DB examples, and documentation so they use `size_id`, the new `s_...` values, the new output paths, and the new `panel` terminology where applicable.
30. Preserve old generated outputs during the transition period and only delete them after the full Step 1 to Step 3 system is manually verified by the user.
31. Keep the main Step 2 user-facing runner at the root of the renamed `product_ingestion/` folder and prefer renaming the current root orchestrator to `run_product_ingestion.py`.
32. Move Step 2 one-time or maintenance scripts into `product_ingestion/scripts/` if they are still needed after cleanup.
33. Delete legacy Step 2 avatar-driven pattern-generation scripts, CLI flags, README examples, and code paths only after the full Step 1 to Step 3 system is manually verified by the user.
34. Treat `generate_for_avatar.py` as the clearest legacy-overlap Step 2 command to retire after manual verification because it depends on avatar-driven pattern generation.
35. Treat `generate_patterns_clo3d.py` as a lower-level generation helper during transition rather than the canonical Step 2 user command.
36. Update the active Step 2 runner and Step 3 consumer together so the new Step 2 output layout is not rolled out while CLO automation still expects the old DXF lookup pattern.

### Manual Verification Gate 2: Step 2

**Goal**: Pause after the cleaned Step 2 migration so the user can manually run and verify Step 2 as a standalone MVP step before Step 3 cleanup is finalized.

**Checks**:

1. Run the cleaned Step 2 pipeline manually through the canonical Step 2 runner.
2. Confirm Step 2 works as a standalone MVP step without depending on Step 1 runtime outputs.
3. Confirm MongoDB is the active source for Step 2 size and cloth metadata in the canonical flow.
4. Confirm the new Step 2 output folder structure and filenames are correct.
5. Do not retire Step 2 overlap commands or legacy paths until this manual check passes.

**Expected Step 2 Input Structure**:

```plain
product_ingestion/input/
  c_001/
    [images for one shirt]
  c_002/
    [images for one shirt]
```

**Expected Step 2 Run Folder Pattern**:

```plain
product_ingestion/output/
  c_001-s_001-001/
```

**Expected Step 2 Run Structure**:

```plain
product_ingestion/output/
  c_001-s_001-001/
    image_info/
      base_garment.png
      colors.json
      extraction_metadata.json
      graphic_diffuse.png
    panels/
      dxf/
        back_panel.dxf
        front_panel.dxf
        sleeve_left.dxf
        sleeve_right.dxf
      svg/
        back_panel.svg
        front_panel.svg
        sleeve_left.svg
        sleeve_right.svg
      panel_metadata.json
    run_summary.json
```

### Phase 4: Step 3 Structural Cleanup

**Goal**: Move the main virtual try-on workflow into a dedicated `vto` layer while keeping `clo_workspace` focused on REST-server and CLO integration support.

**Execution order inside this phase**: create the `vto` app layer and `run_vto.py` first, move user-facing orchestration out of `clo_workspace`, and update Step 3 path resolvers to the cleaned Step 1 and Step 2 contracts before removing old assumptions.

**Steps**:

1. Create a new `vto` folder for the main Step 3 terminal workflow and orchestration code.
2. Create `vto/run_vto.py` as the main Step 3 user-facing runner instead of only renaming a file inside `clo_workspace`.
3. Move the user-facing virtual try-on flow out of `clo_workspace` and into the new `vto` layer.
4. Keep `clo_workspace` as the support/library layer responsible for the REST server and CLO3D connection.
5. Move the terminal-side handling of avatar values, cloth values, and orchestration inputs into the new `vto` layer.
6. Surface logs for all 11 VTO steps through the new Step 3 terminal workflow.
7. Update Step 3 path assumptions so the VTO flow reads the cleaned Step 1 and Step 2 outputs.
8. Limit Step 3 runtime dependencies from earlier stages to the files actually needed for virtual try-on execution.
9. Rename app-level Step 3 references from `pattern` to `panel` wherever they refer to flat garment pieces rather than CLO-native concepts.
10. Keep CLO SDK and REST-boundary names as `pattern` where they directly mirror CLO behavior.
11. Update Step 3 docs and examples so the new `vto` layer is the main entrypoint and `clo_workspace` is documented as the supporting integration layer.
12. Update the Step 3 resolver logic at the same time as the Step 1 and Step 2 path cleanup so CLO automation does not keep pointing to old `pipeline_star/generated/...` or old Step 2 DXF lookup paths.
13. Treat `mirra_pattern_importer.py` as an experimental alternate implementation path rather than the primary Step 3 runtime, and archive or retire it later unless the team still needs it for experiments.
14. Implement `vto/run_vto.py` as an interactive runner similar in style to Step 1.
15. `vto/run_vto.py` should prompt for `user_id` first, resolve the latest available Step 1 run for that user by default, and allow the user to override the Step 1 run number if needed.
16. `vto/run_vto.py` should then prompt for `cloth_id` and `size_id`, resolve the latest available Step 2 run for that `cloth_id + size_id` pair by default, and allow the user to override the Step 2 run number if needed.
17. Before starting the CLO workflow, `vto/run_vto.py` should print the fully resolved Step 1 and Step 2 source runs and ask the user to confirm the selection.
18. Step 3 should create output only under `vto/output/`; no separate `vto/input/` folder should be introduced for now.
19. Step 3 output folders should be named using the locked format `<avatar_run>__<product_run>__<vto_run_number>`, and the VTO run number should increment per selected avatar-run plus product-run combination.
20. Step 3 should not duplicate Step 1 or Step 2 source artifacts into the VTO run folder by default; it should record and consume them by reference.
21. The locked minimal Step 3 run-folder contents should be:
22. `input.json` containing selected source run IDs, resolved source paths, and run-selection metadata.
23. `run_summary.json` containing Step 3 execution status, step-by-step results, and any output/export references that are available.
24. Step 3 may continue using `clo_workspace/exports/` and `clo_workspace/projects/` for CLO-side exports and save files during transition, but the VTO run folder must at least record those paths in `run_summary.json` when applicable.
25. Automatic export/save behavior is not required for this cleanup. If export/save remains manual, `run_summary.json` should record that export/save was manual or skipped rather than pretending the artifacts were produced.

**Expected Step 3 Output Folder Pattern**:

```plain
vto/output/
  u_001-001__c_001-s_001-001__001/
```

**Expected Step 3 Run Structure**:

```plain
vto/output/
  u_001-001__c_001-s_001-001__001/
    input.json
    run_summary.json
```

### Manual Verification Gate 3: Step 3

**Goal**: Pause after the cleaned Step 3 migration so the user can manually run and verify the full virtual try-on flow using cleaned outputs from Step 1 and Step 2.

**Checks**:

1. Run the cleaned Step 3 flow manually through `vto/run_vto.py`.
2. Confirm Step 3 reads its avatar input from cleaned Step 1 output.
3. Confirm Step 3 reads its panel DXF inputs from cleaned Step 2 output.
4. Confirm Step 3 surfaces the expected user-facing logs for the CLO automation flow.
5. Confirm Step 3 reaches the final CLO-ready or simulated state without relying on old fallback paths.
6. Only after this gate passes can legacy overlapping commands, old path assumptions, and stale docs be retired safely.

### Phase 5: Shared Structure Cleanup

**Goal**: To be defined after shared cleanup discussion is completed.

**Steps**:

1. Finalize shared cleanup decisions for common utilities, naming, and layout.
2. Standardize run/output conventions across all MVP steps.
3. Reduce structural confusion from duplicated or misleading paths where required.
4. Preserve the currently used team commands unless later discussion explicitly changes that decision.
5. Update `mirra_measurements` seed scripts, golden-user metadata, and documentation examples to match the cleaned ID conventions used by the rest of the repo.
6. Delay deletion of legacy generated outputs until the user manually verifies the cleaned Step 1 to Step 3 MVP flow end to end.
7. Reflect the new `vto` versus `clo_workspace` boundary consistently across repo docs, paths, and ownership expectations.
8. Keep terminology boundaries explicit across the repo: app layer uses `panel`, CLO integration layer uses `pattern` only where necessary.
9. Align root-level and folder-level markdown docs with the final cleaned repo structure only after legacy deletion is complete.
10. Re-home or remove stale step-local scripts, tests, and scratch markdown files so each step folder follows the same structure: root runner, `scripts/`, `tests/`, core modules, and output/input folders as applicable.
11. Evaluate the remaining `config/` folder contents and either remove the folder entirely or move any CLO-specific configuration into the CLO integration layer.

## Dependencies

- Later discussion for Step 3 cleanup scope and structure
- Later discussion for shared utilities and compatibility decisions

## Expected Outcomes

When this plan is complete:

1. Step 1 outputs will be organized as self-contained per-run folders.
2. Step 1 naming will consistently use the new `u_...` user ID style and zero-padded run numbers.
3. Step 1 artifact names will become simpler and easier to consume from later steps.
4. Step 2 and Step 3 will consume the new Step 1 `output` structure only, without legacy `generated` path support.
5. Avatar and size identifiers will consistently follow the cleaned `u_...` and `s_...` conventions across seeds, docs, database access, and active code paths.
6. The database-facing support layer will use `size` terminology consistently instead of mixed `garment` and `size` terminology.
7. Step 2 will use MongoDB as the only source of cloth size and cloth metadata.
8. Step 2 run folders will follow one finalized layout with flat `image_info/`, grouped `panels/`, and a root `run_summary.json`.
9. Step 3 will have a clear separation between the VTO application layer and the CLO integration library layer.
10. App-level terminology for flat 2D sewing pieces will consistently use `panel` / `panels`, avoiding confusion with printed shirt patterns.
11. The repo will move toward one consistent run/output structure across all MVP steps.
12. The codebase will be easier to work on later without changing current product behavior.
13. Each step folder will have a cleaner internal structure with a single root runner, clearer `scripts/` and `tests/` separation, and less stale documentation.
14. Canonical user entrypoints versus legacy or experimental helper commands will be clearer across Step 2 and Step 3.

## Manual Verification Checklist

After execution, verify:

1. Running the Step 1 pipeline creates outputs under `avatar_generation/output/` instead of `avatar_generation/generated/`.
2. A Step 1 run creates a folder like `u_001-001`.
3. The Step 1 run folder contains exactly the expected flat artifacts:
   - `input.json`
   - `output.json`
   - `avatar.glb`
   - `avatar.obj`
   - `measurements.json`
4. No `.txt` file is created for the Step 1 run output.
5. Step 2 paths that rely on Step 1 measurement handoff still work with `measurements.json`.
6. Step 3 avatar import still works with `avatar.obj` from the new Step 1 run folder.
7. Run numbering continues increasing correctly for the same user using zero-padded format.
8. Measurement seed scripts and golden-user references use the new `u_...` user IDs.
9. The database support layer uses `size_model.py`, `seed_sizes.py`, `size_id`, and the new `s_...` values consistently.
10. Step 2 prompts, Step 2 examples, and Step 2 DB-facing code use `size_id` with the new `s_...` format.
11. Step 2 creates run folders using the new `<cloth_id>-<size_id>-<run_number>` naming pattern.
12. Step 2 no longer accepts avatar-based inputs for cloth size or cloth metadata.
13. Step 2 creates the finalized run structure with:
   - a flat `image_info/` folder
   - `panels/dxf/`
   - `panels/svg/`
   - `panels/panel_metadata.json`
   - root-level `run_summary.json`
14. The main Step 3 terminal flow runs from the new `vto` layer while `clo_workspace` remains the REST/CLO support layer.
15. App-level Step 2 and Step 3 code uses `panel` / `panels` for flat garment pieces, while CLO-boundary names still use `pattern` where required.
16. Legacy generated outputs are still present until the user manually verifies the cleaned Step 1 to Step 3 flow and approves deletion.
17. Legacy scripts and legacy docs are deleted only after the user manually verifies the cleaned Step 1 to Step 3 flow end to end.
18. Root-level and per-folder markdown docs reflect the final cleaned structure and commands.
19. Step 3 resolves the cleaned Step 1 and Step 2 output paths correctly and does not depend on stale fallback locations.
20. Step 2 and Step 3 use the canonical user entrypoints while legacy or experimental overlapping commands are retired or clearly demoted.
