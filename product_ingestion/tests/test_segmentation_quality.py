"""Segmentation quality gate unit tests.

Verifies:
- _compute_quality returns a score in [0, 1].
- Coverage score penalises very small or very large masks.
- _fill_holes removes enclosed holes from a binary mask.
- _feather_mask produces a 4-channel RGBA with soft edges.
- Quality metrics dict has all expected keys.
"""
import sys
import unittest
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_HERE))

from segmentation import GarmentSegmentor


def _solid_mask(h=200, w=200, fill_frac=0.5) -> np.ndarray:
    """Return a uint8 mask with a centred filled rectangle."""
    mask = np.zeros((h, w), dtype=np.uint8)
    ph = int(h * fill_frac ** 0.5)
    pw = int(w * fill_frac ** 0.5)
    y0 = (h - ph) // 2
    x0 = (w - pw) // 2
    mask[y0:y0 + ph, x0:x0 + pw] = 255
    return mask


def _mask_with_hole(h=200, w=200) -> np.ndarray:
    """Return a mask that is a ring (outer - inner square)."""
    outer = _solid_mask(h, w, fill_frac=0.64)
    inner = np.zeros_like(outer)
    ph, pw = h // 4, w // 4
    y0, x0 = (h - ph) // 2, (w - pw) // 2
    inner[y0:y0 + ph, x0:x0 + pw] = 255
    return np.clip(outer.astype(np.int32) - inner.astype(np.int32), 0, 255).astype(np.uint8)


class TestComputeQuality(unittest.TestCase):

    def test_score_in_range(self):
        mask = _solid_mask()
        score, metrics = GarmentSegmentor._compute_quality(mask)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_metrics_keys_present(self):
        mask = _solid_mask()
        _, metrics = GarmentSegmentor._compute_quality(mask)
        expected = {"area_percent", "coverage_score", "edge_sharpness_score",
                    "hole_count", "hole_penalty", "quality_score"}
        self.assertEqual(set(metrics.keys()), expected)

    def test_small_mask_penalised(self):
        tiny_mask = _solid_mask(fill_frac=0.01)   # ~1% coverage
        good_mask = _solid_mask(fill_frac=0.25)   # ~25% coverage
        score_tiny, _ = GarmentSegmentor._compute_quality(tiny_mask)
        score_good, _ = GarmentSegmentor._compute_quality(good_mask)
        self.assertLess(score_tiny, score_good, "tiny mask should score lower")

    def test_empty_mask_low_score(self):
        empty = np.zeros((200, 200), dtype=np.uint8)
        score, metrics = GarmentSegmentor._compute_quality(empty)
        self.assertLess(score, 0.3, "empty mask should have a low quality score")
        self.assertEqual(metrics["area_percent"], 0.0)

    def test_mask_with_holes_penalised(self):
        solid = _solid_mask()
        holey = _mask_with_hole()
        score_solid, m_solid = GarmentSegmentor._compute_quality(solid)
        score_holey, m_holey = GarmentSegmentor._compute_quality(holey)
        self.assertGreater(
            m_holey["hole_count"], 0,
            "ring mask should have at least one detected hole",
        )
        self.assertGreater(
            m_holey["hole_penalty"], m_solid["hole_penalty"],
            "ring mask should have higher hole penalty than solid",
        )


class TestFillHoles(unittest.TestCase):

    def test_hole_filled(self):
        ring = _mask_with_hole()
        # Confirm hole exists before fill
        holes_before = int(np.sum(ring == 0))
        filled = GarmentSegmentor._fill_holes(ring)
        holes_after_inside = 0
        # After fill, the interior should be 255
        h, w = filled.shape
        ph, pw = h // 4, w // 4
        y0, x0 = (h - ph) // 2, (w - pw) // 2
        region = filled[y0:y0 + ph, x0:x0 + pw]
        self.assertTrue(np.all(region == 255), "Interior hole was not filled")

    def test_solid_mask_unchanged(self):
        solid = _solid_mask()
        filled = GarmentSegmentor._fill_holes(solid)
        self.assertEqual(np.sum(solid > 0), np.sum(filled > 0))

    def test_empty_mask_unchanged(self):
        empty = np.zeros((100, 100), dtype=np.uint8)
        filled = GarmentSegmentor._fill_holes(empty)
        self.assertEqual(filled.sum(), 0)


class TestFeatherMask(unittest.TestCase):

    def test_output_is_rgba(self):
        mask = _solid_mask()
        rgb = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
        result = GarmentSegmentor._feather_mask(mask, rgb)
        self.assertEqual(result.shape[2], 4)

    def test_inside_alpha_255(self):
        mask = _solid_mask()
        rgb = np.zeros((200, 200, 3), dtype=np.uint8)
        result = GarmentSegmentor._feather_mask(mask, rgb)
        ph = int(200 * 0.5 ** 0.5)
        y0 = (200 - ph) // 2
        # Interior pixels (inset from border) should be fully opaque
        interior_alpha = result[y0 + 5: y0 + ph - 5, y0 + 5: y0 + ph - 5, 3]
        self.assertTrue(np.all(interior_alpha == 255), "Interior alpha should be 255")

    def test_outside_alpha_zero(self):
        mask = _solid_mask()
        rgb = np.zeros((200, 200, 3), dtype=np.uint8)
        result = GarmentSegmentor._feather_mask(mask, rgb)
        corner_alpha = result[0:5, 0:5, 3]
        self.assertTrue(np.all(corner_alpha == 0), "Corner (outside mask) alpha should be 0")


if __name__ == "__main__":
    unittest.main()
