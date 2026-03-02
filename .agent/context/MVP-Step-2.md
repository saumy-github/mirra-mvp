# Mirra MVP — Step 2: 2D → 3D Clothing Asset Pipeline (Product + Asset Ingestion)

This document defines **Step 2** of the Mirra MVP pipeline: converting **2D garment images** into **assets usable for virtual try-on**.  
Step 2 sits between:

- **Step 1:** 3D digital twin Generation
- **Step 2:** 2D Clothing → 3D/usable asset (this document)
- **Step 3:** Render + Try-on Experience for the user

---

## Step 2A — Product Ingestion Engine (Version 1)

**Goal:** Populate the **Virtual Closet** quickly _without_ full AI automation yet.

### 1. Sourcing Strategy (API Scraping)

- Build a targeted scraper for selected seller websites (e.g., **Amazon**, brand sites) to fetch:
  - Product images
  - Product metadata (where available)

### 2. Sort Logic (Image Classification Scripts)

- Write scripts to classify downloaded images into:
  - **Front View**
  - **Back View**
  - **Model / Mannequin**
- Purpose:
  - Ensure clean source images for asset creation
  - Avoid low-signal/duplicate/irrelevant images

### 3. Asset Processing (Manual / Semi-Auto)

#### Phase 1: Curated Manual Catalog

- Start with a curated set of **~50–100** garments (e.g., T-shirts, dresses)
- Manually verify:
  - Image clarity
  - Correct angle coverage
  - No heavy occlusions / extreme poses
  - Adequate lighting and texture visibility

#### MVP 2D-to-3D Logic (Baseline)

- For MVP, **do not** build full cloth physics conversion.
- Use **basic texture mapping**:
  - Map 2D garment imagery onto the digital twin/garment proxy as textures
  - Treat as the starting point before complex deformable cloth pipelines

---

## Step 2B — 3D Asset Ingestion (MPS Task)

**Goal:** Build a scalable **Virtual Inventory** of clothing assets so users can pick from a catalog without recreating assets each time.

### Inputs

- **2D Images:** Multiple views of a garment (minimum: **Front + Back**)
  - Source can be anything for MVP (scraped / manual / brand-provided)
- **Metadata:**
  - Size: **XS, S, M, L, XL**
  - Fabric / texture type
  - Color

### Outputs

- A **3D asset file** compatible with the digital twin/try-on system
- Stored inside a **Product Inventory database**

### Key Requirements

#### 1. Visual Fidelity

- Must retain from 2D sources:
  - **Color**
  - **Texture / prints / patterns**

#### 2. Flexibility / Deformability

- Asset **must be deformable** (fabric-like), **not** a rigid shell
- Rationale:
  - Same garment behaves differently across different bodies

#### 3. Sizing Logic

- Must account for real-world sizing behavior:
  - XS vs XL should not be identical with uniform scaling only
- Expected behavior examples:
  - Tight/stretching on larger body
  - Looser drape on smaller body
- Implementation options (MVP acceptable):
  - Distinct assets per size **OR**
  - Single base asset + **size-specific scaling parameters**

### MVP Scope (Strict)

- Clothing only:
  - **Upper wear**
  - **Lower wear**
- Keep the asset library small but consistent and testable.

---

## Future Scope (Post-MVP)

- Expand inventory types:
  - Accessories (watches, bags)
  - Makeup
  - Footwear
- Advanced cloth physics:
  - Gravity, wind
  - Fabric weight + stiffness behavior
- More automation:
  - Fully automated scraping + filtering
  - Automated 2D → 3D conversion pipeline (reduced manual verification)

---

## Summary (What Step 2 Must Deliver for MVP)

- A working **Product Ingestion Engine (V1)** to populate a Virtual Closet fast
- A repeatable **Asset Ingestion workflow** that produces:
  - Visually correct clothing assets
  - Flexible/deformable behavior
  - Size-aware results
- A stored **Product Inventory** so assets are reusable across users and sessions
