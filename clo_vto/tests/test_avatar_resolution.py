"""Phase 0: a shopper must get their own avatar or the stock template, never a stranger's.

The bug being fixed globbed `clo_vto/output/*.avt` and returned whatever it found. On a
one-user dev box that always looked right, which is exactly why it survived - the failure
only appears once a second user exists, and by then the avatars carry real faces.

The first test in the cross-user section is the one that matters; the rest hold the ladder
and the degradation order in place around it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clo_vto.native_vto.avatar_resolution import (AvatarResolution, describe,  # noqa: E402
                                                  resolve_avatar)


@pytest.fixture
def world(tmp_path):
    """An output tree and a base template, with helpers to populate runs."""
    output_root = tmp_path / 'output'
    output_root.mkdir()
    template = tmp_path / 'base-1.avt'
    template.write_bytes(b'stock template')

    def make(relative: str, payload: bytes = b'avatar') -> Path:
        path = output_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return path

    def resolve(user_id, **kwargs):
        return resolve_avatar(user_id, output_root=output_root, base_template=template,
                              **kwargs)

    return type('World', (), {'root': output_root, 'template': template,
                              'make': staticmethod(make), 'resolve': staticmethod(resolve)})


# --- the bug this module exists to prevent --------------------------------------------

def test_one_users_avatar_is_never_served_to_another(world):
    """The whole point. u_002 has a faced avatar; u_001 has nothing at all."""
    world.make('u_002-face-001/u_002.avt', b'someone elses face')

    result = world.resolve('u_001')

    assert result.tier == 'base_template'
    assert result.path == world.template.resolve()
    assert 'u_002' not in str(result.path)
    assert not result.is_personalised


def test_a_crowded_output_tree_does_not_confuse_the_lookup(world):
    world.make('u_002-face-001/u_002.avt')
    world.make('u_003-face-009/u_003.avt')
    world.make('u_004-001/result_avatar.avt')
    mine = world.make('u_001-face-001/u_001.avt')

    assert world.resolve('u_001').path == mine.resolve()


def test_a_face_run_is_not_mistaken_for_a_step_one_run(world):
    """`u_001-face-001` must not be read as Step 1 run 001 of some user `u_001-face`."""
    world.make('u_001-face-001/result_avatar.avt', b'wrong file in a face dir')
    result = world.resolve('u_001')
    assert result.tier == 'base_template', result.as_dict()


def test_a_user_whose_id_prefixes_another_is_not_matched(world):
    """`u_1` must not pick up `u_12`'s runs."""
    world.make('u_12-face-001/u_12.avt')
    assert world.resolve('u_1').tier == 'base_template'


def test_a_named_user_never_gets_the_dev_fixture(world):
    result = world.resolve('u_001', allow_dev_fixture=True)
    assert result.tier == 'base_template'
    skipped = [c for c in result.considered if c['tier'] == 'dev_fixture']
    assert skipped and not skipped[0]['used']


# --- the ladder -----------------------------------------------------------------------

def test_faced_glb_wins_over_everything(world):
    world.make('u_001-001/result_avatar.avt')
    world.make('u_001-face-001/u_001.avt')
    glb = world.make('u_001-face-001/faced.glb')

    result = world.resolve('u_001')
    assert result.tier == 'faced_glb'
    assert result.path == glb.resolve()
    assert result.has_face


def test_faced_avt_wins_over_the_step_one_avatar(world):
    world.make('u_001-001/result_avatar.avt')
    faced = world.make('u_001-face-002/u_001.avt')

    result = world.resolve('u_001')
    assert result.tier == 'faced_avt'
    assert result.path == faced.resolve()


def test_the_step_one_avatar_is_used_when_there_is_no_face(world):
    body = world.make('u_001-001/result_avatar.avt')
    result = world.resolve('u_001')

    assert result.tier == 'avatar_avt'
    assert result.path == body.resolve()
    assert result.is_personalised and not result.has_face
    assert any('no faced one' in w for w in result.warnings)


def test_the_base_template_is_the_last_rung(world):
    result = world.resolve('u_001')
    assert result.tier == 'base_template'
    assert result.path == world.template.resolve()
    assert any('not be personalised' in w for w in result.warnings)


def test_the_newest_run_wins_within_a_rung(world):
    world.make('u_001-face-001/u_001.avt', b'old')
    newest = world.make('u_001-face-012/u_001.avt', b'new')
    assert world.resolve('u_001').path == newest.resolve()


def test_run_numbers_sort_numerically_not_lexically(world):
    """009 vs 012: a string sort puts 009 last and would serve a stale avatar."""
    world.make('u_001-face-009/u_001.avt', b'old')
    newest = world.make('u_001-face-012/u_001.avt', b'new')
    assert world.resolve('u_001').path.read_bytes() == b'new'
    assert newest.exists()


def test_both_faced_filenames_are_accepted(world):
    faced = world.make('u_001-face-001/faced.avt')
    assert world.resolve('u_001').path == faced.resolve()


# --- explicit paths -------------------------------------------------------------------

def test_an_explicit_path_short_circuits_the_ladder(world):
    world.make('u_001-face-001/u_001.avt')
    chosen = world.make('somewhere/else.avt')

    result = world.resolve('u_001', explicit=chosen)
    assert result.tier == 'explicit'
    assert result.path == chosen.resolve()


def test_a_missing_explicit_path_falls_back_and_warns(world):
    faced = world.make('u_001-face-001/u_001.avt')
    result = world.resolve('u_001', explicit=world.root / 'nope.avt')

    assert result.tier == 'faced_avt'
    assert result.path == faced.resolve()
    assert any('does not exist' in w for w in result.warnings)


# --- reporting ------------------------------------------------------------------------

def test_the_audit_trail_records_every_rung_considered(world):
    world.make('u_001-001/result_avatar.avt')
    result = world.resolve('u_001')

    tiers = [entry['tier'] for entry in result.considered]
    assert tiers[:3] == ['faced_glb', 'faced_avt', 'avatar_avt']
    assert sum(1 for entry in result.considered if entry['used']) == 1


def test_the_resolution_serialises_for_the_run_record(world):
    payload = world.resolve('u_001').as_dict()
    assert payload['tier'] == 'base_template'
    assert payload['is_personalised'] is False
    assert isinstance(payload['considered'], list)


def test_describe_names_the_rung_so_a_surprise_is_visible(world):
    assert 'NOT personalised' in describe(world.resolve('u_001'))
    world.make('u_001-face-001/u_001.avt')
    assert 'faced avatar' in describe(world.resolve('u_001'))


def test_a_missing_base_template_reports_rather_than_guesses(tmp_path):
    output_root = tmp_path / 'output'
    output_root.mkdir()
    result = resolve_avatar('u_001', output_root=output_root,
                            base_template=tmp_path / 'absent.avt')
    assert isinstance(result, AvatarResolution)
    assert result.path is None
    assert any('base template missing' in w for w in result.warnings)


def test_the_retired_glob_raises_instead_of_guessing():
    from clo_vto.native_vto.context import _discover_default_native_avatar
    with pytest.raises(RuntimeError, match='retired'):
        _discover_default_native_avatar()


# --- the profile avatar rung ----------------------------------------------------------

def test_the_profile_avatar_is_used_when_there_is_no_faced_one(world, tmp_path):
    """The live worker already knows this path; the ladder should land on it."""
    profile = tmp_path / 'profile' / 'avatar.avt'
    profile.parent.mkdir()
    profile.write_bytes(b'profile avatar')

    result = world.resolve('u_001', profile_avatar=profile)
    assert result.tier == 'avatar_avt'
    assert result.path == profile.resolve()


def test_a_faced_avatar_beats_the_profile_avatar(world, tmp_path):
    """The whole reason this is a rung and not `explicit`: faced must still win."""
    profile = tmp_path / 'profile' / 'avatar.avt'
    profile.parent.mkdir()
    profile.write_bytes(b'profile avatar')
    faced = world.make('u_001-face-001/u_001.avt')

    result = world.resolve('u_001', profile_avatar=profile)
    assert result.tier == 'faced_avt'
    assert result.path == faced.resolve()


def test_the_profile_avatar_beats_a_stale_step_one_run(world, tmp_path):
    profile = tmp_path / 'profile' / 'avatar.avt'
    profile.parent.mkdir()
    profile.write_bytes(b'profile avatar')
    world.make('u_001-001/result_avatar.avt', b'older on-disk run')

    assert world.resolve('u_001', profile_avatar=profile).path == profile.resolve()


def test_a_missing_profile_avatar_warns_and_falls_through(world):
    on_disk = world.make('u_001-001/result_avatar.avt')
    result = world.resolve('u_001', profile_avatar=world.root / 'gone.avt')

    assert result.tier == 'avatar_avt'
    assert result.path == on_disk.resolve()
    assert any('missing from disk' in w for w in result.warnings)


def test_a_profile_avatar_never_overrides_another_users_isolation(world, tmp_path):
    """Passing u_002's profile path while resolving u_001 must not leak u_001 a face."""
    profile = tmp_path / 'profile' / 'u_002.avt'
    profile.parent.mkdir()
    profile.write_bytes(b'u_002 avatar')
    world.make('u_002-face-001/u_002.avt', b'u_002 face')

    result = world.resolve('u_001', profile_avatar=profile)
    # The caller explicitly handed us this path for this user, so it is used - but nothing
    # was discovered from u_002's directories, which is the property under test.
    assert result.tier == 'avatar_avt'
    assert 'u_002-face-001' not in str(result.path)


# --- the faced avatar rung ------------------------------------------------------------

def test_a_recorded_faced_avatar_is_used(world, tmp_path):
    """The face job writes beside the avatar it personalised, not into the run tree, so
    without this hint the ladder would never find its output."""
    faced = tmp_path / 'avatars' / 'u_001' / '003' / 'faced.avt'
    faced.parent.mkdir(parents=True)
    faced.write_bytes(b'faced avatar')

    result = world.resolve('u_001', faced_avatar=faced)
    assert result.tier == 'faced_avt'
    assert result.path == faced.resolve()
    assert result.has_face


def test_a_recorded_faced_avatar_beats_the_profile_avatar(world, tmp_path):
    version = tmp_path / 'avatars' / 'u_001' / '003'
    version.mkdir(parents=True)
    (version / 'avatar.avt').write_bytes(b'body only')
    (version / 'faced.avt').write_bytes(b'with face')

    result = world.resolve('u_001', faced_avatar=version / 'faced.avt',
                           profile_avatar=version / 'avatar.avt')
    assert result.tier == 'faced_avt'
    assert result.path.read_bytes() == b'with face'


def test_a_stale_faced_path_warns_and_falls_back_to_the_body(world, tmp_path):
    """A rolled-back version must degrade to the body, never to someone else's face."""
    version = tmp_path / 'avatars' / 'u_001' / '003'
    version.mkdir(parents=True)
    (version / 'avatar.avt').write_bytes(b'body only')

    result = world.resolve('u_001', faced_avatar=version / 'faced.avt',
                           profile_avatar=version / 'avatar.avt')
    assert result.tier == 'avatar_avt'
    assert any('missing from disk' in w for w in result.warnings)


def test_a_faced_glb_still_outranks_a_recorded_faced_avt(world, tmp_path):
    faced = tmp_path / 'faced.avt'
    faced.write_bytes(b'texture only')
    glb = world.make('u_001-face-001/faced.glb')

    result = world.resolve('u_001', faced_avatar=faced)
    assert result.tier == 'faced_glb'
    assert result.path == glb.resolve()


# --- the two output roots -------------------------------------------------------------

def test_face_and_avatar_runs_are_looked_for_in_different_trees(tmp_path):
    """Each pipeline writes under its own package, so the two disk rungs scan two places.

    They used to share one root at the repo root, which was wrong for Step 1 even before
    the face runs moved: `avatar.avt` has always been written to
    `clo_avatar_generation/output`, so that rung could never match.
    """
    face_root = tmp_path / 'face_fitting' / 'output'
    avatar_root = tmp_path / 'clo_avatar_generation' / 'output'
    (face_root / 'u_001-face-001').mkdir(parents=True)
    (avatar_root / 'u_001-001').mkdir(parents=True)
    (avatar_root / 'u_001-001' / 'result_avatar.avt').write_bytes(b'body')
    template = tmp_path / 'base-1.avt'
    template.write_bytes(b'stock')

    result = resolve_avatar('u_001', face_output_root=face_root,
                            avatar_output_root=avatar_root, base_template=template)
    assert result.tier == 'avatar_avt'
    assert result.path == (avatar_root / 'u_001-001' / 'result_avatar.avt').resolve()


def test_a_faced_run_in_the_face_tree_still_wins(tmp_path):
    face_root = tmp_path / 'face_fitting' / 'output'
    avatar_root = tmp_path / 'clo_avatar_generation' / 'output'
    faced = face_root / 'u_001-face-001' / 'u_001.avt'
    faced.parent.mkdir(parents=True)
    faced.write_bytes(b'faced')
    (avatar_root / 'u_001-001').mkdir(parents=True)
    (avatar_root / 'u_001-001' / 'result_avatar.avt').write_bytes(b'body')
    template = tmp_path / 'base-1.avt'
    template.write_bytes(b'stock')

    result = resolve_avatar('u_001', face_output_root=face_root,
                            avatar_output_root=avatar_root, base_template=template)
    assert result.tier == 'faced_avt' and result.path == faced.resolve()


def test_the_defaults_point_at_each_packages_own_output():
    from clo_vto.native_vto import avatar_resolution as resolution
    assert resolution.DEFAULT_FACE_OUTPUT_ROOT.parts[-2:] == ('face_fitting', 'output')
    assert resolution.DEFAULT_AVATAR_OUTPUT_ROOT.parts[-2:] == ('clo_avatar_generation', 'output')


def test_output_root_still_sets_both_for_a_single_temp_tree(world):
    """One directory with both kinds of run in it, which is what most tests want."""
    world.make('u_001-001/result_avatar.avt')
    assert world.resolve('u_001').tier == 'avatar_avt'
