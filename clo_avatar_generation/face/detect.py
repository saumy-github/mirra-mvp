"""Detect face landmarks in a photo using MediaPipe FaceLandmarker."""

from __future__ import annotations

import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


_MODELS_DIR = Path(__file__).parent / "models"
_MODEL_PATH = _MODELS_DIR / "face_landmarker.task"
_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "face_landmarker/face_landmarker/float16/1/face_landmarker.task"
)

# 36-point face oval contour (MediaPipe landmark indices)
FACE_OVAL_INDICES: list[int] = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
]


def _ensure_model() -> None:
    if _MODEL_PATH.exists():
        return
    _MODELS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading face landmark model → {_MODEL_PATH} ...")
    urllib.request.urlretrieve(_MODEL_URL, _MODEL_PATH)
    print("Done.")


def detect(image_path: Path) -> dict:
    """
    Detect face landmarks in a photo.

    Returns:
        detected       : bool — False if no face found
        image_size     : [width, height]
        landmarks_norm : list[tuple[float,float]] — 478 points in [0,1]
        landmarks_px   : list[tuple[int,int]]     — 478 points in pixels
        face_oval_px   : list[tuple[int,int]]     — 36-point oval in pixels
        face_bbox      : {x_min, x_max, y_min, y_max}
    """
    _ensure_model()

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {image_path}")
    h, w = img.shape[:2]

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    options = vision.FaceLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(_MODEL_PATH)),
        num_faces=1,
        min_face_detection_confidence=0.3,
        min_face_presence_confidence=0.3,
    )
    with vision.FaceLandmarker.create_from_options(options) as detector:
        result = detector.detect(mp_image)

    if not result.face_landmarks:
        return {"detected": False, "image_size": [w, h]}

    lm = result.face_landmarks[0]
    norm: list[tuple[float, float]] = [(l.x, l.y) for l in lm]
    px: list[tuple[int, int]] = [
        (int(round(l.x * w)), int(round(l.y * h))) for l in lm
    ]
    oval = [px[i] for i in FACE_OVAL_INDICES]
    xs = [p[0] for p in oval]
    ys = [p[1] for p in oval]

    return {
        "detected": True,
        "image_size": [w, h],
        "landmarks_norm": norm,
        "landmarks_px": px,
        "face_oval_px": oval,
        "face_bbox": {
            "x_min": min(xs), "x_max": max(xs),
            "y_min": min(ys), "y_max": max(ys),
        },
    }
