# CLO Avatar Generation: Completed Work and Confirmed Findings

This note records only the parts of the CLO-native avatar work that have been
implemented or observed directly in this repository and in the current CLO
runtime. It does not include unverified assumptions.

## What Has Been Completed

1. `clo_avatar_generation/` has been isolated as its own runtime lane.
2. The main full-pipeline command is now:
   `python -m clo_avatar_generation.run_clo_vto`
3. The active native try-on runtime now lives inside:
   `clo_avatar_generation/native_vto/`
4. The folder has been split into runtime, avatar setup, research, templates,
   schema, and output areas.
5. The original shared `vto/` runtime is no longer the active runtime path for
   this CLO-native lane.
6. The CLO plugin now contains additive native-avatar endpoints in
   `clo_workspace/plugins/RestPlugin.cpp`:
   - `GET /capabilities`
   - `GET /avatar/native-debug`
   - `POST /import-avatar-avt`
   - `POST /import-avatar-measurements`
7. The CLO-native Python clients and import helpers exist in:
   - `clo_avatar_generation/adapters/clo_native_client.py`
   - `clo_avatar_generation/adapters/clo_native_importer.py`
8. The avatar-only helper now lives in:
   `clo_avatar_generation/avatar_setup/run_avatar.py`
9. The older scaffold runner has been moved to:
   `clo_avatar_generation/research/legacy/run_clo_avatar.py`
10. The current helper for measurement-file-based resizing exists in:
    `clo_avatar_generation/resize_avatar.py`

## What Has Been Confirmed By Running

1. The updated plugin was built, installed into CLO, and loaded successfully.
2. The plugin responded successfully to:
   - `/health`
   - `/capabilities`
   - `/avatar/native-debug`
3. The current CLO-native full pipeline completed successfully with the local
   avatar file:
   `clo_avatar_generation/output/clo_test.avt`
4. The latest native VTO report is:
   `clo_avatar_generation/output/clo_test__native_vto_report.json`
5. In that completed run:
   - all 11 pipeline steps reported success
   - 4 garment patterns were imported
   - all 10 seams in the current t-shirt setup reported success
   - `arrangement_ok` is `true`
   - `ready_for_sewing` is `true`
6. The CLO-native avatar returned arrangement slots during the run.
7. The latest successful report shows:
   - `arrangement_slot_count: 110`
   - `arrangement_list_populated: true`
8. The native slot mapping resolved to concrete slot indices:
   - `front: 60`
   - `back: 43`
   - `sleeve_L: 68`
   - `sleeve_R: 69`
9. The mapped slot names in that run were:
   - `Body_Front_Center_2`
   - `Body_Back_Center_2`
   - `Shoulder_L`
   - `Shoulder_R`
10. After arranging the patterns, the report shows the assigned arrangement
    names on the patterns:
    - `Body_Front_Center_2`
    - `Body_Back_Center_2`
    - `Shoulder_L`
    - `Shoulder_R`

## What We Have Confirmed About CLO Avatars

1. A real CLO avatar saved as `.avt` can be imported into the current CLO
   project through the plugin.
2. The imported CLO avatar can expose named arrangement slots that are useful
   for garment placement.
3. Those slot names are more specific than the old generic front/back/sleeve
   assumptions and include named body regions such as:
   - `Body_Front_Center_*`
   - `Body_Back_Center_*`
   - `Shoulder_L`
   - `Shoulder_R`
   - arm-related slot names present in the report payload
4. The CLO-native lane can already use garment panels from
   `product_ingestion/output/.../panels/dxf` and complete a full try-on run.

## How The CLO Avatar Is Useful

1. It gives access to native arrangement slots in the tested run.
2. Those slots can be matched directly to front, back, and sleeve placement.
3. The current native pipeline has already completed import, arrangement,
   sewing, and simulation with the CLO avatar.
4. The CLO avatar can be used in the current isolated runtime without using the
   original shared `vto/` runtime as the active execution path.

## Confirmed Disadvantages and Current Limits

1. This lane currently depends on a running CLO application with the REST
   plugin loaded.
2. This lane currently requires a real `.avt` file on disk.
3. The current measurement CSV template is explicitly unconfirmed:
   `clo_avatar_generation/schema/measurement_template_unconfirmed.csv`
4. A real measurement-import attempt with the current CSV template failed.
5. The debug result for that attempt reported:
   `Failed to import native avatar measurement CSV`
6. Because of that failed import, changing avatar dimensions through the
   current CSV template is not yet confirmed to work.
7. `resize_avatar.py` is currently experimental and depends on the same
   unconfirmed CSV format.
8. In the latest successful native VTO report, the SDK-reported pattern names
   are:
   `["0", "0", "0", "0"]`
   This means the current runtime is not getting useful semantic pattern names
   from the SDK import result itself.

## Current Active Commands

1. Full CLO-native VTO:
   `python -m clo_avatar_generation.run_clo_vto`
2. Avatar-only import helper:
   `python -m clo_avatar_generation.avatar_setup.run_avatar`
3. Experimental measurement-file resize helper:
   `python -m clo_avatar_generation.resize_avatar`

## Current Evidence Files

1. Runtime report:
   `clo_avatar_generation/output/clo_test__native_vto_report.json`
2. Test avatar:
   `clo_avatar_generation/output/clo_test.avt`
3. Current unconfirmed CSV template:
   `clo_avatar_generation/schema/measurement_template_unconfirmed.csv`
4. Folder overview:
   `clo_avatar_generation/README.md`
