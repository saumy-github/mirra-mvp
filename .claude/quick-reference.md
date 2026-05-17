# Mirra Quick Reference Guide

This document provides quick lookups, checklists, and common references organized by step.

---

## Step 1: Avatar Generation - Quick Reference

### Pre-Work Checklist ✅
- [ ] Read CLAUDE.md (2 min)
- [ ] Read `.claude/current-roadmap.md` (3 min)
- [ ] Read `.claude/architecture/architecture.md` (5 min)
- [ ] Read `.claude/architecture/step_1_avatar.md` (10 min)
- [ ] Check `.claude/repo-rules.md` for coding conventions
- [ ] Verify CLO plugin is built and running

### Command Quick Reference
```bash
# Start avatar generation
python clo_avatar_generation/run_avatar.py

# With sample data
python clo_avatar_generation/run_avatar.py --user-id u_001 --input input.json
```

### File Structure Map
```
clo_avatar_generation/
├── avatar_runtime/
│   ├── step_01_health.py through step_11_save_outputs.py
│   ├── pipeline.py              (main orchestrator)
│   ├── context.py               (Step1Context - state container)
│   ├── client.py                (CLORestClient - REST wrapper)
│   └── field_contract.py        (measurement field definitions)
└── run_avatar.py               (entry point)
```

### Input/Output Locations
- **Input**: MongoDB "measurements" collection or JSON file
- **Output Directory**: `output/<user_id>-<run_number>/`
- **Key Output File**: `<user_id>.avt` (personalized avatar)

### Common Measurement Ranges (Sample Data)
| Measurement | Min | Max | Typical |
|---|---|---|---|
| Height (cm) | 150 | 210 | 170-190 |
| Weight (kg) | 45 | 150 | 60-100 |
| Chest (cm) | 75 | 130 | 90-110 |
| Waist (cm) | 65 | 120 | 75-95 |
| Hip (cm) | 80 | 140 | 95-120 |
| Leg Length (cm) | 60 | 110 | 75-95 |

### Key Files to Modify
- `avatar_runtime/pipeline.py` - Main orchestrator (sequencing)
- `avatar_runtime/context.py` - State management
- `avatar_runtime/step_XX.py` - Individual step logic
- `avatar_runtime/client.py` - CLO plugin communication

### Expected Output Artifacts
```
output/u_001-001/
├── u_001.avt                    (personalized avatar)
├── output.json                  (run summary)
├── error_report.json            (accuracy metrics)
├── clo_payload.json             (measurement spec)
├── import_result.json           (CLO import response)
├── apply_result.json            (CLO apply response)
└── mongo_snapshot.json          (input measurements)
```

### Debugging Quick Reference
| Issue | First Check | Location |
|---|---|---|
| CLO not responding | error_report.json | step_01_health.py results |
| Measurements out of range | mongo_snapshot.json | step_05_normalize_targets.py |
| Low accuracy | error_report.json | step_10_compute_error.py |
| Avatar not exported | output.json status | step_11_save_outputs.py |

---

## Step 2: Product Ingestion - Quick Reference

### Pre-Work Checklist ✅
- [ ] Read CLAUDE.md (2 min)
- [ ] Read `.claude/current-roadmap.md` (3 min)
- [ ] Read `.claude/architecture/architecture.md` (5 min)
- [ ] Read `.claude/architecture/step_2_ingestion.md` (10 min)
- [ ] Check `.claude/repo-rules.md` for coding conventions
- [ ] Prepare input images in `input/` folder

### Command Quick Reference
```bash
# Start product ingestion
python product_ingestion/run_product_ingestion.py

# With sample image
python product_ingestion/run_product_ingestion.py --cloth-id c_001 --size-id M
```

### File Structure Map
```
product_ingestion/
├── segmentation.py              (Stage 1: RMBG + GrabCut)
├── view_selection.py            (Stage 2: CLIP classification)
├── colour_extraction.py          (Stage 3: K-Means colors)
├── design_extraction.py          (Stage 4: edge detection)
├── panel_generation.py           (Stage 5: DXF generation)
├── panels.py                     (DynamicPatternGenerator)
├── panel_export_dxf.py           (DXF export)
├── panel_export_svg.py           (SVG export)
├── garment_measurements.py       (GarmentMeasurements dataclass)
├── garment_router.py             (garment type routing)
├── run_product_ingestion.py      (entry point)
└── input/                        (place cloth images here)
    └── c_001/                    (cloth ID folder)
        ├── image1.jpg
        ├── image2.jpg
        └── ...
```

### Input Structure
```
input/
├── c_001/                       (cloth ID = c_001)
│   ├── front.jpg
│   ├── back.jpg
│   ├── side.jpg
│   └── detail.jpg
├── c_002/
│   └── ...
└── c_NNN/
    └── ...
```

### Output Directory Structure
```
output/c_001-s_m-001/            (cloth_id-size_id-run_number)
├── image_info/
│   ├── base_garment.png         (segmented image)
│   ├── colors.json              (color palette)
│   └── extraction_metadata.json  (extraction params)
├── panels/
│   ├── dxf/
│   │   ├── front_panel.dxf
│   │   ├── back_panel.dxf
│   │   ├── sleeve_left.dxf
│   │   └── sleeve_right.dxf
│   ├── svg/                     (same files in SVG)
│   ├── edge_manifest.json       (edge → index mapping)
│   └── panel_metadata.json      (garment specs)
└── run_summary.json             (processing status)
```

### 5-Stage Pipeline Summary
| Stage | Purpose | Output |
|---|---|---|
| 1: Segmentation | Remove background | base_garment.png |
| 2: View Selection | Classify image view | view_label |
| 3: Color Extraction | K-Means clustering | colors.json |
| 4: Design Extraction | Isolate logos/prints | graphic_diffuse.png |
| 5: Panel Generation | Generate DXF patterns | front/back/sleeve DXF files |

### ⚠️ CRITICAL: Half-Girth Convention
**All width/girth measurements in garment_measurements.py are flat seam-to-seam (half of circumference).**

Examples:
- If chest circumference = 100 cm → half_chest_width = 50 cm (one panel)
- Sleeve full tube = bicep_width × 2
- This is ESSENTIAL for Step 3 seam creation

**If Wrong**: Step 3 seams will be off-size and garment won't fit.

### Key Classes
| Class | Purpose |
|---|---|
| GarmentSegmentor | Image background removal |
| ColourExtractor | K-Means color extraction |
| DesignExtractor | Logo/print detection |
| DynamicPatternGenerator | T-shirt pattern geometry |
| GarmentMeasurements | Measurement dataclass (half-girth convention) |

### Common Tasks
- **Fix segmentation**: Check segmentation.py (RMBG vs GrabCut)
- **Improve colors**: Check colour_extraction.py (K-Means params)
- **Add garment type**: Extend DynamicPatternGenerator in panels.py
- **Debug output**: Check colors.json, edge_manifest.json, panel_metadata.json

### Size ID to Measurements
Mapping (from MongoDB "sizes" collection):
- XS, S, M, L, XL → specific measurements
- Used by DynamicPatternGenerator for panel sizing
- If size_id missing: Pattern generation fails

---

## Step 3: Virtual Try-On - Quick Reference

### Pre-Work Checklist ✅
- [ ] Read CLAUDE.md (2 min)
- [ ] Read `.claude/current-roadmap.md` (3 min)
- [ ] Read `.claude/architecture/architecture.md` (5 min)
- [ ] Read `.claude/architecture/step_3_vto.md` (10 min)
- [ ] Check `.claude/repo-rules.md` for coding conventions
- [ ] Have avatar from Step 1 and patterns from Step 2 ready

### Command Quick Reference
```bash
# Start virtual try-on
python clo_avatar_generation/run_clo_vto.py

# With specific avatar and patterns
python clo_avatar_generation/run_clo_vto.py \
  --avatar output/u_001-001/u_001.avt \
  --patterns output/c_001-s_m-001/panels/dxf/
```

### File Structure Map
```
clo_avatar_generation/native_vto/
├── step_01_health.py through step_11_export_note.py
├── pipeline.py              (main orchestrator)
├── context.py               (PipelineContext - state)
├── client.py                (CLORestClient - REST)
├── seams.py                 (10-seam T-shirt mapping)
├── helpers.py               (utilities)
└── run_clo_vto.py          (entry point)
```

### Input Files Required
```
Avatar:
  output/u_001-001/u_001.avt

Patterns:
  output/c_001-s_m-001/panels/dxf/
    ├── front_panel.dxf
    ├── back_panel.dxf
    ├── sleeve_left.dxf
    └── sleeve_right.dxf

Edge Manifest:
  output/c_001-s_m-001/panels/edge_manifest.json

Pattern Metadata:
  output/c_001-s_m-001/panels/panel_metadata.json
```

### Output Files
```
output/
├── native_vto_report.json       (complete diagnostics)
├── CLO_project_file             (native CLO format)
└── renders/                     (visualization if supported)
```

### 11-Step Pipeline Summary
| Step | Purpose | Key File |
|---|---|---|
| 1 | Health check | step_01_health.py |
| 2 | Create CLO project | step_02_new_project.py |
| 3 | Import avatar | step_03_import_avatar.py |
| 4 | Import patterns | step_04_import_patterns.py |
| 5 | Verify patterns | step_05_verify_patterns.py |
| 6 | Read edges & slots | step_06_read_edges_and_slots.py |
| 7 | Arrange patterns | step_07_arrange_patterns.py |
| 8 | Apply fabric | step_08_apply_fabric.py |
| 9 | Create seams | step_09_create_seams.py |
| 10 | Simulate | step_10_simulate.py |
| 11 | Export | step_11_export_note.py |

### 10-Seam System Quick Reference
```
Shoulder seams (2):
  - Left:  front-left-shoulder ↔ back-left-shoulder
  - Right: front-right-shoulder ↔ back-right-shoulder

Side seams (2):
  - Left:  front-left-side ↔ back-left-side
  - Right: front-right-side ↔ back-right-side

Sleeve tube seams (2):
  - Left:  sleeve-left self-seam
  - Right: sleeve-right self-seam

Armhole seams (4):
  - Front-Left:  front-left-armhole ↔ sleeve-left-armhole
  - Front-Right: front-right-armhole ↔ sleeve-right-armhole
  - Back-Left:   back-left-armhole ↔ sleeve-left-armhole
  - Back-Right:  back-right-armhole ↔ sleeve-right-armhole
```

**Edge names must exactly match edge_manifest.json!**

### Slot System Quick Reference
- Avatar provides predefined slots (e.g., "front", "back", "left_sleeve")
- Pipeline auto-matches patterns to slots by keyword
- If auto-match fails, manual mapping available
- See helpers.py: `find_slot()`, `score_slots()`

### Key Classes
| Class | Purpose |
|---|---|
| PipelineContext | State management |
| CLORestClient | REST API wrapper |
| Seam System | 10-seam T-shirt mapping |
| Helpers | Slot matching, debugging |

### Common Tasks
- **Fix slot matching**: Check helpers.py keyword matching
- **Fix seam creation**: Verify edge_manifest.json edge names
- **Improve render**: Check step_08_apply_fabric.py, materials
- **Optimize simulation**: Check step_10_simulate.py, step count

### Debugging Quick Reference
| Issue | First Check | Location |
|---|---|---|
| Pattern import fails | DXF file exists | step_04_import_patterns.py |
| Slot matching fails | Slot names in report | step_07_arrange_patterns.py |
| Seam creation fails | edge_manifest.json | step_09_create_seams.py |
| Simulation hangs | Step 10 in report | step_10_simulate.py |

---

## All Steps: Common References

### Run Output Folder Locations
| Step | Output Path | Format |
|---|---|---|
| 1 | `output/<user_id>-<run_number>/` | JSON + .avt |
| 2 | `output/<cloth_id>-<size_id>-<run_number>/` | JSON + DXF/SVG |
| 3 | `output/native_vto_report.json` | JSON + CLO project |

### Run Numbering Scheme
- Each step auto-increments run number
- Example: u_001-001, u_001-002, u_001-003 (three separate runs)
- Preserved for debugging and auditing
- Compare outputs across runs using numbers

### Command Execution Rules
✅ **ALWAYS**:
- Run from repo root directory
- Use repo-root relative paths
- Example: `python clo_avatar_generation/run_avatar.py`

❌ **NEVER**:
- Use `python -m` format
- Run from subdirectories
- Example: DON'T use `python -m clo_avatar_generation.run_avatar`

### How to Debug Output
1. Check step status in `output.json` or `native_vto_report.json`
2. Review error files (error_report.json, run_summary.json)
3. Inspect intermediate artifacts (images, DXF files)
4. Add print() statements in relevant step files
5. Run step in isolation with added logging

### Common File Extensions
| Extension | Usage | Step |
|---|---|---|
| .avt | Avatar (binary) | 1 output, 3 input |
| .dxf | Pattern geometry (CAD) | 2 output, 3 input |
| .svg | Pattern vector graphics | 2 output |
| .json | Configuration, output | All |
| .png | Images (segmented, design) | 2 output |
| .csv | Measurements | 1 & 3 input |

### Python Entry Points
| Step | Entry Point | Command |
|---|---|---|
| 1 | run_avatar.py | `python clo_avatar_generation/run_avatar.py` |
| 2 | run_product_ingestion.py | `python product_ingestion/run_product_ingestion.py` |
| 3 | run_clo_vto.py | `python clo_avatar_generation/run_clo_vto.py` |

---

*Last updated: 2026-05-16*
