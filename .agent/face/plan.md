# Face Personalization — Implementation Plan

**Status**: Planning complete, ready to implement  
**Approach**: Option A (texture) ships first. Option B (geometry) added once CLO face morph path is confirmed.

---

## What We Know for Certain

### The .avt structure
```
base-1.avt  (zip file)
├── first.dan                      33MB binary — avatar geometry (body + head mesh)
│                                  Contains 57 float "feature values" — ALL are body
│                                  measurements. Zero face morph params confirmed.
├── MV2_Jinho_01_face.jpg          2048x2048 RGB — face COLOR texture  ← Option A
├── MV2_Jinho_01_face_normal.jpg   2048x2048 RGB — face surface detail ← Option A
├── MV2_Jinho_01_face_roughness.jpg 2048x2048 RGB — face shininess
└── clofiles.json                  path metadata
```

### Already installed in .venv
- `opencv-python 4.10` — image processing, warp, Poisson blend
- `pillow 10.4` — image I/O
- `numpy 1.26` — array ops
- `trimesh 4.11` — 3D mesh (Option B)
- **Missing**: `mediapipe` — install before Option A code

### CLO3D face geometry finding
The 57 `listFeatureValues` floats in `first.dan` are confirmed body-only measurements.
CLO's face geometry path is UNKNOWN — waiting on external input.

---

## Option A — Texture Replacement (ship first)

### What it does
Takes user's front-facing selfie. Extracts their face. Warps it to fit the
avatar's UV face texture layout. Poisson-blends it in. Swaps the texture
file inside the .avt zip. The avatar now has the user's actual face appearance.

### Pipeline
```
front_photo.jpg
    │
    ▼
[A1] detect.py — MediaPipe FaceMesh (Apache 2.0)
     Input : front photo (any resolution)
     Output: 478 (x,y) landmark points on photo
             face bounding polygon (forehead → jaw → cheeks)
             confidence score per landmark
    │
    ▼
[A2] extract.py — OpenCV
     Input : photo + landmarks
     Steps :
       1. Compute minimal bounding polygon around face landmarks
       2. Perspective-warp: face polygon → flat 512x512 canonical square
          (removes head tilt, perspective distortion)
       3. Histogram normalize (stabilize lighting/color)
     Output: flat_face.png — user face, upright, lighting normalized
    │
    ▼
[A3] uv_map.py — OpenCV
     Input : flat_face.png + uv_face_region (from templates/base-1-face-uv.json)
     Steps :
       1. Load UV face polygon from template file
          (describes which pixels in 2048x2048 = the face skin region)
       2. Perspective-warp flat face → UV polygon shape
     Output: face_uv.png — user face warped to match avatar UV geometry
    │
    ▼
[A4] blend.py — OpenCV seamlessClone (Poisson blending)
     Input : face_uv.png + original MV2_Jinho_01_face.jpg
     Steps :
       1. Create mask: 1 inside UV face polygon, 0 outside, feathered edge
       2. cv2.seamlessClone(face_uv, base_face_jpg, mask) → Poisson blend
          Eliminates hard edges. Lighting/color adapts at boundary.
     Output: personalized_face.jpg — 2048x2048, user face on avatar canvas
    │
    ▼
[A5] avt_face.py — zipfile (stdlib)
     Input : source_avt + personalized_face.jpg
     Steps :
       1. Read source .avt zip (same approach as avt_patch.py)
       2. Replace MV2_Jinho_01_face.jpg with personalized_face.jpg
       3. (Optional) generate basic normal map from face texture, swap normal jpg
       4. Write output .avt zip
     Output: personalized_avatar.avt
```

### The UV template question
`uv_map.py` needs to know where the face polygon lives on the 2048x2048 canvas.
**How we find it**: Run MediaPipe on `MV2_Jinho_01_face.jpg` itself — the avatar's
face texture IS a painted UV map, so MediaPipe will detect the face region in UV
space automatically. Store result in `templates/base-1-face-uv.json`.
This is automated — no manual annotation needed.

### Module files
```
clo_avatar_generation/face/
├── __init__.py
├── detect.py          MediaPipe: photo → 478 landmarks
├── extract.py         OpenCV: landmarks → flat canonical face (512x512)
├── uv_map.py          OpenCV: flat face → UV polygon space
├── blend.py           OpenCV Poisson: paste into 2048x2048 avatar canvas
├── avt_face.py        zipfile: swap face textures inside .avt
├── run_face.py        top-level: photo + avt_path → personalized_avt
└── templates/
    └── base-1-face-uv.json   UV face polygon for base-1.avt (auto-generated)
```

### Integration
```
avatar_runtime/pipeline.py   — add step_12 as optional step after step_11
avatar_runtime/step_12_apply_face.py  — calls run_face.py
avatar_runtime/context.py    — add: face_photo_path, face_avt_path fields
run_avatar.py                — add: --face-photo optional CLI arg
```

Step 12 is **optional**: if `--face-photo` is not provided, pipeline skips it.

### Dependencies to install
```bash
pip install mediapipe
```
That's it. Everything else is already in the venv.

---

## Option B — Geometry Morphing (implement after Option A)

### Status: BLOCKED on one unknown
CLO3D's face geometry is NOT in the 57 feature values we already patch.
The face mesh is baked into `first.dan` as static vertices.

**Two possible paths — only one will be confirmed:**

#### Path B1 — CLO SetAvatarProperties with face key names (if it works)
CLO's Avatar Editor has face sliders. Those sliders might write to the
`SetAvatarProperties` REST API with specific key names like "Face Width",
"Jaw Width", etc. We know this API exists. We know it's unreliable for body
measurements (that's why we use binary patching). For face, it might work
because face params might be handled differently internally.

**To test B1**: Open CLO, use the REST API directly:
```
POST /avatar/set-properties
{"Face Width": "15.0", "Jaw Width": "12.5"}
```
See if the avatar's face changes. If yes → Path B1 works.

#### Path B2 — Binary diff to find face vertex offsets (if B1 fails)
Open CLO avatar editor → move face slider → export .avt → binary diff vs base.
If the diff shows changes in the `first.dan` at consistent offsets, we can patch
those offsets directly (same approach as body measurements).

**This is how we found body measurement indexes and it works reliably.**

### 3D face reconstruction model: 3DDFA_V2 (MIT license)
```
3 user photos (front, left 45°, right 45°)
    → 3DDFA_V2
    → face shape parameters:
        face_width, face_depth, jaw_width, nose_height,
        nose_width, cheekbone_width, forehead_width, chin_depth
    → map to CLO face parameter values
    → patch into .avt (via B1 or B2)
```

### Install 3DDFA_V2
```bash
git clone https://github.com/cleardusk/3DDFA_V2
cd 3DDFA_V2
pip install -r requirements.txt
python setup.py build_ext --inplace   # one-time Cython compile ~2 min
```

### Module files (added to face/)
```
clo_avatar_generation/face/
├── reconstruct.py     3DDFA_V2: 3 photos → face shape parameters
├── face_params.py     mapping: 3DDFA_V2 params → CLO face values
└── templates/
    └── base-1-face-params.json   CLO face parameter key names + value ranges
```

### Option B pipeline
```
3 photos
    → reconstruct.py (3DDFA_V2) → face params dict
    → face_params.py → CLO-compatible values
    → avt_patch OR set-properties → geometry-morphed avatar.avt
    → THEN run Option A pipeline on top (texture)

Final output: avatar with correct face SHAPE + correct face TEXTURE
```

---

## Implementation Order

```
Week 1 — Option A complete
  Day 1:  install mediapipe, auto-generate base-1-face-uv.json
  Day 2:  detect.py + extract.py (landmark detection + face extraction)
  Day 3:  uv_map.py + blend.py (UV warp + Poisson blend)
  Day 4:  avt_face.py + run_face.py (end-to-end test)
  Day 5:  step_12_apply_face.py + pipeline integration, test full run

Week 2 — Option B discovery
  Day 1:  install 3DDFA_V2, test on sample photos
  Day 2:  test CLO SetAvatarProperties with face key names (Path B1)
  Day 3:  if B1 fails → binary diff to find face vertex offsets (Path B2)
  Day 4:  reconstruct.py + face_params.py
  Day 5:  end-to-end test: geometry + texture combined
```

---

## Final Combined Pipeline

```
INPUT
  user_id           → body measurements (existing pipeline)
  front_photo.jpg   → face texture (Option A)
  left_photo.jpg    → face geometry (Option B, optional)
  right_photo.jpg   → face geometry (Option B, optional)

STEPS 1-11  →  body-morphed avatar.avt  (existing, unchanged)
STEP 12     →  geometry-morphed avatar.avt  (Option B, if available)
STEP 13     →  texture-personalized avatar.avt  (Option A, always)

OUTPUT
  personalized_avatar.avt  — correct body shape + face geometry + face texture
```

---

## What Needs to Happen Before Writing Code

1. **Install mediapipe** → `pip install mediapipe`  (30 seconds)
2. **Auto-generate UV template** → run MediaPipe on MV2_Jinho_01_face.jpg
   → confirms MediaPipe detects face in UV texture → saves base-1-face-uv.json
3. **Get a test selfie** → any front-facing photo to test the pipeline end-to-end

That's it for Option A. Start coding after those 3 things.

For Option B:
4. **Test CLO SetAvatarProperties face keys** → need CLO running
5. **Install 3DDFA_V2** → git clone + pip install + cython build
