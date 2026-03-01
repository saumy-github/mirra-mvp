# T-Shirt Pipeline Problems

## Problem 1: Seam Matching Name Mismatch ✅ FIXED

**Location:** `step4_pattern_generation.py` → `step5_blender_sewing.py`

**Issue:** `seams.json` used old naming (`front`, `back`, `sleeve_left`) but Blender expected new naming (`Front_Panel`, `Back_Panel`, `Left_Sleeve`).

**Fix:** Updated all references to use consistent naming convention:

- `step4_pattern_generation.py`: seam definitions, pattern keys, summary output
- `step5_blender_sewing.py`: panel dictionary keys, position calls, seam lookup logic

---

## Problem 2: Blender Panel Dictionary Keys ✅ FIXED

**Location:** `step5_blender_sewing.py` - `create_tshirt_panels_manually()`

**Issue:** Dictionary used lowercase keys (`"front"`, `"back"`) but seams.json had `panel_a: "Front_Panel"`.

**Fix:** Changed dictionary keys to match:

```python
panels["Front_Panel"] = create_pattern_mesh_from_points(...)
panels["Back_Panel"] = create_pattern_mesh_from_points(...)
```

---

## Problem 3: Cloth Modifier Disappearing ✅ FIXED

**Location:** `step5_blender_sewing.py` - `add_anatomical_digital twin()`

**Issue:** Cloth modifier was added to garment but disappeared by the time bake ran. Debug showed:

- After add_cloth_modifier: 1 CLOTH modifier
- After add_anatomical_digital twin: 0 modifiers

**Root Cause:** `bpy.ops.object.convert(target='MESH')` operates on ALL SELECTED objects. The garment was still selected when converting the metaball digital twin to mesh, causing the convert operation to also affect (and remove modifiers from) the garment.

**Fix:** Added `bpy.ops.object.select_all(action='DESELECT')` before the convert operation.

---

## Problem 4: Cloth Simulation Not Running 🔄 IN PROGRESS

**Location:** `step5_blender_sewing.py` - bake pipeline

**Issue:** Even with cloth modifier present, simulation may not actually bake/animate.

**Status:** Currently testing after Fix #3...

---

## Problem 5: Static Mesh Export (Not Dynamic)

**Location:** Design decision

**Issue:** The exported .glb is a frozen static mesh, not a live cloth simulation.

**Notes:**

- This is expected - Blender exports geometry, not physics
- For VTO in Blender: open .blend file and press Spacebar to run live simulation
- For browser VTO: would need JavaScript physics library (heavy performance)

---

## Other Notes

- `.blend1` files are Blender auto-backups (not errors)
- Use `--bake` flag for headless/background mode
