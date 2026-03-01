# Learning - Plan 002: MVP Step-2 Implementation

## Blender Python API (bpy) for Cloth Simulation

**Category**: API / Framework
**Description**: Blender's Python API (bpy) provides programmatic access to Blender's cloth physics engine. The key components discovered:

- `bpy.ops.mesh` - Mesh operations and modifiers
- Cloth modifier with properties: mass, stiffness, damping, air resistance
- Collision modifiers for digital twin-garment interaction
- Vertex groups for defining seam constraints (sewing edges together)
- Physics simulation cache and bake system

**Context**: Found in `/2D_to_3D_tshirt/minimal_pipeline/step5_blender_sewing.py`
**Resources**:

- Blender Python API docs: [https://docs.blender.org/api/current/]
- Cloth Physics: [https://docs.blender.org/manual/en/latest/physics/cloth/]

**Date**: 2026-01-26

---

## GrabCut Algorithm for Image Segmentation

**Category**: Algorithm / Computer Vision
**Description**: GrabCut is an iterative segmentation algorithm that separates foreground from background:

1. User provides rough rectangle around object
2. Algorithm builds color models for foreground/background
3. Iteratively refines the boundary using graph cuts
4. Works well for garments on simple backgrounds

**Context**: Found in `/2D_to_3D_tshirt/minimal_pipeline/step1_segmentation.py` using OpenCV's implementation
**Resources**:

- Original paper: "GrabCut — Interactive Foreground Extraction"
- OpenCV docs: cv2.grabCut()

**Date**: 2026-01-26

---

## SVG Pattern Generation for Garment Construction

**Category**: Pattern / CAD
**Description**: T-shirt sewing patterns can be programmatically generated as SVG files from measurements. Key insights:

- Patterns are 2D projections of 3D garment pieces
- Bezier curves create smooth armhole and neckline shapes
- Seam allowances added to all edges for sewing
- SVG format allows import into Blender for 3D conversion

**Context**: Found in `/2D_to_3D_tshirt/minimal_pipeline/step4_pattern_generation.py`
**Resources**:

- SVG path commands (M, L, C for move, line, curve)
- Garment pattern drafting principles

**Date**: 2026-01-26

---

## K-Means Clustering for Color Extraction

**Category**: Algorithm / Machine Learning
**Description**: K-means clustering groups similar colors together to find dominant colors in fabric:

- Each pixel is a point in RGB color space
- Algorithm finds K cluster centers (dominant colors)
- Iteratively assigns pixels to nearest cluster
- Cluster sizes indicate color coverage percentage

**Context**: Found in `/2D_to_3D_tshirt/minimal_pipeline/step3_color_extraction.py` using sklearn
**Resources**:

- sklearn.cluster.KMeans documentation
- Color quantization techniques

**Date**: 2026-01-26

---

## Edge Detection for Design Extraction

**Category**: Computer Vision / Image Processing
**Description**: Canny edge detection identifies printed designs on fabric:

- Gaussian blur removes noise
- Gradient calculation finds intensity changes
- Non-maximum suppression thins edges
- Hysteresis thresholding connects edge fragments
- Design areas have more edges than plain fabric

**Context**: Found in `/2D_to_3D_tshirt/minimal_pipeline/step2_design_extraction.py`
**Resources**:

- OpenCV Canny edge detector: cv2.Canny()
- Canny, J., "A Computational Approach To Edge Detection"

**Date**: 2026-01-26

---
