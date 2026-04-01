"""Panel generation — DynamicPatternGenerator.

Generates measurement-driven T-shirt panels as PieceLayout objects.
Each PieceLayout carries named, typed edges (straight / cubic_bezier /
s_curve) so downstream exporters can write proper DXF SPLINE entities
and SVG bezier paths rather than linear approximations.

Edge layout (0-based, counterclockwise winding)
------------------------------------------------
Front / Back panel — 8 edges:
  0  hem              straight        (0,0) → (half_chest_width, 0)
  1  right_side       cubic_bezier    right side, waist-suppression bow
  2  right_armhole    s_curve         underarm → shoulder (front concave S)
  3  right_shoulder   cubic_bezier    shoulder → neckline edge (crown bow)
  4  neckline         cubic_bezier    right neck edge → left neck edge
  5  left_shoulder    cubic_bezier    neckline edge → shoulder (crown bow)
  6  left_armhole     s_curve         shoulder → underarm (mirror of right)
  7  left_side        cubic_bezier    left side, waist-suppression bow

Sleeve — 5 edges:
  0  cuff             straight        (0,0) → (sleeve_width, 0)
  1  right_underarm   straight        right side, bottom → cap start
  2  cap_front        s_curve         right cap (front of sleeve)
  3  cap_back         s_curve         left cap (back of sleeve)
  4  left_underarm    straight        left side, cap start → bottom

Seam wiring (see seams.py):
  shoulder-right : front[3] ↔ back[3]
  shoulder-left  : front[5] ↔ back[5]
  side-right     : front[1] ↔ back[1]
  side-left      : front[7] ↔ back[7]
  sleeve-R-tube  : sleeve_right[1] ↔ sleeve_right[4]
  sleeve-L-tube  : sleeve_left[1]  ↔ sleeve_left[4]
  arm-R-front    : front[2] ↔ sleeve_right[2]   (right armhole ↔ cap_front)
  arm-R-back     : back[2]  ↔ sleeve_right[3]   (right armhole ↔ cap_back)
  arm-L-front    : front[6] ↔ sleeve_left[3]    (left armhole ↔ cap_back)
  arm-L-back     : back[6]  ↔ sleeve_left[2]    (left armhole ↔ cap_front)
"""
from __future__ import annotations

from math import hypot
from typing import List, Optional, Tuple

try:
    from .curve_config import ArmholeConfig, CurveConfig
    from .curve_segment import CubicBezierSegment, PieceEdge, PieceLayout
except ImportError:
    from curve_config import ArmholeConfig, CurveConfig  # type: ignore
    from curve_segment import CubicBezierSegment, PieceEdge, PieceLayout  # type: ignore

Point2D = Tuple[float, float]


class DynamicPatternGenerator:
    """Generate measurement-driven T-shirt panels as PieceLayout objects.

    Parameters
    ----------
    measurements : GarmentMeasurements
        The garment measurement dataclass from garment_measurements.py.
    curve_config : CurveConfig, optional
        Shape parameters.  Defaults to the standard T-shirt config.
    """

    def __init__(self, measurements, curve_config: Optional[CurveConfig] = None) -> None:
        self.m = measurements
        self.cfg = curve_config if curve_config is not None else CurveConfig()
        self.layouts: dict[str, PieceLayout] = {}

        # Seam-length trackers (cm) — set after generation
        self.front_armhole_length: float = 0.0
        self.back_armhole_length: float = 0.0
        self.sleeve_cap_length: float = 0.0

        # Legacy compatibility: patterns dict mirrors layouts but stores polygon
        # point lists so any code that still does generator.patterns["x"] works.
        self.patterns: dict[str, list] = {}

    # ------------------------------------------------------------------ #
    # Internal curve builders                                              #
    # ------------------------------------------------------------------ #

    def _straight_edge(self, name: str, start: Point2D, end: Point2D) -> PieceEdge:
        return PieceEdge(name=name, edge_type="straight", start=start, end=end)

    def _waist_side_edge(
        self,
        name: str,
        start: Point2D,
        end: Point2D,
        inward_x: float,
    ) -> PieceEdge:
        """Side seam with a gentle waist-suppression bow.

        inward_x > 0 means the bow is to the RIGHT; < 0 means to the LEFT.
        The control points place the bow at ~55% of garment height (waist).
        """
        w = inward_x
        ht = end[1] - start[1]   # signed height (may be negative for downward)
        cp1 = (start[0] + w * 0.4, start[1] + ht * 0.25)
        cp2 = (start[0] + w,       start[1] + ht * 0.55)
        seg = CubicBezierSegment(start, cp1, cp2, end)
        return PieceEdge(
            name=name, edge_type="cubic_bezier",
            start=start, end=end, segments=[seg],
        )

    def _shoulder_edge(
        self,
        name: str,
        start: Point2D,
        end: Point2D,
    ) -> PieceEdge:
        """Shoulder seam with a slight convex crown at the midpoint.

        The crown rises upward by shoulder_crown_cm, causing the seam to
        roll toward the back in 3D simulation.
        """
        crown = self.cfg.shoulder_crown_cm
        mid_x_1 = start[0] + (end[0] - start[0]) * 0.33
        mid_x_2 = start[0] + (end[0] - start[0]) * 0.67
        top_y = max(start[1], end[1]) + crown
        cp1 = (mid_x_1, top_y)
        cp2 = (mid_x_2, top_y)
        seg = CubicBezierSegment(start, cp1, cp2, end)
        return PieceEdge(
            name=name, edge_type="cubic_bezier",
            start=start, end=end, segments=[seg],
        )

    def _neckline_edge(
        self,
        name: str,
        start: Point2D,
        end: Point2D,
        neck_depth: float,
    ) -> PieceEdge:
        """Neckline curve: symmetric downward arc between shoulder points."""
        cx = (start[0] + end[0]) / 2
        cy = (start[1] + end[1]) / 2 - neck_depth
        # Degree-elevation: quadratic → cubic (lossless)
        cp1 = (start[0] + (2 / 3) * (cx - start[0]),
               start[1] + (2 / 3) * (cy - start[1]))
        cp2 = (end[0] + (2 / 3) * (cx - end[0]),
               end[1] + (2 / 3) * (cy - end[1]))
        seg = CubicBezierSegment(start, cp1, cp2, end)
        return PieceEdge(
            name=name, edge_type="cubic_bezier",
            start=start, end=end, segments=[seg],
        )

    def _armhole_edge(
        self,
        name: str,
        underarm: Point2D,
        shoulder: Point2D,
        cfg: ArmholeConfig,
        traversal: str,   # "up" = underarm→shoulder, "down" = shoulder→underarm
    ) -> PieceEdge:
        """Armhole S-curve: concave hollow near underarm, opens at shoulder.

        The S-curve is two cubic Bezier segments joined at a transition point
        located at hollow_position_frac of the armhole height.

        traversal "up" : start=underarm, end=shoulder  (right side)
        traversal "down": start=shoulder, end=underarm  (left side, mirrored)

        "Inward" is always toward the body centre (away from the arm opening).
        The inward direction is detected from the geometry:
          - right-side armhole: underarm is to the RIGHT of shoulder → inward = LEFT
          - left-side armhole: underarm is to the LEFT of shoulder → inward = RIGHT
        """
        # Determine direction independent of traversal
        arm_x, arm_y = underarm
        sh_x, sh_y = shoulder

        total_height = abs(sh_y - arm_y)
        horiz_dist = abs(sh_x - arm_x)
        if horiz_dist < 0.01:
            horiz_dist = 0.01

        # "inward" sign: underarm is further from centre than shoulder
        # right armhole: arm_x > sh_x → inward = LEFT (negative)
        # left armhole:  arm_x < sh_x → inward = RIGHT (positive)
        inward_sign = -1.0 if arm_x > sh_x else 1.0

        # Transition point at hollow_position_frac of height above underarm
        frac = cfg.hollow_position_frac
        tx = arm_x + (sh_x - arm_x) * frac
        ty = arm_y + (sh_y - arm_y) * frac
        transition = (tx, ty)

        hollow = horiz_dist * cfg.hollow_depth_frac * inward_sign
        flare  = horiz_dist * cfg.shoulder_flare_frac * (-inward_sign)

        # Lower segment (underarm → transition): deep concave hollow
        lo_cp1 = (arm_x + hollow * 0.25, arm_y + (ty - arm_y) * 0.20)
        lo_cp2 = (tx + hollow,           ty     - (ty - arm_y) * 0.05)
        lower = CubicBezierSegment(underarm, lo_cp1, lo_cp2, transition)

        # Upper segment (transition → shoulder): flatter, slight outward flare
        hi_cp1 = (tx + hollow * 0.4, ty + (sh_y - ty) * 0.05)
        hi_cp2 = (sh_x + flare,      sh_y - (sh_y - ty) * 0.10)
        upper = CubicBezierSegment(transition, hi_cp1, hi_cp2, shoulder)

        if traversal == "up":
            # underarm → shoulder
            segs = [lower, upper]
            start, end = underarm, shoulder
        else:
            # shoulder → underarm (reverse both segments and their order)
            rev_lower = CubicBezierSegment(transition, lo_cp2, lo_cp1, underarm)
            rev_upper = CubicBezierSegment(shoulder, hi_cp2, hi_cp1, transition)
            segs = [rev_upper, rev_lower]
            start, end = shoulder, underarm

        return PieceEdge(
            name=name, edge_type="s_curve",
            start=start, end=end, segments=segs,
        )

    def _build_cap_pair(
        self, cap_height: float
    ) -> tuple[PieceEdge, PieceEdge, float]:
        """Build cap_front and cap_back edges and return total arc length.

        sleeve_width is the full unfolded sleeve width (bicep_width * 2).
        bicep_width is the flat seam-to-seam half-girth, so the full tube
        circumference = bicep_width * 2.  Using the correct full width gives
        a naturally wide base, which means the binary search converges at a
        shallow cap_height (the correct "rectangle + shallow cap" shape).

        A small outward bulge on the control points adds curvature so the arc
        length grows monotonically with cap_height, which is required for the
        binary search to converge reliably.
        """
        m = self.m
        sleeve_width = m.bicep_width * 2

        cap_start_y = m.sleeve_length - cap_height
        apex = (sleeve_width / 2, m.sleeve_length + cap_height * 0.25)
        right_ua = (sleeve_width, cap_start_y)
        left_ua = (0.0, cap_start_y)

        # Outward bulge: how far the cap curves protrude beyond the sleeve body.
        # Tuned so arc length ≈ target at a moderate cap_height; binary search
        # finds the exact value.
        bulge = cap_height * 0.35

        # cap_front: right underarm → apex, control points RIGHT of sleeve_width
        f_cp1 = (sleeve_width + bulge,           cap_start_y + cap_height * 0.40)
        f_cp2 = (sleeve_width / 2 + bulge * 0.4, m.sleeve_length + cap_height * 0.20)
        front_seg = CubicBezierSegment(right_ua, f_cp1, f_cp2, apex)
        cap_front = PieceEdge(
            name="cap_front", edge_type="cubic_bezier",
            start=right_ua, end=apex, segments=[front_seg],
        )

        # cap_back: apex → left underarm, control points LEFT of 0
        b_cp1 = (sleeve_width / 2 - bulge * 0.4, m.sleeve_length + cap_height * 0.20)
        b_cp2 = (-bulge,                          cap_start_y + cap_height * 0.40)
        back_seg = CubicBezierSegment(apex, b_cp1, b_cp2, left_ua)
        cap_back = PieceEdge(
            name="cap_back", edge_type="cubic_bezier",
            start=apex, end=left_ua, segments=[back_seg],
        )

        total_arc = cap_front.arc_length() + cap_back.arc_length()
        return cap_front, cap_back, total_arc

    # ------------------------------------------------------------------ #
    # Panel generators                                                     #
    # ------------------------------------------------------------------ #

    def _make_body_panel(
        self, name: str, neck_depth: float, armhole_cfg: ArmholeConfig
    ) -> PieceLayout:
        m = self.m
        cfg = self.cfg

        half_w = m.half_chest_width
        center_x = half_w / 2
        r_shoulder = center_x + m.shoulder_width / 2
        l_shoulder = center_x - m.shoulder_width / 2
        r_neck = center_x + m.neck_width / 2
        l_neck = center_x - m.neck_width / 2
        armhole_start_y = m.garment_length - m.armhole_depth
        top_y = m.garment_length

        # --- 8 edges in counterclockwise winding order ---

        # 0: hem — straight bottom
        hem = self._straight_edge("hem", (0.0, 0.0), (half_w, 0.0))

        # 1: right_side — waist bow toward centre (LEFT = negative x)
        r_side = self._waist_side_edge(
            "right_side",
            start=(half_w, 0.0),
            end=(half_w, armhole_start_y),
            inward_x=-cfg.side_waist_suppression_cm,
        )

        # 2: right_armhole — S-curve from underarm UP to shoulder
        r_armhole = self._armhole_edge(
            "right_armhole",
            underarm=(half_w, armhole_start_y),
            shoulder=(r_shoulder, top_y),
            cfg=armhole_cfg,
            traversal="up",
        )

        # 3: right_shoulder — crown bow from shoulder corner to neckline edge
        r_shoulder_edge = self._shoulder_edge(
            "right_shoulder",
            start=(r_shoulder, top_y),
            end=(r_neck, top_y),
        )

        # 4: neckline — downward arc from right neck edge to left neck edge
        neckline = self._neckline_edge(
            "neckline",
            start=(r_neck, top_y),
            end=(l_neck, top_y),
            neck_depth=neck_depth,
        )

        # 5: left_shoulder — crown bow from neckline edge to left shoulder corner
        l_shoulder_edge = self._shoulder_edge(
            "left_shoulder",
            start=(l_neck, top_y),
            end=(l_shoulder, top_y),
        )

        # 6: left_armhole — S-curve from shoulder DOWN to underarm (mirrored)
        l_armhole = self._armhole_edge(
            "left_armhole",
            underarm=(0.0, armhole_start_y),
            shoulder=(l_shoulder, top_y),
            cfg=armhole_cfg,
            traversal="down",
        )

        # 7: left_side — waist bow toward centre (RIGHT = positive x)
        l_side = self._waist_side_edge(
            "left_side",
            start=(0.0, armhole_start_y),
            end=(0.0, 0.0),
            inward_x=cfg.side_waist_suppression_cm,
        )

        layout = PieceLayout(
            name=name,
            edges=[hem, r_side, r_armhole, r_shoulder_edge,
                   neckline, l_shoulder_edge, l_armhole, l_side],
        )
        return layout

    def generate_front_panel(self) -> PieceLayout:
        layout = self._make_body_panel(
            name="front_panel",
            neck_depth=self.m.neck_depth_front,
            armhole_cfg=self.cfg.front_armhole,
        )
        # Armhole arc length = right + left (both use same cfg so same shape)
        r_arc = layout.edges[2].arc_length()
        l_arc = layout.edges[6].arc_length()
        self.front_armhole_length = r_arc + l_arc
        self.layouts["front_panel"] = layout
        self.patterns["front_panel"] = layout.polygon()
        return layout

    def generate_back_panel(self) -> PieceLayout:
        layout = self._make_body_panel(
            name="back_panel",
            neck_depth=self.m.neck_depth_back,
            armhole_cfg=self.cfg.back_armhole,
        )
        r_arc = layout.edges[2].arc_length()
        l_arc = layout.edges[6].arc_length()
        self.back_armhole_length = r_arc + l_arc
        self.layouts["back_panel"] = layout
        self.patterns["back_panel"] = layout.polygon()
        return layout

    def generate_sleeve(
        self,
        piece_name: str = "sleeve_left",
        target_armhole_length: Optional[float] = None,
    ) -> PieceLayout:
        """Generate one sleeve with a binary-search-fitted cap.

        Parameters
        ----------
        piece_name : str
            "sleeve_left" or "sleeve_right".
        target_armhole_length : float, optional
            One armhole's arc length (front or back average).  If given the
            binary search adjusts cap_height until:
              cap_arc ≈ target_armhole_length + cfg.cap_ease_cm
        """
        m = self.m
        cfg = self.cfg
        # Full unfolded sleeve width = full tube circumference.
        # bicep_width is the flat half-girth (seam-to-seam), so multiply by 2.
        sleeve_width = m.bicep_width * 2

        if target_armhole_length is None:
            cap_height = m.armhole_depth * cfg.cap_height_start_frac
            cap_front, cap_back, total_arc = self._build_cap_pair(cap_height)
        else:
            target = target_armhole_length + cfg.cap_ease_cm
            lo = m.armhole_depth * cfg.cap_height_min_frac
            hi = m.armhole_depth * cfg.cap_height_max_frac
            cap_height = (lo + hi) / 2.0

            cap_front, cap_back, total_arc = self._build_cap_pair(cap_height)

            for _ in range(cfg.cap_search_max_iter):
                error = total_arc - target
                if abs(error) <= cfg.cap_ease_tolerance_cm:
                    break
                if error < 0:
                    lo = cap_height        # cap too short → grow
                else:
                    hi = cap_height        # cap too long  → shrink
                cap_height = (lo + hi) / 2.0
                cap_front, cap_back, total_arc = self._build_cap_pair(cap_height)

        cap_start_y = m.sleeve_length - cap_height

        # --- 5 edges ---

        # 0: cuff — straight bottom
        cuff = self._straight_edge(
            "cuff", (0.0, 0.0), (sleeve_width, 0.0)
        )

        # 1: right_underarm — straight right side up to cap
        r_under = self._straight_edge(
            "right_underarm", (sleeve_width, 0.0), (sleeve_width, cap_start_y)
        )

        # 2: cap_front — right half of cap (built above)
        # 3: cap_back  — left half of cap (built above)

        # 4: left_underarm — straight left side back down
        l_under = self._straight_edge(
            "left_underarm", (0.0, cap_start_y), (0.0, 0.0)
        )

        layout = PieceLayout(
            name=piece_name,
            edges=[cuff, r_under, cap_front, cap_back, l_under],
        )

        self.sleeve_cap_length = total_arc
        self.layouts[piece_name] = layout
        self.patterns[piece_name] = layout.polygon()
        return layout
