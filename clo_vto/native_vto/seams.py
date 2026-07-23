"""Seam map for the 4-piece T-shirt pattern set.

Seam edge indices correspond to the edge layout recorded in edge_manifest.json.

Edge layout recap (0-based, per piece) — 10-edge body panels
--------------------------------------------------------------
Front panel — 10 edges (POLYLINE starts at neckline center, 0,1522):
  0 right_neckline   4 right_hem       8 left_shoulder
  1 right_shoulder   5 left_hem        9 left_neckline
  2 right_armhole    6 left_side
  3 right_side       7 left_armhole

Back panel — 10 edges (POLYLINE starts at hem center, 1337,905):
  0 left_hem         4 left_neckline   8 right_side
  1 left_side        5 right_neckline  9 right_hem
  2 left_armhole     6 right_shoulder
  3 left_shoulder    7 right_armhole

IMPORTANT — left/right cross-pairing for body seams:
  When CLO places the back panel facing rearward, the panel's DXF "right" side ends
  up on the avatar's anatomical LEFT side (mirror effect).  Therefore every body seam
  must connect front-right to back-LEFT (and front-left to back-right) to land on the
  same anatomical side of the garment.

Sleeve (left and right, same geometry) — 5 edges:
  0 cuff           2 cap_front        4 left_underarm
  1 right_underarm 3 cap_back

IMPORTANT — all four sleeve edges are misnamed relative to their visual role
(found by direct DXF vertex coordinate analysis, 2026-07-20 — walked the raw
polyline, matched cumulative arc-length to CLO's reported per-edge lengths to
get exact (x,y) for every edge boundary; see
.agent/clo-avatar-vto/seam-edge-mapping.md for the full derivation history):

  left_underarm(4) is the flat WRIST OPENING (384.7, bottom of the pattern) —
    not "cuff". This is the edge that should stay unseamed.
  cuff(0) and cap_back(3) are the two short corner risers connecting that
    flat bottom up to where the cap curve begins (138.5 and 135.3 — 2.3%
    apart, i.e. true mirror-image partners). These are the real "underarm"
    seam — sewn to each other to close the sleeve into a tube.
  right_underarm(1) and cap_front(2) are the two long curves meeting at the
    peak (284.3 and 266.9) — these are the true cap halves, confirmed by
    length-matching against front_armhole/back_armhole (within 2-3%).

Armhole wiring (front panel also cross-paired: DXF right = avatar left):
  Right sleeve right_underarm (edge 1) → front panel LEFT_armhole  (edge 7)  [avatar's right arm]
  Right sleeve cap_front      (edge 2) → back  panel RIGHT_armhole (edge 7)  [avatar's right arm]
  Left  sleeve right_underarm (edge 1) → front panel RIGHT_armhole (edge 2)  [avatar's left arm]
  Left  sleeve cap_front      (edge 2) → back  panel LEFT_armhole  (edge 2)  [avatar's left arm]
  Tube-closing (each sleeve, self-seam): cuff(0) ↔ cap_back(3).
  left_underarm(4) is left unseamed (wrist opening).
"""
from __future__ import annotations

import json
from pathlib import Path


class SeamManifestError(RuntimeError):
    """Raised when the seam manifest is missing or incomplete and fallback is
    disabled (P08).  Always indicates a schema drift or generation failure."""


DEFAULT_SEAM_META = {
    "geometry_hash": "",
    "version": "2",
}

# 10 seams for the 4-piece t-shirt.
# Front panel: 0=right_neckline, 1=right_shoulder, 2=right_armhole, 3=right_side,
#              4=right_hem, 5=left_hem, 6=left_side, 7=left_armhole, 8=left_shoulder, 9=left_neckline
# Back panel:  0=left_hem, 1=left_side, 2=left_armhole, 3=left_shoulder,
#              4=left_neckline, 5=right_neckline, 6=right_shoulder, 7=right_armhole, 8=right_side, 9=right_hem
# NOTE: body seams cross-pair front-right↔back-left (and front-left↔back-right) because CLO
# mirrors the back panel's DXF left/right when it faces it rearward during slot placement.
DEFAULT_SEAMS = [
    # Shoulder seams (front-right ↔ back-left = same anatomical shoulder)
    {"name": "shoulder-right", "a": "front_panel", "la": 1, "b": "back_panel",    "lb": 3, "da": True, "db": False},
    {"name": "shoulder-left",  "a": "front_panel", "la": 8, "b": "back_panel",    "lb": 6, "da": True, "db": False},
    # Side seams (front-right ↔ back-left = same anatomical side seam)
    {"name": "side-right",     "a": "front_panel", "la": 3, "b": "back_panel",    "lb": 1, "da": True, "db": False},
    {"name": "side-left",      "a": "front_panel", "la": 6, "b": "back_panel",    "lb": 8, "da": True, "db": False},
    # Sleeve tube seams (closes the underarm gap; see note at top of file —
    # cuff(0) and cap_back(3) are the two short corner-riser edges that are
    # true mirror partners of each other; left_underarm(4) is actually the
    # flat wrist opening and stays unseamed).
    # da flipped to True (2026-07-20): edges confirmed correct, but seam was
    # crisscrossing — the two riser edges were being walked in opposite
    # winding order relative to each other.
    {"name": "sleeve-L-tube",  "a": "sleeve_left",  "la": 0, "b": "sleeve_left",  "lb": 3, "da": True, "db": False},
    {"name": "sleeve-R-tube",  "a": "sleeve_right", "la": 0, "b": "sleeve_right", "lb": 3, "da": True, "db": False},
    # Armhole seams — right sleeve (sleeve edges: right_underarm=1, cap_front=2 —
    # the true two cap halves meeting at the shoulder peak; see note at top of file)
    # Front: avatar's right arm = front DXF left_armhole (edge 7, cross-paired like shoulder/side)
    # Back:  avatar's right arm = back DXF right_armhole (edge 7, back naming is anatomically direct)
    # db flipped to True (2026-07-20): edge pairing confirmed correct visually,
    # but seam was twisted — sleeve_right is mirrored at placement (unlike
    # sleeve_left), so its armhole seams need the opposite direction parity.
    {"name": "arm-R-front",    "a": "front_panel", "la": 7, "b": "sleeve_right",  "lb": 1, "da": True, "db": True},
    {"name": "arm-R-back",     "a": "back_panel",  "la": 7, "b": "sleeve_right",  "lb": 2, "da": True, "db": True},
    # Armhole seams — left sleeve
    # Front: avatar's left arm = front DXF right_armhole (edge 2, cross-paired)
    # Back:  avatar's left arm = back DXF left_armhole (edge 2, anatomically direct)
    {"name": "arm-L-front",    "a": "front_panel", "la": 2, "b": "sleeve_left",   "lb": 1, "da": True, "db": False},
    {"name": "arm-L-back",     "a": "back_panel",  "la": 2, "b": "sleeve_left",   "lb": 2, "da": True, "db": False},
]


def load_seams_from_manifest(manifest_path: Path) -> list[dict] | None:
    """Build the seam list from an edge_manifest.json file.

    Returns the seam list if the manifest exists and is valid, else None.
    Uses DEFAULT_SEAMS as the template — only the index values are verified
    against the manifest.  If any expected edge name is missing the function
    returns None so the caller can fall back to DEFAULT_SEAMS.
    """
    if not manifest_path.exists():
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    def _idx(piece: str, edge_name: str) -> int | None:
        for entry in manifest.get(piece, []):
            if entry.get("name") == edge_name:
                return int(entry["index"])
        return None

    # Required seam-wiring edges for each piece.
    # Supports both old 8-edge naming (hem/neckline as single edges) and new
    # 10-edge naming (right_hem/left_hem and right_neckline/left_neckline split).
    _REQUIRED = {
        "front_panel":  ["right_side", "right_armhole", "right_shoulder",
                         "left_shoulder", "left_armhole", "left_side"],
        "back_panel":   ["right_side", "right_armhole", "right_shoulder",
                         "left_shoulder", "left_armhole", "left_side"],
        "sleeve_left":  ["cuff", "right_underarm", "cap_front", "cap_back", "left_underarm"],
        "sleeve_right": ["cuff", "right_underarm", "cap_front", "cap_back", "left_underarm"],
    }

    # Verify all seam-critical edges are present
    for piece, names in _REQUIRED.items():
        for name in names:
            if _idx(piece, name) is None:
                return None   # incomplete manifest — fall back

    # Build seams using manifest indices.
    # Body seams cross-pair front-right↔back-left (and front-left↔back-right) because CLO
    # mirrors the back panel's DXF left/right when placing it rearward in its slot.
    seams = [
        {"name": "shoulder-right", "a": "front_panel", "la": _idx("front_panel", "right_shoulder"), "b": "back_panel",    "lb": _idx("back_panel",    "left_shoulder"),  "da": True, "db": False},
        {"name": "shoulder-left",  "a": "front_panel", "la": _idx("front_panel", "left_shoulder"),  "b": "back_panel",    "lb": _idx("back_panel",    "right_shoulder"), "da": True, "db": False},
        {"name": "side-right",     "a": "front_panel", "la": _idx("front_panel", "right_side"),     "b": "back_panel",    "lb": _idx("back_panel",    "left_side"),      "da": True, "db": False},
        {"name": "side-left",      "a": "front_panel", "la": _idx("front_panel", "left_side"),      "b": "back_panel",    "lb": _idx("back_panel",    "right_side"),     "da": True, "db": False},
        # Tube-closing seam: cuff(0) and cap_back(3) are the true mirror-image
        # corner-riser edges (see note at top of file); left_underarm(4) is
        # actually the flat wrist opening and is left unseamed.
        # da flipped to True (2026-07-20): edges confirmed correct, but seam was
        # crisscrossing until direction was untwisted.
        {"name": "sleeve-L-tube",  "a": "sleeve_left",  "la": _idx("sleeve_left",  "cuff"), "b": "sleeve_left",  "lb": _idx("sleeve_left",  "cap_back"), "da": True, "db": False},
        {"name": "sleeve-R-tube",  "a": "sleeve_right", "la": _idx("sleeve_right", "cuff"), "b": "sleeve_right", "lb": _idx("sleeve_right", "cap_back"), "da": True, "db": False},
        # Armhole seams: right_underarm(1) and cap_front(2) are the true two cap
        # halves meeting at the shoulder peak (see note at top of file) — cap_back
        # was never shaped to sew into an armhole and is not used here.
        # db flipped to True on right sleeve (2026-07-20): sleeve_right is mirrored
        # at placement (sleeve_left is not), so its armhole seams need opposite
        # direction parity from sleeve_left's to avoid twisting.
        {"name": "arm-R-front",    "a": "front_panel", "la": _idx("front_panel", "left_armhole"),   "b": "sleeve_right",  "lb": _idx("sleeve_right", "right_underarm"), "da": True, "db": True},
        {"name": "arm-R-back",     "a": "back_panel",  "la": _idx("back_panel",  "right_armhole"),  "b": "sleeve_right",  "lb": _idx("sleeve_right", "cap_front"),      "da": True, "db": True},
        {"name": "arm-L-front",    "a": "front_panel", "la": _idx("front_panel", "right_armhole"),  "b": "sleeve_left",   "lb": _idx("sleeve_left",  "right_underarm"), "da": True, "db": False},
        {"name": "arm-L-back",     "a": "back_panel",  "la": _idx("back_panel",  "left_armhole"),   "b": "sleeve_left",   "lb": _idx("sleeve_left",  "cap_front"),      "da": True, "db": False},
    ]
    return seams


def validate_edge_counts(ctx) -> bool:
    """Compare CLO's reported edge counts against the edge manifest.

    Call this after step_06 has populated ctx.edge_counts.
    Returns True if all pieces match, False if any mismatch.
    """
    manifest = getattr(ctx, "edge_manifest", None)
    if not manifest:
        return True   # no manifest to validate against — skip silently

    all_ok = True
    for piece_name, idx in ctx.piece_to_index.items():
        expected = len(manifest.get(piece_name, []))
        actual = ctx.edge_counts.get(str(idx), -1)
        if expected == 0:
            continue   # piece not in manifest — skip
        if actual != expected:
            print(
                f"  ! Edge count mismatch '{piece_name}': "
                f"manifest={expected}, CLO reported={actual}"
            )
            all_ok = False
        else:
            print(f"  Edge count OK: '{piece_name}' = {actual} edges")
    return all_ok
