"""Sample iris colour from the photo and recolour the .avt eye albedo.

The eyeball is `MV2_Jinho_01_eye.jpg` at 256 px - one texture shared by both eyes, so the
avatar gets one iris colour and heterochromia is out of reach. Everything else about the
eye is geometry or shading we do not touch: the pupil stays black, the sclera stays white,
and only the iris annulus between them moves. Same mechanism as the face albedo and the
hair textures. See
`.agent/clo-avatar-vto/avatar-personalization-split-decision-26_10_28.md` 1.4 and Part 7
Phase 1, which lists eye colour alongside hair colour and hair alpha.

The stock texture's structure, measured off its own radial Lab profile rather than assumed
(L* here is OpenCV's 0-255 scale, as everywhere else in this package):

    r  0-10   L*  0- 18   a=b=128 exactly      pupil, pure black
    r 10-14   L* 18- 39   a,b leaving neutral  pupil edge
    r 14-48   L* 34- 64   a 133-139 b 135-150  iris, warm brown
    r 48-54   L* 71-135                        limbal ring
    r 56+     L* 160-219  a 131 b 131-135      sclera
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cv2
import numpy as np

from .constants import EYE_ALBEDO_ENTRY, eye_geometry_for_size
from .landmarks import FaceLandmarks

if TYPE_CHECKING:
    from face_fitting.io.avt_container import AvtContainer

# MediaPipe's refined mesh appends ten iris vertices to the 468 face ones: a centre plus a
# four-point ring per eye. 468 is the iris beside vertex 33, which `landmarks.py` calls
# eye_l, and 473 the one beside 263. The OpenCV fallback has no iris at all, which is why
# eye colour needs MediaPipe and declines without it.
_MP_IRIS_L = 468
_MP_IRIS_R = 473
_MP_IRIS_RING = 4
DENSE_WITH_IRIS = 478

# Sampling annulus, as fractions of the detected iris radius. The inner bound clears the
# pupil at the widest it plausibly dilates; the outer one stays off the limbal ring, which
# is dark in everyone and would drag every sample toward brown.
IRIS_INNER_FRACTION = 0.42
IRIS_OUTER_FRACTION = 0.88
# MediaPipe fits the whole iris circle even where a lid covers it, so the top and bottom of
# that circle are often eyelid skin. Keeping to a horizontal band about the centre leaves
# the two side lobes, which is the part of the iris that is reliably visible.
IRIS_BAND_FRACTION = 0.55

# Catchlights are near-white and sit inside the iris. Dropped outright before any statistic
# is taken, because a flash highlight is bright enough to pull a mean several L* on its own.
SPECULAR_L = 230.0
# Then a symmetric trim, so neither the remaining highlight nor pupil bleed at the inner
# edge biases the result in either direction.
TRIM_PERCENTILES = (20.0, 80.0)

# An iris radius under about 11 px gives fewer usable pixels than this, and below that the
# sample is JPEG noise with an eye colour somewhere in it. 11 px of iris means roughly
# 170 px interocular, so this is also the honest resolution floor for the feature.
MIN_IRIS_PIXELS = 240
# Spread above which the sampled pixels are not one colour - usually a lid or lash caught
# in the mask, or a half-closed eye.
MAX_IRIS_L_STD = 38.0
# A sample this bright is sclera, not iris: the landmarks missed. Sclera starts at L* 160
# in the stock texture, so this sits a safe margin below it.
MAX_IRIS_L = 150.0

# Ceilings on the shift, because the photo's exposure rides on every channel of the sample:
# an underexposed frame would otherwise hand us a black iris and a blown one a white iris.
MAX_EYE_L_DELTA = 60.0
MAX_EYE_AB_DELTA = 30.0
# Below this the shift is inside one JPEG quantisation step, and re-encoding the texture
# would lose more than the recolour gains.
MIN_EYE_DELTA = 1.0


@dataclass
class EyeSample:
    """What the photo says about this user's iris colour, in photo pixel terms."""
    found: bool
    lab: tuple[float, float, float] | None
    lab_std: tuple[float, float, float] | None
    pixels: int
    confidence: float
    eyes_used: int
    iris_radius_px: float
    source: str
    warnings: list[str] = field(default_factory=list)
    # Where the numbers came from, so a bad sample is diagnosable from the run directory
    # alone and `debug_overlay` can draw it.
    geometry: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            'found': self.found,
            'lab': None if self.lab is None else [round(v, 2) for v in self.lab],
            'lab_std': None if self.lab_std is None else [round(v, 2) for v in self.lab_std],
            'pixels': self.pixels,
            'confidence': round(self.confidence, 3),
            'eyes_used': self.eyes_used,
            'iris_radius_px': round(self.iris_radius_px, 2),
            'source': self.source,
            'warnings': self.warnings,
            'geometry': self.geometry,
        }


@dataclass
class EyeReport:
    mode: str
    recoloured: bool
    delta_lab: tuple[float, float, float]
    source_l: float
    target_l: float
    texture_size: int
    entries_changed: list[str]
    sample: EyeSample
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            'mode': self.mode,
            'recoloured': self.recoloured,
            'delta_lab': [round(v, 2) for v in self.delta_lab],
            'source_l': round(self.source_l, 2),
            'target_l': round(self.target_l, 2),
            'texture_size': self.texture_size,
            'entries_changed': self.entries_changed,
            'sample': self.sample.as_dict(),
            'warnings': self.warnings,
        }


def _empty_sample(source: str, reason: str) -> EyeSample:
    return EyeSample(found=False, lab=None, lab_std=None, pixels=0, confidence=0.0,
                     eyes_used=0, iris_radius_px=0.0, source=source, warnings=[reason])


def _iris_circles(landmarks: FaceLandmarks) -> list[tuple[float, float, float]]:
    """Centre and radius of each iris in photo pixels, from the refined mesh. [] without it."""
    dense = landmarks.dense
    if dense is None or len(dense) < DENSE_WITH_IRIS:
        return []
    circles: list[tuple[float, float, float]] = []
    for base in (_MP_IRIS_L, _MP_IRIS_R):
        centre = dense[base]
        ring = dense[base + 1: base + 1 + _MP_IRIS_RING]
        radius = float(np.mean(np.hypot(ring[:, 0] - centre[0], ring[:, 1] - centre[1])))
        if radius > 0.0:
            circles.append((float(centre[0]), float(centre[1]), radius))
    return circles


def _iris_mask(shape: tuple[int, int], cx: float, cy: float, radius: float) -> np.ndarray:
    """Two side lobes of the iris: inside the annulus and inside the horizontal band."""
    height, width = shape
    y0 = max(0, int(np.floor(cy - radius)))
    y1 = min(height, int(np.ceil(cy + radius)) + 1)
    x0 = max(0, int(np.floor(cx - radius)))
    x1 = min(width, int(np.ceil(cx + radius)) + 1)
    mask = np.zeros((height, width), bool)
    if y1 <= y0 or x1 <= x0:
        return mask

    yy, xx = np.mgrid[y0:y1, x0:x1]
    dy = yy - cy
    dist = np.hypot(xx - cx, dy)
    mask[y0:y1, x0:x1] = ((dist >= IRIS_INNER_FRACTION * radius)
                          & (dist <= IRIS_OUTER_FRACTION * radius)
                          & (np.abs(dy) <= IRIS_BAND_FRACTION * radius))
    return mask


def sample_iris(photo_bgr: np.ndarray, landmarks: FaceLandmarks) -> EyeSample:
    """Mean iris Lab from one frontal photo, or a sample marked not-found with the reason."""
    circles = _iris_circles(landmarks)
    if not circles:
        return _empty_sample(landmarks.source,
                             'Iris landmarks unavailable, so eye colour was not measured. '
                             'The refined MediaPipe mesh is required; the OpenCV fallback '
                             'has no iris.')

    lab = cv2.cvtColor(photo_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    mask = np.zeros(photo_bgr.shape[:2], bool)
    for cx, cy, radius in circles:
        mask |= _iris_mask(photo_bgr.shape[:2], cx, cy, radius)

    radius_mean = float(np.mean([c[2] for c in circles]))
    geometry = {
        'circles': [[round(cx, 1), round(cy, 1), round(r, 2)] for cx, cy, r in circles],
        'inner_fraction': IRIS_INNER_FRACTION,
        'outer_fraction': IRIS_OUTER_FRACTION,
        'band_fraction': IRIS_BAND_FRACTION,
    }

    pixels = lab[mask]
    if pixels.shape[0] == 0:
        sample = _empty_sample(landmarks.source, 'The iris sampling region fell outside the photo.')
        sample.iris_radius_px = radius_mean
        sample.geometry = geometry
        return sample

    # Drop the catchlight before measuring anything, then trim symmetrically.
    kept = pixels[pixels[:, 0] < SPECULAR_L]
    specular_dropped = int(pixels.shape[0] - kept.shape[0])
    geometry['specular_dropped'] = specular_dropped
    if kept.shape[0] == 0:
        sample = _empty_sample(landmarks.source,
                               'Every iris pixel was a specular highlight; the eyes are blown out.')
        sample.iris_radius_px = radius_mean
        sample.geometry = geometry
        return sample

    low, high = np.percentile(kept[:, 0], TRIM_PERCENTILES)
    core = kept[(kept[:, 0] >= low) & (kept[:, 0] <= high)]
    if core.shape[0] == 0:
        core = kept

    mean = tuple(float(core[:, c].mean()) for c in range(3))
    std = tuple(float(core[:, c].std()) for c in range(3))
    geometry['trimmed_l_range'] = [round(float(low), 1), round(float(high), 1)]

    warnings: list[str] = []
    usable = int(core.shape[0])
    if usable < MIN_IRIS_PIXELS:
        warnings.append(f'Only {usable} usable iris pixels (need {MIN_IRIS_PIXELS}); the iris is '
                        f'{radius_mean:.1f}px across in this photo. Eye colour left at stock.')
    if std[0] > MAX_IRIS_L_STD:
        warnings.append(f'Iris sample spread L={std[0]:.1f} is too wide to be one colour - '
                        'likely a lid, lash or half-closed eye in the mask.')
    if mean[0] > MAX_IRIS_L:
        warnings.append(f'Iris sample L={mean[0]:.1f} reads as sclera, not iris; the landmarks '
                        'probably missed. Eye colour left at stock.')

    found = not warnings
    # Confidence is the pixel count against the floor, so it says how much photo there was
    # to measure rather than how certain the colour is. Zero whenever a guard fired.
    confidence = 0.0 if not found else float(np.clip(usable / (MIN_IRIS_PIXELS * 4.0), 0.0, 1.0))

    return EyeSample(found=found, lab=mean, lab_std=std, pixels=usable, confidence=confidence,
                     eyes_used=len(circles), iris_radius_px=radius_mean, source=landmarks.source,
                     warnings=warnings, geometry=geometry)


def iris_weight(size: int) -> np.ndarray:
    """Feathered 0-1 mask over the iris annulus of the eye texture, measured per 1.4.

    Zero on the pupil and on the sclera, so neither moves however far the iris travels.
    Both edges are smoothstepped: a hard edge at the pupil boundary reads as a drawn ring.
    """
    geometry = eye_geometry_for_size(size)
    cx, cy = geometry['centre']
    pupil, inner, outer, limbus = (geometry['pupil_radius'], geometry['iris_inner'],
                                   geometry['iris_outer'], geometry['limbus_radius'])

    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    dist = np.hypot(xx - cx, yy - cy)

    rise = np.clip((dist - pupil) / max(inner - pupil, 1e-6), 0.0, 1.0)
    fall = np.clip((limbus - dist) / max(limbus - outer, 1e-6), 0.0, 1.0)
    weight = np.minimum(rise, fall)
    # Smoothstep, so the feather has no visible shoulder where it meets full strength.
    return (weight * weight * (3.0 - 2.0 * weight)).astype(np.float32)


def iris_mean_lab(texture_bgr: np.ndarray, weight: np.ndarray) -> tuple[float, float, float]:
    """Mean Lab of the stock iris, over the core of the mask only."""
    lab = cv2.cvtColor(texture_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    core = weight > 0.5
    if not core.any():
        core = weight > 0.0
    return tuple(float(lab[..., c][core].mean()) for c in range(3))


def recolour_iris(texture_bgr: np.ndarray, delta_lab: tuple[float, float, float],
                  weight: np.ndarray) -> np.ndarray:
    """Mean-shift the iris in Lab, weighted by the feathered mask.

    No contrast gain, unlike the hair: the stock iris already carries L* 34-64 of radial
    structure, so a plain mean shift keeps the fibre detail the artist painted. The hair
    needed a gain only because its strands start out near-black and flat.
    """
    lab = cv2.cvtColor(texture_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    for channel in range(3):
        lab[..., channel] += delta_lab[channel] * weight
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def debug_overlay(photo_bgr: np.ndarray, sample: EyeSample) -> np.ndarray:
    """Draw the iris circles, the sampled band and the resulting colour onto the photo."""
    out = photo_bgr.copy()
    thickness = max(1, out.shape[1] // 600)
    for cx, cy, radius in sample.geometry.get('circles', []):
        centre = (int(round(cx)), int(round(cy)))
        cv2.circle(out, centre, max(1, int(round(radius))), (0, 255, 255), thickness)
        cv2.circle(out, centre, max(1, int(round(radius * IRIS_INNER_FRACTION))),
                   (255, 128, 0), thickness)
        cv2.circle(out, centre, max(1, int(round(radius * IRIS_OUTER_FRACTION))),
                   (0, 255, 0), thickness)
    if sample.lab is not None:
        swatch_lab = np.array([[sample.lab]], np.float32)
        bgr = cv2.cvtColor(swatch_lab.astype(np.uint8), cv2.COLOR_LAB2BGR)[0, 0].tolist()
        side = max(24, out.shape[1] // 12)
        cv2.rectangle(out, (0, 0), (side, side), bgr, -1)
        cv2.rectangle(out, (0, 0), (side, side), (255, 255, 255), thickness)
    return out


def _decode(container: 'AvtContainer', name: str) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(container.read_entry(name), np.uint8), cv2.IMREAD_COLOR)


def _encode_into(container: 'AvtContainer', name: str, image: np.ndarray, quality: int) -> bool:
    ok, encoded = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return False
    container.replace_entry(name, encoded.tobytes())
    return True


def apply_eyes(container: 'AvtContainer', photo_bgr: np.ndarray, landmarks: FaceLandmarks, *,
               mode: str = 'auto', jpeg_quality: int = 95) -> EyeReport:
    """Recolour the container's iris in place from one frontal photo.

    `mode` is 'auto' or 'none'. One texture serves both eyes, so one colour is all there
    is; the pupil and sclera are left exactly as the artist painted them.
    """
    sample = sample_iris(photo_bgr, landmarks)
    texture = _decode(container, EYE_ALBEDO_ENTRY)
    size = texture.shape[0]
    weight = iris_weight(size)
    source_lab = iris_mean_lab(texture, weight)

    report = EyeReport(mode=mode, recoloured=False, delta_lab=(0.0, 0.0, 0.0),
                       source_l=source_lab[0], target_l=source_lab[0], texture_size=size,
                       entries_changed=[], sample=sample)

    if not sample.found or sample.lab is None:
        # Declining is the only safe reading of a bad sample: a wrong iris colour is one of
        # the most visible errors on a face, and the stock brown is a defensible default.
        report.warnings.append('Eye colour left at the stock iris.')
        report.warnings.extend(sample.warnings)
        return report

    # Clamped, because the photo's exposure rides on every one of these numbers: a dark
    # frame would otherwise hand us a black iris and a blown one a glowing white iris.
    delta = (
        float(np.clip(sample.lab[0] - source_lab[0], -MAX_EYE_L_DELTA, MAX_EYE_L_DELTA)),
        float(np.clip(sample.lab[1] - source_lab[1], -MAX_EYE_AB_DELTA, MAX_EYE_AB_DELTA)),
        float(np.clip(sample.lab[2] - source_lab[2], -MAX_EYE_AB_DELTA, MAX_EYE_AB_DELTA)),
    )
    report.delta_lab = delta
    report.target_l = source_lab[0] + delta[0]

    if max(abs(v) for v in delta) < MIN_EYE_DELTA:
        # Not worth a lossy re-encode of a texture that is already the right colour.
        report.warnings.append('Iris already within a JPEG step of the stock colour; left alone.')
        return report

    recoloured = recolour_iris(texture, delta, weight)
    if not _encode_into(container, EYE_ALBEDO_ENTRY, recoloured, jpeg_quality):
        report.warnings.append(f'Failed to encode {EYE_ALBEDO_ENTRY}; eye colour left at stock.')
        return report

    report.recoloured = True
    report.entries_changed = [EYE_ALBEDO_ENTRY]
    return report
