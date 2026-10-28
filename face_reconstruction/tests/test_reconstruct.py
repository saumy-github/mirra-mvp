"""Reconstruction maths on synthetic observations (no MediaPipe run): the
canonical face, posed and projected into an image at a known scale, with
irises of the real anatomical size."""

import json
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from face_reconstruction import canonical as C  # noqa: E402
from face_reconstruction.glb import to_glb  # noqa: E402
from face_reconstruction.landmarks import FaceObservation  # noqa: E402
from face_reconstruction.reconstruct import reconstruct  # noqa: E402

PX_PER_CM = 40.0
SIZE = 1200


def _observation(view="front", yaw_deg=0.0, face_scale=1.0, seed=0) -> FaceObservation:
    """Canonical face scaled by face_scale, turned by yaw, as image-pixel landmarks."""
    v = C.load().vertices * face_scale
    a = np.radians(yaw_deg)
    r = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
    v = v @ r.T
    irises = []
    for outer, inner in ((33, 133), (263, 362)):              # eye corners -> iris centre
        c = (v[outer] + v[inner]) / 2
        rad = C.IRIS_DIAMETER_CM / 2
        irises += [c, c + [rad, 0, 0], c + [0, rad, 0], c - [rad, 0, 0], c - [0, rad, 0]]
    v = np.vstack([v, irises])
    pts = np.stack([v[:, 0] * PX_PER_CM + SIZE / 2, -v[:, 1] * PX_PER_CM + SIZE / 2, -v[:, 2] * PX_PER_CM], 1)
    rng = np.random.default_rng(seed)
    image = rng.integers(90, 200, (SIZE, SIZE, 3), dtype=np.uint8)
    return FaceObservation(view=view, image=image, points=pts)


def _glb_doc(glb: bytes) -> dict:
    n, = struct.unpack_from("<I", glb, 12)
    return json.loads(glb[20:20 + n])


def test_canonical_model_matches_the_face_mesh():
    c = C.load()
    assert c.vertices.shape == (468, 3) and c.faces.shape == (898, 3)
    assert c.faces.max() == 467 and (c.uvs >= 0).all() and (c.uvs <= 1).all()
    assert int(np.argmax(c.vertices[:, 2])) in (1, 4)          # the nose is the most forward point


def test_metric_size_comes_from_the_iris():
    # A face 10% larger than the canonical one: the iris (anatomically fixed)
    # is what tells the reconstruction it is larger.
    face = reconstruct([_observation(face_scale=1.1)])
    width = np.ptp(face.vertices[:, 0]) * 100
    assert face.scale_source == "iris"
    assert width == pytest.approx(np.ptp(C.load().vertices[:, 0]) * 1.1, rel=0.03)


def test_shape_is_recovered_and_side_views_fuse_into_the_same_frame():
    front = _observation()
    left = _observation("left", yaw_deg=35, seed=1)
    face = reconstruct([left, front])                          # order doesn't matter
    assert face.views == ["front", "left"]
    err = np.abs(face.vertices * 100 - C.load().vertices).max()
    assert err < 0.3                                           # cm


def test_texture_is_feathered_to_transparent_at_the_edge():
    face = reconstruct([_observation()])
    alpha = face.texture[..., 3]
    assert alpha.max() == 255 and alpha.min() == 0
    centre = alpha[alpha.shape[0] // 2 - 20: alpha.shape[0] // 2 + 20, alpha.shape[1] // 2 - 20: alpha.shape[1] // 2 + 20]
    assert centre.min() == 255
    assert ((alpha > 0) & (alpha < 255)).sum() > 1000          # a real ramp, not a hard edge


def test_glb_is_well_formed_and_carries_attachment_anchors():
    glb = to_glb(reconstruct([_observation()]))
    assert glb[:4] == b"glTF" and struct.unpack_from("<I", glb, 8)[0] == len(glb)
    doc = _glb_doc(glb)
    assert doc["materials"][0]["alphaMode"] == "BLEND"
    info = doc["extras"]["mirra_face"]
    assert info["version"] == 1 and info["scaleSource"] == "iris"
    assert 0.12 < info["widthM"] < 0.18 and 0.15 < info["heightM"] < 0.22
    assert info["noseTip"][2] > info["forehead"][2]           # nose in front of forehead (+Z out of the face)
    count = doc["accessors"][0]["count"]
    assert doc["accessors"][2]["count"] == count               # one UV per vertex


def test_front_photo_is_required():
    from face_reconstruction.pipeline import reconstruct_face

    with pytest.raises(ValueError, match="front"):
        reconstruct_face({"left": "x.jpg"})
