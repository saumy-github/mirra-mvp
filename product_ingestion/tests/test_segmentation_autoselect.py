"""Regression tests for the v1_auto segmentation rule (CV plan P15a), CPU only, no models.

The rule decides from the SegFormer clothes-parser label map whether a "Skirt" region is part of the top
(no head visible: flat product photo or a torso crop, e.g. the colour-block shirt c_003) or a real skirt
(a head is visible).
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv_segment as cvs  # noqa: E402

UPPER, SKIRT, HAIR, FACE = 4, 5, 2, 11


def label_map(skirt_rows=(60, 100), head_rows=None, size=100):
    lab = np.zeros((size, size), np.uint8)
    lab[20:60, 20:80] = UPPER
    if skirt_rows:
        lab[skirt_rows[0]:skirt_rows[1], 25:75] = SKIRT
    if head_rows:
        lab[head_rows[0]:head_rows[1], 40:60] = FACE
    return lab


class TestAutoSkirtDecision(unittest.TestCase):
    def test_torso_crop_skirt_is_part_of_the_top(self):
        use_all, f = cvs.auto_skirt_decision(label_map())
        self.assertTrue(use_all)
        self.assertGreaterEqual(f["skirt_frac"], cvs.AUTO_SKIRT_MIN_FRAC)
        self.assertLess(f["head_frac"], cvs.AUTO_HEAD_MAX_FRAC)

    def test_visible_head_means_a_real_skirt(self):
        use_all, f = cvs.auto_skirt_decision(label_map(head_rows=(5, 20)))   # 3 % of the image is face
        self.assertFalse(use_all)
        self.assertGreaterEqual(f["head_frac"], cvs.AUTO_HEAD_MAX_FRAC)

    def test_hair_counts_as_head(self):
        lab = label_map()
        lab[0:10, 30:70] = HAIR                                              # 4 % hair, no face
        self.assertFalse(cvs.auto_skirt_decision(lab)[0])

    def test_no_skirt_keeps_v1(self):
        self.assertFalse(cvs.auto_skirt_decision(label_map(skirt_rows=None))[0])

    def test_tiny_skirt_speck_is_ignored(self):
        lab = label_map(skirt_rows=None)
        lab[90:93, 40:43] = SKIRT                                            # 0.09 % of the image
        self.assertFalse(cvs.auto_skirt_decision(lab)[0])

    def test_only_largest_skirt_component_counts(self):
        lab = label_map(skirt_rows=None)
        for x in range(0, 100, 10):                                          # ten 0.09 % specks = 0.9 % in total
            lab[95:98, x:x + 3] = SKIRT
        self.assertFalse(cvs.auto_skirt_decision(lab)[0])


if __name__ == "__main__":
    unittest.main()
