"""Panel geometry unit tests for the CLO reference block.

Rewritten for `clo_block/` — the old suite asserted the superseded 8-edge
layout, positive cap ease and the `panels.py` / `curve_config.py` clamps, none
of which describe the current generator.

Covers:
- Edge counts: 10 per body panel, 5 per sleeve.
- Closure and non-self-intersection across the size range.
- Cap ease is NEGATIVE — a jersey cap is shorter than its armhole on purpose.
- Below-notch seam lengths match, which is what the notches exist to pin.
- The generated edge_manifest.json drives seams.py:load_seams_from_manifest()
  to exactly the DEFAULT_SEAMS wiring.
"""
import json
import math
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

_PRODUCT_INGESTION = Path(__file__).resolve().parent.parent
_ROOT = _PRODUCT_INGESTION.parent
for _p in (str(_PRODUCT_INGESTION), str(_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from garment_measurements import GarmentMeasurements  # noqa: E402
from clo_block import CloTShirtDraft, CloBlockMeasurements  # noqa: E402
from clo_block.clo_draft import _arc_length  # noqa: E402
from panel_generation_clo import (  # noqa: E402
    garment_to_clo_block,
    generate_panels,
    recommend_bicep_width_cm,
)

BODY_EDGE_COUNT = 5 + 5      # right/left halves, hem and neckline each split
SLEEVE_EDGE_COUNT = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _polygon(layout, n_per_segment: int = 24):
    """Dense outline of a PieceLayout as a list of (x, y)."""
    return [tuple(p) for p in layout.polygon(n_per_segment=n_per_segment)]


def _is_closed(polygon, tol=0.01) -> bool:
    p0, pn = polygon[0], polygon[-1]
    return math.hypot(p0[0] - pn[0], p0[1] - pn[1]) < tol


def _segments_intersect(p1, p2, p3, p4) -> bool:
    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    d1, d2 = _cross(p3, p4, p1), _cross(p3, p4, p2)
    d3, d4 = _cross(p1, p2, p3), _cross(p1, p2, p4)
    return (((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and
            ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)))


def _is_non_self_intersecting(polygon) -> bool:
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
    """A size that satisfies recommend_bicep_width_cm(), unlike the old default.

    bicep_width 21.8 against armhole_depth 24.0 is the s_001 pairing from
    INTEGRATION.md section 6 — it puts the cap at the CLO reference 0.244 of
    the bicep width.
    """
    defaults = dict(
        half_chest_width=52.0,
        garment_length=71.0,
        shoulder_width=46.0,
        neck_width=18.0,
        neck_depth_front=9.0,
        neck_depth_back=2.5,
        sleeve_length=21.0,
        bicep_width=21.8,
        armhole_depth=24.0,
        seam_allowance=1.0,
        fit_type="regular",
        ease_cm=0.0,
        body_height=175.0,
        body_chest=96.0,
        body_shoulder=46.0,
    )
    defaults.update(overrides)
    return GarmentMeasurements(**defaults)


# Sizes spanning the seeded range, each with a bicep proportionate to its
# armhole (values from recommend_bicep_width_cm).
SIZE_CONFIGS = {
    "xs": dict(half_chest_width=43.0, garment_length=60.0, shoulder_width=37.0,
               neck_width=16.0, sleeve_length=15.0, bicep_width=18.4,
               armhole_depth=20.0),
    "m":  dict(),
    "xl": dict(half_chest_width=61.0, garment_length=77.0, shoulder_width=53.0,
               neck_width=20.0, sleeve_length=24.0, bicep_width=25.7,
               armhole_depth=28.0),
    "outlier_wide": dict(half_chest_width=66.0, garment_length=80.0,
                         shoulder_width=57.0, neck_width=21.0,
                         sleeve_length=25.0, bicep_width=27.7,
                         armhole_depth=30.0),
}


def _build(**overrides) -> CloTShirtDraft:
    draft = CloTShirtDraft(garment_to_clo_block(_make_measurements(**overrides)))
    draft.build()
    return draft


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPanelEdgeCounts(unittest.TestCase):
    """10 edges per body panel, 5 per sleeve — what step 06 validates against."""

    def _check_counts(self, label, **overrides):
        draft = _build(**overrides)
        for body in ("front_panel", "back_panel"):
            count = len(draft.layouts[body].edges)
            self.assertEqual(
                count, BODY_EDGE_COUNT,
                f"{label} {body}: expected {BODY_EDGE_COUNT} edges, got {count}")
        for sleeve in ("sleeve_left", "sleeve_right"):
            count = len(draft.layouts[sleeve].edges)
            self.assertEqual(
                count, SLEEVE_EDGE_COUNT,
                f"{label} {sleeve}: expected {SLEEVE_EDGE_COUNT} edges, got {count}")

    def test_xs(self):      self._check_counts("xs", **SIZE_CONFIGS["xs"])
    def test_m(self):       self._check_counts("m")
    def test_xl(self):      self._check_counts("xl", **SIZE_CONFIGS["xl"])
    def test_outlier(self): self._check_counts("outlier", **SIZE_CONFIGS["outlier_wide"])


class TestPanelPolygonClosure(unittest.TestCase):
    def _check_closed(self, label, **overrides):
        draft = _build(**overrides)
        for name, layout in draft.layouts.items():
            self.assertTrue(_is_closed(_polygon(layout, 32)),
                            f"{label} {name}: polygon is not closed")

    def test_xs(self): self._check_closed("xs", **SIZE_CONFIGS["xs"])
    def test_m(self):  self._check_closed("m")
    def test_xl(self): self._check_closed("xl", **SIZE_CONFIGS["xl"])


class TestPanelNonSelfIntersecting(unittest.TestCase):
    def test_m_non_self_intersecting(self):
        draft = _build()
        for name, layout in draft.layouts.items():
            self.assertTrue(_is_non_self_intersecting(_polygon(layout, 24)),
                            f"M-size {name}: polygon self-intersects")


class TestCapEaseIsNegative(unittest.TestCase):
    """The cap is SHORTER than the armhole it fills, and that is correct.

    A jersey tee cap is deliberately undersized and stretched in during
    sewing. The reference block measures -2.25%. Do not "fix" this sign, and
    do not reintroduce the +3.5 cm ease from the retired curve_config.py.
    """

    def _cap_and_armhole(self, draft):
        armhole = (_arc_length(draft.layouts["front_panel"].edges[2]) +
                   _arc_length(draft.layouts["back_panel"].edges[2]))
        sleeve = draft.layouts["sleeve_left"]
        cap = (_arc_length(sleeve.edges[1]) + _arc_length(sleeve.edges[2]))
        return cap, armhole

    def test_reference_block_cap_ease_negative(self):
        draft = CloTShirtDraft(CloBlockMeasurements.clo_default_M())
        draft.build()
        cap, armhole = self._cap_and_armhole(draft)
        ease_pct = (cap - armhole) / armhole * 100.0
        self.assertLess(ease_pct, 0.0,
                        f"reference cap ease should be negative, got {ease_pct:+.3f}%")
        self.assertAlmostEqual(ease_pct, -2.25, delta=0.30)

    def test_cap_ease_negative_across_sizes(self):
        for label, cfg in SIZE_CONFIGS.items():
            with self.subTest(size=label):
                cap, armhole = self._cap_and_armhole(_build(**cfg))
                ease_pct = (cap - armhole) / armhole * 100.0
                self.assertLess(ease_pct, 0.0,
                                f"{label}: cap ease {ease_pct:+.3f}% should be negative")

    def test_cap_height_in_wearable_band(self):
        """A proportionate bicep gives a cap near the reference 0.244 ratio."""
        for label, cfg in SIZE_CONFIGS.items():
            with self.subTest(size=label):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    draft = _build(**cfg)
                ratio = draft.cap_height / draft.m.bicep_full_width
                lo, hi = draft.cfg.cap_height_ratio_band
                self.assertTrue(lo <= ratio <= hi,
                                f"{label}: cap/bicep {ratio:.3f} outside band {lo}-{hi}")
                self.assertEqual([str(w.message) for w in caught], [],
                                 f"{label}: unexpected warning from a proportionate size")


class TestNotchesPinSeamLengths(unittest.TestCase):
    """Below-notch armhole and cap lengths must match exactly.

    The notches exist so the sewn portion below them is length-identical; all
    of the cap's negative ease is absorbed above the notch.
    """

    def test_below_notch_lengths_match(self):
        for label, cfg in SIZE_CONFIGS.items():
            with self.subTest(size=label):
                report = _build(**cfg).seam_report()
                self.assertAlmostEqual(
                    report["below_notch_mismatch_front_mm"], 0.0, delta=1e-6,
                    msg=f"{label}: front below-notch seam lengths differ")
                self.assertAlmostEqual(
                    report["below_notch_mismatch_back_mm"], 0.0, delta=1e-6,
                    msg=f"{label}: back below-notch seam lengths differ")

    def test_ease_is_taken_above_the_notch(self):
        """All of the negative ease sits above the notch, none below it."""
        report = _build().seam_report()
        self.assertLess(report["above_notch_mismatch_front_mm"], 0.0)
        self.assertLess(report["above_notch_mismatch_back_mm"], 0.0)
        self.assertLess(report["ease_mm"], 0.0)

    def test_shoulder_seams_match(self):
        for label, cfg in SIZE_CONFIGS.items():
            with self.subTest(size=label):
                report = _build(**cfg).seam_report()
                self.assertAlmostEqual(
                    report["shoulder_seam_mm"], report["back_shoulder_seam_mm"],
                    delta=0.005,
                    msg=f"{label}: front and back shoulder seams differ")


class TestManifestDrivesDefaultSeams(unittest.TestCase):
    """The generated manifest must reproduce DEFAULT_SEAMS exactly.

    This is the contract that lets seams.py, step_06 and step_09 stay
    untouched. If it breaks, the fix belongs in the generator or the manifest
    writer — not in seams.py.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(_ROOT / "clo_vto" / "native_vto"))
        from seams import DEFAULT_SEAMS, load_seams_from_manifest  # noqa: E402
        cls.DEFAULT_SEAMS = DEFAULT_SEAMS
        cls.load_seams_from_manifest = staticmethod(load_seams_from_manifest)

        cls._tmp = tempfile.TemporaryDirectory()
        out = Path(cls._tmp.name)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            generate_panels(_make_measurements(), out, size_label="test_M")
        cls.manifest_path = out / "edge_manifest.json"

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_manifest_written(self):
        self.assertTrue(self.manifest_path.exists(),
                        "generate_panels did not write edge_manifest.json")

    def test_manifest_edge_counts(self):
        manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for body in ("front_panel", "back_panel"):
            self.assertEqual(len(manifest[body]), BODY_EDGE_COUNT, body)
        for sleeve in ("sleeve_left", "sleeve_right"):
            self.assertEqual(len(manifest[sleeve]), SLEEVE_EDGE_COUNT, sleeve)

    def test_manifest_produces_default_seam_wiring(self):
        seams = self.load_seams_from_manifest(self.manifest_path)
        self.assertIsNotNone(
            seams,
            "load_seams_from_manifest returned None — a seam-critical edge "
            "name is missing from the generated manifest")

        got = [(s["name"], s["a"], s["la"], s["b"], s["lb"], s["da"], s["db"])
               for s in seams]
        want = [(s["name"], s["a"], s["la"], s["b"], s["lb"], s["da"], s["db"])
                for s in self.DEFAULT_SEAMS]
        self.assertEqual(len(got), 10, "expected 10 seams")
        self.assertEqual(got, want)


if __name__ == "__main__":
    unittest.main()
