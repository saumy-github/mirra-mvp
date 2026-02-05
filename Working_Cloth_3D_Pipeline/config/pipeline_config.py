"""
MIRAAA Pipeline Configuration
All measurements in centimeters (cm)
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, List


@dataclass
class SegmentationConfig:
    """Step 1: Image Segmentation Configuration"""
    min_area_percent: float = 25.0
    max_area_percent: float = 80.0
    morphology_cleanup: bool = True
    connected_component_required: bool = True


@dataclass
class DesignExtractionConfig:
    """Step 2: Design/Print Extraction Configuration"""
    texture_variance_threshold: float = 0.15
    edge_detection_method: str = "canny"
    canny_low_threshold: int = 50
    canny_high_threshold: int = 150


@dataclass
class ColorExtractionConfig:
    """Step 3: Fabric Color Extraction Configuration"""
    color_space: str = "LAB"
    clustering_algorithm: str = "KMeans"
    num_clusters: int = 3
    output_format: str = "RGB"


@dataclass
class Measurements:
    """Step 4: Pattern Measurements (all values in cm)"""
    half_chest_width: float = 50.0
    garment_length: float = 70.0
    shoulder_width: float = 44.0
    armhole_depth: float = 22.0
    hem_width: float = 50.0
    
    sleeve_length: float = 22.0
    bicep_width: float = 36.0
    sleeve_cap_height_offset: float = -1.5
    
    neck_width: float = 18.0
    neck_depth_front: float = 9.0
    neck_depth_back: float = 3.0


@dataclass
class PatternPieceConfig:
    """Configuration for a single pattern piece"""
    name: str
    max_vertices: int
    curve_type: str = "bezier"
    
    
@dataclass
class PatternGenerationConfig:
    """Step 4: Pattern Generation Configuration"""
    measurements: Measurements = field(default_factory=Measurements)
    output_directory: str = "pattern_output/"
    metadata_format: str = "json"
    
    # Pattern pieces configuration
    front_bodice_max_vertices: int = 120
    back_bodice_max_vertices: int = 100
    sleeve_max_vertices: int = 48
    neck_band_max_vertices: int = 64
    
    # Sleeve cap ease
    sleeve_cap_ease_percent: float = 8.0
    
    # Neck band
    neck_band_height: float = 4.0
    neck_band_length_reduction_percent: float = 10.0


@dataclass
class StitchDefinition:
    """Stitch definition for garment assembly"""
    stitch_type: str
    from_piece: str
    from_edge: str
    to_piece: str
    to_edge: str


@dataclass
class SimulationConfig:
    """Cloth simulation configuration"""
    cloth_enabled: bool = True
    self_collision_enabled: bool = False
    frame_start: int = 1
    frame_end: int = 120
    auto_bake: bool = True


@dataclass
class GarmentAssemblyConfig:
    """Step 5: Garment Assembly Configuration"""
    engine: str = "Blender"
    addon_name: str = "GarmentTool"
    output_format: str = "GLB"
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    
    stitches: List[StitchDefinition] = field(default_factory=lambda: [
        StitchDefinition(
            stitch_type="side_seam",
            from_piece="front_bodice",
            from_edge="left_side",
            to_piece="back_bodice",
            to_edge="right_side"
        ),
        StitchDefinition(
            stitch_type="shoulder",
            from_piece="front_bodice",
            from_edge="shoulder",
            to_piece="back_bodice",
            to_edge="shoulder"
        ),
        StitchDefinition(
            stitch_type="armhole",
            from_piece="sleeve",
            from_edge="sleeve_cap",
            to_piece="front_bodice + back_bodice",
            to_edge="armhole"
        ),
        StitchDefinition(
            stitch_type="neck",
            from_piece="neck_band",
            from_edge="edge",
            to_piece="front_bodice + back_bodice",
            to_edge="neckline"
        )
    ])


@dataclass
class PipelineConfig:
    """Complete MIRAAA Pipeline Configuration"""
    version: str = "2.0"
    unit: str = "cm"
    
    segmentation: SegmentationConfig = field(default_factory=SegmentationConfig)
    design_extraction: DesignExtractionConfig = field(default_factory=DesignExtractionConfig)
    color_extraction: ColorExtractionConfig = field(default_factory=ColorExtractionConfig)
    pattern_generation: PatternGenerationConfig = field(default_factory=PatternGenerationConfig)
    garment_assembly: GarmentAssemblyConfig = field(default_factory=GarmentAssemblyConfig)
    
    def update_measurements(self, **kwargs):
        """Update measurements with custom values"""
        for key, value in kwargs.items():
            if hasattr(self.pattern_generation.measurements, key):
                setattr(self.pattern_generation.measurements, key, value)


# Default configuration instance
DEFAULT_CONFIG = PipelineConfig()
