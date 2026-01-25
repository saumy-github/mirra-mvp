"""Standardized mannequin appearance for GLB export (matte black, textureless)."""

from typing import Dict, Any


# MVP style metadata
STYLE_NAME = "mannequin-matte-black-v1"
STYLE_VERSION = "1.0"


# Matte black base color (RGBA, normalized 0-1)
MATTE_BLACK_COLOR = [0.0, 0.0, 0.0, 1.0]


# Material properties for matte black mannequin
MATERIAL_PROPERTIES = {
    'baseColorFactor': MATTE_BLACK_COLOR,
    'metallicFactor': 0.0,
    'roughnessFactor': 1.0,
    'doubleSided': False,
}


# Get style metadata for serialization to values JSON
def get_style_metadata() -> Dict[str, Any]:
    return {
        'style_name': STYLE_NAME,
        'style_version': STYLE_VERSION,
        'description': 'Matte black textureless mannequin',
        'has_textures': False,
    }


# Get material configuration for GLB export
def get_material_config() -> Dict[str, Any]:
    return MATERIAL_PROPERTIES.copy()
