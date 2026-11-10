"""Judge a photo before the pipeline spends any work on it.

Measured 2026-11-10: **input resolution dominates subject difficulty.** `test1.png` was
assumed to be the easy case - a stock photo, clean studio lighting - and `test2.png` the
hard one, a real phone photo. The opposite is true. test1 is 622x350, which is 77.7 px
between the eyes, a 4.3x upscale into the head albedo and a 5.3 px iris; eye colour
correctly declines because there is nothing there to measure. test2 is 1200x1600, 340 px
between the eyes, and everything works.

So the cheapest available quality improvement is not an algorithm, it is refusing a bad
photo and saying what to do about it. That is what this module is for. It reports, it does
not decide: `run_face_fitting.py` prints the verdict, and `--min-capture-grade` is there
for a caller that wants a hard gate.

The key number, measured rather than assumed: the stock head albedo has **400.7 px between
the eyes** at 2048 (`texture_fit._target_anchors`, taken with the same detector that reads
the photos). A photo with fewer than that is being upscaled into the UV map and its
resolution is the ceiling on everything downstream - no later stage recovers it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .landmarks import FaceLandmarks

# Interocular distance in the 2048 head albedo. At or above this the photo maps 1:1 and
# nothing is invented; below it, every pixel of the face is being stretched.
UV_INTEROCULAR_2048 = 400.7

# Grade bands, in photo interocular pixels.
GRADE_EXCELLENT = 400.0   # no upscale into the UV at all
GRADE_GOOD = 240.0        # under 1.7x upscale; eye colour has plenty to work with
GRADE_USABLE = 170.0      # the floor at which eye colour still measures (eye_fit)
GRADES = ('poor', 'usable', 'good', 'excellent')

# Iris diameter as a fraction of interocular distance, measured across both test photos
# (0.126, 0.128, 0.135, 0.136). Used to predict eye-colour viability before sampling.
IRIS_FRACTION = 0.13

# Sharpness is Laplacian variance of the face resampled to a fixed square, so that two
# photos at different resolutions are measured on the same footing. Thresholds below are
# calibrated against the two reference photos - see `_sharpness` for why the obvious
# normalisation is wrong.
SHARPNESS_REFERENCE_PX = 256
SHARPNESS_FLOOR = 60.0
SHARPNESS_GOOD = 200.0

# Head pose. Yaw is measured from how far off-centre the nose sits between the cheeks, as
# a fraction of face width; roll from the tilt of the eye line.
MAX_YAW_FRACTION = 0.08
MAX_ROLL_DEGREES = 8.0

# Share of face pixels allowed to be crushed to black or blown to white before the photo
# is carrying no detail in the shadows or the highlights.
MAX_CLIPPED_FRACTION = 0.06
_CLIP_LOW, _CLIP_HIGH = 6, 249

_MP_NOSE_TIP = 1
_MP_CHEEK_L = 234
_MP_CHEEK_R = 454
_MP_FOREHEAD = 10
_MP_CHIN = 152


@dataclass
class Check:
    name: str
    value: float | None
    passed: bool
    detail: str
    advice: str = ''

    def as_dict(self) -> dict:
        return {'name': self.name,
                'value': None if self.value is None else round(self.value, 3),
                'passed': self.passed, 'detail': self.detail, 'advice': self.advice}


@dataclass
class CaptureQuality:
    grade: str
    interocular_px: float
    uv_upscale: float
    eye_colour_viable: bool
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    @property
    def advice(self) -> list[str]:
        return [check.advice for check in self.checks if check.advice and not check.passed]

    def meets(self, minimum: str) -> bool:
        if minimum not in GRADES:
            raise ValueError(f'Unknown grade {minimum!r}; expected one of {GRADES}')
        return GRADES.index(self.grade) >= GRADES.index(minimum)

    def as_dict(self) -> dict:
        return {
            'grade': self.grade,
            'interocular_px': round(self.interocular_px, 2),
            'uv_upscale': round(self.uv_upscale, 3),
            'eye_colour_viable': self.eye_colour_viable,
            'passed': self.passed,
            'checks': [check.as_dict() for check in self.checks],
            'advice': self.advice,
        }


def _grade_for(interocular: float) -> str:
    if interocular >= GRADE_EXCELLENT:
        return 'excellent'
    if interocular >= GRADE_GOOD:
        return 'good'
    if interocular >= GRADE_USABLE:
        return 'usable'
    return 'poor'


def _face_box(landmarks: FaceLandmarks, shape: tuple[int, int]) -> tuple[int, int, int, int]:
    height, width = shape
    dense = landmarks.dense
    if dense is None:
        xs = [landmarks.eye_l[0], landmarks.eye_r[0], landmarks.mouth[0]]
        ys = [landmarks.eye_l[1], landmarks.eye_r[1], landmarks.mouth[1]]
    else:
        xs, ys = dense[:, 0], dense[:, 1]
    return (max(0, int(np.min(xs))), max(0, int(np.min(ys))),
            min(width, int(np.max(xs)) + 1), min(height, int(np.max(ys)) + 1))


def _sharpness(gray_face: np.ndarray, face_width: float) -> float:
    """Laplacian variance of the face resampled to a fixed size.

    Raw Laplacian variance cannot be compared across resolutions, and scaling it by face
    width makes that worse rather than better: the same face in fewer pixels has larger
    jumps between neighbouring pixels, so a small soft photo scores *higher* than a large
    detailed one. Measured on the two test photos, the naive version called a 622x350
    image 799 and a 1200x1600 image 22, which is exactly backwards.

    Resampling both to one size first is what makes the number mean "how much detail is in
    this face". A small face is interpolated up and loses variance, which is the honest
    answer: the detail was never there.
    """
    if gray_face.size == 0 or face_width <= 0:
        return 0.0
    interpolation = cv2.INTER_AREA if face_width >= SHARPNESS_REFERENCE_PX else cv2.INTER_CUBIC
    resized = cv2.resize(gray_face, (SHARPNESS_REFERENCE_PX, SHARPNESS_REFERENCE_PX),
                         interpolation=interpolation)
    return float(cv2.Laplacian(resized, cv2.CV_64F).var())


def _yaw_fraction(landmarks: FaceLandmarks) -> float | None:
    """How far off-centre the nose sits between the cheeks; 0 is square to the camera."""
    dense = landmarks.dense
    if dense is None or len(dense) <= _MP_CHEEK_R:
        return None
    left = float(dense[_MP_CHEEK_L][0])
    right = float(dense[_MP_CHEEK_R][0])
    nose = float(dense[_MP_NOSE_TIP][0])
    width = abs(right - left)
    if width < 1.0:
        return None
    return abs((nose - (left + right) / 2.0) / width)


def _roll_degrees(landmarks: FaceLandmarks) -> float:
    dx = landmarks.eye_r[0] - landmarks.eye_l[0]
    dy = landmarks.eye_r[1] - landmarks.eye_l[1]
    return abs(float(np.degrees(np.arctan2(dy, dx))))


def assess(photo_bgr: np.ndarray, landmarks: FaceLandmarks) -> CaptureQuality:
    """Score one photo. Reports; does not refuse."""
    interocular = landmarks.interocular
    upscale = UV_INTEROCULAR_2048 / interocular if interocular > 0 else float('inf')
    iris_px = interocular * IRIS_FRACTION
    grade = _grade_for(interocular)
    checks: list[Check] = []

    checks.append(Check(
        'resolution', interocular, interocular >= GRADE_USABLE,
        f'{interocular:.0f}px between the eyes; the UV map wants {UV_INTEROCULAR_2048:.0f}, '
        f'so the photo is scaled {upscale:.2f}x',
        'Move closer or use a higher-resolution camera. Source resolution is the ceiling '
        'on every later stage - nothing downstream recovers it.'))

    checks.append(Check(
        'eye colour', iris_px, iris_px >= GRADE_USABLE * IRIS_FRACTION,
        f'iris about {iris_px:.0f}px across',
        'Too few iris pixels to measure eye colour; it will stay the template brown.'))

    x0, y0, x1, y1 = _face_box(landmarks, photo_bgr.shape[:2])
    face = photo_bgr[y0:y1, x0:x1]
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY) if face.size else np.zeros((1, 1), np.uint8)
    sharpness = _sharpness(gray, max(x1 - x0, 1))
    checks.append(Check(
        'sharpness', sharpness, sharpness >= SHARPNESS_FLOOR,
        f'Laplacian variance {sharpness:.0f} (good is {SHARPNESS_GOOD:.0f}+)',
        'The face is soft or out of focus. Upscaling a blurred photo amplifies the blur, '
        'it does not recover detail. Hold still and refocus.'))

    yaw = _yaw_fraction(landmarks)
    if yaw is not None:
        checks.append(Check(
            'head turn', yaw, yaw <= MAX_YAW_FRACTION,
            f'nose is {yaw:.1%} of face width off centre',
            'Face the camera squarely. A turned head hides one cheek, and the warp fills '
            'that side from the template rather than from you.'))

    roll = _roll_degrees(landmarks)
    checks.append(Check(
        'head tilt', roll, roll <= MAX_ROLL_DEGREES,
        f'eye line tilted {roll:.1f} degrees',
        'Keep the eye line level. Tilt is corrected by rotating the photo, which costs a '
        'resampling pass over an already-limited image.'))

    if gray.size:
        clipped = float(((gray <= _CLIP_LOW) | (gray >= _CLIP_HIGH)).mean())
    else:
        clipped = 1.0
    checks.append(Check(
        'exposure', clipped, clipped <= MAX_CLIPPED_FRACTION,
        f'{clipped:.1%} of the face is crushed black or blown white',
        'Even, diffuse light on the face. Clipped pixels carry no colour, so skin and hair '
        'are sampled from whatever is left.'))

    return CaptureQuality(grade=grade, interocular_px=interocular, uv_upscale=upscale,
                          eye_colour_viable=iris_px >= GRADE_USABLE * IRIS_FRACTION,
                          checks=checks)
