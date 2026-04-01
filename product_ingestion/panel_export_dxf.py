"""DXF export for canonical Step 2 panel outputs.

Each PieceLayout is exported as a DXF file containing one closed LWPOLYLINE
on the CutLine layer.  CLO3D's ImportDXF function requires a single closed
boundary polygon per file (DXF-AAMA convention); multiple separate entities
are treated as internal baselines and result in 0 patterns imported.

Curve edges are sampled into LWPOLYLINE vertices at the resolution set by
n_fit.  Shared corner vertices between consecutive edges are de-duplicated
by layout.polygon(), which produces the final closed point list.

Coordinate units: centimetres internally → millimetres in DXF
(doc.units = MM so CLO imports at the correct physical size).
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    try:
        from .curve_segment import PieceLayout
    except ImportError:
        from curve_segment import PieceLayout  # type: ignore

try:
    import ezdxf
    from ezdxf import units

    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

_CM_TO_MM = 10.0


def _pt3(x: float, y: float, scale: float = _CM_TO_MM) -> tuple:
    return (x * scale, y * scale, 0.0)


def _add_cutline_boundary(msp, layout: "PieceLayout", n_fit: int) -> None:
    """Write one closed LWPOLYLINE on the CutLine layer using corner-only vertices.

    CLO3D's ImportDXF requires a single closed boundary polygon per file to
    recognise the file as a pattern piece.  Multiple separate entities (even
    on the same layer) are treated as internal baselines and produce 0
    patterns.

    Corner-only mode: one vertex per logical edge start point gives exactly
    len(edges) CLO line segments, so CLO line index i == logical edge i and
    seam manifest indices (0-7 for body, 0-4 for sleeve) map directly to the
    correct CLO lines.  A dense polygon would give 200+ CLO lines where index
    3 (for example) falls in the middle of the hem rather than on the shoulder.
    """
    if not layout.edges:
        return
    pts_mm = [
        (edge.start[0] * _CM_TO_MM, edge.start[1] * _CM_TO_MM)
        for edge in layout.edges
    ]
    msp.add_lwpolyline(
        pts_mm,
        format="xy",
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
