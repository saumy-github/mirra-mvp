"""Read, identify and replace the texture images inside a glTF/GLB file.

Shared by `verify_in_clo.py`, which asks "is the texture CLO exported the one we wrote?",
and `export_glb.py`, which has to find a specific texture in an export and put a modified
version back. Both need the same two things: a way to decode every image a glTF refers to
however it is stored, and a way to say which `.avt` entry each one came from.

Identification is by content, because CLO exports its images unnamed - `image.name` is
None for all 26 of them - so the only way to tell `hair_main` from `hair_cap` is to
compare what they look like. A whole-texture mean is far too coarse for that (every hair
map is 2048 square and dark), so everything here works on a 32x32 Lab thumbnail.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

# Thumbnail edge used for every comparison. Big enough to tell two dark hair maps apart,
# small enough that JPEG noise averages out.
FINGERPRINT_SIZE = 32


@dataclass
class TextureStats:
    """One decoded image, with enough measured about it to identify it later."""
    shape: tuple[int, int]
    lab: tuple[float, float, float]
    fingerprint: np.ndarray
    label: str = ''
    # Index in the glTF `images` array, for images that came from one.
    index: int | None = None
    # The encoded bytes, kept so an image can be re-measured over a sub-region, or
    # rewritten, without holding every decoded 2048 texture in memory.
    payload: bytes | None = None
    extras: dict = field(default_factory=dict)


def decode(payload: bytes) -> np.ndarray | None:
    return cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)


def stats_for(image: np.ndarray, label: str = '', *, crop: tuple[int, int, int, int] | None = None,
              payload: bytes | None = None, index: int | None = None) -> TextureStats:
    """Measure an image, optionally over a sub-rectangle given as (x0, y0, x1, y1).

    The crop exists for changes confined to part of a frame: recolouring an iris moves the
    whole eye map's mean by about one Lab unit, which is indistinguishable from noise, but
    moves the iris rectangle's mean by a great deal.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    source = lab
    if crop is not None:
        x0, y0, x1, y1 = crop
        if x1 > x0 and y1 > y0:
            source = lab[y0:y1, x0:x1]
    thumb = cv2.resize(source, (FINGERPRINT_SIZE, FINGERPRINT_SIZE), interpolation=cv2.INTER_AREA)
    return TextureStats(
        shape=(image.shape[0], image.shape[1]),
        lab=tuple(float(source[..., c].mean()) for c in range(3)),
        fingerprint=thumb.reshape(-1),
        label=label,
        index=index,
        payload=payload,
    )


def fingerprint_distance(a: TextureStats, b: TextureStats) -> float:
    """RMS Lab difference over the thumbnail - the same units as a Lab distance."""
    return float(np.sqrt(np.mean((a.fingerprint - b.fingerprint) ** 2)))


def load_gltf(path: Path):
    """Open a .glb or a JSON .gltf, whichever this file actually is.

    CLO's plugin writes glTF-separate on some versions and binary GLB on others, so the
    magic is checked rather than the extension trusted. See step_12_export_glb.py.
    """
    from pygltflib import GLTF2

    is_binary = Path(path).read_bytes()[:4] == b'glTF'
    return (GLTF2().load_binary(str(path)) if is_binary else GLTF2().load_json(str(path))), is_binary


def image_payload(gltf, image, path: Path) -> bytes | None:
    """The encoded bytes of one glTF image, from a data URI, a sibling file or the buffer."""
    uri = getattr(image, 'uri', None)
    if uri and uri.startswith('data:'):
        return base64.b64decode(uri.split(',', 1)[1])
    if uri:
        sibling = Path(path).parent / uri
        return sibling.read_bytes() if sibling.exists() else None
    if getattr(image, 'bufferView', None) is not None:
        view = gltf.bufferViews[image.bufferView]
        blob = gltf.binary_blob()
        if blob is None:
            return None
        start = view.byteOffset or 0
        return blob[start:start + view.byteLength]
    return None


def gltf_images(path: Path, gltf=None) -> list[TextureStats]:
    """Every image the glTF refers to, decoded and measured, in `images` order."""
    if gltf is None:
        gltf, _ = load_gltf(path)
    out: list[TextureStats] = []
    for index, image in enumerate(gltf.images or []):
        payload = image_payload(gltf, image, path)
        if payload is None:
            continue
        decoded = decode(payload)
        if decoded is None:
            continue
        out.append(stats_for(decoded, label=image.name or f'image_{index}',
                             payload=payload, index=index))
    return out


def assign(targets: dict[str, TextureStats],
           candidates: list[TextureStats]) -> dict[str, TextureStats]:
    """Pair each named target with one candidate image, one-to-one.

    Uniqueness is the point. All four hair textures and both alpha maps are 2048 square,
    so a nearest-match allowed to reuse a candidate will claim the same image for three
    different entries and report every one of them as a match. Greedy over the globally
    best pair, which is enough when the candidates are this distinct.
    """
    pairs = sorted(
        ((fingerprint_distance(stats, candidate), name, index)
         for name, stats in targets.items()
         for index, candidate in enumerate(candidates) if candidate.shape == stats.shape),
        key=lambda item: item[0],
    )
    assigned: dict[str, TextureStats] = {}
    used: set[int] = set()
    for _distance, name, index in pairs:
        if name in assigned or index in used:
            continue
        assigned[name] = candidates[index]
        used.add(index)
    return assigned


def material_base_colour_image(gltf, material) -> int | None:
    """The `images` index behind a material's base colour, or None."""
    pbr = getattr(material, 'pbrMetallicRoughness', None)
    if pbr is None or pbr.baseColorTexture is None:
        return None
    return gltf.textures[pbr.baseColorTexture.index].source


def replace_image(gltf, index: int, payload: bytes, mime_type: str = 'image/png') -> None:
    """Swap one image's content.

    The new bytes go in as a data URI. A caller writing a binary GLB should convert the
    images back to buffer views afterwards, or the images stay base64 inside the JSON
    chunk - valid, but about a third larger than it needs to be.
    """
    image = gltf.images[index]
    image.uri = f'data:{mime_type};base64,' + base64.b64encode(payload).decode('ascii')
    image.mimeType = mime_type
    image.bufferView = None


def repack_buffer(gltf, image_payloads: dict[int, bytes] | None = None) -> dict:
    """Rebuild the binary buffer so nothing orphaned is paid for twice.

    `pygltflib` 1.16.5 cannot put image data into a buffer - `convert_images(BUFFERVIEW)`
    warns and does nothing - so replacing a texture leaves the file carrying *both* the new
    image, base64 in the JSON chunk, and the old one, still sitting in the binary buffer
    behind a buffer view nothing references any more. Measured: shrinking 23.3 MB of
    textures down to 2.7 MB made the file 1.3 MB *larger*.

    This walks what actually references the buffer - accessors, then images - copies only
    those bytes into a fresh blob, and renumbers the views to match. Anything unreferenced
    simply does not get copied.

    `image_payloads` supplies new bytes for the images whose index it names; any other
    image keeps whatever it already had, from its buffer view or its data URI.

    Refuses rather than corrupts when the file uses a feature this does not model: sparse
    accessors, more than one buffer, or a mesh-compression extension that owns its own
    buffer views.
    """
    from pygltflib import BufferView

    image_payloads = image_payloads or {}
    for accessor in gltf.accessors or []:
        if getattr(accessor, 'sparse', None):
            raise ValueError('repack_buffer does not model sparse accessors')
    if len(gltf.buffers or []) > 1:
        raise ValueError('repack_buffer expects a single buffer')
    for extension in (gltf.extensionsUsed or []):
        if 'draco' in extension.lower() or 'meshopt' in extension.lower():
            raise ValueError(f'repack_buffer cannot renumber views owned by {extension}')

    old_blob = gltf.binary_blob() or b''
    old_views = list(gltf.bufferViews or [])
    new_blob = bytearray()
    new_views: list = []
    remap: dict[int, int] = {}

    def _append(data: bytes, byte_stride=None, target=None) -> int:
        # glTF requires 4-byte alignment for buffer view offsets.
        padding = (-len(new_blob)) % 4
        new_blob.extend(b'\x00' * padding)
        offset = len(new_blob)
        new_blob.extend(data)
        new_views.append(BufferView(buffer=0, byteOffset=offset, byteLength=len(data),
                                    byteStride=byte_stride, target=target))
        return len(new_views) - 1

    def _carry(old_index: int) -> int:
        if old_index in remap:
            return remap[old_index]
        view = old_views[old_index]
        start = view.byteOffset or 0
        data = bytes(old_blob[start:start + view.byteLength])
        remap[old_index] = _append(data, view.byteStride, view.target)
        return remap[old_index]

    # Accessors first, so vertex data keeps the front of the buffer and stays contiguous.
    for accessor in gltf.accessors or []:
        if accessor.bufferView is not None:
            accessor.bufferView = _carry(accessor.bufferView)

    for index, image in enumerate(gltf.images or []):
        payload = image_payloads.get(index)
        if payload is None:
            uri = getattr(image, 'uri', None)
            if uri and uri.startswith('data:'):
                payload = base64.b64decode(uri.split(',', 1)[1])
            elif image.bufferView is not None:
                view = old_views[image.bufferView]
                start = view.byteOffset or 0
                payload = bytes(old_blob[start:start + view.byteLength])
        if payload is None:
            continue
        # A fresh view per image: sharing one with an accessor would be legal but makes
        # every later edit a rewrite of the whole buffer.
        image.bufferView = _append(payload)
        image.uri = None

    gltf.bufferViews = new_views
    gltf.set_binary_blob(bytes(new_blob))
    if gltf.buffers:
        gltf.buffers[0].byteLength = len(new_blob)
        gltf.buffers[0].uri = None

    return {
        'views_before': len(old_views),
        'views_after': len(new_views),
        'views_dropped': len(old_views) - len(remap),
        'bytes_before': len(old_blob),
        'bytes_after': len(new_blob),
    }
