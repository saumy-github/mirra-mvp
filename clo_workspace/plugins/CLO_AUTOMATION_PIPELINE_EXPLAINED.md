# CLO Automation Pipeline (Simple Explanation)

This document explains the CLO automation pipeline in simple words so you can teach it to someone else.

It covers:
- What this pipeline does
- What gets imported and exported
- Which files/functions do what
- The small amount of math used
- Important terms in plain language

---

## 1) What the pipeline does (big picture)

The pipeline automatically does a virtual try-on in CLO:

1. Connect to CLO through a local REST server
2. Start a fresh CLO project
3. Import the avatar OBJ
4. Import four DXF pattern pieces
5. Arrange pieces around the body
6. Apply a fabric
7. Create seams (stitch lines)
8. Run simulation so cloth drapes naturally
9. (Currently) remind user to export manually

Main entry file:
- `clo_workspace/plugins/clo_automation_client.py`

Real step-by-step logic lives in:
- `clo_workspace/plugins/clo_automation_steps/`

---

## 2) "Imports" in this project (two meanings)

People use the word "import" in two ways here.

### A) Python code imports

Example from `clo_automation_client.py`:
- `import json`
- `from clo_automation_steps.client import CLORestClient`
- `from clo_automation_steps.pipeline import run_pipeline`

Meaning: Python is loading code from other files.

### B) CLO asset imports

These are real 3D/2D assets loaded into CLO:
- Avatar import: OBJ file
- Pattern import: DXF files

Meaning: CLO loads geometry files into the scene.

---

## 3) Inputs and outputs (files)

## Inputs used by pipeline

- Avatar:
  - `pipeline_star/generated/clo_avatars/user_m_001_001_avatar.obj`
- Pattern files:
  - `front_panel.dxf`
  - `back_panel.dxf`
  - `sleeve_left.dxf`
  - `sleeve_right.dxf`
  - These are read from latest `run_NNN/patterns_dxf/` folder.

## Outputs

- Simulation result exists in CLO scene memory immediately.
- Export paths are prepared in context:
  - `clo_workspace/exports/`
  - `clo_workspace/projects/`
- In current code, final auto export/save is intentionally skipped (Step 11 prints manual instructions).

---

## 4) Files and their job (simple map)

### `clo_workspace/plugins/clo_automation_client.py`
- Thin launcher.
- Supports modes:
  - `test` -> only checks connection
  - `status` -> prints plugin status JSON
  - no argument -> runs full pipeline

### `clo_workspace/plugins/clo_automation_steps/client.py`
- REST client wrapper.
- Sends HTTP GET/POST calls to CLO plugin.
- Important methods:
  - `health_check()`
  - `new_project()`
  - `import_avatar()`
  - `import_pattern()`
  - `arrange_pattern()`
  - `set_fabric()`
  - `create_seam()`
  - `simulate()`
  - `get_status()`, `wait_for_queue()`
  - `export_garment()`, `save_project()`

### `clo_workspace/plugins/clo_automation_steps/context.py`
- Creates one shared `PipelineContext` object.
- Holds all runtime data: client, paths, loaded pattern count, slots, seams, flags.

### `clo_workspace/plugins/clo_automation_steps/helpers.py`
- Utility functions:
  - `resolve_patterns_dir()` -> finds latest pattern folder
  - `print_result()` -> standard success/failure line
  - `find_slot()` -> finds avatar arrangement slot by keywords

### `clo_workspace/plugins/clo_automation_steps/pipeline.py`
- Orchestrator.
- Runs all step modules in order and stops early on failure.

### `clo_workspace/plugins/clo_automation_steps/seams.py`
- Default seam map (which edge index connects to which edge index).

### Step modules (`step_01_...` to `step_11_...`)
- Each file has one `run(ctx)` function.
- Each step does one clear part of the flow.

---

## 5) Step-by-step function explanation (plain language)

1. `step_01_health.run(ctx)`
- Calls `/health`.
- Confirms CLO plugin is reachable.

2. `step_02_new_project.run(ctx)`
- Clears/starts a fresh project.
- Waits for command queue to finish.

3. `step_03_import_avatar.run(ctx)`
- Imports avatar OBJ if file exists.
- If avatar missing, marks `avatar_loaded=False` and later simulation is skipped for safety.

4. `step_04_import_patterns.run(ctx)`
- Imports each DXF pattern file that exists.
- Waits for queue to finish importing.

5. `step_05_verify_patterns.run(ctx)`
- Reads status and checks how many patterns CLO loaded.
- Stops pipeline if zero patterns loaded.

6. `step_06_read_edges_and_slots.run(ctx)`
- Reads pattern edge counts.
- Fetches arrangement slots from CLO (front/back/left sleeve/right sleeve type positions).
- Builds `slot_map` for later placement.

7. `step_07_arrange_patterns.run(ctx)`
- Places each pattern near matched slot.
- Uses a fixed Z offset so pieces start a little away from body.

8. `step_08_apply_fabric.run(ctx)`
- Applies fabric index `0` to all loaded pattern pieces.

9. `step_09_create_seams.run(ctx)`
- Loops through seam map and sends seam creation commands.
- Each seam says: pattern A + edge A connects to pattern B + edge B.

10. `step_10_simulate.run(ctx)`
- Runs simulation for 150 steps (if avatar is loaded).

11. `step_11_export_note.run(ctx)`
- Currently just prints manual export/save instructions.

---

## 6) REST endpoints used (what Python calls in plugin)

Common endpoints used by the client:
- `GET /health`
- `GET /status`
- `GET /arrangement-list`
- `GET /pattern-arrangements`
- `GET /patterns/count`
- `GET /patterns/{index}`
- `POST /new-project`
- `POST /import-avatar`
- `POST /import-pattern`
- `POST /arrange-pattern`
- `POST /set-fabric`
- `POST /create-seam`
- `POST /simulate`
- `POST /export`
- `POST /save-project`
- `POST /execute` (used internally when queue needs trigger)

Simple meaning:
- `GET` asks for information.
- `POST` asks CLO to do an action.

---

## 7) Math used in this pipeline (simple)

There is no heavy math here. Mostly indexing and basic coordinates.

### A) Unit conversion idea (meters to centimeters)

Avatar OBJ from STAR is in meters. CLO workflows often use centimeters.

So conceptually:

$$
value_{cm} = value_{m} \times 100
$$

This is why documentation mentions avatar import scale of 100.

### B) 3D placement offset

In step 7, each piece is arranged with offset values:
- `offset_x = 0`
- `offset_y = 0`
- `offset_z = 100`

Meaning: place pattern about 100 units away from body direction used by CLO for initial placement, so cloth does not start intersecting deeply.

### C) Seam indexing

A seam entry has:
- pattern index A (`a`)
- edge index A (`la`)
- pattern index B (`b`)
- edge index B (`lb`)

Example idea:
- connect edge 1 of front panel to edge 1 of back panel for side seam.

So seam creation is basically a mapping problem, not calculus.

### D) Queue wait timing

`wait_for_queue(timeout, poll_interval)` polls status repeatedly.

Approximate number of polls:

$$
N \approx \frac{timeout}{poll\_interval}
$$

Example: timeout 60s and poll every 0.3s gives about 200 checks.

---

## 8) Important data structures

### `PipelineContext` (shared state)

Holds key runtime data like:
- `client`
- `avatar_path`, `patterns_dir`
- `pattern_files`
- `seams`
- `avatar_loaded`
- `loaded_patterns`
- `slots`, `slot_map`

This avoids passing many separate variables between functions.

### Seam item format

Each seam dictionary in `DEFAULT_SEAMS` looks like:

```python
{
  "name": "side-right",
  "a": 0,
  "la": 1,
  "b": 1,
  "lb": 1,
  "da": True,
  "db": True,
}
```

---

## 9) How to explain this to someone quickly

Use this short script:

1. "Python talks to CLO through HTTP commands."
2. "We import avatar + 4 pattern files, then place them around the body."
3. "We stitch edges using a seam map (edge index to edge index)."
4. "Then CLO simulates cloth for 150 steps to drape naturally."
5. "Export/save is currently manual for stability reasons."

---

## 10) How to run

From project root:

```powershell
python clo_workspace/plugins/clo_automation_client.py test
python clo_workspace/plugins/clo_automation_client.py status
python clo_workspace/plugins/clo_automation_client.py
```

---

## 11) Common confusion points (easy answers)

- "Why two import meanings?"
  - Python import = load code module.
  - CLO import = load geometry file.

- "Why does simulation skip sometimes?"
  - If avatar is missing, simulation is skipped to avoid CLO crash.

- "Why seam errors happen?"
  - Usually wrong edge indices when DXF geometry changed.

- "Why queue waiting?"
  - CLO actions run asynchronously; we wait until queue is empty before next stage.

---

If you want, I can also create a one-page "presentation version" with diagrams and less code detail.