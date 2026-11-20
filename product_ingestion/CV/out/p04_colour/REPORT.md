# P04 report: colour extraction fixes and multi-colour palettes

*Status: first pass complete. Date: 2026-11-20.*
*Written by the P04 sub-agent and saved here by the orchestrator (sub-agents cannot write report files). Every number comes from the agent's own runs; product_ingestion tests: 35 passed, 16 subtests passed.*

## 1. Goal
- Fix bugs B1, B2 and B3 in `step_03_0_colour_extraction.py`.
- Never reduce a shirt to one colour: output a palette (each colour's share and role, fabric or print) plus a colour region map. `base_colour_hex` is kept only as a compatibility field (the largest fabric colour).
- Compare clustering methods, skin handling and enhancement, and make the best the default.

## 2. Bugs reproduced and fixed
Command: `p04_synthetic_bugs.py`. Results: `out/p04_colour/synthetic/run_01/`.

| Case | v0 (before) | v1 (after) |
|---|---|---|
| B1 tan (210,180,140) | fails: "All pixels were filtered as skin" | `#d2b48c` 100 %, ΔE 0 |
| B1 coral | fails, same message | `#f0806e`, ΔE 0 |
| B1 pink | fails, same message | `#e696aa`, ΔE 0 |
| B1 brown (120,80,50) | 26,917 pixels removed, base ΔE 3.39 | 0 removed, ΔE 0 |
| B1 navy tee with white print and skin-coloured arms in the mask | 4,200 removed | 4,200 skin pixels removed; 92 % navy fabric + 8 % white print |
| B2 white tee with 12 % shadow | base `#c3c3c3` (ΔE 10.3) | base `#f0f0ef` (ΔE 0.54) |
| B2 black tee with 7 % red print | base red (ΔE 39.3) | base black, plus 5.6 % red print |
| B2 colour block, white over teal | base = the dark block | both blocks found as fabric (52 % and 48 %) |
| B3 flat single colour | crash: `ValueError: cannot convert float NaN to integer` | `#6496c8` 100 %, ΔE 0 |
| B3 flat two colours | base off by ΔE 68 | both colours found, ΔE 0 |

**How each bug was fixed:**
- **B1 (skin):** skin is taken from parser labels (`skin_mask=`) or from a guarded YCrCb skin model.
  - If skin-coloured pixels are more than 35 % of the garment, nothing is removed, because the fabric itself is skin-coloured.
  - Only blobs of at least 0.3 % are removed, and the whole garment is never deleted.
- **B2 (base colour):** the base colour is the largest fabric colour after merging clusters within ΔE2000 5. Near-white and near-black colours are no longer skipped.
- **B3 (flat colours):** flat colours are detected before clustering, K is capped at the number of distinct colours, and empty clusters are dropped.
- **Remaining case:** the shadow on a white tee is still listed as a second fabric colour. The option `shade_dl=20` merges it, but it is off by default because it could hide a light print.

## 3. Code
`product_ingestion/step_03_0_colour_extraction.py`:
- **Unchanged:** the v0 code.
- **New function:** `extract_palette_v1(rgba, skin_mask=None, **opts)`. `V1_DEFAULT` = mean-shift, skin "auto", merge ΔE 5, minimum share 2 %, 20,000-pixel subsample, seed 42.
- **New fields:**
  - `ColorInfo.role`;
  - `ColourResult.palette_roles`, `fabric_colours`, `region_map` (small JSON) and `label_map` (H×W array, -1 = not garment; not for JSON);
  - `method`, and `extra_json()`.
- **Main entry point:** `extract_colours(rgba, method="v1", **options) -> (ColourResult, bool)`. `method="v0"` gives the old pipeline.
- **Options:** `skin` (none / hsv / ycrcb / auto / mask), `merge_de`, `shade_dl`, `wb` (greyworld / prepare), `clahe`, `ms_bandwidth`, `min_share`, `clean_k`.
- **Runner:** it should merge `colour_result.extra_json()` into colors.json (orchestrator task).

**Roles and the region map:**
- The largest colour is fabric. Another colour is also fabric when its biggest region is at least 8 % of the garment and at least 0.08 of its edge touches the garment outline (a colour block). Everything else is print.
- Every garment pixel is labelled with its palette colour, then smoothed with a 3×3 majority filter.
- Saved per photo: `region_map.png` and `regions.json`.

Scripts: `p04_synthetic_bugs.py`, `p04_build_fpi_subset.py`, `p04_parser_cache.py` (SegFormer under `gpu_lock`), `p04_run_methods.py`, `p04_fpi_eval.py`, `p04_make_figures.py`.

## 4. Methods compared
**Clustering:**
- K-means (silhouette K 2-8, as v0);
- K-medoids (own alternating PAM on 1,500 pixels);
- GMM (full covariance, K 1-8 by BIC);
- mean-shift (bandwidth 10 in Lab).

Each is followed by ΔE2000 merging at 5. A merge ablation turns merging off.

**Skin handling:** none, v0 HSV, YCrCb, guarded "auto", SegFormer labels.

**Enhancement:** grey-world, CLAHE, `cv_enhance.prepare_for_colour` (P03).

**Commands:**
- Mirra photos: `p04_run_methods.py --masks oracle v0 --eval`, writing to `methods/`. Their roles used an older edge threshold, so the palettes are valid but the roles are not.
- Final default: `p04_run_methods.py ... --tag methods_v2 --label_suffix _v2 --eval`, writing to `methods_v2/`.
- Fashion Product Images: a fixed 800-image subset of T-shirts, tops, shirts and sweatshirts (60×80 px). It was evaluated serially on every third image (266 images): `p04_fpi_eval.py --workers 1 --stride 3`, tags `run_02`, `run_03`, `run_04`.
- Fashion Product masks:
  - `bg`: background connected to the border within ΔE 8, removed;
  - `parsermask`: SegFormer upper-clothes, falling back to `bg`.
- Colour names come from a hand-made table of 32 names, nearest by ΔE2000; "Multi" labels are excluded.

## 5. Results
### Mirra photos, reference (oracle) masks (mean of 5; `figures/mirra_table_oracle.csv`)
| method | palette ΔE | ref share matched | base ΔE | all fabric found ΔE | n colours |
|---|---|---|---|---|---|
| v0 | 2.06 | 0.93 | 1.13 | 1.18 | 2.2 |
| K-means auto | 1.29 | 0.99 | 0.83 | 1.02 | 2.0 |
| K-medoids auto | 1.26 | 0.99 | 0.78 | 0.97 | 2.0 |
| GMM auto | 1.97 | 1.00 | 1.17 | 1.38 | 4.0 |
| GMM, shade merge | 1.66 | 1.00 | 1.03 | 1.23 | 3.2 |
| mean-shift, min share 0.8 % | 1.24 | 1.00 | 0.56 | 0.62 | 4.0 |
| **v1 default (mean-shift, min share 2 %)** | **1.17** | 0.99 | **0.51** | 0.70 | 2.6 |
| K-means, v0 HSV skin | 1.93 | 0.93 | 1.11 | 1.29 | 1.8 |
| K-means, unguarded YCrCb | 2.09 | 0.95 | 1.54 | 1.72 | 2.0 |
| GMM + grey-world | 15.19 | 0.56 | 15.93 | 14.11 | 5.4 |
| GMM + CLAHE | 4.09 | 1.00 | 2.81 | 2.70 | 5.8 |
| GMM + `prepare_for_colour` | 2.06 | 0.99 | 0.99 | 1.16 | 4.6 |
| K-means + `prepare_for_colour` | 1.51 | 0.99 | 1.14 | 1.23 | 2.0 |

### Mirra photos, v0 masks (realistic; `figures/mirra_table_v0.csv`)
| method | palette ΔE | ref share matched | base ΔE | all fabric found ΔE | n colours |
|---|---|---|---|---|---|
| v0 | 5.77 | 0.93 | 1.53 | 1.53 | 2.0 |
| K-means auto | 5.52 | 0.93 | 7.38 | 1.62 | 2.0 |
| GMM auto | 5.31 | 0.95 | 13.93 | 0.89 | 4.4 |
| mean-shift auto | 4.78 | 0.99 | 6.68 | 0.69 | 5.4 |
| **v1 default** | 4.85 | 0.99 | 6.81 | 0.82 | 4.0 |

- **Palette:** quality improves (5.77 → 4.85) and every fabric colour is found.
- **Base colour:** it gets worse (1.53 → 6.81) because the v0 masks leak background: 27 % white on c_002, 41 % grey on c_004, and the person and wall on c_005, where grey becomes the largest colour.
- **Why v0 looked better:** v0 avoided this only by skipping near-white and grey clusters, which is also the cause of bug B2.
- **This is a segmentation problem (P01),** not a colour one.

### Fashion Product Images (266 product photos; `fpi_eval/run_02..04/summary.csv`)
- top1: the base colour's name equals the label.
- any: any palette colour of at least 5 % matches.
- family: close names count as correct (Navy/Blue, Grey/Charcoal, ...).

| method | mask | top1 | top1 family | any | any family | n colours |
|---|---|---|---|---|---|---|
| v0 | bg | 0.207 | 0.327 | 0.357 | 0.496 | 2.4 |
| K-means auto | bg | 0.293 | 0.440 | 0.331 | 0.477 | 2.5 |
| K-medoids auto | bg | 0.293 | 0.444 | 0.320 | 0.481 | 2.5 |
| GMM auto | bg | 0.290 | 0.436 | 0.444 | 0.602 | 6.1 |
| GMM parser skin | bg | 0.320 | 0.477 | 0.462 | 0.613 | 5.5 |
| mean-shift auto | bg | 0.293 | 0.451 | 0.353 | 0.511 | 6.5 |
| **v1 default** | bg | **0.301** | 0.451 | 0.361 | 0.523 | 4.8 |
| v0 | parser | 0.252 | 0.372 | 0.429 | 0.560 | 2.2 |
| GMM | parser | 0.361 | 0.508 | 0.481 | 0.594 | 4.6 |
| **v1 default** | parser | **0.338** | 0.489 | 0.361 | 0.508 | 3.3 |

- **Gain:** top1 improves by 9-10 points over v0 (standard error about 3 points). The differences among the new clusterers are within noise.
- **Bias in "any":** it rewards methods that report many colours (GMM).
- **Why absolute accuracy is low:**
  - `bg` masks include the models wearing the clothes;
  - the photos are tiny (60×80);
  - the name table is ambiguous for dark colours (many "Black" shirts are named Charcoal).

**Timing on the Mirra photos:** v0 1.58 s, K-means 0.84 s, K-medoids 0.51 s, GMM 1.69 s, mean-shift 0.66 s.

## 6. Figures (`out/p04_colour/`)
- `figures/swatches_{oracle,v0}.png`: palette bars per method and photo, with the reference row on top.
- `figures/region_maps_{oracle,v0}.png`: region maps of five clusterers.
- `figures/table_*.png`.
- `figures_v2/*`: the same for the final default.
- **c_003:** white `#dfe1e9` 48 % and dark teal `#1c3533` 52 % come out as two fabric colours, with the stripes as dark lines. c_001's BOSTON is a clean print region.

## 7. What worked and what did not
- **Worked:**
  - Fixing B1, B2 and B3.
  - ΔE2000 merging, which keeps palettes short.
  - Mean-shift: it finds small prints without fixing K, and is fast and deterministic.
  - K-medoids and K-means are good on plain and two-colour shirts.
- **Did not work:**
  - **GMM:** it over-segments shading and JPEG noise into extra colours.
  - **Grey-world (ΔE 15) and CLAHE (4.1):** both are harmful, which agrees with P03.
  - **`prepare_for_colour`:** no gain.
  - **Unguarded YCrCb skin:** worse than no skin removal at all.
  - **Skin handling on leaked masks:** it cannot rescue masks that leak background.

## 8. Issues
- **Memory stop:** the first Fashion Product run (3 worker processes) was stopped by the orchestrator. The re-run is serial on a third of the subset (266 of 800).
- **v0 masks:** they leak background and people, and this dominates the realistic base-colour error.
- **Approximate references:** the Mirra reference palettes are approximate (5 photos); differences below ΔE 1 are not meaningful.
- **White-tee shadow:** still reported as a second fabric colour.
- **Name table:** hand-made, with ambiguous dark colours; `bg` masks include models.
- **Not done:**
  - a palette per panel (needs P19's panel masks);
  - colour fusion across several photos;
  - the runner change to store `extra_json()`.

## 9. Recommendation
- **Default:** use `extract_colours(rgba)` (mean-shift, merge ΔE 5, minimum share 2 %); keep `method="v0"` for before/after comparisons.
- **Photos of people:** pass `skin_mask` from the SegFormer parser (labels 1, 2, 3, 11-15) when it is already running; otherwise use the guarded `skin="auto"`.
- **Judging colour:** use the oracle-mask numbers (palette ΔE 1.17 and base ΔE 0.51, against v0's 2.06 and 1.13). Fix the segmentation (P01) to carry this quality into real use.
- **Regression tests:** add them from the synthetic cases:
  - a flat single colour must not crash;
  - tan, coral, pink and brown tees must not be rejected;
  - a black tee with a red print must keep a black base;
  - a white tee with a shadow must keep a white base.
