# 07 · P16 Several unlabelled photos: automatic view detection and a trained view model

*Status: done (first pass), accepted; "trained" is the new default in step 01 (v0 selectable)*
*Date: 2026-11-20, 06:15 to 09:57 (paused 07:50 to 09:10 by the usage limit) (end = when this record was written, from the file time; start times are estimates)*
*Full report: `out/p16_multiview/REPORT.md`. Module: `product_ingestion/multi_view.py`. Model: `product_ingestion/models/view_classifier/`.*

## Goal
The user's requirement: the pipeline takes several photos of a garment, in any order and with any names, and works out by itself which is the front and which is the back.

## What changed [V]
- `select_views(cloth_dir)` and `assign_views(paths)` label each photo with its view (front, back, side, additional, other) and its presentation (flat or person).
- They choose the front and the back together across the set and flag photos of a different garment.
- The view model is SigLIP 2 image features plus logistic regression, trained on 10,604 DeepFashion In-shop photos labelled by their file names.
- View selection now actually runs on torch 2.4.1. The old CLIP path never loaded: v0 view score 0.

## My check [V]
- I ran `assign_views` (CPU) on a shuffled test set: method `trained:siglip2+none+lr`, a front chosen, no back.
- Both photos in that set were "additional" shots of the same item, and one was wrongly flagged as a different garment. That is the known false-outlier case, reported at 8.8 % of photos.

## Results [V]

| Measure | Value |
|---|---|
| Per-photo view, In-shop test (4 classes) | accuracy 0.649, macro-F1 0.611; back recall 0.98, front recall 0.64 (front is often confused with "additional") |
| Front correct per photo set (60 shuffled sets, end to end) | **0.854**, against 0.617 for "first photo = front" |
| Back found when present / correctly absent | 1.00 (n=9) / 0.882 (n=51) |
| Photo of another garment detected | 0.967 (n=30); false outlier rate 0.088 |
| Same-garment check | AUC 0.942; removing it drops the front-back pair accuracy from 0.79 to 0.61 |
| Mirra photos | views 5/5 (c_002 found as back, p = 0.989); presentation 5/5; mixed folder of 5 different shirts: 4 flagged as different (the maximum) |

Syllabus classifiers compared: naive Bayes, KNN, logistic regression and MLP, each with no reduction, PCA, LDA or PCA + LDA.
- Logistic regression, the MLP and LDA + naive Bayes are within noise (macro-F1 0.59-0.63).
- KNN is worst.

## Judgement
- Accepted. The set-level design is the real contribution: choosing front and back jointly plus the same-garment check turns a modest per-photo classifier into about 85 % correct fronts per set, against 62 % for "first photo".
- **Limits for the paper:**
  - the training photos are all on-model, so flat-lay, mannequin, close-up and size-chart classes have little or no real data;
  - the presentation mix weight was picked after seeing the 5 Mirra photos;
  - Mirra has only one back view.
- The user's own photos (later phase L1) would fix the data gap.

## Next (P10, mine)
- In `run_product_ingestion.py`: call `select_views`, write `image_info/view_assignment.json`, use `va.front` for the main stages and `va.back` for the back panel (P19's `back_rgba`).
- Pass the presentation to P19 (`on_person`) and P04 (skin handling).
