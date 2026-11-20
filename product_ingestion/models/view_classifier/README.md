# View classifier (P16, CV project)

*Status: trained 2026-11-20; used by `product_ingestion/multi_view.py`*

`view_clf.joblib` is one scikit-learn bundle (joblib, ~50 KB) with:

| Part | What it is |
|---|---|
| `backbone` | `siglip2` = frozen `google/siglip2-base-patch16-224` image embedding (768-d, L2-normalised). The weights are not stored here; they are loaded from the Hugging Face cache (safetensors, works on torch 2.4.1). |
| `view_model` | Logistic regression (C=2, `class_weight="balanced"`), classes `front, back, side, additional`. |
| `pres_model` | Logistic regression flat (product photo) versus person. At run time it is averaged 50/50 with zero-shot prompt probabilities (`pres_zs_weight`, `zs_pres`). |
| `same_model` | Logistic regression on 4 pair features (embedding cosine, colour overlap) predicting "same garment". |
| `zs_text` | Mean prompt embeddings for the zero-shot "other" check (size chart, label, packaging). |
| `params` | Set-level decision settings (`back_threshold` 0.5, `usability_weight` 0.0, `other_threshold` 0.6). |

## Labels
DeepFashion In-shop file-name suffix to class: `1_front` and `4_full` to **front**, `3_back` to **back**, `2_side` to **side**,
`7_additional` to **additional** (mixed: alternate poses and some close-ups; it is not a clean detail class), `6_flat` (3 photos) to front.
There are no training photos for "other" (size chart, label), so that check is zero-shot only.

## How trained
`product_ingestion/CV/scripts/p16_extract_features.py siglip2` (features cached once), then
`p16_train.py` (classifier comparison), `p16_tune.py siglip2 none lr` (set-level parameters on held-out train items),
`p16_build_bundle.py siglip2 none lr` (final fit on the whole In-shop train split: 10604 photos).
Seeds fixed (0). All numbers and the other models tried are in
`product_ingestion/CV/out/p16_multiview/` (`results_view.csv`, `results_presentation*.csv`, `results_same_garment.csv`, REPORT).

## Metrics (In-shop test split, 1179 photos; see `metrics.json` for the selection record)
Accuracy 0.649, macro-F1 0.611; recall front 0.64, back 0.98, side 0.86, additional 0.57. Training and test splits share 636 item ids
(different photos), so the same numbers are also given for the 432 test photos of unseen items in `results_view.csv` (`unseen_*`).
