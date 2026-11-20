# Reading Garments from Unlabelled Product Photos

**Outline, Multi-Colour Palette and Two-Level Design Regions for Sewing-Pattern-Driven Virtual Try-On**

*Saumy Bhargava, Tanuj · Department of CSE · Computer Vision course project (CO CSC 601)*

- **Paper (IEEE format):** [paper.pdf](product_ingestion/CV/paper/ieee/paper.pdf) · LaTeX source and figures in [`product_ingestion/CV/paper/ieee/`](product_ingestion/CV/paper/ieee/)
- **Video:** [project video (Google Drive)](https://drive.google.com/file/d/1J8ur4lS7roI6ZQLvHU8DKd8zmeqk5Ldz/view?usp=sharing)
- **Project folder:** [`product_ingestion/`](product_ingestion/) (the product-ingestion pipeline code); the course-project work (plans, scripts, results, figures, paper) is in [`product_ingestion/CV/`](product_ingestion/CV/)

The project is built on the product-ingestion step of Mirra, a virtual try-on system (`product_ingestion/`). Given one or several unlabelled photos of a T-shirt, the code:

1. works out which photo is the front, back, side or other (a trained view classifier), and whether the shirt is flat or worn;
2. cuts the garment out and draws its outline;
3. reads its shape: landmarks, sleeve length, width and length ratios;
4. reads all its colours: a palette with fabric/print roles and a colour region map, never just one colour;
5. finds and outlines each design on the shirt (text, graphic, logo, stripes, colour block, all-over pattern) and labels it;
6. predicts attributes with trained classifiers (pattern, sleeve length, neckline);
7. builds one texture image per sewing-pattern panel (front, back, sleeves), each pixel a fixed patch of fabric.

Every stage compares three kinds of method:
- **classical syllabus methods:** filters, edge and corner detectors, graph cut, clustering, Gabor/wavelet texture, classical classifiers;
- **pretrained models used zero-shot:** SAM 2, SegFormer, SigLIP 2, Grounding DINO, YOLO/YOLOE, OCR;
- **models trained in this project:** view and attribute classifiers, and a fine-tuned YOLO26s-seg garment segmenter.

## Results
**End to end on the 5 Mirra product photos**, same scoring before and after (`product_ingestion/CV/results/mirra_before_after.csv`):

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

**On public data with exact labels** (`product_ingestion/CV/results/public/`):
- **Outline:** mean IoU 0.756 (v0) → 0.892 (final default) over VITON-HD product, VITON-HD person and Fashionpedia street photos. Classical methods reach 0.43 to 0.62. Our fine-tuned YOLO26s-seg reaches 0.889 at 0.03 s per photo, against 0.59 s.
- **Front/back:** the right front is chosen in 85 % of shuffled photo sets.
- **Sleeve length:** classifier macro-F1 0.84.

Details: the paper, `product_ingestion/CV/paper/PAPER_MATERIAL.md` and the plan records in `product_ingestion/CV/plans/`.

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
- **Exact package set** used for the results: `product_ingestion/CV/env/pip-freeze-2026-11-20.txt` (restore guide: `product_ingestion/CV/env/ENVIRONMENT.md`).

## How to run
**1. Read a garment from photos (no database needed).** Give a folder with one or several photos of ONE garment, in any order and with any names:
```
.venv/Scripts/python.exe product_ingestion/CV/scripts/demo_read_garment.py <your folder>
.venv/Scripts/python.exe product_ingestion/CV/scripts/demo_read_garment.py <your folder> --no-attributes
```
- **Test photos are not in the repository:** the Mirra product photos (`product_ingestion/input/`) are kept out of git, and the DeepFashion In-shop demo sets cannot be republished under their licence. Use your own photos, or download DeepFashion In-shop (see `product_ingestion/CV/INDEX.md`) and put the photos of one item in a folder, shuffled and renamed.
- **Output, in `product_ingestion/CV/out/demo/<name>/`:**
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
The prediction format is described at the top of `product_ingestion/CV/scripts/evaluate.py`.
