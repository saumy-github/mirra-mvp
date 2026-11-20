# P01 report: garment outline (segmentation) and model comparison

*Status: first pass finished and tested, 2026-11-20.*
*Written by the P01 sub-agent and saved here by the orchestrator (sub-agents cannot write report files). Numbers are from its runs [V]; [I] marks inference. `OUT` = `out/p01_segmentation/`.*

## 1. Goal
Replace the weak segmentation step: SAM 2 with a centre-point prompt, the candidate with the highest predicted IoU, a buggy hole fill and a meaningless quality score. Compare many methods and combinations on the 5 Mirra photos and on public data with exact masks, fix B5-B7, and produce a clean outline.

## 2. Files
| File | What |
|---|---|
| `step_02_0_segmentation.py` | Rewritten. `method="v0"` is the original behaviour; the new default is `method="v1"`, with a variant `"v1_all"`. `run_segmentation(path, method=None)` keeps its return type `(SegmentationResult, bool)`. The environment variable `MIRRA_SEG_METHOD=v0` also selects the method. `SegmentationResult` gains optional `outline_polygon` and `details` |
| `cv_segment.py` (new) | Mask utilities (the B5 fix); wrappers for SAM 2, SegFormer, RMBG-1.4, YOLO, YOLOE and Grounding DINO; classical methods (GrabCut, K-means, mean-shift, region growing, MRF); voting; quality signals; outline |
| `scripts/p01_*.py` | build_subsets, common, raw_models, methods, public_summary, tables, figures, pipeline_check |

**v1 (default):**
1. SegFormer (`sayeed99/segformer_b3_clothes`) labels the photo. The garment is Upper-clothes + Dress (Skirt is added only if it covers less than 0.5 % of the image).
2. SAM 2 is prompted with the box around the largest garment component and one positive point at the garment pixel farthest from its border, asking for a single mask.
3. Clean-up: open/close, keep the largest component, fill holes smaller than 2 % of the garment.
4. Fallbacks: an RMBG-1.4 box plus centre point, then the v0 chain with fixed cleaning.

**v1_all (variant):** also includes the Skirt class, and removes SegFormer face, hair, arm and leg pixels from the SAM 2 mask.

## 3. Data
- **Mirra:** 5 photos with approximate references (4 of 5 come from SAM 2 candidates, which favours SAM 2 methods), scored with `evaluate.py`.
- **VITON-HD test** (150 rows, seed 0):
  - `viton_cloth`: flat product photos, with the exact cloth mask.
  - `viton_person`: the person photos, with the garment from the parsing labels (5 torso, 21/22 sleeves; checked by eye; noisy at sleeves and edges).
- **Fashionpedia val:** 100 street photos. The reference is the largest upper-body garment polygon, at least 8 % of the image and at least 70 % of all upper garments.
- **Scoring rules:**
  - Public masks are scored with `evaluate.mask_metrics` at a longest side of 512 px.
  - A method that finds nothing counts as an empty mask (IoU 0). `fail` = share of images with IoU < 0.1.
  - Times are per image on the shared GPU, so they are noisy.

## 4. Models and prompts tested
- **SAM 2 (`facebook/sam2-hiera-large`) prompt variants:**
  - `v0`: centre point + 4 corner background points, multi-mask, highest predicted IoU. Area outside 5-95 % triggers a retry with a 3×3 grid.
  - `centre`: centre point only.
  - Box + centre point, single mask, with boxes from RMBG, YOLOE, SegFormer, the rough v0 mask or Grounding DINO. Box-only variants too.
  - SegFormer box with an interior point, optionally with up to 4 negative points on face, hair and arms.
  - An adaptive Skirt rule.
  - Candidate rules: largest candidate not touching the border, or best agreement with RMBG.
- **RMBG-1.4:** salient object (IS-Net, the same family as U²-Net).
- **SegFormer:** TOP = {Upper-clothes, Dress}; ALL = TOP + Skirt.
- **YOLO:** `yolo26m-seg` person mask (a reference only; also with skin removed).
- **YOLOE:** text-prompted `yoloe-26m-seg`, with "t-shirt" alone or a 5-word list.
- **Grounding DINO tiny:** "t-shirt." box, then SAM 2.
- **Classical (syllabus Unit III):**
  - GrabCut from a rectangle or the RMBG box (seeded: GrabCut was not reproducible without a seed);
  - K-means (k = 4, Lab plus position);
  - mean-shift + K-means;
  - region growing (flood fill in Lab);
  - MRF (mean-field Potts) smoothing of the RMBG map.
- **Combinations:**
  - SAM 2 minus SegFormer skin;
  - a confidence-weighted vote of SAM 2 box masks;
  - a vote of SAM 2 + SegFormer + YOLOE;
  - a consensus medoid;
  - a majority of three top-class methods;
  - GrabCut or MRF refinement afterwards.

Each model ran once per image under `gpu_lock` and was cached. The v0 reproduction matches the saved baseline exactly (IoU 0.700, BF 0.617, leakage 0.300).

## 5. Results
### 5.1 Key methods (Mirra from `OUT/mirra_scores.csv`; public from `OUT/public_scores.csv`; all 58 methods in `OUT/summary_all_methods.csv`)

Column key:
- Mirra: IoU, boundary F at 1 % (BF1) and HD95 (% of the diagonal), against the 5 approximate references.
- P cloth, P person, P street: public IoU on VITON product photos, VITON person photos and Fashionpedia street photos.
- P macro: the mean of the three public sets, for IoU, BF1 and HD95.
- P fail: share of public images with IoU below 0.1.
- t: seconds per image.

| Method | Mirra IoU | Mirra BF1 | Mirra HD95 | P cloth | P person | P street | P macro IoU | P macro BF1 | P HD95 | P fail | t (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **v0 (old pipeline)** | 0.700 | 0.617 | 36.5 | 0.932 | 0.775 | 0.562 | **0.756** | 0.736 | 11.2 | 0.080 | 0.55 |
| SAM 2 v0 + B5 fix | 0.915 | 0.865 | 3.63 | 0.925 | 0.772 | 0.564 | 0.754 | 0.750 | 8.9 | 0.097 | 0.55 |
| SAM 2 centre, largest | 0.867 | 0.771 | 6.64 | 0.935 | 0.401 | 0.463 | 0.599 | 0.557 | 16.1 | 0.027 | 0.09 |
| SAM 2 + RMBG box | 0.824 | 0.683 | 8.85 | 0.943 | 0.397 | 0.479 | 0.606 | 0.562 | 15.9 | 0.013 | 0.19 |
| SAM 2 + YOLOE box | 0.595 | 0.599 | 40.2 | 0.863 | 0.894 | 0.233 | 0.663 | 0.661 | 25.6 | 0.269 | 0.31 |
| SAM 2 + Grounding DINO box | 0.950 | 0.904 | 2.75 | 0.948 | 0.861 | 0.840 | 0.883 | 0.884 | 4.45 | 0.027 | 0.51 |
| SAM 2 + SegFormer ALL box | 0.950 | 0.900 | 2.76 | 0.947 | 0.812 | 0.794 | 0.851 | 0.859 | 5.80 | 0.018 | 0.17 |
| **SAM 2 + SegFormer TOP box + point (= v1)** | 0.907 | 0.931 | 6.58 | 0.936 | 0.893 | 0.838 | **0.889** | 0.884 | 4.68 | **0.011** | 0.59 |
| SegFormer ALL box + point, minus skin (= v1_all) | **0.982** | **0.967** | **1.76** | 0.943 | 0.813 | 0.792 | 0.849 | 0.857 | 6.10 | 0.021 | 0.18 |
| Grounding DINO box + point, minus skin | 0.982 | 0.967 | 1.78 | 0.945 | 0.860 | 0.830 | 0.878 | 0.880 | 4.80 | 0.023 | 0.56 |
| SegFormer ALL box + negative points | 0.991 | 0.999 | 0.24 | 0.942 | 0.806 | 0.774 | 0.841 | 0.854 | 6.32 | 0.019 | 0.17 |
| majority of 3 top-class methods | 0.904 | 0.911 | 5.97 | 0.937 | 0.894 | 0.839 | 0.890 | 0.884 | 4.61 | 0.011 | 1.23 |
| SegFormer TOP alone | 0.896 | 0.893 | 6.16 | 0.921 | 0.889 | 0.838 | 0.883 | 0.860 | 4.88 | 0.013 | 0.09 |
| SegFormer ALL alone | 0.970 | 0.917 | 2.25 | 0.936 | 0.810 | 0.787 | 0.844 | 0.836 | 6.43 | 0.013 | 0.09 |
| RMBG salient | 0.818 | 0.636 | 10.6 | 0.941 | 0.399 | 0.463 | 0.601 | 0.551 | 16.2 | 0.013 | 0.11 |
| YOLO person (reference) | 0.610 | 0.429 | 29.4 | 0.560 | 0.388 | 0.471 | 0.473 | 0.404 | 28.2 | 0.127 | 0.05 |
| YOLO person minus skin | 0.677 | 0.645 | 24.9 | 0.557 | 0.866 | 0.831 | 0.751 | 0.713 | 17.0 | 0.127 | 0.13 |
| YOLOE, 5 prompts | 0.583 | 0.583 | 40.7 | 0.842 | 0.869 | 0.210 | 0.641 | 0.627 | 26.5 | 0.266 | 0.30 |
| YOLOE, "t-shirt" only | 0.194 | 0.195 | 80.2 | 0.307 | 0.739 | 0.000 | 0.349 | 0.339 | 63.3 | 0.618 | 0.27 |
| GrabCut from rectangle | 0.770 | 0.543 | 11.2 | 0.923 | 0.514 | 0.417 | 0.618 | 0.541 | 13.9 | 0.022 | 1.21 |
| GrabCut from RMBG box | 0.854 | 0.684 | 9.40 | 0.932 | 0.395 | 0.441 | 0.590 | 0.540 | 16.0 | 0.029 | 0.71 |
| MRF on RMBG | 0.818 | 0.636 | 10.6 | 0.940 | 0.398 | 0.462 | 0.600 | 0.552 | 16.2 | 0.013 | 0.13 |
| K-means, centre cluster | 0.463 | 0.450 | 39.5 | 0.604 | 0.486 | 0.297 | 0.462 | 0.463 | 17.8 | 0.238 | 0.02 |
| mean-shift, centre | 0.588 | 0.486 | 18.2 | 0.594 | 0.544 | 0.332 | 0.490 | 0.481 | 16.8 | 0.178 | 0.13 |
| region growing | 0.485 | 0.436 | 21.1 | 0.621 | 0.437 | 0.235 | 0.431 | 0.396 | 18.3 | 0.304 | 0.01 |
| vote of 3 | 0.903 | 0.810 | 5.42 | 0.944 | 0.729 | 0.492 | 0.722 | 0.699 | 12.1 | 0.011 | 0.56 |
| consensus medoid | 0.906 | 0.811 | 5.38 | 0.945 | 0.791 | 0.546 | 0.761 | 0.740 | 10.3 | 0.011 | 1.16 |

Real entry point `run_segmentation()` on Mirra (per-photo IoU c_001..c_005):

| Method | Mean IoU | c_001 | c_002 | c_003 | c_004 | c_005 |
|---|---|---|---|---|---|---|
| v0 | 0.700 | 1.000 | 0.728 | 0.785 | 0.592 | 0.395 |
| v1 | 0.907 | 0.997 | 0.997 | **0.562** | 0.989 | 0.989 |
| v1_all | 0.982 | 0.997 | 0.997 | 0.939 | 0.989 | 0.987 |

### 5.2 Paired bootstrap on IoU (2,000 resamples, 95 % CI; `OUT/paired_bootstrap_iou.csv`)
| Comparison | VITON product | VITON person | Fashionpedia street |
|---|---|---|---|
| v1 − v0 | +0.004 (−0.014..0.023) | **+0.118 (0.082..0.156)** | **+0.277 (0.213..0.342)** |
| v1 − (v0 + B5 fix) | +0.011 (−0.011..0.035) | +0.121 (0.082..0.165) | +0.274 (0.208..0.338) |
| v1 − Grounding DINO box | −0.013 (−0.027..−0.003) | +0.032 (0.013..0.056) | −0.002 (−0.036..0.031) |
| v1 − SegFormer TOP alone | +0.015 (0.006..0.027) | +0.004 (0.002..0.006) | 0.000 (−0.023..0.021) |

### 5.3 Figures
- `OUT/contact_sheet_selected.jpg`: 23 methods × 5 photos.
- `OUT/contact_sheet_all.jpg`: all 58 methods.
- `OUT/methods/<method>/<cloth>/{mask.png, overlay.jpg}`.

### 5.4 Outline
- **Method:** Gaussian-smooth the mask (sigma 0.4 % of the diagonal), take the largest external contour, and simplify it with Douglas-Peucker (epsilon 0.15 % of the diagonal).
- **Example:** c_001 goes from 3,356 contour points to a 57-point polygon.
- **Outputs:** `OUT/outline/pipeline_v1*/<cloth>/{outline.png, outline_overlay.jpg, polygon.json}`; `SegmentationResult.outline_polygon` carries the polygon.
- This replaces "colour the background and run edge detection". The accuracy of the outline itself was not measured separately.

### 5.5 What worked and what did not
1. **The B5 fix alone** raises Mirra IoU from 0.700 to 0.915 (c_004 0.592 → 0.993, c_003 0.785 → 1.000; both masks touch the top-left corner). It changes nothing on public data (0.756 against 0.754): a real bug, but not what makes the method better.
2. **The v0 prompt is the main weakness:** IoU 0.932 on flat product photos, but 0.775 on person photos and 0.562 on street photos. The centre point picks the person or the print. v0 fails on 8 % of public images.
3. **A good box prompt is the key:** with the SegFormer garment box, macro IoU is 0.889. It clearly beats v0 on person and street photos and ties on flat ones.
4. **The box source matters:**
   - the RMBG box fails on people (it boxes the whole person);
   - YOLOE is good on people but finds nothing on 27 % of images;
   - the Grounding DINO box is the best single box (0.883; best on flat 0.948 and street 0.840) but needs a third model.
5. **Skin removal** gives no public gain but fixes Mirra c_003. Negative points give 0.991 on Mirra but lose on public data (0.841), probably by cutting sleeves [I]. This is the Mirra-reference bias at work.
6. **The TOP-versus-ALL trade-off is still open:**
   - SegFormer calls the dark teal lower half of c_003 "Skirt".
   - With TOP only (v1), c_003 drops to 0.562 (upper half only).
   - Adding Skirt (v1_all) gives Mirra 0.982, but public person and street photos drop (macro 0.849), because real skirts get included.
   - An adaptive rule did worse on both.
   - v1 was kept as the default on public evidence, with v1_all offered as the alternative.
7. **Voting and consensus did not help:** 0.72-0.79 macro, because wrong masks out-vote the right one. The one vote that worked (majority of three top methods, 0.890) is no better than v1 and takes twice as long.
8. **SegFormer alone is strong:** 0.883 macro. SAM 2 adds sharper edges and +0.015 IoU on flat photos.
9. **GrabCut refinement after SAM 2** made edges slightly worse (BF1 0.884 → 0.829). MRF smoothing changed nothing.
10. **Classical methods** (K-means, mean-shift, region growing) fail on printed garments or textured backgrounds: macro 0.43-0.49, with 18-30 % failures. GrabCut reaches 0.923 on flat product photos but only 0.41-0.51 on photos of people.
11. **The YOLO person mask** is only a reference. Its legs and head are included, and even with skin removed it fails on flat photos.
12. **Examples:** c_005 goes from 0.395 (v0, head included) to 0.989 (v1); c_004 from 0.592 to 0.989.

## 6. B6 and B7, and the new quality signals (`cv_segment.compute_quality`)
- **B6 fixed:** `edge_sharpness_score` is now the share of the mask boundary within 2 px of a Canny edge of the photo.
- **B7 fixed:** `hole_count` counts only enclosed holes of at least 50 px, with the mask padded so the outside is never a hole. `holes_before_fill` is recorded.
- **New keys:** `border_touch_ratio`, `sam_pred_iou`, `agreement_iou` (with the SegFormer garment mask), `holes_before_fill`, `edge_alignment`.
- **Score:** `quality_score` = coverage_score × mean(1 − 4 × border_touch, edge_alignment, agreement_iou, sam_pred_iou).
- **Mirra evidence (n = 5):**
  - v0's score is 0.98 for c_001, c_004 and c_005, although c_005's IoU is 0.395.
  - The v1 scores are 0.931 / 0.986 / **0.752** / 0.991 / 0.979. The lowest is c_003, exactly the photo where v1 is worst.
  - The correlation with IoU was not measured on public data.

## 7. Issues
- **U²-Net through rembg never ran in this venv:** `onnxruntime` is not installed, so the v0 "U²-Net fallback" has never worked here. RMBG-1.4 (IS-Net family) was used instead.
- **Ultralytics auto-installed packages:** YOLOE text prompts made Ultralytics run `pip install clip==1.0` (plus `regex`) on its own. torch, numpy and transformers are unchanged. Logged in `env/ENVIRONMENT.md` by the orchestrator.
- **Downloads:** yolo26m-seg (55 MB), yoloe-26m-seg (70 MB), mobileclip2_b (254 MB), Grounding DINO tiny (~0.7 GB, paused when the disk was low and resumed later).
- **Naming slip:** four methods were first named `comb_comb_*`; their folders are in `OUT/methods_stale_run1/` (not deleted). Re-run methods appear twice in `results/mirra_scores.csv`; the later timestamp is the valid row.
- **Caveats:** 5 Mirra images with a reference that favours SAM 2; noisy VITON person labels; coarser Fashionpedia polygons; GPU-contended timings.
- **Tests:** `test_segmentation_quality.py` = 11 passed.
- **Not done:** a time-versus-accuracy plot, the full 5-photo pipeline run, a public quality-versus-IoU correlation, a fine-tuned YOLO-seg (P17).

## 8. Recommendation
- **Default v1** (SegFormer TOP box + interior point → SAM 2, with fallbacks).
  - Public macro IoU 0.889 against 0.756 for v0: person +0.118 and street +0.277 (CIs exclude 0); flat photos equal.
  - Failures 1.1 % against 8.0 %; about 0.6 s per image; two models.
- **Alternative v1_all:** best on the Mirra photos (0.982, c_003 fixed) and on flat photos, but 0.849 on person and street photos. Use it when a top is photographed cropped, so the parser calls its lower half "Skirt", or when the photo is flat on a plain background.
- **Best single detector,** if a third model is acceptable: Grounding DINO box + SAM 2 (macro 0.883, Mirra 0.950; 0.982 with skin removal).
- **Cheapest fallback:** SegFormer TOP alone (0.883, 0.09 s).
- **Do not use:** YOLO person masks, single-prompt YOLOE, the classical methods, voting, GrabCut refinement.
- **Open question:** whether v1 or v1_all fits Mirra's own photos better needs more of them.
