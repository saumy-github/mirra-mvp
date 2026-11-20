# CV index

*Last updated: 2026-11-20 15:55*

Reading order: `questions.md` (anything waiting for you) -> `PLAN.md` (status of every plan) -> `plans/` (what each plan did and found) -> `results/` and `images/` -> `paper/PAPER_MATERIAL.md`.

## Top level

| File | Purpose |
|---|---|
| `INDEX.md` | This file |
| `README.md` | Code README for the GitHub submission (what it does, results, setup, how to run, how to reproduce) |
| `RULES.md` | Rules every plan and sub-agent follows |
| `PLAN.md` | Master plan: goal, starting point, syllabus coverage, every plan with status, how the parallel work runs, decisions, change log |
| `questions.md` | Questions for the user, each marked open or answered |
| `DELETIONS.md` | Log of anything deleted to free disk space, and the rules for what may be deleted |
| `ISSUES.md` | Log of anything that failed or was blocked, its cause and what was done |
| `MIRRA_product_ingestion_review.md` | The user's suggestion file (bugs B1 to B7, prompting and optimisation ideas); input to the plans |
| `syllabus-cv.png` | Course syllabus (CO CSC 601 Computer Vision), mapped to the plans in `PLAN.md` section 2.5 |

## Folders

| Folder | Holds | State |
|---|---|---|
| `env/` | `pip-freeze-2026-11-20.txt` (snapshot of the working `.venv`) and `ENVIRONMENT.md` (restore guide and package-change log) | ready |
| `data/` | Downloaded datasets (table below) | ready |
| `scripts/` | `evaluate.py` (shared scoring, standard prediction format), `gpu_lock.py` (one GPU job at a time, waits for free memory), `resource_watch.py` (disk and memory log), `demo_read_garment.py` (runs every new stage on a folder of photos, no database), `p10_run_all.py` (full pipeline on the 5 photos + scoring), and each plan's `pNN_*.py` | ready |
| `plans/` | One record per finished plan, in the order finished (list below) | ongoing |
| `out/` | Raw outputs, one subfolder per plan with its `REPORT.md`: `p00_baseline/` (references, v0 snapshot, blind judgement sheets), `p01_segmentation/`, `p03_filters/`, `p04_colour/`, `p05_design/`, `p06_shape/`, `p07_attributes/`, `p10_pipeline_runs/` (first pass), `p10_pipeline_runs_v2/` (final run with the final defaults), `p15a_seg_autoselect/`, `p15b_design/`, `p16_multiview/`, `p17_yolo_seg/` (dataset, training runs, weights), `p19_panel_maps/`, `demo_inputs/` (shuffled In-shop photo sets + hidden truth), `demo/` (demo outputs, including the failed full-body outlines). Never deleted. `resource_watch.log` tracks free disk and memory | ongoing |
| `results/` | `mirra_scores.csv` (every scored method; the latest row per label counts), `mirra_summary_by_method.csv`, `mirra_before_after.csv`, `v0_baseline.csv`, `metric_sanity*.csv`, `judgement_agreement.csv`, `public/` (each plan's public-dataset results, 30 files) | ongoing |
| `images/` | `fig_before_after_scores.png`, `fig_outline_public_iou.png`, and 23 key figures copied from the plans (named `pNN_*`) | ongoing |
| `paper/` | `ieee/` (the submitted IEEE paper: `paper.pdf`, LaTeX source `main.tex`, `figures/`), `PAPER_MATERIAL.md` (method per stage, numbers with sources, figure list, timeline, limitations), `citations_candidates.md` | done |

## Plan records (`plans/`)

| Record | Plan | Result in one line |
|---|---|---|
| `01_p00_baseline_and_scoring.md` | P00 | Scoring framework chosen by damage tests and checked against a blind by-eye ranking; v0 scores 0.407 |
| `02_p03_enhancement_filters_edges.md` | P03 | Bilateral + Laplacian best for print edges; global enhancement hurts colour |
| `03_p06_shape_landmarks_corners.md` | P06 | Landmarks and ratios from the outline; reliable on flat photos only |
| `04_p19_p18_panel_pixel_maps.md` | P19, P18 | Per-panel thin-plate-spline pixel maps |
| `05_p04_multicolour_extraction.md` | P04 | Mean-shift in CIELAB; bugs B1-B3 fixed; palettes with roles |
| `06_p07_trained_attribute_models.md` | P07 | Trained sleeve, pattern and neckline classifiers |
| `07_p16_multi_photo_views.md` | P16 | Trained view classifier + joint front/back choice + same-garment check |
| `08_p05_design_regions.md` | P05 | Two-level outlining; fixed periodicity test (B4) |
| `09_p01_garment_outline.md` | P01 | Parser box → SAM 2 (v1); 58 methods compared |
| `10_p10_pipeline_integration.md` | P10 | Everything in the runner; end to end 0.407 → 0.911 (first pass) → 0.960 (final defaults); multi-photo demo |
| `11_p15b_design_relabel.md` | P15b | SigLIP 2 relabelling + fixes; design score 0.904 on realistic masks |
| `12_p15a_segmentation_autoselect.md` | P15a | `v1_auto` head rule; c_003 fixed with no public loss |
| `13_p17_finetuned_yolo_segmentation.md` | P17 | Our fine-tuned YOLO26s-seg ties v1 at 5 % of the time (comparison only) |

## Code and models added outside this folder (in `product_ingestion/`)

| Path | Plan | Purpose |
|---|---|---|
| `multi_view.py` | P16 | Several unlabelled photos → views, presentation, same-garment check |
| `cv_segment.py` | P01, P15a | Segmentation methods and combinations, mask clean-up, quality signals, outline polygon, `auto_skirt_decision` (v1_auto rule) |
| `cv_enhance.py` | P03 | Enhancement, restoration, shading removal, smoothing filters, edge detectors |
| `cv_design_regions.py` | P05, P15b | Design-region proposers, fixed periodicity test, SigLIP 2 relabelling, text-line split |
| `cv_shape.py` | P06 | Landmarks, sleeve class, ratios, corner detectors |
| `cv_attributes.py` | P07 | Trained attribute classifiers (inference) |
| `cv_panel_maps.py`, `cv_texture_check.py` | P19, P18 | Per-panel pixel maps and their check |
| `models/view_classifier/`, `models/attributes/` | P16, P07 | Trained small classifiers used by the pipeline |
| `tests/test_colour_regression.py`, `tests/test_design_regression.py`, `tests/test_segmentation_autoselect.py` | P10, P15a | Regression tests for B1-B4 and the v1_auto rule (full suite: 51 tests) |
| step files `step_01` to `step_06`, `run_product_ingestion.py` | all | New defaults (segmentation `v1_auto`, colour v1, design `v4_relabel`, views trained, textures v1), with `method="v0"` still selectable |

The fine-tuned YOLO weights (P17, not used by the pipeline) are in `out/p17_yolo_seg/runs/run2-2/weights/best.pt`.

## Datasets in `data/`

| Folder | Source | Size | Licence | Used for |
|---|---|---|---|---|
| `data/fashionpedia/` | Fashionpedia val/test images (`val_test2020.zip`, unpacked to `test/`) and `instances_attributes_val2020.json` | 3,200 photos (labels for the 1,158 val photos); 251 MB download | CC BY 4.0 | Garment masks and attributes for P01, P05, P07, P15a, P17 |
| `data/deepfashion_inshop_filtered/` | Hugging Face `ryushinn/DeepFashion-Inshop-Filtered` (train and test parquet) | 157 MB | DeepFashion: non-commercial research only (not for shipping in Mirra) | View labels from file names (`_front`, `_side`, `_back`, `_full`) and several photos per item: P16 and the multi-photo demo |
| `data/vitonhd_test/` | Hugging Face `SaffalPoosh/VITON-HD-test` (2 parquet files: cloth photo, cloth mask, person photo, parsing, pose) | 696 MB on disk | VITON-HD: research only (CC BY-NC) | Product and person photos with exact garment masks: P01, P04, P05, P06, P15a, P16, P17 |
| `data/fashion_product_images_small/` | Hugging Face `ashraq/fashion-product-images-small` (Kaggle "Fashion Product Images (Small)") | 259 MB on disk | As on Kaggle (no licence stated on the mirror) | Product photos with `articleType` and `baseColour` labels: colour accuracy at scale in P04 |
| ~~`data/deepfashion2_upper_masks/`~~ | Hugging Face `zyuzuguldu/deepfashion2-upper-body-masks` | 397 MB | DeepFashion2: research only | *Deleted 2026-11-20: masks only, no photos (unusable); see `DELETIONS.md`* |
| ~~`data/fashionpedia_train/`~~ | Fashionpedia train annotations, fetched by the P07 agent | 740 MB | CC BY 4.0 | *Deleted 2026-11-20 to free disk; see `DELETIONS.md`* |
| ~~`data/dresscode_test/`~~ | Hugging Face `zhengchong/DressCode-Test` | 1.3 GB | DressCode: research only | *Deleted 2026-11-20 to free disk (unused); see `DELETIONS.md`* |

Not downloaded, and why:
- **LogoDet-3K:** 3 GB of generic logos, not on clothes.
- **Full DeepFashion2:** 13 GB, and the upper-body subset covered the need.
- **GarmentCodeData, SewFactory and CLOTH3D:** huge, and synthetic 3D rather than photos.
- **Deep Fashion3D, MGN and full DressCode:** need sign-up forms.
- **TopLogo-10:** no copy found online.
- **Filtered iMaterialist:** overlaps Fashionpedia.
