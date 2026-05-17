# Mirra Troubleshooting Guide

Organized by step. When stuck, find your step and look for similar symptoms.

---

## Step 1: Avatar Generation Troubleshooting

### CLO Plugin Not Responding

**Symptom**: `Connection refused`, `timeout`, or `plugin unreachable` errors

**Causes**:
- CLO application not running
- Plugin not built or outdated
- Network/API connectivity issues

**Solutions**:
1. Verify CLO 3D application is running (check system processes)
2. Check plugin build: `python clo_workspace/build_plugin.py`
3. Verify plugin endpoints in `clo_workspace/plugin_contract.json`
4. Check firewall/network settings (if remote CLO)
5. Try health check command: `python -c "from clo_workspace.client import CLORestClient; CLORestClient().health_check()"`

**Prevention**: Always verify CLO is running before starting Step 1.

---

### Avatar Import Fails

**Symptom**: `import_result.json shows error` or import step fails

**Causes**:
- Base avatar file missing, corrupted, or invalid format
- Avatar path incorrect
- CLO plugin version incompatibility

**Solutions**:
1. Check avatar file exists: `step_04_resolve_base_avatar.py` output
2. Verify .avt file is valid CLO format
3. Try with fresh avatar template from CLO
4. Check `import_result.json` for specific error message
5. Verify avatar path is correct and absolute

**Prevention**: Store avatar templates in known location. Document path in config.

---

### Measurements Out of Range

**Symptom**: `normalize_targets error` or Step 5 fails

**Causes**:
- Input measurements exceed expected ranges
- Typos in measurement field names
- Wrong measurement units
- Incomplete data (missing required fields)

**Solutions**:
1. Check `mongo_snapshot.json` in output - is data correct?
2. Verify measurement values are in expected range (see quick-reference.md)
3. Check field names match `field_contract.py`
4. Verify measurements are in correct units (cm, kg)
5. Ensure all required fields are present (height, weight, chest, waist, hip, leg)

**Prevention**: Validate input data before passing to Step 1. Document expected ranges.

---

### Low Accuracy Metrics

**Symptom**: `error_report.json shows >5% overall error`

**Causes**:
- Extreme body measurements (outliers)
- Inappropriate base avatar template
- Measurement morphing algorithm limitations
- Measurement data quality issues

**Solutions**:
1. Check `error_report.json` for per-measurement errors - which fields have high error?
2. If specific measurements high error: verify input data is correct
3. Try different base avatar template (if available)
4. Review body shape archetype selection
5. For extreme cases (very tall/short/wide): consider manual template adjustment

**Note**: Some error is acceptable. Target is <5% for 95% of users. Extremes may exceed this.

---

### Avatar Not Exported

**Symptom**: `.avt file missing` from output folder

**Causes**:
- Step 11 failed (save_outputs.py)
- Insufficient disk space
- File permission issues
- Output directory not created

**Solutions**:
1. Check `output.json` for Step 11 status
2. Verify output directory created: `output/<user_id>-<run_number>/`
3. Check disk space available
4. Verify write permissions on output directory
5. Check error_report.json for specific export error

---

### CLO Project File Corrupted

**Symptom**: Avatar file appears invalid when used in Step 3

**Causes**:
- Step 11 export incomplete
- File write interrupted
- CLO format mismatch

**Solutions**:
1. Re-run Step 1 from beginning
2. Check all intermediate artifacts in output/
3. Verify CLO plugin version is current

---

## Step 2: Product Ingestion Troubleshooting

### Image Segmentation Fails

**Symptom**: `base_garment.png is blank, mostly white, or completely wrong`

**Causes**:
- Background too similar to garment color
- RMBG-1.4 model not working with this image type
- Image quality too low
- Garment occlusion by body/other objects

**Solutions**:
1. Inspect input image - is garment clearly visible with distinct background?
2. Try GrabCut method instead of RMBG-1.4 (see `segmentation.py`)
3. Improve image quality (lighting, focus, contrast)
4. Remove occlusions if possible
5. Check RMBG-1.4 model is loaded correctly

**Prevention**: Use images with clear backgrounds, good lighting, no occlusion.

---

### Color Extraction Incomplete

**Symptom**: `colors.json missing colors or has only 1-2 dominant colors`

**Causes**:
- Image too monochromatic
- K-Means convergence issues
- Image quality low
- Segmentation produced noisy mask

**Solutions**:
1. Check `base_garment.png` - is it properly segmented?
2. Verify image has sufficient color variation
3. Check K-Means parameters in `colour_extraction.py` (try different k values)
4. Improve segmentation first (see "Image Segmentation Fails" above)
5. Check `colors.json` - is data present but just limited colors? (acceptable if garment actually monochromatic)

---

### DXF Generation Fails

**Symptom**: `front_panel.dxf, back_panel.dxf missing or invalid`

**Causes**:
- `panel_metadata.json` missing garment measurements
- MongoDB "sizes" collection doesn't have size_id entry
- `DynamicPatternGenerator` geometry calculation failed
- DXF export logic error

**Solutions**:
1. Check `panel_metadata.json` exists and has measurements
2. Verify size_id exists in MongoDB "sizes" collection
3. Check `run_summary.json` for specific stage 5 error
4. Inspect `DynamicPatternGenerator` in `panels.py` for geometry logic
5. Verify panel export function (`panel_export_dxf.py`) is working

**Prevention**: Ensure MongoDB "sizes" collection is populated before running Step 2.

---

### Edge Manifest Missing

**Symptom**: `edge_manifest.json not created` or missing from output

**Causes**:
- DXF export completed but edge extraction didn't happen
- Edge detection logic failed
- File write error

**Solutions**:
1. Check DXF files actually exist (they do if export ran)
2. Check `panel_export_dxf.py` for edge extraction logic
3. Verify edge names are correctly generated
4. Check `run_summary.json` for stage 5 completion status
5. Manually inspect DXF files with CAD viewer

**Critical for Step 3**: Without edge_manifest.json, Step 3 seam creation will fail. Re-run Step 2 if this is missing.

---

### Measurement Convention Mismatch

**Symptom**: Step 3 seams fail or garment looks wrong-sized

**Causes**:
- Step 2 used absolute measurements instead of half-girth
- `GarmentMeasurements` dataclass has wrong formula
- MongoDB "sizes" collection has wrong convention

**Solutions**:
1. Review `garment_measurements.py` field definitions
2. Check MongoDB "sizes" collection measurement values
3. Verify half-girth rule is being applied (chest_width = chest_circumference ÷ 2)
4. See `.claude/quick-reference.md` "Half-Girth Rule" for examples
5. Fix measurement source or formula, then re-run Step 2

**CRITICAL**: This breaks Step 3. Must be correct for proper seam creation.

---

### Complex Prints/Patterns Fail

**Symptom**: Design extraction produces blank or wrong `graphic_diffuse.png`

**Causes**:
- Edge detection thresholds not suitable for this print type
- Print too subtle or too complex
- Contrast too low

**Solutions**:
1. Check input image - is design clearly visible?
2. Adjust Canny edge detection thresholds in `design_extraction.py`
3. Try different threshold values for this garment type
4. Check contrast ratio (must be 1-80% of garment area)
5. For very complex patterns, consider simpler approximation

**Acceptable Fallback**: If design extraction fails, proceed without design texture. Step 3 will apply colors only.

---

## Step 3: Virtual Try-On Troubleshooting

### Pattern Import Fails

**Symptom**: `imported_patterns count is 0` in native_vto_report.json or import errors

**Causes**:
- DXF files don't exist or wrong path
- DXF files are invalid/corrupted
- File naming doesn't match expectations

**Solutions**:
1. Verify Step 2 completed successfully (check output folder exists)
2. Verify DXF file paths: front_panel.dxf, back_panel.dxf, sleeve_left.dxf, sleeve_right.dxf
3. Check file names exactly match (case-sensitive on Linux)
4. Manually inspect DXF files with CAD viewer (should have valid geometry)
5. Check `step_04_import_patterns.py` logs for specific error

---

### Slot Matching Fails

**Symptom**: `arrangement_result shows 0 success` or patterns not arranged

**Causes**:
- Auto-matching keywords don't match avatar slot names
- Avatar has unexpected slot names
- Helper function scoring algorithm failing

**Solutions**:
1. Check `step_06_read_edges_and_slots.py` output - what slots are available?
2. Review `helpers.py` keyword matching logic
3. Try manual slot mapping (specify pattern-to-slot in config)
4. Check slot names for typos/case mismatches
5. Verify avatar supports garment type (T-shirt slots should include front, back, sleeves)

**Fallback**: Use manual slot specification if auto-match consistently fails.

---

### Seam Creation Fails

**Symptom**: `seam_result shows 0 seams` or seam creation errors

**Causes**:
- Edge names in `edge_manifest.json` don't match `seams.py` expectations
- Edge indices not found in imported patterns
- Avatar geometry doesn't have expected edges

**Solutions**:
1. Compare edge names in `edge_manifest.json` against `seams.py` (10-seam mapping)
2. Check for typos/capitalization: "front-left-shoulder" vs "front_left_shoulder"
3. Verify all 10 expected edges are in the manifest
4. Check CLO pattern import actually happened (step_05_verify_patterns.py)
5. Manually verify pattern edges with CAD viewer

**Critical**: Seam creation is essential. If this fails, VTO cannot proceed. Check edge names carefully.

---

### Physics Simulation Hangs/Timeout

**Symptom**: Simulation doesn't complete within time limit or takes very long

**Causes**:
- High geometry complexity (many vertices)
- Physics parameters too strict (won't converge)
- CLO plugin slow or unresponsive

**Solutions**:
1. Check garment complexity - do patterns have excessive vertices?
2. Reduce simulation step count (default 150) - edit `step_10_simulate.py`
3. Adjust fabric properties (stiffness, weight)
4. Enable early termination on convergence (if supported)
5. Check CLO plugin responsiveness
6. Try simpler garment (fewer seams, simpler patterns)

**Prevention**: Monitor simulation time in logs. If consistently >5min, optimize geometry or parameters.

---

### Low-Quality VTO Render

**Symptom**: Output looks unrealistic, garment positioning wrong, fit bad

**Causes**:
- Avatar accuracy low (from Step 1)
- Pattern sizing wrong (from Step 2, half-girth convention)
- Wrong seam wiring (edges not connected properly)
- Physics parameters not tuned for fabric

**Solutions**:
1. Check Step 1 accuracy: `error_report.json` in avatar output
2. Check Step 2 patterns: inspect DXF files visually, verify measurements
3. Check seam wiring: verify all 10 seams created successfully
4. Verify edge_manifest.json edge names match seams.py exactly
5. Adjust fabric properties in `step_08_apply_fabric.py`

**Acceptable**: Early MVP render may lack polish. Visual realism improvements are post-MVP.

---

## All Steps: General Troubleshooting

### Output Folder Not Created

**Symptom**: No output/ folder created, or run folder missing

**Causes**:
- Insufficient permissions
- Parent directory doesn't exist
- Script failed before setup

**Solutions**:
1. Check parent directory exists: `c:\D-drive-data\mirra-mvp\output\`
2. Verify write permissions on output directory
3. Check step 2 (run setup) actually ran: should create directory
4. Try creating directory manually: `mkdir output` (if needed)

---

### JSON Artifacts Corrupted/Unreadable

**Symptom**: Error reading JSON files from output, or data looks garbled

**Causes**:
- File write interrupted
- File opened in editor while writing (lock)
- Encoding issues

**Solutions**:
1. Don't manually edit output JSON files while script running
2. Re-run step to regenerate artifacts
3. Check file encoding (should be UTF-8)
4. Don't interrupt script mid-execution
5. Use Python json module to verify: `python -m json.tool <file>`

**Prevention**: Only read output files after step completes. Use json.tool for validation.

---

### Need More Debug Info

**Symptom**: Error message unclear, need more detailed logs

**Solutions**:
1. Add `print()` statements in relevant step files
2. Check all JSON artifacts in output/ folder
3. Run single problematic step in isolation
4. Enable verbose logging if available
5. Check timestamps in logs to trace execution flow

**Tip**: Intermediate artifacts (images, DXF, JSON) are your friends. Inspect them visually/programmatically.

---

### Still Stuck?

1. **Check documentation first**:
   - `.claude/faq.md` (this might be asked before)
   - `.claude/quick-reference.md` (your step)
   - `.claude/architecture/step_X_*.md` (your step)

2. **Inspect artifacts**:
   - All JSON files in output/ folder
   - Images (segmented, design) in output/
   - DXF files with CAD viewer

3. **Narrow it down**:
   - Which step is failing?
   - Which stage within the step?
   - What's the exact error message?

4. **Create minimal reproduction**:
   - Test with simplest possible input
   - Add debugging print() statements
   - Run step in isolation

5. **Ask for help** with:
   - Exact error message
   - Output JSON artifacts
   - Steps to reproduce
   - What you've already tried

---

*Last updated: 2026-05-16*
