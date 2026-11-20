# Plan: number every product_ingestion file by execution order

*Status: draft, not executed*
*Written: 2026-10-18*

## Goal

Anyone opening `product_ingestion/` should see, from the file names alone, which process runs in which order and which files belong to which process. Processes get a number (1 to 6). Files inside a process get a sub-number (1.1, 1.2, ...).

Python module names cannot contain dots, so `1.1` is written as `_1_` in the file name.

## Naming scheme

`step_<NN>_<M>_<name>.py`

- `NN` is the process number, as in 05.
- `M` is the file inside that process. `0` is the process's own main file (the one the runner calls). `1, 2, ...` are the files it uses, in the order they run.
- A `0` main file sorts before its helpers in a file listing.

Chosen so that the explorer order equals the run order.

## Target layout

| Label | Current file | New file | Role |
|---|---|---|---|
| 1.0 | `step_01_view_selection.py` | `step_01_0_view_selection.py` | picks the primary image |
| 1.1 | `garment_router.py` | `step_01_1_garment_router.py` | CLIP front/back/side scoring, called by 1.0 |
| 2.0 | `step_02_segmentation.py` | `step_02_0_segmentation.py` | SAM2 / U²-Net cut-out, quality score |
| 3.0 | `step_03_colour_extraction.py` | `step_03_0_colour_extraction.py` | base colour and palette |
| 4.0 | `step_04_design_extraction.py` | `step_04_0_design_extraction.py` | logo / print crop |
| 5.0 | `step_05_panel_generation_clo.py` | `step_05_0_panel_generation_clo.py` | orchestrates panel generation, writes the two JSONs |
| 5.1 | `clo_block/clo_draft_config.py` | `clo_block/step_05_1_clo_draft_config.py` | measurement and shape config |
| 5.2 | `clo_block/clo_draft.py` | `clo_block/step_05_2_clo_draft.py` | builds the four pieces |
| 5.3 | `clo_block/clo_dxf_writer.py` | `clo_block/step_05_3_clo_dxf_writer.py` | writes the DXFs |
| 5.4 | `panel_export_svg.py` | `step_05_4_panel_export_svg.py` | SVG previews |
| 6.0 | `step_06_texture_projection.py` | `step_06_0_texture_projection.py` | panel texture PNGs |

The order inside step 5 follows what `generate_panels()` actually does: config, draft, DXF, SVG, then metadata and manifest (written by 5.0 itself).

### Files that stay as they are

| File | Why it stays |
|---|---|
| `run_product_ingestion.py` | the entry point; the command is documented and used in scripts |
| `run_manifest.py` | imported from outside the folder by `clo_vto/native_vto/helpers.py`, `utils/prune_output.py` and `worker/tasks.py`; shared across all steps. Renaming it would mean editing three other areas. Same convention as the avatar folder's unprefixed `run_manifest.py` |
| `garment_measurements.py` | shared (runner, 5.0, tests), not owned by one step |
| `curve_segment.py` | shared geometry types (used by 5.0, 5.2, 5.4, 6.0) |
| `clo_block/__init__.py`, `README.md`, `clo_default_ground_truth.json`, `reference_dxf/` | not code in the run path |
| `clo_block/generate_block.py`, `clo_block/validate_against_reference.py` | developer tools, not part of a run |
| `legacy/` | archived, untouched |
| `tests/` | stay as they are; their imports are updated |

## Decisions (confirmed 2026-10-18)

1. Main files carry a `0`: `step_01_0_view_selection.py`, and so on.
2. `tshirt_extractor.py` moves to `legacy/`. `test_segmentation.py` moves into `tests/` as a manual script (its `_HERE` path logic must be adjusted for the new location when it moves).
3. `garment_measurements.py` and `curve_segment.py` stay as they are, unnumbered.

## Edits required (all in one pass per file)

Renames are done with plain `mv`. No `git mv`, no staging, no commit.

Import and reference updates:

- `run_product_ingestion.py`: the six stage imports.
- `step_01_0_view_selection.py`: `from garment_router import GarmentRouter` becomes `step_01_1_garment_router`.
- `step_05_0_panel_generation_clo.py`: the `clo_block.clo_draft`, `clo_draft_config`, `clo_dxf_writer` imports (both the relative and the bare-import fallback blocks) and `panel_export_svg`.
- `clo_block/step_05_2_clo_draft.py`: its import of `clo_draft_config`.
- `clo_block/step_05_3_clo_dxf_writer.py`: its import of `clo_draft`.
- `clo_block/__init__.py`: re-exports.
- `clo_block/generate_block.py` and `clo_block/validate_against_reference.py`: their `clo_block` imports.
- `tests/test_panel_geometry.py`: `clo_block.clo_draft` and the step_05 import.
- `tests/test_texture_projection.py`, `tests/test_segmentation_quality.py`, `test_segmentation.py`: step import names.
- `tshirt_extractor.py`: only if it is kept in place.
- Docstring step numbers at the top of each renamed file (they currently say 1 to 4 loosely).
- Comment-only references to file names: `mirra_measurements/size_model.py`, `mirra_measurements/seed_sizes.py`, `website/backend/scripts/seed_sizes.py`, `requirements.txt`, `clo_vto/native_vto/step_08_apply_fabric.py`, `product_ingestion/garment_measurements.py`.

Nothing outside `product_ingestion/` imports `clo_block`, `garment_router`, `panel_export_svg` or the step modules in code, so the only external edits are comments.

## Verification after execution

1. `python -m unittest discover -s product_ingestion/tests` passes (35 tests).
2. `import run_product_ingestion` succeeds from the repo root.
3. A grep for every old module name across `*.py` returns no stale imports.
4. Optional: one real run, `python product_ingestion/run_product_ingestion.py --cloth-id c_001 --size-id s_001 --skip-clip`, to confirm the output folder layout is unchanged.

## Not changed by this plan

- Output folder layout and file names under `output/`.
- Any logic, thresholds or behaviour in any stage.
- Anything under `legacy/`.

## Next

The explanatory write-up (`info-prod-ing.md`) is cleared and rewritten after your questions, not as part of this plan.
