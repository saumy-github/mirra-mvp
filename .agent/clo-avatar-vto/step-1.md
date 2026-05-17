# Step 1 — CLO Avatar Generation

**Command:** `python clo_avatar_generation/run_avatar.py`

This is the Step 1 implementation of the Mirra MVP. It takes a user's body measurements and produces a personalized CLO avatar (.avt file) by patching the binary internals of a base avatar template.

---

## What It Does

1. Reads user body measurements (from a local JSON file or MongoDB)
2. Maps those measurements to CLO-internal field names using a field contract
3. Directly patches measurement values into the binary `.avt` file
4. Imports the patched avatar into CLO via the REST plugin
5. Saves the result as a `.zprj` project + `.avt` avatar file
6. Verifies the saved avatar binary actually contains the requested values

---

## How to Run

### Interactive (default)
```
python clo_avatar_generation/run_avatar.py
```
Prompts for user_id, run number, base avatar path, measurement file path.

### Non-interactive (scripted)
```
python clo_avatar_generation/run_avatar.py --non-interactive --user-id u_001
```

### All CLI flags
| Flag | Description |
|---|---|
| `--user-id` | Measurement user ID (e.g. `u_001`) |
| `--run-number` | Explicit run number (default: auto-incremented) |
| `--base-avatar` | Override path to the base `.avt` file |
| `--measurement-file` | Override path to measurement JSON |
| `--apply-mode` | One of `auto`, `csv`, `avatar_properties`, `avt_patch` |
| `--active-field` | Isolate specific field(s) for testing (repeatable) |
| `--non-interactive` | Skip all prompts, use defaults |

---

## Inputs

### 1. Measurement JSON (primary source)
Location: `clo_avatar_generation/input/{user_id}.measurements.json`

Example (`u_001.measurements.json`):
```json
{
  "user_id": "u_001",
  "gender": "male",
  "height_cm": 178,
  "weight_kg": 75,
  "chest_circumference_cm": 98,
  "waist_circumference_cm": 82,
  "hip_circumference_cm": 96,
  "shoulder_width_cm": 46,
  "leg_length_cm": 80
}
```

### 2. MongoDB (fallback)
Reads from `mirra_measurements` collection via `mirra_measurements.db`.

### 3. Base Avatar
Default: `clo_avatar_generation/input/base-1.avt`
- Must be a valid `.avt` file (ZIP container with `.dan` binary member)
- Should have companion files: `.arr`, `.iks`, `.avs`, `.mea`

### 4. CLO REST Plugin
Must be running at `http://localhost:50505` before the pipeline starts.
Required capabilities checked at startup:
- `has_native_avatar_import`
- `has_avatar_measurement_import`

---

## The 11-Step Pipeline

| Step | File | Required | Description |
|---|---|---|---|
| 01 | `step_01_health.py` | Yes | Health-check CLO plugin at `localhost:50505` |
| 02 | `step_02_run_setup.py` | Yes | Create numbered run dir (`output/u_001-001/`) |
| 03 | `step_03_fetch_measurements.py` | Yes | Load measurements from JSON or MongoDB |
| 04 | `step_04_resolve_base_avatar.py` | Yes | Validate base `.avt` file is readable ZIP |
| 05 | `step_05_normalize_targets.py` | Yes | Map mongo fields → CLO field names |
| 06 | `step_06_build_payloads.py` | Yes | Build 3 payload formats (CSV, properties, AVT patch) |
| 07 | `step_07_import_base_avatar.py` | Yes | Create fresh CLO project, import base avatar |
| 08 | `step_08_apply_measurements.py` | Yes | Apply measurements (AVT patch route is working) |
| 09 | `step_09_readback.py` | No | Read back post-apply state from CLO |
| 10 | `step_10_compute_error.py` | No | Compute requested vs achieved diff |
| 11 | `step_11_save_outputs.py` | Yes (always) | Save project + avatar, binary-verify result |

Steps 9 and 10 are optional — pipeline continues even if they fail.
Step 11 always runs regardless of earlier failures.

---

## The Working Solution: AVT Binary Patching

Three routes were tried. Only **AVT patching** is reliable.

### How it works (`avt_patch.py`)
1. An `.avt` file is a ZIP container. Inside is a `.dan` binary member.
2. The `.dan` binary contains a block of 57 float values (4 bytes each, little-endian).
3. The block starts at: `offset_of("listFeatureValues" marker) + 273 bytes`
4. Each measurement field is stored at a known feature index within those 57 floats.
5. The pipeline overwrites the float at the right index with the target value.
6. The patched `.avt` is imported into CLO, saved, then re-read to verify.

### Verified field index map
| Measurement field | CLO name | AVT feature index |
|---|---|---|
| `height_cm` | Total Height | 0 |
| `chest_circumference_cm` | Chest | 2 |
| `waist_circumference_cm` | Waist | 6 |
| `hip_circumference_cm` | Low Hip | 8 |
| `leg_length_cm` | Inseam | 26 |
| `shoulder_width_cm` | Across Shoulder (Curvilinear) | 36 |

### Routes that failed
- **CSV route** (`import_avatar_measurements`): both multi-field and single-field imports failed
- **Avatar Properties API** (`set_avatar_properties`): did not reliably change measurement values

---

## Outputs

All outputs go into a numbered run folder: `clo_avatar_generation/output/{user_id}-{run_number:03d}/`

| File | Description |
|---|---|
| `input.json` | Resolved config for this run |
| `mongo_snapshot.json` | Raw measurement doc fetched |
| `target_measurements.json` | Fields normalized to CLO names |
| `clo_payload.json` | Payload manifest |
| `clo_payload.bridge.csv` | CSV bridge payload (unused by working route) |
| `clo_payload.properties.json` | Properties payload (unused by working route) |
| `clo_payload.avt_patch.json` | AVT patch config — what was actually applied |
| `clo_payload.patched.avt` | Patched avatar file that was imported |
| `import_result.json` | CLO import result |
| `apply_result.json` | Apply route result + patch report |
| `readback_measurements.json` | Post-apply state from CLO plugin |
| `error_report.json` | Requested vs achieved values |
| `measurement_verification.json` | Binary verification: pass/fail per field (tolerance ±0.05) |
| `save_outputs.json` | Save/export result |
| `run_summary.json` | Full step-by-step status |
| `output.json` | Final artifact manifest with all paths |
| `result_project.zprj` | **Final CLO project** |
| `result_avatar.avt` | **Final personalized avatar** |

### What "success" means
A run is only marked `completed` if `measurement_verification.json` shows all supported fields:
- `changed_from_base: true` — value differs from base avatar
- `matches_requested: true` — value matches the input measurement (within ±0.05 cm)

---

## Current Status

### Working
- AVT patching for 6 male measurements (height, chest, waist, hip, inseam, shoulder)
- Binary verification of the saved avatar
- JSON-first measurement input (no MongoDB dependency for testing)
- Auto run numbering (`u_001-001`, `u_001-002`, etc.)

### Not working / known issues
- `weight_kg` is not yet verified on the AVT route (Weight may be a computed field, not a direct float)
- CSV import route is still broken
- Avatar Properties API route is unreliable
- Female measurements are not supported in v1
- If the user manually re-applies the default preset inside CLO's Avatar Editor, measurements reset to default

### Male-only scope
v1 only supports male avatars. The field contract has `"scope": "male_only"`. Female fields (bust, under-bust) are reserved for v2.
