"""Parametric t-shirt block that reproduces the CLO 3D default draft.

Given a `CloBlockMeasurements`, produces four `PieceLayout` pieces whose edge
count, edge order, curve shape, notch placement and seam-length relationships
match the CLO reference block.

What is different from the previous DynamicPatternGenerator
-----------------------------------------------------------
* Front and back are 10 edges, not 8.  The hem and the neckline are each split
  at the centre, which is how CLO itself indexes them and what
  clo_vto/default_panels/edge_manifest.json already expects.
* The shoulder seam is straight (the reference has zero crown) and the side
  seam is straight (zero waist suppression, just a taper from chest to hem).
* The back armhole is two Bezier segments, the front is one.
* Cap ease is negative and the cap is solved, not sampled: cap height and peak
  offset are found by a 2-D Newton solve so that each cap half matches its
  armhole plus the configured (negative) ease.
* Notches are first-class.  All four sit the same arc distance from the
  underarm on both the panel and the sleeve, which is what makes the below-
  notch seam lengths match exactly and the sleeve sew in without rotating.

Coordinate frames (millimetres, y up)
-------------------------------------
Body panels: origin at centre hem.  x = 0 is centre front / centre back,
positive x is the wearer's left as drawn (matching the DXF walk order).
Sleeve: origin at the bicep-line centre, y = 0 at the bicep line.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from .clo_draft_config import CloBlockMeasurements, CloDraftConfig, Vec2
except ImportError:  # pragma: no cover - direct script use
    from clo_draft_config import CloBlockMeasurements, CloDraftConfig, Vec2  # type: ignore

# curve_segment lives in the parent package (product_ingestion).  Support all
# three ways this module gets loaded: as part of the package, as a top-level
# module with product_ingestion already on sys.path, and as a bare script run
# from inside this directory (which is how validate_against_reference.py and
# generate_block.py are documented to be invoked).
try:
    from .curve_segment import CubicBezierSegment, PieceEdge, PieceLayout
except ImportError:  # pragma: no cover
    try:
        from curve_segment import CubicBezierSegment, PieceEdge, PieceLayout  # type: ignore
    except ImportError:
        import sys as _sys
        from pathlib import Path as _Path
        _sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
        from curve_segment import (  # type: ignore
            CubicBezierSegment, PieceEdge, PieceLayout,
        )

Point2D = Tuple[float, float]


class CapSolveError(RuntimeError):
    """The cap height / peak offset solve failed to converge."""


# --------------------------------------------------------------------------- #
# Small geometry helpers                                                        #
# --------------------------------------------------------------------------- #

def _bez_point(seg: CubicBezierSegment, t: float) -> Point2D:
    mt = 1.0 - t
    a, b, c, d = seg.p0, seg.p1, seg.p2, seg.p3
    return (
        mt ** 3 * a[0] + 3 * mt ** 2 * t * b[0] + 3 * mt * t ** 2 * c[0] + t ** 3 * d[0],
        mt ** 3 * a[1] + 3 * mt ** 2 * t * b[1] + 3 * mt * t ** 2 * c[1] + t ** 3 * d[1],
    )


def _dense(edge: PieceEdge, n: int = 400) -> List[Point2D]:
    """Densely sample an edge for arc-length work (not for output)."""
    if edge.edge_type == "straight" or not edge.segments:
        return [edge.start, edge.end]
    pts: List[Point2D] = []
    per = max(8, n // len(edge.segments))
    for seg in edge.segments:
        s = [_bez_point(seg, i / (per - 1)) for i in range(per)]
        pts.extend(s[1:] if pts else s)
    return pts


def _arc_length(edge: PieceEdge, n: int = 400) -> float:
    pts = _dense(edge, n)
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def _point_at_arc(edge: PieceEdge, distance: float, n: int = 2000
                  ) -> Tuple[Point2D, Point2D]:
    """Return (point, unit tangent) at `distance` measured from edge.start."""
    pts = _dense(edge, n)
    run = 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b)
        if run + d >= distance:
            f = 0.0 if d == 0 else (distance - run) / d
            p = (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
            t = ((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d else (1.0, 0.0)
            return p, t
        run += d
    a, b = pts[-2], pts[-1]
    d = math.dist(a, b) or 1.0
    return pts[-1], ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def _straight(name: str, a: Point2D, b: Point2D) -> PieceEdge:
    return PieceEdge(name=name, edge_type="straight", start=a, end=b)


def _cubic(name: str, p0: Point2D, c1: Point2D, c2: Point2D, p3: Point2D) -> PieceEdge:
    return PieceEdge(
        name=name, edge_type="cubic_bezier", start=p0, end=p3,
        segments=[CubicBezierSegment(p0, c1, c2, p3)],
    )


def _handle(anchor: Point2D, rel: Vec2, w: float, h: float) -> Point2D:
    """Turn a normalised (dx, dy) handle offset back into an absolute point."""
    return (anchor[0] + rel[0] * w, anchor[1] + rel[1] * h)


def _mirror_x(p: Point2D) -> Point2D:
    return (-p[0], p[1])


def _mirror_edge(edge: PieceEdge, new_name: str, reverse: bool = True) -> PieceEdge:
    """Mirror an edge about x = 0.

    reverse=True also swaps start and end.  That is what building the left
    half of a body panel needs: the mirrored copy has to be walked in the
    opposite direction so the closed loop keeps a single winding.

    reverse=False keeps the traversal direction.  That is what mirroring a
    whole sleeve needs: sleeve_right must present the same edge roles at the
    same indices as sleeve_left, which is exactly what CLO's own export does
    (its sleeve_right is sleeve_left reflected, with matching per-index edge
    lengths and the opposite signed area).
    """
    if edge.edge_type == "straight" or not edge.segments:
        a, b = _mirror_x(edge.start), _mirror_x(edge.end)
        return _straight(new_name, b, a) if reverse else _straight(new_name, a, b)

    if reverse:
        segs = [
            CubicBezierSegment(
                _mirror_x(s.p3), _mirror_x(s.p2), _mirror_x(s.p1), _mirror_x(s.p0)
            )
            for s in reversed(edge.segments)
        ]
        start, end = _mirror_x(edge.end), _mirror_x(edge.start)
    else:
        segs = [
            CubicBezierSegment(
                _mirror_x(s.p0), _mirror_x(s.p1), _mirror_x(s.p2), _mirror_x(s.p3)
            )
            for s in edge.segments
        ]
        start, end = _mirror_x(edge.start), _mirror_x(edge.end)

    return PieceEdge(
        name=new_name, edge_type=edge.edge_type,
        start=start, end=end, segments=segs,
    )


# --------------------------------------------------------------------------- #
# Notch record                                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class Notch:
    """A sleeve-match point on a piece boundary.

    `angle_deg` is the inward normal direction, which is the convention CLO
    uses on DXF layer 4 (group code 50).
    """
    piece: str
    edge_name: str
    edge_index: int
    distance_from_edge_start: float
    point: Point2D
    angle_deg: float
    role: str

    def as_dict(self) -> dict:
        return {
            "edge": self.edge_name,
            "edge_index": self.edge_index,
            "distance_mm": round(self.distance_from_edge_start, 4),
            "x": round(self.point[0], 4),
            "y": round(self.point[1], 4),
            "angle_deg": round(self.angle_deg, 3),
            "role": self.role,
        }


@dataclass
class InternalLine:
    """A construction line for DXF layer 8 (hem folds, chest line, centre)."""
    name: str
    points: List[Point2D]


# --------------------------------------------------------------------------- #
# Generator                                                                     #
# --------------------------------------------------------------------------- #

class CloTShirtDraft:
    """Build the four pattern pieces for one set of measurements.

    >>> m = CloBlockMeasurements.clo_default_M()
    >>> draft = CloTShirtDraft(m)
    >>> draft.build()
    >>> round(draft.layouts["front_panel"].edges[2].arc_length(), 2)
    289.56
    """

    PIECE_ORDER = ("front_panel", "back_panel", "sleeve_left", "sleeve_right")

    # Edge names, kept identical to clo_vto/default_panels/edge_manifest.json
    # so seams.py's by-name lookups keep working unchanged.
    FRONT_EDGE_NAMES = (
        "right_neckline", "right_shoulder", "right_armhole", "right_side",
        "right_hem", "left_hem", "left_side", "left_armhole",
        "left_shoulder", "left_neckline",
    )
    BACK_EDGE_NAMES = (
        "left_hem", "left_side", "left_armhole", "left_shoulder",
        "left_neckline", "right_neckline", "right_shoulder", "right_armhole",
        "right_side", "right_hem",
    )
    # The five sleeve names are historically rotated relative to their physical
    # role (see .agent/clo-avatar-vto/seam-edge-mapping.md).  They are kept as
    # they are to avoid desyncing seams.py; SLEEVE_EDGE_ROLES records what each
    # one actually is.
    SLEEVE_EDGE_NAMES = (
        "cuff", "right_underarm", "cap_front", "cap_back", "left_underarm",
    )
    SLEEVE_EDGE_ROLES = (
        "underarm_seam_front", "cap_half_front", "cap_half_back",
        "underarm_seam_back", "wrist_opening",
    )

    def __init__(
        self,
        measurements: CloBlockMeasurements,
        config: Optional[CloDraftConfig] = None,
    ) -> None:
        measurements.validate()
        self.m = measurements
        self.cfg = config or CloDraftConfig()

        self.layouts: Dict[str, PieceLayout] = {}
        self.notches: Dict[str, List[Notch]] = {}
        self.internal_lines: Dict[str, List[InternalLine]] = {}
        self.grainlines: Dict[str, Tuple[Point2D, Point2D]] = {}

        # Filled in by build()
        self.cap_height: float = 0.0
        self.peak_offset: float = 0.0
        self.front_armhole_length: float = 0.0
        self.back_armhole_length: float = 0.0
        self.cap_front_length: float = 0.0
        self.cap_back_length: float = 0.0
        self.solver_iterations: int = 0

    # ------------------------------------------------------------------ #
    # Derived key points                                                  #
    # ------------------------------------------------------------------ #

    @property
    def shoulder_drop(self) -> float:
        m = self.m
        return self.cfg.shoulder_slope * (m.shoulder_half_width - m.neck_half_width)

    @property
    def y_neck(self) -> float:
        return self.m.garment_length

    @property
    def y_shoulder(self) -> float:
        return self.y_neck - self.shoulder_drop

    @property
    def y_chest(self) -> float:
        return self.y_shoulder - self.m.armhole_depth

    def _back_neck_half(self) -> float:
        return self.m.neck_half_width + self.cfg.back_neck_widen_mm

    def _back_shoulder_half(self) -> float:
        """Back shoulder point.

        When `equal_shoulder_seams` is set the back shoulder line is shifted
        outboard by exactly the same amount as the back neck point, which
        makes the front and back shoulder seams identical in length to machine
        precision.  The CLO reference uses offsets that differ by 0.078 mm and
        so carries a 0.005 mm seam mismatch; matching the offsets costs at
        most 0.04 mm of positional fidelity and removes the mismatch entirely.
        """
        widen = (self.cfg.back_neck_widen_mm if self.cfg.equal_shoulder_seams
                 else self.cfg.back_shoulder_widen_mm)
        return self.m.shoulder_half_width + widen

    def _back_shoulder_y(self) -> float:
        """Back shoulder point y, using the same slope from the back neck."""
        return self.y_neck - self.cfg.shoulder_slope * (
            self._back_shoulder_half() - self._back_neck_half()
        )

    # ------------------------------------------------------------------ #
    # Body panel half-edges (right side, x > 0)                           #
    # ------------------------------------------------------------------ #

    def _neckline_half(self, is_front: bool) -> PieceEdge:
        cfg, m = self.cfg, self.m
        if is_front:
            w, depth = m.neck_half_width, m.neck_depth_front
            r1, r2 = cfg.front_neck_c1, cfg.front_neck_c2
            name = "right_neckline"
        else:
            w, depth = self._back_neck_half(), m.neck_depth_back
            r1, r2 = cfg.back_neck_c1, cfg.back_neck_c2
            name = "right_neckline"
        p0 = (0.0, self.y_neck - depth)
        p3 = (w, self.y_neck)
        return _cubic(name, p0, _handle(p0, r1, w, depth),
                      _handle(p3, r2, w, depth), p3)

    def _shoulder_half(self, is_front: bool) -> PieceEdge:
        if is_front:
            a = (self.m.neck_half_width, self.y_neck)
            b = (self.m.shoulder_half_width, self.y_shoulder)
        else:
            a = (self._back_neck_half(), self.y_neck)
            b = (self._back_shoulder_half(), self._back_shoulder_y())
        return _straight("right_shoulder", a, b)

    def _armhole_half(self, is_front: bool) -> PieceEdge:
        cfg, m = self.cfg, self.m
        if is_front:
            sh = (m.shoulder_half_width, self.y_shoulder)
            underarm = (m.half_chest_width, self.y_chest)
            w = underarm[0] - sh[0]
            h = sh[1] - underarm[1]
            return _cubic(
                "right_armhole", sh,
                _handle(sh, cfg.front_armhole_c1, w, h),
                _handle(underarm, cfg.front_armhole_c2, w, h),
                underarm,
            )
        sh = (self._back_shoulder_half(), self._back_shoulder_y())
        underarm = (m.half_chest_width, self.y_chest)
        w = underarm[0] - sh[0]
        h = sh[1] - underarm[1]
        split = (sh[0] + cfg.back_armhole_split[0] * w,
                 sh[1] + cfg.back_armhole_split[1] * h)
        upper = CubicBezierSegment(
            sh,
            _handle(sh, cfg.back_armhole_upper_c1, w, h),
            _handle(split, cfg.back_armhole_upper_c2, w, h),
            split,
        )
        lower = CubicBezierSegment(
            split,
            _handle(split, cfg.back_armhole_lower_c1, w, h),
            _handle(underarm, cfg.back_armhole_lower_c2, w, h),
            underarm,
        )
        return PieceEdge(
            name="right_armhole", edge_type="s_curve",
            start=sh, end=underarm, segments=[upper, lower],
        )

    def _side_half(self) -> PieceEdge:
        return _straight(
            "right_side",
            (self.m.half_chest_width, self.y_chest),
            (self.m.hem_half_width, 0.0),
        )

    def _hem_half(self) -> PieceEdge:
        return _straight("right_hem", (self.m.hem_half_width, 0.0), (0.0, 0.0))

    # ------------------------------------------------------------------ #
    # Body panels                                                         #
    # ------------------------------------------------------------------ #

    def _build_body_panel(self, is_front: bool) -> PieceLayout:
        """Assemble a 10-edge body panel from its mirrored halves.

        Front walk starts at the centre neck point and runs neckline ->
        shoulder -> armhole -> side -> hem -> (centre) -> mirrored half.
        Back walk starts at the centre hem and runs the other way round, which
        is exactly how CLO orders the back panel's edges.
        """
        r_neck = self._neckline_half(is_front)
        r_shoulder = self._shoulder_half(is_front)
        r_armhole = self._armhole_half(is_front)
        r_side = self._side_half()
        r_hem = self._hem_half()

        l_hem = _mirror_edge(r_hem, "left_hem")
        l_side = _mirror_edge(r_side, "left_side")
        l_armhole = _mirror_edge(r_armhole, "left_armhole")
        l_shoulder = _mirror_edge(r_shoulder, "left_shoulder")
        l_neck = _mirror_edge(r_neck, "left_neckline")

        if is_front:
            ordered = [r_neck, r_shoulder, r_armhole, r_side, r_hem,
                       l_hem, l_side, l_armhole, l_shoulder, l_neck]
            names = self.FRONT_EDGE_NAMES
            piece = "front_panel"
        else:
            # Back walk: centre hem -> left hem -> left side -> ... -> right hem
            ordered = [l_hem, l_side, l_armhole, l_shoulder, l_neck,
                       r_neck, r_shoulder, r_armhole, r_side, r_hem]
            names = self.BACK_EDGE_NAMES
            piece = "back_panel"

        # The left-hand mirrored copies come back reversed; the walk needs them
        # traversed in the direction the loop travels.
        ordered = self._orient_loop(ordered)
        for edge, nm in zip(ordered, names):
            edge.name = nm
        return PieceLayout(name=piece, edges=ordered)

    @staticmethod
    def _reverse_edge(edge: PieceEdge) -> PieceEdge:
        if edge.edge_type == "straight" or not edge.segments:
            return _straight(edge.name, edge.end, edge.start)
        segs = [CubicBezierSegment(s.p3, s.p2, s.p1, s.p0)
                for s in reversed(edge.segments)]
        return PieceEdge(name=edge.name, edge_type=edge.edge_type,
                         start=edge.end, end=edge.start, segments=segs)

    def _orient_loop(self, edges: Sequence[PieceEdge]) -> List[PieceEdge]:
        """Flip any edge whose start does not meet the previous edge's end."""
        out = [edges[0]]
        tol = 1e-6
        for e in edges[1:]:
            prev_end = out[-1].end
            if math.dist(prev_end, e.start) > tol and math.dist(prev_end, e.end) <= tol + 1e-3:
                e = self._reverse_edge(e)
            out.append(e)
        # Close the loop check
        if math.dist(out[-1].end, out[0].start) > 1e-3:
            raise ValueError(
                f"piece boundary does not close: {out[-1].end} != {out[0].start}"
            )
        return out

    # ------------------------------------------------------------------ #
    # Sleeve                                                              #
    # ------------------------------------------------------------------ #

    def _sleeve_geometry(self, cap_height: float, peak_offset: float):
        """Return the sleeve's five key points for a trial cap."""
        m, cfg = self.m, self.cfg
        half_bicep = m.bicep_full_width / 2.0
        armpit_front = (-half_bicep, 0.0)
        armpit_back = (half_bicep, 0.0)
        peak = (peak_offset, cap_height)

        taper = m.bicep_full_width - m.wrist_full_width
        front_taper = taper * cfg.sleeve_front_taper_frac
        back_taper = taper - front_taper
        wrist_front = (-half_bicep + front_taper, -m.underarm_to_wrist)
        wrist_back = (half_bicep - back_taper, -m.underarm_to_wrist)
        return armpit_front, armpit_back, peak, wrist_front, wrist_back

    def _cap_edges(self, cap_height: float, peak_offset: float
                   ) -> Tuple[PieceEdge, PieceEdge]:
        cfg = self.cfg
        af, ab, peak, _, _ = self._sleeve_geometry(cap_height, peak_offset)
        wf = peak[0] - af[0]
        wb = ab[0] - peak[0]
        h = cap_height
        front = _cubic(
            "right_underarm", af,
            _handle(af, cfg.cap_front_c1, wf, h),
            _handle(peak, cfg.cap_front_c2, wf, h),
            peak,
        )
        back = _cubic(
            "cap_front", peak,
            _handle(peak, cfg.cap_back_c1, wb, h),
            _handle(ab, cfg.cap_back_c2, wb, h),
            ab,
        )
        return front, back

    def _solve_cap(self) -> Tuple[float, float]:
        """Find (cap_height, peak_offset) matching both armholes plus ease.

        Two equations, two unknowns, solved with a damped Newton iteration
        using a numerical Jacobian.  No SciPy dependency.

        The targets come straight from the reference block's rule: each cap
        half equals its armhole arc times (1 + ease fraction), where the ease
        fractions are negative.
        """
        cfg, m = self.cfg, self.m
        target_f = self.front_armhole_length * (1.0 + cfg.cap_ease_front_frac)
        target_b = self.back_armhole_length * (1.0 + cfg.cap_ease_back_frac)

        half_bicep = m.bicep_full_width / 2.0
        h = m.bicep_full_width * cfg.cap_height_start_frac_of_bicep
        off = half_bicep * cfg.peak_offset_start_frac_of_half_bicep

        def residual(h_: float, off_: float) -> Tuple[float, float]:
            f, b = self._cap_edges(h_, off_)
            return (_arc_length(f) - target_f, _arc_length(b) - target_b)

        eps = 1e-4
        for i in range(cfg.cap_solve_max_iter):
            self.solver_iterations = i + 1
            r1, r2 = residual(h, off)
            if max(abs(r1), abs(r2)) < cfg.cap_solve_tol_mm:
                return h, off

            a11 = (residual(h + eps, off)[0] - r1) / eps
            a21 = (residual(h + eps, off)[1] - r2) / eps
            a12 = (residual(h, off + eps)[0] - r1) / eps
            a22 = (residual(h, off + eps)[1] - r2) / eps

            det = a11 * a22 - a12 * a21
            if abs(det) < 1e-12:
                raise CapSolveError(
                    "cap solve Jacobian is singular; check bicep_full_width "
                    "against the armhole lengths"
                )
            dh = (-r1 * a22 + r2 * a12) / det
            doff = (-r2 * a11 + r1 * a21) / det

            step = 1.0
            for _ in range(20):
                nh, noff = h + step * dh, off + step * doff
                if (0.05 * half_bicep < nh < 1.6 * half_bicep
                        and abs(noff) < 0.45 * half_bicep):
                    nr = residual(nh, noff)
                    if max(abs(nr[0]), abs(nr[1])) < max(abs(r1), abs(r2)):
                        h, off = nh, noff
                        break
                step *= 0.5
            else:
                raise CapSolveError(
                    f"cap solve stalled at height={h:.3f} offset={off:.3f}; "
                    f"residuals ({r1:.3f}, {r2:.3f}) mm. The bicep width is "
                    f"probably too small for an armhole of "
                    f"{self.front_armhole_length + self.back_armhole_length:.1f} mm."
                )
        raise CapSolveError(
            f"cap solve did not converge in {cfg.cap_solve_max_iter} iterations"
        )

    def _warn_on_implausible_cap(self) -> None:
        ratio = self.cap_height / self.m.bicep_full_width
        lo, hi = self.cfg.cap_height_ratio_band
        if not lo <= ratio <= hi:
            warnings.warn(
                f"cap height / bicep width = {ratio:.3f}, outside the "
                f"wearable band {lo}-{hi} (CLO reference is 0.244). The cap "
                f"satisfies the seam-length constraint but the sleeve will be "
                f"{'spiked' if ratio > hi else 'flat'}. Widen bicep_full_width "
                f"or reduce armhole_depth.",
                stacklevel=3,
            )

    def _build_sleeve(self, mirrored: bool) -> PieceLayout:
        cfg = self.cfg
        af, ab, peak, wf, wb = self._sleeve_geometry(self.cap_height, self.peak_offset)
        cap_f, cap_b = self._cap_edges(self.cap_height, self.peak_offset)

        underarm_front = _straight("cuff", wf, af)
        underarm_back = _straight("cap_back", ab, wb)

        chord = wb[0] - wf[0]
        rise = chord * cfg.wrist_rise_frac
        # Symmetric cubic bowing upward at the midpoint by `rise`.
        c1 = (wb[0] - chord / 3.0, wb[1] + rise * 4.0 / 3.0)
        c2 = (wf[0] + chord / 3.0, wf[1] + rise * 4.0 / 3.0)
        wrist = _cubic("left_underarm", wb, c1, c2, wf)

        edges = [underarm_front, cap_f, cap_b, underarm_back, wrist]
        edges = self._orient_loop(edges)
        for e, nm in zip(edges, self.SLEEVE_EDGE_NAMES):
            e.name = nm

        if mirrored:
            # Reflect in place: index -> role mapping must stay identical to
            # sleeve_left so edge_manifest.json and seams.py apply to both.
            edges = [_mirror_edge(e, e.name, reverse=False) for e in edges]

        return PieceLayout(
            name="sleeve_right" if mirrored else "sleeve_left", edges=edges
        )

    # ------------------------------------------------------------------ #
    # Notches                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _signed_area(layout: PieceLayout) -> float:
        pts = layout.polygon(24)
        return 0.5 * sum(
            a[0] * b[1] - b[0] * a[1]
            for a, b in zip(pts, pts[1:] + pts[:1])
        )

    def _make_notch(self, piece: str, layout: PieceLayout, edge_index: int,
                    distance: float, role: str, from_end: bool = False) -> Notch:
        """Place a notch, measuring from the edge's start or its end.

        `angle_deg` is the inward normal, which is the convention CLO writes
        into group code 50 on DXF layer 4.  Which way "inward" points depends
        on the piece's winding, so it is derived from the signed area rather
        than assumed: clockwise pieces (front, back, sleeve_left) take the
        tangent rotated -90 degrees, counter-clockwise (sleeve_right, which is
        a reflection) takes +90.
        """
        edge = layout.edges[edge_index]
        length = _arc_length(edge)
        d = length - distance if from_end else distance
        if not (0.0 <= d <= length):
            raise ValueError(
                f"notch at {distance:.2f} mm falls outside {piece}."
                f"{edge.name} (length {length:.2f} mm)"
            )
        point, tangent = _point_at_arc(edge, d)
        if self._signed_area(layout) < 0.0:          # clockwise
            inward = (tangent[1], -tangent[0])
        else:                                        # counter-clockwise
            inward = (-tangent[1], tangent[0])
        angle = math.degrees(math.atan2(inward[1], inward[0])) % 360.0
        return Notch(
            piece=piece, edge_name=edge.name, edge_index=edge_index,
            distance_from_edge_start=d, point=point, angle_deg=angle, role=role,
        )

    def _build_notches(self) -> None:
        cfg = self.cfg
        n1 = cfg.notch_distance(self.m.armhole_depth)
        n2 = n1 + cfg.back_notch_gap_mm

        # Front panel: edge 2 (right armhole) is walked shoulder -> underarm,
        # so its notch is measured back from the edge end; edge 7 (the
        # mirrored left armhole) is walked underarm -> shoulder, so its notch
        # is measured forward from the edge start.  Both land the same arc
        # distance from the underarm point, which is the whole point.
        f = self.layouts["front_panel"]
        self.notches["front_panel"] = [
            self._make_notch("front_panel", f, 2, n1, "front_sleeve_match", from_end=True),
            self._make_notch("front_panel", f, 7, n1, "front_sleeve_match"),
        ]

        # Back panel: index 2 (left armhole) is walked underarm -> shoulder,
        # index 7 (right armhole) shoulder -> underarm.
        b = self.layouts["back_panel"]
        self.notches["back_panel"] = [
            self._make_notch("back_panel", b, 2, n1, "back_sleeve_match_1"),
            self._make_notch("back_panel", b, 2, n2, "back_sleeve_match_2"),
            self._make_notch("back_panel", b, 7, n1, "back_sleeve_match_1", from_end=True),
            self._make_notch("back_panel", b, 7, n2, "back_sleeve_match_2", from_end=True),
        ]

        # Both sleeves index identically: edge 1 is the front cap half, walked
        # underarm -> peak; edge 2 is the back cap half, walked peak ->
        # underarm.  Distances measured from the underarm end are therefore
        # from-start on edge 1 and from-end on edge 2, on both sleeves.
        for piece in ("sleeve_left", "sleeve_right"):
            lay = self.layouts[piece]
            self.notches[piece] = [
                self._make_notch(piece, lay, 1, n1, "front_sleeve_match"),
                self._make_notch(piece, lay, 1, 0.0, "cap_peak", from_end=True),
                self._make_notch(piece, lay, 2, n1, "back_sleeve_match_1", from_end=True),
                self._make_notch(piece, lay, 2, n2, "back_sleeve_match_2", from_end=True),
            ]

    # ------------------------------------------------------------------ #
    # Construction lines and grainlines                                   #
    # ------------------------------------------------------------------ #

    def _build_internal_lines(self) -> None:
        cfg, m = self.cfg, self.m
        if not cfg.emit_internal_lines:
            for p in self.PIECE_ORDER:
                self.internal_lines[p] = []
            return

        for piece, neck_depth in (("front_panel", m.neck_depth_front),
                                  ("back_panel", m.neck_depth_back)):
            lines: List[InternalLine] = []
            for off in cfg.hem_fold_offsets_mm:
                lines.append(InternalLine(
                    f"hem_fold_{off:g}",
                    [(-m.hem_half_width, off), (m.hem_half_width, off)],
                ))
            lines.append(InternalLine(
                "chest_line",
                [(-m.half_chest_width, self.y_chest), (m.half_chest_width, self.y_chest)],
            ))
            lines.append(InternalLine(
                "centre_line", [(0.0, 0.0), (0.0, self.y_neck - neck_depth)]
            ))
            self.internal_lines[piece] = lines

        for piece in ("sleeve_left", "sleeve_right"):
            sign = -1.0 if piece == "sleeve_right" else 1.0
            af, ab, peak, wf, wb = self._sleeve_geometry(
                self.cap_height, self.peak_offset
            )
            lines = [
                InternalLine("bicep_line",
                             [(sign * af[0], 0.0), (sign * ab[0], 0.0)]),
                InternalLine("cap_centre",
                             [(sign * peak[0], peak[1]),
                              (sign * peak[0], -m.underarm_to_wrist + 6.8)]),
            ]
            chord = wb[0] - wf[0]
            rise = chord * cfg.wrist_rise_frac
            for off in cfg.sleeve_hem_fold_offsets_mm:
                pts = []
                for i in range(13):
                    t = i / 12.0
                    x = wf[0] + t * chord
                    y = wf[1] + 4.0 * rise * t * (1.0 - t) + off
                    pts.append((sign * x, y))
                lines.append(InternalLine(f"wrist_fold_{off:g}", pts))
            self.internal_lines[piece] = lines

    def _build_grainlines(self) -> None:
        half = self.cfg.grainline_length_mm / 2.0
        mid_body = self.y_chest * 0.5 + self.y_shoulder * 0.25
        for piece in ("front_panel", "back_panel"):
            self.grainlines[piece] = ((0.0, mid_body - half), (0.0, mid_body + half))
        for piece in ("sleeve_left", "sleeve_right"):
            cy = (self.cap_height - self.m.underarm_to_wrist) / 2.0
            self.grainlines[piece] = ((0.0, cy - half), (0.0, cy + half))

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    def build(self) -> Dict[str, PieceLayout]:
        """Generate all four pieces.  Idempotent."""
        self.layouts["front_panel"] = self._build_body_panel(is_front=True)
        self.layouts["back_panel"] = self._build_body_panel(is_front=False)

        self.front_armhole_length = _arc_length(self.layouts["front_panel"].edges[2])
        self.back_armhole_length = _arc_length(self.layouts["back_panel"].edges[2])

        self.cap_height, self.peak_offset = self._solve_cap()
        self._warn_on_implausible_cap()

        self.layouts["sleeve_left"] = self._build_sleeve(mirrored=False)
        self.layouts["sleeve_right"] = self._build_sleeve(mirrored=True)

        sl = self.layouts["sleeve_left"]
        self.cap_front_length = _arc_length(sl.edges[1])
        self.cap_back_length = _arc_length(sl.edges[2])

        self._build_notches()
        self._build_internal_lines()
        self._build_grainlines()
        return self.layouts

    # ---------------------------------------------------------------- #
    def seam_report(self) -> dict:
        """Everything needed to check the block sews cleanly."""
        n1 = self.cfg.notch_distance(self.m.armhole_depth)
        armhole_total = self.front_armhole_length + self.back_armhole_length
        cap_total = self.cap_front_length + self.cap_back_length
        return {
            "cap_height_mm": round(self.cap_height, 4),
            "cap_height_over_bicep": round(
                self.cap_height / self.m.bicep_full_width, 4),
            "peak_offset_mm": round(self.peak_offset, 4),
            "solver_iterations": self.solver_iterations,
            "notch_from_underarm_mm": round(n1, 4),
            "front_armhole_mm": round(self.front_armhole_length, 4),
            "back_armhole_mm": round(self.back_armhole_length, 4),
            "cap_front_mm": round(self.cap_front_length, 4),
            "cap_back_mm": round(self.cap_back_length, 4),
            "armhole_total_mm": round(armhole_total, 4),
            "cap_total_mm": round(cap_total, 4),
            "ease_mm": round(cap_total - armhole_total, 4),
            "ease_pct": round(100.0 * (cap_total - armhole_total) / armhole_total, 4),
            "below_notch_mismatch_front_mm": 0.0,
            "below_notch_mismatch_back_mm": 0.0,
            "above_notch_mismatch_front_mm": round(
                (self.cap_front_length - n1) - (self.front_armhole_length - n1), 4
            ),
            "above_notch_mismatch_back_mm": round(
                (self.cap_back_length - n1 - self.cfg.back_notch_gap_mm)
                - (self.back_armhole_length - n1 - self.cfg.back_notch_gap_mm), 4
            ),
            "shoulder_seam_mm": round(_arc_length(self.layouts["front_panel"].edges[1]), 4),
            "back_shoulder_seam_mm": round(_arc_length(self.layouts["back_panel"].edges[3]), 4),
            "side_seam_mm": round(_arc_length(self.layouts["front_panel"].edges[3]), 4),
            "sleeve_tube_front_mm": round(_arc_length(self.layouts["sleeve_left"].edges[0]), 4),
            "sleeve_tube_back_mm": round(_arc_length(self.layouts["sleeve_left"].edges[3]), 4),
        }

    def edge_manifest(self) -> dict:
        """Manifest in the shape clo_vto/default_panels/edge_manifest.json wants."""
        out: dict = {
            "_note": (
                "Generated by clo_draft.CloTShirtDraft. Front/back are 10 edges "
                "(hem and neckline split at centre), sleeves 5. Sleeve edge names "
                "are historically rotated relative to their physical role; the "
                "'role' field records what each edge actually is."
            )
        }
        for piece in self.PIECE_ORDER:
            lay = self.layouts[piece]
            entries = []
            for i, e in enumerate(lay.edges):
                entry = {"name": e.name, "index": i, "type": e.edge_type,
                         "length_mm": round(_arc_length(e), 3)}
                if piece.startswith("sleeve"):
                    entry["role"] = self.SLEEVE_EDGE_ROLES[i]
                entries.append(entry)
            out[piece] = entries
        out["notches"] = {
            p: [n.as_dict() for n in self.notches.get(p, [])]
            for p in self.PIECE_ORDER
        }
        return out

    def polygons(self, n_fit: Optional[int] = None) -> Dict[str, List[Point2D]]:
        n = n_fit or self.cfg.n_fit
        return {p: self.layouts[p].polygon(n) for p in self.PIECE_ORDER}
