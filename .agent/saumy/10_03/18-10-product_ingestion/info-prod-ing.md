# Product Ingestion: how it works, step by step

*Status: current, written from the code and the output folders (not from older docs)*
*Written: 2026-10-18*

---

## 1. What this part of Mirra does

Product ingestion takes **one photo of a T-shirt** and **one size from MongoDB** and produces:

- a flat **sewing pattern** (four pieces: front, back, left sleeve, right sleeve) as DXF files,
- the **colour** of the shirt,
- the **print or logo** on it,
- a **texture image** for each piece.

Step 3 of Mirra (virtual try-on, `clo_vto`) then takes these pieces, sews them around an avatar and simulates the cloth.

### Two inputs that never mix until step 5

| Input | Where it comes from | What it decides |
|---|---|---|
| The photo | `input/<cloth_id>/` | colour, print, texture |
| The size | MongoDB `sizes` collection, chosen by `size_id` | every dimension of the pattern |

The photo **never** changes the shape of a panel. The shape comes only from the size row.

---

## 2. The files in run order

```
product_ingestion/
  run_product_ingestion.py              entry point, calls the steps below in order

  step_01_0_view_selection.py           1.0  pick the primary image
  step_01_1_garment_router.py           1.1    CLIP front/back/side scoring (used by 1.0)

  step_02_0_segmentation.py             2.0  cut the shirt out of the photo
  step_03_0_colour_extraction.py        3.0  find the shirt colour
  step_04_0_design_extraction.py        4.0  find the logo / print

  step_05_0_panel_generation_clo.py     5.0  build the sewing pattern, write the two JSONs
  clo_block/
    step_05_1_clo_draft_config.py       5.1    measurements and shape settings
    step_05_2_clo_draft.py              5.2    builds the four pieces
    step_05_3_clo_dxf_writer.py         5.3    writes the DXF files
  step_05_4_panel_export_svg.py         5.4    SVG previews

  step_06_0_texture_projection.py       6.0  panel texture images

  garment_measurements.py               shared: the size numbers (T-shirt fields)
  curve_segment.py                      shared: curve and panel geometry types
  run_manifest.py                       shared: run-folder naming
  tests/                                unit tests, plus manual_segmentation_check.py
  legacy/                               old code, not used by the pipeline
```

How to read the numbers: **1.0** is the main file of step 1, **1.1** is a helper that 1.0 uses. The file name writes `1.1` as `_1_` because Python names cannot contain dots.

### The shared files

| File | What it is | Used by |
|---|---|---|
| `garment_measurements.py` | One dataclass, `GarmentMeasurements`, holding a T-shirt's flat dimensions in cm. `from_sizes_db(size_id)` loads one size from MongoDB. | the runner, step 5.0, two test files |
| `curve_segment.py` | The geometry building blocks: `CubicBezierSegment` (one curve), `PieceEdge` (one named edge), `PieceLayout` (a whole panel). | 5.0, 5.2, 5.4, 6.0 |
| `run_manifest.py` | Names and numbers the run folders and finds the latest run. | the runner, plus `clo_vto`, `utils/prune_output.py` and `worker/tasks.py` outside this folder |

---

## 3. What the runner does

`run_product_ingestion.py`:

1. Picks a `cloth_id` (the folder `input/c_00X/`) and a `size_id`, from command-line flags or by asking.
2. Checks that this cloth is offered in that size (the `cloths` collection lists its `size_ids`).
3. Creates the next run folder, `output/<cloth>/<size>/<NNN>/`. The flat id such as `c_001-s_001-001` is written only inside `run_summary.json`.
4. Runs steps `[1/6]` to `[6/6]`.
5. Writes `run_summary.json`.

### What a run leaves behind

```
output/c_001/s_001/001/
  image_info/
    base_garment.png                step 2
    base_garment_feathered.png      step 2
    segmentation_quality.json       step 2
    colors.json                     step 3
    graphic_diffuse.png             step 4
    extraction_metadata.json        steps 1-4 summary
  panels/
    dxf/  svg/                      step 5
    edge_manifest.json              step 5
    panel_metadata.json             step 5
    textures/                       step 6
  run_summary.json
```

The folders named like `c_001-s_001-001` directly under `output/` are older runs from before the nested layout.

---

## 4. Step 1: choose the image (1.0 and 1.1)

**Goal:** a cloth folder can hold several photos. Pick the one that shows the front of the shirt.

### What CLIP is

CLIP is an OpenAI model that turns an image and a sentence into numbers in the same "space". The closer the two, the better the sentence describes the image. "Zero-shot" means we never trained it on shirts. We simply give it four sentences and see which fits best:

| Label | Sentence |
|---|---|
| front | "a photo of the front of a t-shirt" |
| back | "a photo of the back of a t-shirt" |
| side | "a photo of the side of a t-shirt" |
| irrelevant | "a photo that is not of a t-shirt garment" |

The four scores add up to 1. If "irrelevant" is above 0.35 the image is discarded. `ViT-B/32` is the small version of the model.

### How the two files split the work

- `step_01_1_garment_router.py` (1.1) runs CLIP on every image and returns scores.
- `step_01_0_view_selection.py` (1.0) calls it, then picks the image with the best "front" label. If none is labelled front, it takes the one with the highest front score.

The two files **overlap** a little. 1.0 copies the router's scores into a nearly identical `ViewLabel` object, and it picks "best front" again itself instead of using the router's own `best_front`. The router's file-copying feature and command-line mode are not used by the pipeline.

### Known problem: CLIP has never worked in this pipeline

Every run in `output/` records `clip_unavailable_fallback_first_image`, meaning the first image was used. The cause, found by running the router directly:

- The CLIP model's `.bin` weights cannot be loaded with the installed `torch`. Recent `transformers` versions refuse `torch.load` on torch older than 2.6 (a security check, CVE-2025-32434).
- The error is **swallowed** by `except Exception` in 1.0, so nothing visible says why.
- Fixes that were considered:
  - **Upgrade torch to 2.6 or later.** This is the official fix, but it is **ruled out for now**: upgrading would break other dependencies in the environment.
  - **Load safetensors weights.** For `openai/clip-vit-base-patch32` they appear to exist only in an unmerged pull request on the Hub (the main branch has only `pytorch_model.bin`), so this needs a pinned revision. Not yet verified.
  - **Use a different image-text model** that ships safetensors (for example SigLIP 2). Not yet tested here.
  - Whatever is chosen, stop swallowing the exception so the real reason is logged.

All current inputs have only one image per cloth, so this has not hurt results yet. It matters as soon as a cloth has more than one photo.

---

## 5. Step 2: cut the shirt out (2.0)

**Goal:** remove the background, the person and everything else so only the shirt is left.

### How

1. **SAM 2** (`facebook/sam2-hiera-large`) is given hints: one "this is shirt" point at the centre and four "this is background" points at the corners. It returns a mask.
2. If the mask covers less than 5% or more than 95% of the photo, it tries again with a 3×3 grid of "shirt" points over the middle 60%.
3. If SAM 2 still fails, **U²-Net** (via `rembg`) is tried.
4. The mask is cleaned: small noise removed, only the largest connected piece kept, holes filled.

### The two image files

| File | What it is |
|---|---|
| `base_garment.png` | The photo with a hard mask: each pixel is fully visible (255) or fully hidden (0). |
| `base_garment_feathered.png` | The same photo, but the edge fades out softly. |

Checked on real files: the colour values are **identical**, only the transparency differs. In the feathered version, inside the mask stays fully opaque and the fade is added only **outside** the edge (about 6 pixels, blur size 13). So the outline is slightly bigger, and those fade pixels keep the original background colours. Step 6 uses the feathered version.

### The quality score (`segmentation_quality.json`)

| Field | Meaning |
|---|---|
| `area_percent` | How much of the photo the mask covers. |
| `coverage_score` | 1.0 if coverage is 10-80%, lower outside that. |
| `edge_sharpness_score` | How sharp the mask edge is. |
| `hole_count` / `hole_penalty` | Count of enclosed holes. |
| `quality_score` | 0.5 × coverage + 0.3 × sharpness + 0.2 × (1 − hole penalty). |

**Known problem:** only `coverage_score` ever changes. Across all seven quality files in `output/`:

- `edge_sharpness_score` is always 1.0 (a hard black-and-white mask always has the sharpest possible edge),
- `hole_count` is always 1 (by my reading of the code, the outside background is counted as a "hole").

The score is also **never used**. Nothing stops the run if it is low. Example: `c_002` has 89% coverage and scores 0.67, `c_003` scores 0.82, the rest 0.98.

### Known problem: `_fill_holes` adds background and arms to the mask (not fixed yet)

*Status: found 2026-10-18, verified by experiment, **not fixed** (waiting for instructions)*

The mask that leaves step 2 is **not** SAM 2's mask. After SAM 2 picks the shirt, `_clean_mask` ends with `_fill_holes`, which fills every background region that is **not connected to the top-left pixel** of the image.

On a tight crop, background regions that are cut off by the image border (the gap beside an arm, the neck opening, parts of the background) are not connected to that corner. They look like "holes", so they are filled and become part of the garment.

I traced the mask size through each cleanup stage for three cloths:

| Cloth | SAM 2 raw mask | after open/close | after largest piece | **after `_fill_holes`** |
|---|---|---|---|---|
| `c_001` | 57.9% | 57.8% | 57.8% | 57.8% (no effect: background reaches the corner) |
| `c_002` | 65.2% | 65.5% | 65.5% | **89.4%** |
| `c_003` | 66.5% | 66.5% | 66.5% | **84.8%** |

What this does downstream:

- **Wrong colour.** `c_003` is a colour-block T-shirt (white upper half with a stripe band and script text, dark-teal lower half) worn on a person. Its stored base colour is `#182c2a`, a darker teal than the fabric: the white half is skipped by the near-white rule, and the mask also took in arm and background pixels. *(Corrected 2026-11-20: this line earlier called c_003 a red and pink T-shirt.)*
- **Design detection and textures** also use the enlarged mask.
- **The quality score cannot see it.** `c_003` scores 0.82 and `c_002` 0.67, because only the coverage term ever changes.
- The stored outputs were produced by the same code. I re-ran segmentation for `c_002` and `c_003` and got the identical areas (89.43% and 84.77%).
- The shirt-only mask SAM 2 actually picked is correct on all three images; the prompt is not the problem.

Proposed fix (not applied): pad the mask with a 1-pixel background border before the flood fill, so every background region touching an image edge is connected to the corner, and only truly enclosed holes can be filled. A second safeguard would be to fill only holes smaller than about 2% of the garment area.

Evidence: `images/c_003_fillholes_added.png` (the added region in blue) and `images/c_003_sam2_raw_best.png` (SAM 2's own pick). Full write-up: `03-sam2-prompting.md`.

---

## 6. Step 3: find the colour (3.0)

**Goal:** a hex colour code for the shirt fabric.

### How, in order

1. Take the visible pixels (alpha above 10).
2. Remove skin-coloured pixels (a colour range in HSV), in case arms or neck got into the mask.
3. Randomly sample up to 50,000 pixels.
4. Convert to **LAB** colour space. This is a colour space where "how different two colours look" matches the distance between numbers, which makes clustering more natural than in RGB.
5. Try K-Means with 2 to 8 clusters and keep the one with the best **silhouette score** (a measure of how well separated the clusters are). It is computed on a 5,000-pixel sample.
6. Run K-Means with that K and build a palette, one entry per cluster.
7. Sort clusters by size and choose the **largest one that is not near-white or near-black** (lightness L below 15 or above 85) as the base colour.

### `colors.json`

Current layout (checked on every run):

```
base_colour_hex       "#27283b"
clo3d_base_hex        "#27283B"          same colour, upper-case for CLO
k_used                2
skin_pixels_removed   0
palette               list; each entry has rgb, lab, hex, clo3d_hex, percentage
```

The older flat runs have an older layout: only `base_colour_hex` and a five-colour palette. For `c_001` that older base was `#90756b`, a brownish colour, versus navy `#27283b` now. I have not worked out whether the image or the code caused that. The same palette is repeated inside `extraction_metadata.json`.

### Do we extract only one colour?

We extract a **palette**, but only **one colour is used**. `clo_vto/native_vto/step_08_apply_fabric.py` reads `base_colour_hex` (and falls back to `palette[0]` if it is missing). The print colours are not stored as hex codes: they stay as pixels inside `graphic_diffuse.png`. On all five current cloths the best K is 2 (shirt colour plus print or other).

### Possible weakness (from reading the code, not yet seen in a run)

A **black** shirt with a **coloured** logo: the black cluster is skipped as "near-black", so the logo colour could become the base colour. The navy `c_001` has L = 16.75, only just above the cutoff of 15.

---

## 7. Step 4: find the logo or print (4.0)

**Goal:** cut out the graphic on the shirt as its own image.

### How

1. Convert to grey and blur slightly.
2. **Canny edge detection** (explained below).
3. Close small gaps so broken edges join into regions.
4. Find the outlines (contours) of those regions. Keep only regions that cover 1-80% of the shirt and contain enough local contrast.
5. Run the **FFT check** (explained below). If it finds a repeating pattern but there are few contours, the whole shirt counts as a pattern.
6. Merge all kept regions, crop their bounding box and use the filled regions as the transparency.
7. Label the result: `pattern`, `text` (very many edges per area), or `logo`.

### What Canny is

Canny finds edges, the places where brightness changes sharply. Roughly: blur the image, measure how fast brightness changes at each pixel, keep the strong changes, and also keep weaker changes that are connected to strong ones. It needs two thresholds, "strong" and "weak". We set them from the image's own median brightness (0.67× and 1.33×), so dark and bright shirts both work.

### What the FFT check is

An FFT (Fourier transform) describes an image as a mix of repeating waves instead of pixels. A pattern that repeats (polka dots, stripes) produces one very strong wave. Plain fabric does not. We compare the strongest wave to the average; if it is more than 8× bigger, we call it a repeating pattern. This catches all-over prints that edge detection misses, because their many tiny edges are each too small to keep.

### Output: `graphic_diffuse.png`

- Design found: a **cropped** image of just the graphic. Its transparency comes from the filled edge regions, so it can include shirt-coloured pixels between edges. This is why the BOSTON crop looked rough and incomplete.
- No design: an **empty transparent image** the size of the whole photo.

---

## 8. Step 5: build the sewing pattern (5.0 to 5.4)

**Goal:** four flat pieces with the exact dimensions of the chosen size, ready for CLO.

### The flow in `step_05_0_panel_generation_clo.py`

1. Convert the size row (cm) into the block's measurements (mm). `half_chest_width` is the full flat width of one body panel despite its name, so the half-width in mm is `value × 10 / 2`.
2. Derive two values the sizes collection does not store: hem width = 0.93 × chest, wrist width = 0.78 × bicep. (A size document may supply `hem_width_cm` and `wrist_width_cm` to override this.)
3. **5.1** holds the measurements and the shape settings (curve control points, ease, notch distances).
4. **5.2** builds the pieces from Bezier curves. The sleeve cap height is *solved* so that the cap is slightly **shorter** than the armhole it sews into (about 2% negative ease), which is correct for a stretch jersey tee. Notches, internal lines and grainlines are added.
5. **5.3** writes the four DXF files.
6. **5.4** writes SVG previews (a picture of each piece).
7. 5.0 itself writes `panel_metadata.json` and `edge_manifest.json`.

### Units: cm, mm and the 0.1

| Where | Unit |
|---|---|
| Sizes in MongoDB | cm |
| The block and the DXF files | mm |
| CLO's scene | cm |
| Texture and SVG | cm (a scaled copy of the layouts) |

DXF is in mm because CLO's own export is mm and the fitted constants are in mm. CLO's scene is in cm, so `clo_vto` imports the DXF with scale **0.1** (1 mm = 0.1 cm). `clo_vto` picks 0.1 when the file says "mm". If the units cannot be read, it assumes mm and warns, unless strict mode is on, in which case it stops. Our DXFs declare their units; CLO's reference files do not.

### What `clo_block` is

`clo_block/` is the pattern engine. It was **reverse-engineered from CLO's own default T-shirt**, exported as DXF at size M. It reproduces that drafting logic for any measurements. Its checks against CLO's reference (`validate_against_reference.py`) pass 57 of 57 when given CLO's size M measurements; the largest error is 0.57 mm. `clo_default_ground_truth.json` holds the numbers measured from CLO's DXFs (lengths, ratios, curve fits).

### The edges: front and back have 10, sleeves have 5

An "edge" is one side of a piece's outline, from one corner to the next.

**Front and back (10 each).** The outline is walked as hem, side, armhole, shoulder, neckline, then back down the other half. The hem and neckline are each split in two at the centre, which is how CLO indexes them. The old generator had 8 edges.

| Index | Front | Back |
|---|---|---|
| 0 | right_neckline | left_hem |
| 1 | right_shoulder | left_side |
| 2 | right_armhole | left_armhole (two curves) |
| 3 | right_side | left_shoulder |
| 4 | right_hem | left_neckline |
| 5 | left_hem | right_neckline |
| 6 | left_side | right_shoulder |
| 7 | left_armhole | right_armhole (two curves) |
| 8 | left_shoulder | right_side |
| 9 | left_neckline | right_hem |

**Sleeve (5).** Careful: the names in `edge_manifest.json` do not describe what the edges physically are. By measured length (size M):

| Index | Name in the manifest | What it really is | Length |
|---|---|---|---|
| 0 | cuff | short side edge | 138 mm |
| 1 | right_underarm | curved cap, one half | 284 mm |
| 2 | cap_front | curved cap, other half | 267 mm |
| 3 | cap_back | short side edge | 135 mm |
| 4 | left_underarm | the wrist opening | 385 mm |

`clo_vto/native_vto/seams.py` has a comment that acknowledges this. Seams are wired by **index**, not by name, so it works, but the names are misleading.

### Is this how the industry does it?

*(General knowledge, not checked against specific products.)*

- The overall idea is the same as CAD pattern software: start from a **block** (a basic pattern), drive it with a **measurement chart**, export **DXF** (the AAMA/ASTM pattern format).
- Differences: ours is reverse-engineered from **one** CLO size and scaled with fixed ratios, while professional tools use real **grading rules** per size. The photo contributes nothing to shape.

### Our DXFs compared with CLO's

`clo_default_ground_truth.json` is a summary of numbers, not a DXF, so it is not the same kind of file. Compared with CLO's real DXFs, for `c_001` with size `s_001`:

| | CLO reference (size M) | Our output |
|---|---|---|
| Front panel size | 580 × 719 mm | 520 × 710 mm |
| Sleeve size | 490 × 245 mm | 436 × 316 mm |
| Placement | at CLO world coordinates | centred at the origin |
| Extra layers | vertex index labels, seam-allowance layers 84/85/87, layer 14 | none |
| Internal lines (front) | 8 | 4 |
| Vertices (front / back) | 112 / 82 | 98 / 144 |
| Notch points | 4 front, 8 back | 2 front, 4 back (why is not yet understood) |

The size differences come from the **data**, not the code. The seeded size `s_001` is smaller than CLO's M, and its sleeve length (21 cm) is much longer than CLO M's underarm-to-wrist.

---

## 9. Step 6: paint the pieces (6.0)

**Goal:** a texture image for each piece, so CLO can show the real colour and print.

How it works:

1. Pieces are drawn at 10 pixels per cm.
2. **Logo or text design:** every piece is filled with one solid colour (the median fabric colour). The graphic is then pasted on the front chest, 30% of the panel width wide and 35% down from the top.
3. **Pattern or no design:** the front gets the whole shirt photo stretched into the panel shape (a four-corner warp from the shirt's bounding box). Sleeves get the left or right 35% of the photo.
4. The **back is always solid colour**, because there is no back photo.

Output: `panels/textures/<piece>_texture.png` and `texture_projection_metadata.json`.

---

## 10. Is `garment_measurements` the size of all garments?

No. It holds the size of **whichever garment you pass in**, and only for T-shirts.

- The numbers live in the `sizes` collection (10 seeded sizes, `s_001` to `s_010`, fits slim, regular, relaxed, oversized).
- A cloth lists the sizes it is offered in (`size_ids`); a size does not name a cloth. Several cloths can share a size chart. Right now all five seeded cloths share the same list.
- The fields (armhole depth, bicep width, neck depths, sleeve length) describe a short-sleeve top. A jacket or pants would need different fields and a different builder. The `cloths` collection allows categories like `bottom` and `outerwear`, but only a T-shirt can be built today.

---

## 11. Problems found (summary)

| # | Problem | Where | Effect |
|---|---|---|---|
| 1 | CLIP never loads (torch older than 2.6, error hidden) | 1.0, 1.1 | always uses the first image |
| 2 | Quality score never gates anything; only coverage varies | 2.0 | bad segmentation continues silently |
| 3 | Feathered edge keeps background colour in a ~6 px halo | 2.0, 6.0 | possible colour bleed at edges |
| 4 | A black shirt with a coloured logo may get the logo colour as base | 3.0 | wrong base colour (from code reading) |
| 5 | Design crop includes shirt-coloured pixels and is pasted at a fixed size (30% width) | 4.0, 6.0 | rough, shrunken graphic |
| 6 | Back and sleeves never use the photo | 6.0 | solid colour only |
| 7 | Sleeve edge names do not match the real edges | 5.2, manifest | confusing; wiring works by index |
| 8 | Seeded sizes differ from CLO M, so our DXFs look different from the reference | sizes data | not a code bug |
| 9 | **`_fill_holes` adds background and arms to the mask on tight crops** (not fixed yet) | 2.0 | wrong mask, wrong colour (`c_003`, a white and dark-teal tee, stored base `#182c2a`); see section 5 |
| 10 | The CLO "graphic" call is a base-texture replacement, all four pieces share fabric 0, and `step_08` reads the wrong key for `design_type` | `step_08`, CLO plugin | logo and per-piece textures never reach CLO correctly; see `02-graphic-overlay-finding.md` |
