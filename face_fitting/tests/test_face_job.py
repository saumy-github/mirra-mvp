"""The face job as the worker calls it.

`run_for_version_dir` is the library entry point behind `worker.tasks.run_face_job`. The
contract that matters: it writes the faced avatar **beside the avatar it personalised**, so
a user's body and the face fitted to it stay one artifact and roll back together; and it
always leaves a manifest, including when it refused the photo, because a rejection is a
normal outcome a user has to be told about rather than an error to swallow.
"""

from __future__ import annotations

import json
import shutil

import pytest

from face_fitting.face_job import (FACE_MANIFEST_NAME, FACED_AVATAR_NAME, FaceJobOptions,
                                   fit_face, next_run_dir, run_for_version_dir)
from face_fitting.face_runtime.constants import AVT_ENTRY_COUNT, EYE_ALBEDO_ENTRY
from face_fitting.io.avt_container import read_avt

pytestmark = pytest.mark.slow

# Hair and eyes are exercised in their own modules; turning them off keeps these runs to
# the container work and roughly halves the time.
FAST = FaceJobOptions(hair='none', eyes='none', write_diagnostics=False)


@pytest.fixture
def version_dir(tmp_path, base_avt_path):
    """A stand-in for live_upload/avatars/<user>/003/, holding one generated avatar."""
    directory = tmp_path / 'avatars' / 'u_001' / '003'
    directory.mkdir(parents=True)
    shutil.copy(base_avt_path, directory / 'avatar.avt')
    return directory


# --- where it writes -------------------------------------------------------------------

def test_the_faced_avatar_lands_beside_the_avatar_it_came_from(version_dir, repo_root):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    result = run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=FAST)

    assert result.ok, result.reason
    assert result.out_avatar == version_dir / FACED_AVATAR_NAME
    assert result.out_avatar.exists()
    assert (version_dir / 'avatar.avt').exists(), 'the source avatar must survive'


def test_the_source_avatar_is_not_modified(version_dir, repo_root, base_avt_path):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=FAST)
    assert (version_dir / 'avatar.avt').read_bytes() == base_avt_path.read_bytes()


def test_the_faced_avatar_is_a_valid_container(version_dir, repo_root):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    result = run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=FAST)
    assert len(read_avt(result.out_avatar).entries) == AVT_ENTRY_COUNT


# --- the manifest ----------------------------------------------------------------------

def test_a_manifest_is_written_on_success(version_dir, repo_root):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=FAST)

    manifest = json.loads((version_dir / FACE_MANIFEST_NAME).read_text(encoding='utf-8'))
    assert manifest['ok'] is True
    assert manifest['user_id'] == 'u_001'
    assert manifest['faced_avatar'].endswith(FACED_AVATAR_NAME)
    assert manifest['capture']['grade'] == 'good'
    assert manifest['quality_score'] is not None


def test_a_manifest_is_written_even_when_the_photo_is_refused(version_dir, repo_root):
    """A rejection is something a user has to be told; it cannot vanish silently."""
    photo = repo_root / 'face_fitting' / 'input' / 'test.png'
    options = FaceJobOptions(hair='none', eyes='none', write_diagnostics=False,
                             min_capture_grade='good')
    result = run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=options)

    assert not result.ok
    assert 'below the required' in result.reason
    manifest = json.loads((version_dir / FACE_MANIFEST_NAME).read_text(encoding='utf-8'))
    assert manifest['ok'] is False
    assert manifest['faced_avatar'] is None
    assert manifest['capture']['grade'] == 'poor'
    assert not (version_dir / FACED_AVATAR_NAME).exists()


# --- failure handling ------------------------------------------------------------------

def test_a_missing_photo_is_reported_not_raised(version_dir, tmp_path):
    result = fit_face(tmp_path / 'nope.png', version_dir / 'avatar.avt',
                      tmp_path / 'out.avt', tmp_path, options=FAST)
    assert not result.ok and 'not found' in result.reason


def test_a_missing_base_avatar_is_reported_not_raised(tmp_path, repo_root):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    result = fit_face(photo, tmp_path / 'nope.avt', tmp_path / 'out.avt', tmp_path,
                      options=FAST)
    assert not result.ok and 'not found' in result.reason


def test_an_image_with_no_face_is_reported_not_raised(tmp_path, base_avt_path):
    import cv2
    import numpy as np
    blank = tmp_path / 'blank.png'
    cv2.imwrite(str(blank), np.full((400, 400, 3), 128, np.uint8))

    result = fit_face(blank, base_avt_path, tmp_path / 'out.avt', tmp_path, options=FAST)
    assert not result.ok
    assert 'No face detected' in result.reason


# --- the quality score stored on the profile --------------------------------------------

def test_the_quality_score_tracks_the_capture_grade(version_dir, repo_root):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    good = run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=FAST)

    poor_photo = repo_root / 'face_fitting' / 'input' / 'test.png'
    poor = run_for_version_dir('u_001', poor_photo, version_dir / 'avatar.avt', options=FAST)

    assert good.quality_score > poor.quality_score
    assert 0.0 <= poor.quality_score <= 1.0 and 0.0 <= good.quality_score <= 1.0


def test_the_quality_score_is_none_without_an_assessment(tmp_path, base_avt_path):
    result = fit_face(tmp_path / 'nope.png', base_avt_path, tmp_path / 'out.avt', tmp_path)
    assert result.quality_score is None


# --- options ----------------------------------------------------------------------------

def test_disabling_a_stage_leaves_its_entries_alone(version_dir, repo_root):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    result = run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=FAST)
    changed = set(result.summary['entries_changed'])
    assert EYE_ALBEDO_ENTRY not in changed
    assert not any(name.startswith('hair_') for name in changed)


def test_diagnostics_are_skipped_when_turned_off(version_dir, repo_root):
    photo = repo_root / 'face_fitting' / 'input' / 'test2.png'
    run_for_version_dir('u_001', photo, version_dir / 'avatar.avt', options=FAST)
    assert not (version_dir / 'composite_albedo.png').exists()


# --- run directory numbering --------------------------------------------------------------

def test_run_directories_are_numbered_in_sequence(tmp_path):
    first = next_run_dir(tmp_path, 'u_001')
    second = next_run_dir(tmp_path, 'u_001')
    assert first.name == 'u_001-face-001'
    assert second.name == 'u_001-face-002'


def test_run_directories_are_per_user(tmp_path):
    next_run_dir(tmp_path, 'u_001')
    assert next_run_dir(tmp_path, 'u_002').name == 'u_002-face-001'
