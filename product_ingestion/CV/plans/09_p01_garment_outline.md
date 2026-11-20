# 09 · P01 Garment outline: segmentation methods compared

*Status: done (first pass), accepted; `v1` is the new default in `step_02_0_segmentation.py` (v0 and v1_all selectable)*
*Date: 2026-11-20, 06:50 to 10:24 (paused 07:50 to 09:10 by the usage limit); last output 10:24, record written 14:12 after the 10:25 to 14:05 stop (`ISSUES.md` I20)*
*Full report: `out/p01_segmentation/REPORT.md`. Module: `product_ingestion/cv_segment.py`.*

## Goal
Cut the garment out of the photo cleanly and draw its outline. Compare SAM 2 prompts, other models, classical syllabus methods and combinations of 2 or 3, and fix B5, B6 and B7.

## What changed [V]
- **New default v1:** the SegFormer clothes parser gives the garment's box and an interior point, and SAM 2 is prompted with them, asking for a single mask.
- **Variant v1_all:** also uses the parser's "skirt" pixels and removes skin, arms and face.
- **Fixed bugs:**
  - B5: the corner flood fill;
  - B6: edge sharpness is now measured against the photo's edges;
  - B7: holes are counted correctly.
- **New quality signals:** SAM 2's own IoU, border touch, agreement with the parser, edge alignment.
- **Outline:** a smoothed, simplified polygon (`outline_polygon`), replacing "colour the background and run edge detection".
- **Methods compared:** 58 in total.

## My checks [V]
- `results/mirra_scores.csv`, outline score on the 5 Mirra photos: v0 0.658, v1 0.919, v1_all 0.974.
- torch 2.4.1+cu121, numpy 1.26.4 and transformers 4.56.0 are unchanged after the agent's work.
- Ultralytics silently installed `clip` 1.0 and `regex`; logged in `env/ENVIRONMENT.md`.
- The smoke test of the full pipeline (c_002) used v1: mask area 65.0 %, against 65.2 % in the reference and 89.4 % for v0.

## Results [V]

| Method | Mirra IoU (5 photos) | Public macro IoU (VITON product / VITON person / Fashionpedia street) | Failures (IoU < 0.1) |
|---|---|---|---|
| v0 (old: SAM 2 centre point) | 0.700 | 0.756 (0.932 / 0.775 / 0.562) | 8.0 % |
| v0 + B5 fix only | 0.915 | 0.754 | 9.7 % |
| **v1: parser box + point → SAM 2** | 0.907 | **0.889** (0.936 / 0.893 / 0.838) | **1.1 %** |
| v1_all (+ skirt class, minus skin) | **0.982** | 0.849 | 2.1 % |
| Grounding DINO box → SAM 2 | 0.950 | 0.883 | 2.7 % |
| SegFormer parser alone | 0.896 | 0.883 | 1.3 % |
| GrabCut (classical) | 0.770 | 0.618 | 2.2 % |
| K-means / mean-shift / region growing (classical) | 0.46 to 0.59 | 0.43 to 0.49 | 18 to 30 % |
| Votes of several models | 0.90 | 0.72 to 0.79 | 1.1 % |

Paired bootstrap (95 % CI), v1 minus v0:
- VITON person photos: +0.118 (0.082 to 0.156);
- Fashionpedia street photos: +0.277 (0.213 to 0.342);
- flat product photos: no difference (+0.004, −0.014 to 0.023).

## Judgement
- Accepted. This is the most thorough plan: 58 methods, three public test sets with exact masks, confidence intervals, and honest caveats (the Mirra reference favours SAM 2).
- **Main finding for the paper:** the problem was SAM 2's prompt, not SAM 2 itself. A clothes parser's box as the prompt fixes photos of people and street photos, and combinations or votes do not beat a good single prompt. Classical methods work only on flat photos on a plain background.
- **Open trade-off that matters for the user:** on c_003 (white/teal colour-block shirt), v1 loses the teal lower half (IoU 0.562), because the parser calls it a "skirt". Losing half a multi-colour shirt is a serious error for colour and texture. v1_all fixes it (0.939) but is worse on public street photos with real skirts.
  - Decision: try an automatic choice between v1 and v1_all as an improvement pass (P15a), validated on the public sets.
  - Until then: v1 is the default; the runner can select v1_all.

## Found on the way
- **U²-Net never ran:** the old v0 "U²-Net fallback" has never worked in this venv, because `onnxruntime` is not installed.
- **v0's quality score was useless:** it gave 0.98 to a mask with IoU 0.395. The new score ranks c_003 lowest, matching the photo where v1 fails.
