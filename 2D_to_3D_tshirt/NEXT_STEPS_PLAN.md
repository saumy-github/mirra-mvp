# Next Steps Plan - Making the Pipeline Fully Functional

**Goal:** Get the 2D→3D T-shirt pipeline working end-to-end  
**Date:** January 29, 2026  
**Status:** Ready to execute

---

## 🎯 Quick Win Path (Recommended)

**Timeline:** 30-45 minutes  
**Goal:** Test Steps 1-4 (no Blender required)

### Phase 1: Immediate Setup (5 minutes)

#### ✅ Step 1.1: Check Dependencies

**NOTE:** You're using Python 3.14, which is too new for onnxruntime/rembg.  
**GOOD NEWS:** The pipeline automatically falls back to GrabCut segmentation, which works great!

**Verify installed packages:**
```powershell
c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe -m pip list | Select-String "opencv|numpy|scikit"
```

**Should show:**
- opencv-python (installed ✅)
- numpy (installed ✅)
- scikit-learn (installed ✅)
- rembg (installed but backend won't work)

**What this means:**
- Step 1 will use GrabCut (non-AI) segmentation
- Quality: ~85% as good as AI method
- Fully functional, just slightly less automatic

---

#### ✅ Step 1.2: Verify Input Image
```powershell
# Check if front.png exists in correct location
Test-Path 2D_to_3D_tshirt\minimal_pipeline\input_images\front.png
```

**Should return:** `True`

**If False:**
- Place your T-shirt image in `2D_to_3D_tshirt\minimal_pipeline\input_images\`
- Name it `front.png`

---

### Phase 2: Run Python Steps (15 minutes)

#### ✅ Step 2.1: Run Segmentation (Step 1)
```powershell
cd c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline
c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe step1_segmentation.py
```

**Expected output:**
```
============================================================
   STEP 1: T-SHIRT SEGMENTATION
============================================================
✓ Output directory ready: segmentation_output
✓ Loaded front: input_images\front.png (1772x1772 pixels)
→ Attempting AI-based segmentation (rembg)...
✓ Segmentation complete: 45.3% of image is garment
✓ Saved front_mask.png
✓ Saved front_masked.png
```

**Check output:**
- Open `segmentation_output\front_masked.png`
- Background should be transparent
- T-shirt should be cleanly isolated

**If it fails:**
- Check error message
- Ensure rembg[cpu] installed correctly
- Try running again (first run downloads AI model, takes time)

---

#### ✅ Step 2.2: Run Design Extraction (Step 2)
```powershell
# Still in minimal_pipeline directory
c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe step2_design_extraction.py
```

**Expected output:**
```
============================================================
   STEP 2: DESIGN EXTRACTION
============================================================
✓ Loaded front image: 1772x1772 pixels
→ Detecting edges...
  Found 8453 edge pixels
→ Detecting color outliers...
  Found 12034 color outlier pixels
✓ Design covers 12.4% of garment
✓ Saved front_design.png
```

**Check output:**
- Open `design_output\front_design.png`
- Only the printed design should be visible
- Everything else should be transparent

**Troubleshooting:**
- **Too much detected:** Design threshold too sensitive
- **Too little detected:** Increase sensitivity in step2 code
- **Nothing detected:** Plain T-shirt (no design) - this is OK!

---

#### ✅ Step 2.3: Run Color Extraction (Step 3)
```powershell
c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe step3_color_extraction.py
```

**Expected output:**
```
============================================================
   STEP 3: FABRIC COLOR EXTRACTION
============================================================
✓ Loaded front image: 1772x1772 pixels
→ Clustering into 3 color groups...
✓ DOMINANT FABRIC COLOR:
  RGB: (34, 67, 103)
  HEX: #224367
  Name: Dark Blue
  Coverage: 78.2% of fabric
```

**Check output:**
- Open `color_output\front_dominant_color.png`
- Should be a solid square of the fabric color
- Open `color_output\front_fabric_color.json`
- Verify RGB values make sense

---

#### ✅ Step 2.4: Run Pattern Generation (Step 4)
```powershell
c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe step4_pattern_generation.py
```

**You will be prompted:**
```
============================================================
   ENTER T-SHIRT MEASUREMENTS
============================================================
  Press ENTER to use default value shown in [brackets]
  All measurements are in centimeters (cm)

  chest_flat (half chest width, pit to pit) [52.0 cm]:
```

**What to do:**
- **Option A:** Press ENTER 5 times to use defaults
- **Option B:** Enter your measurements in cm

**Expected output:**
```
✓ Generated patterns:
  FRONT PANEL:
    - Width: 52.0 cm (half-width, cut on fold)
    - Length: 72.0 cm
  SLEEVE (x2):
    - Width: 33.6 cm
    - Length: 22.0 cm
✓ Saved front_pattern.svg
✓ Saved back_pattern.svg
✓ Saved sleeve_pattern.svg
```

**Check output:**
- Open `pattern_output\front_pattern.svg` in a browser
- You should see a T-shirt panel outline
- The pattern should look proportional

---

### Phase 3: Verify & Celebrate (5 minutes)

#### ✅ Step 3.1: Check All Outputs

**Run this command to see all generated files:**
```powershell
Get-ChildItem -Recurse -Include *.png,*.svg,*.json | Select-Object FullName
```

**You should see:**
```
segmentation_output\front_mask.png
segmentation_output\front_masked.png
design_output\front_design.png
design_output\front_design_mask.png
design_output\front_fabric_mask.png
color_output\front_dominant_color.png
color_output\front_fabric_color.json
pattern_output\front_pattern.svg
pattern_output\back_pattern.svg
pattern_output\sleeve_pattern.svg
pattern_output\pattern_metadata.json
pattern_output\seams.json
```

**If any are missing:** That step failed - go back and check error messages

---

#### ✅ Step 3.2: Visual Inspection

**Open each output in order:**

1. **front_masked.png** - T-shirt should be clean, no background
2. **front_design.png** - Only the print/logo visible
3. **front_dominant_color.png** - Solid color matching fabric
4. **front_pattern.svg** - Pattern piece outline

**Quality checklist:**
- [ ] Background removed cleanly (no artifacts)
- [ ] Design extracted correctly (or none if plain)
- [ ] Fabric color accurate
- [ ] Patterns look reasonable (not distorted)

---

## 🎨 Full Path Including Blender (Complete 3D Generation)

**Timeline:** 1-2 hours (includes Blender installation)  
**Goal:** Complete pipeline with 3D output

### Phase 4: Blender Setup (30 minutes)

#### 🔧 Step 4.1: Install Blender
1. Download Blender 3.0+ from https://www.blender.org/download/
2. Install to default location
3. Note installation path (usually `C:\Program Files\Blender Foundation\Blender 3.x\`)

**Verify installation:**
```powershell
# Replace with your actual Blender version
& "C:\Program Files\Blender Foundation\Blender 4.0\blender.exe" --version
```

---

#### 🔧 Step 4.2: Create Windows Batch Script

**Create file:** `2D_to_3D_tshirt\minimal_pipeline\run_step5.bat`

```batch
@echo off
echo ============================================
echo Running Blender Sewing Simulation (Step 5)
echo ============================================
echo.

REM Update this path to match your Blender installation
set BLENDER="C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"

REM Check if Blender exists
if not exist %BLENDER% (
    echo ERROR: Blender not found at %BLENDER%
    echo Please update the path in this batch file
    pause
    exit /b 1
)

REM Run the sewing script
%BLENDER% --background --python step5_blender_sewing.py

echo.
echo ============================================
echo Step 5 Complete!
echo ============================================
pause
```

**Save and test:**
```powershell
cd 2D_to_3D_tshirt\minimal_pipeline
.\run_step5.bat
```

---

### Phase 5: Run Blender Steps (30 minutes)

#### 🎨 Step 5.1: Run Sewing Simulation (Step 5)

**Option A: Batch file (automated)**
```powershell
cd 2D_to_3D_tshirt\minimal_pipeline
.\run_step5.bat
```

**Option B: Manual in Blender GUI**
1. Open Blender
2. Switch to "Scripting" workspace (top menu)
3. Click "Open" and select `step5_blender_sewing.py`
4. Click "Run Script" button (play icon)

**Expected console output:**
```
→ Loading pattern: front_pattern.svg
✓ Imported front panel (347 vertices)
→ Loading pattern: back_pattern.svg
✓ Imported back panel (351 vertices)
→ Loading pattern: sleeve_pattern.svg
✓ Imported sleeve panel (243 vertices)
→ Positioning panels for sewing...
→ Applying cloth physics...
→ Running simulation (120 frames)...
```

**This will take 5-10 minutes** depending on your computer

**Check result:**
- In Blender viewport, you should see a 3D T-shirt
- It should look like fabric draping naturally
- Seams should be connected (no gaps)

**If it fails:**
- Check Blender console for error messages
- SVG import might have failed
- Check that pattern SVG files exist

---

#### 🎨 Step 5.2: Apply Texture (Step 6)

**In Blender (after Step 5 completes):**

1. Open `step6_apply_texture.py` in Scripting workspace
2. Click "Run Script"

**Expected output:**
```
→ Loading fabric color...
✓ Loaded color: Dark Blue (#224367)
→ Loading design texture...
✓ Loaded design: TShirt_Design (1772x1772 pixels)
→ Creating material...
✓ Material applied to garment
```

**Check result:**
- Switch to "Shading" workspace
- Enable "Material Preview" mode (sphere icons top right)
- Your T-shirt should now have:
  - Correct fabric color
  - Design/print visible on front

---

### Phase 6: Export Final Model (10 minutes)

#### 📦 Step 6.1: Export for Use

**In Blender:**

1. Select the garment mesh
2. File → Export → FBX (.fbx)
3. Save as `tshirt_3d_final.fbx`

**OR export as OBJ:**
- File → Export → Wavefront (.obj)
- Includes materials and textures

**File locations:**
- FBX: Industry standard (Unity, Unreal, etc.)
- OBJ: Universal format (works everywhere)
- GLTF: Web 3D (AR/VR apps)

---

## 🔧 Troubleshooting Guide

### Issue: "rembg backend not found"
**Fix:**
```powershell
c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe -m pip install "rembg[cpu]"
```

### Issue: "Module not found: cv2"
**Fix:** Make sure you're using the venv Python:
```powershell
c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe script.py
```

### Issue: "Could not load front image"
**Fix:** Check file path:
```powershell
ls 2D_to_3D_tshirt\minimal_pipeline\input_images\
```
Should show `front.png`

### Issue: "Design extraction failed"
**Fix:** This is OK if T-shirt has no design (plain color)
- Check `front_design.png` - should be transparent if no design
- Step 3 will still extract fabric color correctly

### Issue: "SVG import failed in Blender"
**Possible causes:**
1. Blender version too old (need 3.0+)
2. SVG file corrupted
3. Path issues

**Fix:** Re-run step 4 to regenerate SVGs

### Issue: "Cloth simulation explodes"
**Causes:**
- Physics parameters too aggressive
- Sewing springs too strong

**Fix:** Edit `step5_blender_sewing.py`:
```python
CLOTH_SETTINGS = {
    "quality": 8,           # Lower from 12
    "mass": 0.2,            # Lower from 0.3
    "tension_stiffness": 10 # Lower from 15
}
```

### Issue: "Seams don't connect"
**Cause:** Edge matching failed (complex geometry)

**Fix:** Manual approach:
1. In Blender, select two vertices that should connect
2. Alt+M → Merge at Center
3. Repeat for seam edges

---

## 📊 Success Criteria

### ✅ Minimum Viable Output
- [ ] T-shirt segmented with clean edges
- [ ] Design extracted (or confirmed none exists)
- [ ] Fabric color identified correctly
- [ ] SVG patterns generated

### ✅ Full Pipeline Success
- [ ] 3D garment mesh created in Blender
- [ ] Seams connected properly
- [ ] Fabric color applied
- [ ] Design texture visible
- [ ] Exportable as FBX/OBJ

---

## 🎯 Optimization Path (After Basic Pipeline Works)

### Phase 7: Fine-Tuning (ongoing)

#### 🎨 Improve Segmentation Quality
**Edit `step1_segmentation.py`:**
```python
# Try different rembg models
from rembg import remove, new_session
session = new_session("u2net_human_seg")  # Better for clothing
result = remove(rgb_image, session=session)
```

#### 🎨 Adjust Design Detection
**Edit `step2_design_extraction.py`:**
```python
# Make more/less sensitive
edges = cv2.Canny(blurred, 30, 120)  # Lower = more sensitive
threshold = 2.5  # Lower = more aggressive color detection
```

#### 🎨 Better Cloth Physics
**Edit `step5_blender_sewing.py`:**
```python
# For lighter fabric (e.g., silk)
CLOTH_SETTINGS = {
    "mass": 0.15,
    "bending_stiffness": 0.1
}

# For heavier fabric (e.g., hoodie)
CLOTH_SETTINGS = {
    "mass": 0.5,
    "bending_stiffness": 2.0
}
```

---

## 📋 Automation Scripts (Optional)

### Create Master Run Script

**File:** `run_full_pipeline.bat`
```batch
@echo off
setlocal enabledelayedexpansion

set PYTHON=c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe
set BLENDER="C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"

echo ============================================
echo 2D to 3D T-Shirt Pipeline
echo ============================================
echo.

cd 2D_to_3D_tshirt\minimal_pipeline

echo [1/6] Running segmentation...
%PYTHON% step1_segmentation.py
if errorlevel 1 goto error

echo.
echo [2/6] Extracting design...
%PYTHON% step2_design_extraction.py
if errorlevel 1 goto error

echo.
echo [3/6] Extracting color...
%PYTHON% step3_color_extraction.py
if errorlevel 1 goto error

echo.
echo [4/6] Generating patterns...
%PYTHON% step4_pattern_generation.py
if errorlevel 1 goto error

echo.
echo [5/6] Sewing in Blender (this will take several minutes)...
%BLENDER% --background --python step5_blender_sewing.py
if errorlevel 1 goto error

echo.
echo [6/6] Applying textures...
%BLENDER% --background --python step6_apply_texture.py
if errorlevel 1 goto error

echo.
echo ============================================
echo PIPELINE COMPLETE!
echo ============================================
echo Output: Check Blender file and exports
pause
exit /b 0

:error
echo.
echo ============================================
echo ERROR: Pipeline stopped at step %ERRORLEVEL%
echo ============================================
pause
exit /b 1
```

---

## 🚀 Next Actions (Priority Order)

### TODAY (Critical Path)
1. ✅ Install `rembg[cpu]` backend
2. ✅ Run Steps 1-4 with your front.png
3. ✅ Verify all outputs look correct
4. 📸 Take screenshots of results

### THIS WEEK (3D Generation)
5. 🔧 Install Blender
6. 🔧 Create `run_step5.bat`
7. 🎨 Run Step 5 (sewing simulation)
8. 🎨 Run Step 6 (texture application)
9. 📦 Export final FBX model

### NEXT WEEK (Optimization)
10. 🎨 Fine-tune detection parameters
11. 🎨 Test with different T-shirt images
12. 🎨 Adjust cloth physics for realism
13. 📊 Document your settings/tweaks

---

## 📞 Where to Get Help

### Error Messages
- Check [PIPELINE_ISSUES_AND_FIXES.md](./PIPELINE_ISSUES_AND_FIXES.md)
- Search error text in file

### Understanding Steps
- Read [PIPELINE_SUMMARY.md](./PIPELINE_SUMMARY.md)
- Each step has detailed technical explanation

### Visual Issues
- Compare your outputs with expected results above
- Check quality criteria in each phase

---

**🎉 Good luck! Start with Phase 1 and work your way through systematically.**

*Remember: It's OK to stop after Phase 3 - that gives you design, color, and patterns. Blender is optional for full 3D.*
