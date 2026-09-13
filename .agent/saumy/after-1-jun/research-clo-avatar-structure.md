# CLO Avatar & Project Structure — Research Summary
*Last updated: 2026-07-02*

**Purpose**: Document what we know about CLO `.avt` (avatar) and `.zprj` (project) file formats, current field mappings, and what's needed for female avatars.

**Last Updated**: 2026-07-02  
**Scope**: Male (v1 confirmed), Female (reserved, not active)

---

## Part 1: Avatar File Structure (.avt)

### Format Overview

`.avt` files are **binary containers with embedded ZIP archives**.

```
[Binary Prefix] + [ZIP Archive]
 (~N bytes)       (PK\x03\x04 marker)
```

**Anatomy**:
1. **Prefix**: CLO-specific binary header (size varies, unknown exact purpose)
2. **ZIP Marker**: Located at byte offset where `PK\x03\x04` first appears
3. **ZIP Contents**: Standard ZIP format containing:
   - `.dan` file (measurement/deformation data)
   - Other CLO metadata files

**How We Detect The Boundary**:
```python
zip_start = raw.find(b"PK\x03\x04")  # Find ZIP signature
prefix = raw[:zip_start]               # Everything before ZIP
zip_archive = raw[zip_start:]          # ZIP and everything after
```

---

## Part 2: Feature Block Inside .dan File

### Structure

Inside the `.dan` file (which is a binary blob inside the ZIP), there is a **feature value block** — a list of 57 consecutive 4-byte IEEE 754 floats (little-endian).

**How to Locate It**:

```
1. Find the marker: b"listFeatureValues" in .dan bytes
2. marker_offset = .dan.find(b"listFeatureValues")
3. feature_block_start = marker_offset + len("listFeatureValues") + 273
4. Each feature is a 4-byte float at: feature_block_start + (index * 4)
```

**Constants** (from `avt_patch.py`):
```python
LIST_FEATURE_VALUES_MARKER = b"listFeatureValues"
LIST_FEATURE_VALUES_OFFSET = 273  # Bytes after marker
LIST_FEATURE_VALUES_COUNT = 57    # Total feature slots
```

### The 57 Feature Slots

**Total slots available**: 57  
**Currently mapped**: 6 (male only, v1)  
**Unmapped/unknown**: 51

| Slot Index | Measurement (Male) | CLO Name | Unit | Apply Routes | Status |
|---|---|---|---|---|---|
| **0** | `height_cm` | Total Height | cm | avt_patch, properties, csv | ✅ Working |
| **2** | `chest_circumference_cm` | Chest | cm | avt_patch, properties, csv | ✅ Working |
| **6** | `waist_circumference_cm` | Waist | cm | avt_patch, properties, csv | ✅ Working |
| **8** | `hip_circumference_cm` | Low Hip | cm | avt_patch, properties, csv | ✅ Working |
| **26** | `leg_length_cm` | Inseam | cm | avt_patch, properties, csv | ✅ Working |
| **36** | `shoulder_width_cm` | Across Shoulder (Curvilinear) | cm | avt_patch, properties, csv | ✅ Working |
| **?** | `weight_kg` | Weight | kg | csv_bridge only | ⚠️ No index |
| **?** | `bust_circumference_cm` | Bust | cm | (reserved, female) | ❓ Unknown |
| **?** | `under_bust_circumference_cm` | Under Bust | cm | (reserved, female) | ❓ Unknown |
| **1–5, 3–5, 7, 9–25, 27–35, 37–56** | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | ❓ Unmapped |

### Verified Working Example

**Run u_001-028 & u_001-031** (male avatar):
Binary roundtrip verification:
- Height (index 0): Write 178.5 → Read back 178.5 ✅
- Chest (index 2): Write 100.0 → Read back 100.0 ✅
- Waist (index 6): Write 85.0 → Read back 85.0 ✅
- Hip (index 8): Write 98.0 → Read back 98.0 ✅
- Inseam (index 26): Write 90.0 → Read back 90.0 ✅
- Shoulder (index 36): Write 45.0 → Read back 45.0 ✅

**Verification Status**: Feature slots reliably store and return the exact values written. Verified by reading extracted `.avt` files post-morph. User visual inspection of CLO confirms values are applied correctly (avatars display correct measurements in CLO's edit mode).

---

## Part 3: Measurement Application Routes

CLO supports three routes to apply measurements to an avatar:

### Route 1: `avt_patch` (Binary Direct) ✅ **Most Reliable**

**How it works**:
- Directly write float values into the binary feature slots
- Bypass CLO's API entirely
- CLO loads an already-morphed `.dan` file

**Code Path** (`avt_patch.py`):
```python
1. Read base .avt → split prefix + ZIP members
2. Extract .dan from ZIP
3. Locate feature block by marker
4. For each field: struct.pack_into("<f", dan_buffer, offset, value)
5. Write modified .dan back to ZIP
6. Write prefix + new ZIP back to .avt
```

**Verification**:
- Read back the patched `.avt` file
- Compare feature values to requested values
- Tolerance: 0.05 cm (any value within 0.05 cm is considered "match")
- Status: **100% success rate** across all male fields

**Limitation**: Only works for fields with known feature indices. Weight has no index yet.

---

### Route 2: `avatar_properties` (CLO API) ❌ **Currently Broken**

**How it works**:
- Call CLO's `/avatar/set-properties` endpoint
- Send key-value pairs: `{"Chest": 100, "Waist": 85, ...}`
- CLO's SetAvatarProperties() is called on the main thread

**Why it's broken** (from runs 007, 009, 010):
- CLO accepts the HTTP call (returns HTTP 200)
- Reports `"changed": 0` in response
- Missing keys: `["Chest", "Waist", "Total Height", ...]`
- Confirmation read returns empty properties
- **Conclusion**: CLO's `SetAvatarProperties` does not map our body measurement keys to body shape
- It only handles internal physics properties (friction, skin offset, etc.)

**Status**: Considered a false positive — appears to succeed but avatar is not morphed.

---

### Route 3: `csv_bridge` (CSV Import) ❌ **Broken**

**How it works**:
- Build a 2-row CSV file with headers and values
- Call CLO's `/import-avatar-measurements` or `ImportMeasurement()` API
- CLO parses CSV and applies measurements

**Current CSV Template** (measurement_template_unconfirmed.csv):
```csv
Total Height,Weight,Waist,Low Hip,Inseam,Bust,Under Bust,Neck Base,Bicep,Across Shoulder (Curvilinear),Arm
170,65,78,94,79,92,80,36,30,42,58
```

**Why it's broken**:
- Column names are "unconfirmed" (documentation says so)
- In 2024-2025 testing, the CSV route always failed
- Some measurements silently unmatched (e.g., CLO has "Bust" not "Chest")
- Column count mismatch or name mismatch with CLO's internal expectations

**Status**: Never worked. Marked as "broken, not retryable" in the field contract.

---

## Part 4: Current Male Field Contract (v1)

### Included in v1

```json
{
  "version": "v1-draft",
  "scope": "male_only",
  "unit": "cm",
  "fields": [
    {
      "mongo_field": "height_cm",
      "clo_target": "Total Height",
      "avt_feature_index": 0,
      "apply_routes": ["avt_patch", "avatar_properties", "csv_bridge"]
    },
    {
      "mongo_field": "weight_kg",
      "clo_target": "Weight",
      "apply_routes": ["csv_bridge"],  // ← CSV only, NO feature index
      "notes": "No verified feature index yet"
    },
    {
      "mongo_field": "shoulder_width_cm",
      "clo_target": "Across Shoulder (Curvilinear)",
      "avt_feature_index": 36
    },
    {
      "mongo_field": "chest_circumference_cm",
      "clo_target": "Chest",
      "avt_feature_index": 2
    },
    {
      "mongo_field": "waist_circumference_cm",
      "clo_target": "Waist",
      "avt_feature_index": 6
    },
    {
      "mongo_field": "hip_circumference_cm",
      "clo_target": "Low Hip",
      "avt_feature_index": 8
    },
    {
      "mongo_field": "leg_length_cm",
      "clo_target": "Inseam",
      "avt_feature_index": 26
    }
  ]
}
```

### Reserved for v2+ (Female)

```json
{
  "mongo_field": "bust_circumference_cm",
  "clo_target": "Bust",
  "included_in_v1": false,
  "genders": ["female"],
  "avt_feature_index": null  // ← UNKNOWN, not discovered yet
},
{
  "mongo_field": "under_bust_circumference_cm",
  "clo_target": "Under Bust",
  "included_in_v1": false,
  "genders": ["female"],
  "avt_feature_index": null  // ← UNKNOWN, not discovered yet
}
```

---

## Part 5: Female Avatar Support (Not Yet Implemented)

### What We Need to Discover

For female avatars, we need to find:

1. **Feature indices for**:
   - Bust circumference (likely index in 0–56, TBD)
   - Under Bust circumference (likely index in 0–56, TBD)

2. **Which other measurements differ**:
   - Do chest/waist/hip have different semantics for female?
   - Does weight play a larger role in female morphing?
   - Are there female-specific measurements not applicable to male? (e.g., back width, frame width)

3. **Base avatar template**:
   - Is there a female equivalent to `base-1.avt`?
   - Does it use the same feature indices, or different ones?
   - What height/weight range is the female base template?

4. **Gender-specific feature indices**:
   - Are feature indices shared (same slot means same thing for male/female)?
   - Or are they gender-specific (index 0 means different things for male vs. female)?

### Current Status

- **Male**: 6/7 fields working (height, chest, waist, hip, inseam, shoulder, weight)
- **Female**: 0/9 fields implemented. Bust and Under Bust reserved but not mapped.
- **Validation**: No female base avatar in repo yet. No female measurements in test data yet.

---

## Part 6: Project File (.zprj)

### Format

`.zprj` files are **standard ZIP archives** (same as `.zip`).

**Contents**:
- `.avt` file (the avatar inside the project)
- Garment/pattern files (`.dxf`, fabric definitions, etc.)
- Project metadata (`.xml` or JSON)
- Simulation cache files

**How to Extract**:
```python
import zipfile
with zipfile.ZipFile("project.zprj", "r") as z:
    z.extractall("output/")
```

### Why We Use It

In Step 11 (Save Outputs), we:
1. Call CLO's `/save-project` endpoint → writes `.zprj` file
2. Unzip the `.zprj` → extract the `.avt` inside
3. Return the extracted `.avt` as the primary output

**Why not use `/export-avatar-avt`**?
- Windows: `ExportAVT()` raises SEH exceptions (crashes CLO main thread)
- Mac: Works, but `.zprj` extraction is the fallback
- Both platforms: `.zprj` → extract `.avt` is the reliable workaround

---

## Part 7: Measurement Apply Strategy (v1 Working Approach)

### Step 8: Auto-Select Apply Route

```python
def select_apply_route(requested_fields):
    # Fields with feature indices use avt_patch (most reliable)
    avt_patch_fields = [f for f in requested_fields if f in AVT_FIELD_MAP]
    
    if avt_patch_fields:
        return "avt_patch"  # ← DEFAULT, works 100%
    
    # If no avt_patch fields available, try properties
    if CAPABILITIES["has_avatar_property_set"]:
        return "avatar_properties"  # ← FALLBACK, likely doesn't work
    
    # Last resort: CSV (known broken)
    return "csv_bridge"  # ← LAST RESORT, broken
```

**Current Result**: All male fields use `avt_patch` because they all have indices.

---

## Part 8: Known Limitations & Gaps

### Gaps in Current Understanding

1. **57 Feature Slots — 51 Unknown**
   - We've discovered 6 male measurements (indices 0, 2, 6, 8, 26, 36)
   - 51 other slots remain unmapped
   - No documentation from CLO on what they control

2. **Weight Has No Feature Index**
   - Applied via CSV only
   - Never verified after apply
   - CSV route is broken, so weight application is effectively broken

3. **Female Measurements Unmapped**
   - Bust, Under Bust: indices unknown
   - No female base avatar template
   - No female test data

4. **CSV Column Names Unconfirmed**
   - Current template: hardcoded guess
   - CLO's exact expected format: unknown
   - This is why CSV route fails

### Crash-Related Gaps

1. **SEH Exceptions on Windows**
   - `/avatars/state` (GetAvatarCount, etc.) — disabled in Step 9
   - `ExportAVT()` — disabled in Step 11
   - Both raise hardware exceptions that bypass C++ try/catch
   - Workaround: use sync-read (Windows just ported this), or unzip `.zprj` instead

---

## Part 9: Summary of What Works vs. What's Blocked

### ✅ Confirmed Working

| Item | Method | Gender | Evidence |
|------|--------|--------|----------|
| Height | avt_patch (index 0) | Male | Run u_001-028: delta = 0.0 |
| Chest | avt_patch (index 2) | Male | Run u_001-028: delta = 0.0 |
| Waist | avt_patch (index 6) | Male | Run u_001-028: delta = 0.0 |
| Hip | avt_patch (index 8) | Male | Run u_001-028: delta = 0.0 |
| Inseam | avt_patch (index 26) | Male | Run u_001-028: delta = 0.0 |
| Shoulder | avt_patch (index 36) | Male | Run u_001-028: delta = 0.0 |

### ❌ Confirmed Broken

| Item | Method | Gender | Issue |
|------|--------|--------|-------|
| Weight | csv_bridge | Male | No feature index; CSV route broken |
| Any field | avatar_properties | Male | API accepted but avatar not morphed |
| Any field | csv_bridge | Male | Column names unconfirmed, silently fails |
| Bust | (unknown) | Female | No feature index, no base avatar |
| Under Bust | (unknown) | Female | No feature index, no base avatar |

### ❓ Unknown

- 51 remaining feature slots and their purpose
- Female feature indices
- Whether feature indices are shared across genders
- Exact CSV format CLO expects
- Secondary measurements (arm length, back width, etc.)

---

## Part 10: CLO File Formats — What We Know

### Archive Formats (Binary ZIP)

| Format | Size | Content | Confirmed |
|--------|------|---------|-----------|
| `.avt` | 33 MB | Binary prefix + ZIP archive containing `.dan` file + textures (JPG) | ✅ Verified |
| `.zprj` | 35 MB | Binary prefix + ZIP archive containing avatar + garments + project metadata | ✅ Verified |
| `.zpac` | 100 KB | ZIP-based pattern/garment package | ✅ Format is ZIP |

**How we know**: Successfully extracted contents by finding ZIP signature `PK\x03\x04` and unzipping from that point.

### Binary Formats (Internal Structure Unknown)

| Format | Size | Purpose | What We Know |
|--------|------|---------|--------------|
| `.dan` | 33 MB | Avatar mesh + feature data (inside `.avt` ZIP) | Contains "listFeatureValues" marker followed by 57 float values |
| `.avs` | 2.9 KB | Avatar state serialization | Contains readable strings: "listFeatureValues", "BaseFeature", "bUseCupSize", bone names ("Right_shin", "Left_ankle", etc.) |
| `.iks` | 6.2 KB | IK skeleton/joint mapping | Contains joint names as readable strings (complete list visible in binary) |
| `.mea` | 425 B | Measurement data | Header contains "MEA" + "CLO", avatar ID, measurement markers |
| `.pos` | 163 KB | Position/transformation data | Unknown structure |
| `.vmp`, `.vlp`, `.vrp`, `.smp` | 1 KB–1.6 MB | Garment/pattern data | Unknown structure, proprietary CLO format |
| `.cmt`, `.cmp`, `.cpt`, `.osw` | Small | Project metadata | Unknown structure |

**Note**: These formats have no public documentation from CLO. Readable strings were identified via hex inspection, but actual structure is unknown.

### Text Formats

| Format | Size | Content | Verified |
|--------|------|---------|----------|
| `.json` | < 10 KB | UTF-8 JSON configuration (metadata, texture paths, settings) | ✅ Can parse and read |
| `.xml` | < 10 KB | UTF-8 XML environment definition (lighting, wind, camera, background) | ✅ Can parse and read |
| `.csv` | < 1 KB | Comma-delimited measurement values | ✅ Can read, but format is unconfirmed for CLO |
| `.obj` | 26 MB | Standard OBJ mesh format (vertices, normals, texture coords) | ✅ Standard OBJ, can read with standard tools |

### Summary

**Readable Formats**: `.json`, `.xml`, `.obj`, `.csv`  
**Extractable Archives**: `.avt`, `.zprj`, `.zpac`  
**Proprietary/Unknown**: `.dan`, `.avs`, `.iks`, `.mea`, `.pos`, `.vmp/.vlp/.vrp/.smp`, `.cmt/.cmp/.cpt/.osw`

---

## References

- `clo_avatar_generation/avatar_runtime/avt_patch.py` — Binary patching engine
- `clo_avatar_generation/schema/step1_field_contract.json` — Field definitions
- `clo_avatar_generation/avatar_runtime/step_08_apply_measurements.py` — Route selection
- `after-1-jun/summary-26-06-30-1.md` — Run history and route verdicts
- `clo_workspace/mac/RestPlugin_macOS.cpp` — CLO API signatures
- `clo_workspace/windows/RestPlugin_windows.cpp` — Windows sync-read port (Phase 1)
