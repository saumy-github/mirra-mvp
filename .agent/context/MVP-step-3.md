# Mirra MVP — Step 3: Try-On Engine (VTO Integration)

This document defines **Step 3** of the Mirra MVP pipeline: **visually combining** the user’s avatar (Step 1) with a selected clothing asset (Step 2) to render a realistic try-on result.

---

## Step 3 — The Try-On Engine (Core Tech)

### Goal
Visually merge the **cloth asset** with the **avatar** to demonstrate **fit + style**.

---

## Owner
- **Joint Effort** (integration work spanning avatar + asset + rendering)

---

## Inputs
- **Avatar_ID** — the user’s persisted 3D body/avatar (from Step 1)
- **Asset_ID** — the selected clothing asset (from Step 2)

---

## Outputs
- A **visual rendering (3D Scene)** showing the cloth **draped onto** the avatar  
  (the user sees the final try-on visualization)

---

## Core Workflow (Integration)
**Action:** Combine the **Flexible Asset (Step 2)** onto the **Custom Avatar (Step 1)**  
**Result:** A visual simulation where the cloth “drapes” onto the body, showing how that *specific size* fits that *specific user*.

---

## Visualization Methods

### 1) Avatar Mode (Primary for MVP)
- **Warp the product image** to fit the **3D avatar mesh coordinates**
- Technique: **UV mapping** onto avatar/garment proxy mesh

### 2) Live / Camera Mode (Optional for MVP)
- If implemented, use **2D overlays** on a live camera feed:
  - User stands still
  - Clothing image overlays like a **Snapchat-style filter**
- Constraint from doc:
  - For video, use **front-only 2D models**
  - Less movement; user stands still

---

## Fit Visualization Requirements

### Fit Visualization (Must Show Size ↔ Body Interaction)
The system must visually represent how the chosen cloth size interacts with the user’s body shape:

- **Small size on large avatar** → looks **tight / stretched**
- **Large size on small avatar** → looks **loose / relaxed**
- Also supports signals like:
  - “tightness”
  - “sleeve length”
  - (Version 2 feature, but groundwork starts here)

### Fit Accountability (Groundwork Begins in MVP)
- The engine must compare:
  - **User measurements** vs **product size chart**
- Purpose:
  - Visually encode fit differences (tightness / length) instead of only showing a static overlay

---

## Layering Rules

### MVP Layering Scope
- MVP limited to **single layer at a time**
  - OR standard separation: **Top + Bottom**
- No complex stacking (e.g., jacket on shirt) in MVP

### Future Scope (Layering + Motion)
- Multi-layering:
  - Shirt + Sweater + Jacket
- Real-time movement/animation of avatar wearing clothes

---

## Key Product Decisions (Step 3 Implications)

### Target Market
- **India**

### Sizing Policy
- Do **not** rely on letter sizes (S/M/L), because “M” varies widely by brand
- Prefer:
  - **numeric sizes** and/or
  - **actual tape measurements**

### Input Form Switch (Planned UX)
- Toggle in the user input form:
  - **“Most comfortable cloth size used”** vs **“Actual measurement”**

### MVP Input Rules
- Accept measurements **only in inches** (no unit toggle)
- Treat inputs as **ideal** (no sanity checks / validation for MVP)

### Future Validation
- Add mismatch checks (examples):
  - “Chest too large for weight/height”
  - other anomaly detection rules

---

## Summary (What Step 3 Must Deliver for MVP)
- A working **Try-On Engine** that:
  - Takes **Avatar_ID + Asset_ID**
  - Produces a **3D scene rendering** of cloth on avatar
  - Visually communicates **fit differences** (tight vs loose)
- MVP supports **single-layer** try-on with a clean path to future:
  - multi-layering
  - live camera overlays
  - movement/animation
  - stronger measurement validation
