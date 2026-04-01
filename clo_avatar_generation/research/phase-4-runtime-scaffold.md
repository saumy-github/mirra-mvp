# Phase 4 Runtime Scaffold

## Goal

Create the isolated runtime scaffold for the CLO-native experiment without touching the existing STAR path or current VTO path.

## What was added in this phase

### Run and bundle infrastructure

- `run_manifest.py`
- `import_bundle.py`

These define the run folder naming and the import-bundle payload for this isolated lane.

### Schema files

- `schema/avatar_input_schema.py`
- `schema/avatar_output_schema.py`

These define the top-level input and output contracts for the CLO-native experiment.

### Future adapter placeholders

- `adapters/clo_native_client.py`
- `adapters/clo_native_importer.py`

These are placeholders so later phases can add plugin-facing logic without changing the current default client or importer.

### New isolated runners

- `run_clo_avatar.py`
- `run_clo_vto.py`

These are separate from the existing runtime commands on purpose.

## Why this phase matters

This phase gives the CLO-native path its own:

1. output structure
2. run identity
3. bundle assembly logic
4. future adapter boundary
5. runner entrypoints

That keeps the experimental lane self-contained and easy to remove later if needed.

## What this phase does not do

1. build a real CLO measurement CSV
2. import an avatar into CLO
3. call the plugin
4. modify current VTO code
5. modify current measurement DB logic

