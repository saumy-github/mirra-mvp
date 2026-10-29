"""Measured constants for the base avatar template. Re-measure if the template changes."""

from __future__ import annotations

BASE_TEMPLATE = 'MV2_Jinho_01'

AVT_PREFIX_BYTES = 244210
AVT_ENTRY_COUNT = 30

HEAD_ALBEDO_ENTRY = 'MV2_Jinho_01_face.jpg'
HEAD_NORMAL_ENTRY = 'MV2_Jinho_01_face_normal.jpg'
HEAD_ROUGHNESS_ENTRY = 'MV2_Jinho_01_face_roughness.jpg'
HEAD_TEXTURE_SIZE = 2048

# Anchor pixels in the stock 2048x2048 albedo, from the deep-dive measurements.
ANCHORS_2048 = {
    'eye_l': (862.0, 643.0),
    'eye_r': (1166.0, 638.0),
    'mouth': (1024.0, 907.0),
}
INTEROCULAR_PX_2048 = 304.0

# Haar-detected face box in the UV map, as (u0, v0, u1, v1).
FACE_BBOX_UV = (0.344, 0.181, 0.660, 0.497)
# High-detail head region from the Sobel energy analysis, as (u0, v0, u1, v1).
INFORMATIVE_UV = (0.15, 0.10, 0.85, 0.60)

BODY_ALBEDO_ENTRIES = [
    'MV2_Jinho_01_body_Covered_7422644.jpg',
    'MV2_Jinho_01_arm.jpg',
    'MV2_Jinho_01_leg.jpg',
]


def anchors_for_size(size: int) -> dict[str, tuple[float, float]]:
    """Scale the measured 2048-px anchors to another square texture size."""
    scale = size / 2048.0
    return {name: (x * scale, y * scale) for name, (x, y) in ANCHORS_2048.items()}
