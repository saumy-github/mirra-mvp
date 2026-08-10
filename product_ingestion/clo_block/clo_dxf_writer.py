"""AAMA/ASTM DXF writer that mirrors CLO 3D's own export structure.

Why not ezdxf
-------------
The existing panel_export_dxf.py writes an LWPOLYLINE on a layer literally
named "CutLine".  Both choices are wrong for this target:

* CLO exports DXF R12 (`$ACADVER = AC1009`).  LWPOLYLINE does not exist in R12
  — it arrived with R14.  Readers that take the version header seriously will
  reject or silently skip it.
* AAMA/ASTM pattern DXF identifies content by NUMERIC layer, not by name.  A
  layer called "CutLine" carries no meaning; layer "1" does.

The reference files use exactly this structure, so this writer reproduces it:

    layer 1   closed POLYLINE — the sewing line, the boundary CLO reads
    layer 2   POINT per turn point (corner between two named edges)
    layer 3   POINT per curve point (interior tessellation vertices)
    layer 4   POINT per notch, with Z = 7.0 and code 50 = inward normal angle
    layer 7   LINE — grainline
    layer 8   POLYLINE — internal construction lines
    layer 1   TEXT — piece label

Geometry lives inside a BLOCK which is INSERTed once at the origin, again
matching CLO.

Seam allowance
--------------
The reference files contain none: layers 84 and 87 duplicate layer 1 to within
0.15 mm. `seam_allowance_mm` therefore defaults to 0 and, when set, is written
as a separate offset POLYLINE on layer 84 rather than replacing layer 1.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

try:
    from .clo_draft import CloTShirtDraft, InternalLine, Notch
except ImportError:  # pragma: no cover
    from clo_draft import CloTShirtDraft, InternalLine, Notch  # type: ignore

Point2D = Tuple[float, float]

LAYER_BOUNDARY = "1"
LAYER_TURN_POINT = "2"
LAYER_CURVE_POINT = "3"
LAYER_NOTCH = "4"
LAYER_GRAINLINE = "7"
LAYER_INTERNAL = "8"
LAYER_SEAM_ALLOWANCE = "84"

# CLO names its blocks <pattern index>_<size label>.
BLOCK_INDEX = {
    "front_panel": 1,
    "back_panel": 2,
    "sleeve_left": 3,
    "sleeve_right": 7,
}


# --------------------------------------------------------------------------- #
# Low-level group-code emission                                                 #
# --------------------------------------------------------------------------- #

class _Writer:
    def __init__(self) -> None:
        self.buf: List[str] = []

    def g(self, code: int, value) -> None:
        self.buf.append(str(code))
        if isinstance(value, float):
            self.buf.append(f"{value:.6f}")
        else:
            self.buf.append(str(value))

    def text(self) -> str:
        return "\n".join(self.buf) + "\n"

    # -- entities ---------------------------------------------------- #
    def polyline(self, layer: str, pts: Sequence[Point2D], closed: bool) -> None:
        if len(pts) < 2:
            return
        self.g(0, "POLYLINE")
        self.g(8, layer)
        self.g(66, 1)
        self.g(70, 1 if closed else 0)
        self.g(10, 0.0)
        self.g(20, 0.0)
        self.g(30, 0.0)
        for x, y in pts:
            self.g(0, "VERTEX")
            self.g(8, layer)
            self.g(10, float(x))
            self.g(20, float(y))
            self.g(30, 0.0)
        self.g(0, "SEQEND")
        self.g(8, layer)

    def point(self, layer: str, p: Point2D, z: float = 0.0,
              angle: Optional[float] = None) -> None:
        self.g(0, "POINT")
        self.g(8, layer)
        self.g(10, float(p[0]))
        self.g(20, float(p[1]))
        self.g(30, float(z))
        if angle is not None:
            self.g(50, float(angle))

    def line(self, layer: str, a: Point2D, b: Point2D) -> None:
        self.g(0, "LINE")
        self.g(8, layer)
        self.g(10, float(a[0]))
        self.g(20, float(a[1]))
        self.g(30, 0.0)
        self.g(11, float(b[0]))
        self.g(21, float(b[1]))
        self.g(31, 0.0)

    def text_entity(self, layer: str, p: Point2D, value: str,
                    height: float = 20.0) -> None:
        self.g(0, "TEXT")
        self.g(8, layer)
        self.g(10, float(p[0]))
        self.g(20, float(p[1]))
        self.g(30, 0.0)
        self.g(40, float(height))
        self.g(1, value)


# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #

def _offset_polygon(pts: Sequence[Point2D], distance: float) -> List[Point2D]:
    """Outward offset of a closed polygon by `distance`.

    Vertex-normal offset with a mitre limit.  Good enough for a seam-allowance
    line, which is a cutting guide rather than a sewing reference; it is not a
    general-purpose straight skeleton and will misbehave on very sharp spikes,
    which pattern pieces do not have.
    """
    n = len(pts)
    area = 0.5 * sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1]
                     for i in range(n))
    sign = -1.0 if area < 0 else 1.0
    out: List[Point2D] = []
    for i in range(n):
        prev_p, cur, nxt = pts[(i - 1) % n], pts[i], pts[(i + 1) % n]
        n1 = _unit_normal(prev_p, cur, sign)
        n2 = _unit_normal(cur, nxt, sign)
        bx, by = n1[0] + n2[0], n1[1] + n2[1]
        mag = math.hypot(bx, by)
        if mag < 1e-9:
            bx, by, mag = n2[0], n2[1], 1.0
        bx, by = bx / mag, by / mag
        cos_half = max(0.25, bx * n2[0] + by * n2[1])   # mitre limit 4x
        out.append((cur[0] + bx * distance / cos_half,
                    cur[1] + by * distance / cos_half))
    return out


def _unit_normal(a: Point2D, b: Point2D, sign: float) -> Point2D:
    dx, dy = b[0] - a[0], b[1] - a[1]
    d = math.hypot(dx, dy) or 1.0
    return (sign * dy / d, -sign * dx / d)


def _turn_points(draft: CloTShirtDraft, piece: str) -> List[Point2D]:
    return [e.start for e in draft.layouts[piece].edges]


# --------------------------------------------------------------------------- #
# Public API                                                                    #
# --------------------------------------------------------------------------- #

def build_piece_dxf(
    draft: CloTShirtDraft,
    piece: str,
    *,
    size_label: Optional[str] = None,
    n_fit: Optional[int] = None,
    include_curve_points: bool = True,
) -> str:
    """Render one pattern piece as a complete AAMA R12 DXF document."""
    cfg = draft.cfg
    n = n_fit or cfg.n_fit
    label = size_label or draft.m.label
    layout = draft.layouts[piece]
    boundary = layout.polygon(n)

    # polygon() repeats the closing point when edges chain; drop any duplicate
    # so the closed POLYLINE flag does not create a zero-length segment.
    if len(boundary) > 1 and math.dist(boundary[0], boundary[-1]) < 1e-6:
        boundary = boundary[:-1]

    xs = [p[0] for p in boundary]
    ys = [p[1] for p in boundary]
    block_name = f"{BLOCK_INDEX.get(piece, 0)}_{label}"

    w = _Writer()

    # ---- HEADER ----------------------------------------------------- #
    w.g(0, "SECTION")
    w.g(2, "HEADER")
    w.g(9, "$ACADVER")
    w.g(1, "AC1009")
    w.g(9, "$INSUNITS")
    w.g(70, 4)                       # 4 = millimetres
    w.g(9, "$MEASUREMENT")
    w.g(70, 1)                       # 1 = metric
    w.g(9, "$EXTMIN")
    w.g(10, min(xs))
    w.g(20, min(ys))
    w.g(30, 0.0)
    w.g(9, "$EXTMAX")
    w.g(10, max(xs))
    w.g(20, max(ys))
    w.g(30, 0.0)
    w.g(0, "ENDSEC")

    # ---- TABLES ----------------------------------------------------- #
    layers = [LAYER_BOUNDARY, LAYER_TURN_POINT, LAYER_CURVE_POINT, LAYER_NOTCH,
              LAYER_GRAINLINE, LAYER_INTERNAL, "0", "Defpoints"]
    if cfg.seam_allowance_mm > 0:
        layers.append(LAYER_SEAM_ALLOWANCE)
    w.g(0, "SECTION")
    w.g(2, "TABLES")
    w.g(0, "TABLE")
    w.g(2, "LAYER")
    w.g(70, len(layers))
    for name in layers:
        w.g(0, "LAYER")
        w.g(2, name)
        w.g(70, 0)
        w.g(62, 7)
        w.g(6, "CONTINUOUS")
    w.g(0, "ENDTAB")
    w.g(0, "ENDSEC")

    # ---- BLOCKS ----------------------------------------------------- #
    w.g(0, "SECTION")
    w.g(2, "BLOCKS")
    w.g(0, "BLOCK")
    w.g(8, "0")
    w.g(2, block_name)
    w.g(70, 0)
    w.g(10, 0.0)
    w.g(20, 0.0)
    w.g(30, 0.0)
    w.g(3, block_name)

    w.polyline(LAYER_BOUNDARY, boundary, closed=True)

    if cfg.seam_allowance_mm > 0:
        w.polyline(LAYER_SEAM_ALLOWANCE,
                   _offset_polygon(boundary, cfg.seam_allowance_mm), closed=True)

    turns = _turn_points(draft, piece)
    for p in turns:
        w.point(LAYER_TURN_POINT, p)

    if include_curve_points:
        turn_set = [(round(p[0], 4), round(p[1], 4)) for p in turns]
        for p in boundary:
            if (round(p[0], 4), round(p[1], 4)) not in turn_set:
                w.point(LAYER_CURVE_POINT, p)

    for notch in draft.notches.get(piece, []):
        w.point(LAYER_NOTCH, notch.point, z=7.0, angle=notch.angle_deg)

    for line in draft.internal_lines.get(piece, []):
        w.polyline(LAYER_INTERNAL, line.points, closed=False)

    a, b = draft.grainlines[piece]
    w.line(LAYER_GRAINLINE, a, b)

    w.text_entity(LAYER_BOUNDARY,
                  (min(xs), max(ys) + 10.0),
                  f"{piece} {label}")

    w.g(0, "ENDBLK")
    w.g(8, "0")
    w.g(0, "ENDSEC")

    # ---- ENTITIES --------------------------------------------------- #
    w.g(0, "SECTION")
    w.g(2, "ENTITIES")
    w.g(0, "INSERT")
    w.g(8, LAYER_BOUNDARY)
    w.g(2, block_name)
    w.g(10, 0.0)
    w.g(20, 0.0)
    w.g(30, 0.0)
    w.g(0, "ENDSEC")
    w.g(0, "EOF")
    return w.text()


def write_pattern_set(
    draft: CloTShirtDraft,
    out_dir,
    *,
    size_label: Optional[str] = None,
    n_fit: Optional[int] = None,
    include_curve_points: bool = True,
) -> Dict[str, Path]:
    """Write all four pieces as DXF files and return {piece: path}."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written: Dict[str, Path] = {}
    for piece in CloTShirtDraft.PIECE_ORDER:
        path = out / f"{piece}.dxf"
        path.write_text(build_piece_dxf(
            draft, piece, size_label=size_label, n_fit=n_fit,
            include_curve_points=include_curve_points,
        ))
        written[piece] = path
    return written


def write_svg(draft: CloTShirtDraft, path, *, n_fit: Optional[int] = None) -> Path:
    """Flat-lay SVG of all four pieces with notches, for eyeballing a run."""
    n = n_fit or draft.cfg.n_fit
    offsets = {
        "front_panel": (0.0, 0.0),
        "back_panel": (700.0, 0.0),
        "sleeve_left": (1400.0, 0.0),
        "sleeve_right": (1400.0, -450.0),
    }
    body: List[str] = []
    xs: List[float] = []
    ys: List[float] = []
    for piece, (ox, oy) in offsets.items():
        pts = [(p[0] + ox, -(p[1] + oy)) for p in draft.layouts[piece].polygon(n)]
        xs += [p[0] for p in pts]
        ys += [p[1] for p in pts]
        d = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in pts) + " Z"
        body.append(f'<path d="{d}" fill="#B5D4F4" fill-opacity="0.3" '
                    f'stroke="#2C2C2A" stroke-width="2"/>')
        for line in draft.internal_lines.get(piece, []):
            lp = [(p[0] + ox, -(p[1] + oy)) for p in line.points]
            ld = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in lp)
            body.append(f'<path d="{ld}" fill="none" stroke="#8a8880" '
                        f'stroke-width="1.2" stroke-dasharray="8 6"/>')
        ga, gb = draft.grainlines[piece]
        body.append(f'<path d="M {ga[0]+ox:.2f},{-(ga[1]+oy):.2f} '
                    f'L {gb[0]+ox:.2f},{-(gb[1]+oy):.2f}" '
                    f'stroke="#D85A30" stroke-width="2"/>')
        for notch in draft.notches.get(piece, []):
            body.append(f'<circle cx="{notch.point[0]+ox:.2f}" '
                        f'cy="{-(notch.point[1]+oy):.2f}" r="7" fill="none" '
                        f'stroke="#D85A30" stroke-width="2.5"/>')
    pad = 40
    vb = (min(xs) - pad, min(ys) - pad,
          max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
           f'viewBox="{vb[0]:.1f} {vb[1]:.1f} {vb[2]:.1f} {vb[3]:.1f}">'
           + "".join(body) + "</svg>")
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(svg)
    return p
