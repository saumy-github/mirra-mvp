j# Mirra Architecture - High-Level Overview

## System Overview Diagram

```
USER MEASUREMENTS (height, weight, chest, waist, hip, etc.)
        ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Avatar Generation (clo_avatar_generation/)      │
│ • Fetch measurements from MongoDB/JSON                  │
│ • Load base avatar template                             │
│ • Apply custom measurements via morphing                │
│ • Validate accuracy, export .avt                        │
└─────────────────────────────────────────────────────────┘
        ↓
PERSONALIZED 3D AVATAR (.avt file)
        ↓
        
PRODUCT IMAGE (2D photo)
        ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Product Ingestion (product_ingestion/)          │
│ • Segment garment from background                       │
│ • Classify image view (front/back/side)                 │
│ • Extract dominant colors & design/logos                │
│ • Generate 4-piece T-shirt pattern (DXF)                │
│ • Create edge_manifest.json for Step 3                  │
└─────────────────────────────────────────────────────────┘
        ↓
GARMENT PATTERNS (DXF files) + EDGE MANIFESTS
        ↓
        
AVATAR + PATTERNS + MANIFESTS
        ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Virtual Try-On (clo_avatar_generation/)         │
│ • Import avatar into CLO project                        │
│ • Import patterns and verify geometry                   │
│ • Position patterns on avatar (slot arrangement)        │
│ • Create 10-seam system to sew patterns together        │
│ • Run 150-step physics simulation                       │
│ • Export final rendered try-on                          │
└─────────────────────────────────────────────────────────┘
        ↓
FINAL VIRTUAL TRY-ON (physics-simulated garment on body)
```

## Key Principle

**Each step is independent until Step 3**, which combines outputs from both Step 1 and Step 2.
- Step 1 and Step 2 can run in parallel
- Step 3 requires both to be complete

---

## Core Infrastructure Components

### **clo_workspace/** - REST API Plugin Bridge

**Purpose**: Provides REST API endpoints to CLO 3D application. All steps communicate through this plugin, not direct file access.

**Key Files**:
- `build_plugin.py` - Builds Windows and macOS plugin versions
- `plugin_contract.json` - Defines 27 REST API endpoints
- `windows/` - Windows plugin source code
- `mac/` - macOS plugin source code
- `versions/` - Release metadata and version history

**API Summary**:
- 14 read endpoints (health, capabilities, status, avatar state, patterns, arrangement info)
- 13 write endpoints (new project, import avatar, import patterns, create seams, simulate, export)

**Critical**: Plugin must be built and running before Steps 1-3 can execute.

**How It's Used**:
- Step 1: `CLORestClient` in `avatar_runtime/client.py` calls plugin endpoints for avatar import/measurement application
- Step 3: `CLORestClient` in `native_vto/client.py` calls plugin endpoints for pattern operations, seam creation, simulation

---

### **mirra_measurements/** - Measurement Data & Utilities

**Purpose**: Shared measurement data structures, validation, and utilities used across all steps.

**Key Concepts**:
- User body measurements (height, weight, circumferences, lengths)
- Garment measurements (sizing, fit dimensions, panel geometry)
- Measurement field definitions and validation rules
- Conversion between measurement sources (MongoDB, JSON, CSV)

**How It's Used**:
- **Step 1**: Input data (user measurements) come from here
- **Step 2**: Garment measurements for sizing (from MongoDB "sizes" collection)
- **Step 3**: Optional measurement application to avatar

**Critical Detail**: **Half-Girth Convention**
- All width/girth measurements in garment specs are **flat seam-to-seam** (half of full circumference)
- E.g., if chest circumference = 100 cm, half_chest_width = 50 cm (one panel width)
- This is essential for Step 2 → Step 3 integration. Wrong convention breaks seams.

---

### **utils/** - Shared Utilities

**Purpose**: Common helper functions and utilities used across all steps.

**Typical Contents** (depending on what's implemented):
- File I/O operations (reading/writing JSON, DXF, AVT)
- Path and directory management
- Logging and debug utilities
- Data transformation and validation helpers
- Constants and configuration

**How It's Used**: Imported by step pipelines for common tasks

---

## 3-Step Pipeline Details

For detailed information about each step, see:
- **Step 1 Details**: Read `.claude/architecture/step_1_avatar.md`
- **Step 2 Details**: Read `.claude/architecture/step_2_ingestion.md`
- **Step 3 Details**: Read `.claude/architecture/step_3_vto.md`

This document stays high-level; detailed pipeline info is in step-specific files.

---

## Key Interfaces & Data Formats

### **CLO REST API**
- All steps use `CLORestClient` to communicate with CLO 3D
- Endpoints defined in `clo_workspace/plugin_contract.json`
- Timeout handling and retry logic required for stability

### **Avatar File Format (.avt)**
- Binary format used by CLO 3D
- Step 1 exports modified avatar as .avt file
- Step 3 imports .avt file for VTO

### **Pattern Files (DXF/SVG)**
- Step 2 exports garment patterns as DXF (CAD format) and SVG (vector)
- Step 3 imports DXF files for arrangement and seaming
- DXF contains actual geometry; SVG is for visualization

### **Edge Manifests (JSON)**
- Step 2 generates `edge_manifest.json` mapping panel edges to CLO geometry indices
- Step 3 uses edge names to wire 10-seam system
- Critical: Edge names must match exactly or seam creation fails

### **Measurement Bridge Formats**
- **CSV Format**: Traditional measurement template (Step 1 & 3)
- **AVT Patch**: Binary patch applied to avatar file
- **Properties JSON**: Avatar property assignments (newer method)

---

## Data Structures & State Management

### **Step 1 State: Step1Context**
- Location: `avatar_runtime/context.py`
- Tracks: user_id, run_dir, measurements, CLO payloads, import/apply results, error metrics
- Lifecycle: Created at start, populated throughout 11 steps, output at end

### **Step 3 State: PipelineContext**
- Location: `native_vto/context.py`
- Tracks: avatar_path, patterns_dir, project_dir, loaded patterns, slots, seams, arrangement results
- Lifecycle: Created at start, modified through 11 steps, output at end

---

## Legacy Folders (Do Not Modify)

The following folders at repo root are **no longer maintained** and should not be modified:

- **avatar_generation/** - Superseded by `clo_avatar_generation/avatar_runtime/`
- **vto/** - Superseded by `clo_avatar_generation/native_vto/`
- **research/** - Archived learning/exploration
- **random/** - Scratch work and experiments
- **models/** - If not actively used, consider archived

These folders may contain old code or documentation. Use current folders in `clo_avatar_generation/` and `product_ingestion/` instead.

---

## Measurement Conventions

### **Body Measurements** (User Input for Step 1)
- **Height**: Total body height in cm
- **Weight**: Body weight in kg
- **Circumferences**: Chest, waist, hip measured around body at specific points
- **Lengths**: Arm, leg, torso lengths

### **Garment Measurements** (Step 2 for Pattern Sizing)
- **Half-Girth Convention**: All width/girth fields are flat seam-to-seam
  - Example: chest_width = chest_circumference ÷ 2 (width of one front panel)
  - Sleeve_width = bicep_width × 2 (full tube, not flat)
- **Absolute Measurements**: Length, depth, opening sizes are full measurements
- **Rationale**: Flat measurements simplify pattern generation and seam creation

**⚠️ CRITICAL**: Misalignment between Step 2 and Step 3 measurement conventions breaks seam creation. See quick-reference.md for details.

---

## Dependencies Between Steps

```
Step 1 (Avatar)          Step 2 (Ingestion)
     ↓                          ↓
     └──────────────┬───────────┘
                    ↓
              Step 3 (VTO)
                    ↓
            Virtual Try-On
```

- **Step 1 ← Step 2**: Independent. Can run in parallel.
- **Step 3 ← Step 1**: Requires avatar (.avt) from Step 1
- **Step 3 ← Step 2**: Requires patterns (DXF) and edge_manifest.json from Step 2
- **Step 3 → Output**: Cannot produce VTO without both inputs

---

## Output Artifact Structure

### **Step 1 Outputs** (in `output/<user_id>-<run_number>/`)
- `<user_id>.avt` - Modified avatar file
- `output.json` - Complete run summary
- `error_report.json` - Accuracy metrics
- `input.json`, `clo_payload.json` - Input specifications
- `import_result.json`, `apply_result.json` - Step results

### **Step 2 Outputs** (in `output/<cloth_id>-<size_id>-<run_number>/`)
- `panels/dxf/` - DXF pattern files (front, back, sleeves)
- `panels/svg/` - SVG pattern files (same)
- `panels/edge_manifest.json` - Edge index mapping for Step 3
- `panels/panel_metadata.json` - Garment specs and measurements
- `image_info/` - Segmented image, colors, extraction metadata
- `run_summary.json` - Processing status

### **Step 3 Outputs** (in `output/`)
- `native_vto_report.json` - Complete VTO results and diagnostics
- CLO project file (internal CLO representation)
- Render outputs (format TBD - images, video, etc.)

---

## Critical Interfaces Summary

| Interface | Format | Used By | Purpose |
|-----------|--------|---------|---------|
| Avatar | .avt binary | Step 1 → Step 3 | Body representation |
| Patterns | DXF/SVG | Step 2 → Step 3 | Garment geometry |
| Edge Manifest | JSON | Step 2 → Step 3 | Seam wiring index |
| Measurements | CSV/JSON | Step 1 input | Body specs |
| CLO REST API | HTTP JSON | All steps | Plugin communication |
| Run Summary | JSON | Each step | Step results and metadata |

---

## For More Information

**Architecture Deep-Dives**:
- Step 1 details: `.claude/architecture/step_1_avatar.md` (11-step pipeline, classes, I/O)
- Step 2 details: `.claude/architecture/step_2_ingestion.md` (5-stage pipeline, measurement convention)
- Step 3 details: `.claude/architecture/step_3_vto.md` (11-step assembly, 10-seam system)

**Business Context**:
- Project vision: `.claude/project-context.md`
- Requirements: `.claude/context/` folder

**Practical Guides**:
- Quick reference: `.claude/quick-reference.md`
- How to start work: `.claude/commands/start-work.md`
- Troubleshooting: `.claude/troubleshooting.md`

---

*Last updated: 2026-05-16*
