"""Curve primitives and pattern-piece layout.

Replaces the previous approach of immediately evaluating Bezier curves to
point lists.  Control points are kept alive so the DXF exporter can write
proper SPLINE entities and the SVG exporter can sample at any resolution.

Public surface
--------------
CubicBezierSegment   — one cubic Bezier: 4 control points
PieceEdge            — named, typed boundary edge (one or more segments)
PieceLayout          — a complete pattern piece: ordered list of PieceEdges
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from typing import List, Tuple

Point2D = Tuple[float, float]


# --------------------------------------------------------------------------- #
# Geometry primitives                                                           #
# --------------------------------------------------------------------------- #

@dataclass
class CubicBezierSegment:
    """One cubic Bezier curve defined by four control points."""
    p0: Point2D
    p1: Point2D   # first interior control point
    p2: Point2D   # second interior control point
    p3: Point2D   # end point

    def sample(self, n: int = 24) -> List[Point2D]:
        """Return n points along the curve (endpoints included)."""
        pts: List[Point2D] = []
        for i in range(n):
            t = i / (n - 1) if n > 1 else 0.0
            mt = 1.0 - t
            x = (mt**3 * self.p0[0]
                 + 3 * mt**2 * t * self.p1[0]
                 + 3 * mt * t**2 * self.p2[0]
                 + t**3 * self.p3[0])
            y = (mt**3 * self.p0[1]
                 + 3 * mt**2 * t * self.p1[1]
                 + 3 * mt * t**2 * self.p2[1]
                 + t**3 * self.p3[1])
            pts.append((x, y))
        return pts

    def arc_length(self, n: int = 64) -> float:
        """Arc length with adaptive sampling for high-curvature segments (P06).

        If either interior control point deviates from the chord by more than
        20 % of the chord length, the sample count is doubled to avoid
        under-estimating tight curves (armhole hollow, sleeve cap).
        """
        chord = hypot(self.p3[0] - self.p0[0], self.p3[1] - self.p0[1])
        if chord > 1e-6:
            def _perp_dist(p: Point2D) -> float:
                t = (
                    (p[0] - self.p0[0]) * (self.p3[0] - self.p0[0])
                    + (p[1] - self.p0[1]) * (self.p3[1] - self.p0[1])
                ) / (chord * chord)
                cx = self.p0[0] + t * (self.p3[0] - self.p0[0])
                cy = self.p0[1] + t * (self.p3[1] - self.p0[1])
                return hypot(p[0] - cx, p[1] - cy)
            max_dev = max(_perp_dist(self.p1), _perp_dist(self.p2))
            if max_dev / chord > 0.20:
                n = n * 2
        pts = self.sample(n)
        return sum(hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))

    @property
    def control_points(self) -> List[Point2D]:
        return [self.p0, self.p1, self.p2, self.p3]


# --------------------------------------------------------------------------- #
# Pattern piece edge                                                            #
# --------------------------------------------------------------------------- #

@dataclass
class PieceEdge:
    """One named, typed boundary edge of a pattern piece.

    edge_type values
    ----------------
    "straight"       — a single straight line segment (no Bezier data)
    "cubic_bezier"   — a single CubicBezierSegment
    "s_curve"        — two CubicBezierSegments joined at a shared point

    For straight edges, segments is empty and start/end are used directly.
    """
    name: str
    edge_type: str
    # Start and end are stored explicitly so straight edges need no segments.
    start: Point2D
    end: Point2D
    segments: List[CubicBezierSegment] = field(default_factory=list)

    def points(self, n_per_segment: int = 24) -> List[Point2D]:
        """Return sampled points for the whole edge.

        For straight edges: [start, end].
        For curved edges: densely sampled from each segment,
                          shared endpoints de-duplicated.
        """
        if self.edge_type == "straight" or not self.segments:
            return [self.start, self.end]

        result: List[Point2D] = []
        for seg in self.segments:
            pts = seg.sample(n_per_segment)
            if result:
                pts = pts[1:]   # skip duplicate shared endpoint
            result.extend(pts)
        return result

    def arc_length(self) -> float:
        if self.edge_type == "straight" or not self.segments:
            return hypot(self.end[0] - self.start[0],
                         self.end[1] - self.start[1])
        return sum(s.arc_length() for s in self.segments)

    def fit_points(self, n_per_segment: int = 24) -> List[Point2D]:
        """Alias for points() — used explicitly in DXF SPLINE export."""
        return self.points(n_per_segment)


# --------------------------------------------------------------------------- #
# Pattern piece layout                                                          #
# --------------------------------------------------------------------------- #

@dataclass
class PieceLayout:
    """A complete pattern piece: ordered PieceEdges forming a closed loop.

    Edges are stored in winding order (counterclockwise).  The last edge's
    end point is the same as the first edge's start point (closed loop).

    Usage
    -----
    layout.polygon()           — sampled point list for SVG / bbox checks
    layout.seam_lengths()      — dict of edge_name → arc_length (cm)
    layout.edge_manifest()     — list of dicts for edge_manifest.json
    """
    name: str
    edges: List[PieceEdge] = field(default_factory=list)
    _polygon_cache: List[Point2D] = field(default=None, init=False, repr=False)

    def polygon(self, n_per_segment: int = 24) -> List[Point2D]:
        """Sampled polygon for the whole piece (shared endpoints de-duped)."""
        if self._polygon_cache is not None:
            return self._polygon_cache
        pts: List[Point2D] = []
        for edge in self.edges:
            ep = edge.points(n_per_segment)
            if pts:
                ep = ep[1:]   # skip duplicate shared endpoint
            pts.extend(ep)
        self._polygon_cache = pts
        return pts

    def seam_lengths(self) -> dict[str, float]:
        return {e.name: round(e.arc_length(), 4) for e in self.edges}

    def edge_manifest(self) -> list[dict]:
        """Return the list of edge dicts for edge_manifest.json."""
        return [
            {"name": e.name, "type": e.edge_type, "index": i}
            for i, e in enumerate(self.edges)
        ]
