"""Standardized mannequin appearance for GLB export (skin tone, textureless)."""

from typing import Dict, Any

# MVP style metadata
STYLE_NAME = "mannequin-skin-tone-v1"
STYLE_VERSION = "1.0"

# Skin tone base color (RGBA, normalized 0-1)
# RGB: 141, 102, 73 - rich brown North Indian skin tone
SKIN_TONE_COLOR = [0.553, 0.400, 0.286, 1.0]

# Material properties for skin tone mannequin
MATERIAL_PROPERTIES = {
    'baseColorFactor': SKIN_TONE_COLOR,
    'metallicFactor': 0.0,
    'roughnessFactor': 1.0,
    'doubleSided': False,
}

# Get style metadata for serialization to values JSON
def get_style_metadata() -> Dict[str, Any]:
    return {
        'style_name': STYLE_NAME,
        'style_version': STYLE_VERSION,
        'description': 'Skin tone textureless mannequin',
        'has_textures': False,
    }

# Get material configuration for GLB export
def get_material_config() -> Dict[str, Any]:
    return MATERIAL_PROPERTIES.copy()
