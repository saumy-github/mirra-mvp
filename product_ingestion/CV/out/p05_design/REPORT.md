# P05 report: two-level outlining (design regions on the shirt)

*Status: first pass finished, 2026-11-20.*
*Written by the P05 sub-agent and saved here by the orchestrator (sub-agents cannot write report files). All numbers come from its runs. The reference labels are approximate and there are only 5 photos, so treat the scores as indicative. Below, `OUT` = `out/p05_design`, `SC` = `scripts`.*

## 1. Goal
- **Level 1:** the garment outline, from the reference masks (oracle) or the v0 masks.
- **Level 2:** each design region inside the garment, with a type: text, graphic, logo, stripes, colour_block or pattern.

Every method's output is saved and scored with `evaluate.py`.

## 2. Bugs reproduced and fixed
**B4: the FFT "pattern" test fires on everything** (`SC/p05_b4_repro.py`, `OUT/b4_repro/b4_repro.json`).
- A synthetic plain grey tee with two soft folds: v0 reports `has_design=True`, type "pattern", 100 % coverage, FFT ratio 465.6.
- Fashionpedia, 108 plain and 44 printed garments: the old test fires on 100 % of both. Median ratio is 100.6 on plain against 106.2 on printed (AUC 0.571).

**The fix,** in `cv_design_regions.periodicity()`:
- It uses the largest central patch at least 95 % inside the eroded garment, on shading-free luminance, with a Hann window.
- Each frequency is compared with the median of its own ring (radially averaged spectrum). Low radii (below max(8, 0.03 n)), where folds live, are ignored.
- A peak must be a sharp spike (at least 4× its neighbourhood and 12× its ring median) and must have a mirror partner. At least 2 pairs are needed, or 1 very strong pair.

**Result:** the plain folded tee is no longer "periodic", while dotted and striped tees are. On Fashionpedia the test now fires on 8.3 % of plain against 40.9 % of printed garments. A first version without the low-radius and sharpness guards still fired on the folded tee.

**Outline and variance problems:**
- **Garment edge:** edges inside a band of 3 % of √area along the outline are ignored, and the background is no longer painted black.
- **Variance:** the variance check uses the 90th percentile instead of the maximum.
- **Shading removal:** a fabric model aware of colour blocks.
  - k-means in Lab, with close clusters merged; large pieces become blocks.
  - Each block gets a smooth local fabric colour.
  - The deviation map is the ΔE2000 from that local fabric colour.
- **Not used:** P03's `cv_enhance.design_edges` (the agent used its own Canny on flattened luminance) and `pywt` (it wrote its own Haar DWT).

## 3. Files and how to call
- **`product_ingestion/cv_design_regions.py` (new):** `detect_regions(rgb, mask, method)` returns `[{box (pixels), type, confidence, source}]`. Also `prepare`, `periodicity`, the region proposers, `rule_label`, `nms_merge`, `nms_priority`.
- **`step_04_0_design_extraction.py`:**
  - `DesignResult` gains `regions`, `method` and `main_type`.
  - `extract_design(rgba, method=None)`: `method="v0"` is the unchanged original (now also returning one region box). **The new default is `DEFAULT_METHOD = "v3_combo"`**, falling back to v0 if it raises.
  - `graphic_image` is the crop of the largest design region.
  - `design_type` keeps the old vocabulary for Step 3 (logo, text, pattern): graphic and stripes are reported as "logo". The true type is in `main_type` and `regions`.
- **Models:** the default needs EasyOCR and Grounding DINO tiny at run time. Without them it falls back to a connected-component text detector or no DINO boxes.
- **Tests:** `product_ingestion/tests` gives 41 passed, 20 subtests passed. No B4 regression test was added (`tests/` is the orchestrator's).

## 4. Methods tried
Outputs: `OUT/<try>/methods[_v0mask]/<method>/<cloth>/design_regions.json`, with overlays in `OUT/<try>/overlays*/`. `try_01` was the first pass, `try_02` the second, `try_03` and `try_03b` the final code.

| Method | What it does |
|---|---|
| v0 | The original extractor |
| b_classical | Edges on flattened luminance, outline band ignored, closing, contours, 90th-percentile variance |
| c_colour | Pixels with ΔE2000 > 12 from the local fabric colour, then connected pieces |
| d_texture | 12 Gabor filters plus 2-level Haar DWT energies, k-means (k = 3) |
| d_stripes | Hough lines grouped into an evenly spaced parallel family of at least 6 lines |
| e_text | EasyOCR (CRAFT) text boxes |
| f_sam2 | SAM 2 with a 7×7 point grid inside the garment, keeping masks that differ from the fabric |
| g_gdino | Grounding DINO tiny with the prompt "logo. text. graphic print. stripes." on the garment crop |
| h_combo | Colour + OCR + Hough + SAM 2 + colour blocks, merged with non-maximum suppression (NMS) |
| v2_combo | h_combo without SAM 2 |
| v3_combo | v2_combo plus cleaned Grounding DINO boxes (see below) |

How v3_combo cleans the DINO boxes:
- Priority NMS order: Hough, OCR, text_cc, DINO, colour.
- A DINO text box replaces a smaller OCR fragment it contains.
- DINO "stripes" are kept only if Hough agrees; other DINO types are relabelled by size.
- A garment judged plain keeps only its colour blocks.

**Zero-shot relabelling:** the v3 boxes were also relabelled with SigLIP 2 and Marqo-FashionSigLIP (single prompt or ensemble). The crop is padded by 15 %, and a "plain" prediction drops the region.

## 5. Results
**Reference (oracle) masks, mean of 5 photos:**

| Method | F1@0.3 | Precision | Recall | Pixel IoU | Type accuracy | False positives on plain c_002 | Colour blocks found |
|---|---|---|---|---|---|---|---|
| v0 | 0.213 | 0.400 | 0.350 | 0.384 | 0.000 | 1 | 0 |
| b_classical | 0.500 | 0.600 | 0.450 | 0.676 | 0.667 | 0 | 0 |
| c_colour | 0.590 | 0.740 | 0.550 | 0.768 | 0.500 | 0 | 0 |
| d_texture | 0.000 | 0.000 | 0.200 | 0.267 | none matched | 1 | 0 |
| d_stripes | 0.333 | 0.400 | 0.300 | 0.249 | 1.000 | 0 | 0 |
| f_sam2 | 0.280 | 0.400 | 0.250 | 0.404 | 1.000 | 0 | 0 |
| e_text | 0.467 | 0.600 | 0.400 | 0.507 | 1.000 | 0 | 0 |
| g_gdino | 0.363 | 0.317 | 0.650 | 0.624 | 0.250 | 1 | 0 |
| v2_combo | 0.557 | 0.617 | 0.550 | 0.732 | 0.750 | 0 | 1 |
| **v3_combo (default)** | **0.590** | 0.640 | **0.650** | 0.763 | **1.000** | 0 | 1 |
| v3 + SigLIP 2 relabel (single prompt) | **0.707** | **0.933** | 0.650 | **0.785** | 1.000 | 0 | 1 |
| v3 + SigLIP 2 relabel (ensemble) | 0.707 | 0.933 | 0.650 | 0.785 | 0.625 | 0 | 1 |
| v3 + FashionSigLIP relabel (single) | 0.660 | 0.733 | 0.650 | 0.776 | 0.750 | 0 | 1 |
| v3 + FashionSigLIP relabel (ensemble) | 0.633 | 0.700 | 0.650 | 0.764 | 0.500 | 0 | 1 |
| h_combo (with SAM 2) | 0.481 | 0.457 | 0.550 | 0.732 | 0.750 | 0 | 1 |

**v0 masks** (which include background, arms and the person):

| Method | F1@0.3 | Precision | Recall | Pixel IoU | False positives on plain |
|---|---|---|---|---|---|
| v0 | 0.133 | 0.200 | 0.300 | 0.359 | 1 |
| b_classical | 0.133 | 0.200 | 0.300 | 0.384 | 1 |
| c_colour | 0.178 | 0.240 | 0.350 | 0.393 | 1 |
| d_texture | 0.200 | 0.200 | 0.200 | 0.424 | 0 |
| d_stripes | 0.200 | 0.200 | 0.200 | 0.200 | 0 |
| e_text | 0.467 | 0.600 | 0.400 | 0.507 | 0 |
| f_sam2 | 0.000 | 0.000 | 0.000 | 0.209 | 1 |
| g_gdino | 0.377 | 0.333 | 0.650 | 0.640 | 1 |
| h_combo | 0.107 | 0.073 | 0.400 | 0.265 | 1 |
| v2_combo | 0.213 | 0.267 | 0.400 | 0.265 | 1 |
| v3_combo | 0.391 | 0.407 | 0.650 | 0.357 | 1 |

Mask errors dominate here: the plain c_002 mask covers the background, so every method reports false positives.

**Zero-shot labelling of the 10 reference design boxes:**

| Labeller | Correct |
|---|---|
| rules | 5/10 |
| SigLIP 2, single prompt | 6/10 |
| SigLIP 2, ensemble | 5/10 |
| FashionSigLIP, single prompt | 7/10 |
| FashionSigLIP, ensemble | 8/10 |

With n = 10 these differences are noise.

**Fashionpedia plain versus printed** (v2_combo on CPU, 108 plain and 44 printed shirts, tops and sweaters):

| Measure | Plain / printed |
|---|---|
| Old FFT test fires | 100 % / 100 % |
| Fixed periodicity test fires | 8.3 % / 40.9 % |
| Any region found | 90.7 % / 95.5 % |
| v0 "has design" | 100 % / 100 % |

AUC of each signal for telling plain from printed:

| Signal | AUC |
|---|---|
| ΔE coverage fraction | 0.745 |
| Fixed periodicity | 0.663 |
| Old FFT | 0.571 |
| "Any region found" | 0.524 |

On street photos "any region" is not a useful plain/printed decision: hands, occlusion, background and buttons put the median deviation coverage at 10.7 % even on plain garments. The 0.4 % threshold for clean product photos does not transfer.

## 6. Figures
- `OUT/contact_sheet_oracle_masks.jpg`: 11 methods × 5 photos, with the level-1 outline in yellow and the level-2 boxes coloured and labelled by type.
- `OUT/contact_sheet_v0_masks.jpg`: 8 methods × 5 photos with the v0 masks.
- Per-method overlays in `OUT/try_0x/overlays*/`.

## 7. What worked and what did not
- **c_colour:** the best single method, but it cannot see white-on-white text (c_003 "whatever") and breaks the multi-colour CALIFORNIA print into small pieces.
- **OCR:** the best text finder (type accuracy 1.0), but it merges BOSTON and Leotude into one box.
- **Grounding DINO:**
  - It has the best recall (0.65) and finds c_003's faint "whatever" text and the stripe band.
  - On its own it is noisy: duplicate labels, "stripes" on the plain c_002 (score 0.32), type accuracy 0.25.
  - Cleaning its boxes is what made v3 the best combination.
- **SAM 2:** it over-segments letters and misses c_003 and c_005; it adds nothing in combinations.
- **Gabor + DWT texture segmentation:** failed; it fires on folds and shading.
- **Hough stripes:** they find c_003's band (only its sharper lower part) and never fire elsewhere.
- **Colour blocks:** c_003's white and teal blocks are found.
- **Remaining errors:**
  - c_005 still gets 3-4 small false "logo" pieces, near the hand and watch.
  - c_004's neck-logo box is offset.
  - c_004 loses the "Different yet SAME" text: the DINO graphic box contains the OCR text box and NMS drops it.

## 8. Issues
- **Disk:** C: dropped to about 0.2 GB free mid-run. Only the EasyOCR weights were downloaded; Grounding DINO was already cached. `try_01` used the fallback text detector.
- **GPU lock contention:** waits of up to 23 minutes. A stuck `try_02` was stopped and only the needed methods were re-run.
- **Not done:**
  - a B4 regression test;
  - a whole-pipeline run;
  - DWT with `pywt`;
  - SigLIP relabelling inside the pipeline;
  - SAM 2 prompted from DINO boxes;
  - type-level Fashionpedia evaluation.
- **Tuning:** thresholds (ΔE 12, closing, Hough rules) were set while looking at these 5 photos, so this is a tuned baseline, not a general result.

## 9. Recommendation
- **Default:** keep `v3_combo` (oracle F1 0.59, recall 0.65, type accuracy 1.0, no false positive on the plain shirt, colour blocks found), with `v0` selectable.
- **Best measured variant:** v3_combo with SigLIP 2 relabelling (F1 0.707, precision 0.93). It is not yet wired into `extract_design`; that is the next step.
- **Fix the outline first:** with the v0 masks every design method drops (v3 to 0.39). Re-run with the P01 winner's masks.
- **Plain versus printed on street photos:** learn a threshold on labelled data (ΔE coverage plus periodicity).
