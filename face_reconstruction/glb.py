"""Write the face as a self-contained binary glTF: one textured, alpha-blended mesh.

Root `extras.mirra_face` carries what the web viewer needs to attach it to an
avatar head (see website/frontend .../face-attachment.ts):

    version, noseTip / chin / forehead / eyeCentre (metres, mesh frame),
    widthM, heightM, skinToneHex, scaleSource, views
"""
from __future__ import annotations

import json
import struct

import cv2
import numpy as np

from . import canonical as C
from .reconstruct import FaceReconstruction, _orient_faces, vertex_normals

SCHEMA_VERSION = 1


def _expand_by_uv(vertices: np.ndarray, faces: np.ndarray, face_uvs: np.ndarray, uvs: np.ndarray):
    """glTF needs one UV per vertex; split vertices where the OBJ shares a
    position between different UVs."""
    keys = np.stack([faces.ravel(), face_uvs.ravel()], 1)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    pos = vertices[unique[:, 0]]
    uv = uvs[unique[:, 1]]
    uv = np.stack([uv[:, 0], 1.0 - uv[:, 1]], 1)            # glTF UV origin is top-left
    return pos, uv, inverse.reshape(-1, 3), unique[:, 0]


def to_glb(face: FaceReconstruction) -> bytes:
    canon = C.load()
    faces = _orient_faces(canon.vertices, canon.faces)
    # _orient_faces may swap corners; keep the UV corners in step.
    face_uvs = canon.face_uvs.copy()
    swapped = (faces != canon.faces).any(1)
    face_uvs[swapped] = face_uvs[swapped][:, [0, 2, 1]]

    normals_all = vertex_normals(face.vertices, faces)
    pos, uv, tris, src_index = _expand_by_uv(face.vertices, faces, face_uvs, canon.uvs)
    nrm = normals_all[src_index]

    ok, png = cv2.imencode(".png", cv2.cvtColor(face.texture, cv2.COLOR_RGBA2BGRA))
    if not ok:
        raise RuntimeError("could not encode the face texture")

    blobs = [pos.astype(np.float32).tobytes(), nrm.astype(np.float32).tobytes(),
             uv.astype(np.float32).tobytes(), tris.astype(np.uint32).ravel().tobytes(), png.tobytes()]
    views, offset, binary = [], 0, b""
    for i, blob in enumerate(blobs):
        pad = (-len(binary)) % 4
        binary += b"\0" * pad
        offset = len(binary)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(blob)}
        if i < 3:
            view["target"] = 34962
        elif i == 3:
            view["target"] = 34963
        views.append(view)
        binary += blob
    binary += b"\0" * ((-len(binary)) % 4)

    v = face.vertices
    eye_centre = (v[C.LEFT_EYE_OUTER] + v[C.RIGHT_EYE_OUTER]) / 2
    nose_tip = v[int(np.argmax(v[:, 2]))]
    doc = {
        "asset": {"version": "2.0", "generator": "mirra face_reconstruction"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "mirra_face", "mesh": 0}],
        "meshes": [{"name": "mirra_face", "primitives": [{
            "attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3, "material": 0}]}],
        "materials": [{
            "name": "mirra_face_skin",
            "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}, "metallicFactor": 0.0, "roughnessFactor": 0.62},
            "alphaMode": "BLEND",
        }],
        "textures": [{"source": 0, "sampler": 0}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}],
        "images": [{"bufferView": 4, "mimeType": "image/png"}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(pos), "type": "VEC3",
             "min": pos.min(0).tolist(), "max": pos.max(0).tolist()},
            {"bufferView": 1, "componentType": 5126, "count": len(nrm), "type": "VEC3"},
            {"bufferView": 2, "componentType": 5126, "count": len(uv), "type": "VEC2"},
            {"bufferView": 3, "componentType": 5125, "count": int(tris.size), "type": "SCALAR"},
        ],
        "bufferViews": views,
        "buffers": [{"byteLength": len(binary)}],
        "extras": {"mirra_face": {
            "version": SCHEMA_VERSION,
            "noseTip": nose_tip.tolist(),
            "eyeCentre": eye_centre.tolist(),
            "chin": v[C.CHIN].tolist(),
            "forehead": v[C.FOREHEAD].tolist(),
            "widthM": float(np.linalg.norm(v[C.LEFT_FACE_EDGE] - v[C.RIGHT_FACE_EDGE])),
            "heightM": float(np.linalg.norm(v[C.FOREHEAD] - v[C.CHIN])),
            "skinToneHex": face.skin_tone_hex,
            "scaleSource": face.scale_source,
            "views": face.views,
        }},
    }
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binary), 0x004E4942) + binary
    return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body
