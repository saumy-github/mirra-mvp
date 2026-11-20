# 08 · P05 Two-level outlining: design regions on the shirt

*Status: done (first pass), accepted; `v3_combo` is the new default in `step_04_0_design_extraction.py` (v0 selectable)*
*Date: 2026-11-20, 06:52 to 10:02 (paused 07:50 to 09:10 by the usage limit) (end = when this record was written, from the file time; start times are estimates)*
*Full report: `out/p05_design/REPORT.md`. Module: `product_ingestion/cv_design_regions.py`.*

## Goal
The user's idea: outline the shirt first (level 1), then outline and label each design on it (level 2): text, graphic, logo, stripes, colour block, pattern.

## What changed [V]
- **B4 fixed:** the FFT "pattern" test now uses a windowed inner patch, compares peaks with the radially averaged spectrum, ignores low (fold) frequencies, and needs mirrored peak pairs.
  - Old test: fired on 100 % of plain and 100 % of printed Fashionpedia garments.
  - Fixed test: 8.3 % of plain and 40.9 % of printed.
- **Ten region methods compared:** edges, colour deviation, Gabor and wavelet texture, Hough stripes, OCR, SAM 2 point grid, Grounding DINO, and three combinations. Zero-shot relabelling with SigLIP 2 and FashionSigLIP.
- **New default `v3_combo`:** colour-deviation regions, OCR text boxes, Hough stripes, colour blocks, and cleaned Grounding DINO boxes, merged by priority.

## My checks [V]
- Scores in `results/mirra_scores.csv`, reference masks:
  - v3_combo: design score 0.785 (F1 0.59, pixel IoU 0.763, type accuracy 1.0).
  - With SigLIP 2 relabelling: 0.830.
  - v0 on the same masks: 0.199.
- Contact sheet viewed by eye. v0 draws huge wrong boxes, including one around the whole plain pink shirt. v3_combo boxes:
  - BOSTON as text;
  - nothing on the plain shirt;
  - c_003's script text, stripe band and both colour blocks;
  - c_004's graphic and neck logo;
  - CALIFORNIA as text.
- Remaining errors: small false pieces near the hand on c_005, c_004's second text line lost, and BOSTON and "Leotude" merged into one box.

## Results [V] (5 Mirra photos, reference masks)

| Method | F1 @IoU 0.3 | Pixel IoU | Type accuracy | False positive on the plain shirt | Colour blocks |
|---|---|---|---|---|---|
| v0 (old) | 0.213 | 0.384 | 0.00 | yes | no |
| colour deviation (classical) | 0.590 | 0.768 | 0.50 | no | no |
| OCR text boxes | 0.467 | 0.507 | 1.00 | no | no |
| Grounding DINO alone | 0.363 | 0.624 | 0.25 | yes | no |
| SAM 2 point grid | 0.280 | 0.404 | 1.00 | no | no |
| Gabor + wavelet texture | 0.000 | 0.267 | - | yes | no |
| **v3_combo (new default)** | **0.590** | **0.763** | **1.00** | no | **yes** |
| v3_combo + SigLIP 2 relabel | **0.707** | 0.785 | 1.00 | no | yes |

With the old leaky v0 masks every method drops (v3_combo to F1 0.39). The plain shirt's mask includes the background, so false positives appear. Good masks (P01) come first.

## Judgement
- Accepted. This is the biggest single improvement so far (design score 0.164 → 0.785 with reference masks), and the method comparison is rich for the paper:
  - classical colour deviation is strong but blind to white-on-white text;
  - OCR is precise on text;
  - Grounding DINO has high recall but is noisy, and becomes useful only after cleaning;
  - texture filters (Gabor, DWT) fail on folds.
- **Caveat:** thresholds were set while looking at these 5 photos, so the Mirra numbers are optimistic. The Fashionpedia check shows the plain-versus-printed decision does not transfer to street photos.

## Next
- **P15+:** wire the SigLIP 2 relabelling into the default (+0.12 F1, precision 0.93); add a B4 regression test (my `tests/` job).
- **P10:** re-run with P01's masks once P01 finishes.
