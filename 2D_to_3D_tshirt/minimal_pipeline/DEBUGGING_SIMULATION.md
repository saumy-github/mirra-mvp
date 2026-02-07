# DEBUGGING GUIDE - Cloth Simulation Issues

## Current Problem

The simulation **runs** (frames advance 1-150) but the cloth panels **don't move**. They stay frozen in place despite cloth physics being enabled.

## Root Cause Possibilities

When cloth doesn't move during simulation, the most common causes are:

### 1. **NO FACES** (MOST LIKELY)
- Mesh has only **edges**, no surface area
- Cloth simulation **requires polygons/faces** to work
- Check: Open Blender Console and run `len(bpy.data.objects['TShirt_Garment'].data.polygons)`
- Should be > 0, if it's 0 that's the problem

### 2. **Gravity Disabled**
- Scene gravity set to 0
- Cloth gravity multiplier set to 0
- Check: `bpy.context.scene.gravity`
- Should be `(0, 0, -9.8)` or similar

### 3. **All Vertices Pinned**
- Cloth has a "pin group" with all vertices
- Pinned vertices cannot move
- Check: Cloth modifier > Vertex Group Mass

### 4. **Cache Is Baked and Frozen**
- Old simulation baked into cache
- Blender shows old data instead of recalculating
- Fix: Physics Properties > Cloth > Cache > Delete Bake

### 5. **Stiffness Too High**
- Fabric is infinitely stiff
- Won't deform under gravity
- Check tension/compression stiffness values

## Diagnostic Tools We've Created

### 1. **blender_diagnostic.py** 
Comprehensive Blender scene analysis.

**How to use:**
```
1. Open garment_simulation.blend in Blender
2. Go to Scripting workspace (top menu)
3. Open blender_diagnostic.py
4. Click "Run Script"
5. Read console output
```

**What it checks:**
- ✓ Garment mesh exists
- ✓ Vertex count, edge count, **FACE COUNT** (critical!)
- ✓ Cloth modifier present and configured
- ✓ Gravity enabled (scene and cloth)
- ✓ Avatar collision setup
- ✓ Spatial positioning
- ✓ Actual vertex movement test (frame 1 → frame 10)

### 2. **pipeline_diagnostic.py**
Pre-flight check for Python steps.

**How to use:**
```
python pipeline_diagnostic.py
```

**What it checks:**
- ✓ Input images present
- ✓ Segmentation output valid
- ✓ Design extraction succeeded
- ✓ Color extraction succeeded
- ✓ Pattern SVGs generated
- ✓ Metadata files present
- ✓ Blender prerequisites

### 3. **Enhanced Logging in step5_blender_sewing.py**

Now logs:
- Mesh statistics (vertices, edges, **faces**)
- Cloth settings (quality, mass, stiffness)
- Gravity check
- Vertex group info
- Pattern piece face counts

## Step-by-Step Debugging Process

### Phase 1: Verify Mesh Has Faces

This is the #1 issue with cloth simulation.

**In Blender Console:**
```python
import bpy

garment = bpy.data.objects.get('TShirt_Garment')
if garment:
    mesh = garment.data
    print(f"Vertices: {len(mesh.vertices)}")
    print(f"Edges: {len(mesh.edges)}")
    print(f"Faces: {len(mesh.polygons)}")
else:
    print("Garment not found!")
```

**Expected:** Faces > 0 (should be hundreds to thousands)
**If Faces = 0:** The mesh is just wire edges, **NO SURFACE AREA**

**Fix:**
```python
# Select garment
garment.select_set(True)
bpy.context.view_layer.objects.active = garment

# Enter edit mode
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')

# Fill holes (create faces)
bpy.ops.mesh.fill()

# Triangulate
bpy.ops.mesh.quads_convert_to_tris()

# Exit edit mode
bpy.ops.object.mode_set(mode='OBJECT')
```

### Phase 2: Verify Gravity

**In Blender Console:**
```python
import bpy

# Scene gravity
print(f"Scene gravity: {bpy.context.scene.gravity}")

# Cloth gravity multiplier
garment = bpy.data.objects['TShirt_Garment']
cloth_mod = None
for mod in garment.modifiers:
    if mod.type == 'CLOTH':
        cloth_mod = mod
        break

if cloth_mod:
    gravity_mult = cloth_mod.settings.effector_weights.gravity
    print(f"Cloth gravity multiplier: {gravity_mult}")
else:
    print("No cloth modifier!")
```

**Expected:** Scene gravity around `(0, 0, -9.8)`, multiplier = 1.0
**If wrong:** Fix with:
```python
bpy.context.scene.gravity = (0, 0, -9.8)
cloth_mod.settings.effector_weights.gravity = 1.0
```

### Phase 3: Check for Pinning

**In Blender Console:**
```python
import bpy

garment = bpy.data.objects['TShirt_Garment']
cloth_mod = None
for mod in garment.modifiers:
    if mod.type == 'CLOTH':
        cloth_mod = mod
        break

if cloth_mod:
    pin_group = cloth_mod.settings.vertex_group_mass
    if pin_group:
        print(f"⚠ Pin group active: {pin_group}")
        print("  Vertices in this group are frozen!")
        # Disable pinning
        cloth_mod.settings.vertex_group_mass = ""
    else:
        print("✓ No pinning")
```

### Phase 4: Clear Baked Cache

**In Blender UI:**
1. Select garment object
2. Go to Physics Properties panel (right side)
3. Cloth > Cache section
4. Click "Delete Bake"
5. Reset to frame 1
6. Press SPACEBAR again

**Or in Console:**
```python
import bpy
bpy.ops.ptcache.free_bake_all()
bpy.context.scene.frame_set(1)
```

### Phase 5: Test Movement Manually

**In Blender Console:**
```python
import bpy

garment = bpy.data.objects['TShirt_Garment']
mesh = garment.data

# Go to frame 1
bpy.context.scene.frame_set(1)
v0_start = garment.matrix_world @ mesh.vertices[0].co
print(f"Vertex 0 at frame 1: {v0_start}")

# Jump to frame 20
bpy.context.scene.frame_set(20)
v0_end = garment.matrix_world @ mesh.vertices[0].co
print(f"Vertex 0 at frame 20: {v0_end}")

# Calculate movement
distance = (v0_end - v0_start).length
print(f"\nMovement: {distance:.6f} meters")

if distance < 0.001:
    print("❌ NO MOVEMENT - Simulation not working!")
else:
    print(f"✓ Vertex moved {distance} meters")
```

## Code Improvements Made

### 1. **curve_to_mesh() - Lines ~450-470**
Added:
- Comprehensive mesh statistics logging
- **CRITICAL CHECK for faces**
- Warning if mesh has no faces

### 2. **add_cloth_modifier() - Lines ~619-680**
Added:
- Pre-check: verify mesh has faces before adding cloth
- Log all cloth settings (quality, mass, stiffness)
- **Gravity multiplier check and warning**
- Detailed physics parameter logging

### 3. **join_pattern_pieces() - Lines ~750-790**
Added:
- Per-piece face count logging
- Warning if individual pieces lack faces

### 4. **setup_scene() - Lines ~355-395**
Added:
- **Gravity verification and auto-fix**
- Log current gravity settings
- Set to -9.8 if disabled

## Running the Full Pipeline with Diagnostics

**Option 1: Fresh Complete Run**
```
run_pipeline_with_diagnostics.bat
```

This will:
1. Run pre-flight diagnostic
2. Clean old outputs
3. Run steps 1-4 (Python)
4. Verify outputs
5. Run step 5 (Blender) with enhanced logging
6. Suggest diagnostic steps if issues found

**Option 2: Just Blender Diagnostic**
```
blender garment_simulation.blend --python blender_diagnostic.py
```

## Quick Fix Checklist

If simulation runs but nothing moves:

- [ ] Run `blender_diagnostic.py` in Blender console
- [ ] Check face count > 0
- [ ] Check gravity enabled
- [ ] Check no vertices pinned
- [ ] Clear baked cache
- [ ] Test vertex movement manually
- [ ] Check console output for errors

## Expected Behavior

**Working simulation:**
- Frame 1: Flat panels positioned above/around avatar
- Frames 1-50: Panels fall downward due to gravity
- Frames 50-100: Panels drape over avatar collision shape
- Frames 100-150: Sewing springs pull edges together
- Result: T-shirt shape formed around avatar

**Not working (current issue):**
- Frames 1-150: Panels stay exactly where they started
- No falling, no draping, no movement
- Likely cause: **Mesh has no faces**

## Next Steps

1. **Run blender_diagnostic.py in Blender**
   - This is the fastest way to identify the exact issue
   
2. **Check the console output**
   - Look for "FACE COUNT" section
   - If faces = 0, that's the root cause
   
3. **If faces = 0, check curve_to_mesh() function**
   - The `bpy.ops.mesh.fill()` operation may be failing
   - May need to use alternative face creation method
   
4. **Report findings**
   - Copy the diagnostic output
   - We'll fix the specific issue identified

## Contact Info for Errors

When reporting issues, include:
- Output from blender_diagnostic.py
- Vertex/Edge/Face counts
- Any error messages in Blender console
- Screenshot of what panels look like in Blender viewport
