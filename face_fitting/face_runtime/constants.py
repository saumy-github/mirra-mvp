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


# Hair textures. Style is geometry baked into first.dan and out of reach, but colour and
# perceived density are these four entries - the same mechanism as the face albedo.
# See .agent/clo-avatar-vto/avatar-personalization-split-decision-26_10_28.md 1.4 and 5.1.
HAIR_MAIN_ALBEDO_ENTRY = 'hair_main.jpg'
HAIR_CAP_ALBEDO_ENTRY = 'hair_cap.jpg'
HAIR_MAIN_ALPHA_ENTRY = 'hair_main_alpha.jpg'
HAIR_CAP_ALPHA_ENTRY = 'hair_cap_alpha.jpg'
HAIR_TEXTURE_SIZE = 2048


# Eye albedo. One 256px texture serves both eyeballs, so the avatar gets a single iris
# colour. The radii below are measured off the stock texture's own radial Lab profile -
# pupil (a=b=128 exactly) to r 10, iris out to r 48, limbal ring to 54, sclera past 56 -
# and are the full-strength band plus its feather, not those boundaries verbatim.
# See .agent/clo-avatar-vto/avatar-personalization-split-decision-26_10_28.md 1.4.
EYE_ALBEDO_ENTRY = 'MV2_Jinho_01_eye.jpg'
EYE_TEXTURE_SIZE = 256
EYE_IRIS_CENTRE_256 = (125.7, 124.1)
EYE_PUPIL_RADIUS_256 = 13.0
EYE_IRIS_INNER_256 = 16.0
EYE_IRIS_OUTER_256 = 44.0
EYE_LIMBUS_RADIUS_256 = 49.0


def anchors_for_size(size: int) -> dict[str, tuple[float, float]]:
    """Scale the measured 2048-px anchors to another square texture size."""
    scale = size / 2048.0
    return {name: (x * scale, y * scale) for name, (x, y) in ANCHORS_2048.items()}


def eye_geometry_for_size(size: int) -> dict[str, object]:
    """Scale the measured 256-px iris geometry to another square texture size."""
    scale = size / float(EYE_TEXTURE_SIZE)
    return {
        'centre': (EYE_IRIS_CENTRE_256[0] * scale, EYE_IRIS_CENTRE_256[1] * scale),
        'pupil_radius': EYE_PUPIL_RADIUS_256 * scale,
        'iris_inner': EYE_IRIS_INNER_256 * scale,
        'iris_outer': EYE_IRIS_OUTER_256 * scale,
        'limbus_radius': EYE_LIMBUS_RADIUS_256 * scale,
    }
