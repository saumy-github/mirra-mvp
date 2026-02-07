# Blender Cloth Simulation - Testing Guide

## ✅ Fixes Applied

### 1. Path Resolution Error (FIXED)
**Problem:** When opening saved `.blend` file, script tried to create log directories inside the `.blend` file itself
```
FileExistsError: Cannot create a file when that file already exists: 
'...\garment_simulation.blend\blender_logs'
```

**Solution:** Added detection for `.blend` file execution context:
```python
if Path(__file__).suffix == '.blend':
    SCRIPT_DIR = Path(__file__).parent.parent  # Go up from .blend location
else:
    SCRIPT_DIR = Path(__file__).parent         # Normal script execution
```

### 2. Gravity Direction (FIXED)
**Problem:** Garment was positioned on ground, avatar above → fabric fell away
**Solution:** Flipped positioning → garment suspended at Z=0.73m, avatar at Z=0

### 3. Pin Group (ADDED)
**Enhancement:** Added shoulder/neck pinning so garment hangs naturally instead of falling to ground

---

## 🎬 How to Test the Simulation

### **Step 1: Verify Setup**

Blender should now be open with `garment_simulation.blend`. Check:

1. **3D Viewport** - You should see:
   - ✓ Flat T-shaped garment **ABOVE** the avatar body (suspended)
   - ✓ Avatar body (metaball mesh) at ground level
   - ✓ Gap of ~73cm between them

2. **Outliner** (top-right panel):
   - ✓ `TShirt_Garment` (the cloth object)
   - ✓ `Avatar_Smooth_Collision` (the body)
   - ✓ `Ground_Reference` (ground plane)

3. **Timeline** (bottom of screen):
   - Current frame should be **1**
   - End frame should be **150**

---

### **Step 2: Run Simulation**

**Method A: Real-time Playback** (Recommended for first test)
1. Press **SPACEBAR** or click the **Play button** ▶️ in timeline
2. Watch the animation play in real-time
3. You should see:
   - **Frame 1-30:** Garment begins falling downward
   - **Frame 30-60:** Fabric makes contact with avatar shoulders
   - **Frame 60-120:** Draping continues, fabric conforms to body
   - **Frame 120-150:** Settles into final draped position

**Method B: Manual Scrubbing**
1. Click and drag the **blue playhead** in timeline
2. Move it from frame 1 → 50 → 100 → 150
3. Watch garment position update at each frame

**Method C: Jump to Result**
1. Click in timeline and type `150` then ENTER
2. Jumps directly to final frame
3. See final draped state

---

### **Step 3: Verify Cloth Behavior**

**Expected Behavior:**
- ✅ Garment **falls downward** (gravity working)
- ✅ Shoulder/neck area **stays in place** (pins working)
- ✅ Fabric **drapes over avatar** (collision working)
- ✅ Some edges **pull together** (sewing springs working)
- ✅ Fabric **hangs naturally** like real cloth

**Problem Signs:**
- ❌ Nothing moves → Check cloth modifier is enabled
- ❌ Garment falls through avatar → Collision modifier issue
- ❌ Explodes/stretches wildly → Mesh has issues (run diagnostic)
- ❌ Falls to ground completely → Pin group not assigned

---

### **Step 4: Inspect Modifiers**

Click on `TShirt_Garment` in Outliner, then check **Modifiers** panel (wrench icon):

**Should see:**
```
✓ Cloth Modifier
  - Cache: Not baked (real-time sim)
  - Quality: 12
  - Sewing Springs: Enabled ✓
  - Vertex Group: Pin
  
✓ (Avatar) Collision Modifier
  - Thickness: 0.02m
  - Friction: 2.0
```

---

## 🐛 Troubleshooting

### Problem: "Nothing moves when I press spacebar"

**Check 1: Timeline Playing?**
- Look at timeline - blue playhead should be moving
- If not, press SPACEBAR again or click Play ▶️

**Check 2: Cloth Modifier Enabled?**
- Select `TShirt_Garment`
- Modifiers panel → Cloth modifier should have **eye icon** visible
- If grayed out, click the eye to enable

**Check 3: Starting from Frame 1?**
- Timeline should start at frame 1
- If at frame 150, click in timeline, type `1`, press ENTER
- Then press SPACEBAR

**Check 4: Gravity Enabled?**
- Scene Properties (rightmost icon) → Gravity
- Should show: `(0, 0, -9.81)` m/s²

---

### Problem: "Garment explodes or stretches weirdly"

**Cause:** Mesh topology issues or physics instability

**Fix 1: Reduce Simulation Quality**
- Select `TShirt_Garment`
- Modifiers → Cloth → Quality Steps
- Try changing from `12` to `5` (faster, more stable)

**Fix 2: Check Mesh**
- Edit Mode (Tab key)
- Select All (A key)
- Mesh → Normals → Recalculate Outside
- Back to Object Mode (Tab)

**Fix 3: Lower Sewing Force**
- Modifiers → Cloth → Sewing Springs
- Change Max Sewing Force from `100` to `50`

---

### Problem: "Garment falls straight through avatar"

**Cause:** Collision not working

**Fix:**
- Select `Avatar_Smooth_Collision`
- Modifiers panel → Should have "Collision" modifier
- If missing: Add Modifier → Physics → Collision
- Settings:
  - Thickness: 0.02m
  - Damping: 0.6
  - Friction: 2.0

---

## 📊 Performance Notes

**Real-time Simulation Speed:**
- Fast PC: ~30-60 FPS (smooth playback)
- Medium PC: ~10-20 FPS (choppy but viewable)
- Slow PC: ~5 FPS (very slow)

**If too slow:**
1. Reduce Quality Steps (Cloth modifier → Quality: 5)
2. Reduce frame range (Timeline → End: 100 instead of 150)
3. Use "Jump to frame" instead of real-time playback

---

## 🎯 Success Criteria

You know the simulation is working correctly when:

1. ✅ **Frame 1:** Garment clearly above avatar (gap visible)
2. ✅ **Frame 50:** Garment has fallen ~halfway toward avatar
3. ✅ **Frame 100:** Fabric touching/draping over shoulders and torso
4. ✅ **Frame 150:** Natural hanging position, some seams pulled together
5. ✅ **Throughout:** Smooth motion, no explosions, fabric stays intact

---

## 📸 Visual Reference

**Frame 1 (Start):**
```
     [Garment - flat T shape]
     
     ↓↓↓  (gravity)
     
     
     [Avatar body]
     _______________
     [Ground plane]
```

**Frame 150 (End):**
```
     [Garment draped over body]
         ╱╲    ← sleeves hang
        ╱  ╲
       │    │  ← body drapes
       │    │
       ╰────╯
     
     [Avatar inside garment]
     _______________
     [Ground plane]
```

---

## ⏭️ Next Steps After Successful Test

1. **Bake Simulation** (for faster playback):
   - Timeline → Bake All Dynamics (or Ctrl+B)
   - Wait 2-5 minutes
   - Playback will be instant after baking

2. **Export Final Mesh**:
   - Go to frame 150 (final result)
   - File → Export → OBJ / FBX / glTF
   - Use exported mesh in other applications

3. **Apply Texture** (Step 6):
   - Run `python step6_apply_texture.py`
   - Adds the extracted design/color to the garment

---

## 🔧 Advanced: Manual Simulation Tweaks

If you want to experiment:

**Fabric Type Adjustments:**
```
Stiffer fabric (denim):
  - Tension Stiffness: 25
  - Bending Stiffness: 2.0

Lighter fabric (silk):
  - Mass: 0.1
  - Tension Stiffness: 5
  - Bending Stiffness: 0.1
```

**Faster Falling:**
```
Scene Properties → Gravity:
  - Change Z from -9.81 to -15.0
  (Stronger gravity = faster drop)
```

---

## ✅ Quick Checklist

Before reporting issues, verify:

- [ ] Blender opens without Python errors
- [ ] Garment is ABOVE avatar (not on ground)
- [ ] Timeline shows frames 1-150
- [ ] Cloth modifier is enabled (eye icon visible)
- [ ] Pressing SPACEBAR moves timeline playhead
- [ ] Current frame is 1 when starting test
- [ ] Gravity is enabled (Scene Properties)
- [ ] Avatar has collision modifier

If all checked and still no movement → Please share screenshot of:
1. 3D viewport (showing garment position)
2. Modifiers panel (showing cloth settings)
3. Timeline (showing current frame)
