# CV project master plan: better garment reading from product photos

*Status: started 2026-11-20 ~06:00 (user's start command); working overnight without pausing. CLO is off-limits tonight (P20 on hold)*
*Last updated: 2026-11-20*
*Deadline: paper draft and GitHub implementation, 2026-11-21*

Rules: `RULES.md`. Questions for the user: `questions.md`. Each plan gets a record in `plans/NN_<name>.md` when it finishes, and its status is updated here.

---

## 1. Goal

Improve how `product_ingestion/` reads cloth photos, in five areas:
1. **Several photos:** accept 1 to N unlabelled photos of one garment and work out which is the front, back, side or close-up.
2. **Outline:** cut the garment out cleanly and draw its outline.
3. **Shape:** sleeve length, neckline, fit, width and length ratios.
4. **Colour:** the true base colour and palette, including colour-block garments.
5. **Design and design patterns:** find and outline each design region on the shirt (text, logo or graphic, stripes, colour block, all-over print) and label it.

Then package the code with a README, and hand the user the material for the paper.

## 2. Starting point (checked 2026-11-20)

### 2.1 The five Mirra photos (reference labels made by eye, *approximate*)

| Cloth | View | Shown as | Colour | Design | Sleeve, fit |
|---|---|---|---|---|---|
| c_001 | front | on a person | navy | white text "BOSTON" plus small script "Leotude" | elbow length, oversized (dropped shoulder) |
| c_002 | **back** | flat, no person | pink | none (plain) | short, regular |
| c_003 | front | on a person | colour block: white upper half, dark-teal lower half | stripe band plus script text "whatever" | short, slim |
| c_004 | front | flat, no person | brown | square graphic with line patterns plus text | short, regular |
| c_005 | front | on a person | red | text graphic "CALIFORNIA" plus small text | short, regular |

### 2.2 What the current pipeline outputs [V]
From `product_ingestion/output/<cloth>/s_001/001/image_info/`:

| Cloth | Mask area | Quality score | Base colour | "Skin" pixels removed | Design found | Problem |
|---|---|---|---|---|---|---|
| c_001 | 57.9% | 0.98 | `#27283b` navy | 119 | logo, 1.7% | type wrong (it is text); coverage far too small |
| c_002 | 89.4% | 0.666 | `#f44c83` pink | 35,434 (pink fabric) | text, 1.8% | false positive on a plain shirt; mask too big |
| c_003 | 84.8% | 0.821 | `#182c2a` dark teal | 120,602 (arms) | logo, 13.0% | white half ignored; stripes not seen as a pattern; mask too big |
| c_004 | 77.2% | 0.98 | `#3c2925` brown | 4,242 (brown fabric) | text, 13.4% | type wrong (it is a graphic) |
| c_005 | 76.9% | 0.98 | `#c51a29` red | 13,247 | logo, 36.3% | type wrong (it is text) |

### 2.3 Bugs reproduced on the current code [V]
From `MIRRA_product_ingestion_review.md`, re-run against the current (renamed) step files:

| # | File | Bug |
|---|---|---|
| B1 | `step_03_0_colour_extraction.py` | The HSV skin range deletes tan, coral, pink and brown fabric (the whole shirt in synthetic tests) |
| B2 | `step_03_0_colour_extraction.py` | White and black clusters are skipped as base colour (white tee gave grey `#c4c4c4`; black tee with a small red print gave red) |
| B3 | `step_03_0_colour_extraction.py` | A single flat colour crashes K-Means (`ValueError: NaN`) |
| B4 | `step_04_0_design_extraction.py` | The FFT "pattern" test fires on everything (a plain tee with folds scored 822 against a threshold of 8; the real photos scored 56 to 2,163) |
| B5 | `step_02_0_segmentation.py` | `_fill_holes` floods from the corner pixel, so a mask touching the corner becomes 100% |
| B6 | `step_02_0_segmentation.py` | Edge sharpness is measured on the binary mask, so it is always 1.0 |
| B7 | `step_02_0_segmentation.py` | The hole count always reports 1 (the background is counted) |

Also: CLIP view selection never loads on torch 2.4.1 (`openai/clip-vit-base-patch32` has only `.bin` weights), so view selection silently falls back; and the runner uses only one photo per garment.

### 2.4 Tools and data ready (2026-11-20)

| Item | Detail |
|---|---|
| GPU | RTX 4050 Laptop, 6 GB; torch `2.4.1+cu121` sees it |
| New packages | `ultralytics` 8.4.215 (YOLO, YOLOE), `easyocr` 1.7.2 (text regions), `open_clip_torch` 3.1.0 (fashion SigLIP) |
| Fashionpedia val | `data/fashionpedia/`: 3,200 photos (val and test images); labels for the 1,158 val photos (garment masks, sleeve, neckline, textile pattern). CC BY 4.0 |
| DeepFashion In-shop (filtered) | `data/deepfashion_inshop_filtered/`: train and test parquet files (157 MB); file names carry the view (`_front`, `_side`, `_back`, `_full`); several photos per item. Non-commercial research licence |
| Models (downloaded on first use) | SAM 2 and 2.1 large, SegFormer clothes parsers, Grounding DINO tiny, SigLIP 2, CLIP ViT-L/14, Marqo-FashionSigLIP, YOLO and YOLOE weights |
| Environment snapshot | `env/pip-freeze-2026-11-20.txt` and restore guide `env/ENVIRONMENT.md` |

### 2.5 Course syllabus coverage (from `syllabus-cv.png`, CO CSC 601)
The plans use the syllabus methods wherever they fit, next to the modern models, so the paper shows both and compares them.

| Syllabus unit | Methods | Used in |
|---|---|---|
| I: image formation, transforms, enhancement | Fourier transform, convolution, filtering, image enhancement and restoration, histogram processing, perspective, homography, DLT, RANSAC | P03 (enhancement, histogram equalisation and CLAHE, restoration, Fourier-domain homomorphic filtering for shading), P05 (FFT pattern test), L1 (homography, DLT, RANSAC) |
| II: features and scale space | Canny, LoG, DoG, Hough transform, Harris and Hessian corners, SIFT, SURF, HOG, image pyramids, Gaussian derivative filters, Gabor filters, DWT | P03 (Canny against LoG and DoG), P05 (Gabor filter bank and DWT for texture and stripes, Hough lines for stripes), P06 (Harris corners and Hough for garment landmarks), P16 (SIFT or HOG matching for the same-garment check) |
| III: segmentation | Region growing, edge-based segmentation, graph cut, mean shift, MRF, texture segmentation, object detection | P01 (GrabCut graph cut, mean shift, region growing and MRF smoothing, compared with SAM 2, YOLO and SegFormer), P05 (texture segmentation of design regions) |
| IV: clustering, classification, dimensionality reduction | K-means, K-medoids, Gaussian mixtures; Bayes, KNN, ANN; supervised, unsupervised, semi-supervised; PCA, LDA, ICA | P04 (K-means against K-medoids against GMM for colour), P16 and P07 (Bayes, KNN, ANN/MLP classifiers on image features, PCA and LDA, semi-supervised pseudo-labels) |
| V: applications and modern trends | Content-based image retrieval, stitching, computational photography, super-resolution, GPU computing, fusion | P16 (retrieval-style same-garment check, multi-photo fusion), L1 (stitching, super-resolution of the print), GPU use throughout |

---

## 3. Plan list

Priority: **Must** (needed for the code and the paper), **Should** (strengthens the paper), **Could** (only if time is left).

Time boxes are wall-clock minutes for a first pass. Plans in the same wave run at the same time, each in its own sub-agent. Any plan can get more passes later.

| ID | Plan | Area | Priority | Wave | Time box | Needs | Status |
|---|---|---|---|---|---|---|---|
| P00 | Baseline snapshot, reference labels, evaluation script | all | Must | 0 | 30 min | - | *done: `plans/01_p00_baseline_and_scoring.md`; v0 pipeline score 0.407; metrics agree with a blind by-eye ranking (Kendall tau-b 0.77 outline score, 0.83 IoU)* |
| P01 | Garment outline (segmentation) and model comparison | outline | Must | 1 | 60 min | P00 | *done, accepted: `plans/09_p01_garment_outline.md`; public macro IoU 0.889 vs 0.756 (v0), Mirra outline score 0.919 (v1) / 0.974 (v1_all) vs 0.658* |
| P03 | Image enhancement and smoothing-filter study | design, colour | Must | 1 | 40 min | P00 | *done, accepted: `plans/02_p03_enhancement_filters_edges.md`; bilateral 9 + Laplacian edges F1 0.734 vs 0.630 (v0)* |
| P04 | Colour extraction fixes | colour | Must | 1 | 40 min | P00 | *done, accepted: `plans/05_p04_multicolour_extraction.md`; colour score 0.961 with reference masks (v0 0.93); Fashion Product top-1 0.30 vs 0.21* |
| P05 | Two-level outlining: design regions on the shirt | design | Must | 1 | 60 min | P00 | *done, accepted: `plans/08_p05_design_regions.md`; design score 0.785 (0.830 with SigLIP 2 relabel) vs 0.199 for v0, reference masks* |
| P16 | Several unlabelled photos with automatic view detection and a trained view model | several photos | Must | 1 | 75 min | P00 | *done, accepted: `plans/07_p16_multi_photo_views.md`; front correct in 85 % of photo sets (first-photo baseline 62 %), back recall 0.98* |
| P06 | Shape attributes from the outline | shape | Should | 2 | 30 min | P01 | *done, accepted with limits: `plans/03_p06_shape_landmarks_corners.md`; landmarks reliable on flat photos only* |
| P07 | Trained attribute models (design pattern, sleeve, neckline) | design, shape | Should | 2 | 45 min | P01, P05 | *done, accepted with limits: `plans/06_p07_trained_attribute_models.md`; sleeve (3 classes) macro-F1 0.84; pattern 0.52, neckline 0.49* |
| P14 | Evaluation on public datasets (Fashionpedia, VITON-HD, DeepFashion2, DressCode) | all | Should | 2 | 45 min | P01 to P05 | *done inside the plans: P01 (VITON-HD product and person, Fashionpedia), P04 (Fashion Product Images), P05 (Fashionpedia plain vs printed), P06 (VITON-HD shape), P07 (Fashionpedia attributes), P16 (DeepFashion In-shop); gathered in P11* |
| P17 | Fine-tune a small segmentation model (YOLO-seg) on garment masks | outline | Should | 2 | 60 min | P01, datasets | *done, accepted as a comparison (not the default): `plans/13_p17_finetuned_yolo_segmentation.md`; public macro IoU 0.889 (= v1) at 0.03 s per photo vs 0.59 s; zero-shot YOLO 0.64 to 0.75*
| P19 | Per-panel pixel maps: a high-resolution image for the front, back and each sleeve, each pixel a fixed patch of fabric | colour, design | Must | 2 | 60 min | P01, P06, P16 | *done, accepted: `plans/04_p19_p18_panel_pixel_maps.md`; body-panel silhouette IoU 0.87-0.98 vs 0.64-0.87 (v0)* |
| P18 | Texture check: project panel textures back onto the photo and compare; flat and simple 3D previews | colour, design | Must | 3 | 40 min | P19 | *done inside P19 (`cv_texture_check.py`); flat previews done, 3D preview not done* |
| P10 | Wire the best methods into the pipeline, run tests | all | Must | 3 | 40 min | wave 1 winners | *done: `plans/10_p10_pipeline_integration.md`; end to end 0.407 (v0) → 0.911 (first pass) → 0.960 (final defaults, 15:52, restarted with the user's OK after the low-memory stop, `ISSUES.md` I22); multi-photo demo correct on 2 shuffled sets* |
| P11 | Results tables and figures | all | Must | 3 | 30 min | P10 | *done: `scripts/p11_build_results.py`, `scripts/p11_figures.py`; `results/` tables (incl. the final run, P15a, P15b, P17) and `images/` (2 charts + 23 plan figures)* |
| P13 | Executable package and README | code | Must | 3 | 20 min | P10 | *done: `README.md` and `scripts/demo_read_garment.py` (tested on c_004 and two shuffled In-shop photo sets); GitHub repository choice still open (`questions.md` Q2)* |
| P12 | Paper material pack (the user writes the paper) | paper | Must | 3 | 30 min | P11 | *done: `paper/PAPER_MATERIAL.md` (with the final run), `paper/citations_candidates.md`; then, at the user's request, the IEEE paper itself (`paper/ieee/main.tex`, figures, `paper.pdf`), submitted by the user on 2026-11-20* |
| P20 | Live CLO test: launch CLO, start the plugin, run Step 3 with the new pixel maps, take screenshots; per-panel fabrics in the plugin | 3D result | Should | 4 | 90 min | P19, P10 | *on hold: user asked not to use CLO tonight (CLO update pending)* |
| P15a | Improvement: automatic choice between segmentation v1 and v1_all (c_003 loses its teal half under v1) | outline | Should | 4 | 60 min | P01 | *done, accepted: `plans/12_p15a_segmentation_autoselect.md`; `v1_auto` default (c_003 IoU 0.562 -> 0.940; public held-out 0.894 -> 0.897); live check done (same numbers)* |
| P15b | Improvement: SigLIP 2 relabelling wired into the design default; design re-scored on the new masks | design | Should | 4 | 60 min | P05, P01 | *done, accepted: `plans/11_p15b_design_relabel.md`; design score 0.904 vs 0.774 (v3_combo) and 0.215 (v0) on the new masks* |
| P15+ | More improvement passes on the weakest results | any | Should | 4 | until morning | wave 3 | *queued* |
| L1, L2 | Later phase: the user's own photos with homography; GenAI comparison | several | - | later | - | user's decision | *waiting on user* |

Order: wave 0 (me alone) -> wave 1 (five plans at once) -> review -> wave 2 -> review -> wave 3 (integration and packaging, so a complete deliverable exists early) -> wave 4 (keep improving, re-running P10 and P11 after each accepted improvement).

(P02 "view direction" was merged into P16. P08 and P09 became L1 and L2.)

## 3a. How the work runs

- **Me (orchestrator):** I do wave 0, write the instructions for each sub-agent, review every result, choose which method wins, merge it, update this file and `INDEX.md`, and start the next wave. I may change, split, drop or add plans at any time; every change goes in the change log with the reason.
- **Sub-agents:** Sonnet at high effort, one per plan, running at the same time. Each gets `RULES.md`, its plan, its owned files and the evaluation command, and must report back: what it changed, the commands it ran, the metrics against v0, its output folder and its own verdict.
- **File ownership** (so parallel agents never edit the same file):

  | Plan | Owns |
  |---|---|
  | P01 | `step_02_0_segmentation.py` |
  | P16 | `step_01_0_view_selection.py`, `step_01_1_garment_router.py`, new module `multi_view.py` |
  | P19 | `step_06_0_texture_projection.py` (per-panel pixel maps; back panel from the back photo) |
  | P03 | new module `cv_enhance.py` (filters and enhancement) |
  | P04 | `step_03_0_colour_extraction.py` |
  | P05 | `step_04_0_design_extraction.py` |
  | P06 | new module `cv_shape.py` |
  | P07, P14, P17 | their own scripts under `CV/scripts/` (P07 may add an inference module `cv_attributes.py`) |
  | P18 | new module `cv_texture_check.py` |
  | Me | `run_product_ingestion.py`, `scripts/evaluate.py`, reference labels, `tests/`, `PLAN.md`, `INDEX.md`, `questions.md` |

  Each agent writes only its owned files, its `out/<plan>/` folder and its `plans/NN_<name>.md` record. Agents start from the `out/p00_baseline/` inputs (segmented images and reference labels), so P03 to P05 do not wait for P01; once P01 has a winner, I re-run them on the new masks.
- **GPU:** one large model at a time, through the lock file `out/.gpu.lock`.
- **How I judge an agent's work:**
  1. The metric against v0 on the same photos, computed by `scripts/evaluate.py` (not by the agent's own script).
  2. A visual check of its overlays: does the improvement show on the image?
  3. Nothing broken: same output files and JSON keys, public functions unchanged, old method still selectable.
  4. An honest record: failed tries kept and written up.

  A weak agent gets one redirect with specific feedback. If its second pass is still weak, the plan is closed as "tried, not adopted" and its outputs stay for the paper.

---

## 4. Plan details

### P00 Baseline snapshot, reference labels and the scoring framework
Today there is no agreed measure of "better", so P00 first decides **how** methods are scored, then scores v0.
- Re-run the unit tests once and record the count.
- Copy the current per-cloth outputs (mask, colour, design crop, JSON) into `out/p00_baseline/` and make one contact-sheet image per stage.
- Reference labels: table 2.1 as JSON, plus approximate reference masks for the garment and for the design regions of each photo (garment mask started from the best SAM 2 candidate, checked by eye, fixed where needed). Stored in `out/p00_baseline/reference/`, marked approximate. Public datasets give exact references at scale (VITON-HD cloth masks, DeepFashion2 masks, Fashionpedia masks and attributes, In-shop views, Fashion Product colour names).
- **Candidate metrics for each area:**

  | Area | Candidates |
  |---|---|
  | Outline | IoU; boundary F-score at a few pixel tolerances; 95th-percentile boundary distance; leakage (share of the mask that is not garment, such as arms or background) and miss (share of garment not covered) |
  | Colour | Palette distance: colours matched between prediction and reference, ΔE2000 weighted by share; per-region ΔE2000; colour-name accuracy on Fashion Product Images |
  | Design | Region detection precision and recall at IoU 0.5; region IoU; type accuracy (macro-F1); false positives on plain shirts |
  | View | Accuracy, macro-F1, confusion matrix; share of photo sets where the front and back pair is right |
  | Shape | Attribute accuracy (sleeve, neckline); landmark error where references exist |
  | Texture | Photo against re-projected panel textures: ΔE2000 per region and structural similarity (P18) |
  | Without references | Agreement between independent methods; outline alignment with strong image edges; border-touch ratio (usable on any new photo) |

- **Choosing the primary metric per area (meta-evaluation):**
  1. *Sanity:* apply controlled damage to reference outputs (add the arms to a mask, shift a colour, drop a design region) and keep only metrics that get worse by a sensible amount.
  2. *Agreement with human judgement:* rank a small set of real outputs by eye, then check which metric ranks them the same way (Kendall's tau).
  3. *Reliability:* prefer metrics that use exact references from the public datasets; the 5 Mirra photos are reported separately because their references are approximate.
- **One summary score per area** (the chosen primary metric, scaled 0 to 1) and an overall pipeline score (a weighted mean, with the weights written down and justified). Every individual metric is still reported, plus run time.
- Write it as `scripts/evaluate.py`, used by every plan and by me when judging agents.
- Done when the scoring choice is written up with its sanity and agreement results, and the v0 numbers are in `results/v0_baseline.csv`.

### P01 Garment outline (segmentation) and model comparison
- Fix B5: pad the mask with a 1-pixel background border before the flood fill, and fill only holes smaller than about 2% of the garment.
- Fix B6 and B7: replace the quality score with signals that mean something: SAM 2's own predicted IoU, border-touch ratio, holes counted before filling, and agreement between two models.
- SAM 2 prompt variants, each documented with its exact prompt:
  1. Current: centre point plus four corner background points; candidate with the highest predicted IoU.
  2. Box prompt (from a rough first mask or a detector) plus centre point, single mask output.
  3. Candidate choice: the largest candidate that does not cover most of the border.
- Models compared with SAM 2: U²-Net (current fallback); SegFormer clothes parsers (they also label skin, arms and face); YOLO (latest `ultralytics` segmentation models, and text-prompted YOLOE "t-shirt"); Grounding DINO box plus SAM 2.
- Classical syllabus methods compared too (Unit III): GrabCut (graph cut), mean-shift and K-means colour segmentation, region growing, MRF smoothing of the mask border.
- **Combinations of 2 or 3 methods** are tried as well, for example:
  - a detector's box (YOLO, Grounding DINO or the SegFormer garment region) used as the SAM 2 prompt;
  - SAM 2 mask with the SegFormer "arms, skin, face" pixels removed;
  - majority vote of three masks (SAM 2, SegFormer, YOLO), weighted by each model's confidence;
  - any of these refined at the border with GrabCut or MRF smoothing.
- Outline: take the outline from the mask contour (smoothed, simplified polygon) instead of colouring the background and running edge detection on it. Optional GrabCut refinement of the border.
- Save every model's mask and overlay for each photo.
- Metrics: IoU and boundary F-score against the reference masks, mask area, run time.

### P03 Image enhancement and filtering study (syllabus Units I and II)
- Enhancement before colour and design: histogram equalisation and CLAHE (on the L channel), gamma correction, grey-world white balance.
- Restoration: denoising (median, bilateral, non-local means).
- Shading removal: divide by a heavily blurred copy, against homomorphic filtering in the Fourier domain.
- Smoothing before edge detection: Gaussian (current), mean, median and bilateral, at two or three kernel sizes.
- Edge detectors: Sobel, Prewitt, Scharr, Laplacian, LoG, DoG and Canny (current), with and without an image pyramid (scale space); optionally a learned edge model (HED) as the modern comparison.
- Every detector's output is saved for every photo (an edge gallery per photo), whether it wins or not.
- For each combination, measure edges kept inside the reference design regions against false edges on plain fabric and folds. Save an edge-map grid per photo.
- Outcome: the enhancement, filter and edge detector chosen for P04 and P05, with the numbers behind the choice.

### P04 Colour extraction fixes
- B1: remove skin by label (clothes parser from P01), or only when P16 says a person is in the photo; YCrCb skin model as a fallback instead of the wide HSV range.
- B2: base colour is the largest cluster; merge clusters closer than about ΔE 5 (shades of the same fabric); skip white or black only when that cluster is small.
- B3: guard against fewer distinct colours than clusters and against empty clusters.
- **A T-shirt can have several colours, so the result is never a single colour.** The output is a palette (every major colour with its share) and a colour region map (which pixels belong to which colour), per photo and per panel. `base_colour_hex` stays only as a compatibility field for code that expects it (the largest fabric colour). c_003 (white and dark teal) is the test case.
- Clustering compared (syllabus Unit IV): K-means (current), K-medoids and Gaussian mixtures.
- Metric: ΔE2000 against the reference colours, before and after each fix and each enhancement.

### P05 Two-level outlining: design regions on the shirt
- Level 1: the garment outline from P01.
- Level 2, inside the garment:
  - Ignore a band just inside the outline and along seams, so the shirt's own edge is not taken as a design.
  - Shading removal from P03, so folds do not look like prints.
  - Fix B4: run the FFT test on an inner patch with a window, compare peaks with the radially averaged spectrum, and require matching symmetric peaks.
  - Use a percentile of local variance instead of the maximum.
  - Region proposals from colour clustering, SAM 2 automatic masks or box prompts inside the garment, and `easyocr` text boxes.
  - Texture segmentation (syllabus Units II and III): a Gabor filter bank and DWT features clustered into regions; Hough lines to find stripes.
- Label each region: text, logo or graphic, stripes, colour block, all-over print (rules first, then zero-shot labels on crops with SigLIP or the fashion SigLIP).
- Metrics: region IoU and type accuracy against the reference design regions; false positives on the plain c_002.

### P16 Several unlabelled photos with automatic view detection (replaces P02)
Goal: the pipeline accepts a folder of 1 to N photos of one garment, in any order and with any file names, works out which photo is the front, back, side or a close-up, and uses each photo for the right panel.
- **Per-photo labels:** view (front, back, side, close-up, other such as a size chart, label or packaging), presentation (flat lay, mannequin, on a person) and a usability score (blur, garment area, garment cut by the frame).
- **Methods, compared:**
  1. Zero-shot baselines: SigLIP 2, CLIP ViT-L/14 and Marqo-FashionSigLIP, with prompt ensembles (text encoded once; positive classes instead of "not a t-shirt").
  2. **Trained model (preferred):** small classifiers on frozen image features, trained on the view labels in the DeepFashion In-shop file names. Compare the syllabus classifiers (naive Bayes, KNN, an ANN/MLP) and logistic regression, with and without PCA or LDA; fine-tune the last layers only if all are weak.
  3. Geometric cues: a face means a front view on a person; the front neckline sits lower than the back; prints are usually on the front.
- **Decision across the whole set**, not photo by photo: front and back must be different photos, chosen together (best joint score); a same-garment check (colour histogram, feature similarity, SIFT or HOG matching, as in content-based retrieval) flags photos of a different item.
- **Use of each photo:** front photo for the front panel, colour and design; back photo for the back panel texture, colour and back design (today the back panel gets a flat median colour); colour fused across views; close-ups kept for later (registration is plan L1).
- **Output:** new file `image_info/view_assignment.json`. With a single photo, behaviour stays as today.
- **Evaluation:** view accuracy and a confusion matrix on the held-out In-shop test split; multi-photo test sets built from In-shop items (all photos of one item, shuffled and renamed) for the full routing; the 5 Mirra photos (c_002 is the only back view, so report how small that test is).

### P06 Shape attributes from the outline
- From the mask contour: sleeve length class, neckline depth, shoulder slope, fit (width against length), and the ratios hem/chest and sleeve/body length.
- Garment landmarks (shoulder points, armpits, hem corners) from contour curvature, Harris corners and Hough lines (syllabus Unit II).
- Corner and keypoint detectors compared on every photo: Harris, Shi-Tomasi, Hessian, FAST, ORB, SIFT, AKAZE and contour-curvature points; every detector's output is saved (a corner gallery per photo).
- Only the flat photos (c_002, c_004) give clean ratios; on-person photos are reported with that caveat.
- Compare the measured ratios with the fixed ratios in `step_05_0_panel_generation_clo.py` (hem/chest 0.9307, wrist/bicep 0.7840).

### P07 Trained attribute models
- Train small classifiers on frozen image features (SigLIP 2 or fashion SigLIP) with Fashionpedia attribute labels: textile pattern (plain, stripe, floral, letters and numbers, and so on), sleeve length and neckline type. Use the Fashionpedia val split with a held-out part, or more Fashionpedia data if needed.
- Compare the syllabus classifiers (naive Bayes, KNN, ANN/MLP) with logistic regression, with PCA or LDA, and try semi-supervised pseudo-labels on unlabelled photos.
- Optional: a pixel classifier (random forest on colour and texture features) for garment versus background, as a classical baseline.
- Save every model's predictions next to the others, for the paper.

### P14 Evaluation on public datasets
- Run v0 and the winning methods on: Fashionpedia val (tops; masks and attributes), VITON-HD test (product photos of tops with cloth masks), DeepFashion2 upper-body masks, Fashion Product Images (product photos with colour labels), and DressCode test (other garment types, to see what carries over beyond T-shirts).
- Report mask IoU, colour accuracy, attribute and design-pattern accuracy, so the paper has numbers beyond five photos.

### P17 Fine-tune a small segmentation model
- Fine-tune a small YOLO segmentation model on garment masks (DeepFashion2 upper-body masks and VITON-HD cloth masks), on the GPU.
- Compare it with SAM 2, the SegFormer parsers and the classical methods from P01 on held-out photos and on the 5 Mirra photos.

### P19 Per-panel pixel maps
Today [V]: `step_06_0_texture_projection.py` already writes one image per panel at 10 pixels per cm (front and back 520 x 710 px for a 52 x 71 cm panel), but:
- the whole garment, sleeves included, is squeezed into the front panel by one box-to-box warp;
- the back and the sleeves are a single flat colour;
- Step 3 applies each image as a repeating fabric swatch on one shared fabric, so it tiles, shows transparent holes and overwrites other panels (comment in `clo_vto/native_vto/step_08_apply_fabric.py`).

Goal: one image per panel (front, back, left sleeve, right sleeve) where every pixel stands for a fixed patch of fabric (for example 1 mm), cut from the right part of the right photo.
- Map regions to panels: front torso to the front panel, each sleeve region (from the outline, P06 landmarks or the parser's sleeve labels) to its sleeve, the back photo (P16) to the back panel.
- Warp with landmarks (thin-plate spline or piecewise affine from shoulder, armpit, neck and hem points to the same points on the panel) instead of one box-to-box warp.
- Higher resolution where the photo allows it (logos and text), no transparent holes (fill from neighbouring fabric), and a side-car JSON giving each image's size in mm and its origin on the panel, so CLO can place it 1:1.
- When no back photo exists: fill the back from the front's fabric colours without the print, and record that this is an assumption.
- Applying the maps in CLO (one fabric per panel, or a placed graphic covering the whole panel) needs plugin changes outside `product_ingestion/`: see `questions.md` Q6.

### P20 Live CLO test (if the main work is done in time)
What is already known [V] (repo records and the installed files, checked 2026-11-20):
- CLO 2026.1.336 (build 58954) is installed at `C:\Program Files\CLO Standalone OnlineAuth\CLO_Standalone_OnlineAuth_x64.exe`; the installed plugin `plugins\RestPlugin_v1.3.2.dll` (built 2026-11-10 against SDK 336) matches it.
- Launch: start the exe with `MIRRA_PLUGIN_PORT` set (as `clo_workspace/clo_pool.py` does). Build: `clo_workspace/build_plugin.py`. Switch versions: `clo_workspace/scripts/switch_plugin.py` (vault of plugin DLLs). Checks: `/health` (`host_matches_sdk`), `/status`, `/wait` events. Modal dialogs: `rev-eng/experiments/e07_modal_watchdog.py` lists and dismisses them.
- Screenshots: capture the screen with Pillow or PowerShell and inspect the image.

Tested live on 2026-11-20 [V]:
- Launching CLO with `MIRRA_PLUGIN_PORT=50505` works; it opened signed in, with no dialogs.
- **Starting the REST server is now automated:** `pywinauto` (UI Automation) clicks Plugins > "REST Server Execute", then OK; `/health` then returned `ok`, host 2026.1.336, `host_matches_sdk: true`, `has_events: true`.
- Closing CLO through UI Automation works with no save prompt on an empty scene.
- Screenshots work with Pillow `ImageGrab` (1920 x 1080), as long as the screen stays on and unlocked (the laptop is set to never sleep on AC power).
- Build prerequisites exist: CLO SDK 2026.1.336 in `C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.336_Win` and Visual Studio 18 with MSVC; `cmake` is not on the PATH (see `ISSUES.md` I3).

Remaining gap: copying a rebuilt plugin into the CLO `plugins` folder needs administrator rights (`questions.md` Q7). Without that, only the installed plugin can be tested.

Steps:
1. Smoke test with the installed plugin: launch, start the server, `/health`, run Step 3 for one cloth with the current textures and with the new P19 pixel maps; screenshots of the draped garment from front and back.
2. If per-panel fabrics are needed (user approved changing the plugin, Q6): add plugin routes for one fabric per panel and 1:1 image placement (SDK calls listed in `.agent/saumy/10_03/18-10-product_ingestion/06-sdk-gap-analysis.md`), bump the plugin version (keep 1.3.2 in the vault so it can be switched back), build, install (needs Q7), re-test. Keep the Windows and macOS plugin contract in step (`clo_workspace/plugin_contract.json`).
3. Record every screenshot and result in `out/p20_clo/` and the plan record. Stop at the first modal dialog that cannot be dismissed safely.

### P18 Texture check and previews
- Project each panel texture back into the photo's garment shape and compare it with the photo (ΔE per colour region, structural similarity), so we can show the textures match the photo with numbers.
- Make a flat preview (all panels laid out, textured) and a simple 3D preview where possible, so the result can be seen without CLO. The real CLO drape waits for the user (needs CLO running; see `questions.md` Q6 for multi-colour panels).

### P10 Wire into the pipeline
- Make the improved methods the default in the step files, with `v0` still selectable.
- Runner: accept a folder of several photos (P16) and pass each photo to the right stage.
- Add regression tests for B1 to B7; all tests pass.
- Run the full pipeline on c_001 to c_005 and on a few multi-photo sets; check the output layout (only new files and keys).

### P11 Results tables and figures
- `results/`: one CSV per area, comparing v0, each change and the final version.
- `images/`: contact sheets per stage and per model, the filter grid, design-region overlays, view-detection examples, and a pipeline diagram.

### P13 Executable package and README
- A README for the CV work: what it does, setup (`.venv`, `requirements.txt`, CUDA build note), one command per experiment, one command for the full pipeline, where the outputs appear.

### P12 Paper material pack (the user writes the paper)
- In `paper/`: a one-page summary of the method per stage, the figure list with file paths, the final numbers with their `results/` sources, the "how it improved over time" timeline from `plans/`, the limitations, and candidate citations (journal papers from `.agent/cv-course-project/`, tools listed as software). No paper text.

### Later phase (the user decides on these in the morning)

| ID | Plan | What it needs |
|---|---|---|
| L1 (was P08) | The user's own photos: front, back, close-up, angled shot, with an A4 sheet in frame; homography to straighten angled photos and give real centimetres; register a close-up of the print onto the full photo (SIFT, RANSAC homography) for a sharper design | Photos from the user in `data/own_photos/<shirt>/` (P16 makes the pipeline ready for them) |
| L2 (was P09) | GenAI comparison (for example Gemini): ask for view, colours, design text and boxes, and compare with our outputs; comparison only, never the method | The user's yes to send photos to an external service, and a key in the `GEMINI_API_KEY` environment variable |

---

## 5. Decisions made by the user
- *2026-11-20:* torch swapped to the CUDA build of 2.4.1; `ultralytics`, `easyocr` and `open_clip_torch` installed; Fashionpedia val and DeepFashion In-shop (filtered) downloaded; further datasets and pretrained models may be downloaded without asking.
- *2026-11-20:* the pipeline must take several unlabelled photos (P16), with a trained model preferred.
- *2026-11-20:* own photos and Gemini moved to the later phase (L1, L2).
- *2026-11-20:* the user writes the paper; I prepare the material.
- *2026-11-20:* packages may be installed or upgraded during the research; the user restores the environment afterwards from `env/` (snapshot taken).
- *2026-11-20:* to free space I may delete only `.venv` packages, datasets I downloaded, earlier versions of my trained models, and open-weight models I used; nothing that existed before; every deletion logged in `DELETIONS.md`.
- *2026-11-20:* syllabus received (`syllabus-cv.png`); plans mapped to it (section 2.5).
- *2026-11-20:* research starts only on the user's start command.

Open questions are kept only in `questions.md`.

## 6. Change log
| Date | Change |
|---|---|
| *2026-11-20* | Plan written |
| *2026-11-20* | User's update: use the GPU, run tests only after a working change, never delete runs, the user writes the paper (P12 became a material pack) |
| *2026-11-20* | User's update: shorter time boxes; plans run in parallel waves of Sonnet (high effort) sub-agents that I judge; I may change the plan on my own. Added P14 (public-dataset evaluation) and P15+ (improvement passes) |
| *2026-11-20* | User's update: P08 and P09 became the later-phase plans L1 and L2. New Must plan P16 (several unlabelled photos, trained view model), which absorbs P02 |
| *2026-11-20* | Setup finished (GPU, packages, two datasets). P07 refocused on trained attribute models using Fashionpedia labels. Open questions moved to `questions.md` |
| *2026-11-20* | Syllabus added: every plan now names the syllabus methods it compares (section 2.5). Environment snapshot and deletion rules added. Waiting for the start command |
| *2026-11-20* | More datasets downloaded for evaluation and training. Added P17 (fine-tuned segmentation model) and P18 (texture check and previews). P03 and P06 now save a full gallery of edge and corner detectors per photo |
| *2026-11-20 07:20* | Wave 0 done (v0 pipeline score 0.407). Started P06 and P19 (+P18) early on the reference masks to use the night; RAM (16 GB) and disk (C: 1.7 GB free at worst) became the limits, see `ISSUES.md` I7 and I8 |
| *2026-11-20 14:10* | Wave 1 finished (P01, P03, P04, P05, P06, P07, P16, P19 all accepted; records 02 to 08 written 09:17 to 10:02, P01's at 14:12 after the 10:25 to 14:05 stop, `ISSUES.md` I20). Wave 3 started: full pipeline run on all 5 photos, P15a (segmentation auto-choice), P15b (design relabelling), then P17 |
| *2026-11-20 14:50* | P15b accepted: design default `v4_relabel` (SigLIP 2 relabelling + two fixes); c_004 reference text box corrected (I18) |
| *2026-11-20 15:55* | With the user's OK (Q8) the stopped jobs were restarted one at a time. The final run with the final defaults gives end-to-end 0.960 (first pass 0.911, v0 0.407). The multi-photo demo after the outline fix outlines only the top on both sets |
| *2026-11-20 15:20* | Outline fix: parser-prompted masks may cover down to 1 % of the image (tops in full-body photos; found by the multi-photo demo, I23). Claude Code stopped the P10 second pass, the demo re-run and the watchdog for low memory (I22); restarts wait for the user (Q8) |
| *2026-11-20 15:15* | P17 accepted as a comparison: our fine-tuned YOLO26s-seg ties the v1 pipeline on public data at 5 % of the time but is weaker on street photos and misses c_003's lower half, so `v1_auto` stays the default. Agreement-with-judgement check done (P00) |
| *2026-11-20 15:05* | P15a accepted: segmentation default `v1_auto` (v1_all only when a skirt is found and no head is visible). Times in plan records 02 to 10 corrected from file times (I20) |
| *2026-11-20* | User's update: test with CLO if the main work finishes in time. Added P20 (live CLO test, plugin changes allowed for per-panel fabrics; Q6 answered). Installing a rebuilt plugin needs admin rights (Q7) |
| *2026-11-20* | User's update: P00 now first decides how methods are scored (candidate metrics, damage tests, agreement with judgement by eye); P01 tries combinations of 2 or 3 methods; P04 never reduces a shirt to one colour. New P19 (per-panel pixel maps) takes over `step_06_0_texture_projection.py` from P16 |
