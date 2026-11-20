# 06 · P07 Trained attribute models (pattern, sleeve length, neckline)

*Status: done (first pass), accepted with limits*
*Date: 2026-11-20, 06:15 to 09:56 (paused from 07:50 by the usage limit, then held back to save memory) (end = when this record was written, from the file time; start times are estimates)*
*Full report: `out/p07_attributes/REPORT.md`. Module: `product_ingestion/cv_attributes.py`. Models: `product_ingestion/models/attributes/`.*

## Goal
Trained classifiers for garment attributes (textile pattern, sleeve length, neckline), using the syllabus classifiers on top of frozen image features.

## What was run [V]
- Fashionpedia val: 1,345 pattern crops, 740 sleeve crops, 833 neckline crops, evaluated with 5-fold cross-validation grouped by photo plus 5 random hold-outs.
- Features from SigLIP 2 and Marqo-FashionSigLIP, frozen.
- Classifiers: naive Bayes, KNN, MLP (ANN), logistic regression and the LDA classifier, each with and without PCA or LDA; zero-shot baselines; zero-shot fusion; semi-supervised self-training.
- My check: the saved models and the result files (`results_valcv.csv`, `holdout_chosen.csv`, per-class recall) exist and match the report.

## Results [V]

| Attribute | Best model | Macro-F1 (cross-val / hold-out) | Zero-shot | Majority-class accuracy |
|---|---|---|---|---|
| Sleeve, 3 classes | FashionSigLIP + LDA + zero-shot | **0.843 / 0.811** | 0.562 | 0.58 |
| Sleeve, 5 classes | FashionSigLIP + logistic regression | 0.584 / 0.508 | 0.466 | 0.58 |
| Pattern, 10 classes | SigLIP 2 + logistic regression + zero-shot | 0.518 / 0.479 | 0.482 | 0.73 |
| Neckline, 8 classes | FashionSigLIP + LDA + zero-shot | 0.487 / 0.469 | 0.351 | 0.37 |

- Classifier comparison (syllabus Unit IV): logistic regression and the LDA classifier are best; KNN and plain naive Bayes are weak on 768-dimensional features with few samples; the MLP is no better than logistic regression.
- Self-training gave small, mixed gains: it helps with 25 % of the labels and hurts with 5-10 %.
- Sleeve length: the trained model reaches macro-F1 0.84 on the same kind of street photos where P06's outline rules scored only 0.306 accuracy (below the 0.439 majority baseline). Good contrast for the paper: learned features beat hand-made geometry on photos of people.

## Judgement
- Accepted with limits. The sleeve model is a solid trained component, and the other groups are honest but weak:
  - pattern is driven by the "plain" class (text has only 7 training examples);
  - neckline sits at 0.49.
- On the Mirra photos the large text prints (BOSTON, CALIFORNIA) were called "plain", so text detection must come from P05 (OCR), not from this pattern model.
- The training set was limited to Fashionpedia val after my disk and memory emergency forced deletion of the train-split download. This is the main reason pattern and text are weak, and it goes into the limitations.

## Use in the pipeline
- `sleeve3` as the sleeve-length attribute, cross-checked with P06's outline on flat photos.
- Pattern only as a plain-versus-printed flag.
- Neckline as weak evidence.

## Next (if time)
Train on the Fashionpedia train split (about 10 times more data), if disk space can be freed safely.
