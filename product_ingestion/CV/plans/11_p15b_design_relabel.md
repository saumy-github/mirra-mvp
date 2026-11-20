# 11 · P15b Design improvement pass: SigLIP 2 relabelling, two fixes, new masks

*Status: done, accepted; `v4_relabel` is the new default in `step_04_0_design_extraction.py` (v3_combo and v0 selectable)*
*Date: 2026-11-20, about 14:10 to 14:50*
*Agent report: `out/p15b_design/REPORT.md`; outputs in `out/p15b_design/`.*

## Goal
- Put P05's best variant (zero-shot SigLIP 2 relabelling of the v3_combo regions) into the pipeline.
- Re-score design on P01's new masks instead of the old leaky v0 masks.
- Fix two known errors: c_004's caption text swallowed by a graphic box, and c_001's BOSTON and "Leotude" merged into one box.

## What changed [V]
`cv_design_regions.py` has four methods sharing one flow:

| Method | What it adds |
|---|---|
| `v3_combo` | P05's default, unchanged |
| `v3_fix` | The two fixes below |
| `v4_nofix` | SigLIP 2 relabelling |
| **`v4_relabel`** | The fixes plus relabelling (**new default**) |

- **Relabelling:**
  - SigLIP 2 base is loaded lazily and shared across regions.
  - Each region is cropped with 15 % padding and labelled from the P05 prompts; a "plain" prediction drops the region.
  - The model runs on the GPU or the CPU. If it cannot load, the regions are returned unrelabelled with a warning.
- **Fix (a):** a text box inside a non-text box (a caption under a print) is only removed by real overlap, not by being contained.
- **Fix (b):** inside an OCR text box, the ink is cut into glyphs. A separate small text line (smaller glyphs laid out as a line) gets its own box.

## Results [V] (after my label correction for c_004; see `plans/01` "Corrections")

| Method | Masks | Design F1 @0.3 | Pixel IoU | Design score |
|---|---|---|---|---|
| v0 | P01 v1 masks | 0.213 | 0.431 | 0.215 |
| v3_combo (P05 default) | P01 v1 masks | 0.648 | 0.799 | 0.774 |
| **v4_relabel (new default)** | P01 v1 masks | **0.848** | **0.864** | **0.904** |
| v0 | reference masks | 0.213 | 0.396 | 0.203 |
| v3_combo | reference masks | 0.590 | 0.787 | 0.792 |
| v4_relabel | reference masks | 0.827 | 0.859 | 0.895 |

- **No false design** on the plain shirt c_002 with any v3/v4 method.
- **Fix (b):** c_001 goes from F1 0.667 to 1.000 (BOSTON and "Leotude" are now two text boxes).
- **Fix (a):** the c_004 caption text is now found. It scored as a false positive only because my reference box was 20 px too low, which is now corrected.
- **Relabelling:** adds +0.07 to +0.15 F1 and brings type accuracy to 1.0 on matched boxes.
- **CPU equals GPU:** the relabelling numbers on the CPU match P05's GPU numbers (0.707 for v4_nofix on reference masks).

## Judgement
- Accepted. The design stage is now the strongest improvement in the project (design score 0.215 → 0.904 on the realistic masks).
- **Caveats:** thresholds for the line-split rule were set on c_001, the only photo with two text lines. With 5 photos this is a tuned baseline, not a general result.
- **Colour blocks:** on the v1 masks they are not found, because c_003's mask loses the teal half. That is P15a's problem, not a design-method problem.

## Next
- Re-run the pipeline with v4_relabel and P15a's segmentation (P10 second pass).
- A text-heavy public set would test the line-split rule; not done.
