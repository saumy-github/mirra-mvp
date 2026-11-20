# 05 · P04 Colour: bug fixes and multi-colour palettes

*Status: done (first pass), accepted; the new method is the default in `step_03_0_colour_extraction.py` (v0 selectable)*
*Date: 2026-11-20, 06:52 to 09:44 (paused 07:50 to 09:10 by the usage limit) (end = when this record was written, from the file time; start times are estimates)*
*Full report: `out/p04_colour/REPORT.md`.*

## Goal
Fix B1 to B3, and never reduce a shirt to one colour: output every major colour with its share and role (fabric or print), plus a region map.

## What changed [V]
- `extract_colours(rgba)` now uses mean-shift clustering in CIELAB, merges colours closer than ΔE2000 5, removes skin only with a guard (never the whole garment), and labels colours as fabric or print by their region size and contact with the outline.
- New result fields: `palette_roles`, `fabric_colours`, `region_map`, `label_map`.
- `method="v0"` keeps the old behaviour.

## My checks [V]
- The flat single colour that crashed v0 now returns one colour; a tan shirt is no longer deleted as "skin".
- c_003 (reference mask): two fabric colours, `#1c3533` 52.3 % and `#dfe1e9` 47.7 %.
- Recorded scores in `results/mirra_scores.csv`: colour score 0.961 with reference masks (palette ΔE 1.17).

## Results [V]

| Test | v0 | New default |
|---|---|---|
| Synthetic bug cases (tan, coral and pink tees; flat colour; black tee with red print; white tee with shadow) | 4 fail, 1 crash, wrong base colours | all correct |
| Mirra, reference masks: palette ΔE / base-colour ΔE | 2.06 / 1.13 | **1.17 / 0.51** |
| Mirra, v0 masks: palette ΔE | 5.77 | 4.85 |
| Fashion Product Images (266 product photos): colour-name accuracy (top-1) | 0.207 | **0.301** (parser mask: 0.252 → 0.338) |

Clustering methods compared (syllabus Unit IV):
- K-means and K-medoids are good on plain and two-colour shirts.
- Gaussian mixtures over-split shading into extra colours.
- Mean-shift found small prints without a fixed K and scored best.
- Enhancement before clustering (grey-world, CLAHE) hurt, which agrees with P03.

## Judgement
- Accepted. All three bugs are fixed with before/after evidence, and the multi-colour requirement is met (c_003's two blocks are both fabric colours).
- **Important caveat for the paper:** with the old (leaky) v0 masks, the new base colour is worse than v0's (6.81 against 1.53). The leaked background or wall becomes the largest colour, and v0 only escaped this through bug B2 (skipping white and grey). So colour quality depends on segmentation, and P01's masks must feed P04.
- The white-shirt shadow still appears as a second fabric colour; noted as a limitation.

## Next
- P10: the runner must store `extra_json()` in colors.json and pass P01's mask (and the parser skin mask on photos of people).
- Regression tests for the synthetic cases (my `tests/` job in P10).
- Per-panel palettes and colour fusion across several photos (later pass).
