"""The face job as a library call, so the CLI and the worker run the same code.

`run_face_fitting.py` was the only entry point, and it was a `main()` that parsed
arguments, did the work and printed as it went. The worker needs the middle part without
the other two, and a second copy of the middle part would drift from this one within a
week. So the work lives here and both callers drive it.

Deliberately CLO-free. The whole job is texture arithmetic over a ZIP - about 2.3 s on CPU
- which is why it is its own worker task rather than a twelfth step of avatar generation:
a re-shot photo must not trigger a full avatar rebuild, and nothing here can contend for
the single-threaded CLO plugin.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

from face_fitting.face_runtime.capture_quality import CaptureQuality, assess as assess_capture
from face_fitting.face_runtime.constants import (BODY_ALBEDO_ENTRIES, HEAD_ALBEDO_ENTRY,
                                                 HEAD_TEXTURE_SIZE)
from face_fitting.face_runtime.eye_fit import apply_eyes
from face_fitting.face_runtime.eye_fit import debug_overlay as eye_debug_overlay
from face_fitting.face_runtime.hair_fit import apply_hair
from face_fitting.face_runtime.hair_fit import debug_overlay as hair_debug_overlay
from face_fitting.face_runtime.landmarks import detect_landmarks, mediapipe_available
from face_fitting.face_runtime.texture_fit import (face_tone_delta, fit_face_to_albedo,
                                                   shift_albedo_tone)
from face_fitting.io.avt_container import read_avt, write_avt

JPEG_QUALITY = 95

# Face runs live under the package that produces them, like every other pipeline in this
# repo (`clo_avatar_generation/output`, `clo_vto/output`, `product_ingestion/output`).
# They used to land in a shared tree at the repo root, which mixed them in with Step 1's
# runs and put ~31 MB per run where it was easy to commit by accident.
FACE_OUTPUT_ROOT = Path(__file__).resolve().parent / 'output'


@dataclass
class FaceJobOptions:
    texture_size: int = HEAD_TEXTURE_SIZE
    tone_strength: float = 0.0
    skin_match: str = 'body'
    hair: str = 'auto'
    hair_density: float | None = None
    hair_render_compensation: float = 0.0
    eyes: str = 'auto'
    prefer_mediapipe: bool = True
    # When set, a photo graded below this is refused outright instead of being processed
    # into a soft avatar nobody will recognise.
    min_capture_grade: str | None = None
    jpeg_quality: int = JPEG_QUALITY
    # Debug overlays cost a few hundred KB per run and are the only way to diagnose a bad
    # sample after the fact. The worker turns them off for ordinary production runs.
    write_diagnostics: bool = True


@dataclass
class FaceJobResult:
    ok: bool
    reason: str = ''
    out_avatar: Path | None = None
    run_dir: Path | None = None
    capture: CaptureQuality | None = None
    summary: dict = field(default_factory=dict)
    # Kept so a caller can report on them without re-reading output.json.
    fit: object | None = None
    hair: object | None = None
    eyes: object | None = None
    landmarks: object | None = None
    photo_size: tuple[int, int] | None = None

    @property
    def quality_score(self) -> float | None:
        """A single 0-1 number for the avatar profile doc.

        Deliberately the capture grade rather than anything measured off the output: the
        pipeline is deterministic, so how good the result is is decided almost entirely by
        how good the photo was. Scoring the output would mostly re-measure the input.
        """
        if self.capture is None:
            return None
        from face_fitting.face_runtime.capture_quality import GRADES
        return round(GRADES.index(self.capture.grade) / (len(GRADES) - 1), 3)


def _imread(path: Path) -> np.ndarray | None:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def fit_face(photo_path: Path, base_avatar: Path, out_avatar: Path, run_dir: Path, *,
             user_id: str = 'u_001',
             options: FaceJobOptions | None = None) -> FaceJobResult:
    """Write a faced `.avt` from one frontal photo. Returns rather than raising.

    Every failure is a `FaceJobResult` with `ok=False` and a reason fit to show a user,
    because the callers are a CLI that prints it and a worker that stores it.
    """
    options = options or FaceJobOptions()
    photo_path, base_avatar = Path(photo_path), Path(base_avatar)
    out_avatar, run_dir = Path(out_avatar), Path(run_dir)

    if not photo_path.exists():
        return FaceJobResult(False, f'Photo not found: {photo_path}')
    if not base_avatar.exists():
        return FaceJobResult(False, f'Base avatar not found: {base_avatar}')

    photo = _imread(photo_path)
    if photo is None:
        return FaceJobResult(False, f'Could not decode the photo: {photo_path}')

    landmarks = detect_landmarks(photo, prefer_mediapipe=options.prefer_mediapipe)
    if landmarks is None:
        return FaceJobResult(
            False, 'No face detected in the photo. Use a well-lit, front-facing shot.',
            photo_size=(photo.shape[1], photo.shape[0]))

    capture = assess_capture(photo, landmarks)
    result = FaceJobResult(True, capture=capture, landmarks=landmarks,
                           photo_size=(photo.shape[1], photo.shape[0]))
    if options.min_capture_grade and not capture.meets(options.min_capture_grade):
        result.ok = False
        result.reason = (f'Capture grade {capture.grade!r} is below the required '
                         f'{options.min_capture_grade!r}. ' + ' '.join(capture.advice))
        return result

    container = read_avt(base_avatar)
    stock = cv2.imdecode(np.frombuffer(container.read_entry(HEAD_ALBEDO_ENTRY), np.uint8),
                         cv2.IMREAD_COLOR)
    if options.texture_size != stock.shape[0]:
        stock = cv2.resize(stock, (options.texture_size, options.texture_size),
                           interpolation=cv2.INTER_CUBIC)

    composite, weight, report = fit_face_to_albedo(photo, landmarks, stock,
                                                   tone_strength=options.tone_strength)

    skin_delta = (0.0, 0.0, 0.0)
    if options.skin_match == 'body':
        # Move the template's skin to the user's tone rather than bleaching the user's face
        # to the template's. The face keeps its colour; everything else comes to meet it.
        skin_delta = face_tone_delta(composite, stock, weight)
        composite = shift_albedo_tone(composite, skin_delta, protect=weight)
        for entry in BODY_ALBEDO_ENTRIES:
            body = cv2.imdecode(np.frombuffer(container.read_entry(entry), np.uint8),
                                cv2.IMREAD_COLOR)
            shifted = shift_albedo_tone(body, skin_delta)
            ok_body, body_enc = cv2.imencode('.jpg', shifted,
                                             [int(cv2.IMWRITE_JPEG_QUALITY), options.jpeg_quality])
            if ok_body:
                container.replace_entry(entry, body_enc.tobytes())

    hair = None
    if options.hair != 'none':
        # Off the photo, not the composite: hair colour lives above the face oval, which
        # never makes it into the head albedo.
        hair = apply_hair(container, photo, landmarks, mode=options.hair,
                          density_override=options.hair_density,
                          render_compensation=options.hair_render_compensation,
                          jpeg_quality=options.jpeg_quality)

    eyes = None
    if options.eyes != 'none':
        eyes = apply_eyes(container, photo, landmarks, jpeg_quality=options.jpeg_quality)

    ok, encoded = cv2.imencode('.jpg', composite,
                               [int(cv2.IMWRITE_JPEG_QUALITY), options.jpeg_quality])
    if not ok:
        result.ok = False
        result.reason = 'Failed to encode the composited head albedo.'
        return result

    container.replace_entry(HEAD_ALBEDO_ENTRY, encoded.tobytes())
    run_dir.mkdir(parents=True, exist_ok=True)
    out_avatar.parent.mkdir(parents=True, exist_ok=True)
    write_avt(container, out_avatar)

    if options.write_diagnostics:
        cv2.imwrite(str(run_dir / 'composite_albedo.png'), composite)
        cv2.imwrite(str(run_dir / 'composite_weights.png'), (weight * 255).astype(np.uint8))
        if hair is not None:
            cv2.imwrite(str(run_dir / 'hair_sample.png'), hair_debug_overlay(photo, hair.sample))
        if eyes is not None:
            cv2.imwrite(str(run_dir / 'eye_sample.png'), eye_debug_overlay(photo, eyes.sample))

    summary = {
        'user_id': user_id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'photo': str(photo_path),
        'base_avatar': str(base_avatar),
        'output_avatar': str(out_avatar),
        'texture_size': options.texture_size,
        'tone_strength': options.tone_strength,
        'skin_match': options.skin_match,
        'skin_delta_lab': [round(v, 2) for v in skin_delta],
        'capture': capture.as_dict(),
        'entries_changed': container.replaced_names(),
        'fit': report.as_dict(),
        'hair': None if hair is None else hair.as_dict(),
        'eyes': None if eyes is None else eyes.as_dict(),
    }
    (run_dir / 'output.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    result.out_avatar = out_avatar
    result.run_dir = run_dir
    result.summary = summary
    result.fit = report
    result.hair = hair
    result.eyes = eyes
    return result


def next_run_dir(output_root: Path, user_id: str) -> Path:
    """`<output_root>/<user_id>-face-<NNN>`, numbered after the existing runs."""
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    existing = sorted(output_root.glob(f'{user_id}-face-*'))
    run_dir = output_root / f'{user_id}-face-{len(existing) + 1:03d}'
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def mediapipe_ready() -> bool:
    return mediapipe_available()


FACED_AVATAR_NAME = 'faced.avt'
FACE_MANIFEST_NAME = 'face_manifest.json'


def run_for_version_dir(user_id: str, photo_path: Path, avatar_avt: Path, *,
                        options: FaceJobOptions | None = None) -> FaceJobResult:
    """Personalise an avatar in place beside itself, for the live worker.

    The faced avatar is written into the **same version folder** as the avatar it was built
    from, not into a run tree of its own. That keeps the two together: a user's version 003
    body and the face fitted to it are the same artifact, and rolling the version back rolls
    the face back with it. `face_manifest.json` records what was done, next to the
    `run_manifest.json` the avatar job already writes there.
    """
    avatar_avt = Path(avatar_avt)
    version_dir = avatar_avt.parent
    result = fit_face(Path(photo_path), avatar_avt, version_dir / FACED_AVATAR_NAME,
                      version_dir, user_id=user_id, options=options)

    manifest = {
        'user_id': user_id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'ok': result.ok,
        'reason': result.reason,
        'photo': str(photo_path),
        'source_avatar': str(avatar_avt),
        'faced_avatar': None if result.out_avatar is None else str(result.out_avatar),
        'quality_score': result.quality_score,
        'capture': None if result.capture is None else result.capture.as_dict(),
        'entries_changed': result.summary.get('entries_changed', []),
        'hair': result.summary.get('hair'),
        'eyes': result.summary.get('eyes'),
    }
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / FACE_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2),
                                                  encoding='utf-8')
    return result
