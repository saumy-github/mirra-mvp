# P19 per-panel pixel maps and P18 texture check

*Status: first pass finished; known gaps listed under "Not done" and "Issues". Date: 2026-11-20.*
*Written by the P19 sub-agent and saved here by the orchestrator (sub-agents cannot write report files). All numbers come from its runs, stored under `out/p19_panel_maps/`.*

## 1. Goal
One image per pattern panel: front, back, sleeve_left and sleeve_right. Every pixel is a fixed patch of fabric (`mm_per_px` is in the side-car JSON), cut from the right region of the right photo, so CLO can place each image 1:1.

## 2. Files
| File | What |
|---|---|
| `product_ingestion/step_06_0_texture_projection.py` | The old `TextureProjector` class is untouched (this is v0). `project_textures(...)` gains optional keyword parameters and `method="v0"` or `"v1"`, plus a new `project_textures_v1`. `TextureProjectionResult` gains two fields with defaults, `method` and `warps` |
| `product_ingestion/cv_panel_maps.py` (new) | The v1 algorithm: landmarks, torso/sleeve split, thin-plate-spline (TPS) warp, hole fill, print removal for the assumed back, side-car metadata |
| `product_ingestion/cv_texture_check.py` (new) | P18: re-projection onto the photo, ΔE2000, SSIM, silhouette IoU, flat preview, error maps |
| `CV/scripts/p19_*.py` | Experiments; the main ones are `p19_run.py` and `p19_extra.py` |

Unit tests: `pytest product_ingestion/tests/test_texture_projection.py -q` gives 7 passed (run after the last change). The synthetic test garment goes through v1.

## 3. How to call it
```python
project_textures(garment_rgba, layouts, textures_dir, graphic_rgba=None, design_type="", *,
                 method="v1",            # "v0" = old behaviour exactly
                 back_rgba=None,         # photo of the OTHER view (RGBA; alpha > 127 is the mask unless back_mask is given)
                 garment_mask=None,      # H x W uint8 0/255 or bool; overrides alpha > 127
                 landmarks=None,         # optional: cv_shape.garment_landmarks(mask)["landmarks"]
                 px_per_cm=None,         # None = the photo's own density, clamped to 5..20 px/cm
                 view="front",           # view of garment_rgba: "front" | "back"
                 back_mask=None, on_person=False,   # on_person=True: hem estimated, not read from the outline
                 warp="tps")             # "tps" | "affine"
```
- **Compatibility:** the return type and fields are unchanged. If v1 raises an error, the call falls back to v0 and records why in `message`.
- **Prints:** v1 ignores `graphic_rgba` and `design_type`, because the print is already in the photo pixels.
- **Back view:** with `view="back"`, `back_rgba` is treated as the front photo.
- **What the runner should pass:** `garment_mask=<hard mask>`, `view=<P16 result>` and `on_person=<presentation>`. Without them, the alpha channel is thresholded at 127 and the photo is treated as a flat front.
- **Outputs:** `<piece>_texture.png` keeps its name, and `texture_projection_metadata.json` keeps its old keys.
  - New per-panel keys: `texture_size_mm`, `px_per_mm`, `mm_per_px`, `origin`, `panel_polygon_px`, `source`, `from_photo`, `photo_native_px_per_cm`, `photo_px_per_cm_used`, `resolution_note`, `photo_coverage_of_panel`, `filled_fraction`, `assumptions`.
  - New top-level keys: `method`, `main_photo_view`, `other_photo_given`, `warp`, `photo_info`, `notes`, `conventions`.
  - Sample: `metadata_sample_c_003.json`.

## 4. Method v1
1. **Landmarks:**
   - Armpits come from P06 `cv_shape.garment_landmarks`, used only when found by convexity defect; otherwise a bounding-box estimate, flagged.
   - P06's shoulder points are used when they pass sanity checks; otherwise the shoulder tip is where an inward-leaning armhole line, walked up from the armpit, leaves the garment.
   - P06's neck points, cuffs and polygons were not used (noisy on these photos).
2. **Split:**
   - A sleeve is the part of the mask outside the line from armpit to shoulder tip; below the armpit, it is the part outside the vertical through the armpit.
   - The torso is the rest.
   - Each sleeve is the largest connected component, dropped if smaller than 1.2 % of the garment.
3. **Torso to panel:** a thin-plate spline (scipy `RBFInterpolator`, smoothing 10) maps panel pixels to photo pixels. Pairs:
   - armpits and shoulder tips;
   - 4 points along each armhole;
   - the neck-shoulder points, 2 points along each shoulder line and the neck centre;
   - the hem corners and hem centre.

   Untrusted landmarks (top or bottom cropped, photo of a person, implausible hem width) are estimated from the chest width, and this is recorded in the metadata.
4. **Sleeve to panel:**
   - The photo sleeve (shoulder tip, armpit and two cuff corners) is warped onto HALF of the sleeve panel. The other half is a mirror, or comes from the other photo when one is given.
   - Orientation follows the seam table in `clo_vto/native_vto/seams.py`: in a front view the image-right sleeve goes to `sleeve_left`.
   - Sleeves with no usable cuff edge use a 3-point fit.
5. **Resolution:**
   - The photo's own density is the armpit span in pixels divided by the panel's armpit span in cm, clamped to 5..20 px/cm.
   - The photo is reduced only if the target density is below 0.8 times its own.
   - The metadata says "upsampled from the photo (no new detail)" when the panel is upsampled.
6. **Holes:**
   - The region is eroded by 2 px, so no background colour reaches the edges.
   - Gaps of up to 4 px are inpainted (Telea).
   - Larger gaps take the nearest fabric colour, blurred by about 0.8 cm.
   - Everything outside the panel polygon is transparent. `filled_fraction` is recorded.
7. **Back panel without a back photo:**
   - The front photo is cleaned of its print: pixels that differ from the local fabric colour by ΔE > 9 are replaced by the fabric colour of their colour block.
   - The cleaned photo is then warped with the back panel's landmarks.
   - The metadata records that this is an assumption.

## 5. Runs
- `p19_run.py --viton 4`: v0, v1_tps and v1_affine on c_001..c_005 and the first 4 VITON-HD test rows.
  - Outputs: `{v0,v1_tps}/<photo>/` (textures, metadata, flat preview, error map, reprojected photo, side-by-side), `fig_<photo>.jpg`, `metrics.csv`, `metrics.json`.
  - The affine variant was scored, then its images were removed; only its metrics are kept.
- `p19_extra.py`: the two-photo path test (`v1_tps/pair_c004front_c002back/`), `c003_colour_boundary.json`, `metadata_sample_c_003.json`.
- **Earlier attempts kept:** `_try1.jpg`, `_dbg_regions.jpg`, `_dbg_sleeve.jpg`, `metrics_try1_inverse_rbf.*`.
  - **First torso split** (fixed inward-leaning armhole): it cut the BOSTON letters on drop-shoulder c_001. Fixed by using P06's shoulder point.
  - **First cuff-corner rule:** it collapsed the cuff corners to one point. Replaced by a cuff band along the arm axis plus a triangle fallback.
  - **First P18 re-projection** used an inverse TPS fit separately. That gave misleading ΔE values, so it was replaced by an exact forward splat.

## 6. Metrics (`metrics.csv`, `metrics.json`; one run, one photo each)
**How to read them:**
- ΔE00 and SSIM compare the re-projected photo with the photo inside the garment.
- "covered" is the share of garment pixels that land on a photo-derived panel pixel.
- sil_iou is the IoU of the photo region warped onto the panel against the panel polygon. **This is the geometry metric.**
- **Caveat:** the re-projection is the exact inverse of the cut, so ΔE and SSIM only measure resampling and edge losses. They are not accuracy, and v0 scores almost perfectly on them because it is a plain rescale.

| photo | method | ΔE00 mean | ΔE00 p95 | SSIM | covered | sil_iou body | sil_iou sleeves |
|---|---|---|---|---|---|---|---|
| c_001 | v0 | 0.264 | 1.067 | 0.9903 | 0.9662 | 0.7453 | 0.5947 |
| c_001 | v1_tps | 0.349 | 1.172 | 0.9844 | 0.9622 | 0.8474 | 0.6697 |
| c_001 | v1_affine | 0.300 | 1.088 | 0.9892 | 0.9027 | 0.6947 | 0.6559 |
| c_002 (back) | v0 | 0.130 | 0.472 | 0.9948 | 0.9636 | 0.7063 | 0.5204 |
| c_002 | v1_tps | 0.273 | 0.889 | 0.9837 | 0.9767 | 0.9832 | 0.6087 |
| c_002 | v1_affine | 0.271 | 0.889 | 0.9835 | 0.9753 | 0.9553 | 0.5768 |
| c_003 | v0 | 0.456 | 1.882 | 0.9852 | 0.9149 | 0.6778 | 0.4859 |
| c_003 | v1_tps | 0.551 | 2.462 | 0.9831 | 0.6585 | 0.8983 | 0.7684 |
| c_003 | v1_affine | 0.537 | 2.302 | 0.9838 | 0.6638 | 0.8876 | 0.7492 |
| c_004 | v0 | 0.436 | 2.367 | 0.9927 | 0.9538 | 0.6880 | 0.5111 |
| c_004 | v1_tps | 0.877 | 4.154 | 0.9748 | 0.9680 | 0.9732 | 0.6498 |
| c_004 | v1_affine | 0.874 | 4.220 | 0.9751 | 0.9453 | 0.8965 | 0.6394 |
| c_005 | v0 | 0.694 | 3.296 | 0.9952 | 0.9788 | 0.6434 | 0.4561 |
| c_005 | v1_tps | 1.649 | 7.128 | 0.9775 | 0.9147 | 0.9627 | 0.6899 |
| c_005 | v1_affine | 1.639 | 7.210 | 0.9798 | 0.9247 | 0.8258 | 0.6792 |
| viton_0 | v0 | 0.698 | 4.682 | 0.9893 | 0.9833 | 0.8087 | 0.6225 |
| viton_0 | v1_tps | 1.149 | 5.459 | 0.9692 | 0.9300 | 0.9559 | 0.7618 |
| viton_0 | v1_affine | 0.989 | 4.939 | 0.9789 | 0.9164 | 0.8821 | 0.7537 |
| viton_1 | v0 | 0.924 | 3.775 | 0.9846 | 0.9896 | 0.8042 | 0.7620 |
| viton_1 | v1_tps | 1.987 | 8.122 | 0.9356 | 0.9772 | 0.8668 | n/a (no sleeves found) |
| viton_1 | v1_affine | 2.010 | 8.086 | 0.9474 | 0.8889 | 0.8106 | n/a |
| viton_2 | v0 | 0.270 | 0.702 | 0.9930 | 0.9906 | 0.6432 | 0.5061 |
| viton_2 | v1_tps | 0.402 | 1.050 | 0.9845 | 0.9162 | 0.8960 | 0.7975 |
| viton_2 | v1_affine | 0.404 | 1.033 | 0.9855 | 0.8681 | 0.7064 | 0.7702 |
| viton_3 (sleeveless) | v0 | 0.107 | 0.315 | 0.9987 | 0.9810 | 0.8707 | 0.7903 |
| viton_3 | v1_tps | 0.295 | 0.714 | 0.9950 | 0.7462 | 0.9057 | n/a |
| viton_3 | v1_affine | 0.318 | 0.701 | 0.9920 | 0.7371 | 0.8878 | n/a |

**c_003 colour regions** (k-means clusters of the photo):

| region | share | v0 ΔE00 | v1_tps ΔE00 |
|---|---|---|---|
| teal #183432 | 0.5129 | 0.383 | 0.315 |
| white #e9eaf2 | 0.3518 | 0.381 | 0.316 |
| light grey (stripe edges) #bdc5cf | 0.1214 | 0.761 | 0.959 |
| mid grey (thin lines) #687579 | 0.0139 | 2.183 | 7.492 |

Thin lines lose the most with v1 (splat, erosion and resampling). On c_001 the thin white print edges go from 3.55 to 12.66.

**c_003 colour-block boundary** (`c003_colour_boundary.json`, as a fraction of panel height):
- v0 front texture: 0.469.
- v1 front texture: 0.522.
- v1 back texture (print-free, from the front photo): 0.376.

The boundary survives in both front textures. On the assumed back it sits about 0.15 of the panel height too high, because the stripe band is treated as print.

**Filled fractions:**
- c_003 v1: front 0.005, back 0.008, sleeves 0.404 and 0.055.
- c_005 v1: front and back about 0.08, sleeves 0.62 and 0.55.
- c_002 v1: sleeves about 0.48.

The sleeves are high because the photo covers only half of each sleeve panel; the rest is mirrored.

**Resolution used:**

| photo | own px/cm | output px/cm |
|---|---|---|
| c_001 | 11.49 | 11.49 |
| c_002 | 5.14 | 5.14 |
| c_003 | 11.22 | 11.22 |
| c_004 | 2.02 | 5.0 (upsampled, flagged) |
| c_005 | 1.78 | 5.0 (upsampled, flagged) |

v0 always uses 10 px/cm, but c_004 and c_005 hold only about 2 px of real detail per cm.

## 7. Figures
`fig_<photo>.jpg`:
- top row: the photo, v0 re-projection, v0 ΔE map, v1 re-projection, v1 ΔE map;
- middle row: v0 panels as a flat preview;
- bottom row: v1 panels.

Per photo, `v0/<photo>/` and `v1_tps/<photo>/` hold the textures, metadata, `flat_preview.jpg` and `reproj_error_map.jpg`; v1 also has `reprojected_photo.jpg` and `side_by_side.jpg`. Total size is about 12 MB.

## 8. What worked and what did not
**Worked:**
- **Front panel from the torso with TPS:** body sil_iou 0.87-0.98 for v1 against 0.64-0.87 for v0, on all 9 photos.
- **Region separation:** v0 puts the torso, sleeves and even arm fabric inside the front panel, and its sleeve textures contain torso content; v1 does not.
- **TPS against affine-only:** for example c_001 body 0.847 against 0.695, and c_005 0.963 against 0.826.
- **Clean panels:** no transparent holes inside any panel, and no background-coloured edges (v0 shows them on viton_3).
- **Colour block:** the c_003 boundary is kept in the front texture.
- **Other paths:** the back-from-back-photo path works on c_002, the two-photo path runs, and sleeveless garments get a plain-colour sleeve with a note.

**Weak:**
- **c_003 coverage only 0.66:** the photo is cropped at neck and hem, and the hem is estimated from the chest width, so lower photo pixels fall outside the panel.
- **On-person photos (c_001, c_003, c_005):** the hem and neck are estimated, so panel proportions follow the chest width, not the real garment length. The print on the oversized c_001 is stretched wider.
- **Print removal for the assumed back leaves faint ghosts:** c_001, c_004, and "whatever" on the c_003 back. It also misplaces the c_003 stripe band.
- **Mirrored sleeve halves:** without a second photo they show a V-shaped crease from mirrored fold shading.
- **Sleeve orientation:** left/right is not yet verified in CLO. It matters only for printed sleeves.
- **Thin lines** (stripes, fine print edges) lose colour accuracy.
- **No front/back from P16:** P16 was not finished, so only c_002 is known to be a back view.

## 9. Issues
- **P06 landmarks:** the armpits worked on all 9 photos (convexity defect). The other landmarks were noisy: `neck_left == neck_dip` on c_004, and a cuff or sleeve polygon was missing on one side for c_001, c_002, c_003 and c_005.
- **VITON sample:** two of the first four rows are sleeveless, so the sample is small.
- **Disk:** 1-2 GB free during the run. Outputs are kept small (12 MB) and the affine images were not kept.
- **JSON:** numpy booleans in the notes needed a default hook in the metadata writer (fixed).

## 10. Recommendation
1. Keep v1 as the default (it falls back to v0 on error). Wire `garment_mask`, `view` (from P16) and `on_person` into `run_product_ingestion.py`.
2. For on-person or cropped photos, treat the panel proportions as an assumption and say so; they are recorded in `assumptions`.
3. Improve print removal before relying on the assumed back of a printed garment: pin the colour-block boundary to the front's and use a larger feather.
4. For the paper, quote sil_iou, covered, `filled_fraction` and the figures as the evidence. Do not quote ΔE or SSIM as accuracy; they are round-trip losses.

## 11. What CLO needs to place these maps 1:1 (P20, waiting for the user)
- **Placement:** one fabric per panel, or a placed graphic, at `mm_per_px`. The texture (size `texture_size_mm`) sits with its top-left at the panel point `origin.panel_xy_cm` (xmin, ymax) and covers the pattern 1:1.
- **Why today's Step 3 cannot do it:** it tiles one swatch over one shared fabric, and the panels overwrite each other, so the plugin change in `questions.md` Q6 is required.
- **Alpha and seams:** alpha is 0 outside the panel polygon. There is no seam-allowance margin.
- **Assumptions to keep in mind:** the back made from the front photo and the mirrored sleeve halves are assumptions. Check sleeve left/right orientation in CLO.

## 12. Not done
- A 3D-style preview (needs CLO or a mesh).
- Wiring into the runner (the orchestrator's file).
- A true two-photo test with front and back of the same garment.
- Better print removal.
- Several densities or a fabric-grain fill.
- A learned landmark detector for on-person photos.
