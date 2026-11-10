"""Export a faced `.avt` to a self-contained GLB, with hair that is actually see-through.

CLO can export a GLB on its own, and that export already carries the face, body and hair
*colour* we patched in - measured, see
`avatar-personalization-split-decision-26_10_28.md` 1.4. What it does not carry is hair
**opacity**, and without it the avatar is unusable outside CLO:

    CLO's hair materials are alphaMode = BLEND, which is right, but their baseColorTexture
    images are three-channel JPEGs. glTF takes opacity from the base colour's alpha
    channel. BLEND over a texture with no alpha channel is fully opaque, so every strand
    card renders as a solid rectangle and the hair reads as a helmet.

The `.avt` has the missing channel - `hair_main_alpha.jpg` and `hair_cap_alpha.jpg`, the
same maps CLO itself honours on import. This step puts them where glTF expects them: it
finds each hair material's base colour image in the export, composes the matching alpha
map in as a fourth channel, and writes the result back as PNG.

No Blender, no DCC round trip, no hand authoring. The data was already in the container;
only the channel layout was wrong.

    python face_fitting/export_glb.py --avatar output/<run>/<user>.avt

Requires the CLO REST plugin on localhost:50505. Use --from-glb to re-run the alpha fix on
an export you already have, without touching CLO.
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
from face_fitting.face_runtime.constants import (HAIR_CAP_ALBEDO_ENTRY, HAIR_CAP_ALPHA_ENTRY,
                                                 HAIR_MAIN_ALBEDO_ENTRY, HAIR_MAIN_ALPHA_ENTRY)
from face_fitting.io.avt_container import read_avt
from face_fitting.io.glb_textures import (assign, decode, gltf_images, load_gltf,
                                          material_base_colour_image, repack_buffer,
                                          replace_image, stats_for)

# Which alpha map belongs to which albedo. Both pairs share a UV layout, which is why the
# alpha can simply become the albedo's fourth channel.
HAIR_PAIRS = {
    HAIR_MAIN_ALBEDO_ENTRY: HAIR_MAIN_ALPHA_ENTRY,
    HAIR_CAP_ALBEDO_ENTRY: HAIR_CAP_ALPHA_ENTRY,
}

# CLO keeps working after a command returns; the pipeline's own settle delay applies here.
CLO_SETTLE_SECONDS = 4.0
_MIN_GLB_BYTES = 1024

# Mean alpha below this and the hair has been erased rather than made transparent, which
# is worth saying out loud before someone opens the file and sees a bald avatar.
MIN_MEAN_ALPHA = 0.02


@dataclass
class ExportReport:
    avatar: str
    glb: str | None = None
    raw_glb: str | None = None
    hair_materials: int = 0
    images_patched: list[dict] = field(default_factory=list)
    size_bytes: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'avatar': self.avatar, 'glb': self.glb, 'raw_glb': self.raw_glb,
            'hair_materials': self.hair_materials,
            'images_patched': self.images_patched,
            'size_bytes': self.size_bytes, 'warnings': self.warnings,
        }


def export_from_clo(client: CLORestClient, avatar: Path, out_dir: Path, log) -> Path | None:
    log(f'CLO: new project')
    client.wait_for_queue(timeout=30)
    client.new_project()
    client.wait_for_queue(timeout=30)
    time.sleep(CLO_SETTLE_SECONDS)

    log(f'CLO: importing {avatar.name} ({avatar.stat().st_size / 1e6:.1f} MB)')
    result = client.import_avatar_avt(avatar)
    if not result.get('success', False):
        log(f'  ! import failed: {result.get("error") or result.get("message") or result}')
        return None
    client.wait_for_queue(timeout=120)
    time.sleep(CLO_SETTLE_SECONDS)

    raw = out_dir / f'{avatar.stem}_raw.glb'
    log('CLO: exporting GLB')
    export = client.export_avatar_glb(raw)
    if not export.get('success', False):
        log(f'  ! export failed: {export.get("error") or export.get("message") or export}')
        return None
    try:
        client.wait_for_queue(timeout=180)
    except TimeoutError:
        log('  ! queue drain timed out; checking for the file anyway')

    if not raw.exists() or raw.stat().st_size < _MIN_GLB_BYTES:
        log(f'  ! export produced no usable file at {raw}')
        return None
    log(f'  raw export {raw.name} ({raw.stat().st_size / 1e6:.1f} MB)')
    return raw


def _hair_base_colour_indices(gltf) -> dict[int, str]:
    """Base-colour image index -> the material name that uses it, for hair materials only.

    Going through the materials rather than guessing from the images is what makes this
    safe: it patches the textures the hair actually renders with, so a normal or roughness
    map of the same size can never be mistaken for an albedo.
    """
    found: dict[int, str] = {}
    for material in gltf.materials or []:
        name = material.name or ''
        if 'hair' not in name.lower():
            continue
        index = material_base_colour_image(gltf, material)
        if index is not None:
            found.setdefault(index, name)
    return found


def compose_alpha(albedo_bgr: np.ndarray, alpha_map: np.ndarray, *,
                  size: int | None = None) -> bytes:
    """Albedo plus alpha map as one RGBA PNG, the layout glTF reads opacity from.

    PNG because it is the only alpha-capable format every glTF viewer reads - JPEG has no
    alpha channel at all, and WebP needs the `EXT_texture_webp` extension that many
    viewers still skip. It is lossless and therefore large, which `size` exists to offset:
    hair is already the biggest thing in the export.
    """
    gray = alpha_map if alpha_map.ndim == 2 else cv2.cvtColor(alpha_map, cv2.COLOR_BGR2GRAY)
    if size is not None and size != albedo_bgr.shape[0]:
        albedo_bgr = cv2.resize(albedo_bgr, (size, size), interpolation=cv2.INTER_AREA)
    if gray.shape[:2] != albedo_bgr.shape[:2]:
        gray = cv2.resize(gray, (albedo_bgr.shape[1], albedo_bgr.shape[0]),
                          interpolation=cv2.INTER_AREA)
    rgba = cv2.cvtColor(albedo_bgr, cv2.COLOR_BGR2BGRA)
    rgba[..., 3] = gray
    # Maximum compression: this runs once per avatar and every byte ships to a phone.
    ok, payload = cv2.imencode('.png', rgba, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])
    if not ok:
        raise RuntimeError('failed to encode the composed RGBA texture')
    return payload.tobytes()


def patch_hair_alpha(glb_path: Path, avatar: Path, out_path: Path, log,
                     hair_texture_size: int | None = None) -> ExportReport:
    """Put each hair alpha map into its albedo's fourth channel and rewrite the GLB."""
    from pygltflib import ImageFormat

    report = ExportReport(avatar=str(avatar), raw_glb=str(glb_path))
    gltf, _is_binary = load_gltf(glb_path)

    hair_images = _hair_base_colour_indices(gltf)
    report.hair_materials = len(hair_images)
    if not hair_images:
        report.warnings.append('No hair materials found in the export; nothing to patch.')
        log('  ! no hair materials in the export')

    container = read_avt(avatar)
    new_payloads: dict[int, bytes] = {}
    exported = gltf_images(glb_path, gltf)
    # Only the images the hair actually renders with are candidates, so a hair normal map
    # can never win the match against a hair albedo.
    candidates = [image for image in exported if image.index in hair_images]

    targets = {}
    for albedo_entry in HAIR_PAIRS:
        if albedo_entry in container.names():
            decoded = decode(container.read_entry(albedo_entry))
            if decoded is not None:
                targets[albedo_entry] = stats_for(decoded, label=albedo_entry)

    matched = assign(targets, candidates)
    for albedo_entry, alpha_entry in HAIR_PAIRS.items():
        image = matched.get(albedo_entry)
        if image is None:
            report.warnings.append(f'{albedo_entry}: no matching hair image in the export.')
            continue
        if alpha_entry not in container.names():
            report.warnings.append(f'{alpha_entry}: not in the container.')
            continue

        albedo = decode(image.payload)
        alpha_map = decode(container.read_entry(alpha_entry))
        if albedo is None or alpha_map is None:
            report.warnings.append(f'{albedo_entry}: could not decode albedo or alpha.')
            continue

        payload = compose_alpha(albedo, alpha_map, size=hair_texture_size)
        new_payloads[image.index] = payload
        gltf.images[image.index].mimeType = 'image/png'
        mean_alpha = float(cv2.cvtColor(alpha_map, cv2.COLOR_BGR2GRAY).mean() / 255.0)
        if mean_alpha < MIN_MEAN_ALPHA:
            report.warnings.append(
                f'{alpha_entry} is almost entirely transparent (mean {mean_alpha:.3f}); '
                'the hair will be close to invisible.')
        report.images_patched.append({
            'albedo_entry': albedo_entry, 'alpha_entry': alpha_entry,
            'image_index': image.index, 'material': hair_images.get(image.index, ''),
            'mean_alpha': round(mean_alpha, 4), 'bytes': len(payload),
        })
        log(f'  composed {alpha_entry} into image_{image.index} '
            f'({hair_images.get(image.index, "?")}), mean alpha {mean_alpha:.3f}')

    # BLEND is what makes the new alpha channel count; CLO already sets it, but a material
    # left OPAQUE would silently ignore everything above.
    for material in gltf.materials or []:
        if 'hair' in (material.name or '').lower() and material.alphaMode != 'BLEND':
            material.alphaMode = 'BLEND'
            report.warnings.append(f'{material.name}: alphaMode was not BLEND; set it.')

    # Rebuild the buffer rather than trusting pygltflib's own conversion, which leaves the
    # superseded image data behind and makes the file larger instead of smaller.
    try:
        stats = repack_buffer(gltf, new_payloads)
        log(f'buffer rebuilt: {stats["bytes_before"] / 1e6:.1f} MB -> '
            f'{stats["bytes_after"] / 1e6:.1f} MB, '
            f'{stats["views_dropped"]} orphaned view(s) dropped')
    except Exception as exc:  # noqa: BLE001 - a larger file beats no file
        report.warnings.append(f'Could not rebuild the buffer ({exc}); the images are '
                               'written inline, which is valid but larger.')
        for index, payload in new_payloads.items():
            replace_image(gltf, index, payload)
    gltf.save(str(out_path))

    if not out_path.exists():
        report.warnings.append('Writing the patched GLB produced no file.')
        return report
    report.glb = str(out_path)
    report.size_bytes = out_path.stat().st_size
    return report


def verify(glb_path: Path, log) -> bool:
    """Reload the file a viewer would open, and confirm the hair now carries alpha."""
    from pygltflib import GLTF2

    try:
        GLTF2().load_binary(str(glb_path))
    except Exception as exc:  # noqa: BLE001
        log(f'  ! the patched file does not load as binary GLB: {exc}')
        return False

    gltf, _ = load_gltf(glb_path)
    hair_images = _hair_base_colour_indices(gltf)
    ok = True
    for index, material in hair_images.items():
        payload = None
        for image in gltf_images(glb_path, gltf):
            if image.index == index:
                payload = image.payload
                break
        if payload is None:
            log(f'  ! {material}: image_{index} could not be read back')
            ok = False
            continue
        decoded = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_UNCHANGED)
        channels = 0 if decoded is None else (1 if decoded.ndim == 2 else decoded.shape[2])
        if channels == 4:
            coverage = float((decoded[..., 3] > 16).mean())
            log(f'  {material}: image_{index} is RGBA, {coverage:.1%} of it visible')
        else:
            log(f'  ! {material}: image_{index} still has {channels} channels, no opacity')
            ok = False
    return ok


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--avatar', required=True, help='The faced .avt to export.')
    parser.add_argument('--from-glb', default=None,
                        help='Patch this existing export instead of asking CLO for a new one.')
    parser.add_argument('--out-dir', default=None, help="Defaults to the avatar's directory.")
    parser.add_argument('--hair-texture-size', type=int, default=None,
                        help='Downscale the composed hair textures to this square size. '
                             'Hair is the largest thing in the export and its alpha is '
                             'soft, so 1024 usually costs nothing visible.')
    parser.add_argument('--clo-url', default='http://localhost:50505')
    return parser.parse_args()


def _resolve(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else (REPO_ROOT / path)


def main() -> int:
    args = _parse_args()
    avatar = _resolve(args.avatar)
    if not avatar.exists():
        print(f'Error: avatar not found: {avatar}')
        return 1
    out_dir = _resolve(args.out_dir) if args.out_dir else avatar.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print('\nGLB export with hair opacity')
    print('-' * 68)
    print(f'Avatar: {avatar}')

    if args.from_glb:
        raw = _resolve(args.from_glb)
        if not raw.exists():
            print(f'Error: GLB not found: {raw}')
            return 1
        print(f'Reusing export: {raw.name}')
    else:
        client = CLORestClient(base_url=args.clo_url)
        health = client.health_check()
        if health.get('status') != 'ok':
            print(f'Error: CLO plugin not healthy at {args.clo_url}: {health}')
            return 1
        print(f'CLO:    plugin {health.get("version")} ok\n')
        raw = export_from_clo(client, avatar, out_dir, print)
        if raw is None:
            return 1

    out_path = out_dir / f'{avatar.stem}.glb'
    print('\nComposing hair opacity:')
    report = patch_hair_alpha(raw, avatar, out_path, print,
                              hair_texture_size=args.hair_texture_size)

    if report.glb is None:
        print('\nExport failed; see the warnings above.')
        for warning in report.warnings:
            print(f'  ! {warning}')
        return 1

    print('\nVerifying the file a viewer would open:')
    verified = verify(out_path, print)

    (out_dir / 'glb_export.json').write_text(json.dumps(report.as_dict(), indent=2),
                                             encoding='utf-8')
    print(f'\nGLB:    {out_path}  ({report.size_bytes / 1e6:.1f} MB)')
    print(f'Report: {out_dir / "glb_export.json"}')
    for warning in report.warnings:
        print(f'  ! {warning}')
    return 0 if verified else 1


if __name__ == '__main__':
    raise SystemExit(main())
