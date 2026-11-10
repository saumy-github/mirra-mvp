"""The capture gate: the cheapest quality lever we have.

Measured finding behind this module - input resolution dominates subject difficulty. The
"easy" stock photo is the one that fails, because it is 622x350. Refusing a bad photo and
saying what to do about it buys more than any algorithm change currently on the roadmap.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from face_fitting.face_runtime import capture_quality as cq
from face_fitting.face_runtime.capture_quality import GRADES, assess
from face_fitting.face_runtime.landmarks import FaceLandmarks


def _check(quality, name):
    return next(c for c in quality.checks if c.name == name)


def _landmarks(interocular=400.0, centre=(500.0, 500.0), dense=True, roll=0.0, nose_offset=0.0):
    half = interocular / 2.0
    cx, cy = centre
    dy = np.tan(np.radians(roll)) * half
    eye_l = (cx - half, cy - dy)
    eye_r = (cx + half, cy + dy)
    mouth = (cx, cy + interocular * 0.6)
    points = None
    if dense:
        points = np.zeros((478, 2), np.float32)
        points[:] = (cx, cy)
        points[cq._MP_CHEEK_L] = (cx - interocular, cy)
        points[cq._MP_CHEEK_R] = (cx + interocular, cy)
        points[cq._MP_NOSE_TIP] = (cx + nose_offset * interocular * 2.0, cy)
        points[cq._MP_FOREHEAD] = (cx, cy - interocular)
        points[cq._MP_CHIN] = (cx, cy + interocular)
        points[33], points[263] = eye_l, eye_r
    return FaceLandmarks(eye_l=eye_l, eye_r=eye_r, mouth=mouth, source='mediapipe', dense=points)


def _photo(size=1200, seed=0):
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(130, 40, (size, size, 3)), 0, 255).astype(np.uint8)


# --- grading ---------------------------------------------------------------------------

@pytest.mark.parametrize('interocular,expected', [
    (420.0, 'excellent'), (400.0, 'excellent'),
    (300.0, 'good'), (240.0, 'good'),
    (200.0, 'usable'), (170.0, 'usable'),
    (120.0, 'poor'), (77.7, 'poor'),
])
def test_grade_bands(interocular, expected):
    assert cq._grade_for(interocular) == expected


def test_the_uv_target_is_the_measured_one_not_the_old_constant():
    """400.7, from the same detector that reads photos - not the 304 in ANCHORS_2048,
    which is a different convention (pupil centres) and would understate the upscale."""
    assert cq.UV_INTEROCULAR_2048 == pytest.approx(400.7, abs=0.5)


def test_upscale_is_reported_against_that_target():
    quality = assess(_photo(), _landmarks(interocular=200.0))
    assert quality.uv_upscale == pytest.approx(cq.UV_INTEROCULAR_2048 / 200.0, rel=1e-3)


def test_meets_compares_in_grade_order():
    quality = assess(_photo(), _landmarks(interocular=300.0))
    assert quality.grade == 'good'
    assert quality.meets('usable') and quality.meets('good')
    assert not quality.meets('excellent')


def test_meets_rejects_an_unknown_grade():
    with pytest.raises(ValueError):
        assess(_photo(), _landmarks()).meets('flawless')


def test_grades_are_ordered_worst_first():
    assert GRADES == ('poor', 'usable', 'good', 'excellent')


# --- eye colour prediction --------------------------------------------------------------

def test_eye_colour_is_predicted_viable_at_the_measured_floor():
    """170px interocular is where eye_fit's 240-pixel minimum starts being reachable."""
    assert assess(_photo(), _landmarks(interocular=200.0)).eye_colour_viable
    assert not assess(_photo(), _landmarks(interocular=100.0)).eye_colour_viable


def test_the_prediction_matches_what_eye_fit_actually_does_on_the_real_photos(
        photo_low_res, landmarks_low_res, photo_high_res, landmarks_high_res):
    """The gate is only useful if it agrees with the stage it is predicting."""
    from face_fitting.face_runtime.eye_fit import sample_iris

    low = assess(photo_low_res, landmarks_low_res)
    high = assess(photo_high_res, landmarks_high_res)
    assert low.eye_colour_viable is sample_iris(photo_low_res, landmarks_low_res).found
    assert high.eye_colour_viable is sample_iris(photo_high_res, landmarks_high_res).found


# --- sharpness --------------------------------------------------------------------------

def test_blurring_a_photo_lowers_its_sharpness(photo_high_res, landmarks_high_res):
    sharp = _check(assess(photo_high_res, landmarks_high_res), 'sharpness').value
    blurred_photo = cv2.GaussianBlur(photo_high_res, (0, 0), 3)
    blurred = _check(assess(blurred_photo, landmarks_high_res), 'sharpness').value
    assert blurred < sharp / 4.0


def test_a_blurred_face_fails_the_sharpness_check(photo_high_res, landmarks_high_res):
    blurred = cv2.GaussianBlur(photo_high_res, (0, 0), 3)
    assert not _check(assess(blurred, landmarks_high_res), 'sharpness').passed


def test_the_bigger_photo_measures_sharper_than_the_smaller_one(
        photo_low_res, landmarks_low_res, photo_high_res, landmarks_high_res):
    """The regression: raw Laplacian variance called the 622x350 photo 799 and the
    1200x1600 one 22, because squeezing detail into fewer pixels raises per-pixel variance.
    Resampling to a fixed size first is what makes the two comparable."""
    low = _check(assess(photo_low_res, landmarks_low_res), 'sharpness').value
    high = _check(assess(photo_high_res, landmarks_high_res), 'sharpness').value
    assert high > low


# --- pose and exposure ------------------------------------------------------------------

def test_a_square_on_face_passes_the_turn_check():
    assert _check(assess(_photo(), _landmarks()), 'head turn').passed


def test_a_turned_head_is_caught():
    quality = assess(_photo(), _landmarks(nose_offset=0.15))
    assert not _check(quality, 'head turn').passed
    assert any('squarely' in advice for advice in quality.advice)


def test_a_tilted_head_is_caught():
    assert not _check(assess(_photo(), _landmarks(roll=20.0)), 'head tilt').passed
    assert _check(assess(_photo(), _landmarks(roll=2.0)), 'head tilt').passed


def test_head_turn_is_skipped_without_a_dense_mesh():
    """The OpenCV fallback has no cheeks to measure against."""
    quality = assess(_photo(), _landmarks(dense=False))
    assert all(check.name != 'head turn' for check in quality.checks)


def test_a_blown_out_face_fails_exposure():
    photo = np.full((1200, 1200, 3), 255, np.uint8)
    quality = assess(photo, _landmarks())
    assert not _check(quality, 'exposure').passed


def test_a_crushed_face_fails_exposure():
    photo = np.zeros((1200, 1200, 3), np.uint8)
    assert not _check(assess(photo, _landmarks()), 'exposure').passed


def test_an_evenly_lit_face_passes_exposure():
    assert _check(assess(_photo(), _landmarks()), 'exposure').passed


# --- reporting --------------------------------------------------------------------------

def test_advice_is_only_given_for_failed_checks():
    quality = assess(_photo(), _landmarks(interocular=60.0))
    assert not quality.passed
    assert quality.advice
    assert len(quality.advice) <= len([c for c in quality.checks if not c.passed])


def test_the_assessment_serialises_for_output_json():
    payload = assess(_photo(), _landmarks()).as_dict()
    assert payload['grade'] in GRADES
    assert 'checks' in payload and payload['checks']
    assert isinstance(payload['eye_colour_viable'], bool)


def test_the_real_photos_grade_as_measured(photo_low_res, landmarks_low_res,
                                           photo_high_res, landmarks_high_res):
    """test1 is the resolution-starved one despite being the 'easy' subject."""
    assert assess(photo_low_res, landmarks_low_res).grade == 'poor'
    assert assess(photo_high_res, landmarks_high_res).grade == 'good'
