"""Measure the stock head albedo with the same detector used on photos, so conventions match.

The hand-measured anchors in constants.py are pupil centres; MediaPipe's indices are outer eye
corners. Registering a photo against mismatched conventions leaves a systematic error, so the
reference targets are derived here instead of transcribed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_fitting.face_runtime.constants import BASE_TEMPLATE, HEAD_ALBEDO_ENTRY
from face_fitting.face_runtime.landmarks import detect_landmarks
from face_fitting.io.avt_container import read_avt

REFERENCE_DIR = Path(__file__).resolve().parent / 'reference' / BASE_TEMPLATE


def main() -> int:
    parser = argparse.ArgumentParser(description='Derive reference face anchors from the stock albedo.')
    parser.add_argument('--base-avatar', default='clo_avatar_generation/input/base-1.avt')
    args = parser.parse_args()

    base_path = Path(args.base_avatar)
    if not base_path.is_absolute():
        base_path = REPO_ROOT / base_path

    container = read_avt(base_path)
    albedo = cv2.imdecode(np.frombuffer(container.read_entry(HEAD_ALBEDO_ENTRY), np.uint8),
                          cv2.IMREAD_COLOR)
    if albedo is None:
        raise SystemExit(f'Could not decode {HEAD_ALBEDO_ENTRY}')

    landmarks = detect_landmarks(albedo)
    if landmarks is None:
        raise SystemExit('No face detected in the stock albedo')
    if landmarks.dense is None:
        raise SystemExit('Reference calibration needs the dense mesh; install MediaPipe and the model bundle')

    size = albedo.shape[0]
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    np.save(REFERENCE_DIR / 'dense_landmarks.npy', landmarks.dense)

    payload = {
        'template': BASE_TEMPLATE,
        'albedo_entry': HEAD_ALBEDO_ENTRY,
        'texture_size': size,
        'landmark_source': landmarks.source,
        'dense_point_count': int(landmarks.dense.shape[0]),
        'anchors_px': {
            'eye_l': [round(float(v), 2) for v in landmarks.eye_l],
            'eye_r': [round(float(v), 2) for v in landmarks.eye_r],
            'mouth': [round(float(v), 2) for v in landmarks.mouth],
        },
        'interocular_px': round(landmarks.interocular, 2),
    }
    (REFERENCE_DIR / 'anchors.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')

    print(f'Template:     {BASE_TEMPLATE}  ({size}x{size})')
    print(f'Source:       {landmarks.source}')
    print(f'Anchors:      eye_l={payload["anchors_px"]["eye_l"]} '
          f'eye_r={payload["anchors_px"]["eye_r"]} mouth={payload["anchors_px"]["mouth"]}')
    print(f'Interocular:  {landmarks.interocular:.1f}px')
    print(f'Dense mesh:   {landmarks.dense.shape[0]} points')
    print(f'Written to:   {REFERENCE_DIR}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
