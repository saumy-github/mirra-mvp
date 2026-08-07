# Face Personalization — `clo_avatar_generation/face/`

## Goal

Make the CLO3D avatar's face look exactly like the user's face.

This is the core USP of Mirra: the avatar is a true replica of the user's
face — matching face structure, geometry, and skin texture — not just a
generic avatar with a photo pasted on it.

The pipeline takes 3 photos of the user's face and produces a modified `.avt`
file where the avatar head geometry and texture have been replaced with the
user's reconstructed face.

---

## Input: 3 Face Photos

| Photo | Direction | Purpose |
|---|---|---|
| Photo 1 | Front facing | Full face texture + geometry baseline |
| Photo 2 | Left 45 degrees | Left cheek, nose profile, jaw depth |
| Photo 3 | Right 45 degrees | Right cheek, symmetry correction |

3 photos is the minimum to reconstruct accurate face geometry. 1 photo gives
~75% accuracy (recognizable but not exact). 3 photos gives ~90% accuracy
(clearly that person, matching face structure).

**Photo requirements:**
- Good natural lighting, no harsh shadows
- Neutral expression
- Hair pulled back ideally
- No glasses

---

## How It Works

```
3 face photos (front, left 45°, right 45°)
    → detect.py         # MediaPipe Face Mesh — extract landmarks from each photo
    → reconstruct.py    # DECA + FLAME — build 3D face mesh + texture from 3 photos
    → head_blend.py     # replace avatar head geometry with reconstructed face mesh
    → blend.py          # Poisson blend face texture into head texture atlas
    → avt_patch.py      # unzip .avt, swap geometry + texture, rezip
```

Output: a modified `.avt` file with the user's face geometry and texture
applied to the avatar head.

---

## Reconstruction Approach: Two Options

### Option A — DECA + FLAME

DECA is a neural network that reads face photos and outputs a complete 3D face.
FLAME is the underlying parametric face model DECA uses — a mathematical
formula with dials for jaw width, nose shape, cheekbone height, skin texture,
and fine surface detail.

**Output quality:**
- ~90-95% face accuracy
- Automatically extracts UV face texture from photos
- Captures fine details: wrinkles, pores, skin variation
- Native multi-photo (3 photo) support

**Libraries:**

| Library | Purpose |
|---|---|
| `mediapipe` | Face landmark detection — pre-trained, ships ready |
| `DECA` | 3D face reconstruction — download pre-trained weights (~300MB) |
| `FLAME` | Parametric face model used by DECA — free academic registration |
| `trimesh` or `open3d` | Mesh blending at head/neck seam |
| `opencv-python` | Geometric transforms, Poisson blending |
| `pillow` | Image I/O and texture patching |
| `zipfile` (stdlib) | `.avt` is a zip archive |

**Known issues with DECA + FLAME:**

1. **Non-commercial license** — both DECA and FLAME are research-only. Using
   them in a commercial product (which Mirra is) is not permitted without a
   separate commercial license from MPI-IS. This is a legal risk, not just a
   technicality.


2. **Commercial license is not straightforward** — MPI-IS does offer commercial
   licensing for FLAME but it requires direct negotiation with the research
   group. No self-serve option, no fixed pricing, timeline is unpredictable.

3. **DECA has no commercial license path at all** — the DECA repo explicitly
   states research/non-commercial use only. There is no paid tier.

4. **Dependency fragility** — DECA depends on a specific version of PyTorch and
   specific FLAME model file versions. Version mismatches break silently and
   are hard to debug, especially on Apple Silicon (M1/M2).

5. **Setup friction** — FLAME requires manual registration and file placement.
   DECA requires downloading weights separately and pointing config files at
   them. Not a simple `pip install`.

6. **Slow on CPU** — DECA takes ~5-10 seconds per photo on CPU. For 3 photos
   that is 15-30 seconds per user. Acceptable for now but will become a
   bottleneck at scale.

---

### Option B — 3DDFA_V2 + Manual Texture Extraction

3DDFA_V2 is a fast, lightweight 3D face alignment model. It fits a face mesh
to photos accurately. It does not extract texture automatically — that is
handled separately with MediaPipe + OpenCV (~100 lines of code).

**Output quality:**
- ~80-85% face accuracy
- Geometry is strong, fine detail (wrinkles, pores) is not captured
- Texture extraction written manually but straightforward

**Libraries:**

| Library | Purpose |
|---|---|
| `mediapipe` | Face landmark detection — pre-trained, ships ready |
| `3DDFA_V2` | 3D face mesh fitting — MIT license, commercial safe |
| `trimesh` or `open3d` | Mesh blending at head/neck seam |
| `opencv-python` | Texture extraction, Poisson blending |
| `pillow` | Image I/O and texture patching |
| `zipfile` (stdlib) | `.avt` is a zip archive |

**Advantages over DECA + FLAME:**
- MIT license — fully commercial safe, no negotiation needed
- Fast — ~0.5s per photo on CPU
- Simple `pip install` setup, no manual file placement
- You own the texture extraction code — no black box

**Known issues with 3DDFA_V2:**
- Does not extract texture automatically — you write it yourself
- Fine surface detail (wrinkles, pores) not captured
- Slightly lower geometric accuracy than DECA for edge cases (very wide
  faces, strong asymmetry)

---

## Recommended Approach

Start with **Option B (3DDFA_V2)** for the following reasons:

1. Commercially safe from day one — no legal risk
2. Faster to set up and ship
3. The texture extraction gap (~100 lines of OpenCV) is bridgeable
4. The 5-10% accuracy difference is acceptable for VTO where the camera
   focus is on the garment, not the face

Revisit **Option A (DECA + FLAME)** only if:
- A commercial FLAME license is negotiated
- Face accuracy becomes a user-reported complaint
- A DECA commercial alternative emerges

---

## Libraries Used (Option B — current plan)

No ML training. No GPU required. All models are pre-trained.

| Library | Purpose |
|---|---|
| `mediapipe` | Face landmark detection — pre-trained, ships ready |
| `3DDFA_V2` | 3D face mesh from photos — MIT license |
| `trimesh` or `open3d` | Mesh blending at head/neck seam |
| `opencv-python` | Texture extraction, Poisson blending |
| `pillow` | Image I/O and texture patching |
| `zipfile` (stdlib) | `.avt` is a zip archive |

CPU inference is sufficient for a single user's 3 photos.

---

## Module Layout

```
face/
├── README.md               # this file
├── __init__.py
├── detect.py               # MediaPipe — extract landmarks from all 3 photos
├── reconstruct.py          # DECA + FLAME — 3D face mesh + texture from 3 photos
├── head_blend.py           # replace avatar head geometry with reconstructed mesh
├── blend.py                # Poisson blend face texture into head texture atlas
├── avt_patch.py            # unzip .avt, swap geometry + texture, rezip
└── templates/
    └── base-1-face-uv.png  # UV face region mask for base-1.avt
```

---

## Integration Point

Called from a single place in the avatar pipeline:

```
clo_avatar_generation/avatar_runtime/step_12_apply_face.py
```

That step knows only:

```
input:  [front_photo, left_photo, right_photo], avt_path
output: personalized_avt_path
```

---

## Design Rules

1. Everything face-related lives inside `face/`. Nothing outside this folder
   changes when the face pipeline is updated.

2. `step_12_apply_face.py` is the only external caller.

3. No ML training. Pre-trained DECA weights are downloaded once and cached.

4. No GPU required. CPU inference is fine for per-user reconstruction.

---

## What Needs to Happen First

Before writing any code, the `.avt` file structure must be understood:

1. Unzip `avt_templates/base-1.avt`
2. Find the head geometry file and head texture file inside the archive
3. Identify the UV face region on the texture atlas
4. Create `templates/base-1-face-uv.png` — a mask marking the face UV region

This is the only manual setup step. Everything else is automated.