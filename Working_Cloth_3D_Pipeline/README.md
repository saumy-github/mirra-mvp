# MIRAAA Pipeline

**Garment Design Automation Pipeline** - Version 2.0

A complete pipeline for automating garment design from image to 3D model. All measurements are in **centimeters (cm)**.

## Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         MIRAAA Pipeline v2.0                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │   Step 1     │    │   Step 2     │    │   Step 3     │              │
│  │ Segmentation │───▶│   Design     │───▶│    Color     │              │
│  │              │    │  Extraction  │    │  Extraction  │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│         │                                       │                       │
│         │                                       │                       │
│         ▼                                       ▼                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│  │  Binary Mask │    │ Fabric Mask  │    │ Primary RGB  │              │
│  │              │    │ Design Mask  │    │    Color     │              │
│  └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                        Step 4                                 │      │
│  │                  Pattern Generation                           │      │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ │      │
│  │  │   Front    │ │   Back     │ │   Sleeve   │ │  Neck Band │ │      │
│  │  │   Bodice   │ │   Bodice   │ │            │ │            │ │      │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘ │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                        Step 5                                 │      │
│  │                  Garment Assembly                             │      │
│  │         (Blender + GarmentTool + Cloth Simulation)           │      │
│  └──────────────────────────────────────────────────────────────┘      │
│                              │                                          │
│                              ▼                                          │
│                      ┌──────────────┐                                   │
│                      │   GLB Mesh   │                                   │
│                      └──────────────┘                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Installation

```bash
# Clone the repository
cd Miraa_new

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Blender Setup (for Step 5)

For the garment assembly step, you need:
1. [Blender](https://www.blender.org/download/) (3.0 or later)
2. [GarmentTool addon](https://github.com/blender/garment-tool) (optional, for advanced sewing)

## Quick Start

### Full Pipeline (with image input)

```bash
python pipeline.py input_image.jpg -o output/
```

### Pattern Generation Only

```bash
python pipeline.py --pattern-only -o output/ \
    --chest 50 \
    --length 70 \
    --shoulder 44
```

### Individual Steps

```python
from steps import (
    segment_image,
    DesignExtractor,
    FabricColorExtractor,
    PatternGenerator,
    assemble_garment
)

# Step 1: Segment image
seg_result = segment_image("garment.jpg")

# Step 2: Extract design
extractor = DesignExtractor()
design_result = extractor.extract(seg_result.original_image, seg_result.mask)

# Step 3: Extract colors
color_extractor = FabricColorExtractor()
color_result = color_extractor.extract(
    seg_result.original_image, 
    design_result.fabric_mask
)

# Step 4: Generate patterns
generator = PatternGenerator()
patterns = generator.generate_all_pieces()

# Step 5: Generate Blender assembly files
assemble_garment("patterns/", "output/")
```

## Configuration

All configuration is in `config/pipeline_config.py`:

### Measurements (Default values in cm)

| Measurement | Default | Description |
|-------------|---------|-------------|
| `half_chest_width` | 50 | Half of full chest measurement |
| `garment_length` | 70 | Total length from shoulder to hem |
| `shoulder_width` | 44 | Shoulder to shoulder |
| `armhole_depth` | 22 | Depth of armhole |
| `hem_width` | 50 | Width at hem |
| `sleeve_length` | 22 | Length of sleeve |
| `bicep_width` | 36 | Width at bicep |
| `neck_width` | 18 | Neck opening width |
| `neck_depth_front` | 9 | Front neck drop |
| `neck_depth_back` | 3 | Back neck drop |

### Custom Configuration

```python
from config import PipelineConfig, Measurements

config = PipelineConfig()

# Update measurements
config.pattern_generation.measurements = Measurements(
    half_chest_width=52,
    garment_length=72,
    shoulder_width=46,
    # ... other measurements
)

# Run with custom config
from pipeline import MIRAAPipeline
pipeline = MIRAAPipeline(config)
result = pipeline.run("input.jpg")
```

## Project Structure

```
Miraa_new/
├── config/
│   ├── __init__.py
│   └── pipeline_config.py      # All configuration classes
│
├── steps/
│   ├── __init__.py
│   ├── step1_segmentation.py   # Image segmentation
│   ├── step2_design_extraction.py  # Design/print extraction
│   ├── step3_color_extraction.py   # Color analysis
│   ├── step4_pattern_generation.py # SVG pattern creation
│   └── step5_garment_assembly.py   # Blender integration
│
├── pipeline.py                 # Main orchestrator
├── requirements.txt
└── README.md
```

## Output Files

Running the full pipeline generates:

```
output/
├── segmentation_mask.png       # Binary mask from Step 1
├── fabric_mask.png             # Plain fabric regions
├── design_mask.png             # Design/print regions
├── colors.json                 # Extracted color data
├── color_palette.png           # Color swatch visualization
├── pipeline_result.json        # Full result summary
│
├── patterns/
│   ├── front_bodice.svg
│   ├── back_bodice.svg
│   ├── sleeve.svg
│   ├── neck_band.svg
│   └── metadata.json
│
└── assembly/
    ├── garment_assemble.py     # Blender Python script
    └── garment_config.json     # GarmentTool configuration
```

## Running Blender Assembly

After generating patterns:

```bash
# Run with Blender in background mode
blender --background --python output/assembly/garment_assemble.py

# Or open in Blender GUI and run the script
```

## API Reference

### Step 1: Segmentation

```python
from steps import segment_image, SegmentationResult

result: SegmentationResult = segment_image(
    image_path="garment.jpg",
    config=SegmentationConfig(
        min_area_percent=25,
        max_area_percent=80,
        morphology_cleanup=True,
        connected_component_required=True
    )
)

# Access results
result.mask           # Binary numpy array
result.area_percent   # Percentage of image
result.is_valid       # Passed sanity checks
```

### Step 2: Design Extraction

```python
from steps import DesignExtractor, DesignExtractionResult

extractor = DesignExtractor()
result: DesignExtractionResult = extractor.extract(image, mask)

result.fabric_mask          # Plain fabric regions
result.design_mask          # Design/print regions
result.has_design           # True if design detected
result.design_coverage_percent
```

### Step 3: Color Extraction

```python
from steps import FabricColorExtractor, ColorExtractionResult

extractor = FabricColorExtractor()
result: ColorExtractionResult = extractor.extract(image, fabric_mask)

result.primary_color.rgb    # (R, G, B) tuple
result.primary_color.hex_code  # "#RRGGBB"
result.all_colors           # List of all extracted colors
```

### Step 4: Pattern Generation

```python
from steps import PatternGenerator, PatternSet

generator = PatternGenerator(config)
pattern_set: PatternSet = generator.generate_all_pieces()

# Access pieces
for name, piece in pattern_set.pieces.items():
    print(f"{name}: {piece.get_perimeter()} cm perimeter")

# Export to SVG
from steps import SVGExporter
exporter = SVGExporter("output/patterns")
exporter.export_all(pattern_set)
```

### Step 5: Garment Assembly

```python
from steps import assemble_garment

result = assemble_garment(
    pattern_directory="patterns/",
    output_directory="assembly/",
    config=GarmentAssemblyConfig()
)

# Generated files
result["blender_script"]        # Path to .py script
result["garment_tool_config"]   # Path to .json config
result["expected_output"]       # Path to .glb output
```

## Stitch Definitions

The pipeline defines these seam connections:

| Stitch Type | From | To |
|-------------|------|-----|
| `side_seam` | front_bodice.left_side | back_bodice.right_side |
| `shoulder` | front_bodice.shoulder | back_bodice.shoulder |
| `armhole` | sleeve.sleeve_cap | front+back_bodice.armhole |
| `neck` | neck_band | front+back_bodice.neckline |

## Cloth Simulation Settings

Default simulation parameters (adjustable):

| Setting | Default | Description |
|---------|---------|-------------|
| `quality` | 5 | Simulation substeps |
| `mass` | 0.3 kg/m² | Fabric weight |
| `bending_stiffness` | 0.5 | Resistance to bending |
| `tension_stiffness` | 15.0 | Resistance to stretching |
| `frame_range` | 1-120 | Simulation frames |

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues and feature requests, please open a GitHub issue.
