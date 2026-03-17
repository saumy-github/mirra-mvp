# Mirra MVP — Step 2B - 3D Asset Creation Pipeline

This document defines **Step 2B** of the Mirra MVP pipeline - creating **3D clothing assets** from manually curated 2D images and metadata.

**Step 2B sits after Step 2A:**

- **Step 2A -** Manual Product Ingestion (images + metadata)
- **Step 2B -** 3D Asset Generation (this document)
- **Step 3 -** Virtual Try-On Experience

---

## Overview

**Goal -** Convert manually provided 2D t-shirt images and size metadata into realistic 3D clothing assets that maintain proper fit behavior when placed on digital twins.

**Key Principle -** The generated clothing asset should behave like real clothing -

- If a garment is **too small**, it should appear tight/restrictive on the digital twin
- If a garment is **too large**, it should appear loose/baggy on the digital twin
- The asset should **NOT automatically stretch or compress** to perfectly fit every body type

---

## Inputs (From Step 2A)

Step 2A provides manually curated data -

1. **T-shirt Images -**
   - Front view
   - Back view
   - Already classified and organized by a human operator

2. **Metadata File -**
   - Size information (XS, S, M, L, XL)
   - Measurements for each size
   - Fabric type (optional for MVP)
   - Color information (can be extracted or provided)

3. **Organization -**
   - All images properly sorted into directories
   - Naming conventions followed
   - Quality verified manually

---

## Step 2B Pipeline - Three-Stage Process

### Stage 1 - Design Extraction

**Purpose -** Extract visual characteristics from the 2D images

#### Inputs -

- Classified t-shirt images (front/back views)

#### Process -

1. **Color Extraction -**
   - Extract dominant colors from the fabric
   - Identify base color and accent colors
   - Handle patterns/prints if present

2. **Design Pattern Extraction -**
   - Identify graphic elements, logos, prints
   - Extract texture information
   - Segment design areas from plain fabric areas

#### Outputs -

- Color palette data
- Design/pattern masks
- Texture maps for UV application

---

### Stage 2 - Structure Generation

**Purpose -** Create the 3D geometric structure of the t-shirt

#### Inputs-

- T-shirt template (base mesh)
- Size measurements from metadata

#### Process-

1. **Base Template Selection -**
   - Use predefined t-shirt mesh template
   - Template includes -
     - Vertex structure
     - Seam lines
     - UV mapping coordinates

2. **Size-Specific Geometry -**
   - Apply measurements to scale the template
   - Adjust key dimensions -
     - Chest width
     - Shoulder width
     - Sleeve length
     - Body length
   - **Important -** Each size (XS, S, M, L, XL) gets distinct geometry
   - Sizes are **NOT** uniform scalings of each other

3. **Mesh Refinement -**
   - Ensure proper topology for cloth simulation
   - Verify seam alignment
   - Check for mesh quality (no self-intersections)

#### Outputs-

- Size-specific 3D mesh geometry
- Seam line data
- UV coordinates

---

### Stage 3 - Size & Physics Configuration

**Purpose -** Configure the asset to behave realistically when worn by digital twins

#### Inputs

- 3D mesh from Stage 2
- digital twin body measurements (from Step 1)
- Garment size specifications

#### Process

1. **Rigid Base with Limited Physics -**
   - The garment maintains its **original dimensions**
   - Apply basic cloth physics -
     - Gravity (drape behavior)
     - Limited collision response
     - Natural fold/wrinkle patterns
   - **No automatic fitting/stretching** to match digital twin body

2. **Fit Assessment Logic -**
   - Compare garment measurements vs. digital twin measurements
   - Calculate fit gaps -
     - **Negative gap** = too tight (garment smaller than body)
     - **Positive gap** = too loose (garment larger than body)
   - Store fit data with the asset

3. **Visual Behavior Configuration -**
   - **Too Small -**
     - Visible strain/pulling at seams
     - Fabric tension visualization
     - Restricted movement indicators
   - **Too Large -**
     - Loose draping
     - Excess fabric bunching
     - Relaxed silhouette
   - **Good Fit -**
     - Natural drape
     - Comfortable spacing
     - Proper proportions

#### Outputs

- Configured 3D asset with physics properties
- Fit assessment parameters
- Visual behavior rules

---

## Final Output - 3D Clothing Asset

Each processed t-shirt produces a complete 3D asset package -

### Asset Components -

1. **Geometry File -**
   - 3D mesh (.obj, .fbx, or compatible format)
   - Size-specific measurements embedded

2. **Texture Maps -**
   - Diffuse/albedo map (colors and patterns)
   - Normal map (fabric texture detail)
   - Optional - roughness/metalness maps

3. **Physics Configuration -**
   - Cloth simulation parameters
   - Collision properties
   - Rigidity constraints

4. **Metadata JSON -**

   ```json
   {
     "garment_id": "tshirt_001",
     "size": "M",
     "measurements": {
       "chest": 100,
       "shoulder": 45,
       "length": 72,
       "sleeve": 20
     },
     "color_palette": ["#FFFFFF", "#000000"],
     "has_design": true,
     "fabric_type": "cotton"
   }
   ```

5. **Fit Behavior Profile -**
   - Recommended digital twin body ranges
   - Fit warnings/messages
   - Visual behavior flags

---

## Key Requirements for Realistic Fit

### 1. No Auto-Fitting -

- The asset **must not** automatically deform to fit any body type
- Size mismatches should be **visually apparent**
- Users should see realistic consequences of size choices

### 2. Visual Feedback System -

When rendered on an digital twin -

- **Clear visual cues** for fit issues -
  - Too tight - visible pulling, fabric stress
  - Too large - excess fabric, loose hang
  - Good fit - natural drape, comfortable appearance

### 3. Size-Appropriate Messages -

The system should generate user-facing messages -

- "This size may be too small for your measurements"
- "This garment appears to have a loose fit on you"
- "This size looks like a good match"

### 4. Measurement-Based Logic -

- Compare garment dimensions to digital twin body measurements
- Use industry-standard fit tolerances -
  - Chest - 2-4 cm ease for good fit
  - Length - proportional to torso height
  - Shoulders - ±2 cm tolerance

---

## MVP Scope (Strict Limits)

### Included -

- **Garment type -** T-shirts only
- **Views -** Front and back
- **Sizes -** XS, S, M, L, XL (5 standard sizes)
- **Asset count -** ~10-20 t-shirts for initial testing
- **Physics -** Basic gravity + drape (no wind, complex wrinkles)

### Excluded (Post-MVP) -

- Automated image ingestion/classification
- Complex fabric simulation (wind, dynamic movement)
- Other garment types (pants, dresses, jackets)
- Accessories
- Real-time cloth deformation during digital twin movement
- Advanced material properties (elasticity, stiffness variation)

---

## Success Criteria

A successful Step 2B implementation must -

1. ✓ Generate visually accurate 3D assets from 2D images
2. ✓ Preserve color and design fidelity from source images
3. ✓ Create size-distinct geometries (not just scaled copies)
4. ✓ Produce assets that maintain rigid sizing (no auto-fit)
5. ✓ Enable visual identification of fit issues
6. ✓ Store reusable assets in inventory database
7. ✓ Process ~10-20 t-shirts for MVP validation

---

## Next Steps

After Step 2B completion -

- Assets ready for **Step 3 - Virtual Try-On**
- User can select from inventory
- System places asset on digital twin (Step 1)
- Fit assessment + visual feedback provided
- User sees realistic try-on result
