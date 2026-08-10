# clo_block — CLO-compatible parametric t-shirt block

Generates the four t-shirt pattern pieces (front, back, two sleeves) for any
set of measurements, reproducing the drafting logic of CLO 3D's own default
t-shirt block rather than approximating it.

Reverse-engineered from `front_panel.dxf`, `back_panel.dxf`, `sleeve_left.dxf`
and `sleeve_right.dxf` exported from CLO Standalone 2026.0.300, size M.

## Quick start

```bash
python generate_block.py --out ./out/M                      # reproduce CLO size M
python generate_block.py --out ./out/L --half-chest 310 ...  # explicit measurements
python generate_block.py --out ./out/x --from-body \
    --chest-girth 1000 --shoulder-span 470 --back-length 720
```

```python
from clo_draft import CloTShirtDraft
from clo_draft_config import CloBlockMeasurements

draft = CloTShirtDraft(CloBlockMeasurements.clo_default_M())
draft.build()
draft.seam_report()          # every seam length + the ease reconciliation
draft.layouts["front_panel"] # a PieceLayout, same type panels.py produced
draft.notches["sleeve_left"] # sleeve match points with inward-normal angles
```

## What was wrong with the old generator, and why

| | old `DynamicPatternGenerator` | CLO reference | consequence |
|---|---|---|---|
| cap ease | `+3.5 cm`, binary-searched | **−1.27 cm** (−2.25%) | the cap was ~48 mm too long; it had to bubble somewhere |
| ease distribution | 60% crown / 20% per side | **100% above the notches**, zero below | seam crept, sleeve rotated in the armhole |
| notches | none | 4 per sleeve, 1 front / 2 back per panel | nothing forced the sleeve to sit right |
| shoulder seam | 0.5 cm convex crown | **straight** | fake shaping |
| side seam | 0.5 cm waist suppression | **straight taper**, 20.1 mm chest→hem | fake shaping |
| edges per body panel | 8 | **10** (hem and neckline split at centre) | index drift against `edge_manifest.json` |
| back armhole | one S-curve | **two cubics**, split 73.4% down | wrong back armhole shape |
| armhole shape | symmetric hollow, `hollow_depth_frac` | asymmetric single cubic | not reproducible by that parameterisation |

The +3.5 cm figure is the correct industry number for a **woven, tailored**
set-in sleeve. A jersey t-shirt is the opposite case: the cap is cut short and
stretched into the armhole. That single sign error accounts for most of the
"doesn't look like a real tee" problem.

## The three rules that make it sew

**1. Every curved edge is a single cubic Bezier.** Fitting one to each edge of
the CLO block leaves a max residual under 0.5 mm across all four pieces. The
back armhole is the only two-segment edge. Control points are stored in
`CloDraftConfig` as `(dx, dy)` offsets normalised by the edge's bounding box,
so the curve shears with the box as the block grades — which is what a pattern
grader does by hand.

**2. Cap ease is negative and lives above the notches.** Measured on the
reference:

```
front armhole 289.564 + back armhole 274.297 = 563.861 mm
cap front     284.295 + cap back     266.882 = 551.177 mm
                                       ease = −12.68 mm  (−2.25 %)
```

Split at the notches, all of it sits above them:

| segment | panel | sleeve | mismatch |
|---|---|---|---|
| underarm → front notch | 169.93 | 170.00 | +0.07 |
| underarm → back notch 1 | 169.95 | 169.99 | +0.04 |
| back notch 1 → 2 | 10.00 | 9.99 | −0.01 |
| front notch → shoulder | 119.63 | 114.29 | **−5.34** |
| back notch 2 → shoulder | 94.35 | 86.90 | **−7.45** |

**3. So the cap is solved, not specified.** `cap_height` and `peak_offset` are
the two unknowns; the two constraints are that each cap half equals its
armhole arc times `(1 + ease_fraction)`. A damped 2-D Newton iteration with a
numerical Jacobian solves it in 2–3 steps, no SciPy. Placing the notches the
same arc distance from the underarm on both pieces then makes the below-notch
lengths match automatically.

## Files

| file | role |
|---|---|
| `clo_draft_config.py` | `CloBlockMeasurements` (11 independent dimensions) and `CloDraftConfig` (every fitted constant) |
| `clo_draft.py` | `CloTShirtDraft` — builds four `PieceLayout` pieces, notches, internal lines, grainlines |
| `clo_dxf_writer.py` | AAMA/ASTM R12 writer matching CLO's own layer structure |
| `generate_block.py` | CLI |
| `validate_against_reference.py` | regression test against the source DXFs |
| `curve_segment.py` | unchanged copy of the repo's existing primitives |

## DXF output

The previous exporter wrote an `LWPOLYLINE` on a layer named `CutLine`. Both
are wrong for this target: CLO exports R12 (`AC1009`), where `LWPOLYLINE` does
not exist (it arrived in R14), and AAMA/ASTM identifies content by **numeric**
layer, not by name. This writer reproduces CLO's structure:

| layer | content |
|---|---|
| `1` | closed `POLYLINE` — the sewing line, the boundary CLO reads |
| `2` | `POINT` per turn point (corner between named edges) |
| `3` | `POINT` per curve point |
| `4` | `POINT` per notch, `Z = 7.0`, code `50` = inward-normal angle |
| `7` | `LINE` — grainline |
| `8` | `POLYLINE` — hem folds, chest line, centre line |

Geometry sits in a `BLOCK` named `<index>_<size>` which is `INSERT`ed once at
the origin, again matching CLO. There is **no seam allowance** in the
reference files (layers 84 and 87 duplicate layer 1 to within 0.15 mm), so
`seam_allowance_mm` defaults to 0; setting it writes an offset polyline on
layer 84 rather than moving layer 1.

## Validation

```bash
python validate_against_reference.py /path/to/reference/dxf
```

Currently **57/57 checks within tolerance**. Residuals and why they exist:

- **±0.23 mm** on armhole seam lengths (0.07%): ~0.05 mm is tessellation (CLO's
  DXF is a chord approximation of its own curves), the rest is Bezier fit
  residual. Necklines, shoulders, sides and hems land within 0.03 mm.
- **±0.57 mm** on the two sleeve underarm seams: the reference bows them
  0.57 mm over 138 mm, we draft them straight (`underarm_straight`).
- **±0.04 mm** on back neck and back shoulder landmarks: `equal_shoulder_seams`
  holds the two back offsets equal so the front and back shoulder seams match
  to machine precision, where CLO's own differ by 0.005 mm.
- **±0.35 mm** on notch positions; all sixteen notches land within 0.36 mm.

Piece winding matches the reference on all four pieces (front, back and
`sleeve_left` clockwise; `sleeve_right` counter-clockwise, because it is a
reflection). That last point matters: CLO's `sleeve_right` is **already
mirrored in the DXF**, not mirrored at placement time, which is the actual
reason the `db` direction flags differ between the left and right armhole
seams in `seams.py`. `.agent/clo-avatar-vto/seam-edge-mapping.md` currently
states the opposite and should be corrected.

## Integrating into mirra-mvp

1. Drop this package in as `product_ingestion/clo_block/`. It imports
   `curve_segment` from the parent if present.
2. In `panel_generation.py`, swap `DynamicPatternGenerator` for
   `CloTShirtDraft`. It returns the same `dict[str, PieceLayout]`.
3. Map the existing `GarmentMeasurements` to `CloBlockMeasurements`. Two
   fields are new and two change meaning:
   - **new**: `hem_half_width`, `wrist_full_width`
   - **changed**: `bicep_full_width` is the *unfolded* sleeve width, i.e.
     twice the old `bicep_width`; `sleeve_length` is replaced by
     `underarm_to_wrist`
   - **gone**: cap height is solved, so it must not be an input
4. Regenerate `clo_vto/default_panels/edge_manifest.json` from
   `draft.edge_manifest()`. Edge names and indices are unchanged, so
   `seams.py` keeps working; the manifest gains a `role` field recording what
   each sleeve edge physically is, and a `notches` block.
5. Replace `panel_export_dxf.py` with `clo_dxf_writer.py`.

The five sleeve edge names stay historically rotated relative to their real
roles (`cuff` is an underarm seam, `left_underarm` is the wrist opening) so
that `seams.py`'s by-name lookups keep working unchanged.

## Known gaps

- **Grading is unverified.** Everything here was fitted to exactly one size.
  The grade sweep in the test holds ease at −2.267% and shoulder seam match at
  0.0000 from S to 3XL, but whether CLO itself holds the 170 mm notch distance
  absolute or scales it is unknown. `notch_absolute_mm` switches between the
  two. Exporting the same block from CLO at S and XL would settle this, plus
  whether the 0.4 shoulder slope and the −2.25% ease are grade-invariant.
- `from_body()` is a convenience seed applying size M's proportions to a new
  chest, not a fitted grading rule.
- Only the crew-neck set-in-sleeve block is covered. Raglan, V-neck and
  drop-shoulder need their own fitted constants.
