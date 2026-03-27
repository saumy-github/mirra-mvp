# Step 3 Code Explained: Virtual Try-On in clo_workspace

## Naming note

In this repository, the folder is named clo_workspace. If team conversations refer to clo_workshop, they are pointing to the same Step 3 implementation area.

## Step 3 objective in MVP

Step 3 is the virtual try-on execution stage.

Inputs from earlier steps:

1. Avatar asset from Step 1:
OBJ avatar exported by pipeline_star.

2. Garment pattern assets from Step 2:
DXF pieces for front panel, back panel, sleeve left, sleeve right.

Step 3 responsibilities:

1. Load these assets into CLO3D.
2. Position garment pieces around avatar.
3. Stitch seams using known edge mapping.
4. Run cloth simulation to drape garment on body.
5. Prepare export-ready or save-ready state.

## Where Step 3 logic lives

Main Step 3 package:

clo_workspace/plugins/clo_automation_steps

Main entry command:

python clo_workspace/plugins/clo_automation_client.py

Supporting plugin server:

clo_workspace/plugins/RestPlugin.cpp

## How the Step 3 command runs

Entry wrapper:

1. clo_workspace/plugins/clo_automation_client.py
This is intentionally thin and delegates to modular step orchestration.

Orchestrator:

2. clo_workspace/plugins/clo_automation_steps/pipeline.py
This executes each pipeline step in sequence and fails fast when a step fails.

Shared runtime state:

3. clo_workspace/plugins/clo_automation_steps/context.py
Builds a PipelineContext that carries paths, client instance, seam map, slot mapping, and run state.

## Step-by-step behavior in current implementation

### Step 1: Health check

File:
clo_workspace/plugins/clo_automation_steps/step_01_health.py

Action:
Verifies REST plugin server is reachable before any CLO operation.

### Step 2: New project

File:
clo_workspace/plugins/clo_automation_steps/step_02_new_project.py

Action:
Queues a clean project creation so prior scene state does not pollute run results.

### Step 3: Import avatar

File:
clo_workspace/plugins/clo_automation_steps/step_03_import_avatar.py

Action:
Imports the avatar OBJ path from Step 1 output.

Important safety rule:
If avatar is missing, simulation is intentionally skipped later to avoid CLO instability.

### Step 4: Import patterns

File:
clo_workspace/plugins/clo_automation_steps/step_04_import_patterns.py

Action:
Queues import of four DXF files expected by the pipeline.

### Step 5: Verify patterns

File:
clo_workspace/plugins/clo_automation_steps/step_05_verify_patterns.py

Action:
Confirms pattern count loaded in CLO is non-zero and in expected range.

### Step 6: Read edges and arrangement slots

File:
clo_workspace/plugins/clo_automation_steps/step_06_read_edges_and_slots.py

Action:

1. Reads pattern metadata from CLO endpoint.
2. Requests arrangement slot list from CLO.
3. Builds slot matching map for front, back, left sleeve, right sleeve.

### Step 7: Arrange patterns

File:
clo_workspace/plugins/clo_automation_steps/step_07_arrange_patterns.py

Action:
Places each pattern piece into matched arrangement slot with offsets.

Why this matters:
Proper initial placement reduces collisions and improves seam pull-in during simulation.

### Step 8: Apply fabric

File:
clo_workspace/plugins/clo_automation_steps/step_08_apply_fabric.py

Action:
Assigns CLO fabric index to each loaded pattern piece.

### Step 9: Create seams

File:
clo_workspace/plugins/clo_automation_steps/step_09_create_seams.py

Action:
Uses seam map entries to stitch corresponding edges between pattern pieces.

Seam source:

1. Default seam map in clo_workspace/plugins/clo_automation_steps/seams.py.
2. Optional custom seam map can be injected at runtime.

### Step 10: Simulate

File:
clo_workspace/plugins/clo_automation_steps/step_10_simulate.py

Action:
Runs CLO physics simulation for configured step count.

Guard behavior:
Simulation is skipped when avatar is not loaded to prevent crash-prone condition.

### Step 11: Export note

File:
clo_workspace/plugins/clo_automation_steps/step_11_export_note.py

Action:
Current implementation prints manual export and save guidance. Automatic export is intentionally disabled in this step module in current state.

## Step 3 data contracts and dependencies

### Required assets

1. Avatar OBJ from Step 1 pipeline output.
2. Four DXF pattern files from Step 2 pipeline output.

### Required service state

1. CLO3D running.
2. RestPlugin loaded in CLO.
3. REST server started from plugin menu at least once per CLO session.

### Required endpoint behavior

Python step runner assumes the REST endpoints exist and queue-drain status can be polled.

## Practical relationship to Step 2 outputs

Step 3 consumes outputs from Step 2, but does not generate those assets itself.

Asset handoff expected by Step 3:

1. Stable pattern filenames.
2. Stable edge ordering for seam map validity.
3. Accessible path from Step 2 output root.

## Known Step 3 operational risk points

### 1. Pattern path alignment

The automation resolver currently prefers latest run_NNN style path, while Step 2 full orchestrator often writes under pipeline_run_NNN/patterns/run_001. If not aligned, Step 3 may pick older DXFs.

### 2. Seam index fragility

If pattern generation topology changes, seam indices can shift. Default seam map then needs refresh using discover_seam_indices workflow.

### 3. Slot matching variability

Arrangement slot names can vary by CLO state and version, so slot matching is heuristic and may require adjustment.

### 4. Export currently manual in modular flow

Step 11 currently informs operator to export and save manually.

## Supporting utilities relevant to Step 3

### discover_seam_indices.py

Reads DXF geometry directly and helps regenerate seam map entries compatible with CLO edge numbering.

### mirra_pattern_importer.py

Alternative script that demonstrates direct CLO scripting approach. It is a separate approach from REST queue automation and is useful for experiments.

## How to interpret Step 3 in architecture terms

Step 3 is the execution bridge between generated 2D assets and the final simulated garment-on-avatar state.

It is not a CV pipeline and not a pattern-generation pipeline.
It is a CLO orchestration and simulation pipeline.

## Summary

clo_workspace contains the MVP Step 3 virtual try-on engine implementation through modular Python orchestration and a REST plugin bridge.

The core Step 3 value is:

1. Automated scene setup.
2. Automated import and assembly.
3. Automated seam creation.
4. Automated cloth simulation.

When paths and seam indices are in sync with Step 2 outputs, this provides a reliable virtual try-on execution workflow for the MVP.
