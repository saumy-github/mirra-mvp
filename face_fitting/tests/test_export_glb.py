"""Hair opacity in the GLB: the step that makes an exported avatar usable outside CLO.

CLO's own export carries the hair colour we patched but not the hair alpha, and glTF reads
opacity from the base colour's fourth channel. Without this step every strand card renders
as a solid rectangle and the hair is a helmet. These tests cover the composition and the
identification, both of which fail silently if they are wrong - a wrongly matched texture
produces a file that loads fine and looks wrong.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from face_fitting.export_glb import HAIR_PAIRS, compose_alpha
from face_fitting.face_runtime.constants import (HAIR_CAP_ALBEDO_ENTRY, HAIR_CAP_ALPHA_ENTRY,
                                                 HAIR_MAIN_ALBEDO_ENTRY, HAIR_MAIN_ALPHA_ENTRY)
from face_fitting.io.glb_textures import (assign, decode, fingerprint_distance, stats_for)


def _decoded(payload: bytes) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_UNCHANGED)


def _noise(size: int, seed: int, base: int = 120) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(base, 30, (size, size, 3)), 0, 255).astype(np.uint8)


# --- composing the alpha channel ------------------------------------------------------

def test_the_result_is_rgba():
    out = _decoded(compose_alpha(_noise(64, 1), _noise(64, 2)))
    assert out.ndim == 3 and out.shape[2] == 4


def test_the_colour_channels_survive_unchanged():
    """Lossless: PNG, no resize. The albedo must come back bit for bit."""
    albedo = _noise(64, 3)
    out = _decoded(compose_alpha(albedo, _noise(64, 4)))
    assert np.array_equal(out[..., :3], albedo)


def test_the_alpha_channel_is_the_alpha_map():
    albedo, alpha = _noise(64, 5), _noise(64, 6)
    out = _decoded(compose_alpha(albedo, alpha))
    assert np.array_equal(out[..., 3], cv2.cvtColor(alpha, cv2.COLOR_BGR2GRAY))


def test_a_mismatched_alpha_map_is_resized_to_fit():
    out = _decoded(compose_alpha(_noise(64, 7), _noise(128, 8)))
    assert out.shape[:2] == (64, 64)


def test_a_single_channel_alpha_map_is_accepted():
    alpha = np.full((64, 64), 200, np.uint8)
    out = _decoded(compose_alpha(_noise(64, 9), alpha))
    assert out[..., 3].mean() == pytest.approx(200, abs=1)


def test_downscaling_shrinks_both_channels_together():
    out = _decoded(compose_alpha(_noise(256, 10), _noise(256, 11), size=64))
    assert out.shape[:2] == (64, 64)
    assert out.shape[2] == 4


def test_a_fully_opaque_map_stays_opaque():
    out = _decoded(compose_alpha(_noise(64, 12), np.full((64, 64, 3), 255, np.uint8)))
    assert out[..., 3].min() == 255


def test_a_fully_transparent_map_stays_transparent():
    out = _decoded(compose_alpha(_noise(64, 13), np.zeros((64, 64, 3), np.uint8)))
    assert out[..., 3].max() == 0


def test_downscaling_preserves_roughly_the_same_coverage():
    """A thinned alpha must not become opaque just because it was made smaller."""
    alpha = (np.random.default_rng(14).random((256, 256)) * 255).astype(np.uint8)
    alpha_bgr = cv2.cvtColor(alpha, cv2.COLOR_GRAY2BGR)
    full = _decoded(compose_alpha(_noise(256, 15), alpha_bgr))
    small = _decoded(compose_alpha(_noise(256, 15), alpha_bgr, size=64))
    assert small[..., 3].mean() == pytest.approx(full[..., 3].mean(), abs=6)


# --- the albedo/alpha pairing ---------------------------------------------------------

def test_every_hair_albedo_has_an_alpha_partner():
    assert HAIR_PAIRS == {HAIR_MAIN_ALBEDO_ENTRY: HAIR_MAIN_ALPHA_ENTRY,
                          HAIR_CAP_ALBEDO_ENTRY: HAIR_CAP_ALPHA_ENTRY}


def test_the_real_hair_pairs_exist_in_the_container(container):
    for albedo, alpha in HAIR_PAIRS.items():
        assert albedo in container.names()
        assert alpha in container.names()


def test_the_two_hair_albedos_are_distinguishable_by_fingerprint(container):
    """If main and cap looked alike, the assignment could swap their alpha maps."""
    main = stats_for(decode(container.read_entry(HAIR_MAIN_ALBEDO_ENTRY)), 'main')
    cap = stats_for(decode(container.read_entry(HAIR_CAP_ALBEDO_ENTRY)), 'cap')
    assert fingerprint_distance(main, cap) > 2.0


def test_the_real_hair_albedos_match_themselves_and_not_each_other(container):
    main_img = decode(container.read_entry(HAIR_MAIN_ALBEDO_ENTRY))
    cap_img = decode(container.read_entry(HAIR_CAP_ALBEDO_ENTRY))
    targets = {HAIR_MAIN_ALBEDO_ENTRY: stats_for(main_img, 'main-target'),
               HAIR_CAP_ALBEDO_ENTRY: stats_for(cap_img, 'cap-target')}
    candidates = [stats_for(cap_img, 'exported-cap', index=2),
                  stats_for(main_img, 'exported-main', index=4)]

    matched = assign(targets, candidates)
    assert matched[HAIR_MAIN_ALBEDO_ENTRY].label == 'exported-main'
    assert matched[HAIR_CAP_ALBEDO_ENTRY].label == 'exported-cap'


def test_the_alpha_maps_are_not_mistaken_for_albedos(container):
    """All four are 2048 square, so only content tells them apart."""
    targets = {name: stats_for(decode(container.read_entry(name)), name)
               for name in HAIR_PAIRS}
    candidates = [stats_for(decode(container.read_entry(name)), name, index=i)
                  for i, name in enumerate(list(HAIR_PAIRS) + list(HAIR_PAIRS.values()))]

    matched = assign(targets, candidates)
    for albedo_entry in HAIR_PAIRS:
        assert matched[albedo_entry].label == albedo_entry
