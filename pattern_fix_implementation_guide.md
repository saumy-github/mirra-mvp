# Pattern Fix Implementation Guide: The "Leaf Shape" Resolution

This guide provides a long-term, scalable, non-hardcoded solution for correcting the structural defects in the generated T-Shirt sleeves, moving from a mathematically malformed "Leaf Shape" back to an anatomically correct "Rectangle + Semicircle (Cap)".

## 1. Problem Diagnosis & Mathematical Breakdown

After auditing `panels.py`, `panel_generation.py`, and `garment_measurements.py`, the core logic mapping edge curves (using Beziers) and executing arc-length matching (the binary search algorithm matching the sleeve cap to the armholes) is **mathematically sound and correctly implemented.** 

The "leaf shape" bug is exclusively caused by a **scalar mapping error**:
- `bicep_width` extracted via `garment_measurements.py` is **18.0 cm**. This represents the *flat* seam-to-seam measurement of a folded sleeve.
- `panels.py` generates the *entire unfolded* sleeve. The correct width of an unfolded sleeve is its full circumference (`18.0 * 2 = 36.0 cm`).
- However, `panels.py` currently computes the width with `sleeve_width = m.bicep_width / 2` (resulting in a tiny **9.0 cm width**).

Because `panels.py` forces a 52cm armhole curve to squeeze onto an incredibly narrow 9cm base width, it destroys the long rectangular underarms and warps the top curve into a towering "leaf" shape to mathematically satisfy the required 52cm curve length.

---

## 2. Proposed Scalable Solution

Our goal is not to "hardcode" a rectangle, but to feed the dynamic bezier-curve generator the correct proportional dimensions so it maps the flat body sizes cleanly into 3D-ready unfolded geometries.

### Phase 1: Fix Sleeve Geometry Scaling
We must update the core pattern generator to correctly unfold the flat bicep width into a full circumference pattern piece.

**File to Edit:** `product_ingestion/panels.py`
- **Method:** `DynamicPatternGenerator._build_cap_pair` and `DynamicPatternGenerator.generate_sleeve`
- **Target Line:** `sleeve_width = m.bicep_width / 2`
- **Correction:** Modify it to `sleeve_width = m.bicep_width * 2`
- **Why this works:** When the width corrects itself to 36.0 cm, the 52 cm cap curve will naturally lower, stretch gracefully across the top (creating the shallow "semicircle" cap), and restore the long rectangular underarm seams exactly as seen in standard physical pattern-drafting.

### Phase 2: Strengthen Data Integrity (Scalability)
To prevent future ingestion pipelines or manual DB entries from passing the wrong scale (e.g., someone typing `36` into the DB assuming it expects full circumference), we must explicitly document the variable intents.

**File to Edit:** `product_ingestion/garment_measurements.py`
- **Action:** Add strong, explicit type/unit hints to the `GarmentMeasurements` dataclass.
- **Documentation Rules:** Explicitly state that `half_chest_width`, `shoulder_width`, and `bicep_width` are strictly *flat seam-to-seam* measurements (half-girths). This creates a scalable standard for any future garments ingested.

---

## 3. Verification Plan

After applying these fixes, the system defaults will behave as follows:

1. **Dry-Run Validation:** Run `run_product_ingestion.py` targeting the `c_001` with `s_001` combination.
2. **Dimension Extraction:** Inspect the newly generated `sleeve_left.svg`.
3. **Target Expected Result:** 
   - Base width must measure exactly 36.0cm.
   - The shape should resemble a standard pattern shape ("Rectangle + Cap").
4. **VTO Output:** Import the resulting DXF/SVG profiles back into CLO3D via the Virtual Try-On flow to observe the physical sewing of the sleeve cap into the armhole mesh. Because the baseline geometry lengths (52cm matched to 49cm armhole with ease) stayed purely dynamic and mathematical, the mesh will simulate without tension lines.
