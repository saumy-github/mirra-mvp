"""Phase 1a: warp a frontal photo onto the avatar head albedo and write a faced .avt."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_fitting.face_runtime.constants import (BODY_ALBEDO_ENTRIES, HEAD_ALBEDO_ENTRY,
                                                 HEAD_TEXTURE_SIZE)
from face_fitting.face_runtime.landmarks import detect_landmarks, mediapipe_available
from face_fitting.face_runtime.texture_fit import (face_tone_delta, fit_face_to_albedo,
                                                   shift_albedo_tone)
from face_fitting.io.avt_container import read_avt, write_avt

DEFAULT_BASE_AVATAR = 'clo_avatar_generation/input/base-1.avt'
JPEG_QUALITY = 95


def _resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else (REPO_ROOT / path)


def _next_run_dir(user_id: str) -> Path:
    output_root = REPO_ROOT / 'output'
    output_root.mkdir(exist_ok=True)
    existing = sorted(output_root.glob(f'{user_id}-face-*'))
    run_number = len(existing) + 1
    run_dir = output_root / f'{user_id}-face-{run_number:03d}'
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Fit a face photo onto the avatar head texture.')
    parser.add_argument('--photo', required=True, help='Frontal face photo.')
    parser.add_argument('--user-id', default='u_001')
    parser.add_argument('--base-avatar', default=DEFAULT_BASE_AVATAR)
    parser.add_argument('--output-avatar', default=None, help='Defaults to the run directory.')
    parser.add_argument('--texture-size', type=int, default=HEAD_TEXTURE_SIZE,
                        help='Albedo size to write. 4096 doubles face detail; verify CLO accepts it.')
    parser.add_argument('--tone-strength', type=float, default=0.0,
                        help='0 keeps the photo tone, 1 matches the stock head tone for a seamless blend.')
    parser.add_argument('--skin-match', choices=('body', 'face', 'none'), default='body',
                        help="'body' recolours the avatar to the user's skin tone (default); "
                             "'face' bleaches the face to the template instead.")
    parser.add_argument('--no-mediapipe', action='store_true', help='Force the OpenCV fallback.')
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    photo_path = _resolve(args.photo)
    base_path = _resolve(args.base_avatar)
    if not photo_path.exists():
        print(f'Error: photo not found: {photo_path}')
        return 1
    if not base_path.exists():
        print(f'Error: base avatar not found: {base_path}')
        return 1

    print('\nFace Fitting - Phase 1a (texture)')
    print('-' * 50)

    photo = cv2.imdecode(np.fromfile(str(photo_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if photo is None:
        print(f'Error: could not decode photo: {photo_path}')
        return 1
    print(f'Photo:        {photo_path.name}  {photo.shape[1]}x{photo.shape[0]}')

    if not args.no_mediapipe and not mediapipe_available():
        print('Note: MediaPipe model unavailable; falling back to OpenCV landmarks.')

    landmarks = detect_landmarks(photo, prefer_mediapipe=not args.no_mediapipe)
    if landmarks is None:
        print('Error: no face detected in the photo. Use a well-lit, front-facing shot.')
        return 1
    print(f'Landmarks:    {landmarks.source}  interocular={landmarks.interocular:.1f}px')

    container = read_avt(base_path)
    stock = cv2.imdecode(np.frombuffer(container.read_entry(HEAD_ALBEDO_ENTRY), np.uint8),
                         cv2.IMREAD_COLOR)
    if args.texture_size != stock.shape[0]:
        stock = cv2.resize(stock, (args.texture_size, args.texture_size), interpolation=cv2.INTER_CUBIC)
    print(f'Head albedo:  {HEAD_ALBEDO_ENTRY}  {stock.shape[1]}x{stock.shape[0]}')

    composite, weight, report = fit_face_to_albedo(photo, landmarks, stock,
                                                   tone_strength=args.tone_strength)

    skin_delta = (0.0, 0.0, 0.0)
    if args.skin_match == 'body':
        # Move the template's skin to the user's tone instead of bleaching the user's face
        # to the template's. The face keeps its own colour; everything else comes to meet it.
        skin_delta = face_tone_delta(composite, stock, weight)
        composite = shift_albedo_tone(composite, skin_delta, protect=weight)
        for entry in BODY_ALBEDO_ENTRIES:
            body = cv2.imdecode(np.frombuffer(container.read_entry(entry), np.uint8), cv2.IMREAD_COLOR)
            shifted = shift_albedo_tone(body, skin_delta)
            ok_body, body_enc = cv2.imencode('.jpg', shifted, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if ok_body:
                container.replace_entry(entry, body_enc.tobytes())

    run_dir = _next_run_dir(args.user_id)
    ok, encoded = cv2.imencode('.jpg', composite, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
    if not ok:
        print('Error: failed to encode the composited albedo')
        return 1

    container.replace_entry(HEAD_ALBEDO_ENTRY, encoded.tobytes())
    out_avatar = _resolve(args.output_avatar) if args.output_avatar else run_dir / f'{args.user_id}.avt'
    out_avatar.parent.mkdir(parents=True, exist_ok=True)
    write_avt(container, out_avatar)

    cv2.imwrite(str(run_dir / 'composite_albedo.png'), composite)
    cv2.imwrite(str(run_dir / 'composite_weights.png'), (weight * 255).astype(np.uint8))

    summary = {
        'user_id': args.user_id,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'photo': str(photo_path),
        'base_avatar': str(base_path),
        'output_avatar': str(out_avatar),
        'texture_size': args.texture_size,
        'tone_strength': args.tone_strength,
        'skin_match': args.skin_match,
        'skin_delta_lab': [round(v, 2) for v in skin_delta],
        'entries_changed': container.replaced_names(),
        'fit': report.as_dict(),
    }
    (run_dir / 'output.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    print(f'\nWarp mode:    {report.warp_mode}')
    shape = ' '.join(f'{k}={v:.0f}' for k, v in report.similarity_residual_px.items())
    print(f'Shape delta:  {shape}  (how far this face is from the template)')
    print(f'Coverage:     {report.coverage_fraction:.1%} of the UV map')
    print(f'Tone shift:   L={report.tone_shift_lab[0]:.1f} a={report.tone_shift_lab[1]:.1f} b={report.tone_shift_lab[2]:.1f}')
    for warning in report.warnings:
        print(f'  ! {warning}')
    print(f'\nEntries changed: {container.replaced_names()}')
    print(f'Run directory:   {run_dir}')
    print(f'Faced avatar:    {out_avatar}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
