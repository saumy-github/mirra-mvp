"""Shrink an exported avatar GLB to something a phone can actually download.

Measured on a finished avatar export: **23.3 MB of the 38 MB file is textures** - 61% - in
26 images, several of them 2048-square PNGs of 1.5 to 2.7 MB each. The mesh is the smaller
half. So the first lever is a texture budget, and it is pure Python; mesh compression
(Draco, meshopt) is the second and needs tooling we do not have in-process.

The budget is per *role*, not per image, because the roles are not equally worth their
pixels:

* **The face albedo is the identity.** It is the one texture a shopper will study, and
  everything upstream in this pipeline exists to get it right, so it keeps the largest
  allowance.
* **Other base colours** - body, arms, legs, hair - read at body distance and survive 1024
  comfortably.
* **Normal, roughness and occlusion maps** are shading detail. At phone size and under a
  garment they survive 512 without anybody noticing.

Format follows need rather than habit: an image that carries opacity stays PNG, because
JPEG has no alpha channel and dropping it would turn the hair back into a helmet. Anything
else becomes JPEG, which is where most of the saving comes from - CLO writes several maps
as PNG that have no reason to be lossless.

    python face_fitting/optimize_glb.py --glb output/<run>/<user>.glb

No CLO required; this works on any glTF.
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

from face_fitting.io.glb_textures import image_payload, load_gltf, repack_buffer

# Default budget, in pixels along the longest edge, by role.
DEFAULT_BUDGET = {
    'face_colour': 2048,
    'base_colour': 1024,
    'data_map': 512,
}

# JPEG quality for images that carry no alpha. 92 rather than 95 because normal and
# roughness maps are the bulk of what gets re-encoded and they are viewed indirectly;
# the face albedo is re-encoded at FACE_JPEG_QUALITY instead.
JPEG_QUALITY = 92
FACE_JPEG_QUALITY = 95
PNG_COMPRESSION = 9

# Materials whose base colour is the face. Matched on name, which CLO sets from the
# template's own material naming.
FACE_MATERIAL_HINTS = ('face',)


@dataclass
class ImagePlan:
    index: int
    role: str
    before_bytes: int
    after_bytes: int = 0
    before_size: tuple[int, int] = (0, 0)
    after_size: tuple[int, int] = (0, 0)
    keeps_alpha: bool = False
    mime: str = ''
    skipped: str = ''

    def as_dict(self) -> dict:
        return {
            'index': self.index, 'role': self.role,
            'before_bytes': self.before_bytes, 'after_bytes': self.after_bytes,
            'before_size': list(self.before_size), 'after_size': list(self.after_size),
            'keeps_alpha': self.keeps_alpha, 'mime': self.mime, 'skipped': self.skipped,
        }


@dataclass
class OptimizeReport:
    source: str
    output: str | None = None
    before_bytes: int = 0
    after_bytes: int = 0
    images: list[ImagePlan] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def saved_fraction(self) -> float:
        return 0.0 if not self.before_bytes else 1.0 - (self.after_bytes / self.before_bytes)

    def as_dict(self) -> dict:
        return {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'source': self.source, 'output': self.output,
            'before_bytes': self.before_bytes, 'after_bytes': self.after_bytes,
            'saved_fraction': round(self.saved_fraction, 4),
            'images': [plan.as_dict() for plan in self.images],
            'warnings': self.warnings,
        }


def classify_images(gltf) -> dict[int, str]:
    """Image index -> role, by walking every material to the slots it uses.

    A role is decided by how an image is *used*, not by its size or name, because CLO
    exports every image unnamed and a 2048 normal map is indistinguishable from a 2048
    albedo by any other means. An image used in more than one slot keeps the most
    demanding role it is given.
    """
    priority = {'face_colour': 3, 'base_colour': 2, 'data_map': 1}
    roles: dict[int, str] = {}

    def claim(index: int | None, role: str) -> None:
        if index is None:
            return
        if index not in roles or priority[role] > priority[roles[index]]:
            roles[index] = role

    for material in gltf.materials or []:
        name = (material.name or '').lower()
        is_face = any(hint in name for hint in FACE_MATERIAL_HINTS)
        pbr = getattr(material, 'pbrMetallicRoughness', None)
        if pbr is not None:
            if pbr.baseColorTexture is not None:
                source = gltf.textures[pbr.baseColorTexture.index].source
                claim(source, 'face_colour' if is_face else 'base_colour')
            if pbr.metallicRoughnessTexture is not None:
                claim(gltf.textures[pbr.metallicRoughnessTexture.index].source, 'data_map')
        for slot in ('normalTexture', 'occlusionTexture', 'emissiveTexture'):
            info = getattr(material, slot, None)
            if info is not None:
                claim(gltf.textures[info.index].source, 'data_map')

    # An image no material references is still in the file and still costs bytes.
    for index in range(len(gltf.images or [])):
        roles.setdefault(index, 'data_map')
    return roles


def _has_alpha(decoded: np.ndarray) -> bool:
    """True when the image carries real transparency, not just a fourth channel."""
    if decoded is None or decoded.ndim != 3 or decoded.shape[2] != 4:
        return False
    return bool((decoded[..., 3] < 250).any())


def shrink_image(payload: bytes, max_edge: int, *, jpeg_quality: int = JPEG_QUALITY
                 ) -> tuple[bytes, str, tuple[int, int], tuple[int, int], bool] | None:
    """Downscale and re-encode one image. Returns None when it is already smaller."""
    decoded = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_UNCHANGED)
    if decoded is None:
        return None
    if decoded.ndim == 2:
        decoded = cv2.cvtColor(decoded, cv2.COLOR_GRAY2BGR)

    before = (decoded.shape[1], decoded.shape[0])
    keeps_alpha = _has_alpha(decoded)
    longest = max(before)
    if longest > max_edge:
        scale = max_edge / float(longest)
        decoded = cv2.resize(decoded, (max(1, int(before[0] * scale)),
                                       max(1, int(before[1] * scale))),
                             interpolation=cv2.INTER_AREA)
    after = (decoded.shape[1], decoded.shape[0])

    if keeps_alpha:
        # PNG is the only alpha-capable format every glTF viewer reads. Dropping the
        # channel here would undo the hair-opacity work entirely.
        ok, encoded = cv2.imencode('.png', decoded, [int(cv2.IMWRITE_PNG_COMPRESSION),
                                                     PNG_COMPRESSION])
        mime = 'image/png'
    else:
        if decoded.ndim == 3 and decoded.shape[2] == 4:
            decoded = cv2.cvtColor(decoded, cv2.COLOR_BGRA2BGR)
        ok, encoded = cv2.imencode('.jpg', decoded, [int(cv2.IMWRITE_JPEG_QUALITY),
                                                     jpeg_quality])
        mime = 'image/jpeg'
    if not ok:
        return None
    return encoded.tobytes(), mime, before, after, keeps_alpha


def optimize(glb_path: Path, out_path: Path, budget: dict[str, int] | None = None,
             log=print) -> OptimizeReport:
    """Apply the texture budget to a GLB and write the result."""
    from face_fitting.io.glb_textures import replace_image

    budget = {**DEFAULT_BUDGET, **(budget or {})}
    glb_path, out_path = Path(glb_path), Path(out_path)
    report = OptimizeReport(source=str(glb_path), before_bytes=glb_path.stat().st_size)

    gltf, _is_binary = load_gltf(glb_path)
    roles = classify_images(gltf)
    new_payloads: dict[int, bytes] = {}

    for index, image in enumerate(gltf.images or []):
        payload = image_payload(gltf, image, glb_path)
        role = roles.get(index, 'data_map')
        if payload is None:
            report.images.append(ImagePlan(index, role, 0, skipped='could not read'))
            continue

        plan = ImagePlan(index, role, len(payload))
        quality = FACE_JPEG_QUALITY if role == 'face_colour' else JPEG_QUALITY
        shrunk = shrink_image(payload, budget[role], jpeg_quality=quality)
        if shrunk is None:
            plan.skipped = 'could not decode'
            report.images.append(plan)
            continue

        new_payload, mime, before, after, keeps_alpha = shrunk
        plan.before_size, plan.after_size = before, after
        plan.keeps_alpha, plan.mime = keeps_alpha, mime
        if len(new_payload) >= len(payload) and before == after:
            # Re-encoding made it bigger and changed nothing. Keep the original rather
            # than spend bytes and a generation of quality for nothing.
            plan.after_bytes = len(payload)
            plan.skipped = 'already smaller'
            report.images.append(plan)
            continue

        new_payloads[index] = new_payload
        image.mimeType = mime
        plan.after_bytes = len(new_payload)
        report.images.append(plan)

    # Rebuild the buffer rather than trusting pygltflib's own conversion, which silently
    # leaves the superseded image data in place. Without this the file gets *bigger*.
    try:
        stats = repack_buffer(gltf, new_payloads)
        log(f'  buffer rebuilt: {stats["bytes_before"] / 1e6:.1f} MB -> '
            f'{stats["bytes_after"] / 1e6:.1f} MB, '
            f'{stats["views_dropped"]} orphaned view(s) dropped')
    except Exception as exc:  # noqa: BLE001 - fall back to a correct but larger file
        report.warnings.append(f'Could not rebuild the buffer ({exc}); writing with the '
                               'images inline, which is valid but larger.')
        for index, payload in new_payloads.items():
            replace_image(gltf, index, payload, gltf.images[index].mimeType or 'image/jpeg')

    gltf.save(str(out_path))
    if not out_path.exists():
        report.warnings.append('Writing the optimised GLB produced no file.')
        return report

    report.output = str(out_path)
    report.after_bytes = out_path.stat().st_size
    return report


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--glb', required=True, help='The GLB to shrink.')
    parser.add_argument('--out', default=None, help="Defaults to <name>_web.glb beside it.")
    parser.add_argument('--face-colour', type=int, default=DEFAULT_BUDGET['face_colour'],
                        help='Max edge for the face albedo, the one texture carrying identity.')
    parser.add_argument('--base-colour', type=int, default=DEFAULT_BUDGET['base_colour'],
                        help='Max edge for every other base colour.')
    parser.add_argument('--data-map', type=int, default=DEFAULT_BUDGET['data_map'],
                        help='Max edge for normal, roughness and occlusion maps.')
    return parser.parse_args()


def _resolve(text: str) -> Path:
    path = Path(text)
    return path if path.is_absolute() else (REPO_ROOT / path)


def main() -> int:
    args = _parse_args()
    glb = _resolve(args.glb)
    if not glb.exists():
        print(f'Error: GLB not found: {glb}')
        return 1
    out = _resolve(args.out) if args.out else glb.with_name(f'{glb.stem}_web.glb')

    budget = {'face_colour': args.face_colour, 'base_colour': args.base_colour,
              'data_map': args.data_map}

    print('\nGLB texture budget')
    print('-' * 72)
    print(f'Source: {glb}  ({glb.stat().st_size / 1e6:.1f} MB)')
    print(f'Budget: face {budget["face_colour"]}  base {budget["base_colour"]}  '
          f'data {budget["data_map"]}\n')

    report = optimize(glb, out, budget)
    if report.output is None:
        for warning in report.warnings:
            print(f'  ! {warning}')
        return 1

    by_role: dict[str, list[ImagePlan]] = {}
    for plan in report.images:
        by_role.setdefault(plan.role, []).append(plan)
    print(f'{"role":<14} {"n":>3} {"before":>9} {"after":>9}  largest change')
    print('-' * 72)
    for role in ('face_colour', 'base_colour', 'data_map'):
        plans = by_role.get(role, [])
        if not plans:
            continue
        before = sum(p.before_bytes for p in plans) / 1e6
        after = sum(p.after_bytes for p in plans) / 1e6
        biggest = max(plans, key=lambda p: p.before_bytes - p.after_bytes)
        change = (f'{biggest.before_size[0]}->{biggest.after_size[0]}px'
                  if biggest.after_size[0] else 'unchanged')
        print(f'{role:<14} {len(plans):>3} {before:>8.2f}M {after:>8.2f}M  {change}')

    alpha_kept = [p for p in report.images if p.keeps_alpha]
    print(f'\n{len(alpha_kept)} image(s) kept as PNG for transparency '
          f'(dropping it would undo the hair opacity pass)')
    print(f'\n{report.before_bytes / 1e6:.1f} MB -> {report.after_bytes / 1e6:.1f} MB '
          f'({report.saved_fraction:.0%} smaller)')
    for warning in report.warnings:
        print(f'  ! {warning}')

    report_path = out.parent / 'glb_optimize.json'
    report_path.write_text(json.dumps(report.as_dict(), indent=2), encoding='utf-8')
    print(f'\nGLB:    {out}')
    print(f'Report: {report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
