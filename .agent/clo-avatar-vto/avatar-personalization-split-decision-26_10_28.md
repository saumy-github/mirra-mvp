# Where Does Personalization Happen? — `.avt` vs GLB, and Why the Answer Is Both

Written 2026-10-28. Audience: Mirra engineering (whoever picks up avatar/VTO work)
plus whoever signs off on vendor spend.

**Question this answers:** we want a one-to-one replica of the user — body shape from
measurements, plus a recognizable face, hair, skin tone and eyes. Body shape is handled.
Face texture is handled. Hair is where we got stuck. So which of these three do we build?

1. Modify skin/face/eyes in the `.avt`, then do hair in the exported GLB.
2. Use stock `.avt` avatars and do *everything* in the GLB.
3. Take a base `.avt`, modify it as a GLB, convert back to `.avt`, *then* drape clothes.

**Short answer up front:**

- **Option 3 is not viable, and this is now settled rather than suspected.** The SDK's
  `ImportAvatar()` accepts an `.avt` path and nothing else. A GLB/OBJ/FBX comes back in
  as an *object avatar*, not a CLO parametric avatar. More decisively,
  `ImportAvatarMeasurement(csvPath, avtPath, opt)` — the call Step 1 is built on —
  requires an `.avt` template. Round-tripping through GLB destroys the measurement rig,
  which is the one thing that makes our fit claim true. See 2.3.
- **Option 2 is wrong for the body and right for the hair.** Body geometry must be final
  before simulation or the garment was draped on the wrong body. That is not a cosmetic
  defect, it is a false fit claim. See 2.2.
- **Option 1 is correct, but the way it is framed is the problem.** The split should not
  be "textures in `.avt`, geometry in GLB". It should be **by physics**: does this change
  how cloth drapes? If yes, it happens before CLO. If no, it happens after. That rule
  puts hair *and* head shape after CLO, and it is the whole architecture. See Part 3.
- **Hair is not actually stuck.** The `.avt` carries seven hair textures, including
  `hair_main_alpha.jpg` (2048², L\*=29.9) which controls *which parts of each hair card
  are visible*. Hair **colour** and rough **density/hairline** are the same one-line
  texture swap we already do for the face. Only hair **style** is locked in the binary.
  We concluded "hair is geometry, not texture" on 10-27; that was half wrong. See 1.4.
- **Head geometry can be morphed after simulation, with a measured safety margin.**
  Head/jaw-dominated vertices start at **y = 1.645 m** on a 1.89 m avatar. A crew-neck tee
  sits around y = 1.55–1.60. That is a ~4–5 cm clearance, so facial geometry is physically
  disjoint from normal garments. Hoods, turtlenecks, scarves and high collars are the
  named exception set. See 3.2.
- **Face geometry does not need a vendor and does not need FLAME.** MediaPipe's
  FaceLandmarker already gives 478 *3D* landmarks under Apache-2.0. That is a
  licence-clean driver for deforming the 7,740 head vertices directly in the GLB,
  and it sidesteps the Max Planck non-commercial problem flagged in
  `face-personalization-deep-dive-26_10_3.md` §4.5. See Part 6.

---

## Part 1 — What is actually inside the two formats

Everything in this part was measured on `clo_avatar_generation/input/base-1.avt` and on
`faced_avatar.glb` (the real avatar-only export produced through our plugin on 10-27).
Numbers are reproducible, not recalled.

### 1.1 The `.avt` is 29 loose textures and one opaque brain

Thirty ZIP entries. Twenty-nine are plain JPEG/PNG images we can read and rewrite.
One is `first.dan` at **33,066,665 bytes** — 97% of the file — and it holds *everything*
structural.

| Entry class | Count | Editable by us? |
|---|---|---|
| Head textures (`MV2_Jinho_01_face*`, `_eye*`, `_eyelash`, `_tooth*`) | 9 | Yes |
| Body textures (`_arm*`, `_leg*`, `_Body_*`, `_body_Covered_*`) | 8 | Yes |
| Hair textures (`hair_main*`, `hair_cap*`) | 7 | Yes |
| Shoe texture | 1 | Yes |
| Misc (`transparency_*`) | 1 | Yes |
| `clofiles.json` | 1 | Yes |
| **`first.dan`** | 1 | **No — see 1.2** |

### 1.2 `first.dan` is not encrypted, and that is a trap

It is a self-describing tagged binary tree in a Qt-flavoured serialization — field names
sit in plaintext next to their values, with Hungarian type prefixes (`qs` QString,
`b` bool, `i` int, `m4` 4×4 matrix, `v2`/`v3` vectors, `arr`/`list`/`map` containers).
Byte entropy is 7.08 bits/byte and it recompresses to 0.55 of its size, so it is bulk
float arrays, not a cipher. 7,258 readable ASCII runs in the first 5 MB alone.

It is tempting to conclude this is reverse-engineerable. What it contains says otherwise:

| Field | Occurrences | What it is |
|---|---|---|
| `arrJointIndex`, `arrWeight` | 144,908 each | Per-vertex skinning weights |
| `listMeasure`, `listMeasureDiffValuesC`, `listMeasureModeC`, `bUnifiedMeasure`, `listCupSizeValueList` | 1 each | **The parametric measurement rig** |
| `avatarVertexIdxList`, `avatarToPatternVectorList` | 8–9 | **Garment↔avatar binding, by vertex index** |
| `iGluedPatternTriangleIndex`, `v3GluedPatternTriangleABC`, `m4LocalMatrixOnGluedPatternTriangle` | 300 each | **Garment attachment, by avatar triangle index** |
| `qsAvatarID`, `qsOriginAvatarSrcFilePath`, `1_MaleTemplate_07` | 1 each | Template identity |
| `qsProductVersionUTF8` → `2.5.9999.99999` | 1 | Version stamp on the format |

Reading this is plausible. *Writing* it means authoring 144,908 consistent skin-weight
records plus a measurement rig plus index-based garment bindings, into a
version-stamped private format, with no spec and no validator. That is a multi-month
reverse-engineering project that breaks on every CLO update, undertaken to gain
something Option 1 already gives for free. See 2.3.

### 1.3 The SDK confirms the boundary from the other side

From `CLOAPIInterface/include/` in CLO SDK v2026.1.336:

| Capability | API | Verdict |
|---|---|---|
| Load a real parametric avatar | `ImportAvatar(std::string _avtPath, opt)` | **`.avt` only** |
| Apply measurements | `ImportAvatarMeasurement(csvPath, _avtPath, opt)` | **requires an `.avt`** |
| Read measurements | `GetAvatarMeasurements()` | available |
| Load a mesh as an avatar | `ImportOBJ/ImportFBX/ImportGLTF(..., opt)` with `ImportObjectType = 0` | object avatar, not parametric |
| Set an avatar texture at runtime | `SetAvatarTexureMap()` *(SDK's own typo)* | available, not wired |
| Set an avatar opacity map | `SetAvatarOpacityMap()`, `...ByIndex()` | available, not wired — **relevant to hair, see 5.1** |
| Avatar properties | `GetAvatarProperties` / `SetAvatarProperties` | available, wired |
| Re-drape after a change | `ReDrape3DArrangement()` | available |
| **Read or write avatar vertices** | — | **does not exist** |
| **Create or drive morph targets** | — | **does not exist** |

The last two rows are the crux. There is no legitimate API path to avatar geometry at
all. So "modify avatar geometry in CLO" is not a thing we can do by any route —
sanctioned or otherwise.

Note also that `ImportGLTF` exists and `ImportObjectType = 0 : Avatar` exists, which is
exactly why Option 3 *looks* available. It is available; it just silently demotes the
avatar. That is the dangerous kind of working.

### 1.4 Hair colour and density are textures — we were wrong about this

On 10-27 we concluded hair was pure geometry and therefore out of reach. The container
says otherwise:

| Entry | Size | Mean L\* | What it controls |
|---|---|---|---|
| `hair_main.jpg` | 2048² | 2.6 | Strand colour (near-black) |
| `hair_cap.jpg` | 2048² | 3.9 | Scalp/cap colour |
| **`hair_main_alpha.jpg`** | 2048² | 29.9 | **Which parts of each strand card are visible** |
| **`hair_cap_alpha.jpg`** | 2048² | 25.5 | **Which parts of the cap are visible** |
| `hair_main_Normal`, `hair_main_Roughness`, `hair_cap_Normal` | 2048² | — | Shading |

And the exported GLB keeps all three hair materials at `alphaMode = BLEND`, so alpha is
respected end to end. Consequence: **hair colour, perceived density, hairline position
and a receding/faded look are all reachable today** by the same mechanism as the face —
no geometry, no vendor, no CLO change. What is *not* reachable this way is length, curl,
parting direction and volume. Those are genuinely `first.dan`.

For reference, eye colour is `MV2_Jinho_01_eye.jpg` at **256²** — a trivially cheap win
we have not taken.

### 1.5 The exported GLB is fully rigged and cleanly separated

`faced_avatar.glb`, measured:

- 9 meshes, 113 nodes, **9 skins**, 16 materials, 26 images, **0 morph targets**, 0 animations
- Every primitive carries `POSITION`, `NORMAL`, `TEXCOORD_0`, `JOINTS_0`, `WEIGHTS_0`
- A 92-joint hierarchy (`Pelvis` → `Spine`/`Spine1`/`Spine3` → `Neck` → `Head`, limbs, `jaw`)

The two facts that decide the architecture:

**`Hair` is its own mesh, its own node, and its own skin.** 141,426 vertices, 3 primitives,
`alphaMode=BLEND`, and it is weighted to only **five joints** — `Spine3`, `Neck`, `Neck1`,
`Head`, `jaw` — with a bbox of y 1.687–1.908. A replacement hair asset rigged to those
same five joints is a node splice. Nothing about the body is touched.

**`body` is a single mesh of 37,301 shared vertices split across 4 material primitives:**

| Primitive | Verts | y range |
|---|---|---|
| `face` | 7,960 | 1.630 – 1.890 |
| `body2` | 8,889 | 0.761 – 1.697 |
| `arm` | 9,054 | 0.779 – 1.517 |
| `leg` | 11,398 | 0.000 – 0.820 |

Total avatar height 1.890 m. Vertices dominated (>0.5 weight) by `Head`/`jaw`:
**7,740, spanning y 1.645 – 1.890**. Including `Neck`/`Neck1`: 8,378 from y 1.589.

Zero morph targets means CLO exports no blendshapes, so any shape personalization in the
GLB is ours to author — but it also means nothing of CLO's is there to conflict with.

### 1.6 The avatar already survives post-simulation export

This was listed as an open question yesterday and as a gate on the whole geometry phase.
It is already answered inside our own repo. `clo_vto/native_vto/step_12_texture_glb.py:74`
carries a list of avatar material prefixes that the comment states were *"confirmed
avatar-body material names"* against real exports:

```
material_rightshoe, material_leftshoe, material_hair,
face, body2, arm, leg, eye, eyelash, toothsg1
```

So a post-simulation GLB contains the complete avatar — `face`, `material_hair` and all —
alongside the garment. The garment arrives as **one merged material** (`fabric 1`, per the
same file's comment, "confirmed against two independent real exports"), which means
garment and avatar are trivially separable by material name in the post-sim GLB.

One thing to not worry about: `_MAX_TEX_DIM = 1024` in that file applies only to garment
panel textures loaded from disk via `_png_to_bytes`. Avatar materials are skipped
entirely, so our 2048² fitted face texture is not downscaled by step 12.

---

## Part 2 — Scoring the three options

### 2.1 Option 1 — textures in `.avt`, hair in GLB

Works. It is also what we have already half-built. Its only flaw is that the split is
drawn along the wrong line (file format instead of physics), which leaves head *shape*
unassigned and makes hair look like a special case rather than an instance of a rule.
Fixed in Part 3.

### 2.2 Option 2 — stock `.avt`, everything in GLB

**Reject for body. Adopt for hair and head shape.**

The body half fails on the product thesis, not on engineering. If the avatar CLO
simulates on is a stock body, then the drape, the tension map, the stretch and the
"does this fit" answer all describe a stranger. You would then reshape the body
afterwards and the garment — baked at its simulated position — would poke through,
float, and cling to contours that no longer exist. We would be shipping a fit claim we
know to be false, which is worse than shipping no fit claim.

It also throws away `GetAvatarMeasurements`, which is the defensible part of Mirra.

The hair half, by contrast, is simply correct, for the reason in 1.5: hair is already a
separate mesh with a separate skin and a 5-joint binding.

### 2.3 Option 3 — base `.avt` → GLB → back to `.avt` → then clothe

**Reject.** Four independent blockers, in descending order of how fatal they are:

1. **The measurement rig does not survive.** `ImportAvatarMeasurement` takes an `.avt`
   path. Our Step 1 calls it through `/import-avatar-measurements` with a
   `template_path`. A re-imported GLB is an object avatar and has no measurement rig,
   so Step 1 stops working. We would be trading the thing that works for the thing that
   doesn't.
2. **Garment bindings are stored by index.** `avatarVertexIdxList` and
   `iGluedPatternTriangleIndex` reference avatar vertices and triangles by number. Any
   topology change silently invalidates them.
3. **We cannot write `first.dan`.** See 1.2. CLO's own importer could write it for us,
   but only by taking path (1) and demoting the avatar.
4. **It buys nothing.** The entire motivation is to get hair and face shape in before
   the clothes go on. But hair and face shape *do not interact with the clothes* (3.2).
   This is a large, fragile, months-long project to solve a problem that does not exist.

Worth stating plainly because the option is seductive: it is the only one of the three
that *feels* like it produces a single clean artifact. It does. That artifact is just a
worse avatar.

---

## Part 3 — The rule: split by physics, not by file format

> **Does this change how cloth drapes?**
> **Yes → it happens before CLO, in the `.avt`. No → it happens after CLO, in the GLB.**

Everything else follows mechanically.

### 3.1 Applying the rule

| What we personalize | Changes drape? | Where | Status |
|---|---|---|---|
| Height, bust/waist/hip, limb lengths | **Yes** | `.avt` measurements, pre-CLO | Built (Step 1) |
| Face albedo (identity) | No — pixels | `.avt` texture, pre-CLO | Built (`face_fitting/`) |
| Skin tone, body + limbs | No — pixels | `.avt` texture, pre-CLO | Built |
| Eye colour | No — pixels | `.avt` texture (256²), pre-CLO | **Not done, ~1 hour** |
| Hair colour | No — pixels | `.avt` texture, pre-CLO | **Not done, ~half day** |
| Hair density / hairline | No — alpha mask | `.avt` texture, pre-CLO | **Not done, ~2 days** |
| Hair style (length, curl, volume) | No — geometry CLO ignores | **GLB, post-CLO** | Part 5 |
| Head / face shape | No — above the neckline | **GLB, post-CLO** | Part 6 |
| Eyebrows | No | **GLB, post-CLO** | Later |

Note what the rule buys us: pre-CLO texture work rides through CLO's exporter for free
and needs no new plugin endpoints, and post-CLO geometry work cannot regress fit
accuracy *by construction*, because it runs after the simulation it would otherwise
corrupt.

### 3.2 Why head shape is safe after simulation — the measured margin

Head/jaw-dominated vertices begin at **y = 1.645 m**. `body2` (torso) tops out at
**y = 1.697 m**, so the overlap zone is the ~5 cm of jaw-to-collar transition. A crew-neck
t-shirt neckline sits around **y = 1.55–1.60 m**.

So for ordinary garments there is a **4–5 cm clearance** between the highest cloth and
the lowest vertex we would move. Facial geometry and garment geometry are physically
disjoint. Morph the head after the sim and the garment cannot know.

Two hard requirements fall out of this:

- **Falloff must reach zero by y ≈ 1.65**, so the neck seam never moves and no vertex
  shared with `body2` is displaced. This is a constraint on the deformation, not a hope.
- **An exception set must be enumerated and checked:** hoods, turtlenecks, high collars,
  scarves, hats. For those, skip the head morph and log it. Do not guess.

### 3.3 Corrected pipeline order

This is the one real change to yesterday's architecture doc. The face job should run
**after** Step 1, not before it. Texture patching is topology-independent, so it works on
*any* `.avt` — including one that has already been resized. Running it last means nothing
downstream can disturb it, and we avoid having to verify that `ImportAvatarMeasurement`
preserves patched textures.

```
measurements ──► STEP 1 (CLO)          sized .avt, via existing /export-avatar-avt
                      │
photo ──────────► FACE JOB (no CLO)     patch 2048² face + skin + hair + eye textures
                      │                 → faced.avt + face_manifest.json  (~2.3 s)
                      ▼
product ────────► VTO (CLO)             drape on the correct, faced body
                      │                 → post-sim GLB (garment + full avatar)
                      ▼
                  PERSONALIZE GLB       head morph from manifest, hair swap, eyebrows
                  (no CLO)              → faced.glb        never blocks the pipeline
                      ▼
                  three.js viewer
```

Two properties worth protecting:

- **Neither personalization job touches CLO.** CLO is concurrency-1 and that is
  deliberate; the expensive, parallelizable work must stay outside it.
- **The final step degrades silently.** It inherits step 12's rule — every failure mode
  returns success, because a slightly generic head is infinitely better than a failed
  try-on. The fit answer must never depend on the cosmetics.

`/export-avatar-avt` already exists in the plugin, so this ordering needs no new
endpoints.

---

## Part 4 — What "one-to-one replica" should mean

A one-to-one replica from a phone photo is not achievable, and chasing it is how this
project would fail slowly. Define the tiers, claim the right one, and measure the right
thing.

| Tier | What the user sees | How we get there | Honest claim |
|---|---|---|---|
| T0 | Stock avatar, right body | Step 1 only | "your measurements" |
| **T1** | **Right body, own face texture, own skin, own hair colour** | **today + Part 5.1** | **"recognizably you from the front"** |
| T2 | T1 + a hairstyle close to theirs | Part 5.2 | "looks like you" |
| T3 | T2 + own head/face shape | Part 6 | "that's me" |
| T4 | Identical, from multiple views | multi-view, vendor | "a replica" |

T1 is reachable in days, and T1 already sells the product. T3 is the realistic ceiling
for a photo-based pipeline and is where we should aim. T4 needs a capture rig or a
vendor and should not gate anything.

**Measure self-recognition, not geometric error.** Vertex RMS against a ground-truth
scan is a research metric and it does not predict whether a shopper trusts the avatar.
Use two tests instead:

1. **Line-up:** show the user their avatar among five others of similar build. Can they
   pick theirs? Target >90% at T2.
2. **Willingness:** "would you be comfortable showing this to a friend?" This is the
   one that actually correlates with the avatar being used rather than dismissed.

Run both on a panel that matches the user base — which for us means a majority of Indian
users, with the skin-tone and hair-texture range that implies. A pipeline that scores
well on a Western panel and badly on ours has not been validated, it has been flattered.

---

## Part 5 — Hair, honestly

The template-swap experiment on 10-27 (Luka's hair, 202,480 verts, 3.1 cm rise versus
Jinho's 424,278 verts and 1.8 cm rise) was the right experiment and produced the right
conclusion: it is not a long-term answer. Below is the ladder, cheapest first.

### 5.1 Tier A — colour and alpha from the photo (now, no vendor, no geometry)

Per 1.4, hair colour and the alpha masks are ordinary textures in the `.avt`.

- Sample hair colour from the photo above the face oval that MediaPipe already gives us,
  then shift `hair_main.jpg` / `hair_cap.jpg` by the same Lab mean-only transfer we use
  for skin — which deliberately preserves variance, so strand detail survives.
- Erode `hair_main_alpha.jpg` where the user's hair is absent (receding hairline, fade,
  short crop) to shorten and thin the existing cards.

Cost: ~2–3 days. Gets colour correct for most users and silhouette roughly correct for
short hair. Does nothing for length or curl. This is the single best ratio of
believability to effort on the whole list, and it was sitting in the container the entire
time.

A note on `SetAvatarOpacityMap` / `SetAvatarOpacityMapByIndex` (1.3): these would let us
drive the alpha masks at runtime instead of patching the `.avt`. Not needed — patching
keeps the face job out of CLO, which is worth more than the convenience.

### 5.2 Tier B — a curated GLB hair library (the product floor)

20–40 hair assets, each rigged to the same five joints `Hair` already uses, swapped in at
the GLB node level and recoloured per Tier A. Pick the style with a classifier over the
photo (length band × texture class × parting), and let the user override — the override
matters more than the classifier, because a user who corrects their hairstyle once has
been given agency, whereas a user shown the wrong hair has been told we do not see them.

This is what Ready Player Me, Meta avatars and Bitmoji all do, and it is where we should
set the floor. Ceiling is honest: *"a hairstyle like yours"*, not *"your hair"*.

Required coverage, non-negotiable for our user base: straight, wavy, curly, coily;
short/medium/long; and the common Indian styles for both men and women, including
braids, buns and a centre parting. A library that covers four Western cuts is not a
library.

**Side benefit worth real money:** `Hair` is 141,426 vertices against the body's 37,301 —
roughly 3.8× the body, and a dominant share of the 39 MB export. Library hair authored as
low-poly cards would cut delivery size substantially. That 39 MB needs Draco or meshopt
compression plus texture downscaling before it reaches a shopper on mobile regardless;
hair is the biggest single lever.

### 5.3 Tier C — vendor photo→head+hair (the upgrade path)

Vendors that output a riggable GLB head with hair from a selfie — Avaturn, Didimo, Union
Avatars, in3D, Avatar SDK/Itseez3D, Pinscreen — all graft at exactly the GLB point Part 3
defines, so adopting one is a swap, not a re-architecture. Run them as a bake-off.

Scoring criteria, weighted in this order:

1. **Textured, curly and coily hair.** This is the criterion the 10-27 screenshots
   exposed and most systems trained on Western datasets fail it. For our user base this
   is a pass/fail gate, not a tiebreak.
2. **Deeper and darker skin tones** without washing out or going grey.
3. Licence permits commercial use, and the output mesh is ours to keep.
4. Data residency — see the DPDP notes in `face-pipeline-architecture-26_10_28.md`. A
   vendor API call with a user's face is a cross-border transfer.
5. Riggable output with usable topology, not a static scan.
6. Per-avatar cost and latency.

Do not start the bake-off until Tier A and Tier B are shipped. They are independent of
vendor choice, they make the product viable on their own, and they give the bake-off a
real baseline to beat instead of a strawman.

### 5.4 Tier D — strand-based generation

Neural Haircut, HairNet and similar produce genuinely per-user strand hair. Out of scope:
expensive to generate, expensive to render in three.js on a phone, and the licences are
largely research-only. Revisit only if Tier C bakes off badly on criterion 1.

---

## Part 6 — Face geometry without a vendor and without FLAME

The deep-dive on 10-03 (§4.5) correctly flagged that FLAME, STAR, DECA, EMOCA, MICA and
Pixel3DMM are all non-commercial. That rules out the obvious route. There is a less
obvious one that is already installed.

**MediaPipe FaceLandmarker returns 478 3D landmarks plus a facial transformation matrix,
under Apache-2.0.** We are already running it — `face_fitting/face_runtime/landmarks.py`
uses the Tasks API and we already keep `dense_landmarks.npy` for the stock head from
`calibrate_reference.py`. It is, in effect, a licence-clean morphable model we have
already paid for.

Proposed approach:

1. **Once, offline:** establish correspondence between MediaPipe's canonical face mesh and
   the 7,740 `Head`/`jaw`-dominated vertices from 1.5. Done once by hand plus ICP, checked
   in as data. This is the only genuinely fiddly part.
2. **Per user:** solve a smooth deformation field (RBF or Laplacian) from the canonical
   landmarks to the user's, and store it in `face_manifest.json`.
3. **In the GLB step:** apply the field to those vertices, with falloff forced to zero by
   y ≈ 1.65 per 3.2. Recompute normals. Leave `JOINTS_0`/`WEIGHTS_0` untouched — we move
   vertices, we do not retopologize, so the rig stays valid and the avatar stays posable.

Why this is the right first attempt: no vendor, no licence exposure, no new dependency,
reuses the landmark data we already compute, and because it only ever moves existing
vertices it cannot break the skinning. It will be less accurate than a real 3DMM fit —
MediaPipe's depth is weakest exactly where identity lives, in nose projection and chin
shape — so treat it as the T3 attempt and let Tier C vendors compete against it rather
than against nothing.

Expect it to fix the thing texture cannot: the profile silhouette. A warped texture on a
stock skull is convincing head-on and wrong the moment the avatar rotates, which for a
*movable* avatar on the website is exactly the view the shopper will reach for.

---

## Part 7 — Delivery plan

Phases 1–3 need no vendor, no budget and no research, and are worth doing whatever is
decided about geometry.

| # | Work | Depends on | Rough size |
|---|---|---|---|
| 0 | **Fix `_discover_default_native_avatar()`** — see Part 8 | — | 1–2 days |
| 1 | Eye colour + hair colour + hair alpha into the face job (5.1) | — | 3–4 days |
| 2 | Reorder to Step 1 → face job → VTO (3.3); wire `/export-avatar-avt` | 1 | 2–3 days |
| 3 | `step_13_personalize_glb.py` — hair node splice, never blocks | 2 | 3–4 days |
| 4 | GLB delivery: Draco/meshopt, texture budget, size target (5.2) | 3 | 3–4 days |
| 5 | Hair library v1, 20–40 styles + classifier + user override (5.2) | 3 | 3–4 weeks |
| 6 | Recognition panel: line-up + willingness, on a representative panel (Part 4) | 5 | 1 week, recurring |
| 7 | MediaPipe-driven head morph (Part 6) | 3 | 3–4 weeks |
| 8 | Vendor bake-off (5.3) — parallel, procurement-shaped | 6 | 2–3 weeks |

Phases 1–3 take T1 from a script to a product feature in roughly two weeks. Phase 5 is
the floor. Phase 7 is the ceiling we can reach unaided.

---

## Part 8 — One live bug this research surfaced

`clo_vto/native_vto/context.py` resolves the VTO avatar through
`_discover_default_native_avatar()`, which **globs `clo_vto/output/*.avt`** and falls back
to `base-1.avt`. It is entirely user-agnostic.

This is dev scaffolding sitting in the live path. With more than one user it can hand a
shopper someone else's avatar — and once avatars carry real faces, that stops being a
mix-up and becomes a privacy incident.

Replace it with the explicit resolution rule from
`face-pipeline-architecture-26_10_28.md`: `faced.glb → faced.avt → avatar.avt → base
template`, keyed by user and run. It is Phase 0 above because everything else in this
document makes the consequence worse.

---

## Part 9 — Where this document corrects earlier ones

Recorded so nobody re-derives the wrong thing from a stale doc.

| Earlier position | Correction | Evidence |
|---|---|---|
| "Hair is geometry; texture cannot touch it" (10-27) | Half wrong. Colour, density and hairline are textures in the `.avt`; only style is geometry | 1.4 |
| "Does the avatar survive export after a garment simulation?" — open, and gating | Already answered in-repo; post-sim GLB contains the full avatar | 1.6 |
| Face job runs before Step 1 (10-28 doc, Part 4) | Should run after. Texture patching is topology-independent, so last is safest | 3.3 |
| `first.dan` assumed opaque/encrypted | Not encrypted — plaintext-tagged. Still not writable, for different and better reasons | 1.2 |
| Option 3 assumed blocked by file format | Blocked by the *measurement rig* and index-based garment bindings. `ImportGLTF` does exist and will quietly demote the avatar | 1.3, 2.3 |

Two mistakes from 10-27 that are worth not repeating, both cases of reading a
shared buffer instead of a subset:

- The `body` mesh shares one 37,301-vertex buffer across four material primitives in a
  tiled UV atlas. Reading `geometry.vertices` directly gives u spanning 0–4 and produced
  a confidently wrong "MIRRORED" verdict. **Subset by each primitive's own triangles
  first.**
- MediaPipe indices 33/263 are *outer eye corners*; the reference anchors in the
  implementation plan are *pupil centres*. Mixing them put the mouth 87 px out.
  `calibrate_reference.py` exists specifically so anchors are derived with the same
  detector that will later consume them.

---

## Part 10 — Open questions and the tests that close them

| # | Question | Test | Cost |
|---|---|---|---|
| 1 | Does CLO accept a 4096² head albedo, or silently downsample? | Write one, import, export, compare | ~1 h |
| 2 | Does `ImportAvatarMeasurement` preserve patched textures? | Patch, resize, export, compare | ~1 h |
| 3 | Do measurement changes stretch the face texture noticeably? | Resize ±2 sizes, compare face region | ~1 h |
| 4 | What hair does CLO's **online** Library actually offer? | Needs a human in the CLO GUI: Library → Avatar → Male → Accessory → Hair. The local folder is empty | ~15 min |
| 5 | What is the real neckline y for each garment in our catalogue? | Measure from post-sim GLBs; builds the 3.2 exception set | ~half day |
| 6 | Is 39 MB reducible to a mobile-sane budget without visible loss? | Draco + meshopt + texture budget, eyeball at phone size | ~1 day |

Questions 2 and 3 only matter if we keep the 3.3 ordering, and they are cheap enough to
run before committing to it. Question 4 is the only one that needs a person rather than a
script, and it is 15 minutes.

---

## Appendix — Reproducing the measurements

```bash
# .avt container: entry list, sizes, first.dan field census
.venv/Scripts/python.exe -c "from face_fitting.io.avt_container import read_avt; ..."

# Exported GLB: meshes, skins, morph targets, per-primitive vertex counts and y ranges
.venv/Scripts/python.exe -c "from pygltflib import GLTF2; ..."
```

Artifacts these numbers came from:

- `clo_avatar_generation/input/base-1.avt` — stock Jinho avatar, 33,927,576 bytes
- `faced_avatar.glb` — avatar-only export through our plugin, 10-27
- CLO SDK v2026.1.336 headers at `C:/setup/CLO_SDK_v2026.1.336_Win/.../CLOAPIInterface/include/`
- `clo_vto/native_vto/step_12_texture_glb.py:74` — post-sim avatar material list

Timings measured 10-27, for planning: face fitting **2.33 s** end to end (landmarks 0.98,
warp+composite 1.11); CLO new project 4.14 s, `.avt` import 6.46 s, GLB export 8.81 s.
So photo → faced avatar in CLO is ~11 s, and ~21 s including the GLB export.
