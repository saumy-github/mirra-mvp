"""Photo -> 478 face landmarks with MediaPipe Face Landmarker (Apache-2.0)."""
from __future__ import annotations

import os
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)
DEFAULT_MODEL = Path(__file__).resolve().parent / "models" / "face_landmarker.task"
MAX_SIDE_PX = 2048  # bigger phone photos only cost time; landmarks don't improve


@dataclass
class FaceObservation:
    """One photo. `points` are (478, 3): x, y in image pixels, z in the same
    pixel scale (MediaPipe's relative depth; smaller = closer to the camera)."""
    view: str
    image: np.ndarray        # HxWx3 RGB uint8
    points: np.ndarray


def ensure_model(path: Path = DEFAULT_MODEL) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, path)
    return path


@contextmanager
def _quiet_native_stderr():
    """MediaPipe's C++ layer logs straight to fd 2."""
    saved, devnull = os.dup(2), os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 2)
        yield
    finally:
        os.dup2(saved, 2)
        os.close(devnull)
        os.close(saved)


def load_rgb(path: str | Path) -> np.ndarray:
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"could not read image {path}")
    h, w = bgr.shape[:2]
    if max(h, w) > MAX_SIDE_PX:
        s = MAX_SIDE_PX / max(h, w)
        bgr = cv2.resize(bgr, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def observe(path: str | Path, view: str, model_path: Path | None = None) -> FaceObservation:
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    rgb = load_rgb(path)
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(ensure_model(model_path or DEFAULT_MODEL)),
                                 delegate=BaseOptions.Delegate.CPU),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.5,
    )
    with _quiet_native_stderr(), vision.FaceLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)))
    if not result.face_landmarks:
        raise RuntimeError(f"no face detected in the {view} photo")
    h, w = rgb.shape[:2]
    pts = np.array([[p.x * w, p.y * h, p.z * w] for p in result.face_landmarks[0]], float)
    return FaceObservation(view=view, image=rgb, points=pts)
