# P06 report: shape attributes from the outline

*Status: first pass finished. Date: 2026-11-20.*
*Written by the P06 sub-agent and saved here by the orchestrator (sub-agents cannot write report files). Every number comes from a run of the scripts listed below.*

## 1. Goal
Read the garment's shape from its mask outline:
- **landmarks:** neck, shoulder, armpit, cuff and hem points;
- **sleeve length class;**
- **neckline depth;**
- **fit and ratios:** hem/chest, sleeve/body length, cuff/bicep, chest/length;
- **corner and keypoint detectors compared,** with every output saved;
- **the ratio distribution on VITON-HD,** compared with the fixed CLO ratios in `step_05_0_panel_generation_clo.py`.

## 2. How to call it
```python
import sys; sys.path.insert(0, "product_ingestion")
from cv_shape import garment_landmarks, analyze_shape, draw_overlay, detect_keypoints
res = garment_landmarks(mask)     # mask: 2-D uint8 0/255 or bool, upright, any size; never raises
```
`garment_landmarks` returns a JSON-serialisable dict:

| Key | What it holds |
|---|---|
| `ok` | False means the call failed and only `error` is meaningful |
| `landmarks` | `{name: [x, y]}` in input pixels (left and right are image left and right): neck_left, neck_right, neck_dip, shoulder_left/right, armpit_left/right, cuff_left_upper/lower, cuff_right_upper/lower, hem_left/right. The cuff points are absent when the garment is sleeveless |
| `polygons` | `torso`, `sleeve_left`, `sleeve_right` as lists of [x, y]; intersect them with the mask to get each panel's pixels |
| `sleeve`, `sleeve_class` | Sleeve class: sleeveless, short, elbow, three_quarter or long |
| `neckline` | depth_px, depth_over_garment_length, width_px, shape (v, round or flat), notch_fullness |
| `fit` | chest_to_length, shoulder_to_chest, bbox_width_to_height, shoulder_drop_frac, shoulder_slope_deg, dropped_shoulder |
| `ratios` | hem_to_chest, sleeve_to_body_length, wrist_to_bicep, wrist_to_bicep_band, chest_to_length, length_to_chest, shoulder_to_chest, neck_depth_to_length, hem_to_chest_hough |
| `lengths_px` | Pixel lengths of the measured lines |
| `methods` | Which method found each landmark (armpit: convexity_defect or width_profile_fallback) |
| `flags` | Warnings such as touches_image_border:top, armpit_height_asymmetric, sleeves_unequal |

Other public functions:
- `draw_overlay(image_bgr, res)` draws the landmarks and measured lines on a photo.
- `detect_keypoints(gray, method, region, n)` runs one detector: harris, shi_tomasi, hessian, fast, orb, sift or akaze.
- `contour_curvature_points`, `convexity_defects`, `hough_outline_lines` and `clean_outline` are also available.

Check `res["methods"]["armpit"]` and `res["flags"]` before trusting a result.

## 3. Method (one line each)
- **Outline cleanup:** keep the largest component, fill small holes, resample to 900 points, Gaussian-smooth.
- **Slit opening:** long sleeves hanging against the body leave an enclosed gap. A 3 px channel is cut from the gap to the garment's bottom so the gap becomes a notch in the outline.
- **Armpits:** the deepest convexity defect of the convex hull in each half (depth at least 2 % of height). Fallback: the steepest drop in the row-width profile.
- **Neck points:** the highest points either side of the neckline dip. Neck depth is the dip below the line through those two points; V versus round comes from how full the notch is.
- **Shoulder points:** where the contour leaves the straight line fitted just outside each neck point.
- **Sleeve:**
  - The path from shoulder to armpit is a U: upper edge, cuff, lower edge.
  - The cuff corners are where the contour departs from the straight upper and lower edges.
  - No sleeve when the path has no turn of at least 25 degrees.
- **Hem corners:** the outer bottom corners of the body between the two armpits.
- **Sleeve class:** sleeve length / garment length, with breaks at <0.10 sleeveless, <0.40 short, <0.56 elbow and <0.70 three-quarter; anything longer is long. The breaks were chosen from the two clusters in the VITON histogram, not tuned on labels.
- **Hough:** HoughLinesP on the 1-pixel outline. The hem width is the extent of the near-horizontal lines in the bottom 10 %.
- **Detectors:**
  - Harris (blockSize 3, k 0.04) with non-max suppression.
  - Shi-Tomasi (goodFeaturesToTrack).
  - Hessian determinant (sigma 2).
  - FAST-9 (threshold 20).
  - ORB keypoints.
  - SIFT (DoG extrema).
  - AKAZE.
  - Contour curvature (turning angle over ±12 points).
  - Convexity defects.

  Each detector is capped at its strongest 150 points. A point counts as a hit when it lies within 3 % of the garment height of a landmark.

## 4. Commands
Run from the repo root (the scripts import `p06_common.py` from the same folder):
```
.venv/Scripts/python.exe product_ingestion/CV/scripts/p06_extract_viton.py   # 500 masks (every 4th of 2,032 rows), 24 photos
.venv/Scripts/python.exe product_ingestion/CV/scripts/p06_overlays.py        # Mirra 5 + VITON 24 overlays, mirra_shape.json
.venv/Scripts/python.exe product_ingestion/CV/scripts/p06_ratio_stats.py     # viton_shape.csv (500 masks, 13 s)
.venv/Scripts/python.exe product_ingestion/CV/scripts/p06_corners.py         # galleries and corner CSVs (~2.5 min)
.venv/Scripts/python.exe product_ingestion/CV/scripts/p06_sleeve_eval.py     # Mirra 5 + Fashionpedia val
.venv/Scripts/python.exe product_ingestion/CV/scripts/p06_summary.py         # summary tables, histogram, chance baseline
```

## 5. Outputs (`out/p06_shape/`)
- **Overlays:** `overlays/mirra_all.jpg` and `mirra_c_00N.jpg`; `overlays/viton_v000..v023.jpg` and `viton_sheet_0..3.jpg`.
- **Detector galleries:** `corners/c_00N_corners.jpg`, 18 tiles each: 7 detectors on the photo, 7 on the mask outline, contour curvature, convexity defects, Hough lines, and Canny for reference.
- **Corner CSVs:** `corners/mirra_corner_metrics.csv`, `viton_photo_corner_metrics.csv`, `viton_mask_corner_metrics.csv`.
- **Stats:**
  - `stats/corner_detector_summary.csv`, `stats/chance_baseline_outline.csv`;
  - `stats/viton_shape.csv`, `viton_ratio_summary.csv`, `viton_clo_compare.csv`, `ratio_hist.png`, `mirra_shape.json`;
  - `stats/sleeve_eval.json`, `sleeve_eval_mirra.csv`, `sleeve_eval_fashionpedia.csv`, `summary_stdout.txt`.
- **Cached inputs:** `viton_masks/` (500 PNG) and `viton_photos/` (24 JPEG).

## 6. Results

### 6.1 Landmark quality (visual audit of 24 VITON overlays)
- **17 acceptable, 7 failed.** The failures:
  - mesh or tight hanging long sleeves (3);
  - a turtleneck;
  - a tie-strap top;
  - a ruffled tank;
  - a loose long sleeve.
- **Armpit method:** convexity defect on 352 of 500 masks; the width-profile fallback on the other 148 (29.6 %), mostly long sleeves.
- **"Clean" subset:** 327 of 500 masks (defect armpits, no warning flags).

### 6.2 Mirra photos
| Photo | Predicted class | Sleeve/length | Hem/chest | Chest/length | Comment |
|---|---|---|---|---|---|
| c_001 | short (label elbow) | 0.232 | 0.496 | 0.515 | on a person, hands in pockets; dropped shoulder not detected |
| c_002 (back) | short | 0.228 | 0.996 | 0.594 | clean |
| c_003 | short | 0.157 | 0.868 | 0.541 | mask touches the top and bottom of the image |
| c_004 | short | 0.215 | 1.030 | 0.556 | clean; V-versus-round neck call wrong |
| c_005 | short | 0.174 | 0.428 | 0.586 | on a person; hands and belt break the hem |

Sleeve accuracy is 4/5 = 0.80, the same as always guessing "short" (the majority baseline), so this proves nothing. On-person photos distort the outline, so their ratios cannot be trusted.

### 6.3 VITON-HD ratio distribution (clean subset, n = 327 unless noted)
| Ratio | Mean | Std | p5 | Median | p95 |
|---|---|---|---|---|---|
| hem/chest | 1.131 | 0.309 | 0.295 | 1.162 | 1.362 |
| hem/chest, short sleeves (n=246) | 1.133 | 0.176 | 0.939 | 1.157 | 1.312 |
| chest/length | 0.484 | 0.081 | 0.405 | 0.473 | 0.597 |
| shoulder/chest | 1.179 | 0.171 | 0.891 | 1.202 | 1.391 |
| neck depth/length | 0.132 | 0.067 | 0.042 | 0.117 | 0.248 |
| sleeve/length, short only (n=246) | 0.203 | 0.056 | 0.136 | 0.193 | 0.323 |
| cuff/bicep (n=289) | 0.336 | 0.258 | 0.054 | 0.291 | 0.836 |

Class counts over all 500 masks: short 274, sleeveless 131, elbow 51, three-quarter 39, long 5. The "sleeveless" count is inflated by the tight-sleeve failures.

### 6.4 Against the fixed CLO ratios (`stats/viton_clo_compare.csv`)
- **HEM_TO_CHEST 0.9307:**
  - The outline median is 1.162 (clean subset) or 1.131 (all 500). 0.9307 sits at the 8.6th percentile, and only 11 % of tops fall within ±10 % of it.
  - This chest is measured between the two armpits; CLO's block may define chest differently.
  - A Hough-based hem measure gives median 1.010 and agrees only loosely with the contour hem (Spearman 0.40).
- **WRIST_TO_BICEP 0.784:**
  - The outline estimate has median 0.291 and coefficient of variation 0.77, so it is too noisy to use. In a flat photo the sleeve opening is seen at an angle and folded.
  - Keep the fixed value.
- **Worth reading from the photo:**
  - the sleeve class and sleeve/length (std 0.056 for short sleeves);
  - chest/length, shoulder/chest and neck depth;
  - hem/chest only from flat photos, and only once the chest definition matches CLO's.

### 6.5 Sleeve-length accuracy
| Data | n | Accuracy | Within one class | Majority baseline |
|---|---|---|---|---|
| Mirra 5 (approximate labels) | 5 | 0.80 | 1.00 | 0.80 |
| Fashionpedia val (street photos) | 196 | 0.306 | 0.480 | 0.439 |

On street photos the outline method is worse than always guessing the commonest class: arms are bent or crossed, the garment is cropped or hidden. It needs flat or mannequin photos.

### 6.6 Corner and keypoint detectors (500 VITON mask outlines)
Chance baseline: random points on the outline score precision 0.18, and recall 0.185 / 0.540 / 0.781 / 0.873 / 0.960 for 12 / 47 / 92 / 126 / 209 points.

| Detector | Points | Precision (top 40) | Recall |
|---|---|---|---|
| ORB | 331 | 0.672 | 0.727 |
| Contour curvature | 11.7 | 0.611 | 0.628 |
| Harris | 10.8 | 0.576 | 0.476 |
| AKAZE | 209 | 0.483 | 0.945 |
| FAST | 47 | 0.449 | 0.733 |
| Shi-Tomasi | 126 | 0.365 | 0.967 |
| Hessian | 93 | 0.328 | 0.960 |
| SIFT | 39 | 0.311 | 0.460 |
| Convexity defects | 3.2 | 0.844 | 0.261 |

- **On photos,** precision drops: ORB 0.535 on VITON photos and 0.335 on the Mirra photos. Prints and texture create corners, and only 31-52 % of the points lie on the outline.
- **Circularity caveat:** contour curvature and convexity defects use the same contour the landmarks come from, so their scores are an upper bound.
- **Choice:** the contour-based methods (convexity defects for armpits; curvature and line departure for shoulders, cuffs and hem) are the most reliable for named landmarks. Harris on the mask is the best generic detector (about 11 points, precision 0.58). The high recall of Hessian, Shi-Tomasi and AKAZE is at chance level for that many points.

## 7. What worked and what did not
- **Worked:**
  - Flat or mannequin short-sleeve and tank tops: 17 of 24 audited.
  - The slit opening and line-departure rules.
  - Sleeve class separates short from long on VITON.
- **Did not work:**
  - **Cuff/bicep from the outline.**
  - **On-person photos:** shape ratios unusable; c_001's dropped shoulder was missed.
  - **Odd garments:** tight hanging long sleeves, tie straps, ruffles, turtlenecks.
  - **Neckline depth:** the mask notch includes the inside of the collar, so c_002 (back) 0.056 versus c_004 (front) 0.022 is the opposite of the expected order. The rule "the front neckline sits lower than the back" could not be checked.

## 8. Issues
- **This report was returned as text,** not written to disk by the agent.
- **Two bugs were fixed:** 0/1 masks were read as empty, and an unsigned-integer overflow in the width fallback.
- **The first sleeve model failed on hanging sleeves** and was replaced. The old helpers are kept as fallbacks.
- **Not done:**
  - a hand-labelled landmark reference (landmark quality rests on the 24-overlay audit);
  - on-person sleeve and dropped-shoulder fixes;
  - a fit class (only raw numbers and `dropped_shoulder` are exposed);
  - a Fashionpedia neckline evaluation.

## 9. Recommendation
- **Where to use it:** `cv_shape.garment_landmarks` on flat product photos only.
- **For P19:** use `landmarks` and `polygons` as approximate panel-region hints. Fall back to the fixed layout when `methods.armpit == "width_profile_fallback"` or a border flag is set.
- **CLO ratios:** keep the fixed WRIST_TO_BICEP. Read hem/chest, chest/length, shoulder/chest and sleeve class per garment only after the chest definition is matched to CLO's.
- **Where landmarks come from:** the mask outline, not corners found in the photo.

Files created: `product_ingestion/cv_shape.py`; `CV/scripts/p06_common.py`, `p06_extract_viton.py`, `p06_overlays.py`, `p06_ratio_stats.py`, `p06_corners.py`, `p06_sleeve_eval.py`, `p06_summary.py`; everything under `out/p06_shape/`.
