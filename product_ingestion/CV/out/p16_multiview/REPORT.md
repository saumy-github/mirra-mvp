# P16 report: several unlabelled photos, automatic view detection

*Status: first pass finished and tested, 2026-11-20.*
*Written by the P16 sub-agent and saved here by the orchestrator (sub-agents cannot write report files). Below, `OUT` = `product_ingestion/CV/out/p16_multiview/`.*

## 1. Goal
Take a folder of 1 to N unlabelled photos of one garment and decide, for each photo:
- its view: front, back, side, additional or other;
- its presentation: flat or worn by a person.

Then choose the front and back together across the set and flag photos of a different garment. With a single photo, the pipeline behaves as before.

## 2. Files
- **New `product_ingestion/multi_view.py`**, with a command line: `python product_ingestion/multi_view.py <folder or images> --out view_assignment.json`.
- **New `product_ingestion/models/view_classifier/`:** `view_clf.joblib` (52 KB), `metrics.json`, `README.md`.
- **Edited `step_01_1_garment_router.py`:** `GarmentRouter(method="trained"|"v0")`, default "trained", which falls back to the old CLIP path if the model cannot run. `ViewScore` gains `presentation` and `role`. New `--method` flag.
- **Edited `step_01_0_view_selection.py`:**
  - `select_primary_image(dir, skip_clip=False, method="trained")`;
  - `run_view_selection(dir, method)`;
  - new `select_views(dir)`.
  `list_cloth_images` is unchanged.
- **Scripts** (`CV/scripts/p16_*.py`): common, extract_features, cpu_cues, train, train_aux, pres_ensemble, geometry, tune, sets, build_bundle, chosen_cm, eval_files, check_step01.
- **Cached features:** `OUT/features/` (float16, about 60 MB).

## 3. How to call it
```python
from multi_view import assign_views, write_view_assignment_json
from step_01_0_view_selection import list_cloth_images, select_primary_image, select_views

selection = select_primary_image(cloth_dir, skip_clip=args.skip_clip)   # existing call; method="v0" = old CLIP
va = select_views(cloth_dir)                                             # = assign_views([paths...])
write_view_assignment_json(va, run_dir / "image_info" / "view_assignment.json")
primary = va.front          # str path; va.back is a str or None
# va.sides, va.details, va.others (size chart / label), va.outliers (another garment)
# va.photos[i]: view, view_probs, presentation, blur, garment_area, face_found, usability, same_garment_score, role
# va.method starts with "fallback" if the model could not run (first photo = front; reason in va.notes)
```
- **Never fails on the caller:** `assign_views` does not raise for model problems.
- **Output file:** `to_dict()` gives the JSON. It is a new file; no existing keys change.
- **Device:** `assign_views` loads SigLIP 2 on the GPU (about 1 GB) when CUDA is available, so the caller should hold the GPU lock or pass `device="cpu"`.

## 4. Method
- **View probabilities:** a frozen `google/siglip2-base-patch16-224` image embedding (photo padded to a square with its border colour, at 256 px), then logistic regression gives front, back, side and additional.
- **Presentation:** the mean of a trained logistic regression and zero-shot prompt probabilities (weight 0.5).
- **"Other" (size chart, label, packaging):** zero-shot, from stored prompt embeddings.
- **Cues:** blur (Laplacian variance), garment area and frame contact, Haar face, a Lab colour histogram.
- **Same-garment check:** pair logistic regression on embedding cosine similarity plus colour overlap.
  - Photos are grouped by correlation clustering: all partitions when N ≤ 8, average linkage above that.
  - The largest group is the garment; the rest are outliers.
- **Joint choice:** the best sum of log-probabilities over two different photos. A back is accepted only if its probability is at least 0.5.
- **Tuned settings:** back threshold 0.5, usability weight 0.0, "other" threshold 0.6, tuned on held-out training items.

## 5. Commands
`p16_extract_features.py siglip2` (and `marqo`), `p16_cpu_cues.py`, `p16_train.py`, `p16_train_aux.py`, `p16_pres_ensemble.py`, `p16_geometry.py siglip2`, `p16_tune.py siglip2 none lr` (also `marqo lda lr` and `marqo lda nb`), `p16_build_bundle.py siglip2 none lr`, `p16_chosen_cm.py`, `p16_eval_files.py`, `p16_check_step01.py`.

Seeds are fixed at 0, and every GPU use was under `gpu_lock("p16")`.

## 6. Labels and data caveats
- **Label mapping** (In-shop file suffixes):
  - `1_front` + `4_full` = front; `3_back` = back; `2_side` = side; `7_additional` = additional;
  - `6_flat` (3 photos) = front.

  "additional" is mostly other full-body poses, not close-ups, so the front/additional boundary is blurry.
- **Overlap between splits:** 10,604 train and 1,179 test photos, but 636 item ids appear in both, as different photos. Metrics are therefore also given on the 432 test photos of unseen items.
- **Test classes:** front 831, additional 255, back 57, side 36. Imbalance is handled with balanced class weights (logistic regression) or balanced resampling (naive Bayes, KNN, MLP).

## 7. Results
**Zero-shot views, In-shop test** (`results_view_zeroshot.csv`):

| Model | Acc | Macro-F1 | Recall front / back / side / additional | Mirra 5 |
|---|---|---|---|---|
| SigLIP 2 | 0.738 | 0.499 | 0.96 / 0.97 / 0.44 / 0.00 | 5/5 |
| Marqo-FashionSigLIP | 0.744 | 0.524 | 0.96 / 0.98 / 0.58 / 0.00 | 4/5 |

**Trained view classifiers** (`results_view.csv`: 32 rows = 2 backbones × {none, PCA64, LDA, PCA+LDA} × {naive Bayes, KNN, logistic regression, MLP}; selected on held-out validation items):
- **Best by validation macro-F1:** Marqo + LDA + naive Bayes, 0.615 (test accuracy 0.663, macro-F1 0.625).
  - Most logistic regression, MLP and LDA + naive Bayes variants sit at test macro-F1 0.59-0.63, within noise of each other.
  - KNN is worst (0.39-0.42), and PCA alone hurt.
- **Shipped: SigLIP 2 + logistic regression** (calibrated probabilities, best back recall, 5/5 Mirra views).
  - Test accuracy 0.649, macro-F1 0.611.
  - Recall: front 0.64, back 0.98, side 0.86, additional 0.57.
  - Precision: front 0.88, back 0.67, side 0.31, additional 0.38.
  - Unseen items only: accuracy 0.664, macro-F1 0.536.
- **Dominant error:** true fronts predicted as "additional" (240 of 831).
- **Why zero-shot looks more accurate:** it calls almost everything "front". Training mainly buys back and side recall.

**Presentation (flat or person):**
- **VITON-HD:** trained models reach 0.99-1.00, but that is close to a white-background shortcut.
- **Mirra:** trained logistic regression alone gets 3/5, zero-shot 5/5 (0.80 on VITON).
- **The 50/50 mix:** VITON 1.00 and Mirra 5/5. The weight was chosen after seeing the Mirra photos (n = 5), so this is indicative only. No mannequin labels exist.

**Cues:**
- Haar faces are found on 0.84-0.85 of front photos but only 0.07 of back photos, a strong back cue.
- Adding the cues to the embedding did not help (macro-F1 0.611 → 0.604). The neckline-depth cue was not done.

**Same-garment pairs** (160 positive, 160 negative): AUC 0.942. Embedding cosine alone gives 0.942 and colour alone 0.637, so colour adds nothing.

**Set level, on cached features** (In-shop test items with ≥ 2 photos; 100 sets, about half with one photo of another garment added):

| Variant | Front OK (n=81) | Back OK (n=14) | Front-back pair OK | Foreign photo found (n=54) |
|---|---|---|---|---|
| First photo = front (shuffled) | 0.617 | | | |
| Zero-shot, joint choice | 0.840 | 0.857 | 0.728 | 0.963 |
| **Trained, joint choice (chosen)** | **0.877** | **0.929** | **0.790** | **0.963** |
| Trained, no same-garment check | 0.679 | 0.857 | 0.605 | 0.000 |

**Set level, end to end on real files** (60 sets copied to `OUT/testsets/` with shuffled names and a `truth.json`):

| Subset | Front OK | Back OK | Back correctly absent | Pair OK | Foreign found | False outlier rate |
|---|---|---|---|---|---|---|
| All 60 sets | 0.854 (n=48) | 1.00 (n=9) | 0.882 (n=51) | 0.750 (n=48) | 0.967 (n=30) | 0.088 |
| Unseen items only | 0.909 (n=11) | 1.00 (n=1) | 0.900 (n=10) | 0.818 (n=11) | 1.00 (n=6) | 0.042 |

The unseen-item numbers rest on only 11 sets, so they are anecdotal.

**The 5 Mirra photos:**
- **Views:** front, back, front, front, front. This matches the reference labels, with c_002 as the back (p(back) = 0.989).
- **A single photo is always returned as the front;** for c_002 a note records that it looks like a back view.
- **Presentation:** all 5 correct.
- **Mixed folder of the 5 different garments:** 4 of the 5 are flagged as different garments, the maximum possible, since one photo must stay as the reference.

**Step files** (`check_step01.json`):
- `select_primary_image` on a single photo gives `single_photo`.
- Sets of several photos give `trained_joint_front_view`.
- `method="v0"` still falls back to the first image on torch 2.4.1, and `skip_clip` is unchanged.
- "Other" detection fires on a synthetic size chart (0.80) and care label (0.91), but on none of the 1,179 In-shop test photos.

## 8. Earlier attempt kept
`OUT/try_01_cut_objective/` is the first same-garment algorithm. It kept 2 of the 5 different Mirra garments in the mixed folder. It was replaced by correlation clustering, which flags 4 of 5.

## 9. What worked and what did not
- **Worked:**
  - **The set-level logic** (joint choice plus the same-garment check) turns a weak per-photo classifier (macro-F1 0.61) into about 0.85-0.88 correct fronts per set, against 0.62 for "take the first photo".
  - **Back detection is strong** (recall 0.98).
  - **The same-garment check** is the largest single gain.
- **Did not work:**
  - **A clean 4-class view model:** "additional" is ambiguous.
  - **PCA, KNN and the added cues** did not help.
  - **Presentation training:** it relies on a background shortcut.
  - **Usability weighting** changed nothing.
  - **Colour overlap** adds nothing to the same-garment check.
- **Why:** the In-shop photos are all worn by models. There are no flat lays, size charts or close-ups, so the classes "detail", "other", "flat" and "mannequin" have little or no real training data.

## 10. Issues
- **CLIP ViT-L/14:** stopped by the orchestrator (memory and disk) and dropped, so the third zero-shot baseline was not done.
- **Memory:** the first feature extraction loaded whole parquet tables and ran out of memory. It was rewritten to stream batches of at most 32 images with float16 features. The old features are kept in `OUT/features/v0_unstreamed/`.
- **Slow MLP:** the sklearn MLP was very slow under CPU contention. It was fixed with resampling, a smaller network and a 4-thread cap. The shipped model is logistic regression, so this does not affect it.
- **Disk:** C: fell to about 1.2 GB free, so the test sets were capped at 60.
- **Not done:**
  - SIFT/ORB/HOG matching for the same-garment check;
  - the neckline-depth cue;
  - fine-tuning the last layers;
  - mannequin labels;
  - real size-chart photos;
  - wiring the back photo into P19 (a runner task).

## 11. Recommendation
- **Wiring:** call `select_views(cloth_dir)` in `run_product_ingestion.py` right after `select_primary_image` and write `image_info/view_assignment.json`.
- **Which photo goes where:** use `va.front` for segmentation, colour and design, and `va.back` (when present) for the back panel in P19.
- **Default:** keep "trained", with `method="v0"` as the baseline.
- **Numbers to quote:** the set-level ones (about 0.85 correct fronts, 0.97 foreign-photo detection), not the per-photo macro-F1.
- **Next step:** add real flat-lay, mannequin, close-up and size-chart photos (the user's L1 photos) and retrain.
