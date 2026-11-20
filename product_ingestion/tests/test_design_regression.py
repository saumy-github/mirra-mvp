"""Regression tests for the design-extraction fixes of the CV work (P05).

B4: the old FFT "repeating pattern" test fired on everything, so a plain shirt with
two soft folds was reported as an all-over pattern. The fixed periodicity test must
ignore folds but still find real repeating prints (dots, stripes).
Also: a plain shirt must not get any printed-design region from the new default.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cv_design_regions as cvd  # noqa: E402
import step_04_0_design_extraction as s4  # noqa: E402


def tee(kind: str, h: int = 400, w: int = 400):
    img = np.full((h, w, 3), 150, np.float32)
    yy, xx = np.mgrid[:h, :w]
    img *= (1 - 0.12 * np.exp(-((xx - 140) / 25.0) ** 2) - 0.10 * np.exp(-((xx - 270 + 0.3 * yy) / 20.0) ** 2))[..., None]
    if kind == "dots":
        for y in range(15, h, 30):
            for x in range(15 + 15 * ((y // 30) % 2), w, 30):
                cv2.circle(img, (x, y), 6, (40, 60, 160), -1)
    if kind == "stripes":
        for y in range(0, h, 24):
            img[y:y + 10] = (40, 60, 160)
    img += np.random.RandomState(0).normal(0, 2, img.shape)
    img = np.clip(img, 0, 255).astype(np.uint8)
    mask = np.zeros((h, w), np.uint8)
    cv2.rectangle(mask, (30, 20), (w - 30, h - 20), 1, -1)
    img[mask == 0] = 0
    return img, mask > 0


class DesignRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ocr = getattr(cvd, "USE_OCR", None)
        cvd.USE_OCR = False  # keep the test fast and model-free

    @classmethod
    def tearDownClass(cls):
        if cls._ocr is not None:
            cvd.USE_OCR = cls._ocr

    def test_b4_folds_are_not_a_repeating_pattern(self):
        rgb, mask = tee("plain_folds")
        self.assertFalse(cvd.periodicity(cvd.prepare(rgb, mask))["periodic"])

    def test_b4_real_repeating_prints_are_found(self):
        for kind in ("dots", "stripes"):
            with self.subTest(kind=kind):
                rgb, mask = tee(kind)
                self.assertTrue(cvd.periodicity(cvd.prepare(rgb, mask))["periodic"])

    def test_plain_shirt_gets_no_printed_region(self):
        rgb, mask = tee("plain_folds")
        regions = cvd.detect_regions(rgb, mask, method="v2_combo")
        printed = [r for r in regions if r["type"] != "colour_block"]
        self.assertEqual(printed, [], f"unexpected regions on a plain shirt: {printed}")

    def test_v0_still_selectable(self):
        rgb, mask = tee("dots")
        res = s4.extract_design(np.dstack([rgb, mask.astype(np.uint8) * 255]), method="v0")
        self.assertIsNotNone(res)


if __name__ == "__main__":
    unittest.main()
