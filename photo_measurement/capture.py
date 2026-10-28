"""Photo -> Observation (person mask + 2D pose landmarks) using MediaPipe Pose Landmarker.

MediaPipe is Apache-2.0 licensed, so this stage is safe for commercial use.
"""
from __future__ import annotations

import os
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_full/float16/latest/pose_landmarker_full.task"
)
DEFAULT_MODEL = Path(__file__).resolve().parent / "models" / "pose_landmarker_full.task"

# MediaPipe Pose landmark indices we use.
LANDMARKS = {
    "nose": 0, "left_ear": 7, "right_ear": 8,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
    "left_heel": 29, "right_heel": 30,
    "left_foot_index": 31, "right_foot_index": 32,
}


@dataclass
class Observation:
    """One photo reduced to what the measurement stage needs (pixel coordinates)."""
    mask: np.ndarray                      # bool HxW, True = person
    landmarks: dict[str, tuple[float, float, float]]  # name -> (x, y, visibility)
    image_path: str = ""
    image: np.ndarray | None = None       # HxWx3 RGB uint8, for colour sampling
    warnings: list[str] = field(default_factory=list)

    def pt(self, name: str) -> np.ndarray:
        x, y, _ = self.landmarks[name]
        return np.array([x, y], float)

    def mid(self, a: str, b: str) -> np.ndarray:
        return (self.pt(a) + self.pt(b)) / 2.0


@contextmanager
def _quiet_native_stderr():
    """MediaPipe's C++ layer logs straight to fd 2 and ignores Python logging."""
    saved = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)


def ensure_model(path: Path = DEFAULT_MODEL) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, path)
    return path


def _largest_component(mask: np.ndarray) -> np.ndarray:
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if n <= 1:
        return mask
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return labels == largest


def observe(image_path: str | Path, model_path: Path | None = None, mask_threshold: float = 0.5) -> Observation:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    model = ensure_model(model_path or DEFAULT_MODEL)
    options = vision.PoseLandmarkerOptions(
        # CPU: the Metal/GPU path aborts on some macOS builds and servers rarely have GPUs.
        base_options=BaseOptions(model_asset_path=str(model), delegate=BaseOptions.Delegate.CPU),
        running_mode=vision.RunningMode.IMAGE,
        output_segmentation_masks=True,
        num_poses=1,
    )
    # The phone endpoint accepts JPEG, PNG and WebP. MediaPipe's file loader
    # does not decode WebP on every platform; OpenCV supports all three and
    # honours camera EXIF rotation before pose detection.
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise RuntimeError("The body photo could not be decoded.")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    with _quiet_native_stderr(), vision.PoseLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(image)
    if not result.pose_landmarks:
        raise RuntimeError(f"no person detected in {image_path}")

    h, w = image.height, image.width
    lms = result.pose_landmarks[0]
    landmarks = {
        name: (lms[i].x * w, lms[i].y * h, float(lms[i].visibility or 0.0))
        for name, i in LANDMARKS.items()
    }
    raw = result.segmentation_masks[0].numpy_view()
    mask = raw.reshape(raw.shape[0], raw.shape[1]) > mask_threshold
    mask = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)) > 0
    mask = _largest_component(mask)

    rgb = np.asarray(image.numpy_view())
    rgb = np.stack([rgb] * 3, axis=-1) if rgb.ndim == 2 else rgb[..., :3].copy()
    obs = Observation(mask=mask, landmarks=landmarks, image_path=str(image_path), image=rgb)
    top, bottom = np.flatnonzero(mask.any(axis=1))[[0, -1]]
    if top <= 2:
        obs.warnings.append("head touches top edge of photo: step back, height scale will be wrong")
    if bottom >= h - 3:
        obs.warnings.append("feet touch bottom edge of photo: step back, height scale will be wrong")
    return obs
