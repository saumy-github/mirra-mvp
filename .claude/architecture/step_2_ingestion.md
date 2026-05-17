# Step 2: Product Ingestion - Detailed Architecture

## Overview

**Step 2** converts 2D product images into reusable 3D garment patterns while preserving color, texture, and fit intent. The pipeline extracts garment geometry and creates CAD files ready for Step 3.

**Input**: 2D product images (front, back views)  
**Output**: 4-piece DXF patterns + edge manifests + color/design metadata  
**Execution**: ~2 minutes per garment  
**Entry Point**: `python product_ingestion/run_product_ingestion.py`

**Key Characteristic**: Step 2 is **independent**—can run anytime, without Step 1 or 3.

---

## 5-Stage Extraction Pipeline

### **Stage 1: Segmentation**
Isolate garment from background and body.

- **Methods**: RMBG-1.4 (preferred) or GrabCut (fallback)
- **Input**: Original product image
- **Process**:
  - RMBG-1.4: Deep learning background removal
  - GrabCut: Morphological operations if RMBG fails
  - Cleanup: Remove noise, fill holes
- **Output**: 
  - `base_garment.png` - Isolated garment with transparency
  - Area metrics (pixel count, bounding box)
- **File**: `segmentation.py`
- **Challenges**: Complex backgrounds, occlusion, extreme angles

### **Stage 2: View Selection**
Classify image into front, back, side, or irrelevant views.

- **Method**: CLIP zero-shot learning (vision-language model)
- **Input**: Segmented garment image
- **Process**:
  - CLIP embeddings for "front view", "back view", "side view", "irrelevant"
  - Cosine similarity scoring
  - Select highest-scoring view
- **Output**: 
  - View label (front/back/side/irrelevant)
  - Confidence score
- **File**: `view_selection.py`
- **Purpose**: Quality control (skip unusable images)

### **Stage 3: Color Extraction**
Extract dominant color palette from garment.

- **Method**: K-Means clustering in LAB color space (perceptually uniform)
- **Input**: Segmented garment image (RGB)
- **Process**:
  - Convert RGB → LAB (perceptual color space)
  - K-Means clustering (k=5-7 typical)
  - Extract dominant colors and percentages
  - Convert back to RGB and HEX codes
- **Output**: 
  - `colors.json` with RGB, LAB, HEX, percentage for each color
  - Primary color defined
- **File**: `colour_extraction.py`
- **Why LAB?**: Perceptually uniform (E vs H not confused)

### **Stage 4: Design Extraction**
Detect and isolate logos, prints, patterns.

- **Method**: Canny edge detection + contour analysis
- **Input**: Segmented garment image
- **Process**:
  - Canny edge detection (threshold tuning)
  - Contour extraction and analysis
  - Filter by size and contrast ratio
  - Crop bounding box around design
  - Validate against thresholds (1% - 80% of garment area)
- **Output**: 
  - `graphic_diffuse.png` - Isolated design texture
  - Coordinates and size
- **File**: `design_extraction.py`
- **Challenges**: Complex prints, subtle patterns, high variance

### **Stage 5: Panel Generation**
Convert segmented garment into 4-piece T-shirt pattern geometry.

- **Method**: Geometry calculation from measurements
- **Input**: 
  - Segmented garment image (for size reference)
  - GarmentMeasurements (from MongoDB "sizes" collection)
  - Size ID (XS, S, M, L, XL, etc.)
- **Process**:
  - Look up garment measurements in MongoDB by size_id
  - Generate 4 panels (front, back, left sleeve, right sleeve)
  - Calculate vertices and edges using measurement specs
  - Export to DXF (CAD format) and SVG (vector)
  - Create edge_manifest.json mapping edges to CLO indices
  - Create panel_metadata.json documenting garment specs
- **Output**:
  - `panels/dxf/front_panel.dxf`, `back_panel.dxf`, `sleeve_left.dxf`, `sleeve_right.dxf`
  - `panels/svg/` - Same files in SVG format
  - `panels/edge_manifest.json` - Edge index mapping for Step 3
  - `panels/panel_metadata.json` - Garment specs and measurements
- **Files**: `panel_generation.py` (orchestrator), `panels.py` (DynamicPatternGenerator)

---

## Key Classes & Data Structures

### **GarmentSegmentor** (segmentation.py)
Handles background removal and garment isolation.

**Methods**:
- `segment_rmbg()` - RMBG-1.4 deep learning segmentation
- `segment_grabcut()` - GrabCut morphological fallback
- `cleanup_mask()` - Noise removal, hole filling
- Returns: Mask image (binary), RGBA garment image, area metrics

### **ViewLabel** (view_selection.py)
Enum for view classification.

**Values**: `FRONT`, `BACK`, `SIDE`, `IRRELEVANT`

### **ColourExtractor** (colour_extraction.py)
Extracts color palette via K-Means.

**Methods**:
- `extract_kmeans()` - Run clustering
- `to_rgb()`, `to_lab()`, `to_hex()` - Color conversion
- Returns: Color palette with RGB, LAB, HEX, percentage

### **DesignExtractor** (design_extraction.py)
Detects and isolates logos/prints.

**Methods**:
- `detect_edges()` - Canny edge detection
- `find_contours()` - Contour analysis
- `validate_design()` - Check against size/contrast thresholds
- Returns: Design RGBA image, coordinates

### **DynamicPatternGenerator** (panels.py)
Generates T-shirt pattern geometry from measurements.

**Key Method**:
- `generate_panels(measurements: GarmentMeasurements) → List[Panel]`
- Returns: 4 panels (front, back, left sleeve, right sleeve) with vertices and edges

### **GarmentMeasurements** (garment_measurements.py)
Dataclass containing all garment sizing parameters.

**Fields**:
- Body measurements: chest, waist, hip, shoulder, armhole, neckline, etc.
- Garment measurements: lengths, widths, sleeve dimensions
- Scale factors and fit parameters
- ⚠️ **CRITICAL**: Uses **half-girth convention** (see below)

---

## Input Data

### **Product Images**
- Location: `input/c_<cloth_id>/`
- Format: PNG, JPG, JPEG
- Multiple views recommended (front, back, side)
- Quality: Clear background, good lighting, visible details

### **Garment Measurements (MongoDB)**
- Collection: `sizes`
- Query: By `size_id` (e.g., "XS", "S", "M", "L", "XL")
- Fields: All measurements needed for pattern generation
- Fallback: JSON file if MongoDB unavailable

### **Size ID Mapping**
- XS, S, M, L, XL (standard sizing)
- Maps to specific measurements in MongoDB
- Used to determine panel dimensions

---

## Output Data

### **Pattern Files**
- **DXF**: `panels/dxf/front_panel.dxf`, `back_panel.dxf`, `sleeve_left.dxf`, `sleeve_right.dxf`
- **SVG**: Same files in vector format
- Purpose: CAD-ready for Step 3 import

### **Edge Manifest** (CRITICAL for Step 3)
- File: `panels/edge_manifest.json`
- Format: Maps named panel edges to CLO geometry indices
- Example:
  ```json
  {
    "front_neck": 0,
    "front_right_shoulder": 1,
    "front_right_armhole": 2,
    ...
  }
  ```
- **Purpose**: Step 3 uses edge names to wire 10-seam system
- ⚠️ **CRITICAL**: Edge names must exactly match Step 3 seams.py expectations

### **Panel Metadata**
- File: `panels/panel_metadata.json`
- Contains: Garment specifications, measurements, fit parameters, generation metadata
- Used by: Step 3 for arrangement and fabric properties

### **Image Information**
- File: `image_info/extraction_metadata.json`
- Contains: Extraction parameters, model versions, segmentation quality metrics
- File: `image_info/base_garment.png`
- Contains: Isolated, segmented garment image

### **Run Summary**
- File: `run_summary.json`
- Contains: Processing status, stage completion, any errors

---

## Measurement Conventions

### ⚠️ **CRITICAL: Half-Girth Rule**

**All width/girth measurements in GarmentMeasurements are flat seam-to-seam (half of circumference).**

**Examples**:
- If chest circumference = 100 cm
  - `half_chest_width` = 50 cm (width of one front panel)
  - Full garment chest = 100 cm (both front + back pieces)

- Sleeve measurements:
  - `bicep_width` = 20 cm flat
  - Sleeve tube width = `bicep_width × 2` = 40 cm full circumference

**Why**: 
- Simplifies pattern generation (flat panel calculations)
- Matches garment construction (panels sewn together)
- Required for Step 3 seam creation to work correctly

**If Wrong**:
- Step 3 seams will be off-size
- Garment won't fit correctly on avatar
- Physics simulation will look wrong

### **Absolute Measurements**
- **Lengths**: Garment length, sleeve length, armhole depth (full, not halves)
- **Openings**: Neck opening, armhole opening (full circumference)

---

## Dependencies

### **Required**
- Input images in `input/` folder
- MongoDB "sizes" collection OR JSON measurements file
- Python dependencies (OpenCV, PIL, scikit-learn, CLIP)
- No CLO plugin required (pure image processing)

### **Data Dependencies**
- Step 2 has no dependencies on Step 1
- Can run anytime, independently
- Does depend on image quality and measurement data

---

## Error Handling & Debugging

### **Common Issues**

**Segmentation Fails**:
- Background too complex or similar to garment
- Solution: Try different segmentation method (RMBG vs GrabCut)
- Check: `base_garment.png` - is garment fully isolated?

**Color Extraction Incomplete**:
- Image too monochrome or too complex
- Solution: Check K-Means parameters, image contrast
- Check: `colors.json` - are all colors extracted?

**Design Extraction Fails**:
- Threshold tuning needed for garment type
- Solution: Adjust Canny thresholds in design_extraction.py
- Check: `graphic_diffuse.png` - is design visible?

**Pattern Generation Fails**:
- Garment measurements missing or wrong format
- Solution: Verify MongoDB "sizes" collection has size_id entry
- Check: `panel_metadata.json` - are measurements present?

**Edge Manifest Incomplete**:
- Edge extraction didn't find all edges
- Solution: Check DXF file is valid, edge detection logic
- Check: `edge_manifest.json` - does it have all expected edges?

### **Debugging Tips**
- Output images (base_garment.png, graphic_diffuse.png) are preserved
- Check JSON files first (colors.json, panel_metadata.json, run_summary.json)
- Run single stage in isolation with added logging
- Inspect DXF files manually with CAD viewer

---

## Garment Types (Current & Future)

### **Currently Implemented**
- **T-Shirt**: 4-piece pattern (front, back, 2 sleeves)

### **Future Support**
- **Jacket**: 4-8 piece pattern (front, back, sleeves, collar, etc.)
- **Pants**: 4-piece pattern (front, back, 2 legs)
- **Dress**: 2-4 piece pattern (bodice, skirt, sleeves)

To extend: Modify `DynamicPatternGenerator` in `panels.py` and `garment_router.py`

---

## Related Documentation

- **High-level**: `.claude/architecture/architecture.md`
- **Quick reference**: `.claude/quick-reference.md` → Step 2 section
- **FAQ**: `.claude/faq.md` → Step 2 section
- **Troubleshooting**: `.claude/troubleshooting.md` → Step 2 section
- **How to start**: `.claude/commands/start-work.md` → Step 2 section
- **Measurement convention**: `.claude/quick-reference.md` → "Half-girth rule"

---

*Last updated: 2026-05-16*