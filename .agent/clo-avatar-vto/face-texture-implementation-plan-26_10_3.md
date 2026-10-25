# Face Personalization — Phase 1 (Texture) Implementation Plan

Written 2026-10-03. Companion to `face-personalization-deep-dive-26_10_3.md`, which
surveys the whole problem space and the vendor/licensing landscape. **This document is
narrower and more actionable**: it records exactly what we verified about the avatar's
head texture, what the 360° viewer requirement changes, and the code design we are
going to build — shaped so that Phase 2 (real head geometry) swaps implementations
rather than rewriting the pipeline.

**Product constraint driving this plan:** the avatar lives in a movable, rotatable
frame with a simulation mode. It is viewed from every angle. So even the texture-only
phase has to be a **360° head texture problem**, not a "paste a face on the front"
problem. That changes the capture spec and the compositor design, and it is the main
reason this document exists separately from the deep dive.

---

## 0. Status

| | |
|---|---|
| Phase 1 — head texture from photos | **Design locked, implementation next** |
| Phase 2 — head geometry graft into GLB | Deferred. Hooks designed in, nothing built |
| Blocking unknown | Does CLO read the embedded texture or the `clofiles.json` cache path? (§1.8) |
| Test artifact ready | `clo_avatar_generation/input/base-1-FACETEST.avt` |

---

## Part 1 — What we verified

Everything here was run against `clo_avatar_generation/input/base-1.avt` on a Windows
machine with CLO installed, 2026-10-03. This is measured, not assumed. Anything still
unverified is called out in §1.8 rather than quietly presented as fact.

### 1.1 `.avt` container anatomy

```
[0      .. 16)        magic  " AVT        CLO "
[16     .. 244210)    header blob: version info, "5.1_MaleTemplate_07", PNG thumbnail
[244210 .. EOF)       standard ZIP, 30 entries, deflate
```

The ZIP carries `first.dan` (33,066,665 B uncompressed — 97% of the file, the scene and
geometry), `clofiles.json` (a texture-name → absolute-path manifest), and 28 loose
texture images.

Three dialect quirks that a naive `zipfile`-based rebuild silently gets wrong:

1. **Offsets inside the archive are archive-relative**, so the 244 KB prefix shifts every
   one of them. Recover the shift as `concat = eocd_pos - cd_size - cd_offset`.
2. **Local headers declare version 45 with a 20-byte ZIP64 placeholder extra field**,
   while the real sizes sit in the 32-bit fields.
3. **`clofiles.json` carries the "internal attributes" text-file bit set to 1.**

### 1.2 Byte-identical repack — proven

Reading the container and writing it back with no edits produces a file identical to the
original at all **33,927,576** bytes. This matters more than it sounds: it means any
difference in a patched file is exactly and only what we intended to change, so "did we
corrupt something" stops being a debugging hypothesis.

Implementation note: untouched entries are copied out as **raw deflate streams with
their original local headers**, never re-compressed. That is what makes the guarantee
hold, and it is why `replace_entry` reuses the replaced entry's own header bytes rather
than synthesizing fresh ones.

### 1.3 The scene binary references textures by **filename only**

Searching the decompressed `first.dan`:

```
qsFileName     MV2_Jinho_01_face.jpg  bAIFindBR enWrapS ...
qsFileNameUTF8 MV2_Jinho_01_face.jpg  qsAIFileName ...
```

A tagged key/value serialization (`qs` = QString, `b` = bool, `en` = enum). **No hash,
no byte offset, no embedded size, no checksum.** So swapping the JPEG payload requires
zero edits to the 33 MB scene binary. The single most load-bearing finding for Phase 1:
the hard version of this problem does not exist.

A patch run confirms it end to end — `entries changed: ['MV2_Jinho_01_face.jpg']`, the
244 KB prefix preserved byte-for-byte, the other 29 entries bit-identical.

### 1.4 The head is one texture set, laid out as a frontal unwrap

The avatar (`MV2_Jinho_01`) is textured as **separate mesh islands with separate maps** —
face, body, arms, legs, eyes, eyelashes, teeth, hair, shoes. The head set is:

| Entry | Size | Role |
|---|---|---|
| `MV2_Jinho_01_face.jpg` | 2048×2048 | albedo — **the one we replace** |
| `MV2_Jinho_01_face_normal.jpg` | 2048×2048 | surface detail |
| `MV2_Jinho_01_face_roughness.jpg` | 2048×2048 | specular response |

Visual inspection of the albedo: face upright and centred, ears mirrored left and right,
scalp above, neck and shoulders below. Not rotated, not split across islands. **A frontal
photo registers onto it with a 2D warp — no 3D projection required.**

OpenCV's stock frontal-face Haar cascade detects a face *inside the UV map* at
`(705, 370, 647, 647)` px = uv `(0.344, 0.181)–(0.660, 0.497)`, which is about as direct
a confirmation of "this layout is frontal" as you can get.

### 1.5 Registration anchors and accuracy

Measured on the stock 2048² albedo:

| Anchor | px | uv |
|---|---|---|
| left eye | (862, 643) | (0.4209, 0.3140) |
| right eye | (1166, 638) | (0.5693, 0.3115) |
| mouth centre | (1024, 907) | (0.5000, 0.4429) |
| interocular distance | 304 px | — |

Eye midpoint lands at u = 0.495 — the texture midline — confirming a symmetric frontal
projection.

Self-test: a photo rotated 11°, scaled 0.78 and translated, pushed through the warp,
landed its eyes **1.6 px and 2.9 px** from target on a 2048² map (~0.1% of width), and
blended into the stock ears/scalp/neck with no visible seam.

Caveat, stated plainly: that test photo was derived from the same source face, so
detection had an easy case, and a 3-point similarity transform can only translate,
rotate and scale a face — **it cannot reshape one**. Real photos need MediaPipe's
478-point mesh for a dense piecewise-affine warp. Treat the 1.6 px figure as proof the
*transform plumbing* is correct, not as expected accuracy on customer photos.

### 1.6 Resolution ceiling

The face occupies 647×647 px of a 2048² map — roughly **10% of the texture area**. In a
rotatable, zoomable viewer that is not enough. Mitigations, use both:

1. Write a **4096×4096** albedo. Same UV layout, ~1294 px of face. Costs ~4 MB and a
   correspondingly larger `.avt`.
2. Source the face from a **super-resolved crop**, not from whatever the user uploaded.

Pending the Phase 0 check that CLO accepts 4096² in this slot without downsampling.

### 1.7 CLO API surface

`CLOAPIInterface.dll` exports, among others:

```cpp
bool  UtilityAPIInterface::SetAvatarMeshTexture(const std::wstring&, int, const std::wstring&);
std::vector<std::string> UtilityAPIInterface::GetAvatarTexureMap(int);   // CLO's typo
```

Neither is wired into our REST plugin today. Two external corroborations arrived after
we found these: the `for_measurements/` workstream independently cites
`SetAvatarMeshTexture(…, 0, png)` — their middle-argument `0` suggests the `int` is a
**mesh/slot index**, not an avatar index — and CLO's changelog records a
**`SetAvatarTextureMap` added in v8.0.0 (April 2025)**, which may be the newer supported
path. Check which the installed build exposes before writing an endpoint.

### 1.8 Still unverified — do not build past these

| # | Unknown | Why it matters |
|---|---|---|
| 1 | Does CLO load the **embedded ZIP entry** or re-resolve from the absolute path in `clofiles.json` (which points at `C:/Users/Saumy/...`)? | If it prefers the cache, the patch is a silent no-op on some machines and works on others |
| 2 | Does CLO accept a **4096²** map in this slot? | Decides whether §1.6 fix #1 is available |
| 3 | **Is the head UV mirrored or full?** (§2.3) | Decides whether asymmetric faces are representable at all. The single biggest risk in this document |
| 4 | `SetAvatarMeshTexture` parameter semantics | Only affects the optional runtime endpoint |

`base-1-FACETEST.avt` — the stock albedo overlaid with a labelled UV grid and the face
bbox outlined — answers **1 and 3 together** in one look. Open it, rotate the avatar.

---

## Part 2 — What the 360° requirement changes

This is the part the earlier deep dive under-weighted, because at that point we assumed
a mostly front-facing product view.

### 2.1 A frontal photo fills a minority of the head

The head albedo covers the **entire head surface** — face, ears, scalp, back, neck. A
single frontal photo contains data for the face oval and nothing else. Patch only that
and rotate the avatar, and the user sees:

```
  front view          3/4 view              profile            back
 ┌──────────┐      ┌──────────┐         ┌──────────┐      ┌──────────┐
 │ THEIR    │      │ their    │         │  stock   │      │  stock   │
 │ face     │      │ face +   │         │  ear +   │      │  head +  │
 │ (good)   │      │ stock ear│         │  stock   │      │  stock   │
 │          │      │ (seam!)  │         │  jawline │      │  hair    │
 └──────────┘      └──────────┘         └──────────┘      └──────────┘
   convincing        the problem          a stranger       a stranger
```

The identity illusion survives roughly ±30° of yaw and collapses past it. In a rotatable
frame the user *will* go past it — that is the whole point of the frame.

### 2.2 UV coverage budget

Measured detail energy (mean Sobel magnitude) across the stock albedo, in tenths:

```
by u:  0.00  0.10  0.20  0.30  0.40  0.50  0.60  0.70  0.80  0.90
        6.1   7.7   8.5  10.6  11.4  11.3  10.6   9.8   8.3   5.5

by v:  0.00  0.10  0.20  0.30  0.40  0.50  0.60  0.70  0.80  0.90
        5.2   7.7  11.9  18.0  13.8  14.2   8.6   4.5   3.0   2.6
```

Reading that:

- **High-information head region: u ∈ [0.15, 0.85], v ∈ [0.10, 0.60].** Everything
  outside is low-detail filler — the neck/chest gradient below v≈0.65 and the
  wrap-around margins at the u extremes.
- The v-peak at 0.30 (18.0) is the brow/eye band; 0.40–0.50 is nose and mouth.
- So the face oval the single-photo warp fills is roughly **one quarter of the
  informative head area**. The other three quarters — ears, temples, jawline from the
  side, scalp edge, back of head — are what side and back views have to supply.

### 2.3 ⚠ The mirror-symmetry question — biggest open risk

The stock albedo is **left-right mirror-symmetric**: mean absolute difference between
the image and its horizontal flip is **5.78/255**, which is JPEG noise, and no column
band exceeds the asymmetry threshold.

Two very different explanations, and we cannot tell them apart from the image alone:

**(a) Symmetric artwork, full UV.** The artist painted one side and mirrored it, but the
mesh gives the left and right halves of the head their own texels. Asymmetric detail is
representable; the stock art simply doesn't use it. *Fine — proceed as planned.*

**(b) Mirrored UV.** The mesh maps the left and right halves of the head onto the **same
texels**. Then the texture is physically incapable of carrying asymmetric detail: a mole
on one cheek appears on both, a side-parted hairline parts both ways, and a left/right
photo pair cannot be composited independently because they would fight over the same
pixels.

If (b) holds, the 360° texture plan needs rework — probably a UV re-layout on the head
island or an earlier jump to Phase 2 geometry. **Resolve before writing the compositor.**
`base-1-FACETEST.avt` answers it: if both sides of the head show the *same* grid label,
the UV is mirrored; different labels means full.

### 2.4 Capture specification

What we ask the user for, and what each view is allowed to fill:

| View | Yaw | Fills |
|---|---|---|
| **front** | 0° | face oval, forehead, chin, front of neck — the identity core |
| **left 3/4** | ~45° | left cheek, temple, jawline, nasolabial, hairline edge |
| **right 3/4** | ~45° | mirror of the above |
| **left profile** | ~90° | left ear, side of skull, jaw rear |
| **right profile** | ~90° | mirror |
| *back* | 180° | occiput — **skip it** (§2.5) |

**v1 ships with front + two 3/4 views** — three photos. That is the lowest-friction
capture that covers the informative region in §2.2 out to ~±70° of yaw, which is where
the rotatable frame spends almost all its time. Profiles are a v1.1 upgrade; the design
below takes N views, so adding them is data, not code.

Compatibility note: the `for_measurements/` workstream already collects **front + side**
for body measurement. The side photo is a 90° profile, not a 3/4 — usable for the ear and
skull band, not for the cheek. Worth aligning the two capture flows so the user shoots
once, not twice.

### 2.5 What a 360° *texture* still will not fix

Be honest with ourselves and with the UI about this:

- **Head shape stays CLO's.** Skull, jaw, nose and brow are geometry. A perfect texture
  on the wrong skull reads as a mask in motion, even when it photographs well. This is
  precisely what Phase 2 exists to fix, and it is why we are designing for the swap now.
- **Hair is a separate mesh with its own maps** (`hair_main.*`, `hair_cap.*`, with alpha).
  Projecting a photo onto the head albedo does nothing to the hair. A user with a
  different hairstyle will see the stock one. Scope hair out of Phase 1 explicitly; a
  neutral style on everyone is an acceptable v1.
- **Back of the head is unrecoverable from face photos** and is mostly hair anyway. Fill
  it by extending skin tone and the hairline, and never claim it is reconstructed.
- **Ears are geometry too.** A side photo gives ear *texture*; the ear *shape* remains
  the stock one.

---

## Part 3 — Code design

### 3.1 Principles

1. **Never block avatar generation.** A face failure degrades to the stock head, logs,
   and returns success — the rule `step_12_texture_glb.py` already follows.
2. **Separately runnable.** Re-shooting a photo must not require regenerating the avatar.
3. **N views from day one.** Internals take a list of views. Shipping with three is a
   config value, not an architecture.
4. **Phase 2 swaps implementations, not the pipeline.** The interfaces in §3.3 are chosen
   so that "head geometry graft" is a second implementation behind the same seams.
5. **Everything measured is a named constant in one place**, not scattered magic numbers
   — the base avatar template will change and every constant in §1.5 is template-specific.

### 3.2 Package layout

```
face_fitting/
  run_face_fitting.py              # python face_fitting/run_face_fitting.py --user-id u_001
  face_runtime/
    context.py                     # FaceContext: user_id, views, run_dir, artifacts
    constants.py                   # ALL measured values from Part 1, per base template
    step_01_validate_capture.py    # per-view: face found, yaw in range, sharpness, occlusion
    step_02_landmarks.py           # MediaPipe 478 per view (OpenCV 3-pt fallback)
    step_03_estimate_pose.py       # per-view yaw/pitch/roll -> which UV regions it may fill
    step_04_project_views.py       # each view -> (UV layer, confidence weight map)
    step_05_composite.py           # weighted merge of N layers into one albedo
    step_06_skin_match.py          # reconcile head tone against body/arm/leg albedo
    step_07_derive_maps.py         # normal + roughness deltas; stock as fallback
    step_08_write_avatar.py        # delegates to an AvatarWriter (see 3.3)
  io/
    avt_container.py               # byte-faithful .avt read/write  [BUILT, PROVEN]
    glb_writer.py                  # Phase 2 stub
  reference/
    MV2_Jinho_01/
      anchors.json                 # eyes, mouth, from 1.5
      head_region_mask.png         # hand-authored; face oval, ear bands, scalp, neck
      uv_regions.json              # named UV rects from 2.2
```

`avt_container.py` already exists and is proven (§1.2). Everything else is new.

### 3.3 The interfaces that must not change in Phase 2

Three seams. Get these right and Phase 2 is additive.

```python
# --- what a capture gives us -------------------------------------------------
@dataclass
class View:
    image: np.ndarray                 # RGB
    yaw: float                        # degrees, 0 = frontal, + = user's left
    landmarks: dict[str, tuple[float, float]] | None
    quality: float                    # 0..1, from step_01

# --- SEAM 1: photos -> an identity artifact ---------------------------------
class FaceSource(Protocol):
    """Phase 1 returns a texture. Phase 2 returns texture + geometry.
    The pipeline only ever asks for a FaceResult."""
    def build(self, views: list[View]) -> FaceResult: ...

@dataclass
class FaceResult:
    albedo: np.ndarray                      # the composited head map
    normal: np.ndarray | None = None
    roughness: np.ndarray | None = None
    head_mesh: "HeadMesh | None" = None     # None in Phase 1; populated in Phase 2
    diagnostics: dict = field(default_factory=dict)

# --- SEAM 2: an identity artifact -> an avatar file -------------------------
class AvatarWriter(Protocol):
    def write(self, base: Path, result: FaceResult, out: Path) -> WriteReport: ...

class AvtTextureWriter:   # Phase 1 — patches the .avt ZIP entry
    ...
class GlbGraftWriter:     # Phase 2 — splices head_mesh into the exported GLB
    ...

# --- SEAM 3: where identity comes from --------------------------------------
class TextureOnlySource:    # Phase 1 — MediaPipe warp + multi-view composite
    ...
class VendorMeshSource:     # Phase 2 — Avatar SDK / TRELLIS 2 / etc. behind one adapter
    ...
```

Phase 2 adds `VendorMeshSource` and `GlbGraftWriter`. `run_face_fitting.py`, the context,
the validation and the artifact contract are untouched. That is the whole point of
spending design effort now.

### 3.4 The multi-view projection model

The core of Phase 1, and the part that makes it 360° rather than frontal.

Each view produces a **UV layer plus a confidence map**, and the composite is a
confidence-weighted sum. Confidence is the product of three terms:

```
w(u,v) = w_visibility(u,v, yaw) · w_grazing(u,v, yaw) · w_quality(view)
```

- **`w_visibility`** — is this surface point even seen from this yaw? Derived from the
  named UV regions in `uv_regions.json`: a 90° left profile contributes nothing to the
  right cheek band, whatever its pixels say.
- **`w_grazing`** — surfaces seen at a glancing angle are stretched and unreliable.
  Falls off with the angle between view direction and surface normal, approximated per
  UV region rather than per texel (we have no head normals in Phase 1).
- **`w_quality`** — the per-view score from `step_01`, so a blurry 3/4 shot loses to a
  sharp front one in the overlap.

Then:

```
albedo(u,v) = Σᵢ wᵢ(u,v) · layerᵢ(u,v) / Σᵢ wᵢ(u,v)        where Σw > ε
            = stock(u,v)                                    where Σw ≤ ε
```

Two rules that keep it from looking like a collage:

1. **Composite in Lab, and only transfer the mean per region.** High-frequency detail —
   pores, stubble, moles — *is* the identity signal and is exactly what a full histogram
   match destroys. Shift means, keep variance.
2. **Feather every region boundary** over ~5% of its width, and feather the *weights*,
   not the pixels. Weight feathering makes overlaps blend; pixel feathering makes them
   ghost.

Falling back to `stock(u,v)` where no view has data is what makes "ship with 1 photo
today, 3 photos next week, 5 later" work without a code change — coverage simply
improves.

### 3.5 Artifacts

Per the repo convention of a JSON record per step, written to
`output/<user_id>-face-<run>/`:

```
input.json                 views, yaw estimates, source paths
validation.json            per-view accept/reject + reason
landmarks.json             per-view landmark sets
coverage.json              fraction of informative UV covered, per region   <- the 360 metric
composite_albedo.png       the map we wrote
composite_weights.png      debug: which view won where
skin_match.json            Lab shifts applied to head and body maps
write_report.json          which .avt entries changed  (must be exactly the head maps)
output.json                run summary
```

`coverage.json` is the one to watch. It is the honest answer to "how 360 is this
avatar", and it is what the UI should use to decide whether to nudge the user for
another photo.

---

## Part 4 — Changes to the current architecture

### 4.1 Step 1 (`clo_avatar_generation/`)

Today Step 1 ends at `step_11_save_outputs.py`, which exports `<user_id>.avt`.

**Change:** `face_fitting` runs *after* Step 1 and consumes its output.

```
step_11_save_outputs.py  ->  output/<user_id>-<run>/<user_id>.avt
                                      |
                                      v
                        face_fitting/run_face_fitting.py
                                      |
                                      v
                        output/<user_id>-face-<run>/<user_id>.avt   <- Step 3 consumes this
```

Deliberately **not** a 12th step inside Step 1:

- a re-shot photo must not trigger a full avatar rebuild;
- measurement accuracy and face accuracy are different failure domains and should not
  share an exit code;
- Step 1 stays runnable with no photo at all.

Step 3's avatar path becomes "faced avatar if present, else base avatar" — a one-line
resolution change, and the only edit Phase 1 makes to existing code.

### 4.2 Plugin (`clo_workspace/`) — optional, not on the critical path

`POST /avatar/set-mesh-texture` wrapping `SetAvatarMeshTexture` (or
`SetAvatarTextureMap`, per §1.7), plus `GET /avatar/texture-maps` for slot discovery.

Two hard requirements if we build it:

- Use the **`PostMessage` / `WM_APP` dispatch pattern**, not the queue drain. There is an
  explicit comment at `RestPlugin_windows.cpp:188` that `SetFabricPBRMaterialBaseColor`
  and `SetBaseTextureMapImageGivenFilePath` crash from the drain context; an avatar
  texture call is the same family. Copy `FabricDispatcher` (`:386-425`).
- Mirror it in `mac/RestPlugin_macOS.cpp`. The contract's `parity_rule` exists for a
  reason.

Value is live preview ("try another photo" without a file round-trip), not correctness.
Phase 1 ships without it.

### 4.3 Step 3 (`clo_vto/native_vto/`) — Phase 2 hook only

No Phase 1 changes. Phase 2 adds `step_13_face_graft.py` after `step_12_texture_glb.py`,
following its exact pattern (load GLB via `pygltflib`, modify, embed, write, never
block). It runs **after simulation**, so the cloth solver never sees the new head and
collision, drape and the 10-seam system are untouched.

Phase 2 is blocked on the avatar mesh actually reaching the export — see
`simulation-bug-writeup-26_8_10.md`. Phase 1 is not, because it operates upstream.

### 4.4 Storage and reuse

The faced `.avt` is a **per-user durable asset**, same lifecycle as the avatar: generated
once, reused for every try-on. Face cost is per *user*, not per *try-on* — which is why
even an expensive Phase 2 vendor stays economically irrelevant.

Keep the source photos only as long as consent and the retention policy allow. Face
photographs are biometric data under GDPR Art. 9 and BIPA. Out of scope for this
document, but it must be settled before any customer uses this.

---

## Part 5 — Roadmap

| Phase | Deliverable | Depends on |
|---|---|---|
| **0** | Spikes 1 and 3 from §1.8 — open `base-1-FACETEST.avt` in CLO | nothing. Half a day |
| **1a** | Single frontal photo → patched `.avt`, recognizable at ±30° | Phase 0 |
| **1b** | Three views → 360° composite, `coverage.json`, skin-tone reconciliation | 1a |
| **1c** | 4096² maps, super-resolved face crop, ArcFace acceptance gate | 1b + spike 2 |
| **2** | Head geometry grafted into the GLB | avatar-in-export bug fixed |
| **3** | Hair | deliberately unscoped |

Phase 1a and 1b are the same code path at different N. That is the design working.

---

## Part 6 — Open questions

1. **Mirrored or full head UV?** (§2.3) Resolve first. It can invalidate the multi-view
   compositor.
2. **Embedded entry vs `clofiles.json` cache path?** (§1.8) Resolve first.
3. **Does CLO accept 4096²** in the head slot without downsampling?
4. **Capture flow alignment** — can the `for_measurements/` front+side capture and the
   face capture be one user flow? Their side photo is a 90° profile, not the 3/4 this
   plan wants, so this is a product decision, not just an engineering one.
5. **MediaPipe install.** Not currently in `.venv-win312`. Apache 2.0, CPU, commercially
   clean. Needed for the dense warp; the OpenCV 3-point fallback is prototype-grade only.
6. **One CLO bridge or two?** This repo uses a C++ REST plugin; `for_measurements/` uses
   CLO's Python API. Both reach the same CAPI. Worth a decision before both grow.

---

## Appendix — Measured constants (base template `MV2_Jinho_01`)

Every value here is template-specific. Re-measure if the base avatar changes; this is
what `face_runtime/constants.py` holds.

```python
AVT_PREFIX_BYTES      = 244210        # bytes before the first ZIP local header
AVT_MAGIC             = b' AVT        CLO '

HEAD_ALBEDO_ENTRY     = "MV2_Jinho_01_face.jpg"
HEAD_NORMAL_ENTRY     = "MV2_Jinho_01_face_normal.jpg"
HEAD_ROUGHNESS_ENTRY  = "MV2_Jinho_01_face_roughness.jpg"
HEAD_TEXTURE_SIZE     = 2048                      # target 4096, pending spike 2

ANCHORS_2048 = {                                  # px in the stock albedo
    "eye_l": (862.0, 643.0),
    "eye_r": (1166.0, 638.0),
    "mouth": (1024.0, 907.0),
}
INTEROCULAR_PX_2048   = 304.0

FACE_BBOX_UV          = (0.344, 0.181, 0.660, 0.497)   # Haar-detected
INFORMATIVE_UV        = (0.15, 0.10, 0.85, 0.60)       # from detail-energy analysis
MIRROR_SYMMETRY_MAD   = 5.78                           # /255 -- see 2.3, UNRESOLVED

BODY_ALBEDO_ENTRIES = [                                # for skin-tone reconciliation
    "MV2_Jinho_01_body_Covered_7422644.jpg",
    "MV2_Jinho_01_arm.jpg",
    "MV2_Jinho_01_leg.jpg",
]
```

---

*Related: `face-personalization-deep-dive-26_10_3.md` (full problem space, vendors,
licensing), `simulation-bug-writeup-26_8_10.md` (the Phase 2 blocker).*
