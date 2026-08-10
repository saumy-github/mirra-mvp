# Wiring the CLO block into mirra-mvp

Everything below has been run against a copy of the repo. The seam manifest the
new generator emits drives `seams.py` to produce wiring **identical to
`DEFAULT_SEAMS`**, so `seams.py`, `step_09_create_seams.py` and
`step_06_read_edges_and_slots.py` need no changes at all.

## 1. Drop the files in

```
product_ingestion/
  clo_block/
    __init__.py
    clo_draft.py
    clo_draft_config.py
    clo_dxf_writer.py
  panel_generation_clo.py          <- drop-in replacement for panel_generation.py
```

Keep `clo_block/` importing `curve_segment` from the parent package, which it
already does. Nothing else in `product_ingestion/` is touched.

## 2. Switch one import

`product_ingestion/run_product_ingestion.py`, line 48:

```python
-from panel_generation import generate_panels
+from panel_generation_clo import generate_panels
```

`generate_panels(measurements, panels_dir)` has the same signature and returns
the same `PanelGenerationResult` fields, so line 340 and the
`texture_projection` call at line 363 are unchanged.

To pass the size id through to the DXF block names (CLO shows them in the
pattern list, which makes debugging much easier), the call at line 340 becomes:

```python
panel_result = generate_panels(measurements, panels_dir, size_label=size_id)
```

## 3. Units are handled for you

Three conventions meet in this pipeline and the adapter reconciles them:

| consumer | unit | who supplies it |
|---|---|---|
| sizes collection | cm | Mongo |
| `CloTShirtDraft` | mm | fitted constants are in mm |
| `texture_projection` | cm | `PX_PER_CM = 10` |
| DXF for CLO | mm | `$INSUNITS = 4`, CLO imports at scale 0.1 |

`PanelGenerationResult.layouts` comes back in **centimetres**, exactly as the
old generator returned, so `texture_projection.py` and `panel_export_svg.py`
work untouched. The DXF is written in mm directly from the draft.

Verified: `ezdxf.readfile()` on the generated DXF reports `units == 4`, so
`step_04_import_patterns._recommended_import_scale()` returns `0.1` and the
bbox sanity check (`50 <= w,h <= 3000` mm) passes at 580 x 719 mm.

## 4. Measurement conventions — read this before trusting the numbers

`garment_measurements.py`'s docstrings do not describe what `panels.py`
actually does. The docstring says `shoulder_width` is "half shoulder span";
`panels.py` line 287 computes `center_x + shoulder_width / 2`, so it is the
**full** span. Same for `half_chest_width`, which is used as the full flat
panel width. The adapter follows the code, since that is what the seeded sizes
were authored against:

| sizes field (cm) | meaning in code | maps to (mm) |
|---|---|---|
| `half_chest_width_cm` | full flat panel width | `half_chest_width = x*10/2` |
| `shoulder_width_cm` | full shoulder span | `shoulder_half_width = x*10/2` |
| `neck_width_cm` | full neck opening | `neck_half_width = x*10/2` |
| `bicep_width_cm` | folded half-girth | `bicep_full_width = x*2*10` |
| `sleeve_length_cm` | cuff to underarm | `underarm_to_wrist = x*10` |
| — | — | `hem_half_width` derived, ratio 0.9307 |
| — | — | `wrist_full_width` derived, ratio 0.7840 |

## 5. Add two fields to the sizes collection

`hem_width_cm` and `wrist_width_cm`, both full flat widths. Until they exist
the adapter falls back to the CLO reference block's ratios, which means every
size gets the same side-seam and sleeve taper. A straight-sided tee and a
tapered one are indistinguishable in the current schema — that is precisely why
the old panels came out boxy.

`generate_panels(..., hem_width_cm=..., wrist_width_cm=...)` accepts them
directly, and `clo_block_from_size_doc()` reads `hem_width_cm` /
`wrist_width_cm` off the document when present.

## 6. The seeded sizes will not produce wearable sleeves

Run this before anything else:

```python
from panel_generation_clo import recommend_bicep_width_cm
recommend_bicep_width_cm(measurements)
```

All six seeded sizes fail. Every one has a bicep too narrow for the armhole it
has to fill, by a consistent ~3.8 cm:

| size | armhole total | `bicep_width_cm` now | recommended | or set `armhole_depth_cm` to |
|---|---|---|---|---|
| s_001 | 50.14 cm | 18.0 | **21.8** | 19.8 |
| s_002 | 48.20 cm | 17.0 | **20.9** | 18.7 |
| s_003 | 54.66 cm | 20.0 | **23.8** | 21.9 |
| s_004 | 59.19 cm | 22.0 | **25.7** | 23.9 |
| s_005 | 46.26 cm | 16.0 | **20.1** | 17.5 |
| s_006 | 45.02 cm | 15.0 | **19.6** | 16.1 |

The solver still converges on the seeded numbers — it just does so by making
the cap 0.41 to 0.52 of the bicep width, against the CLO reference's 0.244.
That is a spike, not a sleeve. A `UserWarning` fires on every one.

This is not a new bug. The old generator had the same inconsistency and hid it:
`cap_height_max_frac = 0.95` simply clamped the binary search and the run
carried on silently. Correcting s_001 to `bicep_width_cm = 21.8` gives a cap
ratio of exactly 0.244 and no warning.

Pick one column and update `mirra_measurements/seed_sizes.py`.

## 7. Regenerate the VTO default panels

`clo_vto/default_panels/dxf/` is gitignored, so those files exist only on
whoever's machine created them. Repoint that folder at generated output:

```bash
python -c "
from product_ingestion.panel_generation_clo import generate_panels, clo_block_from_size_doc
from product_ingestion.garment_measurements import GarmentMeasurements
m = GarmentMeasurements.from_sizes_db('s_001')
generate_panels(m, 'clo_vto/default_panels', size_label='s_001')
"
cp clo_vto/default_panels/edge_manifest.json clo_vto/default_panels/edge_manifest.json.bak
```

Then the existing smoke test still applies:

```bash
python clo_vto/run_clo_vto.py --use-default-panels
```

Remember CLO's `new-project` is async — start from a genuinely fresh project or
step 06's edge-count validation will abort on accumulated patterns.

## 8. What to expect on the first CLO run

- 10 edges per body panel, 5 per sleeve. `validate_edge_counts` in step 06
  passes because the manifest and the DXF agree by construction.
- All 10 seams wire from the manifest exactly as `DEFAULT_SEAMS` does. If the
  sleeves twist, that is a real geometry regression and not a naming problem —
  the indices are verified identical.
- The sleeve should now sit *lower* and rotate *less* than before, because the
  cap is shorter than the armhole rather than 48 mm longer, and because the
  notches pin the below-notch seam lengths to an exact match.

## 9. Two docs to correct while you are in there

`.agent/clo-avatar-vto/seam-edge-mapping.md` states that `sleeve_left` and
`sleeve_right` share identical DXF geometry and that CLO mirrors the right one
at placement time. They are already mirrored in the file:
`sr.x = -sl.x + 9.485` to within 0.0004 mm, and the signed areas have opposite
signs (`-83191.8` vs `+83191.8`). That reflection is the actual reason
`arm-R-front` and `arm-R-back` need `db=True` while the left-sleeve pair does
not. The wiring is right; only the explanation is wrong, and someone reading it
could well "fix" the flags back to broken.

`garment_measurements.py`'s half-versus-full docstrings, per section 4.

## 10. Files that become dead

- `panels.py` — `DynamicPatternGenerator`
- `curve_config.py` — `CurveConfig`, `ArmholeConfig`
- `panel_export_dxf.py` — superseded by `clo_block/clo_dxf_writer.py`
- `tests/test_panel_geometry.py` — asserts the old 8-edge layout and positive
  cap ease; needs rewriting against `clo_block/validate_against_reference.py`

Leave them in place until a CLO run confirms the new panels sew, then delete in
one commit.
