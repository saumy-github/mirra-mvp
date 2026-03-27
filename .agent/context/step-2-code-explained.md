# Step 2 Code Explained: 2D Garment Generation and CLO Automation

## Scope of Step 2 in this repository

Step 2 in this MVP is implemented across three places:

1. 2d_patterned_garment_generation_clo3d
This is the garment asset preparation layer. It does appearance extraction from product images and pattern generation for CLO-compatible pattern files.

2. clo_workspace
This is the CLO execution layer. It loads avatar and pattern assets into CLO3D through a REST plugin, arranges pieces, creates seams, and runs simulation.

3. config
This holds CLO-related configuration constants. In current code state, this file is mostly standalone and not wired into the active automation command path.

## The two commands your team uses

You listed two active commands:

1. python 2d_patterned_garment_generation_clo3d/main.py 2d_patterned_garment_generation_clo3d/input_images
2. python clo_workspace/plugins/clo_automation_client.py

These two commands are connected in sequence:

1. Command 1 prepares or derives garment assets.
2. Command 2 consumes prepared assets and performs virtual try-on simulation in CLO3D.

## Command 1: What happens after running main.py

Entry file: 2d_patterned_garment_generation_clo3d/main.py

This command is a two-stage orchestrator.

### Stage A: Appearance Extraction

Primary modules:

1. 2d_patterned_garment_generation_clo3d/tshirt_extractor.py
2. 2d_patterned_garment_generation_clo3d/garment_router.py
3. 2d_patterned_garment_generation_clo3d/vision_pipeline.py

Main actions:

1. Segments the garment from background using RMBG, with fallback logic.
2. Optionally routes images by view (front, back, side, irrelevant) using CLIP classification.
3. Extracts color palette and base color.
4. Extracts graphic or print region to a diffuse-style texture image.
5. Writes appearance artifacts under a run folder.

Typical Stage A outputs:

1. base_garment.png
2. graphic_diffuse.png
3. colors.json
4. extraction_metadata.json

### Stage B: Pattern Generation

Primary module:

1. 2d_patterned_garment_generation_clo3d/generate_patterns_clo3d.py

Main actions:

1. Resolves measurement source by priority:
command garment id, avatar json, manual values, or interactive garments DB selection.
2. Builds garment measurements and fit profile.
3. Generates 2D pattern geometry for four pieces:
front panel, back panel, left sleeve, right sleeve.
4. Exports both DXF and SVG pattern sets.
5. Writes pattern metadata including seam-matching checks.

Typical Stage B outputs:

1. patterns_dxf folder
2. patterns_svg folder
3. pattern_metadata.json

### Combined run packaging by main.py

main.py creates combined pipeline folders at:

2d_patterned_garment_generation_clo3d/output/pipeline_run_NNN

Inside each combined run it stores:

1. appearance/ext001 style assets
2. patterns/run_001 style pattern outputs
3. pipeline_result.json summary tying both stages together

This command therefore performs data extraction and pattern creation in one pass.

## Command 2: What happens after running clo_automation_client.py

Entry file: clo_workspace/plugins/clo_automation_client.py

This command is now a thin wrapper that delegates to modular steps in:

clo_workspace/plugins/clo_automation_steps

The orchestrator is:

clo_workspace/plugins/clo_automation_steps/pipeline.py

### Execution steps in CLO automation

The pipeline runs these steps in order:

1. Health check to CLO REST plugin server.
2. New project reset in CLO.
3. Avatar import from pipeline_star OBJ path.
4. Pattern import for four DXF files.
5. Verify pattern count in CLO scene.
6. Read edge and arrangement slot data.
7. Arrange pattern pieces around avatar.
8. Apply fabric assignment to pieces.
9. Create seams using seam map indices.
10. Run simulation.
11. Print export-save note.

Important behavior:

1. This command does not perform image segmentation or color extraction.
2. This command does not generate new DXF or SVG files.
3. It consumes existing avatar and pattern files, then performs CLO-side assembly and simulation.

## Overlap between the two commands

There is workflow overlap at the asset handoff boundary.

Shared domain overlap:

1. Both commands operate on the same garment pipeline context.
2. Both rely on the same 4-piece pattern naming convention.
3. Both are tied to CLO import requirements and seam consistency.

Asset overlap:

1. Command 1 writes pattern files and seam-related metadata.
2. Command 2 reads those pattern files and applies seam map in CLO.

Folder overlap signal:

1. Both commands expect pattern artifacts under output runs.
2. Both implicitly depend on stable naming of panel files.

## Non-overlapping responsibilities

### Unique to Command 1

1. Computer vision extraction from raw input images.
2. Base color and graphic texture derivation.
3. Garment measurement source routing and pattern generation.
4. DXF and SVG creation.
5. Pattern metadata generation.

### Unique to Command 2

1. CLO REST server communication and queue management.
2. CLO project reset and avatar import.
3. Pattern arrangement in 3D slots.
4. Fabric assignment in CLO.
5. Seam creation using explicit edge indices.
6. Cloth simulation execution.

## Critical integration notes discovered from code and outputs

### 1. Pattern output path mismatch risk

Current main.py writes patterns inside:

output/pipeline_run_NNN/patterns/run_001/patterns_dxf

Current CLO helper resolve function searches latest at:

output/run_NNN/patterns_dxf

This means the CLO command may consume an older run_NNN pattern set instead of the latest pipeline_run_NNN output unless paths are aligned or provided explicitly.

### 2. CLO config file is not actively wired

config/clo_config.py contains CLO host, port, paths, and defaults, but current active CLO client uses direct defaults in clo_automation_steps/client.py and does not import config/clo_config.py.

### 3. Appearance outputs are not yet auto-applied in CLO flow

Command 1 produces color and graphic outputs, but command 2 currently applies fabric index and seam simulation without automatically injecting extracted color palette or graphic texture map into CLO material channels.

## Folder-by-folder explanation

### 2d_patterned_garment_generation_clo3d

Key files and roles:

1. main.py
Top-level Step 2 orchestrator that runs appearance and pattern generation in one combined run.

2. tshirt_extractor.py
Core appearance extraction implementation with segmentation, color extraction, and design extraction.

3. garment_router.py
CLIP-based image view routing for selecting front and back candidates.

4. vision_pipeline.py
Single-image convenience pipeline around segmentation, color, and design extraction.

5. generate_patterns_clo3d.py
Pattern generator and measurement conversion logic; exports DXF and SVG and metadata.

6. generate_for_avatar.py
Utility script to generate patterns from avatar DB or local measurement JSON.

7. garment_router.py and vision_pipeline.py
Supporting modules for Stage A preprocessing and extraction quality.

### clo_workspace

Key files and roles:

1. plugins/clo_automation_client.py
Thin CLI entrypoint for running modular CLO automation.

2. plugins/clo_automation_steps/pipeline.py
Step orchestrator for all CLO actions.

3. plugins/clo_automation_steps/step_01 through step_11
Concrete implementation of each CLO workflow stage.

4. plugins/clo_automation_steps/client.py
REST wrapper for CLO plugin endpoints.

5. plugins/clo_automation_steps/seams.py
Default seam index map used by step_09.

6. plugins/discover_seam_indices.py
DXF-based seam index discovery helper to keep seam map synchronized with generated pattern geometry.

7. plugins/RestPlugin.cpp and build files
CLO plugin side implementation that exposes the HTTP endpoints consumed by Python automation.

### config

Key file and role:

1. config/clo_config.py
Centralized CLO settings module containing paths and defaults. Useful as configuration intent, but not currently integrated into active command execution path.

## Recommended way to think about Step 2 execution

Step 2 is a two-lane pipeline with a producer and a consumer:

1. Producer lane:
main.py turns raw garment images and measurement sources into CLO-ready garment assets.

2. Consumer lane:
clo_automation_client.py turns CLO-ready assets into a simulated virtual try-on state inside CLO3D.

Both lanes are required for full Step 2 value. They should be treated as sequential, not competing commands.

## Practical sequence for your team

1. Run main.py with image input folder.
2. Confirm Stage A and Stage B success in pipeline_result.json.
3. Confirm the exact patterns_dxf directory selected for CLO step.
4. Run clo_automation_client.py after CLO REST plugin is active.
5. Verify pattern count, seams, and simulation completion.

## Summary

The two commands overlap in garment asset boundary handling, but they do fundamentally different jobs.

1. main.py is asset creation and preparation.
2. clo_automation_client.py is CLO orchestration and simulation.

The most important integration risk today is path alignment between where patterns are generated and where CLO automation looks for them by default.
