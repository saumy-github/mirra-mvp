"""Eye colour: the Phase 1 item from the split-decision doc Part 7 alongside hair.

The guard rails matter more than the happy path here. A wrong iris colour is one of the
most visible errors possible on a face, so every test below that checks a declined sample
is checking that the stock brown survives contact with a bad photo.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from face_fitting.face_runtime import eye_fit
from face_fitting.face_runtime.constants import (EYE_ALBEDO_ENTRY, EYE_TEXTURE_SIZE,
                                                 eye_geometry_for_size)
from face_fitting.face_runtime.eye_fit import (apply_eyes, iris_mean_lab, iris_weight,
                                               recolour_iris, sample_iris)
from face_fitting.face_runtime.landmarks import FaceLandmarks


def _eye_texture(container) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(container.read_entry(EYE_ALBEDO_ENTRY), np.uint8),
                        cv2.IMREAD_COLOR)


def _lab(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)


# --- the mask -------------------------------------------------------------------------

def test_weight_is_zero_on_the_pupil_and_one_on_the_iris():
    weight = iris_weight(EYE_TEXTURE_SIZE)
    geometry = eye_geometry_for_size(EYE_TEXTURE_SIZE)
    cx, cy = (int(round(v)) for v in geometry['centre'])

    assert weight[cy, cx] == pytest.approx(0.0), 'the pupil must stay black'
    mid = int(round((geometry['iris_inner'] + geometry['iris_outer']) / 2.0))
    assert weight[cy, cx + mid] == pytest.approx(1.0, abs=1e-3)


def test_weight_is_zero_on_the_sclera():
    weight = iris_weight(EYE_TEXTURE_SIZE)
    geometry = eye_geometry_for_size(EYE_TEXTURE_SIZE)
    cx, cy = (int(round(v)) for v in geometry['centre'])
    beyond = int(round(geometry['limbus_radius'])) + 4
    assert weight[cy, cx + beyond] == pytest.approx(0.0), 'the sclera must stay white'
    assert weight[2, 2] == pytest.approx(0.0)


def test_weight_is_monotonic_outward_across_the_feather():
    weight = iris_weight(EYE_TEXTURE_SIZE)
    geometry = eye_geometry_for_size(EYE_TEXTURE_SIZE)
    cx, cy = (int(round(v)) for v in geometry['centre'])
    inner = int(round(geometry['pupil_radius']))
    outer = int(round(geometry['iris_inner']))
    ramp = [weight[cy, cx + r] for r in range(inner, outer + 1)]
    assert all(b >= a - 1e-6 for a, b in zip(ramp, ramp[1:])), ramp


def test_geometry_scales_with_texture_size():
    small = eye_geometry_for_size(EYE_TEXTURE_SIZE)
    large = eye_geometry_for_size(EYE_TEXTURE_SIZE * 2)
    assert large['iris_outer'] == pytest.approx(small['iris_outer'] * 2)
    assert iris_weight(EYE_TEXTURE_SIZE * 2).shape == (EYE_TEXTURE_SIZE * 2,) * 2


# --- measuring the stock texture ------------------------------------------------------

def test_the_stock_iris_measures_as_a_warm_mid_brown(container):
    """Guards the measured constants: if the template changes, this is what catches it."""
    lab = iris_mean_lab(_eye_texture(container), iris_weight(EYE_TEXTURE_SIZE))
    assert 30.0 < lab[0] < 90.0, f'iris L* out of the measured 34-64 band: {lab}'
    assert lab[1] > 130.0 and lab[2] > 135.0, f'iris should be warm (a,b above neutral): {lab}'


# --- recolouring ----------------------------------------------------------------------

def test_recolour_moves_the_iris_and_leaves_pupil_and_sclera_alone(container):
    texture = _eye_texture(container)
    weight = iris_weight(texture.shape[0])
    delta = (40.0, -12.0, -25.0)

    out = recolour_iris(texture, delta, weight)
    before, after = _lab(texture), _lab(out)

    core = weight > 0.9
    assert (after[..., 0][core].mean() - before[..., 0][core].mean()) == pytest.approx(
        delta[0], abs=2.0)

    untouched = weight <= 0.0
    for channel in range(3):
        diff = np.abs(after[..., channel][untouched] - before[..., channel][untouched])
        # 2 L* of slack for the Lab->BGR->Lab quantisation, not for leakage.
        assert diff.max() <= 2.0, f'channel {channel} leaked outside the mask: {diff.max()}'


def test_recolour_preserves_iris_variance(container):
    """A mean-only shift, so the painted fibre detail has to survive it."""
    texture = _eye_texture(container)
    weight = iris_weight(texture.shape[0])
    core = weight > 0.9
    before = _lab(texture)[..., 0][core].std()
    after = _lab(recolour_iris(texture, (30.0, 0.0, 0.0), weight))[..., 0][core].std()
    assert after == pytest.approx(before, rel=0.2)


# --- sampling -------------------------------------------------------------------------

def test_sampling_declines_without_the_refined_mesh():
    """The OpenCV fallback has no iris vertices, so eye colour must simply not happen."""
    bare = FaceLandmarks(eye_l=(10.0, 10.0), eye_r=(30.0, 10.0), mouth=(20.0, 25.0),
                         source='opencv_haar', dense=None)
    sample = sample_iris(np.zeros((64, 64, 3), np.uint8), bare)
    assert not sample.found
    assert sample.pixels == 0
    assert any('Iris landmarks unavailable' in w for w in sample.warnings)


def test_sampling_declines_when_the_mesh_has_no_iris_vertices():
    dense = np.zeros((468, 2), np.float32)
    short = FaceLandmarks(eye_l=(10.0, 10.0), eye_r=(30.0, 10.0), mouth=(20.0, 25.0),
                          source='mediapipe', dense=dense)
    assert not sample_iris(np.zeros((64, 64, 3), np.uint8), short).found


def _synthetic_eye(colour_bgr, radius=24, size=400, specular=False):
    """A photo-shaped image with two flat-coloured irises and matching iris landmarks."""
    photo = np.full((size, size, 3), 220, np.uint8)
    dense = np.zeros((eye_fit.DENSE_WITH_IRIS, 2), np.float32)
    centres = ((size * 0.35, size * 0.5), (size * 0.65, size * 0.5))
    for base, (cx, cy) in zip((eye_fit._MP_IRIS_L, eye_fit._MP_IRIS_R), centres):
        cv2.circle(photo, (int(cx), int(cy)), radius, colour_bgr, -1)
        cv2.circle(photo, (int(cx), int(cy)), max(1, radius // 3), (0, 0, 0), -1)
        if specular:
            cv2.circle(photo, (int(cx), int(cy - radius * 0.4)), max(1, radius // 3),
                       (255, 255, 255), -1)
        dense[base] = (cx, cy)
        dense[base + 1] = (cx - radius, cy)
        dense[base + 2] = (cx + radius, cy)
        dense[base + 3] = (cx, cy - radius)
        dense[base + 4] = (cx, cy + radius)
    landmarks = FaceLandmarks(eye_l=centres[0], eye_r=centres[1], mouth=(size * 0.5, size * 0.7),
                              source='mediapipe', dense=dense)
    return photo, landmarks


def test_sampling_recovers_a_known_iris_colour():
    blue = (200, 120, 40)  # BGR
    photo, landmarks = _synthetic_eye(blue)
    sample = sample_iris(photo, landmarks)

    assert sample.found, sample.warnings
    assert sample.eyes_used == 2
    expected = _lab(np.array([[blue]], np.uint8))[0, 0]
    assert sample.lab[0] == pytest.approx(float(expected[0]), abs=4.0)
    assert sample.lab[1] == pytest.approx(float(expected[1]), abs=4.0)
    assert sample.lab[2] == pytest.approx(float(expected[2]), abs=4.0)


def test_a_catchlight_does_not_wash_out_the_sample():
    blue = (200, 120, 40)
    clean, landmarks = _synthetic_eye(blue)
    flashed, _ = _synthetic_eye(blue, specular=True)

    without = sample_iris(clean, landmarks)
    with_flash = sample_iris(flashed, landmarks)
    assert with_flash.found, with_flash.warnings
    assert with_flash.geometry['specular_dropped'] > 0
    assert with_flash.lab[0] == pytest.approx(without.lab[0], abs=5.0)


def test_sampling_declines_when_the_iris_is_too_few_pixels():
    photo, landmarks = _synthetic_eye((200, 120, 40), radius=5, size=120)
    sample = sample_iris(photo, landmarks)
    assert not sample.found
    assert sample.confidence == 0.0
    assert any('usable iris pixels' in w for w in sample.warnings)


def test_sampling_declines_when_the_region_lands_on_sclera():
    """Landmarks that missed put the mask on the white of the eye; that is not a colour.

    205 grey, not pure white: a real sclera carries shading and sits under the specular
    cutoff, so this exercises the brightness guard rather than the highlight filter.
    """
    photo, landmarks = _synthetic_eye((205, 205, 205))
    sample = sample_iris(photo, landmarks)
    assert not sample.found
    assert any('reads as sclera' in w for w in sample.warnings), sample.warnings


def test_sampling_declines_when_the_eyes_are_blown_out():
    photo, landmarks = _synthetic_eye((252, 252, 252))
    sample = sample_iris(photo, landmarks)
    assert not sample.found
    assert any('blown out' in w for w in sample.warnings), sample.warnings


def test_a_real_photo_at_adequate_resolution_is_sampled(photo_high_res, landmarks_high_res):
    sample = sample_iris(photo_high_res, landmarks_high_res)
    assert sample.found, sample.warnings
    assert sample.eyes_used == 2
    assert sample.pixels >= eye_fit.MIN_IRIS_PIXELS
    assert sample.iris_radius_px > 10.0


def test_a_real_photo_below_the_resolution_floor_declines(photo_low_res, landmarks_low_res):
    """622x350 gives a 5px iris. Declining is the correct answer, not a guess."""
    sample = sample_iris(photo_low_res, landmarks_low_res)
    assert not sample.found
    assert sample.iris_radius_px < 10.0


# --- applying to the container --------------------------------------------------------

def test_apply_changes_only_the_eye_entry(container, photo_high_res, landmarks_high_res):
    report = apply_eyes(container, photo_high_res, landmarks_high_res)
    assert report.recoloured, report.warnings
    assert report.entries_changed == [EYE_ALBEDO_ENTRY]
    assert container.replaced_names() == [EYE_ALBEDO_ENTRY]
    assert report.texture_size == EYE_TEXTURE_SIZE


def test_apply_leaves_the_texture_untouched_when_the_sample_is_bad(container, photo_low_res,
                                                                  landmarks_low_res):
    before = container.read_entry(EYE_ALBEDO_ENTRY)
    report = apply_eyes(container, photo_low_res, landmarks_low_res)
    assert not report.recoloured
    assert report.entries_changed == []
    assert container.replaced_names() == []
    assert container.read_entry(EYE_ALBEDO_ENTRY) == before
    assert 'Eye colour left at the stock iris.' in report.warnings


def test_apply_still_decodes_to_a_valid_jpeg(container, photo_high_res, landmarks_high_res):
    apply_eyes(container, photo_high_res, landmarks_high_res)
    decoded = _eye_texture(container)
    assert decoded is not None
    assert decoded.shape == (EYE_TEXTURE_SIZE, EYE_TEXTURE_SIZE, 3)


def test_the_shift_is_clamped_against_a_badly_exposed_photo(container):
    """A black frame must not produce a black eyeball."""
    photo, landmarks = _synthetic_eye((2, 2, 2))
    report = apply_eyes(container, photo, landmarks)
    if report.recoloured:
        assert abs(report.delta_lab[0]) <= eye_fit.MAX_EYE_L_DELTA
        assert abs(report.delta_lab[1]) <= eye_fit.MAX_EYE_AB_DELTA
        assert abs(report.delta_lab[2]) <= eye_fit.MAX_EYE_AB_DELTA


def test_report_serialises_for_output_json(container, photo_high_res, landmarks_high_res):
    payload = apply_eyes(container, photo_high_res, landmarks_high_res).as_dict()
    assert payload['recoloured'] is True
    assert payload['entries_changed'] == [EYE_ALBEDO_ENTRY]
    assert payload['sample']['found'] is True
    assert len(payload['delta_lab']) == 3


def test_debug_overlay_draws_without_mutating_the_photo(photo_high_res, landmarks_high_res):
    sample = sample_iris(photo_high_res, landmarks_high_res)
    before = photo_high_res.copy()
    overlay = eye_fit.debug_overlay(photo_high_res, sample)
    assert overlay.shape == photo_high_res.shape
    assert np.array_equal(photo_high_res, before), 'the overlay must not draw on its input'
    assert not np.array_equal(overlay, before)
