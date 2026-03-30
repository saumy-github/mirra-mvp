# VTO Pattern Geometry — Status, Fixes & Roadmap

**Last updated:** 2026-03-28
**Branch:** `clothingfixes`
**Relevant files:** `product_ingestion/panels.py`, `product_ingestion/panel_export_dxf.py`, `product_ingestion/garment_measurements.py`, `vto/clo_automation_steps/step_09_create_seams.py`

---

## 1. Background — What This System Does

The pipeline takes garment measurements from a MongoDB size document (`s_001`, etc.), generates flat 2D pattern pieces (front panel, back panel, sleeve left, sleeve right), exports them as DXF files, and imports them into CLO3D via REST API for virtual try-on simulation.

Pattern pieces are described as `PieceLayout` objects — ordered lists of named `PieceEdge` objects (straight, cubic bezier, or S-curve). Edges carry full control-point data so they can be sampled at any resolution.

---

## 2. Raw DB Record (s_001) — Field Interpretations

```json
{
  "size_id": "s_001",
  "half_chest_width_cm": 52.0,
  "garment_length_cm": 71.0,
  "shoulder_width_cm": 46.0,
  "neck_width_cm": 18.0,
  "neck_depth_front_cm": 9.0,
  "neck_depth_back_cm": 2.5,
  "sleeve_length_cm": 21.0,
  "bicep_width_cm": 18.0,
  "armhole_depth_cm": 24.0,
  "seam_allowance_cm": 1.0,
  "fit_type": "regular"
}
```

### Confirmed interpretations

| Field | Value | Meaning | Convention |
|---|---|---|---|
| `half_chest_width_cm` | 52 cm | Width of ONE body panel (front or back) | Half-girth — front+back = 104 cm full chest |
| `shoulder_width_cm` | 46 cm | Full shoulder span | Used as full width, halved in code for per-side geometry |
| `bicep_width_cm` | 18 cm | **Flat seam-to-seam (half-girth) of folded sleeve** | Half-girth — must be `× 2 = 36 cm` for unfolded pattern piece |
| `armhole_depth_cm` | 24 cm | **Vertical depth** of armhole opening on body panel | NOT perimeter — used as Y-axis distance from shoulder line to underarm |
| `sleeve_length_cm` | 21 cm | Cuff hem to underarm (worn length) | Absolute, no halving |
| `garment_length_cm` | 71 cm | Full torso hem to shoulder | Absolute |

### Why bicep_width × 2

`bicep_width = 18 cm` is the flat measurement of a folded sleeve — half the tube circumference. The sleeve pattern piece represents the fully **unfolded** tube, so its width = `18 × 2 = 36 cm`. Using 18 cm (or 9 cm as the old bug did) produces an impossibly narrow sleeve. Using `36 cm` gives realistic short-sleeve proportions.

---

## 3. Problems Found & Fixes Applied

### 3.1 Bug: Sleeve Width — "Leaf Shape" (FIXED)

**Root cause:**
`panels.py` computed `sleeve_width = m.bicep_width / 2 = 9 cm` in both `_build_cap_pair` and `generate_sleeve`. This is half of the half-girth — a quarter of the actual circumference. The binary search then had to grow the cap to an extreme height to reach the required 52 cm arc length over a 9 cm base, producing a tall narrow "leaf" shape instead of a rectangle with a shallow cap.

**Fix applied:**
Changed both occurrences to `sleeve_width = m.bicep_width * 2 = 36 cm`.

**Result after fix:**

| Metric | Before | After |
|---|---|---|
| Sleeve width | 9 cm | 36 cm |
| Cap height (binary search) | very large (leaf) | 12.82 cm |
| Underarm straight portion | tiny | 8.18 cm |
| Total piece height | distorted | 24.2 cm |
| Ease | not matching | 3.48 cm (target 3.5 cm) ✅ |

**Files changed:** `product_ingestion/panels.py` lines 235, 400–403

---

### 3.2 Bug: DXF Format — CLO Rejected Import (FIXED)

**Root cause:**
The DXF exporter wrote one SPLINE entity per logical edge (8 separate entities for body, 5 for sleeve). CLO's `ImportDXF` requires a single closed boundary polygon per file (DXF-AAMA convention). Multiple separate entities were treated as internal baselines → 0 patterns imported.

**Fix applied:**
Changed `_add_cutline_boundary` in `panel_export_dxf.py` to write a single closed LWPOLYLINE per piece.

**Files changed:** `product_ingestion/panel_export_dxf.py`

---

### 3.3 Bug: Seam Index Mismatch — Only 2–3 Seam Lines Appearing (FIXED — MVP level)

**Root cause:**
After switching to a dense LWPOLYLINE (`layout.polygon()` with `n_fit=24`), CLO created one "line" per vertex pair:
- Body panel: 209 vertices → 208 CLO lines
- Sleeve: 50 vertices → 49 CLO lines

The seam manifest uses indices 0–7 for body and 0–4 for sleeve (matching logical edges). With the dense polygon, CLO line `3` fell in the middle of the hem edge's interpolated vertices — not on the shoulder edge. All seam connections landed in the wrong places, producing only 2–3 visible stitch lines in CLO.

**MVP fix applied:**
Changed `_add_cutline_boundary` to use **corner-only vertices** — one vertex per logical edge start point. This gives:
- Body panel: 8 CLO lines (indices 0–7 = logical edges 0–7) ✅
- Sleeve: 5 CLO lines (indices 0–4 = logical edges 0–4) ✅

All 10 seams now connect correct full edges.

**Files changed:** `product_ingestion/panel_export_dxf.py`

**Limitation (see Section 4):** The corner-only DXF sends angular shapes to CLO — straight lines between corners instead of smooth curves. The sleeve cap becomes an inverted V in CLO, not a bezier arc. This is the **permanent fix target**.

---

### 3.4 Bug: Scale Warning in Step 5 (FIXED)

**Root cause:**
`step_05_verify_patterns.py` computed `scene_avatar_height_est = avatar_height_export_cm * avatar_scale_used`. This multiplied the avatar height (already in cm) by the CLO import scale (e.g. 10.0), producing `178 × 10 = 1780 cm` instead of `178 cm`. The panel/avatar ratio was `0.040` instead of `~0.40`.

**Fix applied:**
Changed to `scene_avatar_height_est = avatar_height_export_cm` directly.

**Files changed:** `vto/clo_automation_steps/step_05_verify_patterns.py`

---

## 4. Current State (as of 2026-03-28)

### What works
- ✅ 4 patterns import correctly into CLO (DXF-AAMA single LWPOLYLINE)
- ✅ Sleeve width is 36 cm (correct unfolded circumference)
- ✅ Sleeve cap arc matches armhole arc + ease (3.48 cm, target 3.5 cm)
- ✅ All 10 seams created with correct logical edge indices
- ✅ Scale diagnostic ratio corrected (~0.40)
- ✅ DXF files regenerated: `product_ingestion/output/c_001-s_001-003/panels/dxf/`

### What is still limited

| Issue | Status | Impact |
|---|---|---|
| DXF has angular corners only (no curves) | Accepted for MVP | Sleeve cap is inverted-V in CLO, not smooth arc |
| SVG shows smooth curves; DXF does not | Known gap | SVG is design preview only, not what CLO receives |
| Slot arrangement fallback active | Pre-existing | Patterns positioned via direct offsets, not named slots |
| Export/save step (step 11) disabled | Pre-existing | Manual export required after simulation |

### Sleeve geometry (current correct values)

```
Cuff:            (0, 0) → (36, 0)       width = 36 cm
Right underarm:  (36, 0) → (36, 8.18)   straight, 8.18 cm
Cap front:       (36, 8.18) → (18, 24.2) straight line (corner-only DXF)
Cap back:        (18, 24.2) → (0, 8.18)  straight line (corner-only DXF)
Left underarm:   (0, 8.18) → (0, 0)     straight, 8.18 cm

Cap height (binary search):  12.82 cm
Apex above cuff:             24.20 cm
Armhole arc (per sleeve):    48.48 cm
Sleeve cap arc:              51.95 cm
Ease:                         3.48 cm ✅
```

### Body panel armhole geometry

```
Underarm point: (52.0, 47.0)
Shoulder point: (49.0, 71.0)
Chord:          24.19 cm
S-curve arc:    24.23 cm per side (nearly vertical armhole)
```

---

## 5. The Core Tension — Shape vs Seaming

This is the key architectural conflict for the permanent fix.

### The problem

CLO creates **one line per vertex pair** in a closed LWPOLYLINE. This means:

| DXF mode | CLO lines | Seam index 3 maps to | Shape quality |
|---|---|---|---|
| Dense (209 vertices) | 208 lines | 4th segment of the hem edge (wrong!) | Smooth bezier curves ✅ |
| Corner-only (8 vertices) | 8 lines | shoulder edge (correct ✅) | Angular straight lines ❌ |

You cannot have both correct seaming AND smooth shapes with the current single-entity approach.

### Why dense DXF breaks seaming

`create_seam(pattern_a, line_a, pattern_b, line_b)` in CLO sews **exactly** the two specified segments — it does not auto-detect or extend to the full logical edge. Specifying any line within a dense edge range produces a tiny stitch fragment, not a full edge seam.

---

## 6. Permanent Fix Plan

### Phase 1 — Restore curved shapes (dense DXF) with computed seam indices

**Approach:**
Revert `_add_cutline_boundary` to dense polygon (`layout.polygon(n_per_segment=n_fit)`). Compute the correct CLO line index for the **start** of each logical edge by tracking cumulative vertex counts.

**Seam index table for body panel (n_fit=24)**

| Edge idx | Edge name | Vertex count contributed | CLO line start |
|---|---|---|---|
| 0 | hem (straight) | 2 | **0** |
| 1 | right_side (bezier, 1 seg) | 23 | **1** |
| 2 | right_armhole (s_curve, 2 seg) | 46 | **24** |
| 3 | right_shoulder (bezier, 1 seg) | 23 | **70** |
| 4 | neckline (bezier, 1 seg) | 23 | **93** |
| 5 | left_shoulder (bezier, 1 seg) | 23 | **116** |
| 6 | left_armhole (s_curve, 2 seg) | 46 | **139** |
| 7 | left_side (bezier, 1 seg) | 23 | **185** |

**Seam index table for sleeve (n_fit=24)**

| Edge idx | Edge name | Vertex count contributed | CLO line start |
|---|---|---|---|
| 0 | cuff (straight) | 2 | **0** |
| 1 | right_underarm (straight) | 1 | **1** |
| 2 | cap_front (bezier, 1 seg) | 23 | **2** |
| 3 | cap_back (bezier, 1 seg) | 23 | **25** |
| 4 | left_underarm (straight) | 1 | **48** |

**Problem with this alone:**
`create_seam` stitches only the start segment, not the full edge. The shoulder seam (23 segments) would be stitched at only one point.

### Phase 2 — Multi-segment seam calls

For each seam, call `create_seam` for **every segment** in the edge range, not just the first. This means:
- Shoulder seam (23 segments): 23 API calls
- Side seam (23 segments): 23 API calls
- Armhole seam (46 segments): 46 API calls per side

Total calls: ~300 seam calls vs current 10. CLO's REST queue can handle this but it needs testing.

Alternatively, investigate whether CLO's `create_seam` accepts a line **range** instead of a single index — check `PATTERN_API.json` for any `CreateSeamRange` or similar endpoint.

### Phase 3 — Make indices dynamic

Instead of hardcoding the CLO line offsets, compute them at runtime from the polygon vertex counts:

```python
def compute_clo_line_indices(layout, n_fit=24):
    """Return dict of edge_index -> CLO line start index."""
    indices = {}
    cumulative = 0
    for i, edge in enumerate(layout.edges):
        indices[i] = cumulative
        pts = edge.points(n_fit)
        # First edge contributes all points; subsequent edges skip the shared first
        new_pts = len(pts) if i == 0 else len(pts) - 1
        cumulative += new_pts
    return indices
```

This function should live in `seams.py` or `step_06_read_edges_and_slots.py` and be called before seam creation. The seam manifest then stores logical edge indices (0–7) and the runtime lookup translates them to actual CLO line indices.

### Phase 4 — Update edge_manifest.json

The manifest currently stores logical indices 0–7. After Phase 3, it should either:
- Store logical indices (0–7) with a runtime mapping (preferred — decoupled from n_fit)
- Store actual CLO line indices (fragile — breaks if n_fit changes)

Logical indices + runtime mapping is the correct long-term design.

---

## 7. Files Reference

| File | Role | Status |
|---|---|---|
| `product_ingestion/panels.py` | Generates PieceLayout with all edges | ✅ Fixed (sleeve_width * 2) |
| `product_ingestion/panel_export_dxf.py` | Exports DXF for CLO | ⚠️ Corner-only (MVP fix) |
| `product_ingestion/panel_export_svg.py` | Exports SVG preview | ✅ Shows smooth curves (design intent) |
| `product_ingestion/garment_measurements.py` | GarmentMeasurements dataclass | ✅ Documented conventions |
| `product_ingestion/curve_segment.py` | PieceEdge, PieceLayout, polygon() | ✅ Unchanged |
| `vto/clo_automation_steps/step_06_read_edges_and_slots.py` | Reads CLO edge counts | ✅ Updated for LWPOLYLINE |
| `vto/clo_automation_steps/step_09_create_seams.py` | Calls create_seam API | ✅ Unchanged (uses manifest indices) |
| `vto/clo_automation_steps/step_05_verify_patterns.py` | Scale validation | ✅ Fixed scale calculation |
| `product_ingestion/output/c_001-s_001-003/panels/dxf/` | Generated DXF files | ✅ Regenerated with correct geometry |
| `product_ingestion/output/c_001-s_001-003/panels/svg/` | Generated SVG previews | ✅ Regenerated (shows smooth curves) |

---

## 8. Testing Checklist (before permanent fix)

- [ ] Run `python vto/run_vto.py` with `c_001-s_001-003` and confirm all 10 seams connect visually in CLO
- [ ] Verify sleeve shape in CLO 3D view (inverted-V cap is expected until permanent fix)
- [ ] Run 150-step simulation and confirm fabric drapes without exploding
- [ ] After permanent fix (Phase 1–3): confirm smooth cap curve visible in CLO
- [ ] After permanent fix: confirm seams still cover full edges (not just start segments)
- [ ] Check `PATTERN_API.json` for `CreateSeamRange` or multi-line seam endpoints

---

## 9. What SVG vs DXF Currently Shows

| | SVG | DXF (CLO) |
|---|---|---|
| Sleeve cap | Smooth bezier arc | Two straight lines (inverted V) |
| Armhole | Smooth S-curve | Straight line |
| Side seam | Gentle bow (bezier) | Straight line |
| Shoulder | Slight crown curve | Straight line |
| Neckline | Downward arc | Straight line |
| **Purpose** | Design preview only | What CLO actually simulates |

The SVG is the geometric intent. The DXF is the MVP approximation that enables correct seaming. They will converge once the permanent fix (Phase 1–3) is implemented.
