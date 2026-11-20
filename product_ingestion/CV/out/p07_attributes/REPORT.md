# P07 report: trained attribute models (design pattern, sleeve length, neckline)

*Status: first pass finished 2026-11-20.*
*Written by the P07 sub-agent and saved here by the orchestrator (sub-agents cannot write report files).*

## 1. Goal
Classifiers that read three garment attributes from a photo: textile pattern, sleeve length and neckline. They are trained on frozen image features with the syllabus Unit IV classifiers.

## 2. Labels found (Fashionpedia val: 1,158 photos, 8,781 annotations)
- **Attribute groups:** `textile pattern` (18 values), `animal` (6), `length` (15), `neckline type` (25).
- **Pattern:** sits on the garment annotation (shirt, top, sweater, cardigan, jacket, vest, coat, dress).
- **Sleeve length:** sits on the `sleeve` part annotations (wrist-length 813, short 305, three-quarter 146, elbow 116, sleeveless 12).
- **Neckline type:** sits on the `neckline` part annotations.

## 3. Data
Scripts `p07_common.py` and `p07_build_dataset.py`; manifest `manifest_val.csv`; crops in `crops/val/`.
- **Pattern:** garment crops with the background greyed out by the garment mask; a raw crop was kept as an ablation.
  - **Rare classes merged:** check includes houndstooth; geometric includes chevron, argyle and herringbone; floral includes plant and toile; graphic = cartoon; other = paisley, camouflage, fair isle and animal prints.
  - **1,345 crops:** plain 981, floral 92, stripe 62, abstract 50, check 38, geometric 38, other 38, dot 23, graphic 16, text 7.
- **Sleeve:** each garment takes the label of its longest sleeve (740 crops: long 431, short 162, three-quarter 77, elbow 63, sleeveless 7). A 3-class version groups them as short-or-none 169, mid 140, long 431.
- **Neckline:** a square crop around the neckline (833 crops), merged into 8 classes:
  - round/crew 309, wide 170, v-neck 115, scoop/u 106;
  - sweetheart 54, high-neck 53, halter 15, collarless 11.
- **Evaluation:** 5-fold cross-validation grouped by photo (pooled out-of-fold predictions), plus a re-check with 5 random 80/20 photo-grouped splits.
- **Not done:** a planned 9,000-photo training subset from the Fashionpedia train split was dropped after the memory and disk emergency (the orchestrator deleted the train annotations), so everything is cross-validation on val only.

## 4. Methods and commands
1. **Features:** `p07_extract.py --backbone siglip2 --splits val` and `--backbone fashion_siglip`. The GPU part runs under `gpu_lock`. Zero-shot text embeddings come from `p07_prompts.py`. CLIP ViT-L/14 was stopped by the orchestrator and dropped.
2. **Classifiers:** `p07_train.py --protocol valcv --out try_01_valcv` runs 3 feature sets (siglip2, fashion_siglip, both joined) × 11 classifiers:
   - Gaussian naive Bayes, and PCA + NB;
   - KNN (k = 15, cosine), PCA + KNN, LDA + KNN;
   - logistic regression (C = 0.05 / 0.005 / 0.5, balanced) and PCA + LR;
   - shrinkage-LDA classifier;
   - a small MLP (ANN);
   - LR and LDA fused with 0.5 × log of the zero-shot probabilities.

   Plus the zero-shot baseline. Results are in `try_01_valcv/results_valcv.csv`.
3. **Final selection:** `p07_final.py` tries more pattern variants, chooses one model per group, re-checks it on the 5 hold-out splits, draws confusion matrices, and saves the models to `product_ingestion/models/attributes/`.
4. **Self-training:** `p07_semisup.py --backbone concat` runs semi-supervised self-training with 5 / 10 / 25 % of the labels.
5. **Mirra photos:** `p07_mirra.py` predicts the attributes of the 5 Mirra photos.

## 5. Results (5-fold grouped cross-validation)
| Group | Backbone / classifier | Acc | Balanced acc | Macro-F1 | n | Majority acc | Zero-shot macro-F1 |
|---|---|---|---|---|---|---|---|
| Pattern (10 classes) | SigLIP 2 / LR + zero-shot | 0.828 | 0.502 | 0.518 | 1345 | 0.73 | 0.482 |
| Sleeve (5 classes) | FashionSigLIP / LR (C 0.005) | 0.805 | 0.572 | 0.584 | 740 | 0.58 | 0.466 |
| **Sleeve (3 classes)** | FashionSigLIP / LDA + zero-shot | **0.878** | 0.846 | **0.843** | 740 | 0.58 | 0.562 |
| Neckline (8 classes) | FashionSigLIP / LDA + zero-shot | 0.529 | 0.488 | 0.487 | 833 | 0.37 | 0.351 |

Hold-out re-check (5 random 80/20 photo-grouped splits, mean ± std):

| Group | Accuracy | Macro-F1 |
|---|---|---|
| Pattern | 0.816 ± 0.010 | 0.479 ± 0.027 |
| Sleeve (5 classes) | 0.792 ± 0.037 | 0.508 ± 0.034 |
| Sleeve (3 classes) | 0.861 ± 0.034 | 0.811 ± 0.039 |
| Neckline | 0.543 ± 0.040 | 0.469 ± 0.022 |

Classifier comparison (macro-F1, SigLIP 2 features):

| Classifier | Pattern | Sleeve (3 classes) | Neckline |
|---|---|---|---|
| zero-shot | 0.482 | 0.562 | 0.351 |
| naive Bayes | 0.398 | 0.681 | 0.374 |
| PCA + naive Bayes | 0.444 | 0.695 | 0.339 |
| KNN | 0.211 | 0.587 | 0.235 |
| LDA + KNN | 0.492 | 0.801 | 0.353 |
| logistic regression | 0.487 | 0.807 | 0.403 |
| LDA classifier | 0.505 | 0.809 | 0.407 |
| MLP (ANN) | 0.454 | 0.806 | 0.367 |

Per-class recall:

| Group | Recall by class |
|---|---|
| Pattern | plain 0.93, check 0.71, stripe 0.68, floral 0.62, dot 0.52, geometric 0.45, abstract 0.44, other 0.42, graphic 0.25, text 0.00 (n = 7) |
| Sleeve (5 classes) | short 0.92, long 0.89, elbow 0.51, three-quarter 0.40, sleeveless 0.14 |
| Sleeve (3 classes) | short-or-none 0.95, long 0.92, mid 0.67 |
| Neckline | high-neck 0.68, v-neck 0.66, wide 0.58, sweetheart 0.52, round/crew 0.51, scoop/u 0.36, halter 0.33, collarless 0.27 |

Other findings:
- **Pattern variants:** merging text and graphic into one "print" class raises pattern macro-F1 to 0.581. Masking the background beats the raw crop (0.518 against 0.495).
- **Self-training:** small and mixed. It helps sleeve (3 classes) at 25 % labels (0.76 → 0.78) and hurts at 5-10 % labels (pseudo-labels amplify the majority class).
- **Figures:** `figs/confusion_{pattern,sleeve,sleeve3,neckline}.png` and `figs/mirra_predictions.png`.

## 6. Mirra photos (qualitative; truth approximate)
| Photo | Pattern | Sleeve | Neckline |
|---|---|---|---|
| c_001 (BOSTON text, elbow sleeves) | plain: text missed | short: elbow wrong | round_crew / scoop_u |
| c_002 (plain, short) | plain: correct | short: correct | scoop_u (back view) |
| c_003 (stripes + script text) | text: partly right | short: correct | scoop_u / round_crew |
| c_004 (geometric graphic + text) | text / geometric: plausible | short: correct | scoop_u / round_crew |
| c_005 (CALIFORNIA text) | plain: text missed | short: correct | round_crew |

- **Short sleeves are reliable.**
- **Large chest prints are missed,** because Fashionpedia val has only 7 text examples.

## 7. What worked and what did not
- **Worked:**
  - **Sleeve length in 3 classes:** macro-F1 0.84 against 0.56 zero-shot. P06's outline rule managed only 0.306 accuracy on Fashionpedia (a different test set).
  - **Best classifiers:** logistic regression and shrinkage-LDA. FashionSigLIP is better for sleeve and neckline; SigLIP 2 is better for pattern.
  - **Zero-shot fusion** helped a little.
- **Did not work:**
  - **KNN and plain naive Bayes,** on 768-dimensional features with a few hundred samples.
  - **The MLP:** no better than logistic regression.
  - **Text and graphic patterns** (too few examples).
  - **5-class sleeve:** elbow and three-quarter get confused.
  - **Neckline** (0.49).
- **Caveats:**
  - Pattern accuracy is driven by "plain" (majority 0.73), so macro-F1 and per-class recall are the honest numbers.
  - The models were chosen and reported on the same cross-validation, so the numbers are slightly optimistic (the hold-out re-check agrees).
  - Training data are street and shop photos, not product shots.

## 8. Issues
- **Train subset dropped:** about 4,000 photos (~800 MB) had been fetched by range requests. The orchestrator stopped it for disk and memory reasons and deleted `data/fashionpedia_train/`, so the train-to-val experiment did not run. The `out/p07_attributes/crops/train` crops (174 MB) and `train_selection.json` remain without features.
- **CLIP ViT-L/14 dropped:** stopped by the orchestrator for memory.
- **Agent's own deletions:** it removed its own partial download files (`*.incomplete`, ~700 MB) from killed downloads in the Hugging Face cache, and once deleted `.gpu.lock` after killing its own process.
- **GPU lock fix:** the first extraction held the GPU lock while downloading a model; it now loads on CPU before taking the lock.

## 9. Recommendation
- **Sleeve:** use the 3-class model (short / mid / long) in the shape step as a prior or a cross-check on the outline measurements; 5-class only as a soft hint.
- **Pattern:** use it only as a plain-versus-printed flag (plain recall 0.93). Text detection stays with P05's OCR.
- **Neckline:** treat it as weak evidence.
- **Next step:** train on the Fashionpedia train split (about 10 times the data), add flip augmentation, tune the zero-shot weight.

## 10. How to call `product_ingestion/cv_attributes.py`
```python
from product_ingestion.cv_attributes import predict_attributes, release_models
out = predict_attributes("path/to/photo_or_cutout.png")             # RGBA alpha = mask
out = predict_attributes(bgr_array, mask=mask_uint8)                 # numpy is BGR / BGRA
out["pattern"]["label"], out["pattern"]["confidence"], out["pattern"]["probs"]
# groups=("pattern","sleeve","sleeve3","neckline"), device="cuda"|"cpu"|None (auto; GPU only if >1.5 GB free)
release_models()                                                      # free the backbones
```
- **Models used:** SigLIP 2 for pattern, Marqo-FashionSigLIP for sleeve and neckline, loaded lazily from the Hugging Face cache. The model files are in `product_ingestion/models/attributes/`.
- **GPU lock:** the library does not take it; the caller holds it.
- **Neckline crop:** a heuristic square at the median neckline position found on val.

## Files
- Code: `product_ingestion/cv_attributes.py`.
- Models: `product_ingestion/models/attributes/`.
- Scripts: `scripts/p07_{common,prompts,build_dataset,fetch_train_images,extract,train,final,semisup,mirra}.py`.
- Outputs: `out/p07_attributes/`.
