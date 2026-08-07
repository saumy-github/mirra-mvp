# Face Personalization — Handoff

**Status as of 2026-08-07**: Core pipeline is implemented and runs end-to-end
(photos → personalized `.avt`). It has been exercised on one test subject
(`u_001`) with diagnostic tooling to inspect accuracy. It has **not** been
validated across varied skin tones, lighting conditions, or a second test
subject, and the geometry (face-shape) pass is a first cut, not tuned.

This doc is the entry point for whoever picks this up next. Read this before
`README.md` / `plan.md` in this folder — those two describe the **original
plan** (DECA/FLAME, then 3DDFA_V2 reconstruction + UV bake). The plan changed
during implementation; see "How the approach diverged from the plan" below.
Treat `README.md`/`plan.md` as historical context, not as the current design.

---

## What's done

A full pipeline exists at `clo_avatar_generation/face/` and is wired into the
avatar runtime as an optional step:

```
photos (1–3) + body-morphed .avt
    → detect        MediaPipe FaceLandmarker, 478 landmarks per photo
    → project        homography-warp real photo pixels directly into the
                      CLO UV face atlas (front photo required; left/right
                      optional, used to fill in cheek regions the front
                      photo can't see)
    → beard          jaw-region beard sprite composited from landmarks
    → grade          color grade pass (saturation/hue/brightness + seam blur)
    → hair           recolor avatar's hair texture to match photo hair color
    → morph          displace face-region OBJ vertices (jaw/cheek/nose width
                      and depth) using landmark-derived measurements
    → patch          swap face texture + hair texture inside the .avt zip,
                      write personalized .avt
```

This is invoked from `avatar_runtime/step_12_apply_face.py`, which is called
by `pipeline.py` as an optional step after the body pipeline (step 11). It's
a no-op (returns success, adds a warning) if no face photo was provided or
if there's no avatar to patch yet — the body-only pipeline still works
without this step.

Entry points:
- `face/run_face.py` — the pipeline itself (`run()`), called by step 12.
- `face/run_face_diag.py` and `face/diagnose.py` — standalone diagnostic
  scripts that run the pipeline against a fixed test subject (`u_001`) and
  produce visual debug output (landmark overlays, warp heatmaps, side-by-side
  comparisons) in `output/face_diag/`. Useful for judging accuracy without
  opening CLO3D.
- `face/grade.py` — quick numeric accuracy scoring.

Supporting understanding already banked (don't redo this investigation):
- The `.avt` format is a zip archive; the face color texture, normal map, and
  roughness map are separate JPGs inside it, plus a `.dan` binary holding
  body geometry.
- The `.dan` body "feature values" are confirmed body-measurement-only —
  face shape is not controlled through that channel.
- A UV template (`templates/base-1-face-uv.json`) mapping all 478 MediaPipe
  landmark indices to pixel coordinates on the avatar's own face texture has
  been generated. This is what lets `project.py` warp a real photo directly
  onto the avatar's UV layout without any 3D reconstruction model.
- A base head OBJ (`clo_avatar_generation/input/base_head.obj`) exists and is
  used for the geometry morph pass.

---

## How the approach diverged from the plan

The original plan (see `plan.md`) was: reconstruct a 3D face mesh from 3
photos with a model (DECA+FLAME, or 3DDFA_V2 as the commercially-safe
fallback), bake that into a UV texture, and separately figure out how to
morph CLO's face geometry.

What actually got built instead, and why:

1. **No 3D reconstruction model was used at all.** `project.py` explicitly
   replaces the planned `reconstruct.py` + `bake.py`. Instead of fitting a 3D
   face model and baking a texture from it, it fits a single 2D homography
   from MediaPipe landmarks (photo space → avatar UV space) and warps the
   real photo pixels straight in. Rationale documented in `project.py`: the
   real photo pixels are a better texture than anything a reconstruction
   model would synthesize, and this sidesteps the DECA/FLAME licensing
   problem entirely (MediaPipe is Apache 2.0).
2. **Geometry morphing was solved differently than planned.** The plan's
   "Option B" was blocked on an unknown (whether CLO's face sliders map to
   `SetAvatarProperties` REST keys, or require binary-offset patching like
   body measurements). That question was never resolved through the REST/DAN
   route. Instead, `morph.py` displaces vertices directly on the OBJ mesh
   (`input/base_head.obj`), using ratios derived from MediaPipe landmark
   distances (jaw width, cheek width, nose length/depth) against baseline
   ratios for the stock avatar. This bypasses the `.avt`/`.dan` question
   raised in the plan — worth knowing so nobody re-investigates it.
3. **Texture and geometry are both driven by MediaPipe only.** 3DDFA_V2 was
   never integrated (there's an empty top-level `3DDFA_V2/` directory in the
   repo — that's a leftover from the abandoned path, not live code).

---

## What's not done / open work

- **Only one test subject.** Everything has been run and visually checked
  against `u_001` only. No validation across different face shapes, skin
  tones, ages, facial hair, or glasses.
- **Geometry morph is unvalidated in CLO.** `morph.py` produces a modified
  OBJ (`morphed_head.obj`), but there's no confirmed step that gets this
  geometry back into the `.avt`/CLO pipeline the way the texture patch does
  — check `run_face.py`'s handling of `morph_result` / `morphed_obj` before
  assuming geometry changes actually reach the final avatar CLO renders.
- **No automated pass/fail test.** The diagnostic scripts produce visual
  output and numeric error stats for a human to eyeball; there's no
  assertion-based test that fails CI or blocks a bad pipeline run.
- **Side-photo depth estimation is acknowledged-but-unsolved.** The beard
  module's own comment states MediaPipe z-depth from a single 45° photo is
  only a rough (2.5D) estimate, not a true measurement, and suggests a second
  camera angle would be needed for a kiosk-quality build.
- **Multi-photo blending (left/right) is a fixed-weight blend**, not
  confidence- or quality-driven — worth revisiting once there's more than
  one test subject to tune against.

---

## Known issues (for whoever inherits this)

1. **Skin tone / color grade is not adaptive — it's a fixed correction
   tuned to one subject.** The final color-grade pass
   (`grade.py::apply_color_grade`) hardcodes a fixed saturation boost, hue
   shift, and an **8% brightness reduction described in the code as tuned
   "to match medium-dark complexion."** This runs unconditionally on every
   user's face region. For anyone lighter or darker than that reference
   subject, this will visibly shift their skin tone away from their actual
   photo. This directly contradicts the design intent stated elsewhere in
   the same module (`project.py`'s skin-tone extraction is explicitly
   "no hardcoded skin-tone values, works for any skin tone") — the two
   passes disagree with each other. **This is the highest-priority
   correctness bug to fix before showing this to real users of varied skin
   tones**: either make the grade adaptive (e.g., derive the correction from
   the user's own extracted skin tone rather than a fixed constant) or drop
   the hardcoded shift.
2. **Geometry deformation is clamped defensively, which caps how different
   from the stock face a user can look.** `morph.py` enforces a ratio clamp
   and a max-per-vertex displacement to avoid mesh blow-ups. That's a
   reasonable safety net for a first pass, but it means users with face
   proportions far from the base avatar will be pulled back toward the
   generic shape rather than matched — an accuracy ceiling, not a bug, but
   one that should be called out rather than discovered later.
3. **The plan/README docs in this same folder are stale** relative to the
   actual implementation (see divergence section above). Anyone reading
   `README.md` or `plan.md` first will build a wrong mental model of what's
   implemented (they describe DECA/FLAME or 3DDFA_V2 reconstruction; neither
   is used). Recommend folding the accurate parts of those docs into this
   one and marking the originals historical, or deleting them, once this
   handoff is reviewed.
4. **Model/template coupling to `base-1`.** The UV template
   (`base-1-face-uv.json`) and baseline ratios in `morph.py` were derived
   from one specific avatar base mesh. Nothing in the pipeline detects or
   fails loudly if it's run against a different base avatar — it will
   silently produce a wrong warp rather than erroring.
5. **`3DDFA_V2/` in the repo root is dead weight** from the abandoned
   reconstruction path (see divergence section) — flag for removal, it may
   confuse the next person into thinking it's a live dependency.

---

## How to pick this up

1. Run `python clo_avatar_generation/face/run_face_diag.py` from repo root —
   exercises the full pipeline against the existing `u_001` test photos and
   drops visual diagnostics in `output/face_diag/`. Start here to see
   current output quality before changing anything.
2. Read `run_face.py` top-to-bottom — it's the actual pipeline, in order,
   with each stage's purpose documented in its own module docstring
   (`detect.py`, `project.py`, `beard.py`, `grade.py`, `hair.py`, `morph.py`,
   `avt_face.py`).
3. Fix the color-grade skin-tone issue (#1 above) first — it's the one most
   likely to be visibly wrong to any new test subject.
4. Get a second and third test subject's photos in before trusting any
   accuracy numbers from `diagnose.py` — right now every threshold and
   baseline in the code was tuned against a single face.
