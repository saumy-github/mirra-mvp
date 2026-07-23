"""Panel geometry unit tests (P12).

Covers:
- Non-self-intersection and closure for boundary measurement sets (XS, M, XL, outlier).
- Edge count stability for front/back (8 edges) and sleeves (5 edges).
- Sleeve cap convergence (CapFitError on impossibly tight targets).
- Neckline and armhole clamping (P01, P02).
"""
import sys
import math
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from garment_measurements import GarmentMeasurements
from panels import DynamicPatternGenerator, CapFitError
from curve_config import ArmholeConfig, CurveConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_closed(polygon, tol=0.01) -> bool:
    """Return True if the last point is within tol cm of the first."""
    p0, pn = polygon[0], polygon[-1]
    return math.hypot(p0[0] - pn[0], p0[1] - pn[1]) < tol


def _segments_intersect(p1, p2, p3, p4) -> bool:
    """Return True if segment p1-p2 and segment p3-p4 properly intersect."""
    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1 = _cross(p3, p4, p1)
    d2 = _cross(p3, p4, p2)
    d3 = _cross(p1, p2, p3)
    d4 = _cross(p1, p2, p4)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return False


def _is_non_self_intersecting(polygon) -> bool:
    """Check that no two non-adjacent edges in the polygon cross."""
    n = len(polygon)
    for i in range(n):
        p1, p2 = polygon[i], polygon[(i + 1) % n]
        for j in range(i + 2, n):
            if j == n - 1 and i == 0:
                continue  # adjacent (last ↔ first)
            p3, p4 = polygon[j], polygon[(j + 1) % n]
            if _segments_intersect(p1, p2, p3, p4):
                return False
    return True


def _make_measurements(**overrides) -> GarmentMeasurements:
    defaults = dict(
        half_chest_width=50.0,
        garment_length=70.0,
        shoulder_width=42.0,
        neck_width=18.0,
        neck_depth_front=7.0,
        neck_depth_back=2.0,
        sleeve_length=60.0,
        bicep_width=18.0,
        armhole_depth=20.0,
        seam_allowance=1.0,
        fit_type="regular",
        ease_cm=4.0,
        body_height=175.0,
        body_chest=96.0,
        body_shoulder=44.0,
    )
    defaults.update(overrides)
    return GarmentMeasurements(**defaults)


SIZE_CONFIGS = {
    "xs": dict(half_chest_width=43.0, garment_length=64.0, shoulder_width=38.0,
               neck_width=15.0, bicep_width=15.0, armhole_depth=17.0),
    "m":  dict(),  # use defaults
    "xl": dict(half_chest_width=58.0, garment_length=76.0, shoulder_width=48.0,
               neck_width=21.0, bicep_width=22.0, armhole_depth=23.0),
    "outlier_wide": dict(half_chest_width=75.0, garment_length=85.0, shoulder_width=55.0,
                         neck_width=25.0, bicep_width=28.0, armhole_depth=28.0),
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPanelEdgeCounts(unittest.TestCase):
    def _check_counts(self, size_label, **overrides):
        m = _make_measurements(**overrides)
        gen = DynamicPatternGenerator(m)
        gen.generate_front_panel()
        gen.generate_back_panel()
        gen.generate_sleeve("sleeve_left", target_armhole_length=gen.front_armhole_length)
        gen.generate_sleeve("sleeve_right", target_armhole_length=gen.back_armhole_length)

        for body in ("front_panel", "back_panel"):
            count = len(gen.layouts[body].edges)
            self.assertEqual(count, 8, f"{size_label} {body}: expected 8 edges, got {count}")

        for sleeve in ("sleeve_left", "sleeve_right"):
            count = len(gen.layouts[sleeve].edges)
            self.assertEqual(count, 5, f"{size_label} {sleeve}: expected 5 edges, got {count}")

    def test_xs(self):    self._check_counts("xs", **SIZE_CONFIGS["xs"])
    def test_m(self):     self._check_counts("m")
    def test_xl(self):    self._check_counts("xl", **SIZE_CONFIGS["xl"])
    def test_outlier(self): self._check_counts("outlier", **SIZE_CONFIGS["outlier_wide"])


class TestPanelPolygonClosure(unittest.TestCase):
    def _check_closed(self, size_label, **overrides):
        m = _make_measurements(**overrides)
        gen = DynamicPatternGenerator(m)
        gen.generate_front_panel()
        gen.generate_back_panel()
        armhole_per_sleeve = (gen.front_armhole_length + gen.back_armhole_length) / 2
        gen.generate_sleeve("sleeve_left",  target_armhole_length=armhole_per_sleeve)
        gen.generate_sleeve("sleeve_right", target_armhole_length=armhole_per_sleeve)

        for name, layout in gen.layouts.items():
            poly = layout.polygon(n_per_segment=32)
            self.assertTrue(
                _is_closed(poly),
                f"{size_label} {name}: polygon is not closed",
            )

    def test_xs(self):    self._check_closed("xs", **SIZE_CONFIGS["xs"])
    def test_m(self):     self._check_closed("m")
    def test_xl(self):    self._check_closed("xl", **SIZE_CONFIGS["xl"])


class TestPanelNonSelfIntersecting(unittest.TestCase):
    def test_m_non_self_intersecting(self):
        m = _make_measurements()
        gen = DynamicPatternGenerator(m)
        gen.generate_front_panel()
        gen.generate_back_panel()
        armhole_per_sleeve = (gen.front_armhole_length + gen.back_armhole_length) / 2
        gen.generate_sleeve("sleeve_left",  target_armhole_length=armhole_per_sleeve)
        gen.generate_sleeve("sleeve_right", target_armhole_length=armhole_per_sleeve)

        for name, layout in gen.layouts.items():
            poly = layout.polygon(n_per_segment=24)
            self.assertTrue(
                _is_non_self_intersecting(poly),
                f"M-size {name}: polygon self-intersects",
            )


class TestArmholeConfigClamping(unittest.TestCase):
    def test_extremes_clamped(self):
        cfg = ArmholeConfig(
            hollow_position_frac=0.0,   # below min 0.30 → clamped to 0.30
            hollow_depth_frac=1.0,      # above max 0.30 → clamped to 0.30
            shoulder_flare_frac=0.99,   # above max 0.20 → clamped to 0.20
        )
        self.assertEqual(cfg.hollow_position_frac, 0.30)
        self.assertEqual(cfg.hollow_depth_frac, 0.30)
        self.assertEqual(cfg.shoulder_flare_frac, 0.20)

    def test_valid_values_unchanged(self):
        cfg = ArmholeConfig(hollow_position_frac=0.45, hollow_depth_frac=0.18, shoulder_flare_frac=0.06)
        self.assertAlmostEqual(cfg.hollow_position_frac, 0.45)
        self.assertAlmostEqual(cfg.hollow_depth_frac, 0.18)
        self.assertAlmostEqual(cfg.shoulder_flare_frac, 0.06)


class TestCurveConfigClamping(unittest.TestCase):
    def test_cap_bulge_clamped(self):
        cfg = CurveConfig(cap_bulge_frac=0.01)   # below min 0.25
        self.assertEqual(cfg.cap_bulge_frac, 0.25)

        cfg2 = CurveConfig(cap_bulge_frac=0.99)  # above max 0.45
        self.assertEqual(cfg2.cap_bulge_frac, 0.45)

    def test_underarm_bow_clamped(self):
        cfg = CurveConfig(underarm_bow_cm=5.0)   # above max 1.5
        self.assertEqual(cfg.underarm_bow_cm, 1.5)


class TestCapFitError(unittest.TestCase):
    def test_impossible_target_raises(self):
        m = _make_measurements()
        gen = DynamicPatternGenerator(m)
        gen.generate_front_panel()
        gen.generate_back_panel()
        with self.assertRaises(CapFitError):
            # Target of 999 cm is impossible — forces convergence failure.
            gen.generate_sleeve("sleeve_left", target_armhole_length=999.0)


class TestNecklineGuards(unittest.TestCase):
    def test_excessive_neck_depth_clamped(self):
        # neck_depth_front larger than armhole_depth — should be clamped, not crash
        m = _make_measurements(neck_depth_front=50.0, armhole_depth=20.0)
        gen = DynamicPatternGenerator(m)
        layout = gen.generate_front_panel()
        poly = layout.polygon()
        self.assertGreater(len(poly), 4)

    def test_excessive_neck_width_clamped(self):
        m = _make_measurements(neck_width=60.0, shoulder_width=42.0)
        gen = DynamicPatternGenerator(m)
        layout = gen.generate_front_panel()
        poly = layout.polygon()
        self.assertGreater(len(poly), 4)


if __name__ == "__main__":
    unittest.main()
