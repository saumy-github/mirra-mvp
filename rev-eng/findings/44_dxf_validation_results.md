# DXF validation results (lane AT)

*Status: tool written and run read-only; static, no CLO run*
*Date: 2026-10-29*
*Tool: scripts/dxf_validate.py (stdlib, `python -I scripts/dxf_validate.py [--json] [--tol 0.01] FILE_OR_DIR...`; exit 1 if any FAIL)*
*Basis: findings/32 section 7 checklist; units per findings/35 (`$INSUNITS` read, `UNITS:` text is not the unit source).*

## 1. What the validator checks

| Check | Rule | Severity |
|---|---|---|
| structure | SECTION/ENDSEC/EOF, non-empty, integer group codes | FAIL (no EOF/ENTITIES), WARN |
| header | `$ACADVER` AC1009 expected | WARN if other |
| units | `$INSUNITS` absent or 4 = scale 1; 1/5/6 = 25.4/10/1000 (WARN, only valid if coords really in that unit); other values = 1.0 | PASS/WARN |
| pieces | one per BLOCK (INSERT in ENTITIES), else top-level geometry | FAIL if none |
| boundary | closed POLYLINE on layer 1: >=3 vertices, closed flag (70 bit 1) or first/last gap < tol (0.01 mm default; 0x82703D8 value still unknown) | FAIL |
| dup_last | closed flag AND repeated first vertex | WARN |
| finite | NaN/inf coordinates | FAIL |
| size | piece bbox in mm after unit scale, 50-2000 mm longest side | WARN |
| grain | exactly one layer-7 LINE (or 2-vertex POLYLINE) | WARN |
| notch / curve / turn | layer 4,80-83 / 3 / 2 POINTs present | WARN |
| layers | non-numeric or undecoded layer names (reader parses layer name to int) | WARN |
| ignored entities | SPLINE, ELLIPSE, DIMENSION, SOLID, LWPOLYLINE, etc. (outside jump-table handlers) | WARN |
| annotations | per piece TEXT PIECE NAME / SIZE / QUANTITY; file-wide UNITS / SAMPLE SIZE | WARN |

Validator assumption corrected against the references (fixed in the tool, not here): the reference puts the file-level header TEXT (STYLE NAME, SAMPLE SIZE, UNITS: METRIC, AUTHOR, VERSION ...) as top-level ENTITIES next to the INSERT, and the per-piece TEXT (PIECE NAME, SIZE, QUANTITY) inside the BLOCK. Also the BLOCK record itself must not be counted as an entity (it produced a false layer-name warning in the first run).

## 2. Results

Files scanned: 4 reference + 40 newest generated (cap 40) = 44. The 40 generated are all under `product_ingestion/output/` (no `output/` dir at repo root exists). Pipeline writes there as `c_<id>/s_<id>/<run>/panels/dxf/` (newer) and `c_001-s_00N-00M/panels/dxf/` (older).

| Group | Files | Result |
|---|---|---|
| `product_ingestion/clo_block/reference_dxf/*.dxf` (back, front, sleeve_left, sleeve_right) | 4 | PASS 4 |
| Newest layout `output/c_001..c_005/s_001/001/panels/dxf/` (R12 AC1009 writer, step_05_3) | 20 | WARN 20 |
| Older layout `output/c_001-s_001-004 .. -007`, `c_001-s_002-002` (AC1024, layers CutLine/GrainLine/Notch/Text, LWPOLYLINE-style, no BLOCKs) | 20 | FAIL 20 |

Total PASS 4, WARN 20, FAIL 20.

Reference bboxes (mm, $INSUNITS absent): front 580.2 x 718.6, back 580.2 x 718.6, sleeves 490.3 x 245.1. Generated newest: front/back 520 x 710 (nominal), sleeves 436 x 316.2; all in range.

### Older layout FAIL reasons (all 20 identical)
- `boundary`: no POLYLINE on layer 1. Geometry sits on named layers (`CutLine`, `GrainLine`, `Notch`, `Text`) at top level, `$ACADVER AC1024`. Per findings/32 section 2 the reader parses the layer name as an integer, so these pieces would be empty and dropped. These are superseded by the step_05_3 writer; do not use them for CLO import.

### Newest layout WARN reasons (all 20 identical, no FAIL)
1. No per-piece TEXT `PIECE NAME:`, `SIZE:`, `QUANTITY:`. The writer emits one free TEXT `"front_panel s_001"` on layer 1, which matches no reader key.
2. No file-level `UNITS: METRIC` and no `SAMPLE SIZE:` TEXT (reference has both at top-level ENTITIES).
3. All structural checks PASS: closed layer-1 POLYLINE (flag 70=1, no duplicate last vertex), `$INSUNITS 4` (scale 1), AC1009, 1 grainline on layer 7, layers 2/3/4/8 present, finite coordinates, sane size.

## 3. Pipeline writer vs reference (checks it fails or differs on)

| Item | Reference | step_05_3 writer |
|---|---|---|
| Per-piece annotations | `PIECE NAME: 1`, `SIZE: M`, `QUANTITY: 1` | one unkeyed label; FAIL-class gap (WARN in tool, unverified whether the reader requires them) |
| File-level TEXT | STYLE NAME, CREATION DATE/TIME, AUTHOR, PRODUCT, VERSION, SAMPLE SIZE, UNITS: METRIC at top-level | none |
| Header | `$DWGCODEPAGE ANSI_1252`, `$EXTMIN/$EXTMAX 1e20`, `$LIMMIN/$LIMMAX`, `$TDCREATE`, no `$INSUNITS`/`$MEASUREMENT` | `$INSUNITS 4`, `$MEASUREMENT 1`, real extents (benign: scale stays 1.0) |
| Layer 14 | closed POLYLINE copy of the outline plus 112 vertex TEXT labels (`# -1`) on layers 1 and 14 | absent |
| Layers 84/85/87 | 1 / 4-8 / 1 allowance polylines | absent unless seam allowance requested (84 only) |
| Layer 8 | 8-36 POLYLINEs plus 16 TEXT | 4 POLYLINEs, no TEXT |
| Layer 4 notch | POINT z=7, group 50 angle | same form (matches) |
| Layer 3 curve points | 144-204 | 66-134 (matches pattern) |

## 4. Recommendations for `product_ingestion/clo_block/step_05_3_clo_dxf_writer.py` (not applied)

1. Replace the label at line ~279 (`text_entity(... f"{piece} {label}")`) with the keyed grammar inside the BLOCK on layer 1: `PIECE NAME: <name>`, `SIZE: <label>`, `QUANTITY: 1` (three TEXT entities). Highest value, closes the only gap vs the checklist.
2. After the INSERT in ENTITIES add top-level layer-1 TEXT: `STYLE NAME: <style>`, `SAMPLE SIZE: <label>`, `UNITS: METRIC`, optionally `AUTHOR:`, `VERSION:`, `ANSI/AAMA VERSION: 1.0.0`.
3. Keep `$INSUNITS 4` (scale 1.0, safe), or drop `$INSUNITS`/`$MEASUREMENT` to mirror the reference exactly; never emit 1/5/6 while coordinates are mm. Add `$DWGCODEPAGE ANSI_1252` for parity.
4. Keep the boundary closed flag and no duplicate last vertex (already correct).
5. Optional parity (not proven required): layer 14 outline copy, layer 85/87 allowance polylines, per-vertex `# -1` TEXT. Test the import with items 1-2 first before adding these.
6. Stop shipping or loading the old `c_001-s_00N-00M` AC1024 files; they will import as empty pieces.

## 5. Caveats
- Annotations are WARN not FAIL: findings/32 section 3 [I] says a missing `PIECE NAME` is not rejected in the code found; not verified with a run.
- The tolerance (0x82703D8) is unknown; 0.01 mm is an assumption. Generated boundaries use the closed flag so are tolerance-independent.
- Entities considered "handled" follow the jump-table set; LWPOLYLINE is flagged as dropped though the vendored library lists the string (unverified).
