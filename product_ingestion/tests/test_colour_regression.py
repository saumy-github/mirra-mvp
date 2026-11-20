"""Regression tests for the colour bugs fixed in the CV work (P04).

B1: the old HSV skin filter deleted warm-coloured fabric (tan, coral, pink, brown).
B2: near-white / near-black clusters were skipped as base colour.
B3: a perfectly flat colour crashed K-Means (NaN from an empty cluster).
Also: a colour-block shirt must keep both fabric colours (never one colour only).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from step_03_0_colour_extraction import extract_colours  # noqa: E402

H = W = 200


def shirt(rgb, shade=None, rng=None):
    img = np.zeros((H, W, 4), np.uint8)
    img[40:160, 50:150, :3] = rgb
    img[40:160, 50:150, 3] = 255
    if shade is not None:
        img[40:160, 50:80, :3] = shade
    if rng is not None:
        noise = rng.normal(0, 2, (120, 100, 3))
        img[40:160, 50:150, :3] = np.clip(img[40:160, 50:150, :3] + noise, 0, 255).astype(np.uint8)
    return img


def de(hex_code: str, rgb) -> float:
    h = hex_code.lstrip("#")
    a = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255
    b = np.array(rgb, float) / 255
    return float(deltaE_ciede2000(rgb2lab(a[None, None]), rgb2lab(b[None, None]))[0, 0])


class ColourRegressionTests(unittest.TestCase):
    def test_b1_warm_fabrics_are_not_deleted_as_skin(self):
        for rgb in [(210, 180, 140), (240, 128, 110), (230, 150, 170), (120, 80, 50)]:
            with self.subTest(rgb=rgb):
                res, ok = extract_colours(shirt(rgb))
                self.assertTrue(res.success, res.message)
                self.assertTrue(ok)
                self.assertLess(de(res.base_colour_hex, rgb), 3.0)

    def test_b2_white_tee_with_shadow_keeps_white_base(self):
        res, _ = extract_colours(shirt((245, 245, 245), shade=(196, 196, 196)))
        self.assertLess(de(res.base_colour_hex, (245, 245, 245)), 5.0)

    def test_b2_black_tee_with_small_red_print_keeps_black_base(self):
        img = shirt((20, 20, 22))
        img[70:100, 85:115, :3] = (220, 30, 30)
        res, _ = extract_colours(img)
        self.assertLess(de(res.base_colour_hex, (20, 20, 22)), 5.0)
        self.assertTrue(any(de(c.hex_code, (220, 30, 30)) < 5.0 for c in res.palette),
                        "the red print should still be in the palette")

    def test_b3_flat_single_colour_does_not_crash(self):
        res, ok = extract_colours(shirt((200, 160, 60)))
        self.assertTrue(res.success, res.message)
        self.assertLess(de(res.base_colour_hex, (200, 160, 60)), 1.0)

    def test_colour_block_keeps_both_fabric_colours(self):
        img = shirt((231, 231, 241), rng=np.random.default_rng(0))
        img[100:160, 50:150, :3] = (27, 53, 49)
        res, _ = extract_colours(img)
        fabrics = getattr(res, "fabric_colours", None) or [c.hex_code for c in res.palette]
        self.assertTrue(any(de(h, (231, 231, 241)) < 5.0 for h in fabrics))
        self.assertTrue(any(de(h, (27, 53, 49)) < 5.0 for h in fabrics))

    def test_v0_still_selectable(self):
        # v0 keeps its old behaviour on purpose (including bug B3 on perfectly flat
        # colours), so it is checked on a slightly noisy shirt.
        res, _ = extract_colours(shirt((40, 90, 160), rng=np.random.default_rng(1)), method="v0")
        self.assertTrue(res.success)


if __name__ == "__main__":
    unittest.main()
