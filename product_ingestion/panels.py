"""Panel generation utilities extracted from generate_patterns_clo3d.

This module provides a lightweight `DynamicPatternGenerator` that mirrors the
pattern-generation API used by the canonical pipeline without using the word
"pattern" in the module name (project convention: use "panel" for pieces).
"""

from __future__ import annotations

from math import hypot
from typing import List, Tuple


class DynamicPatternGenerator:
    """Generate simple measurement-driven T-shirt panels.

    Public API matches the original generator enough for `panel_generation.py`:
    - `m`: garment measurements object with expected attributes
    - `patterns`: dict of piece_name -> list[(x,y)]
    - `generate_front_panel()`, `generate_back_panel()`, `generate_sleeve()`
    - seam length trackers: `front_armhole_length`, `back_armhole_length`, `sleeve_cap_length`
    """

    def __init__(self, measurements) -> None:
        self.m = measurements
        self.patterns: dict[str, list[tuple[float, float]]] = {}
        self.curve_smoothness = 6
        self.front_armhole_length = 0.0
        self.back_armhole_length = 0.0
        self.sleeve_cap_length = 0.0

    def _generate_curve(self, start: Tuple[float, float], end: Tuple[float, float], control_offset: Tuple[float, float], num_points: int = 6):
        sx, sy = start
        ex, ey = end
        cx = (sx + ex) / 2 + control_offset[0]
        cy = (sy + ey) / 2 + control_offset[1]

        points: List[Tuple[float, float]] = []
        for i in range(num_points):
            t = i / (num_points - 1) if num_points > 1 else 0
            x = (1 - t) * (1 - t) * sx + 2 * (1 - t) * t * cx + t * t * ex
            y = (1 - t) * (1 - t) * sy + 2 * (1 - t) * t * cy + t * t * ey
            points.append((x, y))

        arc = 0.0
        for a, b in zip(points, points[1:]):
            arc += hypot(b[0] - a[0], b[1] - a[1])
        return points, arc

    def generate_front_panel(self) -> List[Tuple[float, float]]:
        m = self.m
        points: List[Tuple[float, float]] = []

        center_x = m.half_chest_width / 2
        left_shoulder_x = center_x - (m.shoulder_width / 2)
        right_shoulder_x = center_x + (m.shoulder_width / 2)

        points.append((0, 0))
        points.append((m.half_chest_width, 0))

        armhole_start_y = m.garment_length - m.armhole_depth
        points.append((m.half_chest_width, armhole_start_y))

        armhole_end_y = m.garment_length - m.neck_depth_front
        right_armhole_curve, right_arc = self._generate_curve(
            (m.half_chest_width, armhole_start_y),
            (right_shoulder_x, armhole_end_y),
            control_offset=(-max(1.0, (m.half_chest_width - right_shoulder_x) * 0.3), 0),
            num_points=self.curve_smoothness,
        )
        points.extend(right_armhole_curve[1:])

        points.append((right_shoulder_x, m.garment_length))

        neckline_curve, neck_arc = self._generate_curve(
            (right_shoulder_x, m.garment_length),
            (left_shoulder_x, m.garment_length),
            control_offset=(0, -m.neck_depth_front),
            num_points=5,
        )
        points.extend(neckline_curve[1:-1])

        points.append((left_shoulder_x, m.garment_length))
        left_armhole_curve, left_arc = self._generate_curve(
            (left_shoulder_x, armhole_end_y),
            (0, armhole_start_y),
            control_offset=(-max(1.0, left_shoulder_x * 0.3), 0),
            num_points=self.curve_smoothness,
        )
        points.extend(left_armhole_curve)

        self.front_armhole_length = right_arc + left_arc
        self.patterns["front_panel"] = points
        return points

    def generate_back_panel(self) -> List[Tuple[float, float]]:
        m = self.m
        points: List[Tuple[float, float]] = []

        center_x = m.half_chest_width / 2
        left_shoulder_x = center_x - (m.shoulder_width / 2)
        right_shoulder_x = center_x + (m.shoulder_width / 2)

        points.append((0, 0))
        points.append((m.half_chest_width, 0))

        armhole_start_y = m.garment_length - m.armhole_depth
        points.append((m.half_chest_width, armhole_start_y))

        armhole_end_y = m.garment_length - m.neck_depth_back
        right_curve, right_arc = self._generate_curve(
            (m.half_chest_width, armhole_start_y),
            (right_shoulder_x, armhole_end_y),
            control_offset=(-max(1.0, (m.half_chest_width - right_shoulder_x) * 0.3), 0),
            num_points=self.curve_smoothness,
        )
        points.extend(right_curve[1:])

        points.append((right_shoulder_x, m.garment_length))

        neckline_curve, neck_arc = self._generate_curve(
            (right_shoulder_x, m.garment_length),
            (left_shoulder_x, m.garment_length),
            control_offset=(0, -m.neck_depth_back),
            num_points=4,
        )
        points.extend(neckline_curve[1:-1])

        points.append((left_shoulder_x, m.garment_length))
        left_curve, left_arc = self._generate_curve(
            (left_shoulder_x, armhole_end_y),
            (0, armhole_start_y),
            control_offset=(-max(1.0, left_shoulder_x * 0.3), 0),
            num_points=self.curve_smoothness,
        )
        points.extend(left_curve)

        self.back_armhole_length = right_arc + left_arc
        self.patterns["back_panel"] = points
        return points

    def generate_sleeve(self, target_armhole_length: float = None) -> List[Tuple[float, float]]:
        m = self.m
        sleeve_width = m.bicep_width / 2
        sleeve_length = m.sleeve_length

        if target_armhole_length is None:
            cap_height = m.armhole_depth * 0.35
        else:
            cap_height = m.armhole_depth * 0.35

        points: List[Tuple[float, float]] = []
        points.append((0, 0))
        points.append((sleeve_width, 0))

        cap_start_y = sleeve_length - cap_height
        points.append((sleeve_width, cap_start_y))

        cap_top_x = sleeve_width / 2
        cap_top_y = sleeve_length + cap_height * 0.15

        right_cap, right_arc = self._generate_curve(
            (sleeve_width, cap_start_y),
            (cap_top_x, cap_top_y),
            control_offset=(-sleeve_width * 0.15, cap_height * 0.3),
            num_points=self.curve_smoothness,
        )
        points.extend(right_cap[1:])

        left_cap, left_arc = self._generate_curve(
            (cap_top_x, cap_top_y),
            (0, cap_start_y),
            control_offset=(sleeve_width * 0.15, cap_height * 0.3),
            num_points=self.curve_smoothness,
        )
        points.extend(left_cap[1:])

        self.sleeve_cap_length = right_arc + left_arc
        self.patterns.setdefault("sleeve_left", points)
        return points
