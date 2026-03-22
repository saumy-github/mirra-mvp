# Avatar Generation

This pipeline creates a STAR-based avatar bundle from MongoDB body measurements.

## Run

```bash
python avatar_generation/run_avatar.py
```

The CLI asks for a `user_id` and writes a new per-run folder under `avatar_generation/output/`.

## Clear Output

```bash
python avatar_generation/scripts/clear_output.py
```

This removes generated run folders from `avatar_generation/output/` while preserving `.gitkeep`.

## Output Layout

Each run is written to:

```plain
avatar_generation/output/<user_id>-<run_number>/
```

Files inside each run folder:

```plain
input.json
output.json
avatar.glb
avatar.obj
measurements.json
```

No new `clo_avatars/` folder is created.

## Folder Structure

```plain
avatar_generation/
|-- run_avatar.py
|-- first.py
|-- star_runner.py
|-- fit_betas.py
|-- mapping_layer.py
|-- mesh_measure.py
|-- mesh_postprocess.py
|-- avatar_exporter.py
|-- avatar_exporter_clo.py
|-- avatar_style.py
|-- pose_catalog.py
|-- artifact_schema.py
|-- artifact_io.py
|-- run_manifest.py
|-- output/
|   `-- .gitkeep
|-- generated/
|   `-- .gitkeep
|-- scripts/
|   `-- clear_output.py
|-- tests/
|   |-- diagnose_shoulder.py
|   |-- inspect_star_joints.py
|   `-- test_shoulder_landmarks.py
|-- SETUP.md
|-- README.md
`-- .gitignore
```
