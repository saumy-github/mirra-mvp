"""
MIRAAA Pipeline Steps Module
"""

from .step1_segmentation import (
    GarmentSegmentor,
    SegmentationResult,
    segment_image,
    save_mask
)

from .step2_design_extraction import (
    DesignExtractor,
    DesignExtractionResult,
    extract_design
)

from .step3_color_extraction import (
    FabricColorExtractor,
    ColorExtractionResult,
    ColorInfo,
    extract_fabric_color,
    rgb_to_hex,
    hex_to_rgb
)

from .step4_pattern_generation import (
    PatternGenerator,
    PatternPiece,
    PatternSet,
    SVGExporter,
    Point,
    BezierCurve,
    generate_patterns
)

from .step5_garment_assembly import (
    BlenderGarmentAssembler,
    SeamConnection,
    StitchType,
    ClothSettings,
    assemble_garment
)

__all__ = [
    # Step 1
    'GarmentSegmentor',
    'SegmentationResult',
    'segment_image',
    'save_mask',
    
    # Step 2
    'DesignExtractor',
    'DesignExtractionResult',
    'extract_design',
    
    # Step 3
    'FabricColorExtractor',
    'ColorExtractionResult',
    'ColorInfo',
    'extract_fabric_color',
    'rgb_to_hex',
    'hex_to_rgb',
    
    # Step 4
    'PatternGenerator',
    'PatternPiece',
    'PatternSet',
    'SVGExporter',
    'Point',
    'BezierCurve',
    'generate_patterns',
    
    # Step 5
    'BlenderGarmentAssembler',
    'SeamConnection',
    'StitchType',
    'ClothSettings',
    'assemble_garment'
]
