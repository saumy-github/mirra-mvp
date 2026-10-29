# Face + Hair Personalization — Scalable Architecture and Delivery Plan

*Written 2026-10-28. Supersedes the open-questions list in
`face-texture-implementation-plan-26_10_3.md`; that document's Part 1 measurements still
stand and were independently re-verified today.*

**What this document is for.** The 2026-10-03 pair of documents established that a face
*can* be written into the avatar. This one answers the next question: **how does a
personalized face and hair become a routine, automatic part of a try-on run** — so that
when a shopper hits "try this on", the avatar that loads is recognizably them, every
time, without anyone touching CLO.

**Audience.** Engineers building Steps 1/3 and the worker, plus whoever owns the
build-vs-buy decision in Part 6.

---

## 0. Status board

| Item | State |
|---|---|
| `.avt` container read/write, byte-faithful | **Built and proven** — `face_fitting/io/avt_container.py` |
| Phase 1a: frontal photo → faced `.avt` | **Built and working end to end** — `face_fitting/run_face_fitting.py` |
| Skin-tone reconciliation (avatar takes user's tone) | **Built** — default `--skin-match body` |
| Does CLO read the embedded entry or the cache path? | **RESOLVED — embedded entry** (§1.2) |
| Is the head UV mirrored or full? | **RESOLVED — FULL** (§1.3) |
| Does the avatar mesh reach the GLB export? | **RESOLVED — yes** (§1.4) |
| Does CLO accept a 4096² head map? | **Still unverified** — cheap to test now (§8) |
| Wiring into the live VTO job | **Not started** — Part 4 is the plan |
| Hair | **Not solvable by texture.** Part 5 |
| Head geometry (Phase 2) | **Not started.** Part 6 |

---

## Part 1 — What was settled on 2026-10-27/28

Everything here is measured on this machine against `clo_avatar_generation/input/base-1.avt`
with CLO 2026.1.336 and plugin v1.3.2. Measurements, not inferences.

### 1.1 The container facts reproduce

Prefix `244210`, 30 ZIP entries, Haar face box `(705, 370, 647, 647)`, and the Sobel
detail-energy curve all reproduce exactly against the 2026-10-03 numbers. Reading
`base-1.avt` and writing it back is **byte-identical at all 33,927,576 bytes** (same
SHA-256), so any difference in a patched file is only what we intended.

**Caveat for multi-template work:** the 244,210-byte prefix is *per file*, not a format
constant. `MV2.1_Luka.avt` is 256,138 and the library's `MV2.1_Jinho.avt` is 264,095.
The reader derives it (`eocd − cd_size − cd_offset`) and handles all three; the constant
in `constants.py` is documentation, not a parser input.

### 1.2 CLO reads the **embedded** ZIP entry — open question 1 closed

`clofiles.json` maps every texture to an absolute path on a former teammate's machine
(`C:/Users/Saumy/...`), which does not exist here. CLO nonetheless renders correctly, and
extracts its own copy to
`%LOCALAPPDATA%/CLO Virtual Fashion/CLO Standalone OnlineAuth/<session>/<counter>/`,
**byte-identical to the embedded entry**. The counter increments per load (observed 1000
→ 1026 → 1051), so each load re-extracts rather than reusing a cache keyed by name.

**Consequence:** patching the embedded JPEG takes effect reliably, on any machine, with
no need to rewrite `clofiles.json`. The feared "silent no-op on some machines" does not
occur. Confirmed end to end in §1.4.

### 1.3 The head UV is **FULL**, not mirrored — open question 3 closed, favourably

This was flagged as "the single biggest risk in this document". Resolved by measuring the
real mesh rather than eyeballing a probe: import a faced `.avt`, export GLB, and compare
UVs of mirror-paired vertices on the `face` material primitive (7,960 vertices,
u ∈ [0.009, 0.991], y ∈ [1.630, 1.890] on a 1.89 m body).

| Across 5,394 mirror-paired lateral head vertices | Value |
|---|---|
| `median \|u − u_pair\|` (≈0 ⇒ mirrored UV) | 0.2765 |
| `median \|u + u_pair − 1\|` (≈0 ⇒ full UV) | **0.0000** |

Left and right map to **opposite** texels; texture `u < 0.5` belongs to the `−x` side.
So the stock albedo's near-perfect symmetry (MAD 5.78/255) is symmetric *artwork* on a
full UV — explanation (a). **Asymmetric detail is representable, and the multi-view 360°
composite needs no UV re-layout.**

> **Method note, because this is easy to get wrong.** The `body` mesh shares one vertex
> buffer across its four material primitives (face / body2 / arm / leg) in a tiled UV
> atlas — face occupies u ∈ [0,1], the others sit in later tiles. Reading
> `geometry.vertices` directly returns the whole buffer with u spanning 0–4 and yields a
> confidently wrong answer. **Subset by each primitive's own triangles first.** A first
> attempt at this analysis returned "MIRRORED" for exactly this reason.

### 1.4 The avatar reaches the GLB export — Phase 2's feared blocker is clear

`simulation-bug-writeup-26_8_10.md` listed "avatar mesh not reaching the export" as the
Phase 2 blocker. For an **avatar-only** export it is not blocking today: a 39 MB GLB came
back containing `body` (4 material primitives), `Hair`, `eye_L/R`, `eyelash_L/R`, `tooth_`.

The exported face texture differs from the texture we wrote by **0.46–0.66 / 255** — pure
JPEG re-encode noise. That is end-to-end proof of the whole chain: *patch embedded JPEG →
CLO loads it → it lands on the avatar → it survives export*.

**Not yet verified:** that the avatar still reaches the export *after a garment
simulation*, which is the case Phase 2 actually needs. Test this before committing to
Part 6.

### 1.5 Measured performance

| Stage | Time |
|---|---|
| Read photo (1200×1600) | 0.02 s |
| MediaPipe landmark detection | 0.98 s |
| Piecewise-affine warp + composite (2048²) | 1.11 s |
| Encode + write `.avt` | 0.20 s |
| **Face fitting subtotal** | **≈ 2.3 s CPU** |
| CLO new project | 4.1 s |
| CLO import avatar `.avt` (31.5 MB) | 6.5 s |
| CLO export GLB (37.2 MB) | 8.8 s |

**Photo → faced avatar in CLO ≈ 11 s; ≈ 21 s including a GLB for the web viewer.**
Face fitting is ~10% of that; CLO I/O dominates. This matters for Part 3: the face step
is cheap, so caching strategy should be driven by CLO cost, not by fitting cost.

### 1.6 Quality, honestly

On a 1200×1600 photo (interocular 340 px, 1.18× upscale — effectively native):
identity transfers clearly — eyebrows, lashes, a mole, moustache, lip texture.
Skin-tone reconciliation closes the face/head seam from **L = 29.3 to L = −0.2**.

On a 622×350 photo (interocular 77.7 px, **4.31× upscale**) the result is recognizable
but soft. **Source resolution is the dominant quality variable** and it is a capture-UX
problem, not an algorithm problem. See §7.1.

But in a full-body render the avatar still does not read as the user, for two reasons
that texture cannot fix: **the skull is the template's**, and **the hair is the
template's**. That is the honest ceiling of Phase 1 and the reason Parts 5 and 6 exist.

---

## Part 2 — Architectural principle: personalization belongs *after* CLO

The single most useful conclusion from the investigation.

**CLO is a cloth simulator. It needs a body, not a face and not hair.** Drape,
collision, seams and fit accuracy depend on the torso and limbs. What the shopper
actually looks at is a **GLB rendered by three.js** in
`website/frontend/src/features/profile/components/avatar-glb-viewer.tsx`
(`@react-three/fiber` 9.6, `three` 0.185).

```
  measurements ──► CLO Step 1 ──► body .avt ──┐
                                              ├─► CLO Step 3 (VTO) ──► simulated GLB
  garment patterns ──► CLO Step 2 ────────────┘                           │
                                                                          ▼
                                             ┌─────────── personalization layer ────────────┐
                                             │  face texture (Phase 1)  head+hair (Phase 2) │
                                             └──────────────────────────────────────────────┘
                                                                          │
                                                                          ▼
                                                            three.js viewer (what users see)
```

Three consequences worth internalizing:

1. **Hair never has to be a CLO problem.** We spent a day discovering CLO's hair
   constraints (Part 5). Downstream of the export, none of them apply.
2. **Face/hair work cannot regress fit accuracy**, because it runs after simulation.
   Fit correctness and likeness become independent failure domains — which is also why
   they must not share an exit code.
3. **Two injection points, deliberately kept separate**, because they have different
   costs and different blast radii:

| | Point A — texture into `.avt` | Point B — geometry into exported GLB |
|---|---|---|
| When | Before CLO (Step 1 output) | After simulation (Step 3, new step 13) |
| Changes geometry | No | **Yes** |
| Fixes hair | No | **Yes** |
| Status | **Built** | Part 6 |
| Risk to simulation | None (texture only) | None (post-sim) |

**A is not thrown away when B lands.** A remains the cheap path, the fallback when B's
vendor is down, and the thing that makes CLO's own preview look right.

---

## Part 3 — Data model: the faced avatar is a durable per-user asset

### 3.1 The economics that drive the design

**Face cost is per user, not per try-on.** A shopper generates their avatar once and
tries on dozens of garments. Even an expensive Phase 2 vendor call amortizes to
irrelevance. This single fact means:

- Never run face fitting inside the try-on request path.
- Always resolve a *stored* faced asset at try-on time.
- Re-shooting a photo must not require regenerating the avatar (different failure domain,
  and a 4.1 s + 6.5 s CLO round trip we do not need to pay again).

### 3.2 Storage, reusing what exists

The live avatar path already stores versioned artifacts via
`worker/live_upload.py :: save_avatar_version()` into
`<dev_upload|live_upload>/avatars/<user_id>/<version>/` (root chosen by `APP_ENV`), with
`zprj_path`, `avt_path`, `glb_path` and `step_results`. **Face artifacts join that
folder rather than inventing a parallel store.**

```
<root>/avatars/<user_id>/<version>/
  avatar.avt              body, measurement-morphed        (exists today)
  avatar.glb              body GLB                          (exists today)
  faced.avt               + face texture        [Phase 1]   ← new
  faced.glb              + head/hair geometry  [Phase 2]   ← new
  face/
    source_photo.jpg      retained only per §9              ← new
    composite_albedo.png  debug                             ← new
    face_manifest.json    provenance + quality metrics      ← new
```

`face_manifest.json` is the contract between the face stage and everything downstream:

```json
{
  "schema": 1,
  "user_id": "u_002",
  "base_template": "MV2_Jinho_01",
  "source": "texture_v1",
  "landmark_source": "mediapipe",
  "warp_mode": "piecewise_affine",
  "interocular_px": 340.2,
  "upscale_factor": 1.18,
  "coverage_fraction": 0.064,
  "skin_delta_lab": [-30.04, -2.12, -3.83],
  "seam_residual_lab": [-0.2, 0.5, -0.2],
  "quality_score": 0.81,
  "entries_changed": ["MV2_Jinho_01_face.jpg", "..."],
  "created_at": "2026-10-28T06:12:00Z"
}
```

`quality_score` is what the UI uses to decide whether to nudge for a better photo, and
what the pipeline uses to decide whether to fall back to the stock head. **Store the
inputs to that judgement, not just the verdict** — thresholds will be retuned.

### 3.3 Resolution rule

Every consumer uses one rule, implemented once:

> **faced.glb → faced.avt → avatar.avt → base template**, first that exists.

Today VTO resolves its avatar through `clo_vto/native_vto/context.py ::
_discover_default_native_avatar()`, which globs `clo_vto/output/*.avt` and ultimately
falls back to `clo_avatar_generation/input/base-1.avt`. **That function is development
scaffolding and must not be the live path** — it is user-agnostic and will happily hand a
shopper someone else's avatar. Part 4 replaces it.

---

## Part 4 — Wiring it into the live VTO run

This is the part that answers "when we run VTO, the faced avatar is loaded".

### 4.1 Where the live flow runs today

```
backend  src/avatars/engine.py  ──enqueue──►  worker.tasks.run_avatar_job
                                                 │ Step1Context(base_avatar_path_input=_resolve_default_base_avatar())
                                                 │ run_avatar_pipeline()  → ctx.extracted_avatar_path, ctx.avatar_glb_path
                                                 └► save_avatar_version(...)

backend  src/tryon/engine.py    ──enqueue──►  worker.tasks.run_tryon_render
                                                 │ clo_vto pipeline
                                                 │   step_03_import_avatar → client.import_avatar_avt(ctx.avatar_path)
                                                 │   ... step_10_simulate ... export
                                                 └► step_12_texture_glb → simulation_textured.glb
```

### 4.2 The changes, smallest first

**(a) A separate face job — not a 12th step in Step 1.**
New `worker.tasks.run_face_job(user_id, photo_ref)`:
1. load the user's current `avatar.avt` from the version folder,
2. call `face_fitting` (≈2.3 s, no CLO needed),
3. write `faced.avt` + `face_manifest.json` into the **same** version folder,
4. update the avatar profile doc with face status and `quality_score`.

Deliberately its own job because a re-shot photo must not trigger a full avatar rebuild,
and because measurement accuracy and face accuracy are different failure domains.
**It never touches CLO**, so it cannot contend for the single-threaded plugin.

**(b) VTO resolves the user's avatar explicitly.**
`create_context()` already accepts `avatar_path` and `user_id`. The worker passes the
resolved path from §3.3 instead of letting `_discover_default_native_avatar()` guess.
This is a small change with an outsized correctness payoff — it is also the fix for
"shopper sees someone else's avatar", which the current glob makes possible.

**(c) `step_13_face_graft.py`, after `step_12_texture_glb.py`** — Phase 2 only.
Follows step 12's established pattern exactly: read the GLB with `pygltflib`, modify,
embed self-contained, write, and **return True on every failure path so a cosmetic step
never blocks a try-on**. It runs after simulation, so the cloth solver, collision and the
10-seam system never see it.

**(d) Serving.** The viewer requests the try-on render as it does today; the only change
is which GLB the worker stored. No frontend change is required for Phase 1.

### 4.3 Degradation ladder — non-negotiable

A face problem must never cost a shopper their try-on. In priority order, each rung
logs and silently falls to the next:

```
faced.glb (head+hair)  →  faced.avt (texture)  →  avatar.avt (stock head)  →  base template
```

`step_12_texture_glb.py` already encodes this philosophy ("every failure mode returns
True so the pipeline is never blocked by this cosmetic step"). Face work inherits it
verbatim.

---

## Part 5 — Hair: why it is a separate problem

### 5.1 What was established

- **CLO ships 10 male skin variants** (Thomas, Henry, Nate, Dario, Martin, Darnell,
  Jinho, Leo, Luka, Liam) driven by `Preset/Avatar/AvatarSwitch.json`. That system swaps
  `face/body/arm/leg/eye/eyelash/tooth` textures. **Hair is not in the list.**
  The mechanism that looks like it should solve this cannot.
- **Hair colour is already a match and recolouring is wasted effort.** Stock hair
  texture mean L = 6.5 (essentially black); the test subject's hair strands measure
  BGR ≈ `[35, 36, 37]`, also near-black. **The entire gap is volume and curl** — geometry.
- **Hair is per-template geometry baked into `first.dan`.** Jinho and Luka even use
  different shader conventions (`hair_main`/`hair_cap` vs `hair_diffuse`/`hair_alpha2`/
  `hair_spec`).
- **CLO has a hair accessory system, and the local library is empty.**
  `CLO Assets/Avatar/Male/Accessory/Hair/` exists and contains nothing; assets come from
  CLO's online Library. *Still unverified: what that online library actually offers.*

Measured hair volume, from the GLB meshes:

| Template | Hair verts | Rise above scalp | Bounding box W×H×D (m) |
|---|---|---|---|
| Jinho | 424,278 | 1.8 cm | 0.167 × 0.221 × 0.228 |
| Luka | 202,480 | **3.1 cm** | 0.203 × 0.227 × 0.250 |

Luka carries ~70% more rise and a wider silhouette.

### 5.2 Template-picking is a stopgap, and should be labelled as one

Choosing the nearest of two (or ten) templates is **not** a real-user solution: it does
not scale across hair types, it is a step change rather than a continuum, and the local
library is far too small. It is worth doing only as a v1 holding position while Part 6
lands, and only if it costs days rather than weeks.

### 5.3 The real options

| | Approach | Verdict |
|---|---|---|
| **A** | **Vendor head + hair reconstruction** from the selfie, output as GLB | **Primary.** This is where likeness actually comes from |
| **B** | **Parametric hair library + classifier** — classify length/curl/volume/hairline/colour, select a groomed asset, tint, fit to head | **Recommended for hair specifically** |
| **C** | Strand-based reconstruction / Gaussian-splat hair | **Do not ship.** Non-commercial licences, heavy GPU, and splats are not meshes — they cannot sit in a GLB beside simulated cloth |

**Recommendation: A for the head, B for the hair.** This is how the mature avatar
products are themselves built, and it is driven by one specific risk:

> **Photogrammetric hair reconstruction degrades badly on curly and coily hair.** These
> models are overwhelmingly trained on straight-haired Western datasets and tend to
> return a solid helmet-shaped blob on textured hair.
>
> **Mirra's user base will skew Indian, with substantial wavy-to-curly representation —
> precisely this failure mode.** A curated library sidesteps it: an artist groomed each
> style, the quality floor is controlled, and failure is graceful ("nearest of 30")
> rather than uncanny. Make hair-type coverage a **hard scoring criterion**, not a
> footnote.

A library also keeps hair in-house, which materially reduces the §9 privacy surface.

---

## Part 6 — Head geometry: build-vs-buy, and the bake-off that decides it

### 6.1 Swappable adapter is mandatory, not stylistic

Per `face-personalization-deep-dive-26_10_3.md` §4.2, **two of the eight best-known
vendors in this space died within nine months** — Ready Player Me (shut down
2026-01-31) and Union Avatars (offline July 2026, with no announcement). Assume whoever
is chosen will disappear.

The seams for this already exist in `face_fitting` and were built for exactly this:

```python
class FaceSource(Protocol):          # photos -> identity artifact
    def build(self, views: list[View]) -> FaceResult: ...

class AvatarWriter(Protocol):        # identity artifact -> avatar file
    def write(self, base: Path, result: FaceResult, out: Path) -> WriteReport: ...
```

Phase 2 adds a `VendorMeshSource` and a `GlbGraftWriter`. The runner, the context, the
validation and the artifact contract are untouched. **A dead vendor becomes a config
change.** Keep a self-hostable open model behind the same interface as the escape hatch.

### 6.2 Candidate shortlist

From the deep dive's 2026-10-03 survey — **re-verify pricing and liveness before
committing; this market moved twice in nine months.**

| Candidate | Why it is on the list | Watch for |
|---|---|---|
| Avatar SDK / MetaPerson | Best $/avatar (~$800/mo incl. 6,000 ≈ $0.13 each); selfie → rigged head/body GLB | REST API may be Enterprise-tier only |
| Avaturn | API + SDK on Pro | More stylized — a likeness, not a twin |
| Didimo | ~60 s per twin | Published pricing unusable; get a quote |
| TRELLIS 2 (self-host) | **MIT, no usage restrictions**; ~$0.01–0.02/head at volume | ~16 GB VRAM; general-purpose, not face-tuned; idle cost kills it at low volume |
| FLAME 2023 Open | **The only commercially usable FLAME** (CC-BY-4.0) | Gives topology + shape basis; you still build the fitter |

**Legal tripwire:** FLAME 2017/2019/2020, SMPL, SMPL-X and STAR are Max Planck
**non-commercial** and cannot ship. Verified today that `models/star_1_1` and `libs/star`
are **absent from this checkout** (the `.gitmodules` entry is stale, nothing on disk), so
the risk the deep dive raised is currently clear. Confirm nothing reintroduces them.

### 6.3 The bake-off — 1–2 weeks before committing 5–7

1. Collect **15–20 real photos** spanning straight / wavy / curly hair, skin tones,
   genders, glasses, facial hair. Deliberately include the hard cases.
2. Run through **3 vendors + a library-based mock**.
3. Score: likeness, **hair plausibility broken out by hair type**, failure rate, cost,
   licence, latency.
4. Build every candidate behind the §6.1 adapter from day one.

Output is a decision memo, not a prototype. This converts a 5–7 week bet into an
informed one.

---

## Part 7 — Capture UX, the cheapest quality lever available

### 7.1 Resolution is the dominant variable

4.31× upscale produced a soft face; 1.18× produced a sharp one. **No algorithm recovers
detail that was never captured.** The capture flow should:

- require a face of **≥ 800 px** (reject and re-prompt below that),
- reject blur, heavy backlight, sunglasses and extreme yaw **at capture time**, when
  re-shooting costs the user five seconds,
- surface `quality_score` so the UI can ask for a better photo before the avatar is built.

### 7.2 Align with the existing body-measurement capture

The `for_measurements/` workstream already collects **front + side** photos. Face work
wants **front + two 3/4 views** for the 360° composite (Phase 1b). The side photo is a
90° profile — usable for the ear and skull band, not the cheek.

**Settle this as one capture flow, once.** Asking a shopper to photograph themselves
twice for two different subsystems is a conversion problem, not an engineering
preference. This is a product decision and it blocks nothing technical today, but it gets
expensive to change after launch.

---

## Part 8 — Delivery plan

| Phase | Deliverable | Effort | Depends on |
|---|---|---|---|
| **Now** | 4096² spike — does CLO downsample the head slot? Import/export loop is already wired, so this is minutes | ~1 h | nothing |
| **Now** | Verify the avatar survives export **after a garment simulation** (§1.4) | ~1 h | nothing |
| **1** | `run_face_job` + storage + manifest (§4.2a) | 3–4 d | nothing |
| **2** | VTO resolves the user's faced avatar; retire `_discover_default_native_avatar()` from the live path (§4.2b) | 1–2 d | Phase 1 |
| **3** | Capture UX: resolution gate, quality score, reject-and-reprompt (§7.1) | 3–5 d | Phase 1 |
| **4** | Multi-template support — `constants.py` becomes per-template profiles | ~1 d | only if template-picking ships |
| **5** | Phase 1b: 3-view 360° composite, `coverage.json` | 1–2 wk | Phase 1 |
| **6** | **Vendor bake-off + decision memo** (§6.3) | 1–2 wk | photo set |
| **7** | Phase 2: `step_13_face_graft.py`, head + hair into the exported GLB | 5–7 wk | Phase 6 |

**Phases 1–3 are the ones that turn today's working script into a product feature.** They
need no vendor, no budget and no new research, and they are worth doing regardless of how
Part 6 resolves.

Run Phase 6 **in parallel** with 1–3; it is procurement-shaped, not code-shaped.

---

## Part 9 — Privacy and legal, to settle before real users

Face photographs are **biometric data**.

- **India's DPDP Act 2023 applies directly** — Mirra and its users are in India. Explicit
  consent, purpose limitation, a retention limit, and a working deletion path are
  required, not optional.
- **Sending photos to a third-party reconstruction API is a cross-border transfer.** It
  must appear in the privacy policy and in a DPA with the vendor. This is a real argument
  for keeping hair (Part 5B) in-house, and a point to weigh in the Part 6 bake-off.
- **GDPR Art. 9 and BIPA** become live the moment there are EU or Illinois users.
- **Retain source photos only as long as consent allows.** The derived texture is not
  obviously less sensitive than the photo; treat the whole `face/` folder as biometric.

Cheaper to design in now than to retrofit. It should be settled before Phase 1 ships, not
before Phase 7.

---

## Part 10 — Open questions

1. **What hairstyles does CLO's *online* Library actually offer?** Decides whether
   template-picking is a viable stopgap at all. A 30-second look in the CLO GUI
   (Library → Avatar → Male → Accessory → Hair).
2. **Does CLO accept a 4096² head albedo without downsampling?** Doubles face detail.
   Now cheap to test.
3. **Does the avatar survive export after a garment simulation?** Gates Phase 7.
4. **One capture flow or two?** (§7.2) Product decision.
5. **Vendor choice** — output of §6.3.
6. **Eye colour.** Eyes are separate meshes (`eye_L`, `eye_R`) with their own texture;
   the user's eye colour currently never transfers. Cheap, isolated, and a real
   identity cue. Unscoped so far.

---

## Appendix — What exists in `face_fitting/` today

```
face_fitting/
  run_face_fitting.py       photo -> faced .avt            [working]
  calibrate_reference.py    derives targets from the stock albedo with the
                            SAME detector used on photos   [working]
  make_uv_probe.py          Phase 0 UV diagnostic          [working, superseded by §1.3]
  fetch_model.py            MediaPipe bundle (3.7 MB, gitignored)
  io/avt_container.py       byte-faithful .avt read/write  [proven byte-identical]
  face_runtime/
    constants.py            measured, per-template
    landmarks.py            MediaPipe Tasks API + OpenCV fallback
    texture_fit.py          piecewise-affine warp, feathered blend, Lab tone transfer
  reference/MV2_Jinho_01/   anchors.json + dense_landmarks.npy
```

Two design notes worth carrying forward:

- **Anchors are derived, not transcribed.** The 2026-10-03 constants are *pupil centres*
  (interocular 304 px); MediaPipe's indices 33/263 are *outer eye corners* (400.7 px).
  Registering against mismatched conventions left the mouth 87 px off. Measuring the
  stock albedo with the same detector drops it to 7.9 px and removes a whole class of
  bug. Re-run `calibrate_reference.py` whenever the base template changes.
- **Tone reconciliation runs toward the user, not away.** The first implementation
  shifted the user's face by L = +29.3 to match the pale template — seam-correct,
  product-wrong, and it bleached darker-skinned users. The default is now
  `--skin-match body`: the face keeps its colour and the head/body/arms/legs move to meet
  it. Residual seam L = −0.2.

---

*Related: `face-texture-implementation-plan-26_10_3.md` (Part 1 measurements remain
valid), `face-personalization-deep-dive-26_10_3.md` (vendor landscape, licensing),
`simulation-bug-writeup-26_8_10.md` (Phase 7 blocker — re-test per §1.4).*
