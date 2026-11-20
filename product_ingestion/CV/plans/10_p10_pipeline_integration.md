# 10 · P10 Wiring the best methods into the pipeline, and the end-to-end result

*Status: done; final run with the final defaults: pipeline score 0.960*
*Date: 2026-11-20, 09:45 to 10:02 (runner changes and tests), 14:13 to 14:18 (runs on the 5 photos and scoring); file times*

## Goal
Put every accepted method into the real runner `product_ingestion/run_product_ingestion.py`, keep the old behaviour selectable, add regression tests, and score the whole pipeline end to end, exactly as the v0 pipeline was scored in P00.

## What changed [V]
**Runner (`run_product_ingestion.py`):**
- **P16:** `select_views(cloth_dir)` runs after `select_primary_image`.
  - It writes `image_info/view_assignment.json`.
  - The chosen front photo is segmented, and a back photo (if any) is segmented too and passed to the texture step.
  - If a single photo is a back view, the main view is "back".
  - The presentation (flat or person) is recorded.
- **P04:** `colors.json` gets the multi-colour fields (`method`, `palette_roles`, `fabric_colours`, `region_map`) next to the old keys.
- **P05:** `extraction_metadata.json` gets `design.regions` (every region with its box and type) and a `views` block.
- **P06:** new `image_info/shape.json` (landmarks, sleeve class, ratios, plus a note that it is reliable only on flat photos).
- **P07:** new `image_info/attributes.json` (pattern, sleeve length, neckline). The new flag `--no-attributes` skips it.
- **P19:** the texture step receives the hard garment mask, the main view, the back photo and the on-person flag.
- **`run_summary.json`:** new keys `back_image`, `main_photo_view`, `presentation`; `selected_image` is the photo actually used.
- **Safety:** every new stage is wrapped so that a failure is printed and the run continues. No existing output file or JSON key was removed or renamed.

**Step defaults (from the plans):** segmentation v1 (P01), colour v1 mean-shift (P04), design v3_combo (P05), view "trained" (P16), textures v1 (P19). Each keeps `method="v0"` selectable.

**Tests added:**
- `tests/test_colour_regression.py`: B1, B2, B3, colour block, v0 selectable (6 tests).
- `tests/test_design_regression.py`: B4 folds versus real repeats, plain shirt, v0 selectable (4 tests).

**Full suite: 45 passed, 22 subtests passed** (it was 35 before this work).

**Scripts:** `scripts/p10_run_to_standard.py` converts real run outputs to the scoring format.

## Runs [V]
- **Smoke test on c_002:** `run_product_ingestion.py --cloth-id c_002 --size-id s_001 -o out/p10_pipeline_runs --no-attributes`.
- **Full run on all 5 photos** (log `out/p10_pipeline_runs/run_all_5.log`), with outputs in `out/p10_pipeline_runs/<cloth>/s_001/<run>/`. All 5 completed with exit code 0.
- **Scoring:** `p10_run_to_standard.py` then `evaluate.py --label p10_final_pipeline`.

## End-to-end result [V] (5 Mirra photos, approximate references, same scoring as v0)

| Area | v0 pipeline | New pipeline |
|---|---|---|
| Outline score | 0.658 | **0.919** (mask IoU 0.700 → 0.907, leakage 0.300 → 0.001) |
| Colour score | 0.808 | **0.951** (palette ΔE 5.77 → 1.47) |
| Design score | 0.164 | **0.768** (F1 0.133 → 0.648; no false design on the plain shirt) |
| View score | 0.000 | **1.000** (views and presentation 5/5; c_002 recognised as a back view) |
| **Pipeline score** | **0.407** | **0.909** |

Per-photo problems that remain:
- **c_003 (white/teal colour block):** segmentation v1 keeps only the white upper half (IoU 0.562). As a result:
  - the base colour comes out white (base ΔE 67.7);
  - the colour blocks are not found;
  - the shape step calls the half shirt "sleeveless".

  This is the P01 trade-off, being fixed in P15a. With v1_all the mask IoU is 0.939.
- **c_004 and c_005 designs:** F1 0.29; extra small regions and a merged text box. P15b is working on these.

## Judgement
- **Done for the first pass:** the pipeline runs end to end with every new method, the old behaviour stays selectable, and the score more than doubles (0.407 → 0.909) on the user's own photos.
- **Caveat:** the Mirra references are approximate and 4 of 5 garment masks come from SAM 2 candidates. The public-dataset results in each plan record are the stronger evidence.

## Second pass: the final defaults [V]
- **Setup:** `scripts/p10_run_all.py --runs out/p10_pipeline_runs_v2 --label p10_final_pipeline_v2`, holding the GPU lock.
  - Defaults: segmentation `v1_auto` (P15a), colour v1, design `v4_relabel` (P15b), views trained, textures v1.
  - The runner frees the SigLIP 2 labeller after design extraction.
- **First attempt (15:11):** stopped by Claude Code at 15:14 for low memory after 2 photos (`ISSUES.md` I22).
- **Restart (15:47, with the user's OK):** run with nothing else on the GPU. All 5 photos finished with exit 0 by 15:52, c_003 included, so c_003's earlier exit 1 came from the stop.

| Area | v0 | First pass | **Final** |
|---|---|---|---|
| Outline score | 0.658 | 0.919 | **0.974** (mask IoU 0.982; c_003 0.562 → 0.939) |
| Colour score | 0.808 | 0.951 | **0.962** (palette ΔE 1.13; c_003 base colour ΔE 67.7 → 1.08) |
| Design score | 0.160 | 0.774 | **0.903** (F1 0.648 → 0.848; c_003 colour blocks found; type accuracy 1.0) |
| View score | 0.000 | 1.000 | **1.000** |
| **Pipeline score** | **0.407** | **0.911** | **0.960** |

- **Corrected label:** the v0 and first-pass figures are after the c_004 label correction (`plans/01`); before it, they were 0.164 and 0.909.
- **What still fails:**
  - c_004 misses one of its 4 design regions and gets one extra (F1 0.571);
  - c_005 misses its small second text line (F1 0.667).

## Multi-photo demo [V]
`scripts/demo_read_garment.py` was run on two shuffled, renamed DeepFashion In-shop T-shirt sets from the test split (`out/demo_inputs/`, true views in `*_truth.json`). The demo reads views, outline, colour, design, shape and attributes without MongoDB.

| Set | Photos | View result | Correct? |
|---|---|---|---|
| id_00000297 | back, front, full-body front | front = full-body front, back = back | yes |
| id_00006674 | front, back | front = front, back = back | yes |

- **First run (15:08):** the front outlines failed. The top covers about 4.7 % of a full-body photo, and the old 5 % validity floor sent it to the v0 fallback, which covered the background (`out/demo/inshop_*/front_overlay.jpg`, kept).
- **Fix:** made in `step_02_0_segmentation.py` (`ISSUES.md` I23).
- **After the fix (15:54):** both sets outline only the top (`out/demo/inshop_*_after_fix/`). The views are unchanged and correct.
- **Weaknesses left on these 256 px photos:**
  - small false "logo" boxes on a necklace pendant and at a hand;
  - the shape step calls one sleeveless top "short", because shape is unreliable on photos of people (known, P06).

## Next
None for this plan. Possible later work: more design training data for small second text lines (c_005) and multi-part prints (c_004).
