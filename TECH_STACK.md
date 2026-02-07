# Mirra MVP - Tech Stack Summary

**Last Updated:** February 4, 2026

---

## 📋 Overview

The Mirra MVP project is a comprehensive avatar generation and garment simulation pipeline that combines:
- **Human body modeling** using parametric 3D body models (STAR)
- **Garment design extraction** from 2D images
- **3D simulation** of clothing on virtual bodies
- **Measurement management** via MongoDB

---

## 🏗️ Project Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MIRRA MVP                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐        ┌──────────────────┐          │
│  │  Measurements    │        │  Avatar Pipeline │          │
│  │  (MongoDB)       │        │  (STAR Model)    │          │
│  └────────┬─────────┘        └────────┬─────────┘          │
│           │                           │                    │
│           └───────────────┬───────────┘                    │
│                           │                                │
│                    ┌──────▼──────┐                         │
│                    │  2D→3D      │                         │
│                    │  Pipeline   │                         │
│                    └─────────────┘                         │
│                           │                                │
│           ┌───────────────┼───────────────┐                │
│           │               │               │                │
│    ┌──────▼──┐     ┌─────▼────┐    ┌────▼─────┐          │
│    │ Segment │     │ Pattern   │    │ Blender  │          │
│    │ Design  │     │ Generate  │    │ Simulation          │
│    └─────────┘     └───────────┘    └──────────┘          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │              OUTPUT: 3D Garment Model                │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Core Modules

### 1. **mirra_measurements** - Measurement Database
- **Purpose:** Store and retrieve user body measurements
- **Database:** MongoDB
- **Key Files:**
  - `db.py` - MongoDB connection and queries
  - `models.py` - Data models for measurements
  - `seed_measurements.py` - Database initialization
  - `golden_users.py` - Reference user datasets
- **Dependencies:**
  - `pymongo>=4.6.0` - MongoDB driver
  - `python-dotenv>=1.0.0` - Environment variables

### 2. **pipeline_star** - Avatar Generation Pipeline
- **Purpose:** Generate parametric 3D human body models
- **Model:** STAR (Sparse Trained Articulated Human Body Regressor)
- **Key Files:**
  - `first.py` - Main CLI entry point
  - `star_runner.py` - STAR model instantiation and mesh generation
  - `fit_betas.py` - Fit body shape parameters to measurements
  - `avatar_exporter.py` - Export 3D models to GLB format
  - `mesh_postprocess.py` - Post-processing of generated meshes
  - `mesh_measure.py` - Extract measurements from 3D meshes
  - `mapping_layer.py` - Map input measurements to STAR parameters
  - `pose_catalog.py` - Predefined poses (A-pose, etc.)
  - `avatar_style.py` - Material/styling configuration
  - `artifact_io.py` - JSON I/O for pipeline artifacts
  - `artifact_schema.py` - Data schema validation
  - `run_manifest.py` - Manifest and path management
- **Dependencies:**
  - `numpy` - Numerical computations
  - `trimesh` - 3D mesh manipulation
  - STAR model (in `libs/star/`)
- **Output:** GLB files (3D body models)

### 3. **2D_to_3D_tshirt/minimal_pipeline** - Garment Pipeline
- **Purpose:** Extract T-shirt design from images and create 3D garments
- **Key Files:**
  - `step1_segmentation.py` - Background removal & T-shirt isolation
  - `step2_design_extraction.py` - Print/logo detection
  - `step3_color_extraction.py` - Fabric color identification
  - `step4_pattern_generation.py` - SVG sewing pattern creation
  - `step5_blender_sewing.py` - 3D sewing simulation
  - `step6_apply_texture.py` - Texture and color application
- **Workflow:**
  ```
  Image → Segment → Design Extract → Color Extract → Patterns → Sewing → Texture
  ```

#### **Step 1: Segmentation** (`step1_segmentation.py`)
- **Purpose:** Remove background from T-shirt image
- **Methods:**
  - AI-based: `rembg` (U2-Net)
  - Fallback: GrabCut algorithm
  - Refinement: Morphological operations
- **Dependencies:**
  - `opencv-python` (cv2)
  - `numpy`
  - `rembg` (optional, with onnx backend)
- **Outputs:**
  - Binary mask (PNG)
  - Masked RGBA image
  - NumPy array (.npy)

#### **Step 2: Design Extraction** (`step2_design_extraction.py`)
- **Purpose:** Detect printed designs and logos
- **Methods:**
  - Canny edge detection
  - Local variance analysis
  - Color outlier detection
  - Morphological operations
- **Dependencies:**
  - `opencv-python`
  - `numpy`
- **Outputs:**
  - Design mask (PNG)
  - Fabric-only mask (PNG)

#### **Step 3: Color Extraction** (`step3_color_extraction.py`)
- **Purpose:** Identify base fabric color
- **Methods:**
  - K-means clustering (scikit-learn)
  - Dominant color selection
- **Dependencies:**
  - `opencv-python`
  - `numpy`
  - `scikit-learn` (KMeans)
- **Outputs:**
  - Dominant color (JSON, hex, RGB)
  - Color palette

#### **Step 4: Pattern Generation** (`step4_pattern_generation.py`)
- **Purpose:** Create SVG sewing patterns from measurements
- **Inputs:** 5 measurements
  - chest_flat (cm)
  - body_length (cm)
  - shoulder_width (cm)
  - sleeve_length (cm)
  - armhole_depth (cm)
- **Algorithm:** Parametric geometry
- **Outputs:**
  - SVG pattern files (front, back, sleeves)
  - JSON metadata

#### **Step 5: Blender Sewing** (`step5_blender_sewing.py`)
- **Purpose:** 3D construction and cloth simulation
- **Engine:** Blender (Python scripting)
- **Process:**
  1. Import SVG patterns as curves
  2. Convert to cloth meshes
  3. Position for sewing
  4. Define sewing constraints
  5. Run cloth simulation
- **Physics:**
  - Cloth quality: 12 iterations
  - Fabric mass: 0.3 kg/m²
  - Gravity simulation
- **Dependencies:**
  - `bpy` (Blender Python API)
  - `bmesh` (Mesh operations)
  - `mathutils` (Vector/Matrix math)
- **Outputs:**
  - Blender file (.blend)
  - 3D mesh geometry

#### **Step 6: Texture Application** (`step6_apply_texture.py`)
- **Purpose:** Apply colors and designs to 3D mesh
- **Engine:** Blender
- **Process:**
  1. Create Blender materials
  2. Apply base fabric color
  3. Map design texture
  4. Configure material properties
- **Dependencies:**
  - `bpy`
  - `mathutils`
- **Outputs:**
  - Textured 3D model
  - Final garment file

### 4. **pipeline_smpl** & **pipeline_smplx** - Alternative Body Models
- **Purpose:** Alternative body model implementations
- **Status:** Placeholder/alternative implementations
- **Files:**
  - `first.py` - Main entry points
- **Note:** STAR (pipeline_star) is the primary model in use

---

## 🔧 Technology Stack

### **Language**
- **Python 3.x** - Primary language for all pipelines

### **Image Processing**
| Tool | Purpose | Used In |
|------|---------|---------|
| OpenCV (cv2) | Image segmentation, edge detection | Steps 1-3 |
| rembg | AI background removal (U2-Net) | Step 1 |
| NumPy | Array operations | All steps |
| Pillow (PIL) | Image I/O | Various |
| scikit-learn | K-means clustering | Step 3 |

### **3D Modeling & Geometry**
| Tool | Purpose | Used In |
|------|---------|---------|
| Blender | 3D modeling, cloth simulation | Steps 5-6 |
| bpy | Blender Python API | Steps 5-6 |
| bmesh | Blender mesh editing | Step 5 |
| mathutils | Vector/Matrix math | Steps 5-6 |
| trimesh | 3D mesh manipulation | STAR pipeline |
| STAR Model | Parametric human body | Avatar pipeline |

### **Data & Database**
| Tool | Purpose | Used In |
|------|---------|---------|
| MongoDB | Measurement storage | Measurements module |
| PyMongo | MongoDB driver | DB queries |
| JSON | Configuration & data exchange | All steps |
| NumPy (.npy) | Binary array storage | Image masks |

### **File Formats**
| Format | Purpose | Extension |
|--------|---------|-----------|
| PNG | Images (RGB/RGBA) | .png |
| SVG | Vector patterns | .svg |
| JSON | Configuration & metadata | .json |
| NumPy Arrays | Binary masks | .npy |
| Blender Files | 3D scenes | .blend |
| GLB/GLTF | Exported 3D models | .glb |
| EXR | High-quality rendering | .exr |

### **Utilities**
- `pathlib` - Path manipulation
- `json` - JSON parsing
- `argparse` - CLI argument parsing
- `datetime` - Timestamp management
- `gc` - Garbage collection
- `python-dotenv` - Environment variable loading

---

## 🚀 Execution Entry Points

### **Avatar Generation** (Body Models)
```bash
python pipeline_star/first.py --user_id <id> --mode <mode>
```
- **Modes:** query, fit, export
- **Output:** GLB file with textured 3D body

### **Garment Pipeline** (T-Shirt)
```bash
cd 2D_to_3D_tshirt/minimal_pipeline

# Run all steps
./run_complete_pipeline.bat  # Windows
./run_pipeline.sh            # Linux/Mac

# Or individual steps
python step1_segmentation.py
python step2_design_extraction.py
python step3_color_extraction.py
python step4_pattern_generation.py
blender --python step5_blender_sewing.py
blender --python step6_apply_texture.py
```

### **Direct Script**
```bash
python run_avatar_pipeline.py
```
- Interactive CLI for avatar generation

---

## 📊 Data Flow

### **Avatar Generation Flow**
```
User Measurements (MongoDB)
         ↓
fit_betas_to_measurements() [Optimize STAR parameters]
         ↓
generate_mesh() [STAR model]
         ↓
mesh_postprocess() [Refinement]
         ↓
export_mesh_to_glb() [GLB export]
         ↓
3D Body Model (GLB)
```

### **Garment Generation Flow**
```
Input Image
    ↓
Step 1: Segmentation → Mask
    ↓
Step 2: Design Extraction → Design Texture
    ↓
Step 3: Color Extraction → Fabric Color
    ↓
Step 4: Pattern Generation → SVG Patterns
    ↓
Step 5: Blender Sewing → 3D Mesh
    ↓
Step 6: Texture Application → Textured 3D Garment
```

---

## 🗂️ Directory Structure

```
mirra-mvp/
├── mirra_measurements/          # Measurement database module
│   ├── db.py
│   ├── models.py
│   ├── requirements.txt
│   └── ...
├── pipeline_star/               # STAR body model pipeline
│   ├── first.py
│   ├── star_runner.py
│   ├── fit_betas.py
│   ├── avatar_exporter.py
│   ├── generated/               # Output: GLB files & JSONs
│   └── ...
├── pipeline_smpl/               # Alternative SMPL model
├── pipeline_smplx/              # Alternative SMPLx model
├── 2D_to_3D_tshirt/
│   └── minimal_pipeline/        # T-shirt garment pipeline
│       ├── step1_segmentation.py
│       ├── step2_design_extraction.py
│       ├── step3_color_extraction.py
│       ├── step4_pattern_generation.py
│       ├── step5_blender_sewing.py
│       ├── step6_apply_texture.py
│       ├── segmentation_output/
│       ├── design_output/
│       ├── color_output/
│       ├── pattern_output/
│       └── input_images/
├── libs/
│   └── star/                    # STAR body model library
├── run_avatar_pipeline.py       # Main CLI entry point
└── TECH_STACK.md               # This file
```

---

## 🔗 Key Dependencies Summary

### **Core Scientific**
- `numpy` - Numerical arrays
- `scipy` - Scientific computing
- `scikit-learn` - Machine learning (K-means)

### **3D & Graphics**
- `opencv-python` - Computer vision
- `trimesh` - 3D mesh processing
- `bpy` (Blender) - 3D modeling engine
- `bmesh` (Blender) - Mesh editing

### **Image Processing**
- `rembg` - AI background removal
- `Pillow` - Image I/O
- `python-dotenv` - Config management

### **Data Storage**
- `pymongo` - MongoDB database driver

### **Specialized Models**
- **STAR** - Parametric human body model (custom library)
- **SMPL** - Alternative body model (optional)
- **SMPLx** - Hand-inclusive body model (optional)

---

## 🎯 Project Goals

1. **Body Modeling:** Generate realistic 3D human avatars from body measurements
2. **Garment Extraction:** Extract T-shirt design from 2D photos
3. **3D Garment Simulation:** Create realistic 3D garments with physics
4. **Integration:** Combine body models with custom garments
5. **Export:** Generate production-ready 3D models (GLB format)

---

## 📝 Configuration & Environment

### **Environment Variables**
- Managed via `.env` file (python-dotenv)
- MongoDB connection strings
- File paths and directories
- Model parameters

### **Database Configuration**
- MongoDB instance (local or cloud)
- Collections: measurements, users
- Indexes: user_id, timestamps

### **Blender Configuration**
- Version: Compatible with Blender 3.x+
- Python API: bpy module
- Execution: Command-line or interactive

---

## 🚦 Status & Notes

### **Active**
- ✅ `pipeline_star/` - Primary STAR-based avatar generation
- ✅ `mirra_measurements/` - MongoDB measurement storage
- ✅ `2D_to_3D_tshirt/minimal_pipeline/` - Garment pipeline (6 steps)

### **Development**
- 🔄 `pipeline_smpl/` - Alternative model (optional)
- 🔄 `pipeline_smplx/` - Hand-tracking model (optional)

### **Special Features**
- Multi-threaded safety: STAR model cache not thread-safe (single-threaded only)
- Blender integration: Full Python scripting support
- Cloth simulation: Configurable physics parameters
- Image processing: Multiple fallback methods for robustness

---

**For detailed documentation on individual components, refer to:**
- [T-Shirt Pipeline Summary](2D_to_3D_tshirt/PIPELINE_SUMMARY.md)
- [Minimal Pipeline README](2D_to_3D_tshirt/minimal_pipeline/README.md)
- [Measurements Module README](mirra_measurements/README.md)
