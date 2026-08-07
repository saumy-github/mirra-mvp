"""Replace the face color texture inside a CLO .avt file."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import cv2
import numpy as np


_FACE_TEXTURE_NAME = "MV2_Jinho_01_face.jpg"
_HAIR_TEXTURE_NAME = "hair_main.jpg"
_JPEG_QUALITY = 95


def extract_base_texture(avt_path: Path) -> np.ndarray:
    """Read the face texture from an .avt file and return it as a BGR array."""
    raw = avt_path.read_bytes()
    zip_start = raw.find(b"PK\x03\x04")
    if zip_start < 0:
        raise ValueError(f"No ZIP header in {avt_path}")
    with zipfile.ZipFile(io.BytesIO(raw[zip_start:]), "r") as z:
        jpg_bytes = z.read(_FACE_TEXTURE_NAME)
    arr = np.frombuffer(jpg_bytes, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def patch(
    source_avt: Path,
    face_texture: np.ndarray,
    output_avt: Path,
    hair_texture: np.ndarray | None = None,
) -> dict:
    """
    Write a new .avt with the face color texture replaced.

    Preserves all other members exactly as-is.
    Swaps MV2_Jinho_01_face.jpg always, and hair_main.jpg if hair_texture provided.

    Returns metadata dict describing what was patched.
    """
    raw = source_avt.read_bytes()
    zip_start = raw.find(b"PK\x03\x04")
    if zip_start < 0:
        raise ValueError(f"No ZIP header in {source_avt}")
    prefix = raw[:zip_start]

    members: list[tuple[zipfile.ZipInfo, bytes]] = []
    with zipfile.ZipFile(io.BytesIO(raw[zip_start:]), "r") as archive:
        for info in archive.infolist():
            members.append((info, archive.read(info.filename)))

    _, jpg_buf = cv2.imencode(
        ".jpg", face_texture, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY]
    )
    new_face_bytes = jpg_buf.tobytes()

    new_hair_bytes: bytes | None = None
    if hair_texture is not None:
        _, hair_buf = cv2.imencode(
            ".jpg", hair_texture, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY]
        )
        new_hair_bytes = hair_buf.tobytes()

    replaced = False
    hair_replaced = False
    original_bytes = 0
    for i, (info, data) in enumerate(members):
        if info.filename == _FACE_TEXTURE_NAME:
            original_bytes = len(data)
            members[i] = (info, new_face_bytes)
            replaced = True
        elif new_hair_bytes is not None and info.filename == _HAIR_TEXTURE_NAME:
            members[i] = (info, new_hair_bytes)
            hair_replaced = True

    if not replaced:
        raise ValueError(f"{_FACE_TEXTURE_NAME} not found inside {source_avt}")

    out_buf = io.BytesIO()
    with zipfile.ZipFile(out_buf, "w") as archive:
        for info, data in members:
            new_info = zipfile.ZipInfo(info.filename)
            new_info.date_time = info.date_time
            new_info.compress_type = info.compress_type
            new_info.comment = info.comment
            new_info.extra = info.extra
            new_info.create_system = info.create_system
            new_info.external_attr = info.external_attr
            new_info.internal_attr = info.internal_attr
            new_info.flag_bits = info.flag_bits
            archive.writestr(new_info, data)

    output_avt.write_bytes(prefix + out_buf.getvalue())

    return {
        "source_avt": str(source_avt),
        "output_avt": str(output_avt),
        "face_texture_replaced": _FACE_TEXTURE_NAME,
        "original_face_bytes": original_bytes,
        "new_face_bytes": len(new_face_bytes),
        "hair_texture_replaced": hair_replaced,
        "output_size_bytes": output_avt.stat().st_size,
    }
