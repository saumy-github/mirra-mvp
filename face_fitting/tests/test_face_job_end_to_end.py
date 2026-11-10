"""The whole face job, run the way the CLI runs it.

Marked slow: it shells out to `run_face_fitting.py`, which costs a MediaPipe pass plus a
31 MB container rewrite. Run with `-m "not slow"` to skip. What it is really guarding is
that the three texture jobs - face, hair, eyes - compose into one `.avt` that still parses,
because each one was proven on its own long before they ran together.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import cv2
import numpy as np
import pytest

from face_fitting.face_job import FACE_OUTPUT_ROOT
from face_fitting.face_runtime.constants import (AVT_ENTRY_COUNT, BODY_ALBEDO_ENTRIES,
                                                 EYE_ALBEDO_ENTRY, HAIR_CAP_ALBEDO_ENTRY,
                                                 HAIR_MAIN_ALBEDO_ENTRY, HEAD_ALBEDO_ENTRY)
from face_fitting.io.avt_container import read_avt

pytestmark = pytest.mark.slow

USER_ID = 'u_pytest_e2e'


@pytest.fixture(scope='module')
def face_job_run(repo_root):
    """Run the job once for the whole module, then remove its output directory."""
    from face_fitting.tests.conftest import PHOTO_HIGH_RES

    run_dirs_before = set(FACE_OUTPUT_ROOT.glob(f'{USER_ID}-face-*'))
    completed = subprocess.run(
        [sys.executable, 'face_fitting/run_face_fitting.py',
         '--photo', str(PHOTO_HIGH_RES), '--user-id', USER_ID],
        cwd=str(repo_root), capture_output=True, text=True, timeout=600,
    )
    run_dirs_after = set(FACE_OUTPUT_ROOT.glob(f'{USER_ID}-face-*'))
    created = sorted(run_dirs_after - run_dirs_before)

    try:
        yield completed, (created[0] if created else None)
    finally:
        for path in created:
            shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope='module')
def summary(face_job_run):
    completed, run_dir = face_job_run
    assert completed.returncode == 0, f'face job failed:\n{completed.stdout}\n{completed.stderr}'
    assert run_dir is not None, 'the job produced no run directory'
    return json.loads((run_dir / 'output.json').read_text(encoding='utf-8'))


def test_the_job_exits_clean_and_writes_a_run_directory(face_job_run):
    completed, run_dir = face_job_run
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert run_dir is not None and run_dir.is_dir()


def test_the_run_directory_carries_its_diagnostics(face_job_run):
    _, run_dir = face_job_run
    for name in ('output.json', 'composite_albedo.png', 'composite_weights.png',
                 'hair_sample.png', 'eye_sample.png'):
        assert (run_dir / name).exists(), f'missing diagnostic: {name}'


def test_all_three_texture_jobs_reported(summary):
    assert summary['fit']['landmark_source'] == 'mediapipe'
    assert summary['hair'] is not None
    assert summary['eyes'] is not None


def test_the_expected_entries_changed(summary):
    changed = set(summary['entries_changed'])
    assert HEAD_ALBEDO_ENTRY in changed
    assert {HAIR_MAIN_ALBEDO_ENTRY, HAIR_CAP_ALBEDO_ENTRY} <= changed
    assert EYE_ALBEDO_ENTRY in changed, 'eye colour did not reach the container'
    assert set(BODY_ALBEDO_ENTRIES) <= changed, 'skin reconciliation did not run'


def test_skin_reconciliation_runs_toward_the_user(summary):
    """`--skin-match body` by default: the face keeps its colour, the body comes to meet it.

    The bug this guards is the one that bleached a darker-skinned user by L=+29 - seam
    correct, product wrong.
    """
    assert summary['skin_match'] == 'body'
    assert summary['skin_delta_lab'] != [0.0, 0.0, 0.0]


def test_the_output_avatar_is_still_a_valid_avt(summary):
    container = read_avt(summary['output_avatar'])
    assert len(container.entries) == AVT_ENTRY_COUNT


def test_every_texture_in_the_output_still_decodes(summary):
    container = read_avt(summary['output_avatar'])
    for name in container.names():
        if not name.lower().endswith(('.jpg', '.png')):
            continue
        payload = container.read_entry(name)
        decoded = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_UNCHANGED)
        assert decoded is not None, f'{name} came out of the container undecodable'


def test_the_geometry_brain_is_byte_identical_to_the_base(summary):
    base = read_avt(summary['base_avatar'])
    patched = read_avt(summary['output_avatar'])
    assert patched.read_entry('first.dan') == base.read_entry('first.dan')


def test_untouched_entries_are_byte_identical_to_the_base(summary):
    base = read_avt(summary['base_avatar'])
    patched = read_avt(summary['output_avatar'])
    changed = set(summary['entries_changed'])
    for name in base.names():
        if name in changed:
            continue
        assert patched.read_entry(name) == base.read_entry(name), name


def test_the_console_report_mentions_each_stage(face_job_run):
    completed, _ = face_job_run
    for expected in ('Head albedo:', 'Hair sample:', 'Iris sample:', 'Faced avatar:'):
        assert expected in completed.stdout, f'{expected!r} missing from the report'
