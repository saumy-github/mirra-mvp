import random

import numpy as np
import pytest

from photo_measurement.bmnet.data import FILL, VIEW_H, VIEW_W, canonical_view, scalar_features
from photo_measurement.bmnet.predict import fuse


def _person(h=600, w=400, top=50, height=400, width=80):
    m = np.zeros((h, w), bool)
    m[top:top + height, w // 2 - width // 2:w // 2 + width // 2] = True
    return m


def test_canonical_view_removes_framing():
    near = canonical_view(_person(top=20, height=500, width=100))
    far = canonical_view(_person(top=200, height=250, width=50))
    assert near.shape == far.shape == (VIEW_H, VIEW_W)
    rows = lambda v: np.flatnonzero(v.max(axis=1) > 0.5)  # noqa: E731
    assert len(rows(near)) == pytest.approx(FILL * VIEW_H, abs=2)
    assert np.abs(near - far).mean() < 0.01  # same body, different distance -> same input


def test_augmentation_changes_mask_but_keeps_person():
    m = _person()
    aug = canonical_view(m, random.Random(3))
    assert aug.sum() > 0 and not np.allclose(aug, canonical_view(m))


def test_scalar_features_optional_weight_and_sex():
    full = scalar_features(180, 80, "male")
    none = scalar_features(180, None, None)
    assert full[4] == 1 and none[4] == 0 and none[1] == none[2] == none[3] == 0


def test_fuse_uses_learned_values_and_rescales_unlabelled_girths():
    result = {"measurements": {"chest": 90.0, "bust": 92.0, "waist": 80.0, "abdomen": 84.0, "neck": 38.0},
              "methods": {"chest": "two_view", "bust": "two_view", "waist": "two_view",
                          "abdomen": "two_view", "neck": "two_view"}}
    learned = {k: 10.0 for k in ["ankle", "arm-length", "bicep", "calf", "forearm", "height", "hip",
                                 "leg-length", "shoulder-breadth", "shoulder-to-crotch", "thigh", "wrist"]}
    learned.update(chest=99.0, waist=88.0)
    out = fuse(result, learned)
    m = out["measurements"]
    assert m["chest"] == 99.0 and out["methods"]["chest"] == "learned"
    assert m["bust"] == pytest.approx(92 * 99 / 90, abs=0.1)
    assert m["abdomen"] == pytest.approx(84 * 88 / 80, abs=0.1)
    assert m["neck"] == 38.0
