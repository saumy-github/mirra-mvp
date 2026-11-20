# 03 · P06 Shape: landmarks, sleeve length, ratios, corner detectors

*Status: done (first pass), accepted with limits*
*Date: 2026-11-20, 07:10 to 09:27 (paused 07:50 to 09:10 by the usage limit) (end = when this record was written, from the file time; start times are estimates)*
*Full report: `out/p06_shape/REPORT.md`. Module: `product_ingestion/cv_shape.py`.*

## Goal
Read the garment's shape from its outline (landmarks, sleeve class, neckline, fit, ratios), compare corner and keypoint detectors with every output saved, and check the fixed CLO ratios against real tops.

## What was run [V]
- Landmarks and ratios on the 5 Mirra photos and 500 VITON-HD product masks (24 audited by eye).
- 9 detectors (Harris, Shi-Tomasi, Hessian, FAST, ORB, SIFT, AKAZE, contour curvature, convexity defects) plus Hough lines, on the photos and on the mask outlines, with a random-points chance baseline.
- Sleeve class against Fashionpedia val (196 tops).
- My check: `garment_landmarks` on the c_002 and c_004 reference masks returns `ok`, sleeve "short", armpits by convexity defect, and the same ratios as the report.

## Key results [V]

| Finding | Number |
|---|---|
| Landmarks acceptable on flat product photos (eye audit) | 17 of 24 |
| Best landmark source | The mask outline, using convexity defects for armpits and curvature or line departure for shoulders, cuffs and hem. Generic corner detectors on the photo mostly fire on prints: ORB precision 0.34 and Harris 0.19 on the Mirra photos |
| Best generic detector on the outline | Harris: about 11 points, precision 0.58. Hessian, Shi-Tomasi and AKAZE reach high recall only at chance level for the number of points they emit |
| Hem/chest of real tops vs CLO's fixed 0.9307 | Median 1.16 on 327 clean VITON tops; 0.9307 sits at the 8.6th percentile. The chest definitions may differ, so this needs checking before replacing the constant |
| Wrist/bicep from the outline | Not measurable: median 0.29 and coefficient of variation 0.77, because flat photos show the cuff at an angle. Keep CLO's fixed 0.784 |
| Sleeve class on street photos (Fashionpedia) | Accuracy 0.306, below the majority baseline of 0.439. Outline rules fail when arms are bent or cropped |

## Judgement
- Accepted as a careful negative-and-positive result. The agent added a chance baseline for the detectors, admitted where the method fails, and did not over-claim from the 5 Mirra photos (its 4/5 equals the majority baseline).
- **For the paper:** classical outline geometry (convexity defects, curvature) works for flat product photos. On-person and street photos need a learned model, which P07 trains on Fashionpedia labels. That contrast is a useful finding in itself.
- **For the pipeline:** use shape attributes only on flat photos (P16's presentation label decides that), and use the landmarks and torso/sleeve polygons as region hints for P19.

## Not done
- A hand-labelled landmark reference.
- Fixes for on-person photos.
- A fit class.
- A neckline-type evaluation.
