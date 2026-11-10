# Avatar Personalization — Where We Are and Which Way to Go

**Date:** 2026-11-10 · **Branch:** `facetime` · **Supersedes the status boards in**
`face-pipeline-architecture-26_10_28.md` and `avatar-personalization-split-decision-26_10_28.md`
(those two remain the reference for *why* each decision was taken; this is the current state and the route).

Everything below was measured on this machine against `clo_avatar_generation/input/base-1.avt`,
CLO 2026.1.336, plugin 1.3.2. Where something is an inference rather than a measurement it
says so.

---

## Part 0 — The one-paragraph version

Photo → faced `.avt` works, and CLO demonstrably loads every texture we patch. Face, hair
colour, hair density and eye colour are all done and verified. We now have a number for how
much this buys: **a stock avatar scores 51% familiarity against the source photo, ours scores
59%** — and the gain is almost entirely colour (+38 points), because the avatar is still
wearing the template's skull. **That is the whole story of what is left.** Colour is nearly
finished; proportions have not moved and cannot move until we deform geometry. The next big
unlock is head morph, not more texture work.

---

## Part 1 — Status board

| Item | State |
|---|---|
| `.avt` container read/write, byte-faithful | **Done, test-covered** — `face_fitting/io/avt_container.py` |
| Photo → faced `.avt` (face albedo) | **Done** — `face_fitting/run_face_fitting.py` |
| Skin-tone reconciliation toward the user | **Done** — default `--skin-match body` |
| Hair colour (Tier A) | **Done, verified in CLO and in the GLB** |
| Hair density / alpha (Tier A) | **Done, verified in CLO**; needed a GLB fix of our own (Part 3) |
| Eye colour | **Done, verified in CLO** — `face_runtime/eye_fit.py` |
| GLB export with working hair opacity | **Done** — `face_fitting/export_glb.py` |
| Per-user avatar resolution (Phase 0) | **Done** — `clo_vto/native_vto/avatar_resolution.py` |
| Familiarity measurement | **Done** — `face_fitting/compare_to_photo.py` |
| Automated CLO texture verification | **Done** — `face_fitting/verify_in_clo.py` |
| Test suite | **216 tests**, `pytest.ini` |
| Face job as its own worker task (Phase 2) | **Done** — `worker.tasks.run_face_job`, `face_fitting/face_job.py` |
| VTO resolves the user's faced avatar | **Done** — try-on worker resolves through the ladder |
| Hair opacity on the VTO export | **Done** — `step_13_hair_opacity.py` |
| GLB delivery budget (Phase 4) | **Done** — `step_14_glb_budget.py`; 36.7 MB → 16.2 MB |
| Capture-quality gate | **Done** — `face_runtime/capture_quality.py`, `--min-capture-grade` |
| VTO drape → faced avatar, live end to end | **RUN AND PASSING** — 210.9 s, garment draped on the faced avatar, 16.4 MB shipped |
| Hair *style* (Tier B library) | **Not started** — Part 5, Path C |
| Head geometry morph (Phase 7) | **Not started** — Part 5, Path B. **Highest value** |

---

## Part 2 — What is settled, with the evidence

These are closed. Re-deriving them is wasted time.

### 2.1 CLO reads the textures we patch into the `.avt`

`verify_in_clo.py` imports a patched avatar, exports a GLB, and scores each returned texture
against both the stock and the patched version of itself. Distances are RMS Lab over a 32×32
thumbnail; 0.00 is an exact match.

| Entry | vs ours | vs stock | Verdict |
|---|---|---|---|
| `MV2_Jinho_01_face.jpg` | **0.00** | 18.22 | CLO loaded ours |
| `hair_main.jpg` | **0.00** | 17.54 | CLO loaded ours |
| `hair_cap.jpg` | **0.00** | 21.47 | CLO loaded ours |
| `MV2_Jinho_01_eye.jpg` | **0.00** | 6.32 | CLO loaded ours |

This generalises the older "CLO reads the embedded entry" finding, which had only ever been
proven for the face albedo.

### 2.2 CLO honours patched hair alpha on import — but never exports it

Two avatars were rendered in the CLO GUI, one thinned to 0.50. Aligning the screenshots on
their eye/mouth anchors and counting hair pixels: **24,349 vs 27,257 — 10.7% less hair**, lost
almost entirely at the temples, which is where eroding a strand-card alpha thins first.

But the alpha maps appear **nowhere in CLO's GLB export** (nearest candidate 62 and 73 away
from both references). Cause: CLO's hair materials are `alphaMode = BLEND`, which is correct,
but their `baseColorTexture` images are **three-channel JPEGs**, and glTF reads opacity from
the base colour's fourth channel. BLEND over a texture with no alpha channel is opaque hair.

This corrected a wrong claim in the earlier doc ("alpha is respected end to end"). It is not.

### 2.3 CLO renders hair at 0.528× its albedo lightness

We wrote an albedo at L\* 35.2; the CLO render measures 18.6. The strand cards are
semi-transparent, so every pixel is a stack of partly-lit strands over the cap beneath.
Consequence: aiming the albedo straight at the colour sampled from the photo **systematically
undershoots** — the user sees hair about half as light as their own.

`--hair-render-compensation` exists for this and is **off by default**: one subject, one
lighting rig, one camera is not enough to change a default on.

### 2.4 Familiarity, with controls

`compare_to_photo.py` scores a render against the source photo. Shape is Procrustes-aligned
(translation, rotation and scale removed) so it measures shape, not framing. Colour is scored
only on relationships that survive a lighting change — hue and hair-to-skin contrast —
because a CLO render and a room photo are lit differently and absolute L\* would mostly
measure the lamps.

**Controls first**, because a metric nobody has sanity-checked is worse than no metric:

| Control | Score | Means |
|---|---|---|
| photo vs itself | 100% | the metric is self-consistent |
| photo downscaled to render size | 97% | **resolution costs only 3%** |
| two screenshots of the same avatar | 94% | **noise floor ≈ 6%** — ignore smaller differences |

**Results** (subject: `test2.png`):

| Render | Overall | Shape | Proportions | Colour |
|---|---|---|---|---|
| Stock avatar, no face job | 51% | 33% | 58% | 42% |
| Phase 1 faced avatar | **59%** | 43% | **56%** | **80%** |
| Phase 1 + hair thinned 0.50 | 60% | 43% | 57% | 81% |

**The face job buys +38 points of colour, +10 of shape, and nothing at all on proportions
(−2, inside the noise floor).** That is exactly what a texture pass should do, and it is the
single most useful number in this document.

### 2.5 The proportion failures are the skull, not our warp

The suspicion was that our three-anchor warp stretches the photo to fit the template's
eye-to-mouth spacing, making the nose too long. The stock avatar settles it:

| Attribute | Photo | Stock render | Faced render |
|---|---|---|---|
| nose length | 0.381 | 0.536 (**0%**) | 0.547 (**0%**) |
| face width | 1.369 | 1.693 (5%) | 1.644 (20%) |
| face height | 1.672 | 2.061 (7%) | 2.027 (15%) |
| left eye width | 0.304 | 0.304 (100%) | 0.306 (97%) |
| skin hue | 50.5 | 45.9 (92%) | 50.5 (100%) |

Stock scores 0% on nose length too. **The warp is not making it worse; the template skull is
simply a different shape from the subject.** Everything that depends only on texture scores
85–100%; everything that depends on skull shape scores 0–41%.

### 2.6 Input resolution dominates subject difficulty

The working assumption was that `test1.png` (stock photo, clean lighting) is the easy case and
`test2.png` (real photo) the hard one. Measured, it is the other way round:

| | test1.png | test2.png |
|---|---|---|
| Resolution | 622×350 | 1200×1600 |
| Interocular | 77.7 px | 340.2 px |
| UV upscale | **4.31×** | 1.18× |
| Iris diameter | 5.3 px | 21.5 px |
| Eye colour | **declines** (needs 240 px, got 45) | works (762 px) |
| Hair sample | 1,915 px | 28,768 px |

`test1` is not an easier subject, it is a **resolution-starved input**. Its hair and eye
results are the pipeline correctly refusing to guess. A capture UX that enforces roughly
170 px interocular — about a 600 px-wide face crop — would raise output quality more cheaply
than any algorithm change on this list.

---

## Part 3 — The GLB export, and why no Blender is needed

**You do not need Blender.** The question was whether hair had to be rebuilt in a DCC tool.
It does not: the data was already in the container, only the channel layout was wrong.

`face_fitting/export_glb.py` does the whole thing in Python:

1. CLO: new project → import the faced `.avt` → export GLB.
2. Find each **hair material's** base colour image in that export. Going through the materials,
   not the images, is what makes this safe — a hair normal map of the same size can never be
   mistaken for an albedo.
3. Identify which albedo is which by content fingerprint, because CLO exports every image
   unnamed.
4. Compose the matching alpha map in as a fourth channel, re-encode as PNG.
5. Repack and save a self-contained binary GLB, then reload it and confirm the hair images
   really came back as RGBA.

Verified by loading the result in `trimesh`, an unrelated glTF consumer:

```
Hair     alphaMode=BLEND  tex=('RGBA', (1024, 1024))
Hair_1   alphaMode=BLEND  tex=('RGBA', (1024, 1024))
```

**Size.** PNG is the only alpha-capable format every glTF viewer reads, so the file grows.
Measured, on the same avatar:

| Variant | Size |
|---|---|
| CLO raw export (hair opaque — unusable) | 36.4 MB |
| + alpha, hair at 2048², PNG level 9 | 41.2 MB |
| **+ alpha, hair at 1024²** | **37.9 MB** |

**1024² hair costs 1.5 MB over the broken export and is the recommended default.** Two caveats
recorded honestly: `pygltflib` 1.16.5 cannot pack image data into a buffer, so the patched
images stay as base64 data URIs — valid, just larger than necessary; and 38 MB still needs
Draco/meshopt before it reaches a phone, which is Phase 4 and unchanged by any of this.

**Output to look at now:**

```
face_fitting\output\u_phase1_test2-face-001\u_phase1_test2.glb        (38.0 MB)
```

Drag it onto <https://gltf-viewer.donmccurdy.com/>, or open it with the VS Code 3D preview.
Check the hair at the temples and hairline — it should be strands, not a helmet.

---

## Part 4 — Where it merges with VTO

This is the part that turns a demo into the product. The pieces exist; they are not yet
wired in this order.

```
Step 1 (measurements)  →  avatar.avt
                              │
         face job  ───────────┤   photo → faced.avt      ~2.3 s, no CLO
         (own worker job)     │
                              ▼
                     avatar_resolution.resolve_avatar(user_id)
                     faced.glb → faced.avt → avatar.avt → base template
                              │
                              ▼
                     clo_vto  →  import avatar → drape → simulate → export GLB
                              │
                              ▼
                     hair-opacity pass  (Part 3, as a VTO step)
                              │
                              ▼
                     simulation_textured.glb  →  shopper
```

**All three tasks are now implemented** (2026-11-10):

1. **`worker.tasks.run_face_job(avatar_profile_id, photo_path)`** — its own job, deliberately
   not a 12th step of Step 1: a re-shot photo must not trigger a full avatar rebuild, and it
   never touches CLO so it cannot contend for the single-threaded plugin. The work itself moved
   into `face_fitting/face_job.py` so the CLI and the worker drive one implementation. It writes
   `faced.avt` + `face_manifest.json` into the **same version folder** as the avatar it
   personalised, so a user's body and their face are one artifact and roll back together, and
   records `face_status`, `face_quality_score` and `face_capture_grade` on the profile.
2. **The try-on worker resolves through the ladder.** It passes the profile's `faced_avatar_path`
   and `clo_avatar_avt_path` in as the `faced_avt` and `avatar_avt` rungs — not as `explicit`,
   which would skip the faced rungs and keep handing shoppers the stock head.
3. **`step_13_hair_opacity.py`** composes the hair alpha into the simulation GLB, and
   **`step_14_glb_budget.py`** then applies the texture budget. Both follow step_12's rule that
   every failure path returns True, and both leave `final_glb_path` unset when they give up, so
   the worker's `final → textured → raw` fallback *is* the degradation ladder.

Measured on the real export, the whole post-simulation chain:

| Stage | Size |
|---|---|
| CLO raw export (hair opaque, 23.3 MB of textures) | 36.4 MB |
| + hair opacity composed in | 36.7 MB |
| + texture budget (face kept at 2048) | **16.2 MB** |

**56% smaller, with the face albedo untouched.** Most of it came from one finding: pygltflib
1.16.5 cannot write image data into a buffer, so replacing a texture left the file carrying both
the new image base64 in the JSON chunk *and* the old one behind an orphaned buffer view. The
first attempt at the budget shrank 23.3 MB of textures to 2.7 MB and made the file 1.3 MB
*larger*. `io/glb_textures.repack_buffer()` rebuilds the buffer from what actually references it.

### Live end-to-end, run 2026-11-10

Run against the default panels with CLO attached, `user_id=u_phase1_test2`:

```
Avatar for u_phase1_test2: the user's faced avatar (texture)   <- resolver picked the faced rung
[STEP 13] GLB Texture Inject   simulation_textured.glb  34.9 MB
[STEP 14] Hair Opacity         simulation_hair.glb      35.3 MB
[STEP 15] GLB Texture Budget   37.0 MB -> 16.4 MB (56% smaller)
Pipeline complete (210.9s)
```

The shipped `simulation_web.glb` holds the four draped garment panels (1626 / 1717 / 401 / 406
verts) **and** the faced avatar: hair at `alphaMode = BLEND` with an RGBA 1024 texture, face
albedo still RGB 2048. Resolution tier `faced_avt`, `has_face=True`. So the whole chain -
photo → faced `.avt` → per-user resolution → drape → simulate → texture → hair opacity →
delivery budget - works unattended.

**One live bug fixed on the way.** The pipeline prints arrows and box-drawing characters, and a
Windows stdout that is piped rather than a console defaults to cp1252, which cannot encode them.
The `print` raises `UnicodeEncodeError` and the run dies before step 1. That is exactly the
condition the RQ worker runs under, where stdout is never a console, so this would have taken
down every live try-on. Fixed by `logging_setup.ensure_utf8_stdout()`, called from both entry
points, with `errors='replace'` so an unanticipated character degrades to a question mark
instead of killing a render.

The degradation ladder is non-negotiable: a face problem costs a shopper their face, never
their try-on.

---

## Part 5 — Four paths to "looks like them"

The familiarity chart says where the gap is: **colour 80%, proportions 56%, shape 43%.** Pick
paths accordingly. These are not alternatives — A is hours, B and C are the real product, D is
a hedge.

### Path A — Finish the texture pass (hours to days) — *do this first*

Everything here is cheap and already scaffolded.

| Task | Why | State |
|---|---|---|
| Capture-quality gate | 2.6: input resolution dominates everything | **Done.** `capture_quality.py` grades resolution, sharpness, head turn, tilt and exposure, predicts eye-colour viability, and gives per-failure advice. `--min-capture-grade` turns it into a hard gate |
| Calibrate `--hair-render-compensation` | hair-to-skin contrast scores 54%; cause measured in 2.3 | **Blocked on one screenshot** of `u_phase1_comp-face-001` |
| Eye colour on a high-res capture | works at 762 px, declines at 45 | Already instrumented; the gate now predicts it before the run |

The capture spec, derived rather than guessed: the stock head albedo has **400.7 px between the
eyes**. Below that the photo is being upscaled into the UV map; below **170 px** eye colour stops
being measurable at all. test1 sits at 77.7 px, which is why it grades `poor`.

**Ceiling: colour → ~95%, overall → low 60s.** It cannot touch proportions. Be honest that
this path saturates quickly.

### Path B — Head morph (Phase 7, 3–4 weeks) — *the unlock*

Drive the avatar's head geometry from the MediaPipe mesh we already compute. The chart says
proportions (56%) and shape (43%) are where all the familiarity is lost, and this is the only
path that touches them.

- **Upside:** the single largest available gain. Proportions 56% → plausibly 85%+.
- **Risk:** head geometry feeds the measurement rig and the garment bindings. Section 3.2 of
  the split-decision doc has the measured margin showing why morphing *after* simulation is
  safe; that ordering is not optional.
- **Measured by:** this chart, which is why it was built.

### Path C — Hair library (Tier B, Phase 5, 3–4 weeks) — *the product floor*

Hair *style* — length, curl, parting, volume — is geometry in `first.dan` and no texture will
ever reach it. 20–40 rigged GLB hair assets swapped at the node level and recoloured by Tier A,
with a classifier over the photo and, more importantly, a **user override**.

Required coverage is non-negotiable: straight, wavy, curly, coily; short/medium/long; and the
common Indian styles for men and women including braids, buns and a centre parting. A library
covering four Western cuts is not a library.

Honest ceiling: *"a hairstyle like yours"*, not *"your hair"* — which is what Ready Player Me,
Meta avatars and Bitmoji all ship. Side benefit: `Hair` is 141,426 vertices against the body's
37,301, so low-poly library hair is also the biggest single lever on file size.

### Path D — Vendor photo→head+hair (Tier C) — *parallel, procurement-shaped*

Run as a bake-off against Path B rather than instead of it. Buys time-to-quality, costs
control, per-user price and a privacy surface over biometric data.

### Recommended route

**A now** (hours, saturates fast) → **B and C in parallel** (B for the face, C for the hair;
they do not overlap) → **D as a hedge, evaluated against B**. Phase 2 wiring (Part 4) runs
alongside all of it, because without it none of this reaches a shopper.

---

## Part 6 — Open questions

| # | Question | How it closes | Cost |
|---|---|---|---|
| 1 | Does render compensation actually help, and at what value? | Screenshot `u_phase1_comp-face-001` in CLO; re-run `compare_to_photo.py` | 10 min |
| 2 | Does the hair read as strands in a glTF viewer, not a helmet? | Open the GLB from Part 3 | 5 min |
| 3 | Does CLO accept a 4096² head albedo or silently downsample? | Write one, import, export, compare — `verify_in_clo.py` already does the comparison | ~1 h |
| 4 | Does `ImportAvatarMeasurement` preserve patched textures? | Patch, resize, export, compare | ~1 h |
| 5 | ~~Is 38 MB reducible to a mobile budget?~~ | **Largely answered: 16.2 MB** via the texture budget alone (`step_14_glb_budget.py`). Mesh compression (Draco/meshopt) is still untouched and would take it further — `Hair` is 141k verts against the body's 37k | done / partly open |
| 6 | What hair does CLO's **online** Library actually offer? | A human in the CLO GUI: Library → Avatar → Male → Accessory → Hair | 15 min |

**A note on tooling:** a headless glTF renderer (`pyrender` or `moderngl`, neither currently
installed) would let the familiarity score run automatically on every change instead of
waiting for a screenshot. That is the one dependency worth adding — not Blender.

---

## Part 7 — Privacy, unchanged and still binding

Face photos are biometric data. India's DPDP Act 2023 applies directly; GDPR Art. 9 and BIPA
apply to EU and Illinois users. Treat the whole `face/` folder as biometric: explicit consent,
stated retention, deletion on request, and no third-party processing without a DPA.

Phase 0 is already part of this and is done — a shopper can no longer be handed another user's
avatar, because candidate paths are now *built* from the user id rather than discovered by
globbing a shared directory.

---

## Appendix — Running it

```bash
# photo -> faced .avt  (face + hair colour + hair density + eye colour)
python face_fitting/run_face_fitting.py --photo face_fitting/input/test2.png --user-id u_demo

# faced .avt -> GLB with working hair opacity   (needs CLO running)
python face_fitting/export_glb.py --avatar face_fitting/output/u_demo-face-001/u_demo.avt --hair-texture-size 1024

# did CLO actually load our textures?           (needs CLO running)
python face_fitting/verify_in_clo.py --avatar face_fitting/output/u_demo-face-001/u_demo.avt

# how much does it look like them?              (render = a CLO screenshot)
python face_fitting/compare_to_photo.py --photo face_fitting/input/test2.png \
    --render path/to/screenshot.png --label "demo"

# shrink a GLB for delivery (no CLO needed)
python face_fitting/optimize_glb.py --glb face_fitting/output/u_demo-face-001/u_demo.glb

python -m pytest -q      # 216 tests
```

Useful flags: `--hair-render-compensation 1.0` (Path A, question 1), `--hair-density 0.5`
(force thinning), `--hair none` / `--eyes none` (isolate a stage), `--skin-match face`
(bleach the face to the template instead of moving the body to the user — almost never what
you want, and the reason the default is `body`).
