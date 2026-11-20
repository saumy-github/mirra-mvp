# 01 · P00 Baseline, reference labels and the scoring framework

*Status: done (agreement-with-judgement check added 2026-11-20 15:15)*
*Date: 2026-11-20, 06:00 to 07:00*

## Goal
Decide how methods are scored before comparing any, then score today's pipeline (v0) so every later method has a fixed baseline.

## What was done
1. **Unit tests** [V]: `pytest product_ingestion/tests -q` -> 35 passed, 16 subtests passed (31.9 s).
2. **v0 snapshot** [V]: the current outputs of `product_ingestion/output/<cloth>/s_001/001/` (image_info, textures, run_summary, input photo) copied to `out/p00_baseline/v0_outputs/<cloth>/`.
3. **Reference garment masks** (approximate) [V]:
   - `scripts/p00_reference_candidates.py` saved the 3 raw SAM 2 candidates (centre point + 4 corner background points, the v0 prompt) and the SegFormer clothes-parser map for each photo, with overlay sheets in `out/p00_baseline/reference_candidates/<cloth>/candidates_sheet.jpg`.
   - I chose the shirt-only candidate by eye; `scripts/p00_make_reference_masks.py` cleaned it (largest component, holes filled with a padded flood fill, small opening) -> `out/p00_baseline/reference/<cloth>/garment_mask.png`.
4. **Reference labels** (approximate) [V]: `scripts/p00_reference_labels.py` -> `out/p00_baseline/reference/labels.json` (view, presentation, sleeve, fit, design boxes and types, reference palette from the masks); overlays `reference/<cloth>/design_regions_overlay.jpg`.
5. **Scoring script** [V]: `scripts/evaluate.py` (standard prediction format in its docstring; appends to `results/mirra_scores.csv`).
6. **Damage tests** [V]: `scripts/p00_metric_sanity.py` -> `results/metric_sanity.csv` and `results/metric_sanity_{outline,colour,design}_summary.csv`.
7. **v0 scored** [V]: `scripts/p00_v0_to_standard.py` converts v0 outputs (`out/p00_baseline/v0_standard/`); table `results/v0_baseline.csv`.

## Findings while building the references [V]
| Photo | Observation |
|---|---|
| c_004 | SAM 2's highest-scoring candidate (predicted IoU 0.756) is only the print square; the whole shirt is the candidate SAM 2 scores lowest (0.191). Picking by score alone fails. |
| c_005 | All three SAM 2 candidates score low (0.32 to 0.49); one includes the man's head. |
| c_002 | SegFormer clothes parser marks only 5.9% of a flat pink tee as "upper-clothes": it is not trained on product photos. |
| c_003 | SegFormer labels the dark-teal lower half "Skirt" and grabs parts of the arms; SAM 2 candidate 2 is clean. |
| c_004 | SegFormer splits the flat shirt into "upper-clothes" and "dress". |
| v0 masks | Too big on 4 of 5 photos: reference area vs v0 area: c_002 65.2% vs 89.4%, c_003 66.5% vs 84.8%, c_004 45.9% vs 77.2%, c_005 30.4% vs 76.9%. |

**Bias warning:** four reference masks come from SAM 2 candidates, so on the Mirra photos SAM 2-based methods have an advantage (c_001 v0 scores IoU 1.0 because v0 picked the same candidate). Headline outline numbers must come from public datasets with exact masks (VITON-HD, Fashionpedia).

## Choosing the metrics (damage tests, mean over the 5 photos) [V]
Outline (from `metric_sanity_outline_summary.csv`):

| Damage | IoU | Boundary F @1% | HD95 (% diag) |
|---|---|---|---|
| border grown by 1% of diagonal | 0.928 | 0.918 | 2.53 |
| border grown by 2% | 0.861 | 0.000 | 3.88 |
| leak blob 20% of garment (arms/background) | 0.928 | 0.897 | 5.16 |
| missing chunk 5% / 20% | 0.951 / 0.803 | 0.906 / 0.829 | 12.24 / 9.05 |

- IoU barely reacts to border errors; boundary F at 1% reacts to real border errors but not to tiny ones; HD95 is not monotonic (5% missing scores worse than 20%), so it is rejected as primary.
- **Outline score = mean of IoU and boundary F @1%**, with leakage and miss reported separately.

Colour (`metric_sanity_colour_summary.csv`):

| Damage | Palette ΔE | Base-colour ΔE | All fabric colours found ΔE |
|---|---|---|---|
| fabric shifted ~ΔE 2 / 5 / 10 / 20 | 1.28 / 3.10 / 5.87 / 10.51 | 1.37 / 3.28 / 6.39 / 11.68 | 1.46 / 3.48 / 6.40 / 11.56 |
| one colour block dropped (c_003) | 4.96 | **0.40** | 24.60 |
| spurious 10% colour added | 1.47 | 0.14 | 0.00 |
| print colour dropped | 1.92 | 0.15 | 0.00 |

- The base-colour ΔE does not notice when a whole colour block is lost, so it cannot judge multi-colour shirts.
- **Colour score = 1 − palette ΔE / 30** (clipped at 0); "all fabric colours found" is kept as a guard for colour-block shirts.

Design (`metric_sanity_design_summary.csv`):

| Damage | F1 @IoU 0.3 | Pixel IoU | Type accuracy |
|---|---|---|---|
| one region dropped | 0.714 | 0.304 | 1.0 |
| one false region added | 0.658 | 0.781 | 1.0 |
| boxes shifted 25% / 50% of width | 1.000 / 1.000 | 0.712 / 0.524 | 1.0 |
| all types wrong | 0.933 | 0.852 | 0.0 |

- **Design score = mean of F1 @0.3, pixel IoU and type accuracy**, because each catches a failure the others miss.

**View score** = share of photos with the right view. **Pipeline score** = mean of the four area scores (equal weights: all four matter to the user).

**Agreement with judgement by eye** [V] (`scripts/p00_judgement_check.py`, `results/judgement_agreement.csv`, sheets and ranks in `out/p00_baseline/judgement/`):
- **Method:**
  - 8 segmentation methods were drawn on each Mirra photo under hidden letters: v0, v1 and v1_all pipelines, GrabCut, K-means, RMBG, Grounding DINO + SAM 2, and a 3-model vote.
  - I ranked them by eye before opening the key, with ties allowed for outlines I could not tell apart (`ranks.json` gives the reasons).
  - Agreement is Kendall's tau-b between my order and each metric's order.

| Metric | c_001 | c_002 | c_003 | c_004 | c_005 | Mean |
|---|---|---|---|---|---|---|
| IoU | 0.866 | 0.793 | 0.824 | 0.816 | 0.866 | **0.833** |
| Outline score (IoU + boundary F) | 0.701 | 0.793 | 0.737 | 0.816 | 0.784 | 0.766 |
| HD95 | 0.546 | 0.728 | 0.564 | 1.000 | 0.917 | 0.751 |
| Boundary F @1% | 0.791 | 0.672 | 0.390 | 1.000 | 0.742 | 0.719 |

- **All four metrics agree strongly with the eye** (tau 0.72 to 0.83).
  - IoU agrees best: at sheet size the eye mostly sees leaks (arms, trousers, background) and missing pieces, and IoU measures exactly those.
  - Boundary F is noisy inside groups of near-identical outlines (c_003 0.39).
- **Decision:** keep the outline score as the headline, because the damage tests showed that IoU alone misses border errors the eye cannot see at this size. Always report IoU next to it.
- **Limits:** one judge (the orchestrator, who also made the reference masks), 5 photos and 8 methods.

## v0 baseline (5 Mirra photos, approximate references) [V]
| Area | Score | Key numbers |
|---|---|---|
| Outline | 0.658 | IoU 0.700, boundary F @1% 0.617, leakage 0.300 (c_005 leakage 0.605) |
| Colour | 0.808 | palette ΔE 5.77; base-colour ΔE 1.53 |
| Design | 0.164 | F1 0.133; plain c_002 gets a false "text" region; c_003 colour blocks not found |
| View | 0.000 | view selection never ran (CLIP failed to load) |
| **Pipeline** | **0.407** | |

## Next
Wave 1 is running (P01, P03, P04, P05, P16, P07); each scores its methods with `evaluate.py`.

## Corrections
- *2026-11-20 14:49:* the c_004 reference box for the text "Different yet SAME" was about 20 px too low (`[28, 57, 72, 66]` %, covering mostly plain fabric under the text). P15b flagged it, and I confirmed it by drawing both boxes on the photo. Corrected to `[30, 53.5, 70, 60]` % in `scripts/p00_reference_labels.py`, and `labels.json` regenerated.
  - Re-scored with the corrected label: the v0 pipeline (still 0.407), the P10 pipeline (0.911), and the P05 and P15b method rows. The latest row per label in `results/mirra_scores.csv` is the corrected one; earlier rows are kept.
  - Rows scored before the correction (most other P05 rows) give c_004 slightly lower design scores.
