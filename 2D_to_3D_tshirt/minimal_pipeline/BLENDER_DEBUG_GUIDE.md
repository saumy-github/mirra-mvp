# BLENDER DEBUGGING GUIDE - Step 5 T-Shirt Simulation

## What You Should See Now:

In your Blender viewport, you should see:
- ✅ **TShirt_Garment** - Flat gray panels (this is correct!)
- ✅ **Avatar_Smooth_Collision** - Body form
- ✅ **Ground_Reference** - Floor plane

**The panels are FLAT on purpose - they become a T-shirt when you run the simulation!**

---

## Step-by-Step Debugging in Blender:

### STEP 1: Verify the Scene Setup

**Check the Outliner (top right):**
- [ ] TShirt_Garment exists
- [ ] Avatar_Smooth_Collision exists
- [ ] Ground_Reference exists

**Select TShirt_Garment:**
1. Click "TShirt_Garment" in the outliner (right panel)
2. Look at the **Modifiers panel** (wrench icon on right side)
3. You should see a **"Cloth" modifier**

**Check if cloth is configured:**
- Click the dropdown arrow on "Cloth" modifier
- Under "Physical Properties" you should see:
  - Quality: 12
  - Mass: 0.3
  - Tension/Compression stiffness: 15
- Under "Stiffness Scaling" → "Sewing":
  - [ ] "Sewing" checkbox should be CHECKED
  - Max Sewing Force: 100

---

### STEP 2: Check Collision Setup

**Select Avatar_Smooth_Collision:**
1. Click it in the outliner
2. Check **Modifiers panel**
3. You should see **"Collision" modifier**

**If no Collision modifier:**
```python
# In Blender Python Console (bottom left), run:
obj = bpy.data.objects['Avatar_Smooth_Collision']
if not obj.modifiers.get('Collision'):
    obj.modifiers.new('Collision', 'COLLISION')
    print("✓ Added collision")
```

---

### STEP 3: Inspect the Garment Mesh

**With TShirt_Garment selected:**
1. Press **TAB** to enter Edit Mode
2. Look at the mesh - you should see multiple panels
3. Press **TAB** again to exit Edit Mode

**Check vertex count:**
```python
# In Python Console:
obj = bpy.data.objects['TShirt_Garment']
print(f"Vertices: {len(obj.data.vertices)}")
print(f"Faces: {len(obj.data.polygons)}")
# Should show: Vertices: ~144, Faces: ~128
```

---

### STEP 4: Run the Simulation

**Option A: Play Animation**
1. Go to bottom timeline
2. Make sure you're at **Frame 1** (the blue playhead)
3. Press **SPACEBAR** (or click ▶ play button)
4. **WAIT 30-60 seconds** - the panels will fall and fold!

**Option B: Jump to End Result**
1. In the timeline at bottom, click on the frame number
2. Type **150** and press Enter
3. Wait a moment - Blender will calculate all frames
4. The garment should be draped on the avatar!

---

### STEP 5: Troubleshooting - What You Might See

**Issue 1: Panels just fall through the floor**
- **Cause:** Avatar collision not enabled
- **Fix:**
```python
avatar = bpy.data.objects['Avatar_Smooth_Collision']
if not avatar.modifiers.get('Collision'):
    coll = avatar.modifiers.new('Collision', 'COLLISION')
    coll.settings.thickness_outer = 0.02
```

**Issue 2: Panels fall but don't sew together**
- **Cause:** No sewing springs or no vertex groups
- **Check:**
```python
garment = bpy.data.objects['TShirt_Garment']
print("Vertex groups:", [vg.name for vg in garment.vertex_groups])
# Should show sewing groups like "sew_left_side", etc.
```
- **Current problem:** The seams weren't created (we saw warnings)

**Issue 3: Panels explode or act crazy**
- **Cause:** Physics too strong
- **Fix:** Lower cloth settings (see below)

---

### STEP 6: Debug Console Output

**Run this in Python Console to see what's in the scene:**
```python
print("="*50)
print("SCENE INVENTORY")
print("="*50)

# List all objects
print("\nObjects in scene:")
for obj in bpy.data.objects:
    print(f"  - {obj.name} (type: {obj.type})")
    
# Check garment details
garment = bpy.data.objects.get('TShirt_Garment')
if garment:
    print(f"\nGarment details:")
    print(f"  Vertices: {len(garment.data.vertices)}")
    print(f"  Faces: {len(garment.data.polygons)}")
    print(f"  Location: {garment.location}")
    print(f"  Modifiers: {[m.name for m in garment.modifiers]}")
    print(f"  Vertex groups: {[vg.name for vg in garment.vertex_groups]}")
    
    # Check cloth settings
    cloth_mod = garment.modifiers.get('Cloth')
    if cloth_mod:
        print(f"\nCloth settings:")
        print(f"  Quality: {cloth_mod.settings.quality}")
        print(f"  Mass: {cloth_mod.settings.mass}")
        print(f"  Sewing enabled: {cloth_mod.settings.use_sewing_springs}")
        print(f"  Sewing force: {cloth_mod.settings.sewing_force_max}")
    
# Check avatar
avatar = bpy.data.objects.get('Avatar_Smooth_Collision')
if avatar:
    print(f"\nAvatar details:")
    print(f"  Location: {avatar.location}")
    print(f"  Dimensions: {avatar.dimensions}")
    print(f"  Has collision: {avatar.modifiers.get('Collision') is not None}")
```

---

### STEP 7: Manual Simulation Test

**If automatic simulation doesn't work, try this:**

1. **Clear cache:**
```python
bpy.ops.ptcache.free_bake_all()
```

2. **Bake simulation manually:**
```python
# Select garment
garment = bpy.data.objects['TShirt_Garment']
bpy.context.view_layer.objects.active = garment
garment.select_set(True)

# Bake cloth simulation
bpy.ops.ptcache.bake(bake=True)
```

3. **Watch the Info panel** (top bar) for progress

---

### STEP 8: View Different Angles

**To see the garment better:**
- **Middle Mouse Button** - Rotate view
- **Scroll Wheel** - Zoom in/out
- **Shift + Middle Mouse** - Pan view
- **Numpad 7** - Top view
- **Numpad 1** - Front view
- **Numpad 3** - Right side view

---

### STEP 9: What a Working Simulation Looks Like

**At Frame 1 (start):**
- Flat panels positioned around avatar
- Panels are above the avatar body

**At Frame 50:**
- Panels falling due to gravity
- Starting to contact avatar
- Some folding beginning

**At Frame 150 (end):**
- Panels draped over avatar
- Sleeves hanging down sides
- Front and back panels covering torso
- Natural fabric folds

**If seams work (they currently don't):**
- Side edges of front/back should be touching
- Shoulder edges connected
- Looks like a continuous garment

---

### STEP 10: Current Known Issue - Seams Not Working

**We saw these warnings:**
```
⚠ Skipping left_side_seam: piece not found
⚠ Skipping right_side_seam: piece not found
```

**This means:** The panels exist but seams aren't connecting them.

**Why:** The seam definitions expect panel names like "front" and "back", but the script created "Front_Panel" and "Back_Panel".

**Quick fix - Run this in console:**
```python
# Check actual names
for obj in bpy.data.objects:
    if 'Panel' in obj.name or 'Sleeve' in obj.name:
        print(obj.name)

# The garment is already joined, so seams need to be created differently
# For now, the simulation will show panels draping independently
```

---

### STEP 11: Expected vs Current Behavior

**CURRENT (without seams):**
- ✅ Panels fall and drape on avatar
- ✅ Cloth physics works
- ❌ Panels are separate (not sewn together)
- ❌ Looks like 4 separate pieces of fabric

**WITH SEAMS (once fixed):**
- ✅ Panels pull together at edges
- ✅ Forms continuous T-shirt shape
- ✅ Sleeves attach to body
- ✅ Front and back connect at sides

---

## Quick Commands Reference

**Reset simulation:**
```python
bpy.ops.screen.animation_cancel()
bpy.context.scene.frame_set(1)
```

**Go to specific frame:**
```python
bpy.context.scene.frame_set(75)  # Go to frame 75
```

**Check if simulation is baked:**
```python
garment = bpy.data.objects['TShirt_Garment']
cloth_mod = garment.modifiers.get('Cloth')
if cloth_mod:
    print(cloth_mod.point_cache.is_baked)
```

**Clear baked simulation:**
```python
bpy.ops.ptcache.free_bake_all()
```

---

## Next Steps After Debugging

Once you confirm:
1. ✅ Garment has cloth modifier
2. ✅ Avatar has collision
3. ✅ Simulation runs (even if panels are separate)

Then we can:
- **Fix the seaming** (I'll update the script)
- **Adjust cloth parameters** (make it stiffer/softer)
- **Apply texture** (Step 6)

---

## Save Your Work

**Before making changes:**
```
File → Save As → tshirt_debug_v1.blend
```

**Good practice:**
- Save different versions as you debug
- Name them: v1, v2, v3, etc.

---

**Tell me what you see when you run the simulation (spacebar)!**
