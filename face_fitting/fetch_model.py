"""Download the MediaPipe face landmarker bundle (not committed - 3.7 MB binary)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

MODEL_URL = ('https://storage.googleapis.com/mediapipe-models/face_landmarker/'
             'face_landmarker/float16/1/face_landmarker.task')
MODEL_PATH = Path(__file__).resolve().parent / 'reference' / 'models' / 'face_landmarker.task'


def main() -> int:
    if MODEL_PATH.exists():
        print(f'Already present: {MODEL_PATH} ({MODEL_PATH.stat().st_size} bytes)')
        return 0
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f'Downloading {MODEL_URL}')
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f'Saved: {MODEL_PATH} ({MODEL_PATH.stat().st_size} bytes)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
