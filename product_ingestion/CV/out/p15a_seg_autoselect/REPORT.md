# P15a report: automatic choice between v1 and v1_all (new method `v1_auto`)

*Date: 2026-11-20. Written by the P15a sub-agent and saved here by the orchestrator. Status: rule chosen and implemented, validated offline on cached model outputs (405 development + 400 new held-out public images + 5 Mirra photos). The live `run_segmentation()` check on the 5 Mirra photos (`p15a_pipeline_check.py`) was still queued behind the GPU lock when this report was written.*

## 1. Goal
Choose automatically between v1 (SegFormer top box + point → SAM 2) and v1_all (adds the "Skirt" class, removes skin). The target is v1_all's result on photos like c_003, where the lower half of a top is labelled "Skirt", and v1's result where a real skirt or lower garment exists.

## 2. Verdict
**Winner: `v1_auto`, rule "Skirt without head":**
- **When it switches to v1_all:** the largest SegFormer Skirt component covers at least 1 % of the image AND SegFormer Face + Hair cover under 1 % (no head in the photo).
- **Otherwise** it uses v1.
- **Reasoning:** with no head visible, the photo is a flat product shot or a torso crop of a top, so a "Skirt" under the top is the top's own lower half. With a head visible, a person wears a real skirt.

It is now the default. `v1`, `v1_all` and `v0` stay selectable.

The torso-crop evidence is one image (c_003). On public data the rule fires only on flat VITON product photos.

## 3. Setup
- v1 = P01 `sam2_box_segtop_pt`; v1_all = P01 `comb_box_seglc_pt_minus_skin`. Same cleaning and scoring as P01 (`metric_small`, longest side 512).
- **P01's numbers reproduced exactly:** public macro 0.8890 (v1), 0.8492 (v1_all); Mirra 0.9066 and 0.9818.
- **New held-out set** (not used to design the rules), built by `scripts/p15a_build_heldout.py`:
  - 150 VITON-HD test rows each for viton_cloth and viton_person (seed 1, P01 rows excluded);
  - 100 Fashionpedia val photos (seed 1, P01 photos excluded).
- **Bootstrap:** paired, 2000 resamples within each set, seed 0. **Fail rate:** IoU < 0.1.
- **Not completed:** the extra-prompt SAM 2 run (`sam2x`) on held-out images was cancelled while waiting for the GPU lock, so rules using those features are evaluated on dev only.

## 4. Rules tried (public macro IoU)

| Rule | Dev | Held-out | Verdict |
|---|---|---|---|
| v1 | 0.8890 | 0.8940 | baseline |
| v1_all | 0.8492 | 0.8563 | baseline |
| Oracle, best of the two per image | 0.8934 | 0.8976 | upper bound only |
| SAM 2 predicted IoU, pick the higher | 0.8784 | 0.8815 | FAIL: worse than v1, CI excludes 0 |
| SAM 2 IoU, v1_all only if higher by > 0.02 | 0.8912 | 0.8950 | marginal (CI includes 0); fixes c_003 on dev only; needs an extra SAM 2 pass |
| Edge alignment, pick the higher | 0.8626 | 0.8750 | FAIL: person and street photos drop; c_003 not fixed |
| Geometry only (skirt size, contact, reaches bottom, no waist) | 0.8801 | 0.8810 | FAIL: real skirts in cropped person photos look the same as c_003 |
| Head + geometry | 0.8890 | 0.8940 | never fires, so c_003 not fixed |
| **Head: Face + Hair < 1 % (or < 0.5 %)** | **0.8918** | **0.8966** | **WINNER** |
| Head < 2 % | 0.8884 | 0.8960 | too loose: one street photo has head 2.3 % |
| SegFormer ambiguity (> 0.30 or 0.33) | 0.8911 / 0.8923 | 0.8948 / 0.8950 | does not fix c_003 (SegFormer is confident: p = 0.96); fragile |
| Head or ambiguity > 0.33 | 0.8923 | 0.8967 | +0.0001 over the winner; extra threshold and softmax, not adopted |
| SAM 2 on the Skirt region only, spill into the top > 5 % | 0.8918 | not run | equal on dev; extra SAM 2 pass |
| Negative-point prompt variants | n/a | n/a | no usable separation (c_003 0.94 against real skirts 0.96 to 0.98) |

## 5. Final method (paired bootstrap 95 % CI; `rules_final_*.csv`)

| Split | Method | VITON cloth | VITON person | Fashionpedia | Macro | Fail rate | vs v1 (macro) |
|---|---|---|---|---|---|---|---|
| Dev (405) | v1 | 0.9357 | 0.8932 | 0.8382 | 0.8890 | 1.25 % | - |
| | v1_all | 0.9427 | 0.8127 | 0.7921 | 0.8492 | 2.25 % | -0.0399 |
| | **v1_auto** | 0.9440 | 0.8932 | 0.8382 | **0.8918** | 1.25 % | +0.0027 (-0.0000 to +0.0072) |
| Held-out (400) | v1 | 0.9355 | 0.9107 | 0.8357 | 0.8940 | 1.00 % | - |
| | v1_all | 0.9421 | 0.8302 | 0.7967 | 0.8563 | 2.25 % | -0.0376 |
| | **v1_auto** | 0.9435 | 0.9107 | 0.8357 | **0.8966** | 0.75 % | +0.0027 (-0.0003 to +0.0076) |
| Pooled (805) | v1 | 0.9356 | 0.9019 | 0.8370 | 0.8915 | 1.12 % | - |
| | v1_all | 0.9424 | 0.8215 | 0.7944 | 0.8528 | 2.25 % | -0.0387 |
| | **v1_auto** | 0.9437 | 0.9019 | 0.8370 | **0.8942** | 1.00 % | **+0.0027 (+0.0005 to +0.0059)** |

- **Against v1_all,** pooled: +0.0415 (+0.0318 to +0.0521).
- **Per set, v1_auto minus v1,** pooled:
  - viton_cloth +0.0081 (+0.0014 to +0.0178);
  - person and street photos 0.0000, because the rule never fires there.
- **Where it fires:**
  - 11 public images (7 dev, 4 held-out), all flat VITON product photos, plus Mirra c_003.
  - IoU rises on 8 of the 11 and falls on 1 (held-out 01621: 0.963 → 0.844).
- **Code check:** `cv_segment.auto_skirt_decision`, replayed on the cached labels, equals the offline rule on all 805 images (`scripts/p15a_final_table.py`).

**Mirra (5 photos, approximate references, offline replay of cached masks):**

| Method | Mean | c_003 |
|---|---|---|
| v1 | 0.9066 | 0.562 |
| v1_all | 0.9818 | 0.940 |
| **v1_auto** | **0.9821** | **0.940** |

The rule fires only on c_003; the other 4 photos keep their v1 masks (c_001 0.997, c_002 0.997, c_004 0.989, c_005 0.989).

## 6. Code changes
- **`product_ingestion/cv_segment.py`:** `auto_skirt_decision(labels) -> (use_all, features)`, with `AUTO_SKIRT_MIN_FRAC = 0.01` and `AUTO_HEAD_MAX_FRAC = 0.01`.
- **`product_ingestion/step_02_0_segmentation.py`:**
  - new method `"v1_auto"`, now `DEFAULT_METHOD`;
  - SegFormer runs once, the decision is made, then SAM 2 runs once with the v1 or v1_all prompt;
  - the decision is stored in `result.details["auto"]` (skirt_frac, head_frac, use_all);
  - `run_segmentation(path, method=None)` is unchanged, and `MIRRA_SEG_METHOD=v1` selects the old default.
- **Scripts:** `p15a_common.py`, `p15a_build_heldout.py`, `p15a_features.py`, `p15a_gpu.py`, `p15a_rules.py`, `p15a_final_table.py`, `p15a_pipeline_check.py`.

## 7. Commands (repo root)
```
.venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_features.py --split dev
.venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_build_heldout.py
.venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_gpu.py --stage segformer --split held   # then --stage sam2 --split held
.venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_features.py --split held
.venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_rules.py --features features.csv --tag dev
.venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_final_table.py
.venv/Scripts/python.exe product_ingestion/CV/scripts/p15a_pipeline_check.py default v1   # live check (queued behind the GPU lock)
```

## 8. Issues and caveats
- **GPU lock:**
  - P17 held the lock for more than 25 minutes, so the live check was queued.
  - Until it runs, the Mirra numbers are an offline replay of cached masks; the prompts in `segment_v1` are identical to the cached ones.
- **Small margin on the head threshold:**
  - c_003 has Face + Hair 0.3 %; the nearest street counter-example has 1.2 %.
  - 0.5 % and 1 % give identical results; 2 % is worse.
- **Known failure mode [I]:** a photo with the head cropped off, showing a top and a real skirt, would include the skirt. No such case occurred in the 805 public images.
- **Tests:** `test_segmentation_quality.py` gives 11 passed; it runs on the CPU and does not exercise `v1_auto`.

## 9. Recommendation
- Keep `v1_auto` as the default.
- Re-run `p15a_pipeline_check.py` once the GPU is free.
- More Mirra torso-crop and colour-block photos would test the head rule properly.
