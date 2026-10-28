"""MediaPipe's canonical face model: 468 vertices (one per face-mesh landmark, same
order), 898 triangles and a UV layout. Units are centimetres, +Y up, +Z out of
the face (towards the viewer). Bundled in data/ (Apache-2.0, see data/NOTICE)."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

OBJ_PATH = Path(__file__).resolve().parent / "data" / "canonical_face_model.obj"

# Landmark indices used across the package.
NOSE_TIP = 1
FOREHEAD = 10
CHIN = 152
LEFT_EYE_OUTER, RIGHT_EYE_OUTER = 263, 33     # subject's left / right
LEFT_CHEEK, RIGHT_CHEEK = 425, 205
LEFT_FACE_EDGE, RIGHT_FACE_EDGE = 454, 234
# Iris landmarks (only in the 478-point detector output, not in the mesh).
RIGHT_IRIS = (468, 469, 470, 471, 472)        # centre, then 4 boundary points
LEFT_IRIS = (473, 474, 475, 476, 477)
IRIS_DIAMETER_CM = 1.17                       # horizontal visible iris diameter, near-constant in adults


@dataclass(frozen=True)
class CanonicalFace:
    vertices: np.ndarray       # (468, 3) cm
    faces: np.ndarray          # (898, 3) vertex indices
    face_uvs: np.ndarray       # (898, 3) indices into uvs
    uvs: np.ndarray            # (n_uv, 2), v up (OBJ convention)


@lru_cache(maxsize=1)
def load() -> CanonicalFace:
    verts, uvs, faces, face_uvs = [], [], [], []
    for line in OBJ_PATH.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "v":
            verts.append([float(x) for x in parts[1:4]])
        elif parts[0] == "vt":
            uvs.append([float(x) for x in parts[1:3]])
        elif parts[0] == "f":
            corners = [p.split("/") for p in parts[1:4]]
            faces.append([int(c[0]) - 1 for c in corners])
            face_uvs.append([int(c[1]) - 1 for c in corners])
    return CanonicalFace(np.array(verts), np.array(faces), np.array(face_uvs), np.array(uvs))
