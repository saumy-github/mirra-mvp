"""Phase 4: the texture budget, and the buffer rebuild that makes it actually save bytes.

The trap this module exists around: `pygltflib` 1.16.5 cannot write image data into a
buffer. `convert_images(BUFFERVIEW)` warns and does nothing, so a replaced texture ends up
base64 in the JSON chunk while the *old* one stays in the binary buffer behind a view
nothing references. Measured on a real export, shrinking 23.3 MB of textures to 2.7 MB made
the file 1.3 MB larger. `repack_buffer` is the fix, and most of these tests guard it.
"""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from face_fitting.io.glb_textures import repack_buffer
from face_fitting.optimize_glb import (DEFAULT_BUDGET, classify_images, optimize,
                                       shrink_image)

pygltflib = pytest.importorskip('pygltflib')


def _encode(image: np.ndarray, ext: str = '.png') -> bytes:
    ok, payload = cv2.imencode(ext, image)
    assert ok
    return payload.tobytes()


def _noise(size: int, seed: int = 0, channels: int = 3) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(128, 40, (size, size, channels)), 0, 255).astype(np.uint8)


def _tiny_gltf(images: list[bytes], vertex_bytes: bytes = b'\x00' * 48):
    """A minimal but structurally real GLB: one accessor over a buffer, plus images."""
    from pygltflib import (GLTF2, Accessor, Buffer, BufferView, Image, Material,
                           PbrMetallicRoughness, Texture, TextureInfo)

    blob = bytearray(vertex_bytes)
    views = [BufferView(buffer=0, byteOffset=0, byteLength=len(vertex_bytes))]
    gltf_images, textures = [], []
    for payload in images:
        padding = (-len(blob)) % 4
        blob.extend(b'\x00' * padding)
        views.append(BufferView(buffer=0, byteOffset=len(blob), byteLength=len(payload)))
        blob.extend(payload)
        gltf_images.append(Image(bufferView=len(views) - 1, mimeType='image/png'))
        textures.append(Texture(source=len(gltf_images) - 1))

    gltf = GLTF2()
    gltf.buffers = [Buffer(byteLength=len(blob))]
    gltf.bufferViews = views
    gltf.accessors = [Accessor(bufferView=0, componentType=5126, count=4, type='VEC3')]
    gltf.images = gltf_images
    gltf.textures = textures
    gltf.materials = [
        Material(name='face_1',
                 pbrMetallicRoughness=PbrMetallicRoughness(
                     baseColorTexture=TextureInfo(index=0) if textures else None))
    ]
    gltf.set_binary_blob(bytes(blob))
    return gltf


# --- shrinking one image ----------------------------------------------------------------

def test_an_oversized_image_is_downscaled():
    out = shrink_image(_encode(_noise(1024)), 256)
    assert out is not None
    _payload, _mime, before, after, _alpha = out
    assert before == (1024, 1024) and after == (256, 256)


def test_an_image_already_within_budget_keeps_its_size():
    out = shrink_image(_encode(_noise(128)), 512)
    _payload, _mime, before, after, _alpha = out
    assert before == after == (128, 128)


def test_an_opaque_image_becomes_jpeg():
    """Where most of the saving comes from: CLO writes maps as PNG that need not be."""
    _payload, mime, _b, _a, alpha = shrink_image(_encode(_noise(512)), 512)
    assert mime == 'image/jpeg' and alpha is False


def test_a_transparent_image_stays_png():
    rgba = np.dstack([_noise(256), np.full((256, 256), 100, np.uint8)])
    _payload, mime, _b, _a, alpha = shrink_image(_encode(rgba), 256)
    assert mime == 'image/png' and alpha is True


def test_a_fully_opaque_alpha_channel_is_not_treated_as_transparency():
    """A fourth channel of solid 255 carries nothing and should not force PNG."""
    rgba = np.dstack([_noise(256), np.full((256, 256), 255, np.uint8)])
    _payload, mime, _b, _a, alpha = shrink_image(_encode(rgba), 256)
    assert mime == 'image/jpeg' and alpha is False


def test_transparency_survives_the_downscale():
    alpha = np.zeros((512, 512), np.uint8)
    alpha[128:384, 128:384] = 255
    rgba = np.dstack([_noise(512), alpha])
    payload, _mime, _b, _a, keeps = shrink_image(_encode(rgba), 128)
    assert keeps
    decoded = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_UNCHANGED)
    assert decoded.shape[2] == 4
    assert decoded[..., 3].min() == 0 and decoded[..., 3].max() == 255


def test_an_undecodable_payload_is_refused_not_raised():
    assert shrink_image(b'not an image', 256) is None


def test_a_greyscale_image_is_handled():
    grey = np.full((256, 256), 120, np.uint8)
    assert shrink_image(_encode(grey), 128) is not None


# --- role classification -----------------------------------------------------------------

def test_the_face_base_colour_gets_its_own_role():
    gltf = _tiny_gltf([_encode(_noise(64))])
    assert classify_images(gltf)[0] == 'face_colour'


def test_a_non_face_base_colour_is_an_ordinary_base_colour():
    gltf = _tiny_gltf([_encode(_noise(64))])
    gltf.materials[0].name = 'body2_1'
    assert classify_images(gltf)[0] == 'base_colour'


def test_a_normal_map_is_a_data_map():
    from pygltflib import NormalMaterialTexture
    gltf = _tiny_gltf([_encode(_noise(64)), _encode(_noise(64), '.png')])
    gltf.materials[0].normalTexture = NormalMaterialTexture(index=1)
    roles = classify_images(gltf)
    assert roles[0] == 'face_colour' and roles[1] == 'data_map'


def test_an_image_used_in_two_slots_keeps_the_more_demanding_role():
    """Downscaling a shared image to the data-map budget would blur the face with it."""
    from pygltflib import NormalMaterialTexture
    gltf = _tiny_gltf([_encode(_noise(64))])
    gltf.materials[0].normalTexture = NormalMaterialTexture(index=0)
    assert classify_images(gltf)[0] == 'face_colour'


def test_an_unreferenced_image_still_gets_a_role():
    """It costs bytes whether or not a material points at it."""
    gltf = _tiny_gltf([_encode(_noise(64)), _encode(_noise(64))])
    gltf.materials[0].pbrMetallicRoughness.baseColorTexture = None
    assert set(classify_images(gltf)) == {0, 1}


def test_the_default_budget_favours_the_face():
    assert DEFAULT_BUDGET['face_colour'] > DEFAULT_BUDGET['base_colour']
    assert DEFAULT_BUDGET['base_colour'] > DEFAULT_BUDGET['data_map']


# --- repacking the buffer ------------------------------------------------------------------

def test_repacking_drops_orphaned_image_views():
    gltf = _tiny_gltf([_encode(_noise(256)), _encode(_noise(256))])
    stats = repack_buffer(gltf, {0: b'tiny', 1: b'also tiny'})
    assert stats['bytes_after'] < stats['bytes_before']
    assert len(gltf.bufferViews) == 3  # one accessor view plus one per image


def test_repacking_keeps_accessor_data_intact():
    payload = bytes(range(48))
    gltf = _tiny_gltf([_encode(_noise(64))], vertex_bytes=payload)
    repack_buffer(gltf, {0: b'small'})

    view = gltf.bufferViews[gltf.accessors[0].bufferView]
    blob = gltf.binary_blob()
    start = view.byteOffset or 0
    assert blob[start:start + view.byteLength] == payload


def test_repacking_moves_images_out_of_data_uris():
    gltf = _tiny_gltf([_encode(_noise(64))])
    repack_buffer(gltf, {0: b'new bytes'})
    assert gltf.images[0].uri is None
    assert gltf.images[0].bufferView is not None


def test_repacking_keeps_an_image_it_was_given_no_replacement_for():
    original = _encode(_noise(32))
    gltf = _tiny_gltf([original])
    repack_buffer(gltf, {})
    view = gltf.bufferViews[gltf.images[0].bufferView]
    blob = gltf.binary_blob()
    start = view.byteOffset or 0
    assert blob[start:start + view.byteLength] == original


def test_every_view_offset_stays_four_byte_aligned():
    gltf = _tiny_gltf([_encode(_noise(32)), _encode(_noise(32))])
    repack_buffer(gltf, {0: b'a', 1: b'bcd'})
    for view in gltf.bufferViews:
        assert (view.byteOffset or 0) % 4 == 0


def test_the_buffer_length_is_updated():
    gltf = _tiny_gltf([_encode(_noise(128))])
    repack_buffer(gltf, {0: b'x'})
    assert gltf.buffers[0].byteLength == len(gltf.binary_blob())


def test_repacking_refuses_a_file_it_cannot_model():
    """Better to write a larger correct file than a smaller corrupt one."""
    gltf = _tiny_gltf([_encode(_noise(32))])
    gltf.extensionsUsed = ['KHR_draco_mesh_compression']
    with pytest.raises(ValueError, match='draco'):
        repack_buffer(gltf, {})


def test_repacking_refuses_multiple_buffers():
    from pygltflib import Buffer
    gltf = _tiny_gltf([_encode(_noise(32))])
    gltf.buffers.append(Buffer(byteLength=4))
    with pytest.raises(ValueError, match='single buffer'):
        repack_buffer(gltf, {})


# --- the whole pass -------------------------------------------------------------------------

def test_optimizing_shrinks_a_file_and_keeps_it_loadable(tmp_path):
    from pygltflib import GLTF2
    source = tmp_path / 'in.glb'
    _tiny_gltf([_encode(_noise(1024, seed=i)) for i in range(3)]).save(str(source))

    out = tmp_path / 'out.glb'
    report = optimize(source, out, log=lambda _m: None)

    assert report.output is not None
    assert report.after_bytes < report.before_bytes
    assert report.saved_fraction > 0.5
    GLTF2().load_binary(str(out))


def test_optimizing_reports_every_image(tmp_path):
    source = tmp_path / 'in.glb'
    _tiny_gltf([_encode(_noise(512, seed=i)) for i in range(2)]).save(str(source))
    report = optimize(source, tmp_path / 'out.glb', log=lambda _m: None)
    assert len(report.images) == 2
    assert all(plan.role in DEFAULT_BUDGET for plan in report.images)
