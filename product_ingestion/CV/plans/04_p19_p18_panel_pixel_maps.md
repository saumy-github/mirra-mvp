# 04 · P19 Per-panel pixel maps (with P18 texture check)

*Status: done (first pass), accepted; v1 is the new default in `step_06_0_texture_projection.py` (v0 selectable)*
*Date: 2026-11-20, 07:20 to 09:40 (paused 07:50 to 09:10 by the usage limit) (end = when this record was written, from the file time; start times are estimates)*
*Full report: `out/p19_panel_maps/REPORT.md`. Modules: `cv_panel_maps.py`, `cv_texture_check.py`.*

## Goal
The user's idea: save one image per panel (front, back, sleeves) where every pixel is a fixed patch of fabric, cut from the right part of the right photo, so CLO can place it 1:1.

## What changed [V]
- `project_textures(..., method="v1")` is the new default; `method="v0"` keeps the old box-to-box warp. 7 texture unit tests pass.
- v1 splits the torso from the sleeves using armpit and shoulder landmarks (P06), warps each region onto its panel with a thin-plate spline, fills holes from neighbouring fabric, chooses the resolution from the photo's own density, and writes side-car metadata (mm per pixel, origin, assumptions) for 1:1 placement.

## Results [V] (agent's runs; I checked the c_003 figure by eye)

| Measure | v0 (old) | v1 (new) |
|---|---|---|
| Body panel silhouette IoU (photo region warped onto the panel vs the panel shape) | 0.64 to 0.87 | **0.87 to 0.98** (all 9 test photos) |
| Sleeves taken from | the left/right 35 % of the garment box (includes torso) | the real sleeve region |
| Back panel without a back photo | one flat colour | front fabric without the print (an assumption, recorded) |
| Transparent holes inside panels | yes | none |
| Thin-plate spline vs affine-only (c_005 body IoU) | - | 0.963 vs 0.826 |

My visual check of `fig_c_003.jpg`:
- **v0:** the front panel holds the whole shirt, sleeves squeezed in; the back is flat teal, although the shirt's top half is white; the sleeves are teal with stripes, which are torso pixels.
- **v1:** a clean torso with stripes and text on the front; white sleeves, which is correct; a back panel with the white/teal split.
- **Faults still visible in v1:** a faint "whatever" ghost on the back panel and a mirror crease on the sleeves.

## Judgement
- Accepted. It is a clear, visible improvement, and the agent was careful about what its numbers mean: it states that ΔE and SSIM are round-trip losses rather than accuracy, and moved the evidence to silhouette IoU and the figures.
- Known weaknesses go into the paper's limitations:
  - on-person and cropped photos get estimated proportions;
  - print removal for the assumed back leaves ghosts;
  - the mirrored sleeve halves show a crease;
  - thin lines lose some colour accuracy.
- The runner must pass `garment_mask`, `view` and `on_person` to v1. This is my P10 job, after P16 finishes.

## Next
- P10: wire the new parameters into `run_product_ingestion.py`.
- Later pass (P15+): better print removal for the assumed back panel; a true front-and-back test once P16's view assignment is wired.
- 1:1 placement in CLO waits for the user (P20, `questions.md` Q6 and Q7).
