"""Phase 1a: warp a frontal photo onto the avatar textures and write a faced .avt.

The work itself lives in `face_job.py`, so that this CLI and `worker.tasks.run_face_job`
drive one implementation rather than two. This file is argument parsing and reporting.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_fitting.face_job import FACE_OUTPUT_ROOT, FaceJobOptions, fit_face, next_run_dir
from face_fitting.face_runtime.capture_quality import GRADES
from face_fitting.face_runtime.constants import HEAD_ALBEDO_ENTRY, HEAD_TEXTURE_SIZE
from face_fitting.face_runtime.landmarks import mediapipe_available

DEFAULT_BASE_AVATAR = 'clo_avatar_generation/input/base-1.avt'


def _resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else (REPO_ROOT / path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Fit a face photo onto the avatar textures.')
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
    parser.add_argument('--hair', choices=('auto', 'colour', 'density', 'none'), default='auto',
                        help="'auto' takes hair colour and density from the photo; 'colour' and "
                             "'density' do one each. Hairstyle is geometry and never changes.")
    parser.add_argument('--hair-density', type=float, default=None,
                        help='Override the measured thinning strength, 0 (keep the template hair) '
                             'to 1 (thin it to almost nothing).')
    parser.add_argument('--hair-render-compensation', type=float, default=0.0,
                        help='Aim the hair albedo past the sampled colour so it survives '
                             "CLO's shading, which renders hair at about half its albedo. "
                             '0 writes the sampled colour as-is (default), 1 aims for the '
                             'render. Calibrate with compare_to_photo.py before raising it.')
    parser.add_argument('--eyes', choices=('auto', 'none'), default='auto',
                        help="'auto' takes iris colour from the photo. One 256px texture serves "
                             'both eyes, so there is one colour and no heterochromia.')
    parser.add_argument('--min-capture-grade', choices=GRADES, default=None,
                        help='Refuse photos below this grade instead of only reporting it. '
                             'Input resolution is the ceiling on every later stage, so a '
                             'capture UX should gate here rather than ship a soft avatar.')
    parser.add_argument('--no-mediapipe', action='store_true', help='Force the OpenCV fallback.')
    return parser.parse_args()


def _report_capture(capture) -> None:
    print(f'Capture:      {capture.grade.upper()}  interocular={capture.interocular_px:.0f}px  '
          f'UV scale={capture.uv_upscale:.2f}x')
    for check in capture.checks:
        mark = ' ' if check.passed else '!'
        print(f'  {mark} {check.name:<12} {check.detail}')
    for advice in capture.advice:
        print(f'    -> {advice}')


def _report_fit(report) -> None:
    print()
    print(f'Warp mode:    {report.warp_mode}')
    shape = ' '.join(f'{k}={v:.0f}' for k, v in report.similarity_residual_px.items())
    print(f'Shape delta:  {shape}  (how far this face is from the template)')
    print(f'Coverage:     {report.coverage_fraction:.1%} of the UV map')
    print(f'Tone shift:   L={report.tone_shift_lab[0]:.1f} a={report.tone_shift_lab[1]:.1f} '
          f'b={report.tone_shift_lab[2]:.1f}')
    for warning in report.warnings:
        print(f'  ! {warning}')


def _report_hair(hair) -> None:
    sample = hair.sample
    print()
    print(f'Hair sample:   {"found" if sample.found else "not found"}  '
          f'pixels={sample.pixels}  confidence={sample.confidence:.1%}')
    print(f'Hairline:      rise={sample.hairline_rise:.3f} of face height  '
          f'{sample.columns_with_hair}/3 columns  density={sample.density_ratio:.2f}')
    if hair.recoloured:
        print(f'Hair colour:   L {hair.source_l:.1f} -> {hair.target_l:.1f}  '
              f'delta a={hair.delta_lab[1]:.1f} b={hair.delta_lab[2]:.1f}  '
              f'gain={hair.contrast_gain:.2f}')
    else:
        print('Hair colour:   unchanged (stock near-black)')
    if hair.thinned:
        print(f'Hair density:  strength={hair.density_strength:.2f} ({hair.density_source})  '
              f'erode={hair.erode_radius_px}px  opacity '
              f'{hair.alpha_opacity_before:.3f} -> {hair.alpha_opacity_after:.3f}')
    else:
        print('Hair density:  unchanged')
    for warning in hair.warnings:
        print(f'  ! {warning}')


def _report_eyes(eyes) -> None:
    sample = eyes.sample
    print()
    print(f'Iris sample:   {"found" if sample.found else "not found"}  '
          f'pixels={sample.pixels}  radius={sample.iris_radius_px:.1f}px  '
          f'confidence={sample.confidence:.1%}')
    if eyes.recoloured:
        print(f'Eye colour:    L {eyes.source_l:.1f} -> {eyes.target_l:.1f}  '
              f'delta a={eyes.delta_lab[1]:.1f} b={eyes.delta_lab[2]:.1f}')
    else:
        print('Eye colour:    unchanged (stock brown)')
    for warning in sample.warnings + eyes.warnings:
        print(f'  ! {warning}')


def main() -> int:
    args = _parse_args()

    print()
    print('Face Fitting - Phase 1a (texture)')
    print('-' * 50)

    if not args.no_mediapipe and not mediapipe_available():
        print('Note: MediaPipe model unavailable; falling back to OpenCV landmarks.')

    run_dir = next_run_dir(FACE_OUTPUT_ROOT, args.user_id)
    out_avatar = (_resolve(args.output_avatar) if args.output_avatar
                  else run_dir / f'{args.user_id}.avt')

    options = FaceJobOptions(
        texture_size=args.texture_size,
        tone_strength=args.tone_strength,
        skin_match=args.skin_match,
        hair=args.hair,
        hair_density=args.hair_density,
        hair_render_compensation=args.hair_render_compensation,
        eyes=args.eyes,
        prefer_mediapipe=not args.no_mediapipe,
        min_capture_grade=args.min_capture_grade,
    )
    result = fit_face(_resolve(args.photo), _resolve(args.base_avatar), out_avatar, run_dir,
                      user_id=args.user_id, options=options)

    if result.photo_size:
        print(f'Photo:        {Path(args.photo).name}  '
              f'{result.photo_size[0]}x{result.photo_size[1]}')
    if result.landmarks is not None:
        print(f'Landmarks:    {result.landmarks.source}  '
              f'interocular={result.landmarks.interocular:.1f}px')
    if result.capture is not None:
        _report_capture(result.capture)

    if not result.ok:
        print()
        print(f'Error: {result.reason}')
        # 2 means "the photo was refused", which a caller can act on differently from a
        # crash or a missing file.
        return 2 if result.capture is not None else 1

    print(f'Head albedo:  {HEAD_ALBEDO_ENTRY}  {options.texture_size}x{options.texture_size}')
    _report_fit(result.fit)
    if result.hair is not None:
        _report_hair(result.hair)
    if result.eyes is not None:
        _report_eyes(result.eyes)

    print()
    print(f'Entries changed: {result.summary["entries_changed"]}')
    print(f'Run directory:   {result.run_dir}')
    print(f'Faced avatar:    {result.out_avatar}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
