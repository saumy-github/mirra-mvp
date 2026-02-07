# Quick Start Guide - Fixed Pipeline

## ✅ What Was Fixed:

1. **Mesh Density** - Reduced from 400K+ vertices to ~2-5K vertices
   - Changed subdivision from `number_cuts=3` to `number_cuts=1`
   - Changed from `number_cuts=4` to `number_cuts=1`
   - Added vertex count warnings

2. **Cloth Modifier** - Now automatically added during pipeline

3. **Collision Setup** - Avatar collision properly configured

## 🚀 Run From Scratch:

### Option 1: Complete Automated Run
```cmd
cd 2D_to_3D_tshirt\minimal_pipeline
run_complete_pipeline.bat
```

This will:
- ✅ Clean old outputs
- ✅ Run Steps 1-4 (Python)
- ✅ Run Step 5 (Blender setup)
- ⏸ Stop for you to run simulation manually in Blender

### Option 2: Manual Step-by-Step
```cmd
# Python steps
cd 2D_to_3D_tshirt\minimal_pipeline
run_python_steps.bat

# Blender
run_blender_manual.bat
# Then in Blender:
# - Scripting workspace
# - Open step5_blender_sewing.py
# - Run Script
# - Press SPACEBAR
```

## 📊 Expected Results:

### After Steps 1-4:
- Segmented T-shirt: ~58.5% of image
- Design extracted: ~13.6% coverage
- Color: Black (#1C1C1C)
- Patterns: 52cm chest, 72cm length

### After Step 5 Setup:
- **Vertices: ~2,000 - 5,000** (not 400K!)
- Cloth modifier: ✅ Enabled
- Avatar collision: ✅ Enabled
- Sewing springs: ✅ Enabled

### After Simulation (SPACEBAR):
- Frame 1: Flat panels above avatar
- Frame 50: Panels falling, touching avatar
- Frame 150: Draped fabric over body shape

## 🐛 If Issues Occur:

### "Simulation still slow"
**Check vertex count in Blender console:**
```python
garment = bpy.data.objects['TShirt_Garment']
print(f"Vertices: {len(garment.data.vertices)}")
# Should be < 10,000
```

**If still >10K, decimate it:**
```python
decimate = garment.modifiers.new('Decimate', 'DECIMATE')
decimate.ratio = 0.1  # Keep 10%
bpy.ops.object.modifier_apply(modifier='Decimate')
print(f"Reduced to {len(garment.data.vertices)}")
```

### "No cloth modifier"
```python
garment = bpy.data.objects['TShirt_Garment']
cloth = garment.modifiers.new('Cloth', 'CLOTH')
cloth.settings.quality = 5
cloth.settings.mass = 0.3
```

### "Panels fall through floor"
```python
avatar = bpy.data.objects['Avatar_Smooth_Collision']
avatar.modifiers.new('Collision', 'COLLISION')
```

## 💾 Save Your Work

**After successful simulation:**
```
File → Save As → tshirt_final.blend
```

**Export 3D model:**
```
File → Export → FBX (.fbx)
# or
File → Export → Wavefront (.obj)
```

## 📝 Test Checklist

Before running complete pipeline:

- [ ] `front.png` exists in `input_images/`
- [ ] Python 3.13 venv is active
- [ ] Blender 5.0 is installed
- [ ] Old output folders deleted (or will be auto-deleted)

After Python steps complete:

- [ ] Check `segmentation_output/front_masked.png`
- [ ] Check `design_output/front_design.png`
- [ ] Check `color_output/front_dominant_color.png`
- [ ] Check `pattern_output/*.svg` files exist

In Blender:

- [ ] TShirt_Garment exists with <10K vertices
- [ ] Cloth modifier present
- [ ] Avatar has collision
- [ ] Simulation runs smoothly (not frozen)
- [ ] Fabric drapes over avatar by frame 150

## 🎯 Success Criteria:

✅ **Pipeline succeeds if:**
- Simulation runs at 5-24 fps
- Garment drapes naturally over avatar
- Mesh has 2K-5K vertices
- Frame 150 shows T-shirt shape

❌ **Pipeline fails if:**
- Blender freezes (<1 fps)
- Mesh has >100K vertices
- Panels fall through floor
- No cloth movement

---

**Ready to run? Execute:**
```cmd
cd 2D_to_3D_tshirt\minimal_pipeline
run_complete_pipeline.bat
```
