# Reading garments from product photos: outline, shape, colour and design

*Status: working implementation; results as of 2026-11-20 15:55*

*Saumy Bhargava, Tanuj · Department of CSE*

- **Paper (IEEE format):** [paper.pdf](paper/ieee/paper.pdf) · LaTeX source and figures in [`paper/ieee/`](paper/ieee/)
- **Video:** [project video (Google Drive)](https://drive.google.com/file/d/1J8ur4lS7roI6ZQLvHU8DKd8zmeqk5Ldz/view?usp=sharing)

A Computer Vision course project (CO CSC 601) built on the product-ingestion step of Mirra, a virtual try-on system. Given one or several unlabelled photos of a T-shirt, the code:

1. works out which photo is the front, back, side or other (a trained view classifier), and whether the shirt is flat or worn;
2. cuts the garment out and draws its outline;
3. reads its shape: landmarks, sleeve length, width and length ratios;
4. reads all its colours: a palette with fabric/print roles and a colour region map, never just one colour;
5. finds and outlines each design on the shirt (text, graphic, logo, stripes, colour block, all-over pattern) and labels it;
6. predicts attributes with trained classifiers (pattern, sleeve length, neckline);
7. builds one texture image per sewing-pattern panel (front, back, sleeves), each pixel a fixed patch of fabric.

Every stage compares three kinds of method, and every attempt's output is kept:
- **classical syllabus methods:** filters, edge and corner detectors, graph cut, clustering, Gabor/wavelet texture, classical classifiers;
- **pretrained models used zero-shot:** SAM 2, SegFormer, SigLIP 2, Grounding DINO, YOLO/YOLOE, OCR;
- **models trained in this project:** view and attribute classifiers, and a fine-tuned YOLO26s-seg garment segmenter.

## Results
**End to end on the 5 Mirra product photos**, same scoring before and after (`results/mirra_before_after.csv`):

| Area | Before (v0) | First new pipeline | Final pipeline |
|---|---|---|---|
| Outline | 0.658 | 0.919 | 0.974 |
| Colour | 0.808 | 0.951 | 0.962 |
| Design | 0.160 | 0.774 | 0.903 |
| View | 0.000 | 1.000 | 1.000 |
| **Pipeline** | **0.407** | **0.911** | **0.960** |

The final column adds two improvement passes, now the defaults:
- **Outline, `v1_auto`:** the colour-block shirt c_003 goes from IoU 0.562 to 0.940.
- **Design, `v4_relabel`:** the design score with realistic masks goes from 0.774 to 0.904.

**On public data with exact labels** (`results/public/`):
- **Outline:** mean IoU 0.756 (v0) → 0.892 (final default) over VITON-HD product, VITON-HD person and Fashionpedia street photos. Classical methods reach 0.43 to 0.62. Our fine-tuned YOLO26s-seg reaches 0.889 at 0.03 s per photo, against 0.59 s.
- **Front/back:** the right front is chosen in 85 % of shuffled photo sets.
- **Sleeve length:** classifier macro-F1 0.84.

Details: `paper/PAPER_MATERIAL.md` and the plan records in `plans/`.

## Setup (Windows, Python 3.12)
From the repository root:
```
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```
- **GPU (optional, recommended):** the CUDA build of the same torch version:
  ```
  .venv/Scripts/python.exe -m pip install --no-deps torch==2.4.1+cu121 torchvision==0.19.1+cu121 --index-url https://download.pytorch.org/whl/cu121
  ```
- **Models:** pretrained models download from Hugging Face on first use (SAM 2 large, SegFormer clothes parser, SigLIP 2, Marqo-FashionSigLIP, Grounding DINO tiny, EasyOCR).
- **Trained models:** the small classifiers trained in this project are in `product_ingestion/models/` (view classifier, attribute classifiers).
- **Exact package set** used for the results: `env/pip-freeze-2026-11-20.txt` (restore guide: `env/ENVIRONMENT.md`).

## How to run
**1. Read a garment from photos (no database needed).** Give a folder with one or several photos of ONE garment, in any order and with any names:
```
.venv/Scripts/python.exe product_ingestion/CV/scripts/demo_read_garment.py <your folder>
.venv/Scripts/python.exe product_ingestion/CV/scripts/demo_read_garment.py <your folder> --no-attributes
```
- **Test photos are not in the repository:** the Mirra product photos (`product_ingestion/input/`) are kept out of git, and the DeepFashion In-shop demo sets cannot be republished under their licence. Use your own photos, or download DeepFashion In-shop (see `INDEX.md`) and put the photos of one item in a folder, shuffled and renamed.
- **Output, in `out/demo/<name>/`:**
  - `garment_reading.json`: views, outline, palette, design regions, shape, attributes;
  - an overlay with the outline and labelled design boxes, for the front and the back photo;
  - landmark images.

**2. Only the view assignment for a set of photos:**
```
.venv/Scripts/python.exe product_ingestion/multi_view.py <folder> --out view_assignment.json
```

**3. The full Mirra product-ingestion pipeline.** This needs the project's MongoDB with cloth and size documents. It produces panels (DXF/SVG) and per-panel textures too:
```
.venv/Scripts/python.exe product_ingestion/run_product_ingestion.py --cloth-id c_001 --size-id s_001 [--no-attributes] [-o <output root>]
```
- **Defaults:** segmentation `v1_auto`, colour `v1`, design `v4_relabel`, views `trained`, textures `v1`.
- **Old behaviour, for comparison:** `method="v0"` in each step function, or `MIRRA_SEG_METHOD=v0` (or `v1`, `v1_all`) for segmentation.
- **Unit tests:** `.venv/Scripts/python.exe -m pytest product_ingestion/tests -q` (51 tests).

**4. Score any method the same way:**
```
.venv/Scripts/python.exe product_ingestion/CV/scripts/evaluate.py --pred <prediction folder> --label <name>
```
The prediction format is described at the top of `scripts/evaluate.py`.

**5. Reproduce the experiments.** Each plan's scripts are in `scripts/` and named after the plan:

| Plan | What | Main scripts |
|---|---|---|
| P00 | References, baseline, metric damage tests, blind judgement check | `p00_*.py`, `evaluate.py` |
| P01 | Garment outline (58 methods; public sets) | `p01_build_subsets.py`, `p01_raw_models.py`, `p01_methods.py`, `p01_public_summary.py` |
| P03 | Enhancement, smoothing filters, edge detectors | `p03_edge_study.py`, `p03_enhance_study.py`, `p03_figures.py` |
| P04 | Colour clustering and bug fixes | `p04_synthetic_bugs.py`, `p04_run_methods.py`, `p04_fpi_eval.py` |
| P05 | Design regions (two-level outlining) | `p05_run_methods.py`, `p05_score_all.py`, `p05_fashionpedia.py` |
| P06 | Shape, landmarks, corner detectors | `p06_overlays.py`, `p06_corners.py`, `p06_ratio_stats.py` |
| P07 | Trained attribute classifiers | `p07_build_dataset.py`, `p07_extract.py`, `p07_train.py`, `p07_final.py` |
| P16 | View classifier and photo sets | `p16_extract_features.py`, `p16_train.py`, `p16_sets.py`, `p16_eval_files.py` |
| P19 | Per-panel pixel maps | `p19_run.py`, `p19_extra.py` |
| P15a | Automatic v1/v1_all choice (14 rules, held-out set) | `p15a_build_heldout.py`, `p15a_features.py`, `p15a_gpu.py`, `p15a_rules.py`, `p15a_final_table.py` |
| P15b | SigLIP 2 relabelling and fixes for designs | `p15b_segment.py`, `p15b_cache.py`, `p15b_run.py`, `p15b_score.py` |
| P17 | Fine-tuned YOLO26s-seg | `p17_build_dataset.py`, `p17_make_small_list.py`, `p17_train.py`, `p17_eval.py` |
| P10, P11 | End-to-end runs and scoring, tables, figures | `p10_run_all.py`, `p10_run_to_standard.py`, `p11_build_results.py`, `p11_figures.py` |

Large experiments need the datasets in `data/`, which are not in the repository (sources and licences in `INDEX.md`). Only one model job should use the GPU at a time (`scripts/gpu_lock.py`); the machine used had a 6 GB GPU and 16 GB RAM.

## Where things are
| Path | Holds |
|---|---|
| `PLAN.md` | Every plan, in order, with its status |
| `plans/` | What each plan did and found (the "how it improved over time" record) |
| `results/` | The metric tables |
| `images/` | The figures |
| `out/` | Each plan's `REPORT.md` and the reference labels used by `scripts/evaluate.py`. The raw outputs of every method (about 36,500 files, failed attempts included) are kept locally, not in the repository |
| `paper/` | The IEEE paper (`ieee/paper.pdf`; LaTeX source `ieee/main.tex` with its figures) and the material it was written from |
| `ISSUES.md`, `DELETIONS.md` | What went wrong, and what was deleted to free space |

## Code added to `product_ingestion/`
| File | Purpose |
|---|---|
| `multi_view.py` | Several unlabelled photos → front / back / side / other, presentation, same-garment check |
| `cv_segment.py` | Segmentation methods, combinations, fixed mask clean-up, quality signals, outline polygon, the v1_auto rule |
| `cv_enhance.py` | Enhancement, restoration, shading removal, smoothing filters, edge detectors |
| `cv_design_regions.py` | Design-region proposers, the fixed periodicity test, SigLIP 2 relabelling, text-line split |
| `cv_shape.py` | Landmarks, sleeve class, ratios, corner and keypoint detectors |
| `cv_attributes.py` | Trained pattern, sleeve and neckline classifiers |
| `cv_panel_maps.py`, `cv_texture_check.py` | Per-panel pixel maps and their check |

The step files `step_01` to `step_06` keep their public functions; each new default keeps `method="v0"` selectable.
