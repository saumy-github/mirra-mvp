# Getting Started: How to Begin Work on Mirra

This guide explains how to start work on any part of the Mirra MVP pipeline.

---

## ⚠️ CRITICAL: Read Step-Specific Architecture First

Before starting ANY work on Step 1, 2, or 3, **read architecture files for your step only**.

**Why?** To save context tokens and avoid loading unnecessary information.

**How?**:
1. Read `.claude/architecture/architecture.md` (high-level overview - always)
2. Read `.claude/architecture/step_<N>_<name>.md` (your step only - skip others)

**Example**:
- Working on Step 1? Read `architecture.md` + `step_1_avatar.md` ✅
- Skip `step_2_ingestion.md` and `step_3_vto.md` ❌

---

## Before Starting ANY Work

Follow this checklist (2-3 minutes total):

1. ✅ Read `CLAUDE.md` at repo root (2 min) - Quick index
2. ✅ Check `.claude/current-roadmap.md` (3 min) - What's the project status?
3. ✅ Read `.claude/repo-rules.md` (5 min) - How we code here
4. ✅ Read `.claude/architecture/architecture.md` (5 min) - High-level system overview
5. ✅ Read `.claude/architecture/step_<N>_<name>.md` (10 min) - Your specific step
6. ✅ Scan `.claude/quick-reference.md` → Your step section (2 min) - Quick lookups

**Total**: ~27 minutes of reading before coding. Worth it for context.

---

## Working on Step 1: Avatar Generation

### Entry Point
```bash
python clo_avatar_generation/run_avatar.py
```

### Quick Steps
1. ✅ Read `.claude/architecture/step_1_avatar.md` (detailed pipeline info)
2. ✅ Review `avatar_runtime/pipeline.py` (main orchestrator, sequencing logic)
3. ✅ Review `avatar_runtime/context.py` (Step1Context data structure)
4. ✅ Identify which of 11 steps needs modification (step_02 through step_11)
5. ✅ Review relevant `step_*.py` file
6. ✅ Make changes (follow repo-rules.md conventions)
7. ✅ Test with sample measurements
8. ✅ Verify `output/<user_id>-<run_number>/output.json` shows success

### Folder Structure
```
clo_avatar_generation/
└── avatar_runtime/
    ├── step_01_health.py ................. CLO health check
    ├── step_02_run_setup.py .............. Create output dir
    ├── step_03_fetch_measurements.py ..... Load measurements
    ├── step_04_resolve_base_avatar.py .... Select template
    ├── step_05_normalize_targets.py ...... Validate measurements
    ├── step_06_build_payloads.py ......... Create CLO payloads
    ├── step_07_import_base_avatar.py ..... Load into CLO
    ├── step_08_apply_measurements.py ..... Apply morphing
    ├── step_09_readback.py ............... Verify applied
    ├── step_10_compute_error.py .......... Calculate accuracy
    ├── step_11_save_outputs.py ........... Export .avt
    ├── pipeline.py ........................ Orchestrator (runs 11 steps)
    ├── context.py ........................ Step1Context dataclass
    ├── client.py ......................... CLORestClient REST wrapper
    └── field_contract.py ................. Measurement field definitions
```

### Common Tasks

**Debugging avatar morphing**:
- File: `step_08_apply_measurements.py`
- Check: CLO REST API `/import-avatar-measurements` response

**Improving accuracy**:
- File: `step_10_compute_error.py`
- Check: `error_report.json` for per-measurement accuracy metrics

**Changing base template**:
- File: `step_04_resolve_base_avatar.py`
- Modify: Template selection logic, file paths

**Adding new measurement field**:
- File: `avatar_runtime/field_contract.py`
- Update: Field definitions, validation rules, required fields

### Testing
- Use sample measurements from `.claude/quick-reference.md` Step 1 section
- Run: `python clo_avatar_generation/run_avatar.py --user-id u_test --input test_measurements.json`
- Check: `output/u_test-*/output.json` for success status
- Verify: `error_report.json` for accuracy metrics
- Inspect: `.avt` file generated

### Success Criteria
- ✅ `output.json` shows all 11 steps completed
- ✅ `.avt` file exists in output folder
- ✅ `error_report.json` shows <5% accuracy error
- ✅ No CLO errors in `import_result.json`, `apply_result.json`

---

## Working on Step 2: Product Ingestion

### Entry Point
```bash
python product_ingestion/run_product_ingestion.py
```

### Quick Steps
1. ✅ Read `.claude/architecture/step_2_ingestion.md` (detailed 5-stage pipeline)
2. ✅ Review `panel_generation.py` (orchestrator, stage sequencing)
3. ✅ Review `panels.py` (DynamicPatternGenerator, pattern geometry)
4. ✅ Understand which of 5 stages needs modification:
   - Stage 1: `segmentation.py`
   - Stage 2: `view_selection.py`
   - Stage 3: `colour_extraction.py`
   - Stage 4: `design_extraction.py`
   - Stage 5: `panel_generation.py`, `panels.py`, DXF/SVG export
5. ✅ Make changes
6. ✅ Test with sample image
7. ✅ Verify output folder contains DXF files + edge_manifest.json

### Folder Structure
```
product_ingestion/
├── run_product_ingestion.py ........... Entry point
├── panel_generation.py ............... Orchestrator (5 stages)
├── segmentation.py ................... Stage 1: Background removal
├── view_selection.py ................. Stage 2: CLIP classification
├── colour_extraction.py .............. Stage 3: K-Means colors
├── design_extraction.py .............. Stage 4: Edge detection
├── panels.py ......................... DynamicPatternGenerator
├── panel_export_dxf.py ............... DXF export + edge manifest
├── panel_export_svg.py ............... SVG export
├── garment_measurements.py ........... GarmentMeasurements dataclass
├── garment_router.py ................. Garment type routing
└── input/ ............................ Place input images here
    └── c_<cloth_id>/
        ├── image1.jpg
        └── image2.jpg
```

### Common Tasks

**Fixing image segmentation**:
- File: `segmentation.py`
- Check: `base_garment.png` in output (is garment isolated?)
- Try: RMBG-1.4 vs GrabCut methods

**Improving color extraction**:
- File: `colour_extraction.py`
- Check: `colors.json` in output (are colors extracted?)
- Adjust: K-Means parameters (k value)

**Adding new garment type (jacket, pants)**:
- File: `panels.py` (extend DynamicPatternGenerator)
- Also: `garment_router.py` (add type detection)
- Note: Requires new panel topology geometry

**Understanding edge_manifest.json**:
- File: `panel_export_dxf.py` (creates edge manifest)
- Purpose: Maps edge names → CLO indices (needed for Step 3)

### Testing
- Prepare test images in `input/c_test/`
- Run: `python product_ingestion/run_product_ingestion.py --cloth-id c_test --size-id M`
- Check: `output/c_test-s_m-*/panels/dxf/` for DXF files
- Verify: `edge_manifest.json` created
- Inspect: `colors.json`, `base_garment.png`, DXF files visually

### Success Criteria
- ✅ DXF files generated (front, back, sleeves)
- ✅ `edge_manifest.json` created with edge mappings
- ✅ `panel_metadata.json` contains garment measurements
- ✅ `base_garment.png` shows properly segmented garment
- ✅ `colors.json` has color palette extracted
- ✅ `run_summary.json` shows all 5 stages completed

### ⚠️ CRITICAL: Half-Girth Convention
**All width/girth measurements must be flat seam-to-seam (half of circumference).**

- Example: chest_width = chest_circumference ÷ 2
- This is ESSENTIAL for Step 3 seam creation to work
- See `.claude/quick-reference.md` Step 2 section for details

---

## Working on Step 3: Virtual Try-On

### Entry Point
```bash
python clo_avatar_generation/run_clo_vto.py
```

### Quick Steps
1. ✅ Read `.claude/architecture/step_3_vto.md` (detailed 11-step assembly)
2. ✅ Review `native_vto/pipeline.py` (main orchestrator)
3. ✅ Review `native_vto/seams.py` (10-seam T-shirt mapping - CRITICAL)
4. ✅ Identify which of 11 steps needs modification
5. ✅ Make changes
6. ✅ Test with avatar from Step 1 and patterns from Step 2
7. ✅ Verify `output/native_vto_report.json` shows success

### Folder Structure
```
clo_avatar_generation/native_vto/
├── step_01_health.py ................. CLO health check
├── step_02_new_project.py ............ Create CLO project
├── step_03_import_avatar.py .......... Load avatar
├── step_04_import_patterns.py ........ Load patterns
├── step_05_verify_patterns.py ........ Validate geometry
├── step_06_read_edges_and_slots.py ... Extract metadata
├── step_07_arrange_patterns.py ....... Position on avatar
├── step_08_apply_fabric.py ........... Assign materials
├── step_09_create_seams.py ........... Wire 10 seams
├── step_10_simulate.py ............... Physics simulation
├── step_11_export_note.py ............ Export results
├── pipeline.py ........................ Orchestrator
├── context.py ........................ PipelineContext dataclass
├── client.py ......................... CLORestClient wrapper
├── seams.py .......................... 10-seam mapping (CRITICAL!)
└── helpers.py ........................ Slot matching, utilities
```

### Common Tasks

**Fixing slot matching**:
- File: `step_07_arrange_patterns.py`, `helpers.py`
- Check: Available slots from step_06 output
- Try: Manual slot mapping if auto-match fails

**Fixing seam creation**:
- File: `step_09_create_seams.py`, `seams.py`
- Check: `edge_manifest.json` edge names vs `seams.py` expected names
- Verify: All 10 seams defined and wired correctly
- ⚠️ CRITICAL: Edge name mismatches cause seam creation to fail

**Improving render quality**:
- File: `step_08_apply_fabric.py`
- Check: Material properties, colors, textures
- Adjust: Lighting, camera angle parameters

**Optimizing simulation**:
- File: `step_10_simulate.py`
- Reduce: Step count (default 150) if timeout
- Adjust: Fabric properties (stiffness, weight)
- Enable: Early termination on convergence

### Testing
- Prepare: Avatar from Step 1 (`<user_id>.avt`)
- Prepare: Patterns from Step 2 (DXF folder + edge_manifest.json)
- Run: `python clo_avatar_generation/run_clo_vto.py --avatar <path> --patterns <path>`
- Check: `output/native_vto_report.json` for step-by-step results
- Verify: All 11 steps completed
- Inspect: VTO render output

### Success Criteria
- ✅ All 11 steps completed successfully
- ✅ All 10 seams created (step_09 output)
- ✅ Physics simulation completed (step_10 output)
- ✅ `native_vto_report.json` shows success
- ✅ CLO project file generated
- ✅ Render output available

### ⚠️ CRITICAL: 10-Seam System
**Seam wiring must exactly match edge names in edge_manifest.json.**

10-seam configuration:
- 2 shoulder seams
- 2 side seams
- 2 sleeve tube seams (underarm)
- 4 armhole seams (sleeves to front/back)

See `.claude/quick-reference.md` Step 3 section for seam details.

---

## Adding a New Feature

### Process

1. **Understand scope**: Which step(s) does it affect?
2. **Check constraints**:
   - Review `.claude/repo-rules.md` (coding standards)
   - Check `.claude/current-roadmap.md` (existing priorities)
   - Check `.claude/project-context.md` (MVP constraints)
3. **Create plan**: Use 3-phase workflow
   - Discussion phase: Explore options
   - Planning phase: Create detailed plan (see `.agent/plans/`)
   - Execution phase: Implement per plan
4. **Code review checklist**:
   - ✅ Follows naming conventions (snake_case)
   - ✅ Uses repo-root relative paths (NOT `python -m`)
   - ✅ Doesn't modify `.agent/` or `.claude/` without explicit request
   - ✅ Keeps changes scoped to task
   - ✅ Tests locally before considering done
   - ✅ Preserves existing code style/formatting
5. **Create commit**: With clear message describing change

### Scope Example
- **Small change**: Single step file modification → Direct implementation
- **Medium change**: Multi-file modification → Create plan first
- **Large change**: New feature across steps → Full planning + discussion

---

## Debugging a Problem

### Which Step Is Failing?

1. **Check output folder**: Does output/<...>/ exist?
2. **Check status JSON**: `output.json` or `native_vto_report.json`
3. **Identify failing step**: JSON lists each step's success/failure

### Step 1 Debugging

1. ✅ Check `.claude/troubleshooting.md` → Step 1 section (similar issue?)
2. ✅ Review `error_report.json` in output/ (accuracy metrics)
3. ✅ Check `context.json` for state at each step
4. ✅ Run step in isolation with added print() statements
5. ✅ Verify CLO plugin is running (step_01_health.py)

### Step 2 Debugging

1. ✅ Check `.claude/troubleshooting.md` → Step 2 section
2. ✅ Review intermediate images: `base_garment.png`, `graphic_diffuse.png`
3. ✅ Check JSON outputs: `colors.json`, `panel_metadata.json`
4. ✅ Inspect individual stages (stage 1: segmentation, stage 2: view, etc.)
5. ✅ Verify input images are in correct format and location

### Step 3 Debugging

1. ✅ Check `.claude/troubleshooting.md` → Step 3 section
2. ✅ Review `native_vto_report.json` for which step failed
3. ✅ Verify avatar from Step 1 is valid
4. ✅ Verify patterns + edge_manifest.json from Step 2 are present
5. ✅ Check seam wiring (edge names match edge_manifest.json)

### General Debug Tips
- Output artifacts are **intentionally preserved** for debugging
- Check **JSON files first** (they tell you what happened)
- **Run problematic step in isolation** with added logging
- **Inspect visual outputs** (images, DXF files) with appropriate tools
- Check `.claude/quick-reference.md` and `.claude/faq.md` first (may be documented)

---

## Commands Quick Reference

### All Commands (Run from repo root)

```bash
# Step 1: Avatar Generation
python clo_avatar_generation/run_avatar.py

# Step 2: Product Ingestion
python product_ingestion/run_product_ingestion.py

# Step 3: Virtual Try-On
python clo_avatar_generation/run_clo_vto.py

# Build CLO plugin (if plugin code changes)
python clo_workspace/build_plugin.py
```

### Command Format
✅ **ALWAYS**: Repo-root relative paths, NOT `python -m`
- `python clo_avatar_generation/run_avatar.py` ✅
- `python -m clo_avatar_generation.run_avatar` ❌

---

## Documentation Quick Links

| Need | Location |
|------|----------|
| Project overview | `.claude/project-context.md` |
| Coding rules | `.claude/repo-rules.md` |
| High-level architecture | `.claude/architecture/architecture.md` |
| Step 1 deep-dive | `.claude/architecture/step_1_avatar.md` |
| Step 2 deep-dive | `.claude/architecture/step_2_ingestion.md` |
| Step 3 deep-dive | `.claude/architecture/step_3_vto.md` |
| Quick references | `.claude/quick-reference.md` |
| Common questions | `.claude/faq.md` |
| Troubleshooting | `.claude/troubleshooting.md` |
| Project status | `.claude/current-roadmap.md` |

---

## Need Help?

1. ✅ **Quick lookup**: Check `.claude/quick-reference.md`
2. ✅ **Known issue**: Check `.claude/troubleshooting.md`
3. ✅ **Architecture question**: Check `.claude/architecture/` (your step)
4. ✅ **Common question**: Check `.claude/faq.md`
5. ✅ **Still stuck**: Ask with full context (error, artifacts, reproduction steps)

---

*Last updated: 2026-05-16*
