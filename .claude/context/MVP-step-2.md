# MVP Step 2: Product Ingestion & 3D Clothing Asset Generation

**Goal**: Convert 2D product images into 3D clothing assets usable for virtual try-on simulation.

Step 2 sits between:
- **Step 1**: 3D digital twin generation (personalized avatar)
- **Step 2**: 2D images → 3D assets (this document)
- **Step 3**: Virtual try-on experience (simulation + rendering)

---

## What Step 2 Delivers

### Input Data

**2D Product Images**
- Multiple views of a garment (minimum: front + back)
- High-quality product photography
- Clear garment visibility with minimal occlusion

**Metadata**
- Size specification (XS, S, M, L, XL)
- Garment measurements (chest width, length, sleeve length, etc.)
- Color information (can be extracted from image or provided)
- Garment type (T-shirt, for MVP)

### Output: Reusable 3D Clothing Asset

Each processed product produces a complete 3D asset package:

**Pattern Files**
- DXF format (vector-based pattern pieces for precision)
- SVG format (scalable graphics for web preview)
- Edge manifest (named seams for integration with Step 3)

**Texture & Color Data**
- Base color palette (dominant and accent colors)
- Design/graphic extraction (prints, patterns, logos)
- Diffuse texture map for rendering

**Metadata & Configuration**
- Garment measurements and fit specifications
- Panel information and seam layout
- Size-specific geometry (not uniform scaling)
- Fit behavior data (tight/loose/good fit indicators)

**Physics & Simulation Ready**
- Patterns optimized for cloth simulation
- Seam allowances and topology for deformation
- Configuration for gravity, drape, and natural wrinkles

---

## Key Requirements

### 1. Visual Fidelity
- Must preserve color accuracy from source image
- Must retain design/pattern/print details
- Must capture texture characteristics (fabric type appearance)

### 2. Size-Specific Geometry
- Each size (XS, S, M, L, XL) has distinct pattern pieces
- NOT simple uniform scaling of a single template
- Accounts for real-world fit behavior:
  - Tight fit on small bodies → visible strain
  - Loose fit on large bodies → excess fabric draping
  - Good fit → natural silhouette

### 3. Deformability
- Asset must be soft/deformable (like real fabric)
- NOT rigid or hard-shell
- Responds naturally to body shape and gravity
- Shows realistic wrinkles and draping

### 4. Reusability
- Assets stored in searchable product inventory
- Can be used across multiple users and sessions
- Consistent behavior across different avatars

---

## MVP Scope

### Included
- **Garment Type**: T-shirts only
- **Views**: Front and back
- **Sizes**: 5 standard sizes (XS, S, M, L, XL)
- **Asset Count**: ~10-20 t-shirts for validation
- **Physics**: Basic gravity + natural draping (no wind/complex wrinkles)
- **Color & Design**: Full extraction and preservation

### Excluded (Post-MVP)
- Other garment types (pants, dresses, jackets, etc.)
- Accessories (watches, bags, shoes)
- Fully automated image ingestion/quality checking
- Complex fabric simulation (wind resistance, elasticity variation)
- Real-time animation during avatar movement
- Advanced material properties (metallic, transparent fabrics)

---

## User Interaction Flow

1. **Admin/Curator** uploads product images and metadata to inventory system
2. **Step 2 Pipeline** processes images through automated workflow
3. **3D Asset** created and stored in product inventory database
4. **User** browsing virtual closet can select any stored asset
5. **Step 3** places asset on user's digital twin for try-on simulation

---

## Success Criteria

A successful Step 2 implementation must:

- ✓ Extract visual characteristics (color, design, texture) from 2D images
- ✓ Generate size-specific 3D patterns (not uniform-scaled)
- ✓ Produce patterns in DXF format (precision vector format)
- ✓ Create texture maps for visual rendering
- ✓ Generate metadata for fit assessment and seam configuration
- ✓ Store assets in reusable inventory (linked by product_id)
- ✓ Successfully integrate with Step 3 VTO pipeline
- ✓ Process ~10-20 t-shirts with consistent quality
- ✓ Handle multiple product views (front/back) correctly

---

## Integration Points

### With Step 1 (Avatar)
- Uses avatar's body measurements for fit comparison
- Compares garment dimensions against digital twin to assess fit quality

### With Step 3 (VTO)
- Exports pattern data (DXF) for seam creation
- Provides edge manifest for automated seam wiring
- Supplies texture maps for visual rendering
- Includes fit behavior data for feedback messages

---

## MVP Success

Step 2 is complete when:
1. T-shirt ingestion pipeline is stable and repeatable
2. Patterns generate correctly for all 5 sizes
3. Color and design extraction accurate
4. Assets successfully used in Step 3 VTO simulation
5. ~10-20 test garments processed with consistent quality
6. System ready for inventory expansion (post-MVP)

---

*Last updated: 2026-05-16*
