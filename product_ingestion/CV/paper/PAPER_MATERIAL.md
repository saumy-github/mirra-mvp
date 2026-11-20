# Material for the paper (the user writes the paper; no paper text here)

*Prepared: 2026-11-20, updated 15:55. Numbers come from the files named next to them.*

Other files in this folder: `citations_candidates.md` (journal inspiration papers, classic methods, tools, datasets).

---

## 1. One-line summary
The project rebuilds the photo-reading stage of a garment ingestion pipeline (views, outline, shape, colour, designs, per-panel textures). At every stage it compares syllabus methods with pretrained models and with models trained here.
- **End to end:** on the 5 Mirra product photos the score rises from **0.407 (v0) to 0.911 (first new pipeline) to 0.960 (final pipeline)**.
- **Public data:** the gains are in section 3.

## 2. Pipeline and method per stage (what to describe in "Method")

| Stage | Before (v0) | After (final default) | Methods compared at this stage | Code |
|---|---|---|---|---|
| 1. Several photos, view and presentation | CLIP zero-shot that never loaded (torch 2.4 refuses its weights); first photo used | SigLIP 2 image features + logistic regression trained on DeepFashion In-shop view labels; front and back chosen jointly across the set; same-garment check (feature cosine + colour), photos grouped by correlation clustering | Naive Bayes, KNN, MLP, logistic regression, with or without PCA/LDA (Unit IV); Haar faces; content-based retrieval for the same-garment check (Unit V) | `multi_view.py`, `step_01_*` |
| 2. Garment outline | SAM 2 with a centre point; highest-score candidate; corner flood fill (B5); meaningless quality score (B6, B7) | **v1_auto:** SegFormer clothes parser gives a box and an interior point, then SAM 2 single mask. The parser's "Skirt" class is added only when no head is visible (Face + Hair < 1 % of the image), which keeps both halves of a colour-block top. Fixed hole fill; quality from SAM 2 IoU, border touch and edge alignment; outline as a simplified polygon (Douglas-Peucker) | GrabCut (graph cut), K-means, mean-shift, region growing, MRF smoothing (Unit III); YOLO, YOLOE, Grounding DINO, RMBG, votes of 2 or 3 models; 14 automatic selection rules; **a YOLO26s-seg model fine-tuned here** | `cv_segment.py`, `step_02_0_*` |
| 3. Enhancement and filtering | Gaussian 5 + auto-Canny | Bilateral 9 + Laplacian zero crossings for print edges; no global enhancement before colour | Histogram equalisation, CLAHE, gamma, grey-world, Retinex, Fourier homomorphic filtering, mean/median/Gaussian/bilateral filters, Sobel/Prewitt/Scharr/Laplacian/LoG/DoG/Canny, image pyramid (Units I-II) | `cv_enhance.py` |
| 4. Colour | K-means; HSV "skin" filter that deleted warm fabrics (B1); white and black skipped as base (B2); crash on a flat colour (B3); one base colour | Mean-shift in CIELAB, merging within ΔE2000 5, guarded skin removal; full palette with fabric/print roles and a colour region map (never one colour) | K-means, K-medoids, Gaussian mixture, mean-shift (Unit IV) | `step_03_0_*` |
| 5. Designs (two-level outlining) | Canny contours + an FFT "pattern" test that fired on everything (B4); one box; wrong types | Level 1 = garment outline; level 2 = every design region with a type (text, graphic, logo, stripes, colour block, pattern). **v4_relabel:** proposals from colour deviation + OCR + Hough stripes + colour blocks + cleaned Grounding DINO boxes. Each region is then retyped zero-shot by SigLIP 2 (a "plain" verdict drops it). A caption inside a graphic is kept, and a small second text line is split off by glyph height. Fixed periodicity test (windowed FFT, ring median, mirrored peaks) | Canny, Gabor filter bank and wavelet (DWT) texture segmentation, Hough lines, FFT periodicity (Units I-III); SAM 2, Grounding DINO, OCR, SigLIP zero-shot labels | `cv_design_regions.py`, `step_04_0_*` |
| 6. Shape | none from the photo (fixed CLO ratios) | Landmarks from the outline (convexity defects for armpits; curvature and line departure for shoulders, cuffs and hem); sleeve class; width and length ratios (reliable on flat photos) | Harris, Shi-Tomasi, Hessian, FAST, ORB, SIFT, AKAZE, contour curvature, convexity defects, Hough (Unit II) | `cv_shape.py` |
| 7. Attributes (trained) | none | Pattern, sleeve length and neckline classifiers on frozen SigLIP 2 / FashionSigLIP features, trained on Fashionpedia | Naive Bayes, KNN, MLP, logistic regression, LDA; PCA; semi-supervised self-training (Unit IV) | `cv_attributes.py` |
| 8. Per-panel pixel maps | One bounding-box homography squeezing the whole shirt into the front panel; flat-colour back and sleeves | Torso/sleeve split from landmarks; thin-plate-spline warp of each region onto its panel; hole filling; back panel from the back photo (or the print-free front); side-car metadata in mm per pixel | Homography, affine, thin-plate spline (Unit I) | `cv_panel_maps.py`, `step_06_0_*` |

## 3. Key numbers (all from `results/`)

**End to end, the 5 Mirra photos** (`results/mirra_before_after.csv`; approximate hand-made references):

| Area | v0 | First new pipeline (P10) | Final pipeline |
|---|---|---|---|
| Outline | 0.658 | 0.919 | 0.974 |
| Colour | 0.808 | 0.951 | 0.962 |
| Design | 0.160 | 0.774 | 0.903 |
| View | 0.000 | 1.000 | 1.000 |
| **Pipeline** | **0.407** | **0.911** | **0.960** |

- **Label correction:** the v0 and first-pass figures are after the c_004 label correction (section 6). Before it, v0 design was 0.164 and the first-pass pipeline 0.909; the v0 pipeline score did not change.
- **Final run details:**
  - mask IoU 0.982 (c_003 0.562 → 0.939);
  - palette ΔE 1.13; c_003's colour blocks found, and its base-colour ΔE 67.7 → 1.08;
  - design F1 0.848, no false design on the plain shirt, type accuracy 1.0;
  - c_004 and c_005 each miss one design region.

**Outline on public data** (exact labels; `results/public/p01_*`, `p15a_*`, `p17_*`):

| Method | VITON product | VITON person | Street | Macro IoU | Failures | Time per photo |
|---|---|---|---|---|---|---|
| v0 (SAM 2 centre point) | 0.932 | 0.775 | 0.562 | 0.756 | 8.0 % | 0.55 s |
| Best classical (GrabCut) | | | | 0.618 | | |
| Zero-shot YOLOE / YOLO person minus skin | | | | 0.641 / 0.751 | 26.6 % / 12.7 % | 0.30 / 0.13 s |
| v1 (parser box + point → SAM 2) | 0.936 | 0.893 | 0.838 | 0.889 | 1.1 % | 0.59 s |
| **v1_auto (final default)** | 0.944 | 0.893 | 0.838 | **0.892** | 1.1 % | 0.59 s |
| YOLO26s-seg fine-tuned here (P17) | 0.979 | 0.901 | 0.788 | 0.889 | 1.8 % | 0.03 s |

- **v0 to v1:** person photos +0.118 (95 % CI 0.082 to 0.156), street photos +0.277 (0.213 to 0.342), flat product photos unchanged.
- **v1_auto against v1:**
  - On 400 new held-out images: 0.8966 against 0.8940. Pooled: +0.0027 (95 % CI +0.0005 to +0.0059).
  - Never worse on person or street photos (the rule never fires there).
  - Mirra c_003 IoU 0.562 → 0.940.
- **Fine-tuned YOLO:** equals v1 at 5 % of its time, but is in-domain and weaker on street photos.

**Other stages:**
- **Design, mean of the 5 Mirra photos** (`results/mirra_scores.csv`, labels `p15b_*`):
  - design score 0.215 (v0) → 0.774 (v3_combo) → **0.904 (v4_relabel)**;
  - F1@0.3 0.213 → 0.648 → 0.848;
  - no false design on the plain shirt.
- **Design on public data, plain against printed** (`results/public/p05_fashionpedia_*`): the old FFT test fires on 100 % of plain and 100 % of printed garments; the fixed test on 8.3 % against 40.9 %.
- **Colour** (`results/public/p04_fashion_product_run_02_summary.csv`): colour-name accuracy on 266 product photos 0.207 → 0.301.
- **Edges** (`results/public/p03_edge_scores_summary.csv`): print-edge F1 0.630 → 0.734; false edges on plain fabric 1.02 % → 0.65 %.
- **Views** (`results/public/p16_*`):
  - front chosen correctly in 85.4 % of shuffled photo sets (first-photo baseline 61.7 %);
  - back recall 0.98;
  - a photo of another garment detected 96.7 % of the time.
- **Multi-photo demo** (`plans/10`): on 2 shuffled, renamed In-shop test sets, the front and back were both right. After the outline fix the outline covers only the top; at 256 px small false "logo" boxes remain (a necklace pendant, a hand).
- **Attributes** (`results/public/p07_*`):
  - sleeve length (3 classes) macro-F1 0.843 (hold-out 0.811);
  - pattern 0.518;
  - neckline 0.487.
- **Shape** (`results/public/p06_*`): on 327 clean VITON-HD tops, hem/chest has median 1.16 against CLO's fixed 0.93; wrist/bicep cannot be measured from flat photos.
- **Panel maps** (`results/public/p19_panel_maps_metrics.csv`): body-panel silhouette IoU 0.64-0.87 (v0) → 0.87-0.98 (new) on 9 photos.

**Choosing and checking the metrics** (`plans/01`):
- **Damage tests** (`results/metric_sanity_*_summary.csv`):
  - IoU alone misses border errors;
  - base-colour ΔE misses a lost colour block;
  - box F1 misses wrong types.
  - Resulting scores: outline = IoU + boundary F; colour = palette ΔE; design = F1 + pixel IoU + type accuracy.
- **Blind check against judgement by eye** (`results/judgement_agreement.csv`):
  - 8 outline methods × 5 photos, ranked before the key was opened;
  - Kendall tau-b: IoU 0.833, outline score 0.766, HD95 0.751, boundary F 0.719.
  - All metrics agree with the eye, IoU most; boundary F is noisy among near-identical outlines.

## 4. "How we improved it over time" (from `plans/`, in order)
1. `01` P00: built the scoring framework; v0 scores 0.407. SAM 2's top candidate is the print, not the shirt (c_004); the parser fails on flat photos.
2. `02` P03: bilateral filtering beats mean, median and Gaussian for print edges; global enhancement hurts colour.
3. `03` P06: outline geometry works on flat photos, fails on photos of people and street photos.
4. `04` P19: per-panel thin-plate-spline maps replace one box-to-box warp.
5. `05` P04: B1-B3 fixed, multi-colour palettes; leaky v0 masks still corrupt the base colour, so segmentation must come first.
6. `06` P07: trained sleeve classifier beats outline rules on street photos; pattern and neckline weak (little data).
7. `07` P16: joint front/back choice + same-garment check turns a modest per-photo classifier into 85 % correct fronts per set.
8. `08` P05: design 0.164 → 0.785 (reference masks); Grounding DINO noisy alone but useful once cleaned; Gabor/DWT texture fails on folds.
9. `09` P01: the SAM 2 prompt was the problem; a parser box fixes it; votes do not help; open v1/v1_all trade-off on the colour-block shirt.
10. `10` P10: everything wired into the runner; end to end 0.407 → 0.909 (0.911 after the label correction).
11. `11` P15b: SigLIP 2 relabelling plus two fixes; design score on realistic masks 0.774 → 0.904. A reference label error was found on the way (c_004 text box 20 px low).
12. `12` P15a: "is a head visible?" decides how to read the parser's labels; c_003 fixed with no loss on public data. Model-confidence, edge and geometry rules all failed.
13. `13` P17: a model trained here (1,468 photos, 30 min) equals the two-model zero-shot chain at 5 % of the time; zero-shot YOLO variants reach only 0.64 to 0.75.
14. `01` (addendum): the blind judgement check confirms the metrics.
15. `10` (addendum): the multi-photo demo found the views correctly, but exposed a 5 % area floor that discarded tops in full-body photos (fixed, I23); after the fix both sets outline only the top.
16. `10` (final run): with all final defaults the end-to-end score is 0.960.

Failed attempts kept for the paper (images in `out/`, never deleted):
- classical segmenters;
- votes and consensus;
- the 13 losing automatic selection rules (`out/p15a_seg_autoselect/rules_*.csv`);
- Gabor/DWT texture segmentation;
- the first sleeve model;
- the unthinned edge scoring;
- the inverse-TPS check;
- CLIP ViT-L (dropped for memory);
- the first same-garment algorithm;
- YOLO box → SAM 2;
- the demo's failed full-body outlines (`out/demo/inshop_*/front_overlay.jpg`).

## 5. Figures (in `images/`)

| File | Shows |
|---|---|
| `fig_before_after_scores.png` | Per-area scores of v0, the first new pipeline and the final pipeline (end to end, 5 Mirra photos) |
| `fig_outline_public_iou.png` | 16 outline methods on public data, coloured by family: classical (syllabus), pretrained zero-shot, trained in this project |
| `p00_sam2_candidates_c_004.jpg`, `p00_sam2_candidates_c_002.jpg` | SAM 2's top candidate is the print (c_004); the parser misses a flat shirt (c_002) |
| `p00_reference_design_regions_c_003.jpg` | Hand-made reference regions (stripes, text, colour blocks) |
| `p01_contact_sheet_selected.jpg` | 23 segmentation methods × 5 photos |
| `p03_fig1_smoothing_filters.png` | Mean, median, Gaussian and bilateral on folds and a print |
| `p03_fig2_edge_detectors.png` | The nine edge detectors |
| `p03_fig3_enhancement_shading.png` | Enhancement and shading removal |
| `p03_fig4_f1_vs_false_edges.png` | Print-edge F1 against false edges, all 117 combinations |
| `p03_edge_gallery_c_004.png` | Every filter × detector on one photo |
| `p04_swatches_oracle.png` | Palettes per clustering method |
| `p04_region_maps_oracle.png` | Colour region maps (c_003's two fabric blocks) |
| `p05_contact_sheet_oracle_masks.jpg` | Two-level outlining: 11 design methods × 5 photos |
| `p06_landmarks_mirra.jpg` | Landmarks and measured lines |
| `p06_corners_c_004.jpg` | 9 corner and keypoint detectors on one photo |
| `p06_ratio_hist.png` | Shape ratios of 500 VITON-HD tops |
| `p07_confusion_sleeve3.png`, `p07_confusion_pattern.png` | Trained attribute classifiers |
| `p07_mirra_predictions.png` | Attribute predictions on the Mirra photos |
| `p16_confusion_view.png` | View classifier confusion matrix |
| `p16_examples_testsets.png` | Photo sets with the chosen front and back |
| `p16_mirra_mixed_grid.png` | Five different shirts: 4 flagged as different garments |
| `p19_panel_maps_c_003.jpg`, `p19_panel_maps_c_001.jpg` | v0 against new panel textures |

More figures to take straight from `out/`:
- the blind judgement sheets, `out/p00_baseline/judgement/<cloth>_sheet.jpg`;
- P17's training curves, `out/p17_yolo_seg/runs/run2-2/results.png`;
- P15b's design overlays, `out/p15b_design/try_02_cpu/v1/v4_relabel/overlays/`.

## 6. Limitations to state
- **Small own dataset:** 5 Mirra photos with approximate hand-made references, made by one annotator.
  - 4 of the 5 reference masks come from SAM 2 candidates, which favours SAM 2 methods, so public data is the main evidence.
  - One reference box (c_004 text) had to be corrected during the work.
- **Tuned on the test photos:** design thresholds, the text-line split rule and the presentation-mix weight were set while looking at the Mirra photos.
- **Head rule:** v1_auto rests on one real torso-crop case (c_003), and the head threshold has little margin (c_003 0.3 %, nearest counter-example 1.2 %).
- **Fine-tuned YOLO:** tested in-domain (same datasets as training).
- **Training-data gaps:**
  - View training photos are all on-model (no flat lays, close-ups or size charts).
  - Attribute models were trained on Fashionpedia val only (the train split was dropped for disk and memory), so text and graphic patterns have very few examples.
- **Photos of people:** shape and panel proportions from the outline are unreliable when a person wears the shirt.
- **No 3D drape in CLO** (the user's choice tonight); per-panel placement in CLO needs a plugin change (`questions.md` Q6, Q7).
- **Hardware:** 6 GB GPU and 16 GB RAM, so models ran one at a time. Memory limits stopped several runs (`ISSUES.md` I7, I9, I13, I17, I22), and timings are noisy.

## 7. Datasets and licences
See `INDEX.md`: Fashionpedia (CC BY 4.0), VITON-HD and DeepFashion In-shop (research only), Fashion Product Images (Kaggle).
