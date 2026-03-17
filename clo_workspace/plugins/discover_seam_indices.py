"""
discover_seam_indices.py
────────────────────────
Reads the DXF pattern files directly (via ezdxf) to extract exact edge indices
and generate the SEAM_MAP for CLO3D sewing automation.

The CLO API's GetPatternInformation() returns only metadata — no edge geometry.
So this script reads geometry from the source DXF files, which have the exact
same POLYLINE vertex ordering that CLO uses for its internal line indices.

USAGE
─────
  python plugins/discover_seam_indices.py
         [--dir PATH_TO_PATTERNS_DXF_FOLDER]

  If no --dir is given, it searches for the latest run_NNN/patterns_dxf/
  folder under 2d_patterned_garment_generation_clo3d/output/.

OUTPUT
──────
  • Edge table per pattern piece
  • Identified seam edges with semantic labels
  • Copy-pasteable SEAM_MAP Python list
"""

import sys
import math
import glob
import argparse
from pathlib import Path

try:
    import ezdxf
except ImportError:
    print("ERROR: ezdxf is required.  pip install ezdxf")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# DXF reading helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_polyline_edges(dxf_path):
    """
    Opens a DXF file and returns a list of edge dicts for the first POLYLINE.
    Each segment (vertex[i] → vertex[i+1]) becomes one edge, 0-indexed.
    These indices match CLO's internal line numbering for the imported pattern.
    """
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    poly = next((e for e in msp if e.dxftype() == "POLYLINE"), None)
    if poly is None:
        return []

    verts = [v.dxf.location for v in poly.vertices]
    n = len(verts)
    edges = []
    for i in range(n):
        a = verts[i]
        b = verts[(i + 1) % n]
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        length = math.sqrt(dx * dx + dy * dy)
        edges.append({
            "index":  i,
            "length": length,
            "start":  (a[0], a[1]),
            "end":    (b[0], b[1]),
        })
    return edges


def orient(edge):
    sx, sy = edge["start"]
    ex, ey = edge["end"]
    dx = abs(ex - sx)
    dy = abs(ey - sy)
    if dx + dy < 1e-6:
        return "P"
    r = dy / (dx + 1e-9)
    return "H" if r < 0.4 else ("V" if r > 2.5 else "D")


def midpoint(edge):
    return ((edge["start"][0] + edge["end"][0]) / 2,
            (edge["start"][1] + edge["end"][1]) / 2)


def print_edge_table(name, edges, pattern_index):
    print(f"\n  Pattern {pattern_index}: {name}  ({len(edges)} edges)")
    print(f"  {'idx':>4}  {'len':>7}  {'or':>2}  {'mid_x':>7}  {'mid_y':>7}"
          f"  start → end")
    print("  " + "-" * 80)
    for e in edges:
        mx, my = midpoint(e)
        sx, sy = e["start"]
        ex, ey = e["end"]
        print(f"  {e['index']:>4}  {e['length']:>7.1f}  {orient(e):>2}  "
              f"{mx:>7.1f}  {my:>7.1f}  "
              f"({sx:.1f},{sy:.1f}) → ({ex:.1f},{ey:.1f})")


# ─────────────────────────────────────────────────────────────────────────────
# Hardcoded seam map based on DXF geometry analysis
# (Run `python discover_seam_indices.py --show-edges` to verify these indices
#  against your specific DXF files — they are stable as long as the pattern
#  generator hasn't changed.)
# ─────────────────────────────────────────────────────────────────────────────
#
# Pattern order (must match import order — see clo_automation_client.py):
#   0 = front_panel    1 = back_panel    2 = sleeve_left    3 = sleeve_right
#
# Front panel (19 edges):
#   0: hem (H,54), 1: side-R (V,49.8), 2-6: armhole-R curves (D),
#   7: armhole-R upper (V,9), 8: shoulder-R (D,11.7),
#   9-10: neckline (H), 11: shoulder-L (D,11.7),
#   12: armhole-L upper (V,9), 13-17: armhole-L curves (D), 18: side-L (V,49.8)
#
# Back panel (18 edges):
#   0: hem (H,54), 1: side-R (V,49.8), 2-7: armhole-R curves (D/V),
#   8: shoulder-R (H,15.1), 9: neckline (H,15), 10: shoulder-L (H,15.1),
#   11-16: armhole-L curves (D/V), 17: side-L (V,49.8)
#
# Sleeve left/right (13 edges, identical geometry):
#   0: cuff hem (H,19), 1: tube-seam-A (V,9.3),
#   2-6: cap right half (D, going up to tip),
#   7-11: cap left half (D, going down from tip),
#   12: tube-seam-B (V,9.3)

def build_hardcoded_seam_map():
    """
    Returns the SEAM_MAP derived from direct DXF analysis.
    Directions (da/db) are best-effort; flip db if a seam is twisted in CLO.
    """
    F, B, L, R = 0, 1, 2, 3     # pattern indices

    seams = [
        # ── Body structural seams ───────────────────────────────────────────
        {"name": "side-right",     "a": F, "la": 1,  "b": B, "lb": 1,  "da": True, "db": True},
        {"name": "side-left",      "a": F, "la": 18, "b": B, "lb": 17, "da": True, "db": True},
        {"name": "shoulder-right", "a": F, "la": 8,  "b": B, "lb": 8,  "da": True, "db": True},
        {"name": "shoulder-left",  "a": F, "la": 11, "b": B, "lb": 10, "da": True, "db": True},

        # ── Sleeve tube (each sleeve sewn to itself to form a cylinder) ─────
        {"name": "sleeve-L-tube",  "a": L, "la": 1,  "b": L, "lb": 12, "da": True, "db": False},
        {"name": "sleeve-R-tube",  "a": R, "la": 1,  "b": R, "lb": 12, "da": True, "db": False},

        # ── Right sleeve cap → right armhole ────────────────────────────────
        # Sleeve front-half (edges 2-6) ↔ front panel right armhole (edges 2-6)
        {"name": "arm-R-fr-0",     "a": F, "la": 2,  "b": R, "lb": 2,  "da": True, "db": True},
        {"name": "arm-R-fr-1",     "a": F, "la": 3,  "b": R, "lb": 3,  "da": True, "db": True},
        {"name": "arm-R-fr-2",     "a": F, "la": 4,  "b": R, "lb": 4,  "da": True, "db": True},
        {"name": "arm-R-fr-3",     "a": F, "la": 5,  "b": R, "lb": 5,  "da": True, "db": True},
        {"name": "arm-R-fr-4",     "a": F, "la": 6,  "b": R, "lb": 6,  "da": True, "db": True},
        # Sleeve back-half (edges 7-11, reversed) ↔ back panel right armhole (edges 2-6)
        {"name": "arm-R-bk-0",     "a": B, "la": 2,  "b": R, "lb": 11, "da": True, "db": True},
        {"name": "arm-R-bk-1",     "a": B, "la": 3,  "b": R, "lb": 10, "da": True, "db": True},
        {"name": "arm-R-bk-2",     "a": B, "la": 4,  "b": R, "lb": 9,  "da": True, "db": True},
        {"name": "arm-R-bk-3",     "a": B, "la": 5,  "b": R, "lb": 8,  "da": True, "db": True},
        {"name": "arm-R-bk-4",     "a": B, "la": 6,  "b": R, "lb": 7,  "da": True, "db": True},

        # ── Left sleeve cap → left armhole ───────────────────────────────────
        # Sleeve_left is mirrored: cap right-half faces back, left-half faces front
        # Sleeve left-half (edges 7-11, reversed) ↔ front panel left armhole (edges 13-17)
        {"name": "arm-L-fr-0",     "a": F, "la": 13, "b": L, "lb": 11, "da": True, "db": True},
        {"name": "arm-L-fr-1",     "a": F, "la": 14, "b": L, "lb": 10, "da": True, "db": True},
        {"name": "arm-L-fr-2",     "a": F, "la": 15, "b": L, "lb": 9,  "da": True, "db": True},
        {"name": "arm-L-fr-3",     "a": F, "la": 16, "b": L, "lb": 8,  "da": True, "db": True},
        {"name": "arm-L-fr-4",     "a": F, "la": 17, "b": L, "lb": 7,  "da": True, "db": True},
        # Sleeve right-half (edges 2-6) ↔ back panel left armhole (edges 12-16)
        {"name": "arm-L-bk-0",     "a": B, "la": 12, "b": L, "lb": 2,  "da": True, "db": True},
        {"name": "arm-L-bk-1",     "a": B, "la": 13, "b": L, "lb": 3,  "da": True, "db": True},
        {"name": "arm-L-bk-2",     "a": B, "la": 14, "b": L, "lb": 4,  "da": True, "db": True},
        {"name": "arm-L-bk-3",     "a": B, "la": 15, "b": L, "lb": 5,  "da": True, "db": True},
        {"name": "arm-L-bk-4",     "a": B, "la": 16, "b": L, "lb": 6,  "da": True, "db": True},
    ]
    return seams


# ─────────────────────────────────────────────────────────────────────────────
# Find the DXF folder
# ─────────────────────────────────────────────────────────────────────────────

def find_dxf_dir():
    repo = Path(__file__).parent.parent.parent
    runs = sorted(glob.glob(str(
        repo / "2d_patterned_garment_generation_clo3d" / "output" / "run_*" / "patterns_dxf"
    )))
    return Path(runs[-1]) if runs else None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate CLO seam indices from DXF files")
    parser.add_argument("--dir", help="Path to patterns_dxf folder", default=None)
    parser.add_argument("--show-edges", action="store_true",
                        help="Print full edge table for verification")
    args = parser.parse_args()

    dxf_dir = Path(args.dir) if args.dir else find_dxf_dir()
    if not dxf_dir or not dxf_dir.exists():
        print("ERROR: Could not find patterns_dxf folder.")
        print("       Pass --dir PATH_TO_FOLDER explicitly.")
        sys.exit(1)

    print(f"Reading DXF files from: {dxf_dir}\n")

    # Expected files in import order (must match clo_automation_client.py PATTERNS list)
    FILES = ["front_panel.dxf", "back_panel.dxf", "sleeve_left.dxf", "sleeve_right.dxf"]
    NAMES = ["front_panel", "back_panel", "sleeve_left", "sleeve_right"]

    all_edges = {}
    for idx, (fname, name) in enumerate(zip(FILES, NAMES)):
        path = dxf_dir / fname
        if not path.exists():
            print(f"  ! Missing: {path}")
            all_edges[idx] = []
            continue
        edges = read_polyline_edges(path)
        all_edges[idx] = edges
        if args.show_edges:
            print_edge_table(name, edges, idx)

    if not args.show_edges:
        # Quick summary
        for idx, name in enumerate(NAMES):
            n = len(all_edges.get(idx, []))
            print(f"  {name} (pattern {idx}): {n} edges")

    seam_map = build_hardcoded_seam_map()

    print("\n" + "=" * 72)
    print("SEAM MAP  (26 seams total)")
    print("=" * 72)
    print(f"\n  {'Seam':<22}  A(pat,edge) ↔ B(pat,edge)  dir")
    print("  " + "-" * 55)
    for s in seam_map:
        print(f"  {s['name']:<22}  ({s['a']},{s['la']:>2}) ↔ ({s['b']},{s['lb']:>2})"
              f"  {s['da']}/{s['db']}")

    print("\n" + "=" * 72)
    print("COPY-PASTE INTO example_workflow(seam_map=...)")
    print("=" * 72)
    print("\nSEAM_MAP = [")
    for s in seam_map:
        print(f'    {{"name": "{s["name"]}", '
              f'"a": {s["a"]}, "la": {s["la"]}, '
              f'"b": {s["b"]}, "lb": {s["lb"]}, '
              f'"da": {s["da"]}, "db": {s["db"]}}},')
    print("]")
    print()
    print("Usage:")
    print("  from clo_workspace.plugins.clo_automation_client import example_workflow")
    print("  example_workflow(seam_map=SEAM_MAP)")
    print()
    print("NOTE: If seams look twisted in CLO simulation, flip 'db' on the")
    print("      affected seam entry (True↔False).  Armhole directions especially")
    print("      may need adjustment depending on sleeve arrangement orientation.")

    return seam_map


if __name__ == "__main__":
    main()
