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

Armhole wiring (front panel also cross-paired: DXF right = avatar left):
  Right sleeve cap_front (edge 2) → front panel LEFT_armhole  (edge 7)  [avatar's right arm]
  Right sleeve cap_back  (edge 3) → back  panel LEFT_armhole  (edge 2)  [avatar's right arm]
  Left  sleeve cap_back  (edge 3) → front panel RIGHT_armhole (edge 2)  [avatar's left arm]
  Left  sleeve cap_front (edge 2) → back  panel RIGHT_armhole (edge 7)  [avatar's left arm]
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
    # Sleeve tube seams (underarm seam on each sleeve)
    {"name": "sleeve-L-tube",  "a": "sleeve_left",  "la": 1, "b": "sleeve_left",  "lb": 4, "da": False, "db": False},
    {"name": "sleeve-R-tube",  "a": "sleeve_right", "la": 1, "b": "sleeve_right", "lb": 4, "da": False, "db": False},
    # Armhole seams — right sleeve
    # Front: avatar's right arm = front DXF left_armhole (edge 7, cross-paired like shoulder/side)
    # Back:  avatar's right arm = back DXF right_armhole (edge 7, back naming is anatomically direct)
    {"name": "arm-R-front",    "a": "front_panel", "la": 7, "b": "sleeve_right",  "lb": 2, "da": True, "db": False},
    {"name": "arm-R-back",     "a": "back_panel",  "la": 7, "b": "sleeve_right",  "lb": 3, "da": True, "db": False},
    # Armhole seams — left sleeve
    # Front: avatar's left arm = front DXF right_armhole (edge 2, cross-paired)
    # Back:  avatar's left arm = back DXF left_armhole (edge 2, anatomically direct)
    {"name": "arm-L-front",    "a": "front_panel", "la": 2, "b": "sleeve_left",   "lb": 3, "da": True, "db": False},
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
        {"name": "sleeve-L-tube",  "a": "sleeve_left",  "la": _idx("sleeve_left",  "right_underarm"), "b": "sleeve_left",  "lb": _idx("sleeve_left",  "left_underarm"), "da": False, "db": False},
        {"name": "sleeve-R-tube",  "a": "sleeve_right", "la": _idx("sleeve_right", "right_underarm"), "b": "sleeve_right", "lb": _idx("sleeve_right", "left_underarm"), "da": False, "db": False},
        {"name": "arm-R-front",    "a": "front_panel", "la": _idx("front_panel", "left_armhole"),   "b": "sleeve_right",  "lb": _idx("sleeve_right", "cap_front"),      "da": True, "db": False},
        {"name": "arm-R-back",     "a": "back_panel",  "la": _idx("back_panel",  "right_armhole"),  "b": "sleeve_right",  "lb": _idx("sleeve_right", "cap_back"),       "da": True, "db": False},
        {"name": "arm-L-front",    "a": "front_panel", "la": _idx("front_panel", "right_armhole"),  "b": "sleeve_left",   "lb": _idx("sleeve_left",  "cap_back"),       "da": True, "db": False},
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
