"""Score how much a rendered avatar looks like the person in the source photo.

Built because "does it look like them?" was being answered by eye, which cannot tell a
real improvement from a change of camera angle. This measures a CLO screenshot against
the photo it came from and produces a per-attribute breakdown, so the next change to the
pipeline can be judged against a number rather than an impression.

    python face_fitting/compare_to_photo.py --photo face_fitting/input/test2.png \\
        --render path/to/clo_screenshot.png --label "test2 phase 1"

What is and is not honest here matters more than the score, so both are reported:

  * **Shape is comparable.** Both sides go through the same detector, get Procrustes
    aligned - translation, rotation and scale removed - and the residual is expressed in
    units of interocular distance. Resolution affects precision, not bias.
  * **Absolute colour is not comparable.** A CLO render is lit by CLO's studio rig and a
    photo by whatever room it was taken in, so comparing skin L* directly measures the
    lighting as much as the texture. Colour is therefore scored on *relationships that
    survive a lighting change* - hair-to-skin contrast, and hue angle - and the raw
    numbers are printed beside them as context, not as a score.
  * **Anything smaller than a few pixels in the render is not measurable at all** and is
    reported as such rather than scored. At a typical screenshot size the iris is about
    3 px across, which is nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_fitting.face_runtime.hair_fit import sample_hair
from face_fitting.face_runtime.landmarks import FaceLandmarks, detect_landmarks

# MediaPipe mesh vertices for the proportions a person actually recognises. Each is a
# distance, taken as a ratio to interocular distance so it is scale free.
FEATURES: dict[str, tuple[int, int]] = {
    'face width (cheek to cheek)': (234, 454),
    'face height (brow to chin)': (10, 152),
    'jaw width': (172, 397),
    'nose width': (98, 327),
    'nose length': (168, 1),
    'mouth width': (61, 291),
    'left eye width': (33, 133),
    'right eye width': (362, 263),
    'brow to eye': (105, 33),
    'chin to mouth': (152, 17),
}

# Forehead and cheek patches for skin, as fractions of the face box. Kept off the brows,
# the nose specular and the beard line.
SKIN_PATCHES = {
    'forehead': (0.42, 0.10, 0.58, 0.18),
    'left cheek': (0.18, 0.45, 0.32, 0.58),
    'right cheek': (0.68, 0.45, 0.82, 0.58),
}

# A render smaller than this across the eyes cannot support the fine measurements, and the
# report says so instead of scoring noise.
MIN_RENDER_INTEROCULAR = 25.0
# Iris diameter in pixels below which eye colour is not measurable in a render.
MIN_IRIS_PX = 8.0

# A shape residual of this many interocular units scores zero. 0.10 is a tenth of the
# distance between the eyes, which is a different face, not a different photo.
SHAPE_RESIDUAL_ZERO = 0.10
# Ratio error that scores zero for a single proportion: 25% off is unmistakably not them.
FEATURE_ERROR_ZERO = 0.25
# Hue difference in degrees that scores zero.
HUE_ERROR_ZERO = 60.0
# Contrast-ratio error that scores zero, as a fraction.
CONTRAST_ERROR_ZERO = 1.0


@dataclass
class Attribute:
    name: str
    group: str
    photo: float | None
    render: float | None
    score: float | None
    unit: str = ''
    note: str = ''

    def as_dict(self) -> dict:
        return {
            'name': self.name, 'group': self.group,
            'photo': None if self.photo is None else round(self.photo, 4),
            'render': None if self.render is None else round(self.render, 4),
            'score': None if self.score is None else round(self.score, 4),
            'unit': self.unit, 'note': self.note,
        }


@dataclass
class Comparison:
    label: str
    attributes: list[Attribute] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def group_score(self, group: str) -> float | None:
        scored = [a.score for a in self.attributes if a.group == group and a.score is not None]
        return float(np.mean(scored)) if scored else None

    def groups(self) -> list[str]:
        seen: list[str] = []
        for attribute in self.attributes:
            if attribute.group not in seen:
                seen.append(attribute.group)
        return seen


def _imread(path: Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def _score(error: float, zero_at: float) -> float:
    """1.0 at no error, 0.0 at `zero_at`, linear between. Never negative."""
    return float(np.clip(1.0 - error / zero_at, 0.0, 1.0))


def _procrustes_residual(a: np.ndarray, b: np.ndarray) -> float:
    """RMS distance between two meshes after removing translation, rotation and scale.

    Expressed in units of the first mesh's interocular distance, so it answers "how
    differently shaped is this face" rather than "how big is the image".
    """
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    a_centred = a - a.mean(axis=0)
    b_centred = b - b.mean(axis=0)
    a_scale = np.sqrt((a_centred ** 2).sum())
    b_scale = np.sqrt((b_centred ** 2).sum())
    if a_scale == 0 or b_scale == 0:
        return float('inf')
    a_norm = a_centred / a_scale
    b_norm = b_centred / b_scale

    u, _s, vt = np.linalg.svd(b_norm.T @ a_norm)
    rotation = u @ vt
    aligned = b_norm @ rotation

    residual = np.sqrt(((a_norm - aligned) ** 2).sum(axis=1).mean())
    # Back into interocular units: a_norm is a divided by a_scale, and the interocular
    # distance in that same normalised frame is the natural yardstick.
    interocular_norm = np.linalg.norm(a_norm[33] - a_norm[263])
    return float(residual / interocular_norm) if interocular_norm else float('inf')


def _feature_ratios(landmarks: FaceLandmarks) -> dict[str, float]:
    dense = landmarks.dense
    if dense is None:
        return {}
    interocular = landmarks.interocular or 1.0
    out: dict[str, float] = {}
    for name, (i, j) in FEATURES.items():
        if max(i, j) < len(dense):
            out[name] = float(np.linalg.norm(dense[i] - dense[j]) / interocular)
    return out


def _face_box(landmarks: FaceLandmarks) -> tuple[float, float, float, float]:
    dense = landmarks.dense
    if dense is None:
        xs = [landmarks.eye_l[0], landmarks.eye_r[0], landmarks.mouth[0]]
        ys = [landmarks.eye_l[1], landmarks.eye_r[1], landmarks.mouth[1]]
        return (min(xs), min(ys), max(xs), max(ys))
    return (float(dense[:, 0].min()), float(dense[:, 1].min()),
            float(dense[:, 0].max()), float(dense[:, 1].max()))


def _skin_lab(image: np.ndarray, landmarks: FaceLandmarks) -> dict[str, tuple[float, float, float]]:
    x0, y0, x1, y1 = _face_box(landmarks)
    width, height = x1 - x0, y1 - y0
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    out: dict[str, tuple[float, float, float]] = {}
    for name, (u0, v0, u1, v1) in SKIN_PATCHES.items():
        px0, px1 = int(x0 + u0 * width), int(x0 + u1 * width)
        py0, py1 = int(y0 + v0 * height), int(y0 + v1 * height)
        px0, py0 = max(0, px0), max(0, py0)
        px1, py1 = min(image.shape[1], px1), min(image.shape[0], py1)
        if px1 <= px0 or py1 <= py0:
            continue
        patch = lab[py0:py1, px0:px1].reshape(-1, 3)
        # Median, so a specular highlight or a stray hair does not move it.
        out[name] = tuple(float(np.median(patch[:, c])) for c in range(3))
    return out


def _hue_degrees(lab: tuple[float, float, float]) -> float:
    """Hue angle from OpenCV Lab, where a and b are offset by 128."""
    return float(np.degrees(np.arctan2(lab[2] - 128.0, lab[1] - 128.0)) % 360.0)


def _hue_gap(a: float, b: float) -> float:
    gap = abs(a - b) % 360.0
    return min(gap, 360.0 - gap)


def compare(photo: np.ndarray, render: np.ndarray, label: str) -> Comparison:
    result = Comparison(label=label)

    photo_lm = detect_landmarks(photo)
    render_lm = detect_landmarks(render)
    if photo_lm is None or photo_lm.dense is None:
        result.warnings.append('No dense mesh on the source photo; nothing can be compared.')
        return result
    if render_lm is None or render_lm.dense is None:
        result.warnings.append('No face detected in the render; check the crop and framing.')
        return result

    if render_lm.interocular < MIN_RENDER_INTEROCULAR:
        result.warnings.append(
            f'The render is only {render_lm.interocular:.0f}px between the eyes. Shape scores '
            'stay meaningful but fine features are near the detector floor; a larger '
            'screenshot would tighten every number below.')

    # --- shape ------------------------------------------------------------------------
    residual = _procrustes_residual(photo_lm.dense, render_lm.dense)
    result.attributes.append(Attribute(
        'whole-face mesh (Procrustes residual)', 'Shape', 0.0, residual,
        _score(residual, SHAPE_RESIDUAL_ZERO), unit='interocular units',
        note='Translation, rotation and scale removed, so this is shape alone.'))

    photo_ratios, render_ratios = _feature_ratios(photo_lm), _feature_ratios(render_lm)
    for name, photo_value in photo_ratios.items():
        render_value = render_ratios.get(name)
        if render_value is None:
            continue
        error = abs(render_value - photo_value) / photo_value if photo_value else float('inf')
        result.attributes.append(Attribute(
            name, 'Proportions', photo_value, render_value,
            _score(error, FEATURE_ERROR_ZERO), unit='x interocular'))

    # --- colour, on lighting-robust relationships -------------------------------------
    photo_skin = _skin_lab(photo, photo_lm)
    render_skin = _skin_lab(render, render_lm)
    photo_hair = sample_hair(photo, photo_lm)
    render_hair = sample_hair(render, render_lm)

    shared = [name for name in photo_skin if name in render_skin]
    if shared:
        photo_skin_l = float(np.mean([photo_skin[n][0] for n in shared]))
        render_skin_l = float(np.mean([render_skin[n][0] for n in shared]))
        photo_skin_hue = float(np.mean([_hue_degrees(photo_skin[n]) for n in shared]))
        render_skin_hue = float(np.mean([_hue_degrees(render_skin[n]) for n in shared]))

        gap = _hue_gap(photo_skin_hue, render_skin_hue)
        result.attributes.append(Attribute(
            'skin hue', 'Colour', photo_skin_hue, render_skin_hue,
            _score(gap, HUE_ERROR_ZERO), unit='degrees',
            note='Hue survives a lighting change far better than lightness does.'))
        result.attributes.append(Attribute(
            'skin lightness (context only)', 'Context', photo_skin_l, render_skin_l, None,
            unit='L* 0-255', note='Not scored: the render is lit by CLO, the photo by a room.'))

        if photo_hair.found and render_hair.found:
            # Contrast ratio rather than absolute hair L*: a scene that brightens
            # everything moves hair and skin together and leaves this almost unchanged.
            photo_contrast = photo_hair.lab[0] / max(photo_skin_l, 1.0)
            render_contrast = render_hair.lab[0] / max(render_skin_l, 1.0)
            error = abs(render_contrast - photo_contrast) / max(photo_contrast, 1e-6)
            result.attributes.append(Attribute(
                'hair-to-skin contrast', 'Colour', photo_contrast, render_contrast,
                _score(error, CONTRAST_ERROR_ZERO), unit='ratio',
                note='How dark the hair reads against this face, which is what a person sees.'))

            hair_gap = _hue_gap(_hue_degrees(photo_hair.lab), _hue_degrees(render_hair.lab))
            result.attributes.append(Attribute(
                'hair hue', 'Colour', _hue_degrees(photo_hair.lab),
                _hue_degrees(render_hair.lab), _score(hair_gap, HUE_ERROR_ZERO), unit='degrees'))
        else:
            result.warnings.append('Hair could not be sampled on both sides; hair colour unscored.')

    # --- hairline ---------------------------------------------------------------------
    if photo_hair.measured and render_hair.measured:
        error = abs(render_hair.hairline_rise - photo_hair.hairline_rise)
        result.attributes.append(Attribute(
            'hairline height', 'Shape', photo_hair.hairline_rise, render_hair.hairline_rise,
            _score(error, 0.20), unit='fraction of face height',
            note='Template geometry, not something the texture pass can move.'))

    # --- what cannot be measured ------------------------------------------------------
    iris_px = render_lm.interocular * 0.13 * 2.0
    if iris_px < MIN_IRIS_PX:
        result.attributes.append(Attribute(
            'eye colour', 'Not measurable', None, None, None,
            note=f'The iris is about {iris_px:.0f}px across in this render. Needs a close-up '
                 'to judge; the .avt texture was verified separately.'))

    return result


def _bar(score: float | None, width: int = 24) -> str:
    if score is None:
        return '-' * width
    filled = int(round(score * width))
    return '#' * filled + '.' * (width - filled)


def _print_report(result: Comparison) -> None:
    print(f'\nFamiliarity: {result.label}')
    print('=' * 78)
    for group in result.groups():
        group_score = result.group_score(group)
        header = f'{group}' if group_score is None else f'{group}  ({group_score:.0%})'
        print(f'\n{header}')
        print('-' * 78)
        for attribute in result.attributes:
            if attribute.group != group:
                continue
            photo = '    -' if attribute.photo is None else f'{attribute.photo:8.3f}'
            render = '    -' if attribute.render is None else f'{attribute.render:8.3f}'
            score = '  n/a' if attribute.score is None else f'{attribute.score:5.0%}'
            print(f'  {attribute.name:<34} {photo} {render}  {score}  {_bar(attribute.score)}')

    scored = [a.score for a in result.attributes if a.score is not None]
    if scored:
        overall = float(np.mean(scored))
        print('\n' + '=' * 78)
        print(f'  Overall familiarity: {overall:.0%}')
        parts = [f'{group} {result.group_score(group):.0%}'
                 for group in result.groups() if result.group_score(group) is not None]
        if parts:
            print('  ' + ',  '.join(parts))

    for warning in result.warnings:
        print(f'\n  ! {warning}')


def _chart(results: list[Comparison], path: Path) -> None:
    """A plain bar chart of every scored attribute, one column per render compared."""
    names = [a.name for a in results[0].attributes if a.score is not None]
    if not names:
        return
    row_height, label_width, bar_width = 26, 330, 240
    # Wide enough for the percentage printed at the end of each bar to clear the next
    # column, which at a narrower gap it overlapped.
    gap = 56
    width = label_width + len(results) * (bar_width + gap) + 40
    height = 90 + row_height * len(names)
    canvas = np.full((height, width, 3), 253, np.uint8)

    font, scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1
    cv2.putText(canvas, 'Familiarity against the source photo', (20, 34),
                font, 0.62, (20, 20, 20), 2, cv2.LINE_AA)
    for index, result in enumerate(results):
        x = label_width + index * (bar_width + gap)
        cv2.putText(canvas, result.label[:30], (x, 62), font, scale, (90, 90, 90), 1, cv2.LINE_AA)

    for row, name in enumerate(names):
        y = 90 + row * row_height
        cv2.putText(canvas, name[:44], (20, y + 14), font, scale, (40, 40, 40), thickness,
                    cv2.LINE_AA)
        for index, result in enumerate(results):
            match = next((a for a in result.attributes if a.name == name), None)
            if match is None or match.score is None:
                continue
            x = label_width + index * (bar_width + gap)
            cv2.rectangle(canvas, (x, y), (x + bar_width, y + 15), (232, 232, 232), -1)
            # Red below half, amber to 80%, green above: the thresholds the report uses.
            colour = ((70, 70, 215) if match.score < 0.5
                      else (60, 170, 225) if match.score < 0.8 else (90, 170, 70))
            cv2.rectangle(canvas, (x, y), (x + int(bar_width * match.score), y + 15), colour, -1)
            cv2.putText(canvas, f'{match.score:.0%}', (x + bar_width + 4, y + 13),
                        font, 0.38, (60, 60, 60), 1, cv2.LINE_AA)

    cv2.imwrite(str(path), canvas)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--photo', required=True, help='The source photo the avatar was built from.')
    parser.add_argument('--render', required=True, action='append',
                        help='A render of the avatar. Repeat to compare several.')
    parser.add_argument('--label', action='append', default=None,
                        help='Name for each render, in the same order.')
    parser.add_argument('--out-dir', default=None, help='Where to write the report and chart.')
    return parser.parse_args()


def _resolve(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else (REPO_ROOT / path)


def main() -> int:
    args = _parse_args()
    photo_path = _resolve(args.photo)
    photo = _imread(photo_path)
    if photo is None:
        print(f'Error: could not read the photo: {photo_path}')
        return 1

    labels = args.label or []
    results: list[Comparison] = []
    for index, render_text in enumerate(args.render):
        render_path = _resolve(render_text)
        render = _imread(render_path)
        if render is None:
            print(f'Error: could not read the render: {render_path}')
            return 1
        label = labels[index] if index < len(labels) else render_path.stem
        result = compare(photo, render, label)
        _print_report(result)
        results.append(result)

    out_dir = _resolve(args.out_dir) if args.out_dir else photo_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'photo': str(photo_path),
        'comparisons': [
            {
                'label': r.label,
                'overall': (None if not [a for a in r.attributes if a.score is not None]
                            else round(float(np.mean([a.score for a in r.attributes
                                                      if a.score is not None])), 4)),
                'groups': {g: (None if r.group_score(g) is None else round(r.group_score(g), 4))
                           for g in r.groups()},
                'attributes': [a.as_dict() for a in r.attributes],
                'warnings': r.warnings,
            }
            for r in results
        ],
    }
    (out_dir / 'familiarity.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    chart_path = out_dir / 'familiarity.png'
    _chart(results, chart_path)
    print(f'\nReport: {out_dir / "familiarity.json"}')
    print(f'Chart:  {chart_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
