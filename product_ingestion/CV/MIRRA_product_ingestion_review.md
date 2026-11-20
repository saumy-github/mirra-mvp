# MIRRA — `product_ingestion/` Review and Optimization Plan

**Repo:** `saumy-github/mirra-mvp` (reviewed on `main`, which is ~1 month ahead of the `Tanuj` branch for this folder; the only differences are in `run_manifest.py` and `run_product_ingestion.py`)
**Purpose:** Computer Vision course submission. Suggests optimizations to the product ingestion pipeline (model prompting and everything else), grounded in the two uploaded papers.
**Date:** November 2026

---

## 1. Source papers

| # | Paper | Venue | Why it matters here |
|---|---|---|---|
| P1 | Lyu, Wang, Ye, Sun, Chao — *Body data-driven garment pattern construction in digital fashion innovations: a review* | Textile Research Journal, 2026, 96(11–12):1299–1335 (DOI 10.1177/00405175251352800) | Frames pattern construction by body data dimension (1D → 4D). Says parametric pattern systems work best when 1D measurements are **automatically extracted from photos/scans** and fed in as parameters. Also notes CNNs are commonly used to extract measurements and garment specs from 2D images. |
| P2 | Luo, Qu, Zhao, Zhang, Yang — *Deep Learning for 3D Fashion Design: Survey From a Sewing Pattern–Driven Perspective* | IEEE Transactions on Circuits and Systems for Video Technology, 2026 | Proposes a 4-stage pipeline: **representation → generation → reconstruction → editing**. "Image-based reconstruction" is a named stage. Lists evaluation metrics: #Panels, #Edges, **Panel L2**, Rot/Trans L2, stitch precision/recall, Average Matching Distance, **panel IoU (rasterized)**, Chamfer Distance, CLIP Score. |

Both are **journal** papers, which matters because the CV instructor requires journal-only citations.

> Note: P2's uploaded PDF (a Firefox "PDF.js viewer" print) has a shifted font encoding; the text was decoded for reading. Numbers inside P2 should be checked against the original before quoting.

---

## 2. What the pipeline does today

Entry point: `product_ingestion/run_product_ingestion.py`

| Stage | File | Method |
|---|---|---|
| 1. View selection | `view_selection.py` → `garment_router.py` | CLIP ViT-B/32 zero-shot, 4 text prompts (front / back / side / irrelevant) |
| 2. Segmentation | `segmentation.py` | SAM 2 (`facebook/sam2-hiera-large`) with point prompts → fallback U²-Net via `rembg` |
| 3. Colour | `colour_extraction.py` | Skin-pixel HSV filter → K-Means in LAB, K picked by silhouette score |
| 4. Design | `design_extraction.py` | Auto-Canny + contours + local variance + FFT "repeating pattern" test |
| 5. Panels | `panel_generation_clo.py` + `clo_block/` | Reverse-engineered CLO parametric T-shirt block → DXF (mm) + SVG |
| 6. Texture | `texture_projection.py` | Bounding-box-to-bounding-box warp of the photo onto each panel |

### Key finding: the photo never affects the garment's shape

`run_product_ingestion.py:362-363`:

```python
measurements = GarmentMeasurements.from_sizes_db(size_id)
panel_result = generate_panels(measurements, panels_dir, size_label=size_id)
```

Panel geometry comes **only from the size chart in MongoDB**. The image only drives colour, print, and texture. Even the hem and wrist widths are fixed CLO ratios (`panel_generation_clo.py`):

```python
HEM_TO_CHEST_RATIO   = 269.9999 / 290.0975   # 0.930697
WRIST_TO_BICEP_RATIO = 384.3506 / 490.2734   # 0.783952
```

The module's own docstring says that until `hem_width_cm` / `wrist_width_cm` exist in the size documents, "a straight-sided tee is impossible to express".

This is exactly the gap both papers point to (P1: automatic photo → measurement → parametric system; P2: image-based reconstruction stage). **It is the strongest CV contribution available** (Section 6).

---

## 3. Confirmed bugs (reproduced on synthetic inputs)

All of these were run against the repo code, not inferred.

| # | Location | What happens | Evidence |
|---|---|---|---|
| B1 | `colour_extraction.py:49-52, 271` | The HSV skin filter (H 0–25 / 165–180, S 20–170, V 80–255) also matches warm fabrics. Tan, coral, pink and brown tees have **every pixel removed** and colour extraction fails. | tan `#d2b48c`, coral `#f0806e`, pink `#e696aa`, brown `#785032` → all returned "All pixels were filtered as skin". `skin_pixels_removed` also reports 0 on that failure path. |
| B2 | `colour_extraction.py:116, 324-328` | Clusters with L<15 or L>85 are skipped as "shadow/highlight". White and black tees are the most common colours, so they get the wrong base colour. | White tee `#f5f5f5` with fold shading → base `#c4c4c4` (the shadow grey). Black tee + small red print (6%) → base `#dc1e1e` (the print). |
| B3 | `colour_extraction.py:307` | A perfectly uniform-colour image crashes: K-Means is run with K≥2 on one distinct colour, an empty cluster gives NaN, `int(NaN)` raises. | Flat mustard tee `(200,160,60)` → `ValueError: cannot convert float NaN to integer`. Rare with real photo noise, but it's an unhandled crash. |
| B4 | `design_extraction.py:145-153` | FFT "repeating pattern" test uses peak/mean of the magnitude spectrum with threshold 8. Natural images have a ~1/f spectrum, so this ratio is almost always huge. | A **plain grey tee with two soft folds** → `has_design=True, type=pattern, coverage=100%`, FFT ratio **822.5** (threshold 8). |
| B5 | `segmentation.py:393-399` (`_fill_holes`) | Flood-fill starts at pixel (0,0). If the garment touches the top-left corner (common in tight e-commerce crops), the whole background is treated as a "hole" and filled. | Mask covering 56% → after `_clean_mask` covers **100%**. SAM 2's result is then rejected (area > 95%) and the pipeline silently falls back to U²-Net. |
| B6 | `segmentation.py:430-440` | `edge_sharpness_score` runs Sobel on the **binary mask**, not the photo, so it is always ~1.0 for any mask. | Perfect synthetic rectangle → `edge_sharpness_score: 1.0`. |
| B7 | `segmentation.py:446-455` | `hole_count` counts connected components of the inverted mask. The code comment says label 0 is the external background; it's actually the garment. The external background is label 1, so it's always counted as a "hole". It's also measured **after** holes are filled. | Solid mask with no holes → `hole_count: 1, hole_penalty: 0.1`. |

Net effect of B6 + B7: the reported segmentation `quality_score` (0.5·coverage + 0.3·sharpness + 0.2·(1−holes)) carries almost no information.

### Fixes

**B1 — skin filter only when a person is present**

```python
# Only remove skin if a human-parsing model / CLIP "on_model" label says a person is in frame.
if view.presentation == "on_model":
    rgb_pixels, skin_removed = _remove_skin_pixels(rgb_pixels)   # or better: use parser's skin labels
```

Best option: a clothes-parsing model (SegFormer trained on clothing, or SCHP) gives explicit `upper-clothes`, `arms`, `face` labels, so skin is excluded by label, not colour.

**B2 — choose the largest cluster; only skip light/dark clusters if they're small**

```python
palette.sort(key=lambda c: c.percentage, reverse=True)
base = palette[0]
if _is_near_white_or_black(base.lab) and base.percentage < 30:
    base = next((c for c in palette if not _is_near_white_or_black(c.lab)), base)
```

Better still: merge clusters whose ΔE2000 < ~5 (shading of the same fabric), then report the merged cluster's upper-percentile L (the lit fabric, not the shadow).

**B3 — guard empty clusters**

```python
n_distinct = len(np.unique(lab_pixels.round(1), axis=0))
best_k = min(best_k, max(1, n_distinct))
...
if not cluster_mask.any():
    continue
```

**B4 — see Section 5.2.**

**B5 — pad before flood-fill**

```python
@staticmethod
def _fill_holes(mask):
    padded = cv2.copyMakeBorder(mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    inv = cv2.bitwise_not(padded)
    ff = np.zeros((padded.shape[0] + 2, padded.shape[1] + 2), np.uint8)
    cv2.floodFill(inv, ff, (0, 0), 0)          # (0,0) is now guaranteed background
    return cv2.bitwise_or(padded, inv)[1:-1, 1:-1]
```

**B6 / B7 — replace the quality score with signals that mean something**

- SAM 2's own predicted IoU and stability score for the chosen mask.
- Agreement (IoU) between the SAM 2 mask and the fallback model's mask.
- Photo blur: variance of the Laplacian on the garment region.
- Border-touch ratio (fraction of mask pixels on the image border).
- Count holes on the mask **before** `_fill_holes`, skipping label 0 (garment) and the label that touches the border.

---

## 4. Model prompting improvements

### 4.1 CLIP view selection (`garment_router.py:73-81`)

Current prompts:

```python
VIEW_PROMPTS = {
    "front": "a photo of the front of a t-shirt",
    "back": "a photo of the back of a t-shirt",
    "side": "a photo of the side of a t-shirt",
    "irrelevant": "a photo that is not of a t-shirt garment",
}
```

Problems and fixes:

1. **"Irrelevant" is a negation.** CLIP handles "not X" poorly; the text embedding is still close to "t-shirt". Replace with **positive** classes for what actually appears in product galleries: size chart, fabric close-up, label/tag, packaging, lifestyle photo.
2. **Front vs back is hard for ViT-B/32.** Give each class 5–8 templates with visible cues, and average the normalized text embeddings (prompt ensembling, as in the CLIP paper):

   ```python
   GARMENT = "t-shirt"   # parameterize; don't hard-code
   PROMPTS = {
     "front": [
       "a flat-lay product photo of the front of a {g}",
       "the front side of a {g}, showing the lower scooped front neckline",
       "a {g} seen from the front with its chest print visible",
       "a ghost-mannequin photo of the front of a {g}",
     ],
     "back": [
       "a flat-lay product photo of the back of a {g}",
       "the back side of a {g}, showing the higher straight back neckline",
       "the back of a {g} with a neck label visible",
     ],
     "side":       ["a side view of a {g} on a mannequin", "a {g} photographed from the side"],
     "size_chart": ["a size chart table with garment measurements", "a measurement guide diagram"],
     "detail":     ["a close-up photo of fabric texture", "a macro photo of stitching on fabric"],
     "label":      ["a photo of a clothing care label", "a close-up of a brand tag"],
     "lifestyle":  ["a lifestyle photo of a person outdoors", "a fashion editorial photo"],
   }
   ```

3. **Encode text once.** Today the processor encodes all prompts again for every image. Compute class embeddings once at init and cache them; batch all images in one forward pass.
4. **Add a second label: presentation** — `flat_lay`, `ghost_mannequin`, `on_model`. Prefer flat-lay for segmentation and measurement (a body distorts the silhouette). This label also decides whether skin removal (B1) runs.
5. **Decide across the whole image set**, not per image: pick front = argmax over images of `(score_front − score_back)`, back = argmax of the reverse, with the constraint that they're different images.
6. **`CONFIDENCE_FLOOR` is never checked in `classify_image`**, although the comment says it is. Either apply it or delete it. Calibrate both thresholds on a small labelled set and report a confusion matrix.
7. **Stronger model:** SigLIP (sigmoid, per-class independent scores, so an "irrelevant" threshold is meaningful) or CLIP ViT-L/14. A fashion-tuned SigLIP variant is also worth a test (check its licence).
8. **Use the back image.** The router already finds `best_back`, but the pipeline drops it and `texture_projection.py:107-109` fills the back panel with a flat median colour.

### 4.2 SAM 2 prompting (`segmentation.py:224-228, 191`)

Current: Pass 1 = one centre foreground point + 4 corner background points; Pass 2 (if area is out of 5–95%) = 3×3 grid of foreground points.

Problems:

- **A single point is ambiguous.** SAM returns several candidate masks (sub-part / part / whole), and the code picks the one with the highest predicted IoU (`best_idx = scores.argmax()`), which doesn't prefer the whole garment. A centre point on a chest print can return just the print. A print bigger than 5% of the frame passes the area check. *(SAM 2 wasn't run in this review, so treat this as a risk to test on real photos, not a confirmed bug.)*
- **Corner negatives assume the background reaches the corners** — false for tight crops (and see B5).
- For on-model photos, a centre point may return the person instead of the shirt.

Fixes:

1. **Box prompt.** Get a box from GroundingDINO with the text prompt `"t-shirt."`, or from the fallback model's mask bounding box, and pass `box + centre point` to SAM 2.
2. With multiple points or a box, request a **single mask** (`multimask_output=False`). If keeping multimask, pick the largest candidate that doesn't touch most of the border, not the highest-IoU one.
3. **On-model photos:** use a clothes-parsing model's `upper-clothes` mask directly (this also solves B1).
4. **Fallback model:** the code uses `u2net`, but `.claude/architecture/step_2_ingestion.md` says RMBG-1.4 + GrabCut — docs and code disagree. BiRefNet (MIT licence) is a stronger fallback than U²-Net. RMBG-2.0 is good but has a non-commercial licence.

---

## 5. Other CV fixes

### 5.1 Colour extraction
- Fix B1–B3 (above).
- Optional white balance (gray-world on background pixels) before clustering.
- Report colour accuracy as **ΔE2000** against a ground-truth swatch (e.g. the hex from the product listing).

### 5.2 Design extraction (B4 and false positives)
- **Remove shading first:** divide the grey image by a heavily blurred copy of itself (Retinex-style) so folds and wrinkles stop looking like prints.
- **Fix the FFT test:** compute on an inner patch of the eroded garment mask (no silhouette edge), apply a Hann window, compare peaks to the **radially averaged** spectrum (not the global mean), and require ≥2 symmetric peaks. Autocorrelation is an alternative.
- **Variance check (`:280`)** uses the **max** local variance inside a contour, so one wrinkle pixel passes. Use a percentile (e.g. 75th) or the mean.
- **Ignore a band near the garment outline and seams** — the mask boundary itself creates strong edges and huge local variance.
- Learned alternative: GroundingDINO / SAM 2 inside the garment crop with prompts like `"logo. text. graphic print."`, then CLIP to label each region "printed graphic" vs "plain fabric".

### 5.3 Texture projection (`texture_projection.py`)
- The current warp maps the garment **bounding box** to the panel bounding box, so the silhouette is stretched. Sleeves are taken from the left/right 35% of the box (`ARM_FRAC`), which includes torso.
- Replace with a **landmark-based thin-plate-spline (or piecewise-affine) warp**: detected photo landmarks (neck points, shoulder points, armpits, hem corners, cuffs) → the same landmarks on each panel. `clo_block` already knows exact panel landmark coordinates.
- Use the back photo for the back panel.
- De-light the texture (same Retinex step) so shading isn't baked in and then shaded again by CLO.

### 5.4 Engineering
- Models are loaded fresh on every run (`GarmentSegmentor()` and `GarmentRouter()` are instantiated per call). Fine for CLI; cache them for the worker/service.
- The photo is opened from disk multiple times in segmentation; pass the array through.

---

## 6. Proposed CV course contribution: image-driven garment measurement

**Close the loop:** flat-lay photo → garment landmarks → measurements in cm → `CloBlockMeasurements` → panels.

```
photo ─► view + presentation (CLIP/SigLIP) ─► segmentation (SAM 2, box-prompted)
      ─► landmark detection ─► metric scale (ArUco / size-chart anchor)
      ─► measurements (chest, length, shoulder, neck, sleeve, bicep, hem, wrist)
      ─► garment_to_clo_block() ─► DXF/SVG panels ─► TPS texture warp
```

### 6.1 Landmarks
- **Classical baseline:** from the mask contour — armpits as convexity-defect points, shoulders and neck points from contour curvature, hem corners as the lowest extreme points.
- **Learned model:** HRNet trained on DeepFashion2's short-sleeve-top landmarks (25 points for that category).
- Compare the two in the report.

### 6.2 Metric scale
- **Flat-lay with a marker:** an ArUco/ChArUco marker in frame → homography to remove perspective → exact px-per-cm.
- **Catalogue images without a marker:** predict **ratios** (hem/chest, wrist/bicep, length/chest, …) and scale by one known value from the size chart. This alone replaces the two hard-coded CLO ratios with per-garment values.

### 6.3 Ground truth is already in the repo
The sizes collection in MongoDB stores the real measurements for each cloth/size, so measurement error can be computed for every ingested garment without extra labelling.

### 6.4 Evaluation plan (metrics from P2 where possible)

| What | Metric | Data |
|---|---|---|
| Measurements | MAE in cm per measurement; % within ±1 cm | Sizes DB ground truth |
| Panels | **Panel IoU** (rasterized) and **Panel L2** (P2) vs CLO reference | `clo_block/validate_against_reference.py` |
| Segmentation | mIoU, boundary F-score | ~50 hand-labelled photos (CVAT) |
| View selection | Accuracy + confusion matrix | Same photo set |
| Colour | ΔE2000 | Product-listing hex / swatch |
| Design detection | Precision / recall of "has print" | Same photo set |

### 6.5 Ablations for the paper
1. Segmentation: U²-Net vs SAM 2 centre-point vs SAM 2 box-prompted vs clothes parser.
2. View selection: single prompt vs prompt ensemble vs SigLIP.
3. Landmarks: classical contour vs HRNet.
4. Scale: marker homography vs size-chart anchor.
5. Panels: fixed CLO ratios vs image-predicted ratios (Panel IoU).

---

## 7. Citations note (journal-only rule)

SAM 2, CLIP, DeepFashion2 and GroundingDINO are **conference/arXiv** papers. Ask the instructor whether models can be cited as tools/software.

Journal references that cover the methods used:

| Topic | Reference |
|---|---|
| Survey (patterns ← body data) | Lyu et al., *Textile Research Journal*, 2026 |
| Survey (DL + sewing patterns) | Luo et al., *IEEE TCSVT*, 2026 |
| Landmarks backbone | Wang et al., "Deep High-Resolution Representation Learning for Visual Recognition", *IEEE TPAMI*, 2021 (HRNet) |
| Salient segmentation | Qin et al., "U²-Net", *Pattern Recognition*, 2020 |
| Markers / scale | Garrido-Jurado et al., ArUco, *Pattern Recognition*, 2014 |
| Thin-plate spline warp | Bookstein, *IEEE TPAMI*, 1989 |
| Colour difference | Sharma, Wu, Dalal, CIEDE2000, *Color Research & Application*, 2005 |
| Choosing K | Rousseeuw, silhouettes, *J. Computational and Applied Mathematics*, 1987 |
| Shading removal | Land & McCann, Retinex, *J. Optical Society of America*, 1971 |

---

## 8. Suggested order of work

1. **Bug fixes B1–B7** (small; add regression tests in `product_ingestion/tests/` using the synthetic cases from Section 3).
2. **CLIP prompt ensemble + presentation label + cached embeddings**; use the back image.
3. **Box-prompted SAM 2** + real segmentation quality signals.
4. **Shading removal + fixed FFT test** in design extraction.
5. **Landmarks + scale + measurements → `CloBlockMeasurements`** (the CV contribution).
6. **TPS texture warp** using the landmarks from step 5.
7. **Labelled set + evaluation + ablations** → paper.

---

## Appendix — reproduction scripts

Run against `product_ingestion/` (with `opencv-python-headless`, `scikit-learn`, `numpy`).

```python
import sys, warnings, numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, "product_ingestion")
from segmentation import GarmentSegmentor
from colour_extraction import extract_colours
from design_extraction import extract_design

H = W = 400
def shirt(rgb, shade=False):
    img = np.zeros((H, W, 4), np.uint8)
    img[80:320, 100:300, :3] = rgb; img[80:320, 100:300, 3] = 255
    if shade:
        img[80:320, 100:160, :3] = (np.array(rgb) * 0.8).astype(np.uint8)
    return img

# B6/B7: quality metrics on a perfect mask
m = np.zeros((H, W), np.uint8); m[80:320, 100:300] = 255
print(GarmentSegmentor._compute_quality(m)[1])          # hole_count=1, edge_sharpness=1.0

# B5: corner-touching mask
m2 = np.zeros((H, W), np.uint8); m2[0:300, 0:300] = 255
print((GarmentSegmentor._clean_mask(m2) > 0).mean())   # 1.0 instead of 0.5625

# B2: white tee -> grey
print(extract_colours(shirt((245, 245, 245), shade=True))[0].base_colour_hex)   # #c4c4c4

# B2: black tee + small red print -> red
b = shirt((20, 20, 22)); b[150:200, 170:230, :3] = (220, 30, 30)
print(extract_colours(b)[0].base_colour_hex)            # #dc1e1e

# B1: warm-coloured tees -> all pixels removed as "skin"
for rgb in [(210, 180, 140), (240, 128, 110), (230, 150, 170), (120, 80, 50)]:
    print(extract_colours(shirt(rgb))[0].message)

# B4: plain tee with two folds -> "pattern", 100% coverage
p = shirt((150, 150, 150)).astype(np.float32)
yy, xx = np.mgrid[0:H, 0:W]
fold = 1 - 0.25*np.exp(-((xx-180)**2)/72) - 0.2*np.exp(-((yy-0.6*xx-60)**2)/50)
p[..., :3] *= fold[..., None]
print(extract_design(p.clip(0, 255).astype(np.uint8)).message)
```
