"""Hair Tier A: colour and alpha from the photo, per split-decision doc 5.1.

Hairstyle is geometry in `first.dan` and nothing here can touch it. What these tests pin
down is the part that is reachable - colour, perceived density, and above all the
behaviour when the photo does not support a measurement, because the failure that costs
us a user is shaving a full head of hair off an avatar on the strength of a bad sample.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from face_fitting.face_runtime import hair_fit
from face_fitting.face_runtime.constants import (HAIR_CAP_ALBEDO_ENTRY, HAIR_CAP_ALPHA_ENTRY,
                                                 HAIR_MAIN_ALBEDO_ENTRY, HAIR_MAIN_ALPHA_ENTRY)
from face_fitting.face_runtime.hair_fit import (apply_hair, brighten_gain, recolour_hair,
                                                sample_hair, thin_alpha)
from face_fitting.face_runtime.landmarks import FaceLandmarks

ALBEDOS = (HAIR_MAIN_ALBEDO_ENTRY, HAIR_CAP_ALBEDO_ENTRY)
ALPHAS = (HAIR_MAIN_ALPHA_ENTRY, HAIR_CAP_ALPHA_ENTRY)


def _decode(container, name):
    return cv2.imdecode(np.frombuffer(container.read_entry(name), np.uint8), cv2.IMREAD_COLOR)


def _mean_l(image):
    return float(cv2.cvtColor(image, cv2.COLOR_BGR2LAB)[..., 0].mean())


# --- the contrast gain ----------------------------------------------------------------

def test_gain_is_unity_when_darkening_or_unchanged():
    assert brighten_gain(100.0, 40.0) == pytest.approx(1.0)
    assert brighten_gain(50.0, 50.0) == pytest.approx(1.0)


def test_gain_rises_when_brightening_and_is_capped():
    """The stock strands are near-black, so a big lift needs contrast or it reads as paint."""
    assert brighten_gain(6.5, 35.8) > 1.0
    assert brighten_gain(1.0, 250.0) == pytest.approx(hair_fit.MAX_CONTRAST_GAIN)


def test_gain_is_monotonic_in_the_target():
    targets = [10.0, 30.0, 60.0, 120.0]
    gains = [brighten_gain(6.5, t) for t in targets]
    assert all(b >= a for a, b in zip(gains, gains[1:])), gains


# --- recolouring ----------------------------------------------------------------------

def test_recolour_shifts_the_mean_by_the_delta(container):
    texture = _decode(container, HAIR_MAIN_ALBEDO_ENTRY)
    out = recolour_hair(texture, (30.0, 4.0, 5.0), gain=1.0)
    assert _mean_l(out) - _mean_l(texture) == pytest.approx(30.0, abs=2.0)


def test_recolour_at_unit_gain_preserves_strand_variance(container):
    """Mean-only by design: the variance is the only strand detail that survived the JPEG."""
    texture = _decode(container, HAIR_MAIN_ALBEDO_ENTRY)
    before = cv2.cvtColor(texture, cv2.COLOR_BGR2LAB)[..., 0].std()
    out = recolour_hair(texture, (40.0, 0.0, 0.0), gain=1.0)
    after = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)[..., 0].std()
    assert after > before * 0.8


def test_gain_above_one_expands_variance(container):
    texture = _decode(container, HAIR_MAIN_ALBEDO_ENTRY)
    flat = cv2.cvtColor(recolour_hair(texture, (40.0, 0.0, 0.0), 1.0), cv2.COLOR_BGR2LAB)
    lifted = cv2.cvtColor(recolour_hair(texture, (40.0, 0.0, 0.0), 2.0), cv2.COLOR_BGR2LAB)
    assert lifted[..., 0].std() > flat[..., 0].std()


# --- thinning the alpha ---------------------------------------------------------------

def test_zero_strength_is_a_no_op(container):
    alpha = _decode(container, HAIR_MAIN_ALPHA_ENTRY)
    out, radius = thin_alpha(alpha, 0.0)
    assert radius == 0
    assert out.mean() == pytest.approx(alpha.mean(), abs=0.5)


def test_thinning_reduces_opacity_monotonically(container):
    alpha = _decode(container, HAIR_MAIN_ALPHA_ENTRY)
    means = [thin_alpha(alpha, s)[0].mean() for s in (0.0, 0.2, 0.5, 0.9)]
    assert all(b <= a for a, b in zip(means, means[1:])), means
    assert means[-1] < means[0]


def test_erode_radius_scales_with_strength_and_is_capped(container):
    alpha = _decode(container, HAIR_MAIN_ALPHA_ENTRY)
    assert thin_alpha(alpha, 0.05)[1] <= thin_alpha(alpha, 0.5)[1]
    assert thin_alpha(alpha, 1.0)[1] <= hair_fit.MAX_ERODE_PX


def test_thinning_keeps_the_map_a_three_channel_image(container):
    """CLO reads these as ordinary JPEG textures; a single-channel write would break them."""
    out, _ = thin_alpha(_decode(container, HAIR_CAP_ALPHA_ENTRY), 0.4)
    assert out.ndim == 3 and out.shape[2] == 3


# --- density from the hairline --------------------------------------------------------

def test_density_is_full_at_the_forehead_and_zero_when_bald():
    assert hair_fit._density_from_rise(hair_fit.DENSITY_RISE_FULL) == pytest.approx(1.0)
    assert hair_fit._density_from_rise(hair_fit.DENSITY_RISE_BALD) == pytest.approx(0.0)
    assert hair_fit._density_from_rise(0.0) == pytest.approx(1.0)
    assert hair_fit._density_from_rise(1.0) == pytest.approx(0.0)


def test_density_decreases_as_the_hairline_rises():
    rises = [0.05, 0.10, 0.20, 0.30]
    values = [hair_fit._density_from_rise(r) for r in rises]
    assert all(b <= a for a, b in zip(values, values[1:])), values


# --- sampling -------------------------------------------------------------------------

def test_sampling_declines_without_the_dense_mesh():
    bare = FaceLandmarks(eye_l=(10.0, 10.0), eye_r=(30.0, 10.0), mouth=(20.0, 25.0),
                         source='opencv_haar', dense=None)
    sample = sample_hair(np.zeros((128, 128, 3), np.uint8), bare)
    assert not sample.found
    assert not sample.measured
    assert any('No dense mesh' in w for w in sample.warnings)


def test_a_real_photo_is_sampled_with_all_three_columns(photo_high_res, landmarks_high_res):
    sample = sample_hair(photo_high_res, landmarks_high_res)
    assert sample.found, sample.warnings
    assert sample.measured
    assert sample.columns_with_hair == 3
    assert sample.pixels > hair_fit.MIN_COLOUR_PIXELS


def test_thick_hair_is_not_thinned(photo_high_res, landmarks_high_res):
    """density_ratio 1.0 means the hairline sits on the forehead vertex: nothing to erode."""
    sample = sample_hair(photo_high_res, landmarks_high_res)
    assert sample.density_ratio == pytest.approx(1.0, abs=0.05)


def test_the_sample_is_darker_than_the_forehead_it_was_measured_against(photo_high_res,
                                                                       landmarks_high_res):
    sample = sample_hair(photo_high_res, landmarks_high_res)
    skin_l = sample.geometry['skin_lab'][0]
    assert sample.lab[0] < skin_l, 'hair sampled brighter than skin means the band missed'


# --- applying to the container --------------------------------------------------------

def test_auto_on_thick_hair_recolours_without_touching_the_alphas(container, photo_high_res,
                                                                 landmarks_high_res):
    report = apply_hair(container, photo_high_res, landmarks_high_res, mode='auto')
    assert report.recoloured
    assert not report.thinned
    assert set(report.entries_changed) == set(ALBEDOS)
    for entry in ALPHAS:
        assert entry not in container.replaced_names()


def test_colour_mode_never_touches_the_alphas(container, photo_high_res, landmarks_high_res):
    before = {name: container.read_entry(name) for name in ALPHAS}
    apply_hair(container, photo_high_res, landmarks_high_res, mode='colour')
    for name, payload in before.items():
        assert container.read_entry(name) == payload


def test_density_mode_never_touches_the_albedos(container, photo_high_res, landmarks_high_res):
    before = {name: container.read_entry(name) for name in ALBEDOS}
    apply_hair(container, photo_high_res, landmarks_high_res, mode='density')
    for name, payload in before.items():
        assert container.read_entry(name) == payload


def test_an_unmeasured_sample_leaves_the_template_hair_alone(container):
    """The regression that matters: an unmeasured sample reports density 0, which would
    read as bald. 'Do not know' has to mean 'do not touch'."""
    bare = FaceLandmarks(eye_l=(10.0, 10.0), eye_r=(30.0, 10.0), mouth=(20.0, 25.0),
                         source='opencv_haar', dense=None)
    before = {name: container.read_entry(name) for name in ALBEDOS + ALPHAS}

    report = apply_hair(container, np.zeros((128, 128, 3), np.uint8), bare, mode='auto')

    assert not report.recoloured
    assert not report.thinned
    assert report.density_strength == 0.0
    assert report.density_source == 'unmeasured'
    assert container.replaced_names() == []
    for name, payload in before.items():
        assert container.read_entry(name) == payload, name


def test_a_density_override_thins_even_without_a_photo_measurement(container):
    bare = FaceLandmarks(eye_l=(10.0, 10.0), eye_r=(30.0, 10.0), mouth=(20.0, 25.0),
                         source='opencv_haar', dense=None)
    report = apply_hair(container, np.zeros((128, 128, 3), np.uint8), bare,
                        mode='density', density_override=0.6)
    assert report.thinned
    assert report.density_source == 'override'
    assert report.alpha_opacity_after < report.alpha_opacity_before
    assert set(report.entries_changed) == set(ALPHAS)


def test_a_full_strength_override_warns_that_it_is_not_a_clean_shave(container):
    bare = FaceLandmarks(eye_l=(10.0, 10.0), eye_r=(30.0, 10.0), mouth=(20.0, 25.0),
                         source='opencv_haar', dense=None)
    report = apply_hair(container, np.zeros((128, 128, 3), np.uint8), bare,
                        mode='density', density_override=1.0)
    assert any('near-nothing' in w for w in report.warnings)


def test_patched_hair_textures_stay_decodable(container, photo_high_res, landmarks_high_res):
    """Every entry we rewrite has to come back out of the container as a readable JPEG."""
    apply_hair(container, photo_high_res, landmarks_high_res, mode='auto', density_override=0.3)
    for name in ALBEDOS + ALPHAS:
        decoded = _decode(container, name)
        assert decoded is not None, name
        assert decoded.shape[0] == decoded.shape[1] == 2048, name


def test_report_serialises_for_output_json(container, photo_high_res, landmarks_high_res):
    payload = apply_hair(container, photo_high_res, landmarks_high_res).as_dict()
    assert payload['recoloured'] is True
    assert payload['sample']['found'] is True
    assert len(payload['delta_lab']) == 3
    assert 'density_source' in payload


# --- render compensation --------------------------------------------------------------

def test_no_compensation_writes_the_sampled_colour_unchanged():
    from face_fitting.face_runtime.hair_fit import compensated_target_l
    assert compensated_target_l(35.82, 0.0) == pytest.approx(35.82)


def test_full_compensation_divides_by_the_measured_shading_factor():
    """Measured: CLO renders hair at 0.528 of its albedo, so aim that much higher."""
    from face_fitting.face_runtime.hair_fit import compensated_target_l
    assert compensated_target_l(35.82, 1.0) == pytest.approx(
        35.82 / hair_fit.RENDER_LIGHTNESS_FACTOR, abs=0.5)


def test_compensation_is_monotonic_and_capped():
    from face_fitting.face_runtime.hair_fit import compensated_target_l
    values = [compensated_target_l(35.82, c) for c in (0.0, 0.25, 0.5, 1.0)]
    assert all(b >= a for a, b in zip(values, values[1:])), values
    assert compensated_target_l(250.0, 1.0) <= hair_fit.MAX_COMPENSATED_L


def test_compensation_lifts_the_albedo_in_a_real_run(container, photo_high_res,
                                                     landmarks_high_res):
    plain = apply_hair(container, photo_high_res, landmarks_high_res, mode='colour')
    from face_fitting.io.avt_container import read_avt
    from face_fitting.tests.conftest import BASE_AVATAR
    lifted = apply_hair(read_avt(BASE_AVATAR), photo_high_res, landmarks_high_res,
                        mode='colour', render_compensation=1.0)
    assert lifted.target_l > plain.target_l
    assert lifted.delta_lab[0] > plain.delta_lab[0]
    # Hue must not move with the lightness: shading darkens hair, it does not recolour it.
    assert lifted.delta_lab[1] == pytest.approx(plain.delta_lab[1], abs=0.01)
    assert lifted.delta_lab[2] == pytest.approx(plain.delta_lab[2], abs=0.01)
