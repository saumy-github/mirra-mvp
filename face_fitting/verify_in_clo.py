"""Prove CLO actually reads the textures the face job patched into a `.avt`.

This closes the open risk under Tier A: every texture result so far has been measured on
our side of the container. Patching bytes into a ZIP is only useful if CLO loads those
bytes rather than a cached copy or a path reference, and that was proven once, for the
face albedo alone - not for the four hair entries and not for the eye.

The test is an A/B rather than an eyeball. For each patched entry we know two reference
colours: the stock template's and the one we wrote. CLO imports the avatar and exports a
GLB; we pull the same texture back out of that GLB and ask which of the two it is closer
to. If it lands on ours, CLO read the embedded entry. If it lands on stock, the patch was
ignored and the whole approach needs rethinking.

    python face_fitting/verify_in_clo.py --avatar output/<run>/<user>.avt

Requires the CLO REST plugin running on localhost:50505 with a licensed CLO3D attached.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clo_avatar_generation.avatar_runtime.client import CLORestClient
from face_fitting.face_runtime.constants import (EYE_ALBEDO_ENTRY, HAIR_CAP_ALBEDO_ENTRY,
                                                 HAIR_CAP_ALPHA_ENTRY, HAIR_MAIN_ALBEDO_ENTRY,
                                                 HAIR_MAIN_ALPHA_ENTRY, HEAD_ALBEDO_ENTRY)
from face_fitting.io.avt_container import read_avt
from face_fitting.io.glb_textures import TextureStats as _TextureStats
from face_fitting.io.glb_textures import assign, fingerprint_distance, gltf_images
from face_fitting.io.glb_textures import decode as _decode_image
from face_fitting.io.glb_textures import stats_for

DEFAULT_BASE_AVATAR = 'clo_avatar_generation/input/base-1.avt'

# The entries Tier A and the face job touch. Order is report order.
VERIFIED_ENTRIES = [
    HEAD_ALBEDO_ENTRY,
    HAIR_MAIN_ALBEDO_ENTRY,
    HAIR_CAP_ALBEDO_ENTRY,
    HAIR_MAIN_ALPHA_ENTRY,
    HAIR_CAP_ALPHA_ENTRY,
    EYE_ALBEDO_ENTRY,
]

# CLO keeps working after a command returns, so the pipeline's own settle delay applies
# here too. See step_07_import_base_avatar.py for the race this avoids.
CLO_SETTLE_SECONDS = 4.0

# Lab distance below which two textures are the same image. JPEG re-encoding on CLO's side
# moves a mean by well under one L*, so this is generous.
SAME_IMAGE_LAB = 2.0
# How much closer to ours than to stock a match has to be before it counts as decided,
# in Lab units. Entries we barely changed cannot be decided either way, and say so.
DECISIVE_MARGIN_LAB = 3.0
# Above this, the best candidate in the export is a different texture entirely, so the
# entry is missing from the export rather than wrong in it. The two are worth separating:
# a patch CLO ignored is a bug in our approach, whereas a texture CLO never exports is a
# limit on what the GLB can deliver, and the fix for each is in a different place.
ABSENT_FINGERPRINT_LAB = 25.0

# Entries whose change is confined to part of the frame, as the sub-rectangle to compare
# over. The iris covers under a tenth of the eye map, so a whole-texture comparison dilutes
# a 10-Lab recolour down into the noise and reports it as undecidable.
REGION_OF_INTEREST = {EYE_ALBEDO_ENTRY: 'iris'}


@dataclass
class EntryVerdict:
    entry: str
    verdict: str
    detail: str
    patched_lab: list[float] | None = None
    stock_lab: list[float] | None = None
    exported_lab: list[float] | None = None
    distance_to_patched: float | None = None
    distance_to_stock: float | None = None
    shape: list[int] | None = None

    def as_dict(self) -> dict:
        return {
            'entry': self.entry,
            'verdict': self.verdict,
            'detail': self.detail,
            'patched_lab': self.patched_lab,
            'stock_lab': self.stock_lab,
            'exported_lab': self.exported_lab,
            'distance_to_patched': self.distance_to_patched,
            'distance_to_stock': self.distance_to_stock,
            'shape': self.shape,
        }


# The texture identification layer lives in `io/glb_textures.py` so that `export_glb.py`,
# which has to find the same images in the same exports, uses one implementation rather
# than a second copy that can drift from this one.
TextureStats = _TextureStats
_decode = _decode_image
_fingerprint_distance = fingerprint_distance
_assign = assign


def _iris_box(size: int) -> tuple[int, int, int, int]:
    """Bounding box of the iris in the eye map, from the measured geometry."""
    from face_fitting.face_runtime.constants import eye_geometry_for_size
    geometry = eye_geometry_for_size(size)
    cx, cy = geometry['centre']
    radius = geometry['limbus_radius']
    return (max(0, int(cx - radius)), max(0, int(cy - radius)),
            min(size, int(cx + radius) + 1), min(size, int(cy + radius) + 1))


def _stats(image: np.ndarray, label: str = '', region: str | None = None,
           payload: bytes | None = None) -> TextureStats:
    """Measure an image, narrowing to the iris rectangle when the region asks for it."""
    crop = _iris_box(image.shape[0]) if (region == 'iris'
                                         and image.shape[0] == image.shape[1]) else None
    stats = stats_for(image, label=label, crop=crop, payload=payload)
    stats.extras['region'] = region or 'full'
    return stats


def _avt_stats(path: Path, entries: list[str]) -> dict[str, TextureStats]:
    container = read_avt(path)
    out: dict[str, TextureStats] = {}
    for name in entries:
        if name not in container.names():
            continue
        payload = container.read_entry(name)
        image = _decode(payload)
        if image is not None:
            # Full frame here: assignment pairs these against full-frame exported images,
            # and a crop on one side only would match the wrong texture. The region is
            # applied to both sides together in `_verdict_for`.
            out[name] = _stats(image, label=name, payload=payload)
    return out


def _lab_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return float(np.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))))


def _in_region(stats: TextureStats, region: str | None) -> TextureStats:
    """Re-measure an exported image over the region its entry cares about."""
    if region is None or stats.payload is None:
        return stats
    image = _decode(stats.payload)
    if image is None:
        return stats
    return _stats(image, label=stats.label, region=region, payload=stats.payload)


def _verdict_for(entry: str, patched: TextureStats, stock: TextureStats | None,
                 match: TextureStats | None) -> EntryVerdict:
    if match is None:
        return EntryVerdict(entry, 'NOT FOUND',
                            f'No {patched.shape[0]}x{patched.shape[1]} image in the export to '
                            'compare against.',
                            patched_lab=[round(v, 2) for v in patched.lab],
                            shape=list(patched.shape))

    # Now that the pairing is settled, narrow all three to the part of the frame this
    # entry's change actually lives in.
    region = REGION_OF_INTEREST.get(entry)
    if region is not None:
        match = _in_region(match, region)
        patched = _in_region(patched, region)
        stock = _in_region(stock, region) if stock is not None else None

    to_patched = _fingerprint_distance(match, patched)
    result = EntryVerdict(
        entry, 'UNKNOWN', '',
        patched_lab=[round(v, 2) for v in patched.lab],
        stock_lab=None if stock is None else [round(v, 2) for v in stock.lab],
        exported_lab=[round(v, 2) for v in match.lab],
        distance_to_patched=round(to_patched, 2),
        shape=list(patched.shape),
    )

    if stock is None:
        result.verdict = 'PATCH READ' if to_patched <= SAME_IMAGE_LAB else 'MISMATCH'
        result.detail = f'{match.label}: Lab distance {to_patched:.2f} from what we wrote.'
        return result

    to_stock = _fingerprint_distance(match, stock)
    result.distance_to_stock = round(to_stock, 2)
    separation = _fingerprint_distance(patched, stock)

    if min(to_patched, to_stock) > ABSENT_FINGERPRINT_LAB:
        result.verdict = 'NOT IN EXPORT'
        result.detail = (f'Nearest candidate {match.label} is {to_patched:.2f} from ours and '
                         f'{to_stock:.2f} from stock, so it is a different texture: CLO does '
                         'not put this entry in the GLB at all. Says nothing about whether '
                         'CLO honours it internally - only that the GLB cannot carry it.')
    elif separation < DECISIVE_MARGIN_LAB:
        result.verdict = 'NOT DECIDABLE'
        result.detail = (f'{match.label}: we barely changed this entry (stock and patched are '
                         f'{separation:.2f} apart), so the export cannot tell them apart.')
    elif to_patched + DECISIVE_MARGIN_LAB < to_stock:
        result.verdict = 'PATCH READ'
        result.detail = (f'{match.label}: {to_patched:.2f} from ours vs {to_stock:.2f} from '
                         'stock. CLO loaded the embedded entry.')
    elif to_stock + DECISIVE_MARGIN_LAB < to_patched:
        result.verdict = 'PATCH IGNORED'
        result.detail = (f'{match.label}: {to_stock:.2f} from stock vs {to_patched:.2f} from '
                         'ours. CLO did not use the patched entry.')
    else:
        result.verdict = 'AMBIGUOUS'
        result.detail = (f'{match.label}: {to_patched:.2f} from ours, {to_stock:.2f} from '
                         'stock. Too close to call.')
    return result


def _export(client: CLORestClient, avatar: Path, out_dir: Path, logger) -> Path | None:
    logger(f'CLO: new project')
    client.wait_for_queue(timeout=30)
    client.new_project()
    client.wait_for_queue(timeout=30)
    time.sleep(CLO_SETTLE_SECONDS)

    logger(f'CLO: importing {avatar.name} ({avatar.stat().st_size / 1e6:.1f} MB)')
    result = client.import_avatar_avt(avatar)
    if not result.get('success', False):
        logger(f'  ! import failed: {result.get("error") or result.get("message") or result}')
        return None
    client.wait_for_queue(timeout=120)
    time.sleep(CLO_SETTLE_SECONDS)

    glb_path = out_dir / f'{avatar.stem}_clo_export.glb'
    logger(f'CLO: exporting GLB')
    export = client.export_avatar_glb(glb_path)
    if not export.get('success', False):
        logger(f'  ! export failed: {export.get("error") or export.get("message") or export}')
        return None
    try:
        client.wait_for_queue(timeout=180)
    except TimeoutError:
        logger('  ! queue drain timed out; checking for the file anyway')

    if not glb_path.exists():
        logger(f'  ! export produced no file at {glb_path}')
        return None
    logger(f'  exported {glb_path.name} ({glb_path.stat().st_size / 1e6:.1f} MB)')
    return glb_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--avatar', required=True, help='The patched .avt to verify.')
    parser.add_argument('--base-avatar', default=DEFAULT_BASE_AVATAR,
                        help='Stock template, used as the other side of the A/B.')
    parser.add_argument('--out-dir', default=None,
                        help="Where to put the export and the report. Defaults to the "
                             "avatar's own directory.")
    parser.add_argument('--clo-url', default='http://localhost:50505')
    return parser.parse_args()


def _resolve(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else (REPO_ROOT / path)


def main() -> int:
    args = _parse_args()
    avatar = _resolve(args.avatar)
    base = _resolve(args.base_avatar)
    if not avatar.exists():
        print(f'Error: avatar not found: {avatar}')
        return 1

    out_dir = _resolve(args.out_dir) if args.out_dir else avatar.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print('\nCLO texture verification')
    print('-' * 68)
    print(f'Avatar:  {avatar}')
    print(f'Stock:   {base}')

    client = CLORestClient(base_url=args.clo_url)
    health = client.health_check()
    if health.get('status') != 'ok':
        print(f'Error: CLO plugin not healthy at {args.clo_url}: {health}')
        return 1
    print(f'CLO:     plugin {health.get("version")} ok\n')

    patched_stats = _avt_stats(avatar, VERIFIED_ENTRIES)
    stock_stats = _avt_stats(base, VERIFIED_ENTRIES) if base.exists() else {}

    glb_path = _export(client, avatar, out_dir, print)
    if glb_path is None:
        print('\nVerification could not run: CLO did not produce an export.')
        return 1

    exported = gltf_images(glb_path)
    print(f'  {len(exported)} images recovered from the export\n')

    assigned = _assign(patched_stats, exported)
    verdicts = [_verdict_for(entry, patched_stats[entry], stock_stats.get(entry),
                             assigned.get(entry))
                for entry in VERIFIED_ENTRIES if entry in patched_stats]

    print(f'{"entry":<38} {"verdict":<15} ours   stock')
    print('-' * 68)
    for item in verdicts:
        ours = '    -' if item.distance_to_patched is None else f'{item.distance_to_patched:5.2f}'
        stock = '    -' if item.distance_to_stock is None else f'{item.distance_to_stock:5.2f}'
        print(f'{item.entry:<38} {item.verdict:<15} {ours}  {stock}')
    print()
    for item in verdicts:
        print(f'  {item.entry}: {item.detail}')

    decided = [v for v in verdicts if v.verdict in ('PATCH READ', 'PATCH IGNORED', 'MISMATCH')]
    read_ok = [v for v in decided if v.verdict == 'PATCH READ']
    ignored = [v for v in decided if v.verdict != 'PATCH READ']
    absent = [v for v in verdicts if v.verdict == 'NOT IN EXPORT']

    report = {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'avatar': str(avatar),
        'base_avatar': str(base),
        'clo_plugin_version': health.get('version'),
        'export': str(glb_path),
        'images_in_export': len(exported),
        'entries': [v.as_dict() for v in verdicts],
        'summary': {
            'decided': len(decided),
            'patch_read': len(read_ok),
            'patch_ignored': len(ignored),
            'not_in_export': len(absent),
        },
    }
    report_path = out_dir / 'clo_verification.json'
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

    print(f'\nDecided {len(decided)} of {len(verdicts)} entries: '
          f'{len(read_ok)} read by CLO, {len(ignored)} ignored.')
    if absent:
        print(f'{len(absent)} entries are absent from the GLB export: '
              + ', '.join(v.entry for v in absent))
    print(f'Report: {report_path}')

    if ignored:
        print('\nCLO ignored at least one patched texture. Tier A rests on it reading them, '
              'so this needs explaining before any more hair work.')
        return 1
    if not decided:
        print('\nNothing was decidable - the patched and stock textures are too alike in this '
              'run. Re-run on an avatar whose textures moved further.')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
