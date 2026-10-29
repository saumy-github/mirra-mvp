"""Phase 0 diagnostic: write a labelled UV grid onto the head albedo to expose the UV layout.

Open the result in CLO and rotate the avatar. If the left and right sides of the head show
DIFFERENT labels (L* vs R*), the head UV is full and asymmetric faces are representable.
If both sides show the SAME label, the UV is mirrored and the multi-view plan needs rework.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_fitting.face_runtime.constants import (ANCHORS_2048, FACE_BBOX_UV, HEAD_ALBEDO_ENTRY,
                                                 INFORMATIVE_UV)
from face_fitting.io.avt_container import read_avt, write_avt

GRID_DIVISIONS = 10
OVERLAY_ALPHA = 0.55


def _draw_probe(albedo: np.ndarray) -> np.ndarray:
    size = albedo.shape[0]
    overlay = albedo.copy()
    step = size // GRID_DIVISIONS

    for i in range(GRID_DIVISIONS + 1):
        pos = min(i * step, size - 1)
        cv2.line(overlay, (pos, 0), (pos, size - 1), (60, 60, 60), 2)
        cv2.line(overlay, (0, pos), (size - 1, pos), (60, 60, 60), 2)

    # The midline is the mirror axis: labels left of it must differ from labels right of it.
    cv2.line(overlay, (size // 2, 0), (size // 2, size - 1), (0, 255, 255), 6)

    for row in range(GRID_DIVISIONS):
        for col in range(GRID_DIVISIONS):
            cx, cy = col * step + step // 2, row * step + step // 2
            is_left = col < GRID_DIVISIONS // 2
            side = 'L' if is_left else 'R'
            # Mirrored column index, so a mirrored UV shows the same number on both sides
            # and only the L/R letter and colour differ.
            column_id = (GRID_DIVISIONS // 2 - col) if is_left else (col - GRID_DIVISIONS // 2 + 1)
            colour = (0, 0, 235) if is_left else (235, 80, 0)
            label = f'{side}{column_id}{row}'
            cv2.putText(overlay, label, (cx - 58, cy + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.15, (255, 255, 255), 7, cv2.LINE_AA)
            cv2.putText(overlay, label, (cx - 58, cy + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.15, colour, 3, cv2.LINE_AA)

    blended = cv2.addWeighted(overlay, OVERLAY_ALPHA, albedo, 1.0 - OVERLAY_ALPHA, 0)

    def to_px(box):
        return tuple(int(round(v * size)) for v in box)

    fu0, fv0, fu1, fv1 = to_px(FACE_BBOX_UV)
    cv2.rectangle(blended, (fu0, fv0), (fu1, fv1), (0, 255, 0), 5)
    iu0, iv0, iu1, iv1 = to_px(INFORMATIVE_UV)
    cv2.rectangle(blended, (iu0, iv0), (iu1, iv1), (0, 165, 255), 4)

    scale = size / 2048.0
    for name, (x, y) in ANCHORS_2048.items():
        cx, cy = int(round(x * scale)), int(round(y * scale))
        cv2.drawMarker(blended, (cx, cy), (255, 0, 255), cv2.MARKER_CROSS, 46, 6)
        cv2.putText(blended, name, (cx + 22, cy - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 0, 255), 3, cv2.LINE_AA)

    return blended


def main() -> int:
    parser = argparse.ArgumentParser(description='Write a labelled UV-grid probe into a .avt head albedo.')
    parser.add_argument('--base-avatar', default='clo_avatar_generation/input/base-1.avt')
    parser.add_argument('--output', default='clo_avatar_generation/input/base-1-FACETEST.avt')
    parser.add_argument('--dump-texture', default=None, help='Also write the probe albedo as a PNG.')
    args = parser.parse_args()

    base_path = (REPO_ROOT / args.base_avatar) if not Path(args.base_avatar).is_absolute() else Path(args.base_avatar)
    out_path = (REPO_ROOT / args.output) if not Path(args.output).is_absolute() else Path(args.output)

    container = read_avt(base_path)
    albedo = cv2.imdecode(np.frombuffer(container.read_entry(HEAD_ALBEDO_ENTRY), np.uint8),
                          cv2.IMREAD_COLOR)
    if albedo is None:
        raise SystemExit(f'Could not decode {HEAD_ALBEDO_ENTRY} from {base_path}')

    probe = _draw_probe(albedo)
    ok, encoded = cv2.imencode('.jpg', probe, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not ok:
        raise SystemExit('Failed to encode the probe texture')

    container.replace_entry(HEAD_ALBEDO_ENTRY, encoded.tobytes())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_avt(container, out_path)

    if args.dump_texture:
        dump = (REPO_ROOT / args.dump_texture) if not Path(args.dump_texture).is_absolute() else Path(args.dump_texture)
        dump.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(dump), probe)
        print(f'Probe texture: {dump}')

    print(f'Base avatar:   {base_path}  ({base_path.stat().st_size} bytes)')
    print(f'Probe avatar:  {out_path}  ({out_path.stat().st_size} bytes)')
    print(f'Entries changed: {container.replaced_names()}')
    print(f'Texture size: {probe.shape[1]}x{probe.shape[0]}')
    print('\nOpen the probe avatar in CLO and rotate the head:')
    print('  - different labels on left vs right (L* vs R*) -> UV is FULL, plan proceeds')
    print('  - same label on both sides                     -> UV is MIRRORED, plan needs rework')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
