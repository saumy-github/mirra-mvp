# 02 · P03 Image enhancement, smoothing filters and edge detectors

*Status: done (first pass), accepted*
*Date: 2026-11-20, 06:50 to 09:17 (paused 07:50 to 09:10 by the usage limit) (end = when this record was written, from the file time; start times are estimates)*
*Full report: `out/p03_filters/REPORT.md`. Module: `product_ingestion/cv_enhance.py`.*

## Goal
Compare the syllabus methods (Units I and II) for preparing a garment photo: enhancement and restoration before reading colour, and smoothing filters plus edge detectors for finding print edges without fabric folds. Every method's output is saved.

## What was run [V]
- 17 single enhancements and 47 chains, on the 5 Mirra photos under 5 conditions (clean plus 4 known synthetic degradations: colour cast, dark, noise, uneven light), and on 50 VITON-HD product photos for fold flatness.
- 13 smoothing settings (none; mean, median, Gaussian, bilateral at 3, 5 and 9 px) × 9 edge detectors (Sobel, Prewitt, Scharr, Laplacian, LoG, DoG, auto-Canny, Canny on a pyramid with AND/OR) × 5 photos = 585 edge maps, plus the same with 4 pre-processing steps.

## Results [V] (agent's runs; I checked that the module entry points exist and that `summary_edges.csv` matches the report)

| Question | Answer |
|---|---|
| Best way to find print edges while ignoring folds | **Bilateral filter 9 px + Laplacian zero crossings**: edge F1 0.734 against 0.630 for the current pipeline (Gaussian 5 + auto-Canny); false edges on plain fabric 0.65 % against 1.02 % (plain c_002: 0.059 % against 0.090 %) |
| Which smoothing filter protects print edges best (user's mean vs median question) | **Bilateral**: it keeps the print and removes fabric texture. Mean and median at 9 px (and Gaussian 9) wipe out the print together with the folds (F1 down to 0.0-0.49 for several detectors); at 3 px, median (F1 0.727) is close to bilateral |
| Does enhancement help colour reading | No method improves colour on clean photos. Edge-preserving denoising is neutral (ΔE 0.22-0.28). Grey-world (ΔE 14.6), histogram equalisation (11-22) and Retinex (26-29) damage colour. Grey-world fails because a single-coloured shirt breaks its "average is grey" assumption |
| Shading removal | Dividing by a blurred copy flattens folds best on single-colour shirts (VITON-HD flatness 0.83) but wrecks colour-block shirts (c_003 ΔE 24.7: it treats a colour block as lighting); the per-region version keeps c_003 at ΔE 0.80. Homomorphic (Fourier) filtering adds false edges |
| Pre-processing before edges | None helped; CLAHE triples the false-edge rate (3.3 %) |

## Judgement
- Accepted. The study is thorough, saves every output, and the record is honest about its limits: the design boxes are coarse, the reference palettes come from the same photos, and the sample is only 5 photos.
- The edge result is a clear, explainable improvement for the paper. "Bilateral beats mean, median and Gaussian because it smooths within regions but not across edges" is the classic textbook behaviour, now measured on our garments.
- The Laplacian output is dotted rather than a clean contour, so it is best used as evidence of where a print is, not as the print's outline. That is how P05 should use it.

## Feeds into
- **P04:** `ce.prepare_for_colour` (bilateral 9 + per-region shading removal) before clustering; no grey-world, histogram equalisation, CLAHE or Retinex.
- **P05:** `ce.design_edges` (bilateral 9 + Laplacian) as the edge evidence for design regions.

## Not done
- HED learned edge model (disk was nearly full; downloads stopped).
- DWT, because `pywt` is not installed. P05 must use another route for wavelets.
