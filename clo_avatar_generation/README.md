# CLO Avatar Generation

## Purpose

This folder is the isolated CLO-native avatar lane.

It owns:

1. CLO-based avatar loading and resizing helpers
2. the local CLO-native virtual try-on runtime
3. reports and runtime outputs for this lane

It may read input files from other folders, especially:

1. garment panels from `product_ingestion/output/.../panels/dxf`
2. the already available REST plugin endpoints

But its runtime code should not depend on the shared `vto/` folder anymore.

## Main Commands

Step 1 avatar-generation command:

```powershell
python -m clo_avatar_generation.run_avatar
```

This command:

1. starts from a measurement `user_id`
2. creates a numbered run folder under `output/`
3. fetches the user measurement snapshot
4. resolves the locked base avatar
5. builds the human-readable JSON payload plus the CLO bridge payload
6. calls the local CLO plugin
7. writes `run_summary.json` and `output.json`

Step 3 native VTO command:

```powershell
python -m clo_avatar_generation.run_clo_vto
```

This command:

1. finds the local CLO-native avatar `.avt`
2. reads the latest or chosen garment panel directory
3. runs the isolated native VTO pipeline from `clo_avatar_generation/native_vto/`
4. writes the report to `clo_avatar_generation/output/`

## Other Root Commands

Avatar-side helpers:

1. `python -m clo_avatar_generation.resize_avatar`

These are helpers, not the main try-on entrypoint.

The avatar-only import helper now lives in:

- `clo_avatar_generation/avatar_setup/run_avatar.py`

Use it with:

```powershell
python -m clo_avatar_generation.avatar_setup.run_avatar
```

The older scaffold runner now lives in:

- `clo_avatar_generation/research/legacy/run_clo_avatar.py`

It is kept only as legacy reference code.

## Active Runtime Files

The active CLO-native VTO runtime lives in:

- `clo_avatar_generation/native_vto/`

The active Step 1 avatar-generation runtime lives in:

- `clo_avatar_generation/avatar_runtime/`

Key runtime areas:

1. `native_vto/client.py`
2. `native_vto/context.py`
3. `native_vto/helpers.py`
4. `native_vto/seams.py`
5. `native_vto/pipeline.py`
6. `native_vto/step_01_...` through `native_vto/step_11_...`

Step 1 runtime areas:

1. `avatar_runtime/client.py`
2. `avatar_runtime/context.py`
3. `avatar_runtime/run_manifest.py`
4. `avatar_runtime/field_contract.py`
5. `avatar_runtime/pipeline.py`
6. `avatar_runtime/step_01_...` through `avatar_runtime/step_11_...`

## Research-Only Area

Non-runtime phase notes and investigation documents live under:

- `clo_avatar_generation/research/`

This area is for:

1. phase findings
2. implementation notes
3. design and comparison documents

It is not the active runtime path.

## Input and Output Areas

Reusable avatar inputs:

- `clo_avatar_generation/avt_templates/`

Runtime outputs and generated artifacts:

- `clo_avatar_generation/output/`

This includes:

1. reports
2. per-user Step 1 run folders such as `u_001-001`
3. temporary measurement bridge CSVs
4. local research/test avatar files used by this lane

## Current Isolation Rule

If this lane changes in the future:

1. modify code inside `clo_avatar_generation/`
2. do not rely on further runtime edits in `vto/`
3. keep `product_ingestion/` as an input source only

This keeps the CLO-native lane removable and easier to reason about.
