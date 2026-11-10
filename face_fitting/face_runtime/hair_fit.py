"""Sample hair colour and density from the photo, then recolour and thin the .avt hair textures.

Hairstyle - length, curl, parting, volume - is geometry baked into `first.dan` and out of
reach. Colour, perceived density and hairline position are not: they are four ordinary
textures in the container, reachable by the same mechanism as the face albedo. See
`.agent/clo-avatar-vto/avatar-personalization-split-decision-26_10_28.md` 1.4 and 5.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import cv2
import numpy as np

from .constants import (HAIR_CAP_ALBEDO_ENTRY, HAIR_CAP_ALPHA_ENTRY, HAIR_MAIN_ALBEDO_ENTRY,
                        HAIR_MAIN_ALPHA_ENTRY, HAIR_TEXTURE_SIZE)
from .landmarks import FaceLandmarks

if TYPE_CHECKING:
    from face_fitting.io.avt_container import AvtContainer

# MediaPipe mesh vertices that bound the head in the photo. 10 sits mid-forehead, not at
# the hairline, which is exactly why a receding hairline shows up as a measurable rise.
_MP_FOREHEAD = 10
_MP_CHIN = 152
_MP_CHEEK_L = 234
_MP_CHEEK_R = 454

# Forehead skin reference patch, as fractions of face height below the forehead vertex and
# of face width either side of centre. Kept clear of the brows and of the temple shadow.
SKIN_PATCH_V = (0.04, 0.16)
SKIN_PATCH_U = 0.20

# Lab distance from forehead skin at which a pixel stops being skin and starts being hair.
# Generous, because forehead speculars swing L* by 15 or so on their own.
SKIN_DISTANCE = 22.0
# A hairline has to be a sustained run, not one noisy pixel. As a fraction of face height.
HAIR_RUN_V = 0.02
# How far above the forehead vertex to look before calling it bald, as a fraction of face height.
SEARCH_V = 0.60
# Columns walked upward: centre, and either side at this fraction of face width, which is
# where a receding hairline shows first.
TEMPLE_U = 0.18

# Colour band above the detected hairline, as fractions of face height and width. Sized
# generously; the band follows the hairline curve and `_sample_pixels` then drops the skin
# and background pixels inside it, which is what keeps a short crop off the wall behind.
COLOUR_BAND_V = 0.22
COLOUR_BAND_U = 0.25
# The backdrop is measured rather than guessed at, because curls are full of holes and the
# wall shows through every one. Lab distance below which a band pixel is backdrop, not hair.
BACKGROUND_DISTANCE = 30.0
# Margin strips sampled for the background colour, as multiples of face width from centre.
BACKGROUND_MARGIN_U = 1.1
# Spread above which the backdrop is too busy to have one colour; the filter is then skipped.
BACKGROUND_L_STD = 25.0
# Below this many usable pixels the sample is not worth trusting.
MIN_COLOUR_PIXELS = 400
# Spread of the trimmed core above which the hair colour is not a single colour.
MIXED_BAND_L_STD = 42.0

# Hairline rise, as a fraction of face height, that maps to full and to zero density.
DENSITY_RISE_FULL = 0.05
DENSITY_RISE_BALD = 0.30

# Thinning limits at 2048 px. The strand cards are a few pixels wide, so a radius of 8
# erases all but the thickest of them.
MAX_ERODE_PX = 8
# Extra gamma applied to the alpha at full strength. The maps are soft JPEGs, so most of
# the perceived density sits in the mid-greys that whole-pixel erosion cannot reach.
ALPHA_GAMMA_RANGE = 2.0

# Ceiling on the contrast expansion used when brightening. The stock strands are near-black
# (L* 2.6), so a pure mean shift to a light target yields flat paint; a gain around the mean
# lifts the little strand variance that survived the JPEG with it.
MAX_CONTRAST_GAIN = 2.5

# CLO renders hair far darker than its albedo: the strand cards are semi-transparent, so
# every pixel is a stack of partly-lit strands over the cap and the scalp beneath. Measured
# 2026-11-10 by sampling the same hair in the albedo we wrote and in a CLO screenshot of
# the avatar wearing it - albedo L* 35.2 rendered as L* 18.6, a factor of 0.528. Aiming the
# albedo straight at the colour sampled from the photo therefore undershoots: the user sees
# hair about half as light as their own.
#
# One subject, one lighting rig, one camera - not enough to turn this on by default, which
# is why `render_compensation` is 0.0 unless asked for. To calibrate: run the face job at a
# few compensation values, screenshot each in CLO, and compare with
# `compare_to_photo.py`, which scores hair-to-skin contrast directly.
RENDER_LIGHTNESS_FACTOR = 0.528
# Never ask the albedo for more than this, however dark the render is: past it the strands
# stop reading as hair and start reading as grey paint.
MAX_COMPENSATED_L = 170.0


@dataclass
class HairSample:
    """What the photo says about this user's hair, in photo pixel terms."""
    found: bool
    lab: tuple[float, float, float] | None
    lab_std: tuple[float, float, float] | None
    pixels: int
    confidence: float
    hairline_rise: float
    density_ratio: float
    columns_with_hair: int
    source: str
    # Whether the scalp walk actually ran. `found` is about colour and is False for a bald
    # head too; this is about trust, and separates "no hair there" from "could not look".
    measured: bool = False
    warnings: list[str] = field(default_factory=list)
    # Where in the photo the numbers above came from. Reported so a bad sample can be
    # diagnosed from the run directory alone, and drawn by `debug_overlay`.
    geometry: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            'found': self.found,
            'lab': None if self.lab is None else [round(v, 2) for v in self.lab],
            'lab_std': None if self.lab_std is None else [round(v, 2) for v in self.lab_std],
            'pixels': self.pixels,
            'confidence': round(self.confidence, 3),
            'hairline_rise': round(self.hairline_rise, 4),
            'density_ratio': round(self.density_ratio, 3),
            'columns_with_hair': self.columns_with_hair,
            'source': self.source,
            'measured': self.measured,
            'warnings': self.warnings,
            'geometry': self.geometry,
        }


@dataclass
class HairReport:
    mode: str
    recoloured: bool
    thinned: bool
    delta_lab: tuple[float, float, float]
    contrast_gain: float
    density_strength: float
    density_source: str
    erode_radius_px: int
    source_l: float
    target_l: float
    alpha_opacity_before: float
    alpha_opacity_after: float
    entries_changed: list[str]
    sample: HairSample
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            'mode': self.mode,
            'recoloured': self.recoloured,
            'thinned': self.thinned,
            'delta_lab': [round(v, 2) for v in self.delta_lab],
            'contrast_gain': round(self.contrast_gain, 3),
            'density_strength': round(self.density_strength, 3),
            'density_source': self.density_source,
            'erode_radius_px': self.erode_radius_px,
            'source_l': round(self.source_l, 2),
            'target_l': round(self.target_l, 2),
            'alpha_opacity_before': round(self.alpha_opacity_before, 4),
            'alpha_opacity_after': round(self.alpha_opacity_after, 4),
            'entries_changed': self.entries_changed,
            'sample': self.sample.as_dict(),
            'warnings': self.warnings,
        }


def _head_frame(landmarks: FaceLandmarks) -> tuple[float, float, float, float] | None:
    """(centre_x, forehead_y, face_width, face_height) from the dense mesh, or None."""
    if landmarks.dense is None or len(landmarks.dense) <= _MP_CHEEK_R:
        return None
    dense = landmarks.dense
    forehead_y = float(dense[_MP_FOREHEAD][1])
    chin_y = float(dense[_MP_CHIN][1])
    left_x = float(dense[_MP_CHEEK_L][0])
    right_x = float(dense[_MP_CHEEK_R][0])
    height = abs(chin_y - forehead_y)
    width = abs(right_x - left_x)
    if height < 1.0 or width < 1.0:
        return None
    return (left_x + right_x) / 2.0, forehead_y, width, height


def _skin_reference(lab: np.ndarray, centre_x: float, forehead_y: float, width: float,
                    height: float) -> tuple[np.ndarray, tuple[int, int, int, int]] | None:
    """Median forehead Lab plus its patch. Median, so a specular highlight does not move it."""
    y0 = int(round(forehead_y + SKIN_PATCH_V[0] * height))
    y1 = int(round(forehead_y + SKIN_PATCH_V[1] * height))
    x0 = int(round(centre_x - SKIN_PATCH_U * width))
    x1 = int(round(centre_x + SKIN_PATCH_U * width))
    y0, y1 = max(0, y0), min(lab.shape[0], y1)
    x0, x1 = max(0, x0), min(lab.shape[1], x1)
    patch = lab[y0:y1, x0:x1]
    if patch.size == 0:
        return None
    return np.median(patch.reshape(-1, 3), axis=0), (x0, y0, x1, y1)


def _hairline_profile(lab: np.ndarray, skin: np.ndarray, x0: int, x1: int, forehead_y: float,
                      height: float) -> tuple[np.ndarray, int]:
    """Hairline y for every column in [x0, x1), -1 where that column found no hair.

    Returns (profile, search_top). One vectorised pass over the whole scalp strip: the
    hairline is a curve, and a per-column answer is what lets the colour band follow it.
    """
    top = max(0, int(round(forehead_y - SEARCH_V * height)))
    bottom = min(lab.shape[0], int(round(forehead_y)) + 1)
    if bottom - top < 2 or x1 - x0 < 1:
        return np.full(max(0, x1 - x0), -1, np.int32), top

    # A horizontal box blur stands in for a per-column median window: a strand of hair is
    # wider than the noise, and this is O(1) per pixel where a median is not.
    window = max(3, int(round(0.03 * height)) * 2 + 1)
    smoothed = cv2.blur(lab[top:bottom, x0:x1], (window, 1))
    is_hair = np.linalg.norm(smoothed - skin[None, None, :], axis=2) > SKIN_DISTANCE

    # filter2D anchored at the kernel's first element gives the mean of the `run_needed`
    # rows starting at each row, so a value of 1 marks the top of an unbroken run.
    run_needed = max(3, int(round(HAIR_RUN_V * height)))
    kernel = np.ones((run_needed, 1), np.float32) / float(run_needed)
    runs = cv2.filter2D(is_hair.astype(np.float32), -1, kernel, anchor=(0, 0),
                        borderType=cv2.BORDER_CONSTANT) > 0.999

    rows = np.arange(runs.shape[0], dtype=np.int32)[:, None]
    lowest = np.where(runs, rows, -1).max(axis=0)
    # The hairline is the run's bottom row, which is where the hair meets the forehead.
    return np.where(lowest >= 0, top + lowest + run_needed - 1, -1).astype(np.int32), top


def _background_reference(lab: np.ndarray, centre_x: float, width: float, top: int,
                          bottom: int) -> np.ndarray | None:
    """Median Lab of the margins either side of the head, or None if they are too busy."""
    top, bottom = max(0, top), min(lab.shape[0], bottom)
    left = int(round(centre_x - BACKGROUND_MARGIN_U * width))
    right = int(round(centre_x + BACKGROUND_MARGIN_U * width))
    strips = [lab[top:bottom, :max(0, left)], lab[top:bottom, max(0, right):]]
    pixels = [strip.reshape(-1, 3) for strip in strips if strip.size > 0]
    if not pixels:
        return None
    margin = np.concatenate(pixels, axis=0)
    if len(margin) < MIN_COLOUR_PIXELS or float(margin[:, 0].std()) > BACKGROUND_L_STD:
        return None
    return np.median(margin, axis=0)


def _band_mask(profile: np.ndarray, rows: int, band_height: int) -> np.ndarray:
    """Per-column window of `band_height` pixels sitting directly above each hairline."""
    ys = np.arange(rows, dtype=np.int32)[:, None]
    return ((profile >= 0)[None, :] & (ys < profile[None, :])
            & (ys >= profile[None, :] - band_height))


def _sample_pixels(band: np.ndarray, skin: np.ndarray,
                   background: np.ndarray | None) -> tuple[np.ndarray, np.ndarray, int, float] | None:
    """Trimmed-mean Lab of the hair pixels offered, with their spread and count."""
    if len(band) < 1:
        return None
    keep = np.linalg.norm(band - skin[None, :], axis=1) > SKIN_DISTANCE
    if background is not None:
        # Curls are full of holes, and the wall shows through every one of them.
        keep &= np.linalg.norm(band - background[None, :], axis=1) > BACKGROUND_DISTANCE
    kept = band[keep]
    confidence = float(len(kept)) / float(len(band))
    if len(kept) < MIN_COLOUR_PIXELS:
        return None

    # The interquartile core is hair; the tails are whatever leaked past the two filters,
    # and the specular sheen on top of the head.
    low, high = np.percentile(kept, [25.0, 75.0], axis=0)
    core = kept[np.all((kept >= low) & (kept <= high), axis=1)]
    if len(core) < MIN_COLOUR_PIXELS // 4:
        core = kept
    # Spread of the core, not of everything kept. The tails are scalp showing through a
    # sparse fringe and the sheen on top of the head; both are meant to be thrown away, so
    # counting them would report an unstable estimate every time the hair is short.
    return core.mean(axis=0), core.std(axis=0), int(len(kept)), confidence


def _density_from_rise(rise: float) -> float:
    """Full hair at the forehead vertex is 1.0; a hairline risen to DENSITY_RISE_BALD is 0."""
    span = DENSITY_RISE_BALD - DENSITY_RISE_FULL
    return float(np.clip(1.0 - (rise - DENSITY_RISE_FULL) / span, 0.0, 1.0))


def sample_hair(photo_bgr: np.ndarray, landmarks: FaceLandmarks) -> HairSample:
    """Measure hair colour and density above the face oval.

    Colour is a trimmed mean over a shallow band that sits directly on top of the hairline
    and follows its curve, so it stays inside the head rather than cutting across the
    silhouette; skin- and background-coloured pixels inside the band are then dropped.
    Density comes from how far the hairline has risen off the forehead.
    """
    warnings: list[str] = []
    frame = _head_frame(landmarks)
    if frame is None:
        return HairSample(False, None, None, 0, 0.0, 0.0, 0.0, 0, landmarks.source, warnings=[
            'No dense mesh; hair needs the MediaPipe landmarks to locate the scalp.'])

    centre_x, forehead_y, width, height = frame
    lab = cv2.cvtColor(photo_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    reference = _skin_reference(lab, centre_x, forehead_y, width, height)
    if reference is None:
        return HairSample(False, None, None, 0, 0.0, 0.0, 0.0, 0, landmarks.source, warnings=[
            'Forehead skin patch fell outside the photo; cannot separate hair from skin.'])
    skin, skin_patch = reference

    x0 = max(0, int(round(centre_x - COLOUR_BAND_U * width)))
    x1 = min(lab.shape[1], int(round(centre_x + COLOUR_BAND_U * width)))
    profile, search_top = _hairline_profile(lab, skin, x0, x1, forehead_y, height)

    geometry: dict = {
        'forehead_y': round(forehead_y, 1),
        'face_width': round(width, 1),
        'face_height': round(height, 1),
        'skin_lab': [round(float(v), 2) for v in skin],
        'skin_patch': list(skin_patch),
        'band_x': [x0, x1],
    }

    # Density is read at three columns - centre and both temples, where a hairline recedes
    # first. A column with no hair at all counts as bald rather than being dropped, which
    # is what makes recession register instead of averaging itself away.
    probes = [centre_x - TEMPLE_U * width, centre_x, centre_x + TEMPLE_U * width]
    probe_y: list[int] = []
    for probe_x in probes:
        index = int(round(probe_x)) - x0
        probe_y.append(int(profile[index]) if 0 <= index < len(profile) else -1)
    geometry['columns'] = [[int(round(x)), None if y < 0 else y] for x, y in zip(probes, probe_y)]

    found = [y for y in probe_y if y >= 0]
    density_ratio = float(np.mean([_density_from_rise((forehead_y - y) / height) if y >= 0 else 0.0
                                   for y in probe_y]))

    if not found:
        warnings.append('No hair detected above the forehead; treating this as bald or very short.')
        return HairSample(False, None, None, 0, 0.0, SEARCH_V, 0.0, 0, landmarks.source,
                          measured=True, warnings=warnings, geometry=geometry)

    hairline_y = float(np.median(found))
    rise = (forehead_y - hairline_y) / height
    geometry['hairline_y'] = round(hairline_y, 1)
    if len(found) < len(probes):
        warnings.append(f'Hair found in {len(found)} of {len(probes)} scalp columns; '
                        'hairline is receding or the photo is cropped.')

    band_height = max(2, int(round(COLOUR_BAND_V * height)))
    mask = _band_mask(profile, lab.shape[0], band_height)
    geometry['band_rows'] = [int(max(search_top, profile[profile >= 0].min() - band_height)),
                             int(profile.max())]

    background = _background_reference(lab, centre_x, width, geometry['band_rows'][0],
                                       geometry['band_rows'][1])
    if background is not None:
        geometry['background_lab'] = [round(float(v), 2) for v in background]

    sampled = _sample_pixels(lab[:, x0:x1][mask], skin, background)
    if sampled is None:
        warnings.append('Too little hair visible above the hairline (cropped, or a very short '
                        'crop); keeping the stock hair colour.')
        return HairSample(False, None, None, 0, 0.0, rise, density_ratio, len(found),
                          landmarks.source, measured=True, warnings=warnings, geometry=geometry)

    lab_mean_arr, lab_std_arr, pixels, confidence = sampled
    lab_mean = tuple(float(v) for v in lab_mean_arr)
    lab_std = tuple(float(v) for v in lab_std_arr)

    if lab_std[0] > MIXED_BAND_L_STD:
        warnings.append(f'Hair colour is unstable across the scalp band (L sigma {lab_std[0]:.0f}); '
                        'expect dyed, greying or strongly lit hair to come out approximate.')

    # Subsampled so the profile stays readable in output.json while still drawing the dome.
    step = max(1, len(profile) // 64)
    geometry['hairline_profile'] = [int(v) for v in profile[::step]]
    geometry['profile_step'] = step

    return HairSample(True, lab_mean, lab_std, pixels, confidence, rise, density_ratio,
                      len(found), landmarks.source, measured=True, warnings=warnings,
                      geometry=geometry)


def debug_overlay(photo_bgr: np.ndarray, sample: HairSample) -> np.ndarray:
    """Draw where the hair numbers came from. A bad sample is obvious here and nowhere else."""
    out = photo_bgr.copy()
    geometry = sample.geometry
    if not geometry:
        return out

    thickness = max(1, int(round(geometry.get('face_height', 100) / 150.0)))

    patch = geometry.get('skin_patch')
    if patch:
        cv2.rectangle(out, (patch[0], patch[1]), (patch[2], patch[3]), (0, 200, 255), thickness)

    # The band is drawn as the two curves that bound it, because it follows the hairline
    # rather than being a rectangle: a straight green line here would mean the fix is gone.
    profile = geometry.get('hairline_profile')
    if profile:
        step = geometry.get('profile_step', 1)
        band_x0 = geometry.get('band_x', [0, 0])[0]
        band_height = max(2, int(round(COLOUR_BAND_V * geometry.get('face_height', 0))))
        lower = [(band_x0 + i * step, y) for i, y in enumerate(profile) if y >= 0]
        if len(lower) > 1:
            upper = [(x, y - band_height) for x, y in lower]
            cv2.polylines(out, [np.array(lower, np.int32)], False, (0, 255, 0), thickness)
            cv2.polylines(out, [np.array(upper, np.int32)], False, (0, 255, 0), thickness)

    forehead_y = int(round(geometry.get('forehead_y', 0)))
    for column_x, hairline_y in geometry.get('columns', []):
        top = forehead_y - int(round(SEARCH_V * geometry.get('face_height', 0)))
        cv2.line(out, (column_x, top), (column_x, forehead_y), (255, 160, 0), thickness)
        if hairline_y is not None:
            cv2.circle(out, (column_x, int(round(hairline_y))), thickness * 3, (0, 0, 255), -1)

    if sample.lab is not None:
        # The sampled colour itself, as a swatch, so it can be compared against the photo.
        swatch_lab = np.full((1, 1, 3), sample.lab, np.float32)
        bgr = cv2.cvtColor(swatch_lab.astype(np.uint8), cv2.COLOR_LAB2BGR)[0, 0].tolist()
        side = max(24, out.shape[1] // 12)
        cv2.rectangle(out, (0, 0), (side, side), bgr, -1)
        cv2.rectangle(out, (0, 0), (side, side), (255, 255, 255), thickness)
    return out


def brighten_gain(source_l: float, target_l: float) -> float:
    """Contrast expansion for a mean shift that brightens. 1.0 when darkening or close."""
    if target_l <= source_l + 1.0:
        return 1.0
    return float(np.clip(np.sqrt((target_l + 1.0) / (source_l + 1.0)), 1.0, MAX_CONTRAST_GAIN))


def recolour_hair(texture_bgr: np.ndarray, delta_lab: tuple[float, float, float],
                  gain: float = 1.0) -> np.ndarray:
    """Mean-shift a hair albedo in Lab, expanding L contrast about its own mean by `gain`."""
    lab = cv2.cvtColor(texture_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    mean_l = float(lab[..., 0].mean())
    # Gain about the texture's own mean, so the shared delta still lands where it should and
    # the main/cap brightness relationship the artist authored survives.
    lab[..., 0] = (lab[..., 0] - mean_l) * gain + mean_l + delta_lab[0]
    lab[..., 1] += delta_lab[1]
    lab[..., 2] += delta_lab[2]
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def thin_alpha(alpha_bgr: np.ndarray, strength: float) -> tuple[np.ndarray, int]:
    """Shrink and soften the visible part of a hair alpha map. Returns (map, erode radius)."""
    gray = alpha_bgr if alpha_bgr.ndim == 2 else cv2.cvtColor(alpha_bgr, cv2.COLOR_BGR2GRAY)
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0.0:
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR), 0

    # Gamma first, erosion second. Gamma thins continuously by pulling down the soft strand
    # edges; erosion then removes whole thin cards once the strength is high enough.
    gamma = 1.0 + strength * ALPHA_GAMMA_RANGE
    out = np.power(gray.astype(np.float32) / 255.0, gamma) * 255.0

    radius = int(round(strength * MAX_ERODE_PX * (gray.shape[0] / float(HAIR_TEXTURE_SIZE))))
    if radius >= 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
        out = cv2.erode(out, kernel)
    return cv2.cvtColor(np.clip(out, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR), radius


def _decode(container: 'AvtContainer', name: str) -> np.ndarray:
    return cv2.imdecode(np.frombuffer(container.read_entry(name), np.uint8), cv2.IMREAD_COLOR)


def _encode_into(container: 'AvtContainer', name: str, image: np.ndarray, quality: int) -> bool:
    ok, encoded = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return False
    container.replace_entry(name, encoded.tobytes())
    return True


def compensated_target_l(sampled_l: float, compensation: float) -> float:
    """Albedo lightness to ask for so the *render* lands on `sampled_l`.

    `compensation` is 0 for none - write the sampled colour straight into the albedo - and
    1 to aim for the render instead, dividing by the measured shading factor. Values
    between the two scale linearly, and the result is capped.
    """
    compensation = float(np.clip(compensation, 0.0, 1.0))
    if compensation <= 0.0:
        return float(sampled_l)
    full = sampled_l / RENDER_LIGHTNESS_FACTOR
    return float(min(sampled_l + (full - sampled_l) * compensation, MAX_COMPENSATED_L))


def apply_hair(container: 'AvtContainer', photo_bgr: np.ndarray, landmarks: FaceLandmarks, *,
               mode: str = 'auto', density_override: float | None = None,
               render_compensation: float = 0.0,
               jpeg_quality: int = 95) -> HairReport:
    """Recolour and thin the container's hair textures in place from one frontal photo.

    `mode` is 'auto' (colour and density), 'colour', 'density' or 'none'. Nothing here can
    change hairstyle; a user whose hair is long when the template's is short will still be
    wearing the template's haircut, in their own colour.
    """
    sample = sample_hair(photo_bgr, landmarks)
    warnings = list(sample.warnings)
    changed: list[str] = []

    want_colour = mode in ('auto', 'colour')
    want_density = mode in ('auto', 'density')

    main = _decode(container, HAIR_MAIN_ALBEDO_ENTRY)
    main_lab = cv2.cvtColor(main, cv2.COLOR_BGR2LAB).astype(np.float32)
    source_lab = tuple(float(main_lab[..., c].mean()) for c in range(3))

    delta = (0.0, 0.0, 0.0)
    gain = 1.0
    recoloured = False
    target_l = source_lab[0]
    if want_colour and sample.found and sample.lab is not None:
        # Lightness may be aimed past the sampled colour to survive CLO's shading; a and b
        # are not, because shading darkens hair without changing its hue.
        target_l = compensated_target_l(sample.lab[0], render_compensation)
        delta = (target_l - source_lab[0],
                 sample.lab[1] - source_lab[1],
                 sample.lab[2] - source_lab[2])
        gain = brighten_gain(source_lab[0], target_l)
        # One delta and one gain for both albedos, measured off hair_main. Shifting each to
        # the same mean instead would flatten the cap-under-strands shading to nothing.
        for entry in (HAIR_MAIN_ALBEDO_ENTRY, HAIR_CAP_ALBEDO_ENTRY):
            texture = main if entry == HAIR_MAIN_ALBEDO_ENTRY else _decode(container, entry)
            if _encode_into(container, entry, recolour_hair(texture, delta, gain), jpeg_quality):
                changed.append(entry)
                recoloured = True
    elif want_colour:
        warnings.append('Hair colour left at the stock near-black; see the sample warnings.')

    if density_override is not None:
        strength = float(np.clip(density_override, 0.0, 1.0))
        density_source = 'override'
    elif sample.measured:
        strength = float(np.clip(1.0 - sample.density_ratio, 0.0, 1.0))
        density_source = 'photo'
    else:
        # A sample that never ran reports density 0, which would read as bald and shave the
        # avatar. Leaving the template's hair alone is the only safe reading of "don't know".
        strength = 0.0
        density_source = 'unmeasured'
        if want_density:
            warnings.append('Hair density not measured; left at the template default.')

    thinned = False
    radius = 0
    opacity_before = opacity_after = 0.0
    if want_density:
        alphas = [(entry, _decode(container, entry))
                  for entry in (HAIR_MAIN_ALPHA_ENTRY, HAIR_CAP_ALPHA_ENTRY)]
        opacity_before = float(np.mean([alpha.mean() / 255.0 for _, alpha in alphas]))
        after: list[float] = []
        for entry, alpha in alphas:
            thinned_map, radius = thin_alpha(alpha, strength)
            after.append(thinned_map.mean() / 255.0)
            if strength > 0.0 and _encode_into(container, entry, thinned_map, jpeg_quality):
                changed.append(entry)
                thinned = True
        opacity_after = float(np.mean(after))
        if strength >= 0.9:
            warnings.append('Hair thinned to near-nothing. The cards are still there in the '
                            'geometry, so expect a sparse crop rather than a clean shave.')

    return HairReport(
        mode=mode,
        recoloured=recoloured,
        thinned=thinned,
        delta_lab=delta,
        contrast_gain=gain,
        density_strength=strength,
        density_source=density_source,
        erode_radius_px=radius,
        source_l=source_lab[0],
        target_l=target_l,
        alpha_opacity_before=opacity_before,
        alpha_opacity_after=opacity_after,
        entries_changed=changed,
        sample=sample,
        warnings=warnings,
    )
