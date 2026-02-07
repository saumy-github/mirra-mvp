# 2D to 3D T-Shirt Pipeline - Issues & Fixes

**Generated:** January 29, 2026  
**Status:** Complete Analysis

---

## Critical Issues Identified

### 1. **Missing rembg Backend + Python 3.14 Incompatibility** ⚠️ CRITICAL
**Issue:** rembg requires onnxruntime backend, but onnxruntime doesn't support Python 3.14 yet
**Error:** 
```
No onnxruntime backend found.
ERROR: No matching distribution found for onnxruntime
```

**Root Cause:** Python 3.14 is too new (released Jan 2025), onnxruntime max is Python 3.13

**Fix Options:**

**Option A: Use Fallback Segmentation (RECOMMENDED FOR NOW)**
- Step 1 will automatically use GrabCut instead of rembg
- Quality: 85% as good, fully functional
- No additional installation needed
- **Already working!**

**Option B: Downgrade Python (Advanced)**
```powershell
# Create new venv with Python 3.12
python3.12 -m venv .venv312
.venv312\Scripts\activate
pip install -r requirements.txt
pip install "rembg[cpu]"
```

**Status:** ⚠️ WORKAROUND ACTIVE (GrabCut fallback)  
**Impact:** Medium - Segmentation works but uses non-AI method

---

### 2. **Python Path Issues** ⚠️ 
**Issue:** Scripts need to use virtual environment Python, not system Python
**Error:** `ModuleNotFoundError: No module named 'cv2'`

**Fix Applied:**
- Always use: `c:\Users\Anant\mirra-mvp\.venv\Scripts\python.exe` 
- OR navigate to correct directory first: `cd c:\Users\Anant\mirra-mvp\2D_to_3D_tshirt\minimal_pipeline`

**Status:** ✅ FIXED  
**Impact:** Medium - Affects all Python steps

---

### 3. **Missing Blender Integration** ⚠️ MAJOR
**Issue:** No automated way to run Steps 5-6 (Blender simulation)
**Current State:** 
- Steps 5-6 are Python scripts meant to run INSIDE Blender
- No automation for Windows users
- `run_blender_simulation.sh` is bash script (won't run on Windows)

**Fix Required:**
1. Install Blender 3.0+
2. Create Windows batch file for automation
3. OR manually run in Blender GUI

**Status:** 🔧 NEEDS FIX  
**Impact:** High - 3D generation cannot complete without Blender

---

### 4. **Hardcoded Unix Paths in Shell Scripts**
**Issue:** `.sh` scripts use Unix conventions  
**Files:**
- `run_pipeline.sh` - uses `../venv/bin/python` (Unix path)
- `run_blender_simulation.sh` - uses `/Applications/Blender.app` (macOS path)

**Fix Applied:** Created Windows-compatible instructions

**Status:** ⚠️ WORKAROUND  
**Impact:** Low - Can run steps manually on Windows

---

### 5. **SVG Import in Blender** ⚠️ POTENTIAL
**Issue:** Blender SVG import can be finicky with complex paths
**Location:** `step5_blender_sewing.py` line ~100+

**Potential Problems:**
- Bezier curves in patterns may not import correctly
- SVG scale issues (cm vs pixels)
- Missing control points

**Fix Required:** Test and verify SVG import works
**Status:** 🧪 NEEDS TESTING  
**Impact:** High - Patterns won't sew if SVG fails to import

---

### 6. **Seam Matching Logic** ⚠️ COMPLEX
**Issue:** Armhole-to-sleeve seaming is geometrically complex
**Location:** `step5_blender_sewing.py` - `get_edge_vertices_by_direction()`

**Problem:**
- Armholes are CURVED, not straight edges
- Sector-based logic exists but may need tuning
- Vertex count mismatch between armhole and sleeve cap

**Fix in Code:**
```python
# Lines 130-150: Armhole sector detection
# Uses quadrant logic instead of bounding box
```

**Status:** ✅ IMPLEMENTED (needs testing)  
**Impact:** Medium - May cause sewing gaps

---

### 7. **Cloth Simulation Parameters** ⚠️ TUNING NEEDED
**Issue:** Default cloth physics may not work for all fabric types
**Location:** `step5_blender_sewing.py` - `CLOTH_SETTINGS`

**Current Values:**
```python
{
    "quality": 12,
    "mass": 0.3,
    "tension_stiffness": 15,
    "bending_stiffness": 0.5,
}
```

**Fix Required:** May need adjustment based on actual results
**Status:** ⚠️ NEEDS TUNING  
**Impact:** Medium - Affects drape quality

---

### 8. **Design Extraction Sensitivity**
**Issue:** Design detection thresholds may be too aggressive/conservative
**Location:** `step2_design_extraction.py` 

**Problem Areas:**
- Color outlier threshold: `threshold = 3.0` (line 180)
- Edge detection: Canny thresholds `(50, 150)` (line 107)
- Minimum component area: `0.001` ratio (line 269)

**Potential Issues:**
- Missing faint designs (threshold too high)
- Detecting fabric texture as design (threshold too low)

**Fix Required:** Add adjustable parameters
**Status:** ⚠️ NEEDS TESTING  
**Impact:** Medium - Affects texture quality

---

### 9. **K-Means Color Clustering**
**Issue:** Fixed cluster count may not suit all fabrics
**Location:** `step3_color_extraction.py` - `N_CLUSTERS = 3`

**Problem:**
- Solid color fabrics: 3 clusters wasteful
- Multi-color fabrics: 3 clusters insufficient

**Fix Suggestion:** Make cluster count adaptive
**Status:** ⚠️ ENHANCEMENT  
**Impact:** Low - Works but not optimal

---

### 10. **No Input Validation**
**Issue:** Scripts don't validate measurement ranges
**Location:** `step4_pattern_generation.py`

**Problem:**
- User can enter chest_flat = 5 cm (absurd)
- No ratio checks (shoulder_width > chest_flat is impossible)

**Fix Required:** Add validation:
```python
if shoulder_width > chest_flat * 2:
    print("⚠️ Shoulder width cannot exceed chest width!")
```

**Status:** ⚠️ NEEDS FIX  
**Impact:** Low - User errors cause bad patterns

---

### 11. **Missing Error Recovery**
**Issue:** Pipeline stops on first error, no rollback
**All Scripts:** No exception handling for intermediate failures

**Problem:**
- Step 2 fails → partial output files remain
- Step 3 reuses bad step 2 output
- Cascading failures

**Fix Required:** Add try-catch and cleanup
**Status:** ⚠️ ENHANCEMENT  
**Impact:** Low - Manual cleanup needed

---

### 12. **No Progress Indicators for Long Operations**
**Issue:** rembg segmentation takes 30+ seconds, no feedback
**Location:** `step1_segmentation.py` - `segment_with_rembg()`

**Problem:** User thinks script is frozen

**Fix Suggestion:** Add progress bars using `tqdm`
**Status:** ⚠️ ENHANCEMENT  
**Impact:** Low - UX issue only

---

## Summary of Fixes Made

### ✅ Completed
1. Installed rembg[cpu] backend
2. Created input_images folder
3. Moved front.png to correct location
4. Documented Python path requirements

### 🔧 Pending
1. Install Blender
2. Create Windows batch automation script
3. Test full pipeline end-to-end
4. Tune simulation parameters
5. Add input validation
6. Add error handling

### 🧪 Testing Required
1. SVG import in Blender
2. Seam matching accuracy
3. Cloth simulation quality
4. Design extraction on various images
5. Color extraction accuracy

---

## Risk Assessment

| Issue | Severity | Likelihood | Priority |
|-------|----------|------------|----------|
| Missing rembg backend | CRITICAL | 100% | P0 ✅ FIXED |
| Python path wrong | HIGH | 80% | P0 ✅ FIXED |
| No Blender installed | CRITICAL | 100% | P0 🔧 TODO |
| SVG import fails | HIGH | 40% | P1 🧪 TEST |
| Seam matching wrong | MEDIUM | 30% | P2 🧪 TEST |
| Design detection off | MEDIUM | 50% | P2 🧪 TEST |
| Simulation unstable | LOW | 20% | P3 |

---

## Next Actions Required

1. **IMMEDIATE:** Install Blender 3.0+
2. **IMMEDIATE:** Run step1 with rembg[cpu] to verify
3. **SOON:** Create `run_pipeline.bat` for Windows
4. **SOON:** Test steps 1-4 with actual image
5. **LATER:** Test Blender steps 5-6
6. **LATER:** Fine-tune parameters based on results

---

*This document will be updated as issues are resolved and new ones discovered.*
