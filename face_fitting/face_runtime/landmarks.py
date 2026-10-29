"""Face landmark detection: MediaPipe's dense mesh when available, OpenCV 3-point fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# MediaPipe 1.x ships only the Tasks API, which loads this bundle from disk.
FACE_LANDMARKER_MODEL = Path(__file__).resolve().parents[1] / 'reference' / 'models' / 'face_landmarker.task'

# MediaPipe FaceMesh indices for the anchors we register against.
_MP_EYE_L = 33
_MP_EYE_R = 263
_MP_MOUTH_UPPER = 13
_MP_MOUTH_LOWER = 14
# Outer face silhouette, used to build the blend mask when the dense mesh is available.
_MP_FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400,
    377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
]


@dataclass
class FaceLandmarks:
    """Anchors in photo pixel coordinates, plus the dense mesh when MediaPipe supplied one."""
    eye_l: tuple[float, float]
    eye_r: tuple[float, float]
    mouth: tuple[float, float]
    source: str
    dense: np.ndarray | None = None
    oval: np.ndarray | None = None

    @property
    def interocular(self) -> float:
        return float(np.hypot(self.eye_r[0] - self.eye_l[0], self.eye_r[1] - self.eye_l[1]))

    def anchor_matrix(self) -> np.ndarray:
        return np.array([self.eye_l, self.eye_r, self.mouth], dtype=np.float32)


def mediapipe_available() -> bool:
    try:
        import mediapipe  # noqa: F401
        return FACE_LANDMARKER_MODEL.exists()
    except Exception:
        return False


def _detect_mediapipe(image_bgr: np.ndarray) -> FaceLandmarks | None:
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.core.base_options import BaseOptions

    height, width = image_bgr.shape[:2]
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(FACE_LANDMARKER_MODEL)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
    )
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB,
                        data=cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
    with vision.FaceLandmarker.create_from_options(options) as landmarker:
        result = landmarker.detect(mp_image)

    if not result.face_landmarks:
        return None

    points = np.array([[lm.x * width, lm.y * height]
                       for lm in result.face_landmarks[0]], dtype=np.float32)
    mouth = (points[_MP_MOUTH_UPPER] + points[_MP_MOUTH_LOWER]) / 2.0
    return FaceLandmarks(
        eye_l=tuple(points[_MP_EYE_L]),
        eye_r=tuple(points[_MP_EYE_R]),
        mouth=tuple(mouth),
        source='mediapipe',
        dense=points,
        oval=points[_MP_FACE_OVAL],
    )


def _detect_opencv(image_bgr: np.ndarray) -> FaceLandmarks | None:
    """Prototype-grade fallback: Haar face box, then eyes inside it, mouth inferred geometrically."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
    if len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
    eyes = eye_cascade.detectMultiScale(gray[y:y + int(h * 0.6), x:x + w], 1.1, 6)

    if len(eyes) >= 2:
        chosen = sorted(eyes, key=lambda e: e[2] * e[3], reverse=True)[:2]
        centres = sorted([(x + ex + ew / 2.0, y + ey + eh / 2.0) for ex, ey, ew, eh in chosen])
        eye_l, eye_r = centres[0], centres[1]
    else:
        # Fall back to the canonical eye placement within a Haar face box.
        eye_l = (x + 0.30 * w, y + 0.38 * h)
        eye_r = (x + 0.70 * w, y + 0.38 * h)

    mouth = ((eye_l[0] + eye_r[0]) / 2.0, y + 0.75 * h)
    return FaceLandmarks(eye_l=eye_l, eye_r=eye_r, mouth=mouth, source='opencv_haar')


def detect_landmarks(image_bgr: np.ndarray, *, prefer_mediapipe: bool = True) -> FaceLandmarks | None:
    if prefer_mediapipe and mediapipe_available():
        found = _detect_mediapipe(image_bgr)
        if found is not None:
            return found
    return _detect_opencv(image_bgr)
