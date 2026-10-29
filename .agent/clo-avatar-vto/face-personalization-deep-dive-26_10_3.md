# Face Personalization on the Mirra Avatar — Architecture Deep Dive & Build Plan

Written 2026-10-03. Audience: Mirra engineering (whoever picks up avatar/VTO work)
plus whoever signs off on vendor spend.

**Question this answers:** how do we put an accurate, high-resolution, *identical*
face — reconstructed from one photo of the user — onto the avatar we build in CLO 3D,
and what does that cost in money and time?

**Short answer up front:**

- The `.avt` avatar file is a **ZIP archive** whose head albedo is a loose
  2048x2048 JPEG called `MV2_Jinho_01_face.jpg`, laid out as a **frontal head
  unwrap**. Nothing about the avatar's face is locked inside CLO's binary format.
  This is the single most important finding in this document — it makes the cheap
  route possible, and it was verified locally, not assumed. See Part 3.
- CLO's own API DLL exports `UtilityAPIInterface::SetAvatarMeshTexture(...)` and
  `GetAvatarTexureMap(int)`. Neither is wired into our plugin yet. Wiring them is a
  ~1-day plugin change and gives us runtime face swapping. See 3.4.
- **Recommended path is two-phase.** Phase A ("recognizable face") is a pure-Python
  texture warp into that 2048-square map: ~$0/avatar, no vendor, no GPU, no CLO SDK
  change, ships in ~2-3 weeks. Phase B ("identical face") adds real head *geometry*
  by grafting a reconstructed head mesh into the exported GLB, ~5-7 further weeks.
  See Part 6.
- **Do not build Phase B on FLAME-derived research code.** FLAME 2017/2019/2020,
  STAR (already vendored in this repo), DECA, EMOCA, MICA and Pixel3DMM are all
  non-commercial licenses. We are a commercial product. See 4.5 — this includes an
  existing compliance problem in `libs/star/` that has nothing to do with faces.

---

## Part 1 — How the architecture works today

Grounding. If you already know the pipeline, skip to Part 2.

### 1.1 The three steps and where the avatar lives

```
MEASUREMENTS                      PRODUCT IMAGE
     |                                  |
  STEP 1                             STEP 2
clo_avatar_generation/          product_ingestion/
  11 steps                        5 stages
     |                                  |
  <user>.avt  <----- avatar -----> DXF panels + edge_manifest.json
     |                                  |
     +--------------+-------------------+
                    |
                 STEP 3
             clo_vto/native_vto/
               12 steps
                    |
            simulation_textured.glb
                    |
        website/frontend  (react-three-fiber)
```

Step 1 and Step 2 are independent. Step 3 needs both. The face question lives almost
entirely in Step 1's output artifact and Step 3's final export.

### 1.2 Step 1 — avatar generation (`clo_avatar_generation/avatar_runtime/`)

Eleven sequential step modules, orchestrated by `pipeline.py`, with mutable state in
`Step1Context` (`context.py`). The shape that matters here:

| Step | File | What it does |
|---|---|---|
| 1 | `step_01_health.py` | Plugin reachable? |
| 2 | `step_02_run_setup.py` | `output/<user_id>-<run>/` |
| 3 | `step_03_fetch_measurements.py` | Mongo or JSON |
| 4 | `step_04_resolve_base_avatar.py` | **Picks the base `.avt` template** |
| 5-6 | `step_05_*`, `step_06_build_payloads.py` | Normalize; build CSV/JSON/AVT payloads |
| 7 | `step_07_import_base_avatar.py` | `POST /import-avatar-avt` |
| 8 | `step_08_apply_measurements.py` | `POST /import-avatar-measurements` or `/avatar/set-properties` |
| 9-10 | `step_09_readback.py`, `step_10_compute_error.py` | Verify, score accuracy |
| 11 | `step_11_save_outputs.py` | `POST /export-avatar-avt` → `<user_id>.avt` |

The template today is `clo_avatar_generation/input/base-1.avt` (33.9 MB). Everything
personal about the avatar at this stage is *dimensional* — the morph driven by
measurements. The head is whatever the template shipped with. Right now that is a CLO
stock male avatar internally named **`MV2_Jinho_01`**, so every Mirra user currently
wears the same stranger's face.

There is also `avt_patch.py` in this package, which already does binary patching of
`.avt` payloads. That module is the natural home for the face-texture swap in 6.1 — we
would be extending an existing capability, not inventing one.

### 1.3 The plugin bridge (`clo_workspace/`)

Everything talks to CLO over a REST plugin built from `windows/RestPlugin_windows.cpp`
and `mac/RestPlugin_macOS.cpp`, contract in `plugin_contract.json` (16 read + 18 write
endpoints). Two structural facts constrain any face work:

1. **Commands are queued, not immediate.** Most writes push an `APICommand` onto
   `g_commandQueue` and return "queued. Call `/execute` to process." The queue is
   drained on CLO's main thread.
2. **Some CAPI calls cannot run from the queue drain.** There is an explicit comment at
   `RestPlugin_windows.cpp:188` that `SetFabricPBRMaterialBaseColor` and
   `SetBaseTextureMapImageGivenFilePath` crash when called from the timer/drain context.
   The fix was to `PostMessage` custom `WM_APP` messages (`WM_MIRRA_SET_TEXTURE`, +102)
   so they execute on a clean call stack. **Any new avatar-texture endpoint must follow
   that same dispatch pattern** — it is in exactly the same family of call as the ones
   that crashed. See `FabricDispatcher` around `RestPlugin_windows.cpp:386-425` for the
   template to copy.

### 1.4 Step 3 — VTO and the export (`clo_vto/native_vto/`)

Twelve steps. The last two are where a face would land in the user's browser:

- `step_11_export_note.py` — calls `/export`, which maps to
  `EXPORT_API->ExportGLTF(path, options, asGLB)` with `bIncludeHiddenObject = true`.
  Then it *verifies the content*: parses the GLB and blocks if `len(gltf.meshes)` is
  below `len(ctx.pattern_files) + 1`, because a known bug produced 4 panels and **no
  avatar mesh**.
- `step_12_texture_glb.py` — loads the GLB with `pygltflib`, embeds per-panel PNGs as
  base64 data URIs, rewrites `pbrMetallicRoughness.baseColorTexture`, writes
  `simulation_textured.glb`.

**`step_12` is a working, in-repo precedent for doing identity work in Python on the
exported GLB rather than inside CLO.** Phase B (6.3) is the same move applied to the
head. Note its design rule: every failure path returns `True` so a cosmetic step never
blocks the pipeline. Face injection should honor that rule.

### 1.5 What the customer actually sees

`website/frontend/package.json` pins `three ^0.185.1`, `@react-three/fiber ^9.6.1`,
`@react-three/drei ^10.7.6`. **The deliverable is an interactive 3D GLB in the browser,
not a rendered image.**

This matters more than anything else in the vendor comparison, and it kills an otherwise
very attractive cheap option: we cannot do image-space face swapping with an
identity-preserving diffusion model (PuLID at ~$0.04/image, InstantID ~$0.069, Nano
Banana Pro at $0.134 for 1K-2K) and call it done. Those produce a 2D picture. A user who
orbits the avatar would watch the illusion collapse. **The face has to exist in the
GLB.** 2D identity models stay useful for marketing hero shots and for the
texture-synthesis sub-step in 6.2, but they are not an architecture.

### 1.6 Known blocker you inherit

Per `.agent/clo-avatar-vto/simulation-bug-writeup-26_8_10.md`, the pipeline currently
exports, at best, arranged-but-unsewn panels **with no avatar mesh present**. Confirmed
against the checked-in artifact:

```
clo_vto/output/simulation.glb  ->  meshes: 4, materials: 1
  [0] '1' verts=1626   [1] '2' verts=1717   [2] '3' verts=401   [3] '7' verts=406
  attrs: POSITION, NORMAL, TEXCOORD_0        (no avatar mesh)
```

Phase A is **not** blocked by this — it changes the `.avt`, upstream of simulation.
Phase B **is** blocked, because it operates on an avatar mesh that currently never
reaches the export. Sequence accordingly.

(Separately: `avatar_generation/output/u_001-002/avatar.glb` from the legacy folder has
exactly 6890 vertices and `POSITION` only — no UVs. 6890 is the SMPL/STAR vertex count,
confirming that legacy path was body-model-based. It has no UV layout, so it is not
useful here.)

---

## Part 2 — The four places a face can be injected

| | Insertion point | Changes geometry? | Needs plugin change? | Needs CLO rebuild? | Effort |
|---|---|---|---|---|---|
| **A** | Rewrite face texture inside `.avt`, offline | No | No | No | Low |
| **B** | `SetAvatarMeshTexture` at runtime via new endpoint | No | Yes | Yes | Low-Med |
| **C** | Graft head mesh into the exported GLB | **Yes** | No | No | High |
| **D** | 2D face swap on a rendered image | No | No | No | Low |

**A and B are the same capability at different times.** A patches the artifact, B
patches the live CLO session. A is strictly better for our pipeline because the `.avt`
is what we persist and reuse across sessions; B is worth having anyway for iteration
speed and for a "preview before commit" UX.

**C is the only route to an actually identical face**, because identity lives at least
as much in skull/jaw/nose *shape* as in skin pixels. A photo pasted onto Jinho's head
geometry gives you a person wearing a mask of the user: convincing dead-on, uncanny at
three-quarter view.

**D is out** as an architecture, per 1.5. Keep it in the back pocket for marketing.

---

## Part 3 — Evidence: what was verified locally

Run against this machine and this repo on 2026-10-03. Separated out because the whole
build plan depends on it being true.

### 3.1 `.avt` is a ZIP with a magic prefix

```
$ python -c "import zipfile; print(zipfile.is_zipfile('clo_avatar_generation/input/base-1.avt'))"
True

first 16 bytes                       : b' AVT        CLO '
first PK\x03\x04 local header offset : 244210
entries                              : 30
```

The file opens as a ZIP despite the prefix because Python locates the central directory
from the end. **Note the first local header is at 244210, not 16** — there is a ~244 KB
region between the magic and the first ZIP member. Treat the container as "opaque prefix
+ ZIP": when rewriting, preserve byte-for-byte everything before the first local header
and rebuild the archive after it. Verify the round-trip opens in CLO before trusting it.

### 3.2 The 30 entries

```
first.dan                                33,066,665   <- binary scene/geometry, 97% of file
clofiles.json                                 4,187   <- texture name -> absolute path manifest
MV2_Jinho_01_face.jpg                       975,275   <- HEAD ALBEDO  (2048x2048 RGB)
MV2_Jinho_01_face_normal.jpg              1,050,880   <- (2048x2048)
MV2_Jinho_01_face_roughness.jpg             882,558
MV2_Jinho_01_body_Covered_7422644.jpg     1,526,376   <- torso albedo (2048x2048)
MV2_Jinho_01_Body_normal_7422646.jpg      1,251,714
MV2_Jinho_01_Body_roughness_7422648.jpg   1,656,201
MV2_Jinho_01_arm.jpg / _normal / _roughness
MV2_Jinho_01_leg.jpg / _normal / _roughness
MV2_Jinho_01_eye.jpg (256x256) / _normal / _Roughnessl      [sic - CLO's typo]
MV2_Jinho_01_eyelash.jpg
MV2_Jinho_01_tooth.jpg / _normal / _roughness
hair_main.jpg / _Normal / _Roughness / _alpha
hair_cap.jpg / _Normal / _alpha
Male_Sneaker_01_7407164.jpg
transparency_7407168.png
```

The avatar is textured as **separate mesh islands with separate maps**: face, body,
arms, legs, eyes, eyelashes, teeth, hair, shoes. CLO's own forum guidance — that the
base mesh is "a mesh ID group with sub groups within the UV ... for the torso, head,
arms and legs, eyeballs and mouth" — matches this exactly. A face swap touches three
files and nothing else. Hair is independent and swappable on its own later.

Also in the binary: `"hasSkinSuit": true`. The avatar wears CLO's skin suit, which is
why the torso map is named `body_Covered`. Not a face concern, but it means the body
albedo you see is not bare skin.

### 3.3 The face UV layout — and the resolution ceiling

Extracted `MV2_Jinho_01_face.jpg` and looked at it. It is a **frontal head unwrap**:
face centered and upright, ears mirrored left and right, scalp above, neck and
shoulders below. The face is not rotated, split, or distributed across islands. **A
frontal user photo maps onto this layout with a 2D warp — no 3D projection math
required for Phase A.**

Then ran OpenCV's stock frontal-face Haar cascade on the texture itself:

```
texture      : 2048 x 2048
face bbox px = (705, 370, 647, 647)
         uv  = (0.344, 0.181) - (0.660, 0.497)
```

A stock face detector finding a face *in a UV map* is the cleanest possible confirmation
that the layout is frontal and that landmark-based alignment will work.

**But read the number again: the face occupies 647x647 px of a 2048-square map, about
10% of the texture area.** That is the resolution ceiling for a naive drop-in swap, and
647px of face is *not* "high resolution identical" in a zoomable web viewer. Two fixes,
use both:

1. Write a **4096x4096** face map instead. Same UV layout, ~1294px of face. Costs ~4x
   the JPEG bytes (~4 MB) and a correspondingly larger `.avt`.
2. Source the face region from a **super-resolved** crop of the user photo rather than
   whatever resolution they happened to upload.

Must verify that CLO accepts a 4096-square map in this slot without downsampling — one
of the Phase 0 spikes in Part 7.

### 3.4 CLO's API DLL exports avatar texture functions we are not using

From `C:/Program Files/CLO Standalone OnlineAuth/CLOAPIInterface.dll`:

```
?SetAvatarMeshTexture@UtilityAPIInterface@CLOAPI@@UEAA_NAEBV?$basic_string@_W...@@H0@Z
?GetAvatarTexureMap@UtilityAPIInterface@CLOAPI@@UEAA?AV?$vector@V?$basic_string@D...@H@Z
?GetAvatarOpacityMaps@UtilityAPIInterface@CLOAPI@@...
?SetAvatarActivation@UtilityAPIInterface@CLOAPI@@...
?DeleteAvatar@UtilityAPIInterface@CLOAPI@@...
```

Demangling the two that matter:

```cpp
bool  UtilityAPIInterface::SetAvatarMeshTexture(const std::wstring&, int, const std::wstring&);
std::vector<std::string> UtilityAPIInterface::GetAvatarTexureMap(int);   // CLO's typo; keep it
```

Compare with what the plugin actually calls today (grep of `RestPlugin_windows.cpp`):
`ImportAvatar`, `ImportAvatarMeasurement`, `GetAvatarProperties`, `SetAvatarProperties`,
`IsShowAvatar`, `SetShowHideAvatar`, `AlignAvatarsAndGarmentToCenter`, plus the fabric
and pattern families. **`SetAvatarMeshTexture` is not wired. The capability is sitting
there unused.**

One real caveat: the signature was inferred from the mangled name, not read from a
header. `C:/Program Files/CLO Standalone OnlineAuth/ApiStubFiles/` is **empty** on this
machine — the SDK headers live wherever `CLO_SDK_PATH` in `clo_workspace/.env` points.
So the *parameter semantics* are **unconfirmed**: which wstring is the mesh/slot name
and which is the file path, and what the `int` indexes (avatar index? texture-type enum?
slot index?). Resolve by reading `UtilityAPIInterface.h` in the real SDK before writing
the endpoint. `GetAvatarTexureMap(int)` returning `vector<string>` is almost certainly
the discovery call that reveals slot ordering.

### 3.5 One landmine in `clofiles.json`

```json
{
  "MV2_Jinho_01_face.jpg": "C:/Users/Saumy/AppData/Local/CLO Virtual Fashion/CLO Standalone OnlineAuth/20268/1031/MV2_Jinho_01_face.jpg",
  ...
}
```

The manifest maps each embedded texture to an **absolute path on a teammate's machine**.
That raises a question Phase 0 must settle: **when CLO loads this `.avt`, does it use
the embedded ZIP entry or re-resolve from that cache path?** If it prefers the cache
path, swapping the embedded JPEG silently does nothing on a machine where that cache
exists and silently works on one where it does not — a debugging nightmare that will
cost someone a day.

Mitigation if it does prefer the cache: rewrite `clofiles.json` to point at a per-user
path alongside the swapped entry, and write the face JPEG there too.

---

## Part 4 — Getting a face out of one photo: the technology landscape

Four tiers, roughly by quality × cost × legal risk.

### 4.1 Tier 0 — Texture-only warp (no 3D reconstruction at all)

Detect facial landmarks in the user's photo and in `MV2_Jinho_01_face.jpg`, warp the
photo into the texture's landmark layout, blend, write back. Pure 2D.

- **Stack:** MediaPipe Face Landmarker (478 3D landmarks, **Apache 2.0**, commercially
  clean, CPU, ~30 ms) + OpenCV (already here, 4.10.0) for the piecewise-affine or
  thin-plate-spline warp and the multiband/Poisson blend.
- **New dependency:** `mediapipe` only. `cv2`, `Pillow`, `numpy`, `trimesh` are already
  installed in `.venv-win312`.
- **Cost:** $0 marginal. CPU-seconds.
- **Quality:** recognizable, not identical. Head *shape* stays Jinho's. Convincing at
  front view, degrades at three-quarter and profile.
- **Why it is still the right first move:** it is the entire delta between "every user
  sees a stranger" and "every user sees themselves," for ~2-3 weeks and no vendor.

### 4.2 Tier 1 — Commercial head-reconstruction APIs

Buy the head mesh. The 2026 market has consolidated hard:

| Vendor | Status | Price | Notes |
|---|---|---|---|
| **Avatar SDK / MetaPerson** (itSeez3D) | Active | **$800/mo, 6,000 avatars incl., $0.03 extra** | Selfie → rigged full-body or head-only. GLB/glTF/FBX. First avatar free, 7-day API trial. **REST API appears Enterprise-tier only** — Pro ships Unity/Unreal/Web SDKs. Best $/avatar by a wide margin. |
| **Avaturn** (same company as in3D) | Active | **$800/mo, 1,000 avatars incl., $0.15 extra** | API + SDK on Pro. More stylized than photoreal — a likeness, not a twin. |
| **Didimo** | Active | from ~$100 one-time; credit model, per-didimo rate not public | ~60s per digital twin. Get a real quote; published pricing is not usable for modeling. |
| **Hyper3D Rodin** | Active | ~$0.75/gen direct ($1.50/credit × 0.5); **~$0.40 via fal.ai**, ~$0.70 via 302.ai; Business $120/mo for API + 4K textures | **Commercial rights on all tiers, including free downloads.** General image-to-3D, not face-specialized. |
| **Tripo** | Active | **$0.20-0.30** per image-to-3D (20-30 credits @ $0.01) | +5-20 credits for HD geometry / quad mesh. Cheapest per call. General-purpose. |
| **Reallusion Headshot 3** | Active (Apr 2026, CC5) | **$199 perpetual** + ~$0.30/image for its Nano-Banana-backed generator | Highest likeness quality in the list. **GUI plugin; batch automation unconfirmed** — probably an artist tool for us, not a service. |
| ~~Ready Player Me~~ | **Dead — shut down 2026-01-31** (Netflix acquisition) | — | Do not design against it. |
| ~~Union Avatars~~ | **Dead — offline July 2026**, no announcement | — | Same. |

Two of the eight best-known vendors in this space died in the last nine months, one of
them without telling anyone. **Whatever we pick, the adapter must be swappable** — one
interface, pluggable backends, and a self-hostable fallback (4.3) behind it.

### 4.3 Tier 2 — Open-source, self-hosted, commercially licensed

| Model | License | VRAM | Notes |
|---|---|---|---|
| **TRELLIS 2** (Microsoft) | **MIT, no usage restrictions** | ~16 GB (A100/A6000 tested) | Current quality leader among fully-open image-to-3D. PBR materials. General-purpose, not face-tuned. |
| **Hunyuan3D 2.1** (Tencent) | Tencent Community License — free commercially **until 1M MAU**; **does not apply in UK/EU/South Korea** | 10-29 GB | Best texture/material accuracy of the open models. Read the geography clause before shipping in the EU. |
| **FLAME 2023 Open** | **CC-BY-4.0 — commercial use permitted with attribution** | n/a (parametric) | The *only* commercially usable FLAME. Gives topology + a shape basis; you still build the fitter. |
| **MediaPipe Face Landmarker** | **Apache 2.0** | CPU | 478 landmarks. The Tier-0 workhorse. |

Self-hosted economics: a TRELLIS 2 head on an L4/A10G at ~$0.50-1.00/hr and ~30-60 s
per head is ~**$0.01-0.02/head** in compute, plus idle. That beats every Tier 1 API by
an order of magnitude *at volume* — and loses badly at low volume, where idle GPU cost
dominates and you are also paying an engineer to keep it alive.

### 4.4 Tier 3 — Research SOTA (benchmark only, do not ship)

Best accuracy available today, all legally unusable for us:

- **Pixel3DMM** (2025) — per-pixel normals + UV priors from ViTs constraining a 3DMM
  fit. Beat MICA in a technical-artist user study (1.6 vs 1.42). **CC-BY-NC-4.0, and
  requires a FLAME account.** Non-commercial twice over.
- **FaceLift** (ICCV 2025) — multi-view latent diffusion generates side/back views, a
  transformer reconstructs 360° 3D Gaussian splats. Beautiful; **splats are not a
  mesh**, so it needs conversion before it could sit in a GLB next to simulated cloth.
- **DECA / EMOCA / MICA / SMIRK / TokenFace** — all FLAME-based, all non-commercial.

Use these to set the quality bar and to score vendors. Do not put them in the product.

### 4.5 The licensing trap — read before anyone downloads anything

The entire academic face/body modeling ecosystem rests on Max Planck models whose
license grants use "for the sole purpose of performing non-commercial scientific
research, non-commercial education, or non-commercial artistic projects," and states
that "any other use, in particular any use for commercial purposes, is prohibited ...
includ[ing] incorporation in a commercial product, use in a commercial service." It
further prohibits using the model "to train methods/algorithms/neural networks/etc. for
commercial use of any kind."

Scope:

- **Non-commercial:** FLAME 2017 / 2019 / 2020 / Blender add-on, SMPL, SMPL-X, **STAR**.
- **Commercial OK:** **FLAME 2023 Open only** (CC-BY-4.0).

**This repo already has a problem here, independent of faces.** `libs/star/LICENSE` and
`models/star_1_1/LICENSE.txt` are both that Max Planck non-commercial license, and the
STAR weights are vendored under `models/star_1_1/{male,female,neutral}`. `libs/star` is
referenced from `libs/star/convertors/convert_smplx_to_star.py`, and the legacy
`avatar_generation/` output carries SMPL/STAR's 6890-vertex signature. If STAR is dead
code from the superseded `avatar_generation/` path, **delete it** — the license also
forbids redistribution, and it is sitting in a repo. If it is load-bearing anywhere, it
needs a commercial license from Max Planck or a replacement.

Worth raising with whoever owns legal *before* face work starts, since the answer
("can we use MPI models commercially?") determines whether half of Tier 2/3 is even on
the table.

---

## Part 5 — Why the obvious shortcut doesn't work

Stating this explicitly because it will come up.

**"Can't we just ask an image model to generate the face texture?"** — feed the user
photo plus the existing `MV2_Jinho_01_face.jpg` to Nano Banana Pro ($0.134 at 1K-2K,
$0.24 at 4K) or Flux Kontext and ask for a UV-space face map.

Partly. Image models are genuinely good at *identity-preserving face synthesis* and
genuinely bad at *UV layout discipline*. They will return a beautiful face that is 2-5%
misaligned against the mesh's UV coordinates — and a 2% misalignment in UV space puts
the eyes slightly off the eye sockets, which reads as deeply wrong to a human in a way
a blurrier but correctly registered texture does not.

The right use of these models is **inside** the Tier-0 pipeline, not instead of it: a
landmark-driven geometric warp guarantees registration, then optionally an image model
*inpaints* the regions where the photo has no data (under-chin, ear edges, scalp line).
Registration from geometry, plausibility from the model. Not the other way round.

---

## Part 6 — Recommended architecture

### 6.1 Phase A — `face_fitting/` module and the `.avt` texture patch

New top-level package following repo conventions (`product_ingestion/`-style: a
`run_*.py` entry point, numbered step modules, a context object, JSON artifacts):

```
face_fitting/
  run_face_fitting.py          # python face_fitting/run_face_fitting.py --user-id u_001
  face_runtime/
    context.py                 # FaceContext: user_id, photo_path, run_dir, artifacts
    step_01_validate_photo.py  # resolution, single face, frontality, lighting, occlusion
    step_02_landmarks.py       # MediaPipe 478 on the photo AND on the base face texture
    step_03_warp.py            # TPS / piecewise-affine: photo -> UV layout
    step_04_skin_match.py      # match warped face to body/arm/leg albedo (see 6.2)
    step_05_blend.py           # multiband + Poisson at the oval boundary
    step_06_maps.py            # derive normal + roughness deltas; keep base as fallback
    step_07_patch_avt.py       # rewrite ZIP entries; preserve prefix + clofiles.json
  reference/
    base_face_landmarks.json   # cached 478 landmarks of MV2_Jinho_01_face.jpg
    face_region_mask.png       # feathered oval, authored once by hand
```

Insertion into Step 1: after `step_11_save_outputs.py` writes `<user_id>.avt`, patch it.
Keep it a **separate runnable pipeline** rather than a 12th step, so a user can re-shoot
their photo without regenerating the whole avatar, and so a face failure never blocks
avatar generation (same philosophy as `step_12_texture_glb.py`).

Hard requirements from Part 3:

- Preserve bytes `[0, 244210)` of the container exactly; rebuild the ZIP after them.
- Write **4096-square** albedo, not 2048 (3.3) — pending the Phase 0 check that CLO
  accepts it.
- Settle the `clofiles.json` cache-path question (3.5) before trusting any result.
- Never overwrite `base-1.avt`. Patch a copy in the run directory.

### 6.2 The quality details that decide whether this looks real

This is where Phase A succeeds or fails. Budget real time for it.

**Skin-tone continuity.** The face map is one of six albedo maps. Swap only the face and
you get a head that does not match its own neck, arms and legs — the single most likely
way this ships looking broken. Fix: compute mean Lab chromaticity of the warped face and
of `body_Covered`, `arm`, `leg`, then shift **all body maps** toward the face's tone —
not the reverse, since the face is the identity signal and must not be recolored. That
means Phase A writes six-plus texture entries, not three. Hands and neck are where
mismatch shows first.

**Lighting normalization.** A user photo carries its own lighting; an albedo map must be
lighting-free or CLO's renderer double-lights it. At minimum, estimate and divide out
low-frequency luminance while retaining high-frequency detail (pores, stubble, moles) —
that detail *is* the identity signal, and it is exactly what a naive histogram match
destroys.

**The boundary.** Feather over ~5% of face width, in Lab, using a hand-authored mask
(`face_region_mask.png`) rather than a detector bbox — the bbox from 3.3 is square, the
face is an oval, and the hairline and jaw transitions want artistic control once.

**Eyes and teeth stay CLO's.** `MV2_Jinho_01_eye.jpg` is 256-square and separate. Do not
transplant eyes from a photo; the geometry is a sphere with its own UV, and a warped
photo iris will not land on it. If eye color matters, recolor the 256-square map
parametrically.

**Failure gates.** Reject and ask for a re-shoot rather than shipping a bad face: no face
or more than one detected, yaw beyond ~±15°, face region below a source-pixel threshold
(suggest 512 px), heavy occlusion (hand, mask, sunglasses), extreme backlighting. A clear
"retake your photo" beats a disturbing avatar.

**Acceptance metric.** Don't eyeball it. Render the patched avatar front-on, run a face
embedding (ArcFace or similar) on the render and on the source photo, require cosine
similarity above a threshold calibrated on ~20 internal faces. Gate releases on it.

### 6.3 Phase B — real head geometry, grafted into the GLB

Only after Phase A ships and the 1.6 avatar-missing-from-export bug is fixed.

New `step_13_face_graft.py` in `clo_vto/native_vto/`, running after `step_12`:

1. Reconstruct a textured head mesh from the photo (vendor adapter — Tier 1 or 2).
2. Load `simulation_textured.glb`; identify the avatar mesh (by name, or via the
   mesh-count logic `step_11` already uses).
3. Isolate the head region of the avatar mesh. The clean way is by **UV island**, not by
   position: head vertices are exactly those whose UVs address the face map. Reliable,
   and a direct payoff from the island structure in 3.2.
4. Rigid-align the reconstructed head to the avatar's head (Procrustes on the neck
   boundary loop plus landmark correspondence), then non-rigidly fit the last ~1 cm so
   the neck seam closes.
5. Replace faces, stitch the neck ring, embed the new texture as a data URI — the exact
   mechanics `step_12` already implements (`_embed_texture`, `_apply_texture`).
6. Write `simulation_face.glb`. Fall back to the Phase A result on any failure.

**Why this is safe with respect to physics:** it happens entirely *after* simulation. The
cloth solver never sees the new head, so collision, drape and the 10-seam system are
untouched. That is the strongest argument for doing geometry in post rather than
importing a custom avatar into CLO.

**The counter-option — import a custom full avatar OBJ/GLB into CLO** (`ImportAvatar`
accepts OBJ/FBX/GLB; the plugin already exposes `POST /import-avatar`) — is a trap. You
would lose CLO's native measurement morphing (all of `step_08`), its skinning, and its
tuned collision geometry, in exchange for a face. CLO's own documentation and community
are clear that avatars "do not change substantially" and that the Avatar Style
Configurator makes only minor adjustments; third-party avatars are supported but
degraded. Don't trade a working body pipeline for a head.

**Hair.** `hair_main.*` and `hair_cap.*` are separate entries with alpha maps. Hair is a
separate project and the thing users will notice second. Scope it out of Phase A and B
explicitly; a neutral short style on everyone is an acceptable v1.

### 6.4 Phase A' — the runtime endpoint (optional, parallel)

`POST /avatar/set-mesh-texture {slot, avatar_index, texture_path}` wrapping
`SetAvatarMeshTexture`, plus `GET /avatar/texture-maps` wrapping `GetAvatarTexureMap`.
About a day of plugin work **once the header semantics are confirmed** (3.4), and it
must use the `PostMessage`/`WM_APP` dispatch pattern rather than the queue drain (1.3).
Also needs the macOS counterpart in `mac/RestPlugin_macOS.cpp` to preserve parity — the
contract's `parity_rule` exists for a reason. Nice to have; not on the critical path.

---

## Part 7 — Timeline

Assumes one engineer, with a designer available for ~3 days (face mask, look-dev QA).
Calendar weeks, not ideal-engineer weeks.

### Phase 0 — De-risking spikes (3-5 days). Do these before committing to anything.

| # | Spike | Kills the plan if it fails? |
|---|---|---|
| 1 | Swap `MV2_Jinho_01_face.jpg` for a solid red square, rebuild the `.avt`, open in CLO | **Yes.** If CLO rejects a rebuilt container, Phase A is dead and we go straight to Phase B |
| 2 | Does CLO use the embedded entry or the `clofiles.json` cache path? (3.5) | No, but it changes the design |
| 3 | Does CLO accept a 4096-square map in that slot without downsampling? (3.3) | No — fall back to 2048 and manage expectations |
| 4 | Read `UtilityAPIInterface.h` in the real SDK; confirm `SetAvatarMeshTexture` params | No — only affects Phase A' |
| 5 | Export a *good* GLB (avatar present); confirm the head has UVs and a distinct material | Only for Phase B — and it is blocked on 1.6 |

Spike 1 is half a day and it determines everything. Do it first, do it Monday.

### Phase A — Texture face (2-3 weeks)

| Week | Work |
|---|---|
| 1 | `face_fitting/` scaffold, photo validation, MediaPipe landmarks on photo + base texture, first TPS warp end-to-end. Target: recognizable; ugly seams fine |
| 2 | Skin-tone matching across all six albedo maps, lighting normalization, multiband blend, hand-authored mask, normal/roughness handling. The week that decides quality |
| 3 | `.avt` patch step hardened, failure gates, ArcFace acceptance metric, 20-face internal test set, wire into Step 1, docs |

**Ship gate: ~3 weeks to a recognizable face on the live avatar.**

### Phase A' — Runtime endpoint (1 week, parallelizable, optional)

Windows + macOS endpoint, contract and version-file updates, client method, test.

### Phase B — Geometry face (5-7 weeks, starts after 1.6 is fixed)

| Weeks | Work |
|---|---|
| 1 | Vendor bake-off on the same 20 faces: Avatar SDK vs Tripo vs Rodin vs self-hosted TRELLIS 2. Score likeness, topology sanity, texture resolution, latency, failure rate |
| 2 | Adapter interface + chosen backend; `face_reconstruction/` package with a swappable provider (two vendors died this year — build for replacement) |
| 3-4 | `step_13_face_graft.py`: UV-island head isolation, Procrustes + non-rigid neck fit, mesh splice, texture embed. The hard engineering |
| 5 | Neck seam quality, skin-tone continuity at the graft, LOD/filesize budget for the web viewer |
| 6-7 | Buffer. Something here will take two weeks longer than planned; historically it is the neck seam |

**Realistic total to "high-resolution identical 3D face": ~9-11 weeks from start**,
including Phase A, and assuming the simulation/export blocker is resolved in parallel by
someone else. If it is not, Phase B cannot start — that is the schedule risk to
escalate, not the face work itself.

---

## Part 8 — Costs

### 8.1 Build cost

| Item | Engineer-weeks |
|---|---|
| Phase 0 spikes | 0.5-1 |
| Phase A | 2-3 |
| Phase A' (optional) | 1 |
| Phase B | 5-7 |
| **Total** | **8.5-12** |

Plus ~3 designer-days (face mask authoring, look-dev QA pass).

### 8.2 Per-avatar run cost

The critical economic point: **a face is generated once per user and reused forever**,
exactly like the avatar. It is not a per-try-on cost. Even an expensive option is
negligible against user lifetime value.

| Option | Per face | 1,000 users | 10,000 users | 100,000 users |
|---|---|---|---|---|
| **Phase A (texture warp, self-run)** | ~$0 (CPU-seconds) | ~$0 | ~$0 | ~$0 |
| Tripo image-to-3D | $0.20-0.30 | $200-300 | $2,000-3,000 | $20,000-30,000 |
| Rodin via fal.ai | ~$0.40 | $400 | $4,000 | $40,000 |
| Rodin direct | ~$0.75 | $750 | $7,500 | $75,000 |
| Avatar SDK Pro | $800/mo covers 6,000/mo; $0.03 over | $800/mo | $800/mo | $800/mo + ~$1,320 |
| Avaturn Pro | $800/mo covers 1,000/mo; $0.15 over | $800/mo | $800/mo + $1,350 | $800/mo + $14,850 |
| Self-hosted TRELLIS 2 (L4 @ ~$0.75/hr, ~45 s/head) | ~$0.01-0.02 + idle | idle dominates | ~$150-200 + idle | ~$1,500-2,000 + idle |

**Avatar SDK is the standout commercial deal** — $800/mo flat for 6,000 avatars/month
($0.13 each at full use, $0.03 beyond) is cheaper than Avaturn at every volume and
cheaper than per-call vendors above roughly 2,700 faces/month. Caveat: **REST API appears
to be Enterprise-tier only**; Pro ships Unity/Unreal/Web SDKs. Confirm server-side REST
is available on Pro before modeling on it, or budget for Enterprise.

**Crossover:** below ~2,000 faces/month, per-call (Tripo at $0.20-0.30) beats any $800/mo
subscription. Above ~5,000/month, self-hosting TRELLIS 2 starts to win if we already run
GPUs for anything else. Start per-call, keep the adapter swappable.

### 8.3 Licenses and one-offs

| Item | Cost | Needed? |
|---|---|---|
| MediaPipe, OpenCV, pygltflib, Pillow, trimesh | $0 (Apache/MIT/BSD) | Yes — Phase A |
| TRELLIS 2 | $0 (MIT) | Only if self-hosting |
| FLAME 2023 Open | $0 (CC-BY-4.0, attribution required) | Only if building our own fitter |
| KeenTools FaceBuilder (Blender) | $699/yr studio floating; $15.99-39.99/mo individual | Only as an artist tool for golden-reference heads |
| Reallusion Headshot 3 | $199 perpetual + ~$0.30/image | Only as an artist tool / quality bar |
| MPI commercial license (FLAME/SMPL/STAR) | Quote from ps-license@tue.mpg.de | **Only if 4.5 says we must keep STAR** |
| Nano Banana Pro / Flux / PuLID for seam inpainting | $0.039-0.24/image | Optional, Phase A week 2 |

**Recommended spend to ship Phase A: $0.** That is the argument for doing it first.

---

## Part 9 — Risks and open questions

| Risk | Impact | Mitigation |
|---|---|---|
| CLO rejects a rebuilt `.avt` container | Phase A dead | **Phase 0 spike 1.** Fallback: Phase A' runtime `SetAvatarMeshTexture`, or straight to Phase B |
| CLO reads textures from `clofiles.json` cache paths, not embedded entries | Silent no-op; works on one machine, not another | Phase 0 spike 2; write to both locations |
| Face capped at 647 px (3.3) | "High resolution" not met | 4096-square map + super-resolved source crop; verify CLO accepts 4K |
| Avatar still missing from GLB export (1.6) | **Phase B cannot start** | Owned by the existing simulation-bug workstream — escalate as a dependency, not a face problem |
| `SetAvatarMeshTexture` param semantics wrong | Phase A' slips | Read the real SDK header first; use `GetAvatarTexureMap` to discover slots |
| New avatar-texture CAPI call crashes from the queue drain | Plugin instability | Copy the `WM_APP` / `FabricDispatcher` pattern (`RestPlugin_windows.cpp:188`) — a known, already-solved failure mode here |
| Vendor shutdown | Rework | Two died in 2026 (RPM, Union Avatars). Adapter interface + self-hostable fallback, mandatory |
| MPI non-commercial models in a commercial product (4.5) | Legal | Audit `libs/star/` and `models/star_1_1/` now; delete if dead code |
| Uncanny valley at three-quarter view in Phase A | User trust | Set expectations in UI; ArcFace gate; prioritize Phase B |
| Biometric data (face photos) | Regulatory (GDPR Art. 9, BIPA) | Out of scope for this doc but **must** be settled before launch: retention, consent, deletion. Flag to whoever owns privacy |

**Decisions needed:**

1. Ship Phase A alone as a milestone, or hold until Phase B? (Recommendation: ship A. It
   is the difference between a stranger's face and the user's, for ~3 weeks and $0.)
2. Is STAR in `libs/` live or dead code? (4.5 — needs an answer regardless.)
3. Target volume for the first 12 months? It picks the vendor tier in 8.2.
4. Is a designer available for the mask and look-dev, or does the engineer do it?

---

## Part 10 — Sources

Local evidence (verified 2026-10-03 on this machine): `clo_avatar_generation/input/base-1.avt`,
`C:/Program Files/CLO Standalone OnlineAuth/CLOAPIInterface.dll`,
`clo_vto/output/simulation.glb`, `clo_workspace/windows/RestPlugin_windows.cpp`,
`clo_workspace/plugin_contract.json`, `website/frontend/package.json`,
`libs/star/LICENSE`, `models/star_1_1/LICENSE.txt`.

External:

- [FLAME model license](https://flame.is.tue.mpg.de/modellicense.html) — non-commercial vs. FLAME 2023 Open CC-BY-4.0
- [Pixel3DMM (GitHub)](https://github.com/SimonGiebenhain/pixel3dmm) — CC-BY-NC-4.0, requires FLAME
- [Pixel3DMM paper](https://arxiv.org/pdf/2505.00615)
- [FaceLift, ICCV 2025](https://arxiv.org/abs/2412.17812) / [GitHub](https://github.com/weijielyu/FaceLift)
- [Avatar SDK cloud pricing](https://avatarsdk.com/pricing-cloud/)
- [Avaturn pricing](https://avaturn.me/pricing/)
- [Avatar Platforms in 2026: Who's Alive, Who's Gone](https://avatarsdk.com/ninja-forms/2f5hk/) — RPM and Union Avatars shutdowns
- [Tripo API pricing](https://developers.tripo3d.ai/en/pricing)
- [Hyper3D Rodin on fal.ai](https://fal.ai/models/fal-ai/hyper3d/rodin) / [Rodin review & pricing](https://www.glbgpt.com/hub/hyper3d-rodin-review/)
- [Reallusion Headshot 3](https://www.reallusion.com/character-creator/headshot/) / [Headshot 3 pricing thread](https://discussions.reallusion.com/t/important-headshot-3s-ai-features-pricing/17053)
- [KeenTools FaceBuilder for Blender](https://keentools.io/products/facebuilder-for-blender)
- [Hunyuan3D vs TRELLIS vs TripoSR (2026)](https://triposr.org/blog/hunyuan3d-vs-trellis) — licenses, VRAM
- [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js) — 478 landmarks, Apache 2.0
- [CLO: Using 3rd Party Avatars](https://support.clo3d.com/hc/en-us/community/posts/360000165927-Using-3rd-Party-Avatars-in-CLO) — avatar mesh ID groups / UV sub-groups
- [CLO: Import OBJ](https://support.clo3d.com/hc/en-us/articles/115012226667-Import-OBJ)
- [AI image generation API pricing, 2026](https://www.buildmvpfast.com/api-costs/ai-image) — PuLID / InstantID / Nano Banana rates
