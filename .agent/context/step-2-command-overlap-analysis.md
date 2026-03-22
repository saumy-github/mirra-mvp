# Step 2 Command Overlap Analysis

## Command A

python 2d_patterned_garment_generation_clo3d/main.py 2d_patterned_garment_generation_clo3d/input_images

## Command B

python clo_workspace/plugins/clo_automation_client.py

## High-level answer

These commands are connected but not equivalent.

1. Command A creates Step 2 assets.
2. Command B consumes those assets to run try-on simulation in CLO.

There is overlap only at file contracts and naming assumptions, not at full functionality level.

## Functional overlap matrix

### A and B both touch

1. T-shirt panel identity model:
front panel, back panel, left sleeve, right sleeve.

2. Pattern file contract:
DXF files must exist with expected names.

3. Seam compatibility assumptions:
Edge ordering in generated patterns must match seam mapping used by CLO automation.

### Only Command A does

1. Segmentation of garment from input images.
2. CLIP-based image view routing.
3. Dominant color extraction.
4. Graphic or print extraction map creation.
5. Garment measurement resolution from DB, manual input, or avatar json.
6. Dynamic pattern geometry generation.
7. DXF and SVG export.
8. Pattern metadata and seam-length validation output.

### Only Command B does

1. CLO REST health and queue flow checks.
2. New CLO project creation.
3. Avatar OBJ import.
4. DXF pattern import into CLO scene.
5. Pattern arrangement on body slots.
6. Fabric assignment in CLO.
7. Seam creation by explicit edge indices.
8. Physics simulation.
9. Final pipeline status reporting from CLO side.

## Overlap details where confusion usually happens

### 1. Pattern generation versus pattern usage

Command A generates patterns.
Command B imports and simulates patterns.

So both are pattern-related, but only one is a generator.

### 2. Seam logic appears in both places but at different levels

Command A validates seam length compatibility in metadata.
Command B performs actual seam construction in CLO using seam index pairs.

### 3. Output folder conventions are not fully unified

Observed producer output from main.py:

output/pipeline_run_NNN/patterns/run_001/patterns_dxf

Observed CLO consumer default lookup:

output/run_NNN/patterns_dxf

This creates a practical overlap bug risk where Command B may read a different run than Command A just produced.

## Current state of config folder in this overlap

config/clo_config.py defines CLO host, port, paths, and defaults, but active CLO automation steps currently use direct internal defaults and do not import this config file.

Implication:

1. Config exists as intended centralization.
2. Runtime path is currently split, so changing config file alone may not affect command behavior.

## Operational recommendation for your team

1. Treat Command A as required pre-step for pattern asset freshness.
2. Before Command B, explicitly verify the DXF folder it will consume.
3. Keep seam index map synchronized with generated pattern topology, especially after pattern generator changes.
4. Use discover_seam_indices workflow whenever edge ordering changes.

## Single-line summary

Command A prepares garment assets from images and measurements, while Command B executes CLO virtual try-on from those assets; they overlap at the pattern contract boundary, not in core responsibilities.
