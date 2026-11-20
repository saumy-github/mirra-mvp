# Trained garment attribute models (P07, CV)

*Status: first pass, trained 2026-11-20*

Frozen image backbone features, then a small classifier trained on Fashionpedia val labels (1,158 photos, crops by garment/part box).
Load through `product_ingestion/cv_attributes.py` (`predict_attributes`). Fashionpedia is research-licence data: keep these models out of shipped Mirra builds.

| file | classes | backbone | classifier | 5-fold grouped CV (macro-F1 / acc) | n crops |
|---|---|---|---|---|---|
| pattern.pkl | plain, stripe, floral, check, dot, geometric, abstract, text, graphic, other | siglip2 (google/siglip2-base-patch16-224) | logistic regression + 0.5 x zero-shot | 0.518 / 0.828 | 1345 |
| sleeve.pkl | sleeveless, short, elbow, three_quarter, long | Marqo-FashionSigLIP | logistic regression (C=0.005) | 0.584 / 0.805 | 740 |
| sleeve3.pkl | short_or_none, mid, long | Marqo-FashionSigLIP | LDA (shrinkage) + 0.5 x zero-shot | 0.843 / 0.878 | 740 |
| neckline.pkl | round_crew, scoop_u, v_neck, wide, sweetheart, high_neck, halter, collarless | Marqo-FashionSigLIP | LDA (shrinkage) + 0.5 x zero-shot | 0.487 / 0.529 | 833 |

Each `.json` holds the class counts and the CV numbers. The `.pkl` holds the fitted sklearn model, class list, backbone names and text embeddings.
Final models are fitted on all val crops; the metrics above come from cross-validation (never from the fit data). Details: `product_ingestion/CV/out/p07_attributes/`.
