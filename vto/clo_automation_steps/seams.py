"""Seam map for the 4-piece T-shirt pattern set.

Seam edge indices correspond to the edge layout defined in panels.py and
recorded in edge_manifest.json at generation time.

Edge layout recap (0-based, per piece)
---------------------------------------
Front / Back panel — 8 edges:
  0 hem            3 right_shoulder   6 left_armhole
  1 right_side     4 neckline         7 left_side
  2 right_armhole  5 left_shoulder

Sleeve (left and right, same geometry) — 5 edges:
  0 cuff           2 cap_front        4 left_underarm
  1 right_underarm 3 cap_back

Armhole wiring:
  Right sleeve cap_front (edge 2) → front panel right_armhole (edge 2)
  Right sleeve cap_back  (edge 3) → back  panel right_armhole (edge 2)
  Left  sleeve cap_back  (edge 3) → front panel left_armhole  (edge 6)
  Left  sleeve cap_front (edge 2) → back  panel left_armhole  (edge 6)
  (Left sleeve is geometrically identical but oriented in reverse on the arm.)
"""
from __future__ import annotations

import json
from pathlib import Path


DEFAULT_SEAM_META = {
    "geometry_hash": "",
    "version": "2",
}

# 10 seams replacing the old 26-seam hardcoded map.
# Each SPLINE entity = one CLO edge → one seam entry per seam line.
DEFAULT_SEAMS = [
    # Shoulder seams
    {"name": "shoulder-right", "a": "front_panel", "la": 3, "b": "back_panel",    "lb": 3, "da": True, "db": True},
    {"name": "shoulder-left",  "a": "front_panel", "la": 5, "b": "back_panel",    "lb": 5, "da": True, "db": True},
    # Side seams
    {"name": "side-right",     "a": "front_panel", "la": 1, "b": "back_panel",    "lb": 1, "da": True, "db": True},
    {"name": "side-left",      "a": "front_panel", "la": 7, "b": "back_panel",    "lb": 7, "da": True, "db": True},
    # Sleeve tube seams (underarm seam on each sleeve)
    {"name": "sleeve-L-tube",  "a": "sleeve_left",  "la": 1, "b": "sleeve_left",  "lb": 4, "da": True, "db": False},
    {"name": "sleeve-R-tube",  "a": "sleeve_right", "la": 1, "b": "sleeve_right", "lb": 4, "da": True, "db": False},
    # Armhole seams — right sleeve
    {"name": "arm-R-front",    "a": "front_panel", "la": 2, "b": "sleeve_right",  "lb": 2, "da": True, "db": True},
    {"name": "arm-R-back",     "a": "back_panel",  "la": 2, "b": "sleeve_right",  "lb": 3, "da": True, "db": True},
    # Armhole seams — left sleeve (cap orientation is reversed vs right sleeve)
    {"name": "arm-L-front",    "a": "front_panel", "la": 6, "b": "sleeve_left",   "lb": 3, "da": True, "db": True},
    {"name": "arm-L-back",     "a": "back_panel",  "la": 6, "b": "sleeve_left",   "lb": 2, "da": True, "db": True},
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

    # Edge name → index look-up for each piece
    _EDGE_NAMES = {
        "front_panel":  ["hem", "right_side", "right_armhole", "right_shoulder",
                         "neckline", "left_shoulder", "left_armhole", "left_side"],
        "back_panel":   ["hem", "right_side", "right_armhole", "right_shoulder",
                         "neckline", "left_shoulder", "left_armhole", "left_side"],
        "sleeve_left":  ["cuff", "right_underarm", "cap_front", "cap_back", "left_underarm"],
        "sleeve_right": ["cuff", "right_underarm", "cap_front", "cap_back", "left_underarm"],
    }

    # Verify all expected edges are present
    for piece, names in _EDGE_NAMES.items():
        for name in names:
            if _idx(piece, name) is None:
                return None   # incomplete manifest — fall back

    # Build seams using manifest indices
    seams = [
        {"name": "shoulder-right", "a": "front_panel", "la": _idx("front_panel", "right_shoulder"), "b": "back_panel",    "lb": _idx("back_panel",    "right_shoulder"), "da": True, "db": True},
        {"name": "shoulder-left",  "a": "front_panel", "la": _idx("front_panel", "left_shoulder"),  "b": "back_panel",    "lb": _idx("back_panel",    "left_shoulder"),  "da": True, "db": True},
        {"name": "side-right",     "a": "front_panel", "la": _idx("front_panel", "right_side"),     "b": "back_panel",    "lb": _idx("back_panel",    "right_side"),     "da": True, "db": True},
        {"name": "side-left",      "a": "front_panel", "la": _idx("front_panel", "left_side"),      "b": "back_panel",    "lb": _idx("back_panel",    "left_side"),      "da": True, "db": True},
        {"name": "sleeve-L-tube",  "a": "sleeve_left",  "la": _idx("sleeve_left",  "right_underarm"), "b": "sleeve_left",  "lb": _idx("sleeve_left",  "left_underarm"), "da": True, "db": False},
        {"name": "sleeve-R-tube",  "a": "sleeve_right", "la": _idx("sleeve_right", "right_underarm"), "b": "sleeve_right", "lb": _idx("sleeve_right", "left_underarm"), "da": True, "db": False},
        {"name": "arm-R-front",    "a": "front_panel", "la": _idx("front_panel", "right_armhole"),  "b": "sleeve_right",  "lb": _idx("sleeve_right", "cap_front"),      "da": True, "db": True},
        {"name": "arm-R-back",     "a": "back_panel",  "la": _idx("back_panel",  "right_armhole"),  "b": "sleeve_right",  "lb": _idx("sleeve_right", "cap_back"),       "da": True, "db": True},
        {"name": "arm-L-front",    "a": "front_panel", "la": _idx("front_panel", "left_armhole"),   "b": "sleeve_left",   "lb": _idx("sleeve_left",  "cap_back"),       "da": True, "db": True},
        {"name": "arm-L-back",     "a": "back_panel",  "la": _idx("back_panel",  "left_armhole"),   "b": "sleeve_left",   "lb": _idx("sleeve_left",  "cap_front"),      "da": True, "db": True},
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
