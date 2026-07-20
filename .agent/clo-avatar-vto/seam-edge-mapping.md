# Seam Edge Mapping — Sleeve/Armhole Fix (RESOLVED)

Status: **visually confirmed correct in CLO on 2026-07-20.** All 10 seams —
4 body seams (shoulders + sides, untouched, previously confirmed), 4 armhole
seams, and 2 sleeve tube seams — are sewing cleanly with no twist/crisscross.

Source of truth for indices: `clo_vto/default_panels/edge_manifest.json`
(names) and `clo_vto/native_vto/seams.py::DEFAULT_SEAMS` /
`load_seams_from_manifest()` (which seam connects which named edge, plus the
`da`/`db` direction flags CLO needs).

## Edge layout (as CLO reports it — unchanged throughout this fix)

**front_panel** (pattern index 0) — 10 edges:

| idx | manifest name    | length (CLO units) |
|-----|-------------------|---------------------|
| 0   | right_neckline     | 156.0 |
| 1   | right_shoulder     | 145.8 |
| 2   | right_armhole      | 289.6 |
| 3   | right_side         | 412.8 |
| 4   | right_hem          | 270.0 |
| 5   | left_hem           | 270.0 |
| 6   | left_side          | 412.8 |
| 7   | left_armhole       | 289.6 |
| 8   | left_shoulder      | 145.8 |
| 9   | left_neckline      | 156.0 |

**back_panel** (pattern index 1) — 10 edges:

| idx | manifest name    | length (CLO units) |
|-----|-------------------|---------------------|
| 0   | left_hem           | 270.0 |
| 1   | left_side          | 412.8 |
| 2   | left_armhole       | 274.3 |
| 3   | left_shoulder      | 145.8 |
| 4   | left_neckline      | 114.9 |
| 5   | right_neckline     | 114.9 |
| 6   | right_shoulder     | 145.8 |
| 7   | right_armhole      | 274.3 |
| 8   | right_side         | 412.8 |
| 9   | right_hem          | 270.0 |

**sleeve_left** (pattern index 2) and **sleeve_right** (pattern index 3) —
5 edges each, identical geometry (mirrored at placement, not in the DXF):

| idx | manifest name    | length (CLO units) |
|-----|-------------------|---------------------|
| 0   | cuff               | 138.5 |
| 1   | right_underarm     | 284.3 |
| 2   | cap_front          | 266.9 |
| 3   | cap_back           | 135.3 |
| 4   | left_underarm      | 384.7 |

## The names are misleading — actual geometry (ground truth)

The manifest/seams.py edge *names* are kept as-is (to avoid touching the
by-name lookups everywhere), but **none of the 5 sleeve edge names match
their visual/physical role**. This was established two ways:

1. Length-matching against the body panel armholes (front_armhole=289.6,
   back_armhole=274.3) — `right_underarm`(284.3) and `cap_front`(266.9) are
   within 2–3% of those, `cap_back`(135.3) is 50%+ off from either.
2. **Direct DXF vertex-coordinate analysis** (2026-07-20, authoritative):
   walked the raw closed POLYLINE (92 points) inside
   `sleeve_left.dxf`'s INSERT block (layer `"1"`), computed cumulative
   arc-length around the loop, and matched it against CLO's reported edge
   lengths (they sum to the DXF's total perimeter to within 0.1 unit, so
   the boundary positions are exact, not approximate):

   | cumulative length | vertex (x, y)        | edge boundary |
   |--------------------|-----------------------|----------------|
   | 0.0                | (465.96, 1213.21)     | cuff start / left_underarm end |
   | 138.5              | (408.93, 1338.82)     | cuff end / right_underarm start |
   | 422.8              | (664.05, **1458.34**) | right_underarm end / cap_front start — **topmost point (the peak)** |
   | 689.7              | (899.20, 1338.82)     | cap_front end / cap_back start |
   | 825.0              | (850.31, **1213.21**) | cap_back end / left_underarm start |
   | 1209.7 (= 0.0)     | (465.96, 1213.21)     | loop closes |

   Reading the y-coordinates off this table: `left_underarm` (825.0→1209.7)
   runs between two points that share **y = 1213.21** — it's dead flat. Both
   `cuff` (0→138.5) and `cap_back` (689.7→825.0) are short risers that start
   at that same y = 1213.21 baseline and climb to y ≈ 1338.82. And the peak
   (y = 1458.34, the single highest point in the whole pattern) sits exactly
   at the `right_underarm`/`cap_front` boundary.

   **In plain terms** (matches the flat-bottom/curved-top/straight-sides
   sketch of the pattern):
   - `left_underarm` (edge 4, 384.7) = the flat **wrist opening**, not a seam
     at all — left unseamed.
   - `cuff` (edge 0, 138.5) and `cap_back` (edge 3, 135.3) = the two short
     corner risers connecting the flat wrist opening up to where the cap
     curve begins — true mirror partners (2.3% length difference). These are
     the real underarm/tube-closing seam.
   - `right_underarm` (edge 1, 284.3) and `cap_front` (edge 2, 266.9) = the
     two long curves meeting at the peak — the true cap halves, sewn to the
     front/back panel armholes.

## Final wiring (confirmed working, 2026-07-20)

| Seam            | Piece A → edge                  | Piece B → edge                     | da    | db    |
|------------------|----------------------------------|--------------------------------------|-------|-------|
| shoulder-right   | front_panel → right_shoulder (1) | back_panel → left_shoulder (3)       | True  | False |
| shoulder-left    | front_panel → left_shoulder (8)  | back_panel → right_shoulder (6)      | True  | False |
| side-right       | front_panel → right_side (3)     | back_panel → left_side (1)           | True  | False |
| side-left        | front_panel → left_side (6)      | back_panel → right_side (8)          | True  | False |
| arm-R-front      | front_panel → left_armhole (7)   | sleeve_right → right_underarm (1)    | True  | True  |
| arm-R-back       | back_panel → right_armhole (7)   | sleeve_right → cap_front (2)         | True  | True  |
| arm-L-front      | front_panel → right_armhole (2)  | sleeve_left → right_underarm (1)     | True  | False |
| arm-L-back       | back_panel → left_armhole (2)    | sleeve_left → cap_front (2)          | True  | False |
| sleeve-L-tube    | sleeve_left → cuff (0)           | sleeve_left → cap_back (3)           | True  | False |
| sleeve-R-tube    | sleeve_right → cuff (0)          | sleeve_right → cap_back (3)          | True  | False |

`left_underarm` (edge 4) is intentionally left unseamed on both sleeves — it's
the wrist opening.

Body seams (shoulders/sides) cross-pair front-right↔back-left because CLO
mirrors the back panel's DXF left/right when placing it rearward.

### Why `arm-R-front`/`arm-R-back` need `db=True` but `arm-L-front`/`arm-L-back` don't

`sleeve_right` and `sleeve_left` share identical DXF geometry — CLO mirrors
`sleeve_right` only at placement time, not in the pattern file itself. That
placement-time mirror flips the edge's effective winding direction as CLO's
stitcher sees it, so the right sleeve's armhole seams need the opposite `db`
parity from the left sleeve's to avoid a twist. The tube seams (`sleeve-L/R
-tube`) are self-seams within one piece, so both needed the same `da=True`
fix (this one wasn't about left/right mirroring — see below).

## Debugging history (chronological)

1. **Original (broken) wiring**: armhole seams used `cap_front`/`cap_back`
   with front/back mixed up, and the tube seam was
   `right_underarm(1)`↔`left_underarm(4)`. Visually twisted per screenshots.
2. **First fix attempt** (length-matching only, no DXF coordinates): swapped
   armhole to `right_underarm(1)`+`cap_front(2)`, tube to
   `cap_back(3)`↔`left_underarm(4)`. This fixed the armhole-to-panel
   connections (confirmed correct by user) but the tube seam was now
   sewing a 135.3-unit edge directly to a 384.7-unit edge (2.8x mismatch) —
   looked stretched/wrong.
3. **Direction-flag pass**: user reported the *right* sleeve's armhole seams
   were twisted even though the edge pairing was confirmed correct → flipped
   `db` to `True` on `arm-R-front`/`arm-R-back` only (mirroring compensation,
   see above). Fixed.
4. **Geometry re-derivation**: direct DXF vertex-coordinate analysis (see
   table above) revealed `cuff(0)` and `cap_back(3)` — not
   `left_underarm(4)` — are `cap_back`'s true mirror partner, and
   `left_underarm(4)` is actually the flat wrist opening that should stay
   unseamed. Rewired the tube seam to `cuff(0)`↔`cap_back(3)`.
5. **Final direction-flag pass**: new tube-seam edge pairing initially sewed
   crisscrossed (edges walked in opposite winding order) → flipped `da` to
   `True` on both `sleeve-L-tube` and `sleeve-R-tube`. Confirmed clean.

## Reproducing / re-verifying

```
python clo_vto/run_clo_vto.py --use-default-panels
```

Requires the CLO REST plugin running and a **fresh project** (File → New) —
CLO's `new-project` command is async and if a pipeline run starts before the
previous scene finishes clearing, patterns accumulate and Step 06's edge-count
validation aborts the run (harmless, just re-run after resetting).
