"""Shared fixtures for the face-fitting tests.

MediaPipe detection costs a couple of seconds a photo, so the landmark fixtures are
session-scoped. The container fixture is not: every test that patches one needs its own.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_fitting.face_runtime.landmarks import detect_landmarks  # noqa: E402
from face_fitting.io.avt_container import read_avt  # noqa: E402

BASE_AVATAR = REPO_ROOT / 'clo_avatar_generation' / 'input' / 'base-1.avt'
PHOTO_HIGH_RES = REPO_ROOT / 'face_fitting' / 'input' / 'test2.png'
PHOTO_LOW_RES = REPO_ROOT / 'face_fitting' / 'input' / 'test.png'


def _imread(path: Path) -> np.ndarray:
    # np.fromfile rather than cv2.imread: the repo's paths are Windows paths and may be
    # non-ASCII, which cv2.imread silently fails on.
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


@pytest.fixture(scope='session')
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope='session')
def base_avt_path() -> Path:
    if not BASE_AVATAR.exists():
        pytest.skip(f'Base avatar not present: {BASE_AVATAR}')
    return BASE_AVATAR


@pytest.fixture
def container(base_avt_path):
    """A fresh parse per test, because most tests mutate it."""
    return read_avt(base_avt_path)


@pytest.fixture(scope='session')
def photo_high_res() -> np.ndarray:
    if not PHOTO_HIGH_RES.exists():
        pytest.skip(f'Test photo not present: {PHOTO_HIGH_RES}')
    return _imread(PHOTO_HIGH_RES)


@pytest.fixture(scope='session')
def photo_low_res() -> np.ndarray:
    if not PHOTO_LOW_RES.exists():
        pytest.skip(f'Test photo not present: {PHOTO_LOW_RES}')
    return _imread(PHOTO_LOW_RES)


@pytest.fixture(scope='session')
def landmarks_high_res(photo_high_res):
    found = detect_landmarks(photo_high_res)
    if found is None:
        pytest.skip('No face detected in the high-resolution test photo')
    return found


@pytest.fixture(scope='session')
def landmarks_low_res(photo_low_res):
    found = detect_landmarks(photo_low_res)
    if found is None:
        pytest.skip('No face detected in the low-resolution test photo')
    return found
