# T-Shirt Image to 3D Garment Pipeline

A minimal but complete pipeline that transforms T-shirt images into 3D garments.

## 🎯 What It Does

```plain
┌─────────────────┐     ┌─────────────────┐
│   INPUT IMAGE   │     │  MEASUREMENTS   │
│   (appearance)  │     │   (structure)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌─────────┐            ┌─────────┐
    │ Extract │            │ Generate│
    │ Design  │            │ Patterns│
    │ + Color │            │  (SVG)  │
    └────┬────┘            └────┬────┘
         │                       │
         └───────────┬───────────┘
                     ▼
              ┌─────────────┐
              │   BLENDER   │
              │  Sew + Sim  │
              └──────┬──────┘
                     ▼
              ┌─────────────┐
              │  3D GARMENT │
              │ with texture│
              └─────────────┘
```

## 📁 Files

| File | Description |
| ---- | ----------- |

| `step1_segmentation.py` | Remove background from T-shirt image |
| `step2_design_extraction.py` | Extract printed design/logo |
| `step3_color_extraction.py` | Find base fabric color |
| `step4_pattern_generation.py` | Generate SVG sewing patterns |
| `step5_blender_sewing.py` | Sew panels in Blender |
| `step6_apply_texture.py` | Apply color and design texture |
| `run_pipeline.sh` | Run everything automatically |

## 🚀 Quick Start

### 1. Place your T-shirt image

```bash
cp your_tshirt.png minimal_pipeline/input_images/front.png
```

### 2. Run the pipeline

```bash
cd minimal_pipeline
./run_pipeline.sh
```

### Or run steps individually

```bash
# Python steps (run from minimal_pipeline directory)
../.venv/bin/python step1_segmentation.py
../.venv/bin/python step2_design_extraction.py
../.venv/bin/python step3_color_extraction.py
../.venv/bin/python step4_pattern_generation.py

# Blender steps (run in background mode)
blender --background --python step5_blender_sewing.py --python step6_apply_texture.py

# Or run interactively in Blender GUI:
# 1. Open Blender
# 2. Go to Scripting workspace
# 3. Open step5_blender_sewing.py and click "Run Script"
# 4. Then open step6_apply_texture.py and click "Run Script"
```

## 📏 Measurements

Step 4 will prompt for these measurements (in cm):

| Measurement | Description | Example |
| ----------- | ----------- | ------- |

| `chest_flat` | Half chest width (pit to pit) | 52 cm |
| `body_length` | Shoulder seam to hem | 72 cm |
| `shoulder_width` | Shoulder to shoulder | 46 cm |
| `sleeve_length` | Shoulder to sleeve hem | 22 cm |
| `armhole_depth` | Shoulder to underarm | 24 cm |

## 📂 Output Structure

```plain
minimal_pipeline/
├── input_images/
│   ├── .gitkeep               # Keeps folder in git
│   └── front.png              # Your input image
├── segmentation_output/
│   ├── .gitkeep               # Keeps folder in git
│   ├── front_mask.png         # Binary mask
│   └── front_masked.png       # T-shirt with transparent bg
├── design_output/
│   ├── .gitkeep               # Keeps folder in git
│   ├── front_design.png       # Extracted design
│   └── front_fabric_mask.png  # Fabric-only areas
├── color_output/
│   ├── .gitkeep               # Keeps folder in git
│   ├── front_fabric_color.json
│   └── front_dominant_color.png
├── pattern_output/
│   ├── .gitkeep               # Keeps folder in git
│   ├── front_pattern.svg
│   ├── back_pattern.svg
│   └── sleeve_pattern.svg
├── .gitignore                 # Ignores generated outputs
└── [Blender output saved separately]
```

**Note**: Output files are git-ignored (see `.gitignore`), only directory structure is tracked.

## 🔧 Requirements

### Python

```bash
pip install opencv-python numpy rembg scikit-learn
```

### Blender

- Download from [https://www.blender.org/download/]
- Version 3.0 or higher

## 🎨 Key Concepts

### Image = Appearance

- Fabric color
- Printed design
- Texture details

### Measurements = Structure

- Panel dimensions
- Seam positions
- Garment fit

**The image never determines size. Measurements always determine size.**

## 📝 License

MIT License
