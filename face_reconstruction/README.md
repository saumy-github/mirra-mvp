# Face reconstruction

1–3 face photos → `face.glb`: a textured, metric face mesh that the web viewer
places on the shopper's avatar head (profile avatar page and studio try-on).
Everything used is Apache-2.0 (MediaPipe Face Landmarker + its canonical face
model), so there is no research-only licence in this layer.

```
front (+ left/right ~45°) photos
  → MediaPipe Face Landmarker: 478 landmarks per photo (landmarks.py)
  → per view: metric scale from the iris (11.7 mm), rigid alignment onto the
    canonical face, depth relief bounded to ±15% (monocular depth is the weak axis)
  → fuse: per-vertex weighted mean (weight = how squarely each photo saw it)
  → texture: canonical UV atlas, each triangle warped from the photos that saw it
    at < ~70°, side photos colour-matched to the front, rim filled and feathered
  → face.glb (glb.py) with extras.mirra_face {noseTip, widthM, skinToneHex, …}
```
The viewer (`website/frontend/src/features/profile/components/face-attachment.ts`)
finds the avatar's nose (front-most point at nose height), which way it faces
(toes) and its head width, then places the face nose-tip to nose-tip, 4 mm proud,
shrinking it only if it is wider than the head.

## What it is / isn't
- A personalised **face** (forehead to chin, cheek to cheek) on the stock CLO head.
  Hair, ears, skull shape and the back of the head are CLO's.
- The expression in the front photo is baked in — the capture guidance asks for a
  relaxed face with lips together.
- Body skin colour is not yet tinted to match the face (`skinToneHex` is recorded
  for that).

## Run
```bash
python face_reconstruction/run_face_reconstruction.py --front f.jpg [--left l.jpg --right r.jpg] --out face.glb
python -m pytest face_reconstruction/tests
```
The website path: `POST /api/v1/faces` (or the phone's QR link) → `measure`
queue → `worker/face_tasks.py`. The model (`models/face_landmarker.task`, 3.7 MB)
is downloaded on first use.
