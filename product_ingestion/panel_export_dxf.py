"""DXF export for canonical Step 2 panel outputs.

Each PieceLayout is exported as a DXF file containing one closed LWPOLYLINE
on the CutLine layer.  CLO3D's ImportDXF function requires a single closed
boundary polygon per file (DXF-AAMA convention); multiple separate entities
are treated as internal baselines and result in 0 patterns imported.

Coordinate units: centimetres internally → millimetres in DXF
(doc.units = MM so CLO imports at the correct physical size).

Curved edges are encoded via LWPOLYLINE bulge values (DXF §W-F-1012) rather
than dense vertex sampling.  One vertex per edge keeps CLO line index i equal
to logical edge i, so seam manifest indices remain aligned.  Bulge encodes
the arc as tan(included_angle/4), preserving the correct curve shape in CLO's
viewport without changing the edge count.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    try:
        from .curve_segment import PieceEdge, PieceLayout
    except ImportError:
        from curve_segment import PieceEdge, PieceLayout  # type: ignore

try:
    import ezdxf
    from ezdxf import units

    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

_CM_TO_MM = 10.0


def _pt3(x: float, y: float, scale: float = _CM_TO_MM) -> tuple:
    return (x * scale, y * scale, 0.0)


def _edge_bulge(edge: "PieceEdge") -> float:
    """Return the DXF LWPOLYLINE bulge value for one edge.

    bulge = tan(included_angle / 4).
    Positive bulge = arc bows left of the direction of travel (CCW).
    Straight edges return 0.0.

    The approximation fits a single circular arc to each Bezier edge by
    measuring the sagitta (perpendicular deviation at the curve midpoint).
    For s_curve edges the midpoint is the segment junction, which gives a
    reasonable single-arc approximation.
    """
    if edge.edge_type == "straight" or not edge.segments:
        return 0.0

    s = edge.start
    e = edge.end

    # Midpoint on the Bezier path
    if edge.edge_type == "cubic_bezier":
        mid_pts = edge.segments[0].sample(3)  # t=0, 0.5, 1.0
        mid_bezier = mid_pts[1]
    elif edge.edge_type == "s_curve":
        # Junction of the two Bezier segments is the natural path midpoint
        mid_bezier = edge.segments[0].p3
    else:
        return 0.0

    # Chord midpoint
    mid_chord_x = (s[0] + e[0]) / 2.0
    mid_chord_y = (s[1] + e[1]) / 2.0

    # Sagitta vector from chord midpoint → Bezier midpoint
    sag_x = mid_bezier[0] - mid_chord_x
    sag_y = mid_bezier[1] - mid_chord_y
    sagitta = math.hypot(sag_x, sag_y)
    chord   = math.hypot(e[0] - s[0], e[1] - s[1])

    if sagitta < 1e-6 or chord < 1e-6:
        return 0.0

    half_chord = chord / 2.0
    # Radius of the approximating circular arc
    radius = (half_chord ** 2 + sagitta ** 2) / (2.0 * sagitta)

    sin_half = min(half_chord / radius, 1.0)
    half_angle = math.asin(sin_half)
    bulge_mag = math.tan(half_angle / 2.0)

    # Sign: positive (CCW) if the sagitta bows left of the chord direction
    chord_dx = e[0] - s[0]
    chord_dy = e[1] - s[1]
    cross = chord_dx * sag_y - chord_dy * sag_x
    return bulge_mag if cross > 0 else -bulge_mag


def _add_cutline_boundary(msp, layout: "PieceLayout", n_fit: int) -> None:
    """Write one closed LWPOLYLINE on the CutLine layer.

    One vertex per logical edge (corner-only) with LWPOLYLINE bulge values for
    curved edges.  This keeps CLO line index i == logical edge i so seam
    manifest indices remain correct, while curved edges (sleeve cap, armhole,
    neckline) are rendered as smooth arcs rather than straight lines.

    If CLO ignores bulge on import the geometry degrades gracefully to the
    previous corner-only straight-line behaviour — seam indices still align.
    """
    if not layout.edges:
        return

    pts = []
    for edge in layout.edges:
        x_mm = edge.start[0] * _CM_TO_MM
        y_mm = edge.start[1] * _CM_TO_MM
        bulge = _edge_bulge(edge)
        pts.append((x_mm, y_mm, 0.0, 0.0, bulge))  # x, y, start_width, end_width, bulge

    msp.add_lwpolyline(
        pts,
        format="xyseb",
        close=True,
        dxfattribs={"layer": "CutLine", "color": 7},
    )


def _add_notches(msp, layout: "PieceLayout") -> None:
    """Add small perpendicular notch lines at key seam reference points."""
    name = layout.name
    pts_mm = layout.polygon(n_per_segment=16)
    if not pts_mm:
        return
    pts_scaled = [(x * _CM_TO_MM, y * _CM_TO_MM) for x, y in pts_mm]
    max_y = max(p[1] for p in pts_scaled)

    if "panel" in name:
        # Notch at each shoulder point (top 10% of piece)
        shoulder_pts = [p for p in pts_scaled if p[1] > max_y * 0.90]
        for px, py in shoulder_pts[:2]:
            msp.add_line(
                (px - 2.5, py, 0), (px + 2.5, py, 0),
                dxfattribs={"layer": "Notch", "color": 1},
            )
    elif "sleeve" in name:
        # Notch at the cap apex
        top_pts = [p for p in pts_scaled if abs(p[1] - max_y) < 10.0]
        if top_pts:
            px, py = top_pts[len(top_pts) // 2]
            msp.add_line(
                (px - 2.5, py, 0), (px + 2.5, py, 0),
                dxfattribs={"layer": "Notch", "color": 1},
            )


def _add_grain_line(msp, layout: "PieceLayout") -> None:
    pts_mm = layout.polygon(n_per_segment=16)
    if not pts_mm:
        return
    pts_scaled = [(x * _CM_TO_MM, y * _CM_TO_MM) for x, y in pts_mm]
    xs = [p[0] for p in pts_scaled]
    ys = [p[1] for p in pts_scaled]
    cx = sum(xs) / len(xs)
    msp.add_line(
        (cx, min(ys) + 50.0, 0),
        (cx, max(ys) - 50.0, 0),
        dxfattribs={"layer": "GrainLine", "color": 5},
    )


def _add_label(msp, layout: "PieceLayout") -> None:
    pts_mm = layout.polygon(n_per_segment=16)
    if not pts_mm:
        return
    pts_scaled = [(x * _CM_TO_MM, y * _CM_TO_MM) for x, y in pts_mm]
    cx = sum(p[0] for p in pts_scaled) / len(pts_scaled)
    cy = sum(p[1] for p in pts_scaled) / len(pts_scaled)
    msp.add_text(
        layout.name.replace("_", " ").title(),
        dxfattribs={"layer": "Text", "height": 50.0, "color": 3},
    ).set_placement((cx, cy, 0))


def export_panels_dxf(
    layouts: "dict[str, PieceLayout]",
    measurements,
    output_dir: Path,
    n_fit: int = 24,
) -> None:
    """Export each PieceLayout as a DXF file.

    Parameters
    ----------
    layouts : dict[str, PieceLayout]
        Piece name → PieceLayout, as produced by DynamicPatternGenerator.
    measurements : GarmentMeasurements
        Used only for legacy notch placement heuristics.
    output_dir : Path
        Directory to write DXF files into (created if absent).
    n_fit : int
        Number of fit-points sampled per curve segment for SPLINE entities.
        Higher = smoother CLO approximation.  Default 24 is sufficient for
        garment-scale curves.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    if not HAS_EZDXF:
        print("Warning: ezdxf not available, skipping DXF export.")
        return

    for name, layout in layouts.items():
        doc = ezdxf.new("R2010")
        doc.units = units.MM   # CLO3D expects millimetres
        msp = doc.modelspace()

        _add_cutline_boundary(msp, layout, n_fit=n_fit)
        _add_notches(msp, layout)
        _add_grain_line(msp, layout)
        _add_label(msp, layout)

        output_file = output_dir / f"{name}.dxf"
        doc.saveas(str(output_file.resolve()))
        print(f"  Wrote DXF: {output_file.name}")
