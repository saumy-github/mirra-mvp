# P03 report: image enhancement and filtering study

*Status: first pass finished (HED learned-edge model not run). Date: 2026-11-20.*
*Written by the P03 sub-agent; saved here by the orchestrator, because sub-agents cannot write report files. Paths are relative to `out/p03_filters/` unless stated.*

## 1. What was built
- **Module:** `product_ingestion/cv_enhance.py`. It holds every enhancement, restoration, shading-removal, smoothing and edge-detector function, as plain numpy functions with an optional garment mask.
- **Scripts** (`CV/scripts/`): `p03_common.py`, `p03_edge_study.py`, `p03_enhance_study.py`, `p03_sensitivity.py`, `p03_summarize.py`, `p03_figures.py`.
- **Data:** 5 Mirra photos with reference masks and approximate design boxes, plus 50 VITON-HD product photos (first 50 rows of the first parquet, read in small row batches) for the fold-flatness study.
- **Scale:** 13 smoothing settings × 9 detectors × 5 photos = 585 edge maps, all saved. 18 single enhancements and 47 chains were run on 5 photos under 5 conditions (clean plus 4 synthetic degradations).

**Commands** (repo root, `.venv/Scripts/python.exe`):
```
product_ingestion/CV/scripts/p03_edge_study.py              (also: --pre clahe_L_2 | shading_divide | shading_homomorphic | denoise_nlm)
product_ingestion/CV/scripts/p03_sensitivity.py
product_ingestion/CV/scripts/p03_enhance_study.py --viton 50   (about 14 min)
product_ingestion/CV/scripts/p03_summarize.py > product_ingestion/CV/out/p03_filters/summary_tables.md
product_ingestion/CV/scripts/p03_figures.py
```
`p03_edge_study.py` appends to its CSV, so move the old CSV before re-running.

## 2. Methods in `cv_enhance.py`
- **Enhancement:** `hist_equalize` (L or RGB), `clahe` (clip 2 and 4), `gamma_correct` (0.7, 1.5, auto), `grey_world`, `white_patch`, `retinex` (SSR and MSR).
- **Denoising:** median, Gaussian, bilateral (sigma colour 25), non-local means.
- **Shading removal:**
  - `remove_shading_divide`: divide by a heavily blurred luminance copy. `regions=3` estimates the blur separately for each k-means colour region.
  - `remove_shading_homomorphic`: log, FFT, Gaussian high-emphasis filter, inverse FFT.
- **Smoothing:** none, mean, median, Gaussian, bilateral, each at k = 3, 5, 9. The pipeline today uses Gaussian 5.
- **Edge detectors:**
  - Sobel, Prewitt and Scharr: gradient magnitude, then non-maximum suppression and hysteresis.
  - Laplacian, LoG (sigma 1.5) and DoG (sigma 1.0 and 1.6): zero crossings.
  - `canny`: the pipeline's auto-Canny rule.
  - `canny_pyr_and` and `canny_pyr_or`: Canny on a 3-level pyramid. AND keeps a level-0 edge only if a half-size edge lies within 3 px; OR takes the union of all levels.
- **Shared sensitivity rule:** each detector's response is normalised so an ideal step of height A gives A. The high threshold is 0.33 × median grey and the low threshold is half of that, matching the pipeline's auto-Canny in step-size terms.

## 3. Protocol
- **Image size:** photos larger than 768 px (c_001, c_003) were shrunk with INTER_AREA; the others stay at native size.
- **Garment edge excluded:** the background is replaced by the nearest garment pixel before filtering. Edges are counted only inside the garment mask eroded by 1.2 % of the long side (at least 3 px), so the shirt's own outline is not counted.
- **Regions:**
  - D (design): the text, graphic, logo, stripes and pattern boxes inside the eroded mask.
  - F (plain fabric): the eroded mask minus the design boxes, with the boxes grown by the band width.
- **c_003 colour-block boundary:** a real colour edge but not a print edge. The two `colour_block` boxes are not in D, and a strip of 4 band widths around the split line is removed from F.
- **Edge metrics** (edge maps thinned to 1 px; tolerance 0.5 % of the long side):
  - recall = share of D pixels within the tolerance of an edge.
  - precision = recall / (recall + the same share on F).
  - F1 = mean over c_001, c_003, c_004 and c_005.
  - FER (fold false-edge rate) = edge pixels on plain fabric / plain-fabric pixels, in %, mean of the 5 photos. c_002, the plain shirt, is also reported on its own.
- **Colour accuracy:** k-means in Lab on F, matched to the reference fabric palette, share-weighted CIEDE2000. The reference palette was made from the same photos, so on clean photos this measures drift caused by the method, not accuracy. Known degradations test accuracy: colour cast (R ×1.2, B ×0.8), dark (gamma 1.8), noise (sigma 12), and shading (a light ramp plus a dark blob).
- **Flatness:** pooled within-cluster std of L, after / before (lower is flatter). Print contrast kept = std of L in the design boxes, after / before.

## 4. Part A: enhancement (ΔE2000, lower is better; mean of 5 photos)
Files: `enhance_scores.csv`, `summary_enhance.csv`, `summary_enhance_rows.csv`, `summary_chains.csv`, `summary_tables.md`.

| method | clean | cast | dark | noise | shade | mean | flatness ratio | print kept |
|---|---|---|---|---|---|---|---|---|
| denoise_gauss5 | 0.224 | 8.141 | 10.712 | 0.463 | 5.688 | 5.046 | 0.900 | 0.841 |
| denoise_bilateral9 | 0.276 | 8.221 | 10.700 | 0.447 | 5.727 | 5.074 | 0.931 | 0.993 |
| denoise_median5 | 0.265 | 8.329 | 10.726 | 0.408 | 5.689 | 5.084 | 0.886 | 0.875 |
| none | 0.221 | 8.317 | 10.706 | 0.705 | 5.729 | 5.136 | 1.000 | 1.000 |
| denoise_nlm | 0.452 | 7.864 | 10.880 | 0.664 | 5.868 | 5.146 | 0.944 | 1.002 |
| shading_divide_regions | 0.421 | 8.210 | 10.746 | 0.795 | 6.114 | 5.257 | 0.964 | 1.006 |
| clahe_L_2 | 3.972 | 9.466 | 9.517 | 6.528 | 3.475 | 6.592 | 1.716 | 1.125 |
| shading_homomorphic | 2.926 | 9.077 | 11.923 | 3.154 | 6.682 | 6.752 | 1.130 | 1.093 |
| gamma_0.7 | 7.717 | 10.987 | 4.887 | 7.517 | 5.192 | 7.260 | 1.053 | 0.917 |
| white_patch | 7.687 | 10.759 | 10.370 | 6.577 | 8.946 | 8.868 | 1.517 | 1.189 |
| shading_divide | 5.442 | 11.162 | 12.181 | 6.646 | 8.918 | 8.870 | 1.052 | 0.796 |
| gamma_auto | 11.448 | 15.798 | 5.892 | 11.375 | 12.288 | 11.360 | 1.142 | 0.862 |
| hist_eq_L | 11.205 | 14.700 | 16.043 | 11.134 | 11.423 | 12.901 | 5.773 | 1.248 |
| grey_world | 14.606 | 14.103 | 18.764 | 14.390 | 16.058 | 15.584 | 1.254 | 1.098 |
| hist_eq_rgb | 22.095 | 19.899 | 25.385 | 25.227 | 21.815 | 22.884 | 5.735 | 1.124 |
| retinex_ssr | 26.369 | 25.796 | 25.120 | 39.411 | 26.709 | 28.681 | 2.939 | 1.044 |
| retinex_msr | 26.642 | 26.213 | 25.449 | 39.375 | 26.906 | 28.917 | 2.639 | 1.036 |

Run time per image (CPU, longest side at most 768 px):

| method | ms |
|---|---|
| gamma | 2-3 |
| grey_world, white_patch | 13-14 |
| CLAHE | 20 |
| median, Gaussian | 18-22 |
| bilateral 9 | 40 |
| shading_divide | 95 |
| homomorphic | 222 |
| shading_divide_regions | 338 |
| NLM | 803 |

**Best chains:**

| chain | mean ΔE | flatness | print kept | ms |
|---|---|---|---|---|
| bil9 | 5.074 | 0.931 | 0.993 | 37 |
| nlm | 5.146 | 0.944 | 1.002 | 894 |
| nlm+shreg | 5.197 | 0.895 | 1.009 | 1163 |
| bil9+shreg | 5.216 | 0.888 | 0.999 | 377 |

`bil9+shreg` gives ΔE 0.471 on clean photos. Any chain containing grey_world sits near ΔE 15.

**Findings:**
- **Clean photos:** nothing improves colour fidelity. Edge-preserving denoising is neutral (ΔE 0.22-0.28), while global contrast and balance methods move the colour by ΔE 3-27.
- **Colour cast:** no method fixes it (best: NLM 7.86, against 8.32 for doing nothing). Grey-world makes it worse (14.1), because a single-coloured garment breaks its grey-average assumption.
- **Dark exposure:** only gamma 0.7 helps (10.71 → 4.89). This is partly circular, since the degradation itself was a gamma of 1.8.
- **Uneven light:** CLAHE gives the lowest colour distance (3.48 against 5.73) but raises noise (flatness 1.37). Plain `shading_divide` flattens most (0.752) but worsens colour (8.92).
- **Noise:** median 5, bilateral 9 and Gaussian 5 (ΔE 0.41-0.46) beat NLM (0.66) and doing nothing (0.71). Gaussian 5 and median 5 lose print contrast (0.84 and 0.88).
- **Colour blocks:** plain `shading_divide` fails on c_003 (ΔE 24.74), because it treats the block as lighting. The per-region version gives 0.80 and homomorphic filtering 11.85.
- **Seam:** `shading_divide_regions` leaves a visible seam on c_002 under strong synthetic shading (fig3) and barely flattens clean photos (0.973).

**VITON-HD fold flatness** (50 images; `viton_flatness.csv`, `summary_viton.csv`):

| method | std ratio (mean) | colour shift ΔE |
|---|---|---|
| bil9+shdiv | 0.777 | 0.621 |
| shading_divide | 0.826 | 0.510 |
| gw+bil9+shdiv | 0.849 | 8.119 |
| median5 | 0.910 | 0.161 |
| bil9+shreg | 0.913 | 0.342 |
| shading_divide_regions | 0.955 | 0.201 |
| bilateral9 | 0.962 | 0.226 |
| homomorphic | 1.023 | 0.878 |
| grey_world | 1.100 | 8.028 |
| clahe_L_2 | 1.703 | 2.931 |
| retinex_msr | 3.056 | 21.455 |
| hist_eq_L | 8.007 | 23.632 |

## 5. Part B: smoothing filter × edge detector
Files: `edge_scores.csv`, `summary_edges.csv`, `edge_sensitivity.csv`, `edge_scores_pre.csv`.

**Top fold-safe combinations** (c_002 FER ≤ 0.15 % and 5-photo FER ≤ 1.0 %; 63 of 117 qualify):

| combination | recall | precision | F1 | FER 5 photos % | FER c_002 % | ms |
|---|---|---|---|---|---|---|
| **bilateral 9 + laplacian** | 0.595 | 0.967 | **0.734** | 0.646 | 0.059 | 20.8 |
| bilateral 3 + laplacian | 0.599 | 0.953 | 0.732 | 0.975 | 0.146 | 18.1 |
| bilateral 5 + laplacian | 0.590 | 0.964 | 0.729 | 0.692 | 0.103 | 22.8 |
| median 3 + laplacian | 0.595 | 0.942 | 0.727 | 0.901 | 0.112 | 18.3 |
| gaussian 3 + dog | 0.535 | 0.925 | 0.674 | 0.899 | 0.085 | 27.2 |
| gaussian 3 + laplacian | 0.515 | 0.981 | 0.673 | 0.226 | 0.000 | 19.4 |
| bilateral 9 + canny | 0.518 | 0.917 | 0.659 | 0.879 | 0.096 | 7.0 |
| bilateral 9 + canny_pyr_and | 0.509 | 0.915 | 0.651 | 0.866 | 0.055 | 9.4 |

**References:**

| combination | recall | precision | F1 | FER 5 photos % | FER c_002 % | ms |
|---|---|---|---|---|---|---|
| gaussian 5 + canny (current pipeline) | 0.494 | 0.889 | 0.630 | 1.024 | 0.090 | 2.0 |
| none + canny | 0.580 | 0.797 | 0.667 | 3.122 | 0.376 | 2.0 |
| none + laplacian (best raw F1, not fold-safe) | 0.706 | 0.880 | 0.778 | 3.689 | 0.473 | 19.3 |

**Per photo (F1 / FER %):**

| photo | bilateral 9 + laplacian | gaussian 5 + canny |
|---|---|---|
| c_001 | 0.700 / 0.019 | 0.598 / 0.565 |
| c_002 | n/a / 0.059 | n/a / 0.090 |
| c_003 | 0.754 / 0.112 | 0.753 / 0.642 |
| c_004 | 0.652 / 2.449 | 0.469 / 2.693 |
| c_005 | 0.829 / 0.589 | 0.700 / 1.130 |

**Pre-processing before edges** (bilateral 9 + laplacian; F1 / FER %): none 0.734 / 0.646; clahe_L_2 0.741 / 3.286; denoise_nlm 0.732 / 0.722; shading_divide 0.722 / 0.573; shading_homomorphic 0.738 / 1.754. No pre-processing raised fold-safe F1.

**Threshold sensitivity** (step factor 0.2 / 0.33 / 0.5 × median grey; F1): bilateral 9 + laplacian 0.745 / 0.734 / 0.727; gaussian 5 + canny 0.632 / 0.630 / 0.628. The ranking holds at all three settings.

Mean and median at 9 px, and Gaussian 9, kill the print along with the folds (F1 0.0-0.49 for several detectors). Bilateral keeps the print hatching and the four sub-prints while removing fabric texture (fig1).

## 6. Figures and galleries
- **Figures** (`figures/`):
  - `fig1_smoothing_filters.png`: c_002 folds and the c_004 print under each smoothing filter, then auto-Canny.
  - `fig2_edge_detectors.png`: the nine detectors after Gaussian 5, on c_003, c_004 and c_002.
  - `fig3_enhancement_shading.png`: shading removal and contrast methods, clean and shaded.
  - `fig4_f1_vs_false_edges.png`: F1 against false-edge rate for all 117 combinations.
- **Edge galleries:** `edges/gallery_c_00X.png` (rows = 13 smoothing settings, columns = 9 detectors). Maps are in `edges/<filter>_<k>__<detector>/<cloth>.png`; with pre-processing in `edges_pre/<pre>/`.
- **Enhancement:**
  - `enhance/<method>/<cloth>.png` and `enhance/<method>/gallery.jpg`;
  - `enhance/gallery_<cloth>.jpg`;
  - `enhance_chains/<chain>/<cloth>.jpg`;
  - `enhance_degraded/<degradation>/<method>/<cloth>.jpg`.

## 7. What worked and what did not
**Worked:**
- Bilateral 9 before the detector: Laplacian precision rose from 0.88 to 0.97 while recall stayed at 0.60.
- Zero-crossing detection with a step-strength threshold: F1 0.734 against 0.630 for the current pipeline, with the false-edge rate cut from 1.024 % to 0.646 %.
- Bilateral or NLM denoising plus per-region shading removal: colour changed by only ΔE 0.4-0.5, with the best flatness (0.888).
- Thinning edge maps before scoring. Unthinned scoring (`edge_scores_try01_unthinned.csv`, kept) had made `canny_pyr_or` look best.

**Did not work:**
- Grey-world (ΔE 14.6 on clean photos, and it worsened the cast).
- Histogram equalisation and Retinex (fabric variation ×3-8, colour moved by ΔE 11-27).
- Plain `shading_divide` on colour blocks.
- The unsmoothed Laplacian (best raw F1 0.778, but a 3.7 % false-edge rate).
- `canny_pyr_or` (thick, mislocated lines).
- The c_003 script text (white on white) was found by no detector at the default sensitivity.

## 8. Issues
- **Coarse design boxes:** the boxes are approximate, so recall is a coverage score, not pixel-accurate edge recall.
- **Laplacian output is dotted:** it fills dense print areas (good for locating print regions after closing, but not a clean contour). For contiguous contours use `bilateral 9 + canny` (F1 0.659) or `canny_pyr_and` (F1 0.651).
- **c_004 false edges:** it has the highest false-edge rate (2.449 %), because its plain region is small and contains seams and small unlabelled prints.
- **Clean-photo colour numbers are not independent:** the reference palette came from the same photos. Only the synthetic degradations test accuracy.
- **HED not run:** disk was nearly full and downloads were stopped. `pywt` (PyWavelets) is not installed.
- **A MemoryError hit the first enhancement run:** fixed by converting only masked pixels to Lab and adding a retry in `p03_common.py`. No output was lost.
- **Timings are noisy** (shared CPU). c_001 and c_003 were scored at 768 px only.
- **Small sample:** 5 photos and no confidence intervals. F1 differences of a few hundredths are not meaningful.
- **Seed:** fixed at 0.

## 9. Recommendation
- **P04 (colour):**
  - Read the fabric colour from `ce.prepare_for_colour(rgb, mask)` (bilateral 9, then per-region shading removal).
  - Do not use grey-world, histogram equalisation, CLAHE, Retinex or auto-gamma before reading colour. Gamma 0.7 is the only fix that helped an under-exposed photo.
  - Plain `shading_divide` is acceptable only for single-colour garments.
- **P05 (design):**
  - Use `ce.design_edges(rgb, mask)` (bilateral 9 + Laplacian zero crossings, garment edge band ignored), or `ce.design_edges(rgb, mask, smooth=("bilateral", 9), detector="canny")` when closed contours are needed.
  - Do not add CLAHE or homomorphic filtering before edge detection.
  - P05 must still measure the effect on the final design regions with `evaluate.py`.

**How to call `cv_enhance.py`:**
```python
import sys; sys.path.insert(0, "product_ingestion")
import cv_enhance as ce
# rgb: uint8 (H,W,3) RGB; mask: bool (H,W)
colour_img = ce.prepare_for_colour(rgb, mask)
edges = ce.design_edges(rgb, mask)                  # 0/255 uint8
edges2 = ce.design_edges(rgb, mask, smooth=("bilateral", 9), detector="canny")
out = ce.apply_chain(rgb, ["denoise_bilateral9", "shading_divide_regions"], mask)
g = ce.smooth_gray(ce.to_gray(ce.fill_outside(rgb, mask)), "median", 5)
e = ce.detect_edges(g, "log", mask)
```
`ce.ENHANCERS`, `ce.SMOOTHERS` and `ce.EDGE_DETECTORS` list every method.
