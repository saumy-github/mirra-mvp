# CLO3D Avatar Import Troubleshooting Guide

This guide helps resolve common issues when importing MIRRA-generated avatars into CLO3D.

## Table of Contents

- [Quick Checklist](#quick-checklist)
- [Common Issues](#common-issues)
- [Import Settings](#import-settings)
- [Validation Steps](#validation-steps)

---

## Quick Checklist

Before importing, verify:

- [ ] CLO3D SET Enterprise is installed and running
- [ ] OBJ file exists and is not corrupted (check file size > 100 KB)
- [ ] Avatar was exported using `avatar_exporter_clo.py`
- [ ] Measurements JSON file exists alongside OBJ file
- [ ] You have removed the default avatar (if present)

---

## Import Settings

### Recommended Import Settings

When importing via **Avatar → Import Avatar** or `Ctrl+Shift+A`:

```
File Format: OBJ
Import As: Avatar

Scale:
⚪ Auto-detect from file
⚪ Custom scale: 1.0  ← SELECT THIS

Units:
⚪ Meters  ← SELECT THIS (STAR exports in meters)
⚪ Centimeters
⚪ Millimeters

Orientation:
⚪ Y-up  ← SELECT THIS
⚪ Z-up

Options:
☑️ Import as collision object
☑️ Merge duplicate vertices
⬜ Flip normals (only if avatar appears dark)
⬜ Generate normals (only if normals are missing)
```

---

## Common Issues

### Issue 1: Avatar Too Large or Too Small

**Symptoms:**
- Avatar appears as tiny dot or fills entire screen
- Height shows as 0.0175 or 175000 instead of 175 cm
- Avatar not visible in default view

**Cause:** Unit mismatch between export and import

**Solution:**

1. **Check export units:**
   - STAR mesh should be in meters (Y-axis range ~0 to 1.75 for 175cm person)
   - Verify in OBJ file header comments

2. **Correct import settings:**
   - In CLO import dialog, select **"Meters"** as unit
   - If still wrong, manually adjust:
     - Too large (17500 cm): Scale = 0.01
     - Too small (0.0175 m): Scale = 100

3. **Manual scaling after import:**
   - Right-click avatar → Transform → Scale
   - Adjust uniformly in all axes

### Issue 2: Avatar Upside Down or Rotated

**Symptoms:**
- Avatar appears inverted
- Feet point up instead of down
- Avatar lying horizontally instead of standing

**Cause:** Coordinate system mismatch

**Solutions:**

1. **Try different orientation:**
   - In import dialog, switch between Y-up and Z-up

2. **Rotate after import:**
   - Right-click avatar → Transform → Rotate
   - Common fixes:
     - 180° on X-axis (upside down)
     - 90° on X-axis (lying down)

3. **Check export:**
   - Verify STAR mesh is Y-up coordinate system
   - Check vertex positions: Y should be height axis

### Issue 3: Avatar Normals Inverted (Appears Dark)

**Symptoms:**
- Avatar appears completely black or very dark
- Lighting doesn't work correctly
- Surfaces look inside-out

**Cause:** Inverted face normals

**Solutions:**

1. **During import:**
   - Check ☑️ "Flip normals" in import dialog

2. **After import:**
   - Right-click avatar in 3D window
   - Select "Flip Normals"

3. **Verify normals in export:**
   - Check if OBJ file includes vertex normals (lines starting with `vn`)
   - If missing, enable `include_normals=True` in export

### Issue 4: Avatar Not Acting as Collision Object

**Symptoms:**
- Patterns fall through avatar during simulation
- No collision detection with garments
- Physics doesn't work correctly

**Solutions:**

1. **Set as collision object:**
   - Right-click avatar in Object Browser
   - Select "Set as Collision Object"
   - Verify checkmark appears next to avatar

2. **Check during import:**
   - Ensure ☑️ "Import as collision object" is checked

3. **Verify collision settings:**
   - Right-click avatar → Properties
   - Under "Collision" tab, ensure:
     - Collision enabled: Yes
     - Collision thickness: 1-2 mm (default)

### Issue 5: Avatar Positioning Wrong

**Symptoms:**
- Avatar floating above ground
- Avatar positioned off-center
- Avatar tilted or not standing straight

**Solutions:**

1. **Reset position:**
   - Right-click avatar → Transform
   - Reset Position: (0, 0, 0)
   - Reset Rotation: (0, 0, 0)

2. **Adjust ground contact:**
   - If feet don't touch ground plane:
     - Select avatar
     - Click Move Tool (or press `M`)
     - Drag Y-axis (vertical) until feet touch ground
     - Ground plane is Y = 0

3. **Check export:**
   - Verify STAR mesh has feet near Y = 0
   - If not, adjust in export or enable `recenter=True` in postprocess

### Issue 6: Avatar Missing Body Parts

**Symptoms:**
- Hands, feet, or head not visible
- Holes in the mesh
- Incomplete geometry

**Cause:** Export or mesh generation issue

**Solutions:**

1. **Verify mesh completeness:**
   - Check vertex count: Should be ~6,890 for STAR
   - Check face count: Should be ~13,776 for STAR
   - Open OBJ in another viewer (Blender, MeshLab) to verify

2. **Regenerate avatar:**
   ```bash
   python pipeline_star/first.py \
       --user_id [user_id] \
       --mode generate_avatar \
       --run_number [run_number]
   ```

3. **Check measurements:**
   - Extreme measurements may cause mesh issues
   - Verify measurements are within plausible ranges

### Issue 7: File Not Found or Cannot Import

**Symptoms:**
- "File not found" error
- "Invalid OBJ format" error
- Import button grayed out

**Solutions:**

1. **Verify file exists:**
   ```powershell
   Test-Path "path\to\avatar.obj"
   ```

2. **Check file permissions:**
   - Ensure CLO3D has read access to the file location
   - Try copying file to CLO workspace directory

3. **Validate OBJ format:**
   - Open OBJ in text editor
   - Should start with header comments
   - Should contain `v` (vertices) and `f` (faces) lines

4. **Check file size:**
   - Should be > 100 KB for typical STAR mesh
   - If much smaller, export may have failed

---

## Validation Steps

After successful import, verify the following:

### Visual Inspection

- [ ] Avatar is visible in 3D window
- [ ] Avatar is properly proportioned (not squashed/stretched)
- [ ] Avatar is standing upright
- [ ] Avatar is positioned with feet on ground plane (Y = 0)
- [ ] Avatar is facing correct direction (front = -Z axis)
- [ ] All body parts present (head, hands, feet)

### Technical Verification

- [ ] Avatar is set as collision object (check in Object Browser)
- [ ] Mesh statistics match OBJ file:
  - Vertices: ~6,890
  - Faces: ~13,776
- [ ] Height matches user measurement (± 5 cm tolerance)
- [ ] No error messages in CLO3D console

### Functional Test

- [ ] Create simple garment (rectangle pattern)
- [ ] Position pattern near avatar body
- [ ] Run 10-frame simulation
- [ ] Verify pattern collides with avatar (doesn't fall through)

---

## Getting Help

If issues persist:

1. **Check measurements:**
   - Review `[user_id]_[run]_measurements.json`
   - Verify all measurements are reasonable

2. **Check export log:**
   - Look for errors during OBJ export
   - Verify export completed successfully

3. **Test with simple mesh:**
   - Try importing a basic test cube OBJ
   - If that works, issue is with avatar mesh

4. **Contact support:**
   - Prepare: OBJ file, measurements JSON, screenshots
   - Include: CLO version, error messages, steps to reproduce

---

## Reference: Expected Avatar Properties

| Property | Expected Value | Tolerance |
|----------|---------------|-----------|
| File Size | 500 KB - 2 MB | - |
| Vertices | ~6,890 | ±100 |
| Faces | ~13,776 | ±200 |
| Height | User height ±5 cm | 5 cm |
| Format | OBJ with normals | - |
| Units | Meters | - |
| Orientation | Y-up | - |
| Position | Feet at Y = 0 | ±2 cm |

---

## Version History

- **v1.0** (2026-02-27): Initial troubleshooting guide
- Based on: PHASE1_CLO3D_SETUP_DETAILED_GUIDE.md
