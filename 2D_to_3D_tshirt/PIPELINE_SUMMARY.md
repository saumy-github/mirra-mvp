# 2D to 3D T-Shirt Pipeline - Complete Summary

**Architecture Overview**  
**Last Updated:** January 29, 2026

---

## 🎯 What This Pipeline Does

Transforms a **2D photograph** of a T-shirt into a **fully textured 3D garment model**.

```
INPUT                  PROCESS                   OUTPUT
┌──────────┐          ┌──────────┐             ┌──────────┐
│  Photo   │  ──────► │ Pipeline │  ─────────► │   3D     │
│  (PNG)   │          │ 6 Steps  │             │  Model   │
└──────────┘          └──────────┘             └──────────┘
                           │
                ┌──────────┼──────────┐
                │          │          │
          ┌─────▼────┐ ┌──▼───┐ ┌───▼────┐
          │ Segment  │ │Design│ │ Color  │
          │ Extract  │ │ Gen. │ │ Sew    │
          └──────────┘ └──────┘ └────────┘
```

---

## 📊 Pipeline Architecture

### **Phase 1: Image Analysis** (Steps 1-3)
**Goal:** Extract appearance information from the photo

| Step | Name | Input | Output | Technology |
|------|------|-------|--------|-----------|
| 1 | Segmentation | `front.png` | T-shirt mask | rembg (U2-Net AI) |
| 2 | Design Extraction | Masked image | Design texture | Edge detection, K-means |
| 3 | Color Extraction | Fabric pixels | Base color | Color clustering |

### **Phase 2: Structure Generation** (Step 4)
**Goal:** Create physical pattern pieces from measurements

| Step | Name | Input | Output | Technology |
|------|------|-------|--------|-----------|
| 4 | Pattern Generation | 5 measurements | SVG patterns | Parametric geometry |

### **Phase 3: 3D Construction** (Steps 5-6)
**Goal:** Assemble 3D garment and apply textures

| Step | Name | Input | Output | Technology |
|------|------|-------|--------|-----------|
| 5 | Sewing & Simulation | SVG patterns | 3D mesh | Blender cloth physics |
| 6 | Texture Application | Color + design | Textured 3D | Blender materials |

---

## 🔬 Technical Deep Dive

### **Step 1: Segmentation** (`step1_segmentation.py`)

**Purpose:** Remove background, isolate T-shirt

**Process:**
1. Load input image (JPG/PNG)
2. Run AI background removal (rembg/U2-Net)
3. Fallback to GrabCut if rembg unavailable
4. Refine mask edges (morphological operations)
5. Create RGBA image with transparent background

**Key Functions:**
- `segment_with_rembg()` - AI-powered (best quality)
- `segment_garment_grabcut()` - Semi-automatic fallback
- `refine_mask()` - Edge smoothing

**Output Files:**
```
segmentation_output/
├── front_mask.png          # Binary mask (white=shirt, black=bg)
├── front_masked.png        # RGBA image (transparent bg)
└── front_mask.npy          # NumPy array (for scripts)
```

**Dependencies:** opencv-python, numpy, rembg

---

### **Step 2: Design Extraction** (`step2_design_extraction.py`)

**Purpose:** Separate printed design from fabric

**Process:**
1. Load masked T-shirt from Step 1
2. Detect edges using Canny edge detector
3. Analyze texture variation (local variance)
4. Detect color outliers (pixels != fabric color)
5. Combine all three methods with OR logic
6. Clean up with morphological operations
7. Create fabric-only mask (garment - design)

**Key Algorithms:**
- **Edge Detection:** Canny(50, 150) for print boundaries
- **Texture Analysis:** Local variance kernel (15x15)
- **Color Outliers:** 3-sigma deviation from fabric mean

**Output Files:**
```
design_output/
├── front_design_mask.png       # Binary mask of design
├── front_design.png            # Extracted design (RGBA)
├── front_fabric_mask.png       # Fabric areas only
└── front_visualization.png     # Color-coded overlay
```

**Why it matters:** Accurate fabric-only mask = correct color extraction

---

### **Step 3: Color Extraction** (`step3_color_extraction.py`)

**Purpose:** Find the true base fabric color

**Process:**
1. Load masked image + fabric mask from Step 2
2. Extract fabric pixels (exclude design)
3. Convert BGR → LAB color space
4. Run K-means clustering (k=3)
5. Dominant cluster = fabric color
6. Calculate color statistics (mean, std dev)
7. Generate hex code and color name

**Key Algorithm:**
- K-means clustering in RGB space
- Largest cluster = dominant color
- Sampling ~100k pixels for performance

**Output Files:**
```
color_output/
├── front_fabric_color.json     # Full color data
├── front_dominant_color.txt    # Simple text format
├── front_color_swatch.png      # Visual bar chart
└── front_dominant_color.png    # Solid color square
```

**JSON Structure:**
```json
{
  "dominant": {
    "rgb": [45, 67, 89],
    "hex": "#2d4359",
    "name": "Dark Blue",
    "percentage": 78.4
  },
  "all_colors": [...],
  "statistics": {...}
}
```

**Dependencies:** scikit-learn

---

### **Step 4: Pattern Generation** (`step4_pattern_generation.py`)

**Purpose:** Create sewing patterns from measurements

**Key Concept:** **Image ≠ Size. Measurements = Size.**

**The 5 Critical Measurements:**
1. **chest_flat** - Half chest width (pit to pit when laying flat)
2. **body_length** - Shoulder seam to bottom hem
3. **shoulder_width** - Shoulder point to shoulder point
4. **sleeve_length** - Shoulder seam to sleeve hem
5. **armhole_depth** - Shoulder seam to underarm point

**Process:**
1. Prompt user for measurements (or use defaults)
2. Calculate panel dimensions from measurements
3. Generate front panel with neckline curve
4. Generate back panel (shallower neckline)
5. Generate sleeve with cap curve
6. Add seam allowances (1.5 cm)
7. Export as SVG (real size in cm)
8. Generate seam definitions for Blender

**Mathematical Components:**
- **Bezier Curves:** Smooth necklines, armholes, sleeve caps
- **Parametric Design:** All dimensions calculated from 5 inputs
- **Real-Size Output:** SVG viewBox in cm (1:1 scale)

**Pattern Pieces:**
- **Front:** Cut 1 on fold → full width when unfolded
- **Back:** Cut 1 on fold → full width when unfolded  
- **Sleeve:** Cut 2 (left/right mirrored)

**Output Files:**
```
pattern_output/
├── front_pattern.svg           # Front panel
├── back_pattern.svg            # Back panel
├── sleeve_pattern.svg          # Sleeve (cut 2x)
├── pattern_metadata.json       # All measurements
└── seams.json                  # Sewing instructions
```

**seams.json Structure:**
Defines which edges connect:
```json
{
  "seams": [
    {
      "name": "left_side_seam",
      "panel_a": "front",
      "edge_a": "side_seam",
      "panel_b": "back",
      "edge_b": "side_seam"
    },
    ...
  ]
}
```

---

### **Step 5: Blender Sewing** (`step5_blender_sewing.py`)

**Purpose:** Convert 2D patterns → 3D garment via cloth simulation

**⚠️ IMPORTANT:** This runs INSIDE Blender, not standalone

**Process:**
1. Import SVG patterns from Step 4
2. Convert curves → mesh (polygon outlines)
3. Scale from cm → meters (Blender units)
4. Position panels in 3D space
5. Define sewing constraints (vertex groups)
6. Apply cloth physics to all panels
7. Pin matching seam edges together
8. Run simulation (gravity pulls into shape)
9. Bake simulation to mesh
10. Save as Blender file

**Cloth Physics Settings:**
```python
{
  "quality": 12,              # Simulation substeps
  "mass": 0.3,                # Fabric weight (kg/m²)
  "tension_stiffness": 15,    # Resist stretching
  "compression_stiffness": 15,
  "bending_stiffness": 0.5,   # Fabric drape
  "air_damping": 1            # Air resistance
}
```

**Sewing Mechanics:**
- **Spring Constraints:** Pull matching edges together
- **Vertex Groups:** Define seam edges
- **Force Field:** Optional wind for draping

**Seam Matching Strategy:**
- **Straight Seams:** Bounding box edge detection
- **Curved Seams (armhole):** Sector-based quadrant detection
- **Vertex Count Matching:** Interpolate if counts differ

**Critical Function:**
```python
get_edge_vertices_by_direction(mesh, direction="armhole_left")
# Returns vertices in the upper-left quadrant
# Excludes shoulder top and side straight edges
```

**Output:** Blender `.blend` file with 3D garment

**How to Run:**
1. Open Blender
2. Scripting workspace
3. Open `step5_blender_sewing.py`
4. Click "Run Script"

OR command line:
```bash
blender --python step5_blender_sewing.py
```

**Dependencies:** Blender 3.0+

---

### **Step 6: Texture Application** (`step6_apply_texture.py`)

**Purpose:** Apply color + design to 3D mesh

**⚠️ IMPORTANT:** Run AFTER Step 5 inside Blender

**Process:**
1. Load fabric color from `color_output/front_fabric_color.json`
2. Load design image from `design_output/front_design.png`
3. Convert RGB 0-255 → 0.0-1.0 (Blender format)
4. Create material with Principled BSDF shader
5. Set base color to fabric color
6. Add design image as texture overlay (if exists)
7. Mix using alpha channel (design transparency)
8. Create UV unwrap for proper texture mapping
9. Assign material to garment mesh
10. Render preview

**Material Node Tree:**
```
┌─────────────┐
│  Design PNG │──┐
│  (texture)  │  │
└─────────────┘  │
                 │    ┌──────────┐       ┌────────┐
                 ├───►│ Mix RGB  │──────►│ BSDF   │
                 │    │ (Alpha)  │       │ Output │
┌─────────────┐  │    └──────────┘       └────────┘
│ Fabric Color│──┘
│   (solid)   │
└─────────────┘
```

**UV Mapping:**
- Smart UV Project (for complex geometry)
- OR manual UV unwrap (for control)

**Output:** Final textured 3D model in Blender

---

## 🔄 Data Flow Between Steps

```
Step 1:  front.png 
         → front_masked.png, front_mask.png

Step 2:  front_masked.png, front_mask.png
         → front_design.png, front_fabric_mask.png

Step 3:  front_masked.png, front_fabric_mask.png
         → front_fabric_color.json

Step 4:  User measurements
         → *.svg patterns, seams.json

Step 5:  *.svg, seams.json
         → 3D mesh in Blender

Step 6:  3D mesh, front_fabric_color.json, front_design.png
         → Textured 3D garment
```

---

## 🛠️ Technology Stack

### **Python Libraries**
| Library | Purpose | Used In |
|---------|---------|---------|
| opencv-python | Image processing | Steps 1, 2, 3 |
| numpy | Array operations | All steps |
| rembg | AI background removal | Step 1 |
| scikit-learn | K-means clustering | Step 3 |
| Pillow | Image I/O | Steps 1-3 |

### **External Tools**
| Tool | Purpose | Used In |
|------|---------|---------|
| Blender 3.0+ | 3D modeling & simulation | Steps 5, 6 |
| U2-Net | AI segmentation model | Step 1 (via rembg) |

### **File Formats**
- **Input:** PNG, JPG
- **Intermediate:** PNG (RGBA), JSON, NPY
- **Output:** SVG, Blender (.blend), OBJ/FBX (export)

---

## ⚙️ Configuration & Parameters

### **Tunable Settings**

**Step 1:**
```python
# GrabCut rectangle margin
margin_x = int(width * 0.1)    # 10% horizontal margin
margin_y = int(height * 0.05)  # 5% vertical margin
```

**Step 2:**
```python
# Edge detection
cv2.Canny(blurred, 50, 150)

# Color outlier threshold
threshold = 3.0  # Standard deviations

# Minimum design area
min_area_ratio = 0.001  # 0.1% of garment
```

**Step 3:**
```python
# Number of color clusters
N_CLUSTERS = 3

# Max pixels to sample
max_samples = 100000
```

**Step 4:**
```python
# Seam allowance
SEAM_ALLOWANCE = 1.5  # cm

# SVG display scale
SVG_SCALE = 10  # 1 cm = 10 pixels
```

**Step 5:**
```python
# Cloth simulation quality
CLOTH_SETTINGS = {
    "quality": 12,
    "mass": 0.3,
    "tension_stiffness": 15,
    "bending_stiffness": 0.5,
}
```

---

## 📁 Complete Directory Structure

```
2D_to_3D_tshirt/
├── minimal_pipeline/
│   ├── input_images/
│   │   └── front.png                    # INPUT: Your T-shirt photo
│   ├── segmentation_output/
│   │   ├── front_mask.png              # Step 1 output
│   │   └── front_masked.png
│   ├── design_output/
│   │   ├── front_design.png            # Step 2 output
│   │   ├── front_design_mask.png
│   │   └── front_fabric_mask.png
│   ├── color_output/
│   │   ├── front_fabric_color.json     # Step 3 output
│   │   └── front_dominant_color.png
│   ├── pattern_output/
│   │   ├── front_pattern.svg           # Step 4 output
│   │   ├── back_pattern.svg
│   │   ├── sleeve_pattern.svg
│   │   └── seams.json
│   ├── step1_segmentation.py
│   ├── step2_design_extraction.py
│   ├── step3_color_extraction.py
│   ├── step4_pattern_generation.py
│   ├── step5_blender_sewing.py
│   └── step6_apply_texture.py
```

---

## 🎓 Key Concepts

### **1. Separation of Concerns**
- **Appearance (Steps 1-3):** Extract visual information from photo
- **Structure (Step 4):** Define physical dimensions from measurements
- **Assembly (Steps 5-6):** Combine appearance + structure → 3D

### **2. Image ≠ Size Principle**
The photo NEVER determines garment size. Only measurements do.

**Example:**
- Photo shows a large T-shirt
- User enters small measurements
- **Result:** Small T-shirt with large design

### **3. Parametric Design**
All patterns generated from 5 measurements. Change measurements → new patterns.

### **4. Cloth Physics**
Blender simulates real fabric behavior:
- Gravity pulls panels down
- Spring constraints pull seams together
- Collision prevents self-intersection
- Result: Natural drape

---

## 🚧 Known Limitations

1. **Single View:** Only uses front image (back is optional)
2. **Simple Patterns:** T-shirt only (no complex garments)
3. **Flat Design:** Assumes design is flat on fabric
4. **No Wrinkles:** Input photo should be unwrinkled
5. **Blender Required:** Steps 5-6 need manual Blender setup
6. **No Real-time:** Full pipeline takes ~5-10 minutes

---

## 🔮 Future Enhancements

1. **Multi-View:** Use front + back + side photos
2. **Garment Types:** Add pants, jackets, dresses
3. **Fabric Physics:** Different materials (cotton, silk, denim)
4. **Auto-Rigging:** Pose-able avatar wearing garment
5. **Web Interface:** Browser-based upload → 3D viewer
6. **AR Export:** Output for AR try-on apps

---

*This document provides a complete technical overview of the 2D to 3D pipeline architecture and implementation.*
