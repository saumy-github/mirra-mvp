# 12 · P15a Segmentation improvement pass: choosing v1 or v1_all automatically

*Status: done, accepted; `v1_auto` is the new default in `step_02_0_segmentation.py` (v1, v1_all and v0 selectable). Live check on the 5 Mirra photos done at 15:02, with the same numbers as the offline replay.*
*Date: 2026-11-20, about 14:10 to 15:00*
*Agent report: `out/p15a_seg_autoselect/REPORT.md`; outputs in `out/p15a_seg_autoselect/`.*

## Goal
Fix the one open outline failure from P01 and P10:
- The default v1 keeps only the white upper half of the colour-block shirt c_003 (IoU 0.562), because the clothes parser calls the teal lower half "Skirt".
- v1_all includes the Skirt class and fixes c_003 (0.940), but it is clearly worse on photos of people and street photos.

## What was tried [V]
14 selection rules, designed on P01's 405 public images and checked on 400 new held-out public images.

| Kind of rule | Result |
|---|---|
| Model confidence (SAM 2 predicted IoU; SegFormer class probability) | Worse than v1, or no fix for c_003: SegFormer is 96 % sure c_003's lower half is a skirt |
| Edge alignment of the two masks | Worse on person and street photos |
| Geometry of the "skirt" (size, contact with the top, reaches the bottom, no waist) | Worse: real skirts in cropped photos of people look the same as c_003 |
| Extra SAM 2 prompts (negative points, skirt-only prompt) | No usable separation, or no gain for an extra model pass |
| **Is a head visible?** (SegFormer Face + Hair under 1 % of the image) | **Winner** |

## The rule
- **Rule:** if the parser finds a "Skirt" of at least 1 % of the image and no head, the photo is a flat product shot or a torso crop of a top. The "skirt" is then the top's own lower half, so v1_all is used; otherwise v1 is used.
- **Cost:** the decision uses the SegFormer output that v1 computes anyway, so it adds no model pass.

## Results [V] (public IoU, paired bootstrap 95 % CI)

| | v1 | v1_all | **v1_auto** |
|---|---|---|---|
| Held-out macro IoU (400 new images) | 0.8940 | 0.8563 | **0.8966** |
| Pooled macro IoU (805 images) | 0.8915 | 0.8528 | **0.8942** |
| Pooled failure rate (IoU < 0.1) | 1.12 % | 2.25 % | **1.00 %** |
| Mirra, mean of 5 (offline replay) | 0.9066 | 0.9818 | **0.9821** |
| Mirra c_003 | 0.562 | 0.940 | **0.940** |

- **Against v1:** +0.0027 macro IoU pooled (CI +0.0005 to +0.0059). It is never worse on person or street photos, because the rule never fires there.
- **Where it fires:**
  - on 11 public images (all flat product photos), improving 8 and worsening 1;
  - on Mirra c_003.
- **Code check:** the coded decision equals the offline rule on all 805 images.

## Judgement
- **Accepted.**
  - It removes the last large outline error on the user's photos with no cost elsewhere.
  - It is also the clearest "classical reasoning on top of a model" example: a simple scene rule (is there a head?) decides how to read the model's labels.
- **Caveats:**
  - The torso-crop case rests on one photo (c_003).
  - The head threshold has little margin: c_003 has 0.3 %, and the nearest street counter-example has 1.2 %.
  - A headless photo of a top worn with a real skirt would include the skirt; none appeared in 805 public images.
  - The live check (`out/p15a_seg_autoselect/pipeline_check.json`, 15:02) and the final P10 run gave the same Mirra IoU as the offline replay (mean 0.982, c_003 0.939).

## Failed attempts kept for the paper
The rule table in the report (model-confidence, edge, geometry and extra-prompt rules) shows why the obvious "trust the more confident model" choice fails.

## Next
- Live check: done (same numbers).
- P10 final run with v1_auto + v4_relabel: pipeline score 0.960 (`plans/10`).
