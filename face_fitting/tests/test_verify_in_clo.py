"""The verifier's own matching logic, tested without CLO.

Worth testing on its own because its failure mode is silent and expensive: it reports a
pass. Two bugs it has already had, both caught here -

  * a nearest-match allowed to reuse an exported image claimed one hair texture for three
    different entries and passed all three;
  * cropping the reference to a region of interest while leaving the exported side full
    frame matched the eye map against a tooth texture.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from face_fitting import verify_in_clo as verifier
from face_fitting.face_runtime.constants import (EYE_ALBEDO_ENTRY, HAIR_CAP_ALBEDO_ENTRY,
                                                 HAIR_MAIN_ALBEDO_ENTRY, HEAD_ALBEDO_ENTRY)


def _encoded(image: np.ndarray) -> bytes:
    ok, payload = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    assert ok
    return payload.tobytes()


def _stats_of(image: np.ndarray, label: str = '') -> verifier.TextureStats:
    payload = _encoded(image)
    return verifier._stats(cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR),
                           label=label, payload=payload)


def _noise(size: int, seed: int, base: int = 120) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(base, 30, (size, size, 3)), 0, 255).astype(np.uint8)


# --- the fingerprint ------------------------------------------------------------------

def test_identical_images_have_zero_distance():
    image = _noise(256, seed=1)
    assert verifier._fingerprint_distance(_stats_of(image), _stats_of(image)) < 1.0


def test_different_textures_of_the_same_size_are_far_apart():
    a, b = _stats_of(_noise(256, 1)), _stats_of(_noise(256, 2, base=60))
    assert verifier._fingerprint_distance(a, b) > verifier.DECISIVE_MARGIN_LAB


def test_a_mean_shift_is_visible_to_the_fingerprint():
    """What the hair recolour does: the whole frame moves, and that must register."""
    image = _noise(256, 3)
    shifted = np.clip(image.astype(np.int16) + 40, 0, 255).astype(np.uint8)
    assert verifier._fingerprint_distance(_stats_of(image), _stats_of(shifted)) > 10.0


def test_the_fingerprint_does_not_notice_a_small_local_change_on_a_full_frame():
    """Why the eye needs a region: a change over a tenth of the frame dilutes away.

    This is the behaviour that made the eye undecidable, asserted so nobody removes the
    region of interest thinking it is redundant.
    """
    image = _noise(256, 4)
    local = image.copy()
    cv2.circle(local, (126, 124), 30, (20, 40, 200), -1)
    whole_frame = verifier._fingerprint_distance(_stats_of(image), _stats_of(local))
    assert whole_frame < verifier.ABSENT_FINGERPRINT_LAB


def test_the_region_of_interest_recovers_that_change():
    image = _noise(256, 4)
    local = image.copy()
    cv2.circle(local, (126, 124), 30, (20, 40, 200), -1)
    cropped = verifier._fingerprint_distance(
        verifier._in_region(_stats_of(image), 'iris'),
        verifier._in_region(_stats_of(local), 'iris'))
    assert cropped > verifier.DECISIVE_MARGIN_LAB


def test_the_iris_box_sits_inside_the_eye_map_and_scales():
    x0, y0, x1, y1 = verifier._iris_box(256)
    assert 0 <= x0 < x1 <= 256 and 0 <= y0 < y1 <= 256
    big = verifier._iris_box(512)
    assert (big[2] - big[0]) == pytest.approx((x1 - x0) * 2, abs=2)


# --- assignment -----------------------------------------------------------------------

def test_each_entry_gets_its_own_exported_image():
    """The regression: three 2048-square entries all claiming the same export and passing."""
    textures = {HAIR_MAIN_ALBEDO_ENTRY: _noise(64, 10),
                HAIR_CAP_ALBEDO_ENTRY: _noise(64, 11),
                HEAD_ALBEDO_ENTRY: _noise(64, 12)}
    patched = {name: _stats_of(image, name) for name, image in textures.items()}
    exported = [_stats_of(image, f'img_{name}') for name, image in textures.items()]

    assigned = verifier._assign(patched, exported)
    assert len(assigned) == 3
    assert len({id(stats) for stats in assigned.values()}) == 3, 'an image was claimed twice'
    for name in textures:
        assert assigned[name].label == f'img_{name}'


def test_assignment_ignores_images_of_a_different_resolution():
    patched = {EYE_ALBEDO_ENTRY: _stats_of(_noise(64, 20), EYE_ALBEDO_ENTRY)}
    assert verifier._assign(patched, [_stats_of(_noise(128, 21), 'wrong_size')]) == {}


def test_assignment_leaves_an_entry_unpaired_when_images_run_out():
    patched = {HAIR_MAIN_ALBEDO_ENTRY: _stats_of(_noise(64, 30), HAIR_MAIN_ALBEDO_ENTRY),
               HAIR_CAP_ALBEDO_ENTRY: _stats_of(_noise(64, 31), HAIR_CAP_ALBEDO_ENTRY)}
    assigned = verifier._assign(patched, [_stats_of(_noise(64, 30), 'only_one')])
    assert len(assigned) == 1


# --- verdicts -------------------------------------------------------------------------

def _verdict(entry, patched_img, stock_img, exported_img):
    return verifier._verdict_for(entry, _stats_of(patched_img), _stats_of(stock_img),
                                 _stats_of(exported_img, 'exported'))


def test_an_export_matching_our_patch_reads_as_patch_read():
    stock = _noise(64, 40, base=40)
    patched = np.clip(stock.astype(np.int16) + 60, 0, 255).astype(np.uint8)
    result = _verdict(HAIR_MAIN_ALBEDO_ENTRY, patched, stock, patched)
    assert result.verdict == 'PATCH READ'


def test_an_export_matching_stock_reads_as_patch_ignored():
    stock = _noise(64, 41, base=40)
    patched = np.clip(stock.astype(np.int16) + 60, 0, 255).astype(np.uint8)
    result = _verdict(HAIR_MAIN_ALBEDO_ENTRY, patched, stock, stock)
    assert result.verdict == 'PATCH IGNORED'


def test_an_unrelated_export_reads_as_not_in_export():
    """The alpha maps: CLO's GLB has no counterpart, so neither reference is close."""
    stock = _noise(64, 42, base=40)
    patched = np.clip(stock.astype(np.int16) + 60, 0, 255).astype(np.uint8)
    result = _verdict(HAIR_MAIN_ALBEDO_ENTRY, patched, stock, _noise(64, 43, base=220))
    assert result.verdict == 'NOT IN EXPORT'


def test_an_unchanged_entry_is_reported_as_not_decidable():
    stock = _noise(64, 44)
    result = _verdict(HAIR_CAP_ALBEDO_ENTRY, stock, stock, stock)
    assert result.verdict == 'NOT DECIDABLE'


def test_a_missing_pair_is_reported_rather_than_passed():
    result = verifier._verdict_for(HAIR_MAIN_ALBEDO_ENTRY, _stats_of(_noise(64, 45)), None, None)
    assert result.verdict == 'NOT FOUND'


def test_verdicts_serialise_for_the_report():
    stock = _noise(64, 46, base=40)
    patched = np.clip(stock.astype(np.int16) + 60, 0, 255).astype(np.uint8)
    payload = _verdict(HAIR_MAIN_ALBEDO_ENTRY, patched, stock, patched).as_dict()
    assert payload['verdict'] == 'PATCH READ'
    assert payload['entry'] == HAIR_MAIN_ALBEDO_ENTRY
    assert payload['distance_to_patched'] is not None
