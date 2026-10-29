# CLO SDK v2026.1.336 — Deep Dive, Incident Register and Opportunity Map

Written 2026-10-29. **Audience: Claude and other agents working on this repo.**
Not written for a human reader skimming for a decision — written so that an agent
asking *"does CLO already support X?"* gets a correct answer in one grep instead of
re-deriving it from headers.

**Companion file:** [`03-clo-sdk-function-inventory-26_10_29.md`](03-clo-sdk-function-inventory-26_10_29.md)
— the complete, generated list of all **1,137 declarations** with signatures, doc
comments, params, returns, `header:line` refs and capability tags. That file is the
raw surface. This file is the judgment: what each family is for, what we already use,
what has previously crashed CLO **and exactly why**, and what is worth building on.

---

## Part 0 — Read this first

### 0.1 The one number that matters

| | Count |
|---|---|
| SDK declarations (incl. overloads) | **1,137** |
| Distinct SDK functions our plugin calls | **34** |
| Share of the surface never called by Mirra | **~97%** |

We have been building against roughly 3% of CLO's API. Several things we have
discussed building by hand already exist. Three examples found while writing this,
all unused: a **stress/strain map** (a per-vertex tight/loose readout — see 4.5), a
**complete animation recording system** (4.6), and **pattern-to-avatar-measure line
pinning** (4.3).

### 0.2 How to answer "does CLO support X?"

1. Grep the inventory file for a capability tag: `[fit-map]`, `[animation]`,
   `[grading]`, `[elastic]`, `[trim]`, `[avatar]`, `[measure]`, `[simulate]`,
   `[fabric]`, `[pattern]`, `[topstitch]`, `[export]`, `[import]`, `[render]`,
   `[graphic]`, `[gui]`, `[rest]`, `[project]`, `[techpack]`.
2. Read the `header:line` to see the real signature and the full comment.
3. **Then check Part 3 of this file before calling it.** Several functions crash or
   hang CLO in ways the signature does not hint at.
4. If it is not in the inventory, it is not in the SDK. Say so plainly rather than
   assuming a workaround exists.

### 0.3 The rule this document exists to prevent breaking

A past incident that ruled out *one function* has repeatedly been read later as ruling
out *a whole family*. The clearest case: `EXPORT_API` was excluded wholesale in v1.1.1
after `ExportAVT` raised SEH exceptions. `ExportAVT` works today behind an SEH guard,
and `ExportGLB` and `ExportZPrj` are load-bearing in the live pipeline. **An incident
is a fact about one call under one condition, not a verdict on a namespace.** Part 3
records the condition for each one so the scope stays visible.

---

## Part 1 — The seven interfaces

All accessed through the macros our plugin already uses. Nothing here is optional
reading: the threading constraint in 1.2 is the single most common source of crashes.

| Header | Accessor | Decls | Wired | What lives here |
|---|---|---|---|---|
| `UtilityAPIInterface.h` | `UTILITY_API` | 407 | 6 | Scene/project, avatar control, simulation settings, trims, buttons, zippers, topstitch, rendering, grading, GUI widgets. The grab-bag. |
| `FabricAPIInterface.h` | `FABRIC_API` | 284 | 10 | Fabric objects — almost entirely *appearance*. Physical properties come from `.jfab` files (4.4). |
| `PatternAPIInterface.h` | `PATTERN_API` | 231 | 21 | Pattern pieces, outline lines, seams, arrangement, elastic, pins, avatar-measure attachment. |
| `ExportAPIInterface.h` | `EXPORT_API` | 123 | 9 | Every export: meshes, images, video, tech packs, BOM/POM. Historically the crash-prone family (3.1). |
| `ImportAPIInterface.h` | `IMPORT_API` | 44 | 5 | Every import: avatars, patterns, poses, measurements, meshes. |
| `GuiAPIInterface.h` | `GUI_API` | 39 | 0 | Native dialogs, tool windows, dock panels, widgets. Entirely unused. |
| `RestAPIInterface.h` | `REST_API` | 9 | 0 | CLO making **outbound** HTTP calls. Not our inbound server. Entirely unused (4.10). |

### 1.1 These are interface classes with dummy default bodies

Every declaration is `virtual` with a default body returning a dummy
(`{ return ""; }`, `{ return false; }`, `{}`). The real implementation is in CLO's DLL.

**Consequence worth internalizing:** if CLO's DLL does not override a given function
for our build, calling it returns the dummy and *does nothing silently*. A `false`
return can mean "failed" or "not implemented here". There is no way to tell them apart
from the signature. So when wiring anything new, verify the observable side effect in
CLO, never just the return value.

### 1.2 The hard constraint: all SDK calls must run on CLO's main thread

Our REST server runs on its own thread. It can never call a CLO API directly — it hands
work to the main thread, which drains a queue on a 200 ms `SetTimer` tick.

Every endpoint is therefore one of three types. The full treatment is in
[`.agent/saumy/after-1-jun/clo-api-call-types.md`](../saumy/after-1-jun/clo-api-call-types.md)
and should be read before adding an endpoint. In brief:

| | Type 1 Async/Queued | Type 2 Sync-Read | Type 3 Direct |
|---|---|---|---|
| Used for | mutations | reads needing an answer | plugin-internal state |
| Touches SDK | yes | yes | **no** |
| Queue | yes, `isSync=false` | yes, `isSync=true` + promise | not used |
| HTTP blocks | no | yes, 3 s cap | no |
| Result | poll `/status` | same response via `std::future` | same response |

Type 2 wraps **each individual** SDK call in its own `try/catch` so one bad call cannot
stop the promise being fulfilled and hang the HTTP caller for the full 3 s. Preserve
that pattern.

### 1.3 Concurrency is 1, deliberately

One CLO instance, one queue, one main thread. Never run a second worker against the
same CLO. This is a standing repo rule, and it is why expensive personalization work
belongs **outside** CLO (see `avatar-personalization-split-decision-26_10_28.md`).

---

## Part 2 — What Mirra uses today

All 34 wired calls, by pipeline role.

### Step 1 — Avatar generation
| Call | Interface | Role |
|---|---|---|
| `ImportAvatar` | IMPORT | Load a `.avt`. **`.avt` only** — see 4.1 |
| `ImportAvatarMeasurement` | IMPORT | Apply a measurement CSV against an `.avt` template. The core of Step 1 |
| `ImportMeasurement` | IMPORT | Measurement import variant |
| `SetAvatarProperties` / `GetAvatarProperties` | UTILITY | Property-based sizing path. **`Get` crashes on an absent index — 3.3** |
| `ExportAVT` | EXPORT | Write the sized `.avt`. Behind an SEH guard — 3.1 |
| `NewProject` | UTILITY | Reset. **Clears garments only; avatars survive — 3.6** |
| `DeleteAvatar` | UTILITY | **Hangs on an absent index. Dead code — 3.4** |
| `GetAvatarCount` / `GetAvatarNameList` / `GetAvatarGenderList` | EXPORT | Present in source, runtime-gated — 3.2 |

### Step 2/3 — Patterns, fabric, simulation, export
| Call | Interface | Role |
|---|---|---|
| `ImportDXF`, `ImportOBJ` | IMPORT | Pattern and mesh import |
| `GetPatternCount`, `GetPatternInformation`, `GetPatternInputInformation` | PATTERN | Pattern introspection |
| `GetBoundingBoxOfPattern`, `GetPatternPieceArea`, `GetLineLength` | PATTERN | Geometry probes for seam mapping |
| `GetArrangementList`, `GetArrangementOfPattern` | PATTERN | Arrangement slot discovery |
| `SetArrangement`, `SetArrangementPosition`, `SetArrangementOrientation` | PATTERN | Place patterns on the avatar |
| `AddSeamlinePairGroup` | PATTERN | Create seams |
| `SetPatternPieceFabricIndex`, `GetFabricIndexForPattern` | PATTERN/FABRIC | Fabric assignment |
| `SetFabricPBRMaterialBaseColor`, `SetBaseTextureMapImageGivenFilePath` | FABRIC | Colour and texture |
| `Simulate` | UTILITY | Run the solver. **No settings are configured first — 4.7** |
| `ExportGLB` | EXPORT | The delivered mesh. **Not `ExportGLTF` — 3.5** |
| `ExportGLTF` | EXPORT | Still referenced; superseded by `ExportGLB` |
| `ExportZPrj` | EXPORT | Project save; also how the `.avt` is recovered |
| `DisplayMessageBox` | UTILITY | Debug only |

### 2.1 What this list tells us

- **Zero** simulation settings are configured. We call `Simulate` on defaults (4.7).
- **Zero** fabric *physical* properties are set. We set colour and texture only (4.4).
- **Zero** reads of fit/stress/strain, garment measurements, POM or BOM (4.5).
- **Zero** use of grading, i.e. no native multi-size support (4.8).
- **Zero** trims, buttons, zippers, elastic or topstitch — so no jeans fly, no
  waistband, no plackets (4.9).
- **Zero** animation, so nothing to drive interactive or scrubbed cloth motion (4.6).

Each of those is a gap we have discussed filling by hand. Each has native support.

---

## Part 3 — Incident register

**This is the most important part of this document.** Every known crash, hang or
wrong-output incident, with the root cause, the *exact condition*, current status, and
explicitly what it does and does not rule out.

Sources: `clo_workspace/versions/v_1.1.0 … v_1.3.2.json`, the referenced `.agent`
write-ups, and the current plugin source.

### 3.1 `EXPORT_API` raised SEH exceptions — MITIGATED, not forbidden

- **Condition:** `ExportAVT` raised a Windows SEH (hardware) exception, killing the
  thread that called it. Also hit via the `/avatars/state` probe.
- **Root cause:** SEH is not a C++ exception. Under `/EHs`, `catch (...)` does **not**
  catch it — recorded explicitly in v1.2.0. So the plugin's existing handlers were
  blind to it, and a faulting read left a Type 2 promise unfulfilled for the full 3 s
  timeout.
- **What we did:** v1.1.1 stubbed the endpoints and advertised
  `has_avatar_avt_export = false`, routing `.avt` recovery through `.zprj` extraction
  instead. v1.2.0 deferred the real fix. It then landed: the Windows plugin now has
  `__try`/`__except` wrappers plus a crash-dump writer, and `ExportAVT` is called
  through `ExportAVT_SEHSafe` (`RestPlugin_windows.cpp:612-624`).
- **Status:** **Usable behind the SEH guard.** `ExportGLB` and `ExportZPrj` are
  load-bearing in the live pipeline today.
- **Do not over-read:** this does **not** mean `EXPORT_API` is off-limits. It means
  **wrap new `EXPORT_API` calls in the existing SEH guard.** The guard is the
  deliverable from this incident — use it rather than avoiding the namespace.
- **Constraint on the guard:** MSVC forbids mixing `__try`/`__except` with local C++
  objects needing unwinding, so the guarded function body must hold no such locals.
  Follow the existing shape at `RestPlugin_windows.cpp:527-606`.

### 3.2 No safe way to count avatars — OPEN

- **Condition:** asking CLO how many avatars are in the scene.
- **Every known route is ruled out, each for its own reason:**
  - `GetAvatarCount`, `GetAvatarNameList` — `EXPORT_API`, SEH-crash-prone (3.1)
  - `GetAvatarProperties(index)` — crashes outright on an absent index (3.3)
  - `IsShowAvatar(index)` — cannot distinguish *hidden* from *absent*; its default
    body returns `false` for both (and see 1.1 — `false` may also mean "not
    implemented")
  - counting our own imports — wrong: the pipeline imports twice per run but the scene
    often ends with one avatar, because a patched import *replaces* rather than adds
- **Status:** worked around by `g_avatarsLoaded`, a plugin-side atomic counter.
- **Known limitation:** it only sees avatars imported *through the plugin*. An avatar
  loaded by hand in the CLO GUI is invisible to it.
- **If you need to solve this properly:** the SEH guard from 3.1 did not exist when
  `GetAvatarCount` was excluded. Re-testing `GetAvatarCount` *behind the guard* is the
  obvious unexplored move, and it is cheap. Do it on a scratch scene, not a pipeline run.

### 3.3 `GetAvatarProperties(index)` crashes on an absent index — OPEN

- **Condition:** calling it with an index where no avatar exists.
- **Evidence:** confirmed live 2026-08-22. A bare `/clear-avatars` against an empty
  scene logged `probe GetAvatarProperties(0) begin` with no matching end; the CLO
  process was gone.
- **Why it surprised us:** it lives in `UtilityAPIInterface`, not the
  SEH-crash-prone `EXPORT_API` family. Family membership is not a safety signal.
- **Status:** do not call it to *discover* what exists. It is safe only when you
  already know an avatar is at that index.
- **General rule this generalizes to:** **no per-index avatar query is safe against an
  index you have not independently confirmed.** Treat index bounds as a precondition
  you must establish some other way, not something the API will validate for you.

### 3.4 `DeleteAvatar()` hangs the main thread on an absent index — OPEN

- **Condition:** the index list contains an index with no avatar at it.
- **Evidence:** confirmed live 2026-08-22. Logged `BEGIN clear-avatars tracked=2` then
  `DeleteAvatar begin count=2` with no matching end, against a scene holding one
  avatar. Recovery required killing and relaunching CLO.
- **Status:** `/clear-avatars` and `g_avatarsLoaded` remain in the plugin as **dead
  code**. Step 7 no longer invokes them.
- **Do not re-enable** without first solving 3.2. The route is harmless while unused;
  it is a CLO-killer the moment it is called with a stale count.
- **Note the asymmetry:** 3.3 crashes (fast, obvious, process gone), 3.4 hangs (slow,
  looks like a long simulation). A hang is the worse failure because it is easy to
  misread as progress.

### 3.5 `ExportGLTF` produced invalid `.glb` — FIXED

- **Condition:** calling `ExportGLTF` and expecting binary GLB.
- **Root cause:** it produced JSON-embedded content mislabeled with a `.glb`
  extension. CLO's own UI (`File > Export > glTF 2.0 (GLB)`) produced a valid binary
  file from the same scene — which is how the discrepancy was found.
- **Fix:** switched to `ExportGLB`. Verified with `pygltflib` (correct `glTF` binary
  magic, loads cleanly).
- **Lesson worth keeping:** when SDK output looks wrong, **reproduce the operation
  through CLO's GUI and compare bytes.** That single technique found this bug. The GUI
  is the reference implementation.
- **Residual:** verified on Windows against an avatar-only scene. `ExportGLTF` is still
  referenced in source. Mac was never ported and still calls the old path.

### 3.6 `NewProject()` does not clear avatars — BY DESIGN, caused a data leak

- **Condition:** assuming `NewProject()` resets the scene.
- **Fact:** the SDK header states it plainly — `UtilityAPIInterface.h:448-451` in
  v2026.1.336: *"Clear the current garment and begin a new garment"*. Garments only.
  Avatars survive.
- **Aside, and a live demonstration of 3.8:** `v_1.3.2.json` cites this as
  `UtilityAPIInterface.h:419-421`, which was correct for the `2026.0.356` SDK and is now
  the User Custom Library block. **Line numbers drift between SDK versions — always
  re-resolve a cited line against the SDK you actually have, by function name.**
- **Consequence:** avatars accumulated across pipeline runs in one CLO session, and
  step 11 extracted the wrong one — **exporting a previous user's body under the
  current run's id.**
- **Evidence:** passing runs' saved projects contained exactly one `.avt` member;
  failing runs contained two or three, and the correct avatar was present every time
  but was not the one extracted.
- **Fix:** `step_11_save_outputs.py` now selects the highest-numbered `.avt` member and
  **hard-fails** any run whose saved project contains other than exactly one avatar —
  so a leak is reported rather than silently corrected.
- **Why this one matters most:** it is the only incident here that produced *wrong
  output that looked correct*. A crash tells you. This did not. Note the shape — it is
  the same class of bug as `_discover_default_native_avatar()` globbing a shared output
  directory (see the personalization doc, Part 8).

### 3.7 `POST /export` hangs on a completely empty scene — OPEN

- **Condition:** no avatar, no patterns loaded.
- **Symptom:** queue never drains; CLO's main thread burns CPU and never returns.
  Recovery requires restarting CLO.
- **Status:** not root-caused. Not a blocker — the real pipeline always loads an avatar
  first.
- **Relevance:** if you are writing a probe or a test harness that exports from a bare
  scene, this will bite you. Load something first.

### 3.8 SDK/app version coupling has broken CLO before — **ACTION NEEDED**

- **Incident:** a plugin built against SDK `2025.2.368` hung CLO **permanently on
  `NewProject()`** after the app was upgraded to `2026.1.188` on 2026-08-15. Fixed by
  rebuilding against `2026.0.356` (SDK v10.0.3), matching the Qt 6.10 migration the
  vendor changelog requires a rebuild for.
- **Current state:** the plugin is built against **`2026.0.356`**. The SDK now on this
  machine is **`2026.1.336`**. These do not match.
- **What to do:** before trusting any new finding from the `2026.1.336` headers,
  confirm which SDK the *running* plugin was built against, and treat newer-header
  functions as unavailable until rebuilt. A function in the new headers may simply not
  exist in the DLL the installed plugin binds to — and per 1.1 it will fail *silently*,
  returning a dummy.
- **This is the most likely cause of a "the SDK says this exists but it does nothing"
  report.** Check it first.

### 3.9 `set-fabric-graphic` silently ignores placement — OPEN (plugin bug, not SDK)

- **Condition:** posting `u`/`v`/`scale` to `/set-fabric-graphic`.
- **Cause:** the schema in `plugin_contract.json` accepts them, but
  `ProcessCommandQueue` never applies them — it calls the same `dispatchTexture()` used
  for plain textures. A graphic therefore always behaves as a full texture replacement,
  never a positioned overlay.
- **Status:** pre-existing, documented in
  [`.agent/clo-avatar-vto/known-issue-26_7_23.md`](../clo-avatar-vto/known-issue-26_7_23.md).
  Note that `v_1.3.0.json` cites this file under its old name
  (`known-issue-fabric-graphic-placement.md`), which no longer exists — the version
  JSONs' doc references have drifted, so resolve them by date rather than by filename.
- **The SDK is not at fault** and has the right functions — see `[graphic]` in the
  inventory (87 declarations, 0 wired), e.g. `SetGraphicStylePositionOnPattern`,
  `SetGraphicStyleDimensionsOnPattern`, `GetGraphicStylePlacementPoints`. Wiring those
  is the actual fix.

### 3.10 Avatar measurement CSV import — long-running uncertainty

- Carried as "remains under investigation" from v1.1.0 (2026-03-31) through v1.3.0
  (2026-07-23). It works well enough to be the basis of Step 1, via
  `/import-avatar-measurements` with a 2-row bridge CSV generated from
  `schema/measurement_template_unconfirmed.csv`.
- The template filename says `unconfirmed`, and `schema/legacy_routes.md` treats both
  this and `avatar_properties` as legacy routes. Treat the field mapping as
  provisional. `GetAvatarMeasurements` (4.2) is the unused read-back that would let us
  verify what actually landed.

### 3.11 Threading divergence, Windows vs Mac

- v1.1.1: Windows read endpoints called CLO APIs **from the HTTP thread**, violating
  1.2; Mac already used the safer `dispatchSyncRead` pattern. Windows was brought into
  line.
- Mac has been `pending` since v1.3.0 and has no `TraceLog` equivalent. **Any finding
  in this document verified on Windows should be assumed unverified on Mac.**

---

## Part 4 — Capability deep dive

What each family can do, what we use, and what is worth taking. Counts are declarations
including overloads.

### 4.1 Avatar control — 30 declarations, 4 wired

Settled: `ImportAvatar` takes a **`.avt` path only**; `ImportOBJ`/`ImportFBX`/
`ImportGLTF` with `ImportObjectType = 0` import a mesh as an *object avatar* with no
parametric measurement rig. This is why the GLB→`.avt` round-trip is dead — see
`avatar-personalization-split-decision-26_10_28.md`.

**There is no avatar vertex read/write API and no morph-target API.** Avatar geometry
is not reachable by any sanctioned route. Do not look again; look at the GLB instead.

Unused and interesting:

| Function | Why it matters |
|---|---|
| `SetAvatarMeshTexture` | *"Import AvatarTexture Body Part(face, body, arm, leg)"* — per-body-part texture setting, at runtime. The face/skin work currently patches the `.avt`; this is the live alternative |
| `SetAvatarTexureMap` | Set texture maps for an avatar (SDK's own typo — spelled `Texure`) |
| `SetAvatarOpacityMap`, `SetAvatarOpacityMapByIndex` | **Runtime control of the avatar's opacity maps.** The hair alpha masks (`hair_main_alpha.jpg`) are exactly this — this is the live route to reshaping hair without touching the `.avt` |
| `SetAvatarSoftBodyStiffness` / `Get…` | **Soft-body avatar.** The body can deform under tight clothing. Direct realism gain for a fit product, and nothing else on our roadmap provides it |
| `SetAvatarSmooth`, `GetAvatarSubdivisionLevel` | Subdivision control — quality/performance lever on the delivered mesh |
| `SetAvatarActivation`, `SetShowHideAvatar`, `IsShowAvatar` | Activate/deactivate and show/hide. See 3.2 on `IsShowAvatar`'s ambiguity |
| `AlignAvatarsAndGarmentToCenter` | Scene normalization before export — likely removes a class of framing bugs |

### 4.2 Measurements — 13 declarations, 0 wired

`GetAvatarMeasurements` — *"Gets all measurements (user measures and avatar-default
resizing measurements) on the avatar at the specified index."*

**This is the read-back we have never used**, and 3.10 is a direct consequence: we push
a measurement CSV and never confirm what CLO actually applied. Wiring this closes a
months-old uncertainty and gives Step 1 a verification step. High value, low effort.

### 4.3 Pattern ↔ avatar measure attachment — 9 declarations, 0 wired

`AttachPatternToAvatarMeasure(patternIndex, lineIndex, avatarMeasureName)` — the API
equivalent of the manual *"Attach to Measure (Avatar)"* workflow. It runs the solver
afterwards, registers one undo step, and **returns JSON** including `lineLength`,
`measureBasicLength` and `measureSurfaceLength` in mm. Height/linear measures are
rejected; it wants girths.

Read companions: `GetAllPatternToAvatarMeasures`, `GetPatternToAvatarMeasureByAvatar`,
`…ByPatterns`, `…ByMeasures`, `GetPatternEdgeToAvatarMeasureAttachment`,
`SetPatternEdgeToAvatarMeasure`, `GetPatternsAttachedToAvatarMeasures`.

**Why this is a significant find.** Our arrangement today places patterns by slot and
position. This instead *pins a pattern line to a named body measure* — a waistband to
the waist, a cuff to the wrist. That is:

- a better arrangement primitive for garments where the anchor point is the whole point
  (waistbands, cuffs, necklines);
- the natural mechanism for the **saree/dupatta tuck point** problem raised in the
  garment-scaling discussion, where there is no pattern-to-slot mapping to speak of;
- a **fit readout** — comparing the returned `lineLength` against
  `measureSurfaceLength` is a direct tight/loose number at that point on the body, in mm.

### 4.4 Fabric — 284 declarations, 10 wired, and the physical properties are not here

Critical structural finding: `FabricAPIInterface` is **almost entirely appearance** —
PBR base colour, normal/roughness/metalness/displacement/opacity maps, Substance,
AOP transforms. There is **no setter for stiffness, bending, density or friction.**

Physical properties come from **`.jfab` files**, applied with
`ChangeFabricWithJson(path)` (*"Overwrite all the properties of a fabric with json
file(.jfab)"*). The SDK ships the schema: `Documents/JFABSpec.json` (169 distinct keys)
and `Documents/fabric_sample.jfab`. The `mapPhysical` block is the cloth solver's real
input:

```jsonc
"mapPhysical": {
  "fHK": 10000.0,          // stretch stiffness
  "fSuK": 10.0, "fSvK": 10.0,            // shear stiffness U/V
  "fBuK": 8000.0, "fBvK": 2000.0, "fBhK": 8000.0,   // bending stiffness U/V/H
  "fBucklingStiffnessU/V/H": 1.8,        // + fBuLR/fBvLR/fBhLR buckling ratios
  "fDensity": 0.0003, "fThickness": 0.5,
  "fFriction": 0.03, "fIDS": 0.0001,     // friction, internal damping
  "listNonlinearHK": [], "listNonlinearSuK": [], "listNonlinearSvK": [],
  "mapRawData": { "MVWarpForceList": [], "MVWeftForceList": [], "MVBiasForceList": [] }
}
```

**So fabric realism for every new garment class is a JSON authoring problem, not an API
problem.** Denim, chiffon, georgette, silk, cotton jersey become a checked-in `.jfab`
library. `mapRawData` even accepts real warp/weft/bias force–length curves, so measured
fabric test data can be loaded directly if a supplier provides it.

This is the cheapest high-impact item on the whole list, and it is a prerequisite for
jeans (stiff) and sarees (very light, very drapey) behaving differently at all.

Also unused: `AddFabric`, `ReplaceFabric`, `AssignFabricToPattern`, `DeleteFabric`,
`GetFabricInfo` (read-back), `ExportFabric`/`ExportZFab` (persist a tuned fabric),
`CreateZfabFromTextures`, `CombineZfab`, `ImportXtexFile`/`ApplyXtexFile` (note the
distinction: `Import` overwrites everything, `Apply` sets only what the file contains),
`ImportGLTFAsFabric`, and the `AutoGenerateFabric{Normal,Opacity,Roughness,Displacement}Map`
family — which would generate PBR maps from a base colour texture, directly relevant to
Step 2 ingesting flat product images.

### 4.5 Fit maps — 4 declarations, 0 wired. **The biggest unused opportunity.**

```
SetStressMapStatus(bool)   GetStressMapStatus()
SetStrainMapStatus(bool)   GetStrainMapStatus()
```

CLO's stress and strain maps are the industry-standard tight/loose visualization — the
thing a technical designer actually looks at to judge fit. **We are a fit product and we
have never switched them on.**

Turn one on, then export an image (4.11) or a GLB, and the result is a per-garment,
per-user tightness readout. Two uses, both central:

1. **Shopper-facing:** a tight/loose heatmap is a far stronger fit claim than a static
   render. It is the visual that distinguishes us from a 2D try-on toy.
2. **Internal:** a quantitative signal for size recommendation that does not require us
   to invent a fit metric from measurements.

Caveats to establish before promising anything: these are *render states*, so the output
path is an image or a textured export rather than numbers — check whether the colours
survive `ExportGLB` or whether an image export is required. And confirm the maps appear
on the garment rather than the avatar. Both are one-hour tests.

### 4.6 Animation — 26 declarations, 0 wired. **This is the interactive-physics route.**

| Function | Role |
|---|---|
| `SetAnimationRecording`, `RunAnimationRecording` | *"Start recording an animation within the specified frame range."* |
| `SetStartAnimationFrame`, `SetEndAnimationFrame`, `GetTotalEndAnimationFrame`, `GetAnimationLayerFrameRange` | Frame range control |
| `SetCurrentAnimationFrame`, `GetCurrentAnimationFrame`, `MoveAnimationFrame` | Seek |
| `CopyFromFirstClothCache` | Copy the first cloth cache to the current frame |
| `ImportPose` / `ExportPose` | Pose files — the input for multi-pose drape |
| `ExportAnimationVideo`, `ExportTurntableVideo` | Video out (needs an XVid MPEG-4 codec installed — a real deployment dependency) |

Plus, in `ImportExportOption` (`CloApiData.h`): `bCreateAvatarJointAnimation`,
`bCreateAvatarCacheAnimation`, `bCreateAvatarBlendShapeAnimation`, `morphingFrameCount`,
and `fps` for vertex cache. `ImportAlembic` exists on the import side.

**This is exactly the "bake the motion in CLO, scrub it in the browser" plan.** It is
not a workaround — it is a first-class CLO feature we had not looked for. It gives the
CLO-like grab-and-move feel without a browser-side solver, and therefore without the
browser becoming a second source of truth about fit.

Note the exported GLB currently contains **0 morph targets and 0 animations**, so none
of this is coming through today. Whether it arrives as vertex cache, joint animation or
blendshapes depends on those export flags, and that choice determines what three.js can
play back. Worth settling early.

### 4.7 Simulation settings — 21 declarations, 1 wired

We call `Simulate` on defaults. Unused levers:

`SetSimulationQuality`, `SetSimulationTimeStep`, `SetSimulationNumberOfSimulation`
(substeps), `SetSimulationCGIterationCount`, `SetSimulationCGResidual`,
`SetSimulationCGFinishCondition`, `SetSimulationSelfCollisionIterationCount`,
`SetSimulationSelfCollisionAvoidanceStiffness`, `SetSimulationAirDamping`,
`SetSimulationGravity`, `SetSimulationNonlinearSimulation`,
`SetSimulationGroundCollision`, `SetSimulationGroundHeight`,
`SetSimulationLayerBasedCollisionDetection`, `SetSimulationNumberOfCPUInUse`,
`SetParticleDistanceOfPattern(s)`, `SetAddlThicknessCollision`.

Three that matter most for garment scaling:

- **`SetParticleDistanceOfPattern`** — mesh resolution per pattern. This is *the* lever
  for a saree: 5.5 m of fabric at t-shirt particle distance is unaffordable, and at too
  coarse a distance the pleats disappear. Per-pattern control means spending resolution
  only where it shows.
- **`SetSimulationNonlinearSimulation`** — pairs with the `listNonlinear*` curves in
  `.jfab` (4.4). Required for fabrics whose stretch is not linear, which is most real
  cloth.
- **`SetSimulationNumberOfCPUInUse`** — throughput. With concurrency pinned at 1 (1.3),
  per-run CPU allocation is the only scaling knob we have.

Also `SetSimulationLayerBasedCollisionDetection` matters for layered outfits — a dupatta
over a top, a jacket over a shirt.

### 4.8 Grading / sizes — 30 declarations, 0 wired

A complete multi-size system: `AddGradingSize`, `AddGradingSizeGroup`,
`ImportGradeRuleToSizeGroup` (load a `.rul` grade rule file),
`ChangeGradingSizeInformation`, `GetGradingSizeTotalCount`,
`GetCurrentGradingSizeIndex`, `GetGradingSizeListFromRuleTable`,
`GetValidGradingSizeGroupInformation`, `GetGradingSizeQuantityMix`.

And the part that makes it ours: **`SetGradingPairedAvatar`** (pair a loaded avatar to a
grading size), **`SetGradingPairedAvatarFromFile`** (pair an `.avt`), and
**`SetGradingPairedAvatarSizing`** (load an Avatar Size `.avs` file as a grading size's
avatar sizing).

So CLO natively supports *one graded garment, many sizes, each paired to an avatar*.
That is the shape of **"which size should I buy?"** — and we would otherwise build it by
simulating N separate runs. Also per-size grading of graphics, buttons, buttonholes and
individual pattern points, which matters when a print or a button placket must scale
correctly across sizes.

### 4.9 Trims, buttons, zippers, elastic, topstitch — ~114 declarations, 0 wired

This is the complex-garment answer, and it is substantial.

**Buttons** — `AddButtonToPattern`, `AddButtonHoleToPattern`, `PlaceButtonPairsOnEdge`,
`DistributeButtonPairsOnEdge` (evenly space N pairs along two seam-paired edges),
`CreateButtonholesForButtonHeads` (ray-cast through the placket), `FastenButtons`,
`UnfastenAllButtons`, `ConvertTrimsToButtons`, and **`GetButtonPairInfoAsJson`** — a
JSON report of every head/hole pair and whether each is fastened.

That last one is quietly a **fit signal**: a shirt that cannot button on this body is
the most unambiguous "too small" result available, and it comes back as JSON rather than
needing interpretation.

**Zippers** — a full style API (teeth type/width, slider, puller, top/bottom stoppers,
tape thickness, weight) plus `GenerateZippersFromObj`, mirroring the GUI's *"Register
OBJ"* flow. Jeans flies and jackets need this.

**Elastic** — `SetPatternPieceElastic`, `…Strength`, `…StrengthRatio`,
`…SegmentLength`, `…TotalLength`, all with `lineIndex == -1` meaning "all lines".
Waistbands, cuffs, leggings, joggers, saree petticoats. Without this, an elasticated
waistband can only be faked.

**Topstitch** — ~48 declarations including `PlaceTopstitchOnInternalLine`,
`AddSeamlineTopstitch`, and full style control (width, distance, number of lines,
offset, colour, opacity). Visible topstitching is denim's signature; absent it, jeans
read as blue cotton trousers.

`SetPatternPieceSeamtaping` is also there for technical outerwear.

### 4.10 `RestAPIInterface` — 9 declarations, 0 wired

CLO can make **outbound** HTTP calls: `CallRESTGet`, `CallRESTPost`, `CallRESTPut`,
`CallRESTPostWithMultipartFormData`, plus `CallbackRestRequest` and
`CallbackRestMultiRequest` for async with callbacks, and `GetByteArrayFromStream`.

Our whole architecture polls `/status` after queueing (Type 1, 1.2). This would let CLO
**push** completion to our backend instead — removing poll latency and the 200 ms timer
cadence from the critical path. `CallbackRestMultiRequest` suggests fan-out is supported.

Worth evaluating, with a caution: a callback fires on CLO's thread, so whatever it runs
inherits every constraint in 1.2 and 1.3.

### 4.11 Export and rendering — 123 + ~180 declarations, 9 wired

Beyond the mesh exports we use:

| Function | Why it matters |
|---|---|
| `ExportPatternJSON`, `ExportPatternCPX` | Pattern data out as JSON / binary CLO Pattern eXchange. Directly relevant to Step 2's reusable-pattern goal |
| `ExportGarmentInformation`, `…ToStream` | *"same as given in Garment Information"* — the `ToStream` variants return a string, so **no temp file round-trip** |
| `ExportPOM`, `ExportBOM` | Point of Measure and Bill of Materials. POM is garment spec measurement — the other half of a fit comparison |
| `ExportTechPack`, `ExportTechPackToStream` | Full tech pack JSON; `TechPackSpec.json` ships in the SDK |
| `ExportStdViewImage`, `ExportCustomViewImage`, `ExportMultiViewImages`, `ExportThumbnail3D`, `ExportSnapshot2D` | **Server-side multi-view rendering.** A cheap image-based try-on tier for low-end devices, and the output path for fit maps (4.5) |
| `…ForAllColorways` variants | One call per colourway — the natural fit for a product in several colours |
| `ExportRenderingImageForCustomView`, `SetLightPresetForExportRenderingImage` | V-Ray quality renders with light presets. Marketing-grade stills |

Prefer the `ToStream` variants wherever they exist: they avoid temp files, which removes
a class of path and cleanup bugs from the pipeline.

### 4.12 `GuiAPIInterface` — 39 declarations, 0 wired

A full widget toolkit inside CLO: `CreateToolWindow`, `CreateDockPanel`, `AskConfirm`,
`AskText`, `AskChoice`, `AskMultiChoice`, `AskForm`, and widgets including `AddTable`,
`AddProgressBar`, `AddDropdown`, `AddImage`, `AddSlider`, `AddMenu`.

Not product surface — but a genuinely useful **internal ops panel**: queue depth, last
results, avatar count, a "run pipeline" button, live `TraceLog` tail. Given that
debugging currently means reading log files beside a GUI, this is a modest build with a
real payoff.

`IsGuiAvailable` — *"Check whether native GUI commands can be used in the current
session"* — is also the clean way to detect headless operation.

---

## Part 5 — Ranked opportunities

Ordered by value per unit of effort, for our actual goals. "Effort" is plugin + pipeline
work, excluding verification.

| # | Opportunity | Why | Effort |
|---|---|---|---|
| 1 | **Fit maps** — `SetStressMapStatus` / `SetStrainMapStatus` (4.5) | We are a fit product that has never rendered the industry-standard fit visualization | ~1 day + a 1 h feasibility test |
| 2 | **`.jfab` fabric library** (4.4) | Unblocks every non-jersey garment class. JSON authoring, schema ships with the SDK | 2–3 days + per-fabric tuning |
| 3 | **`GetAvatarMeasurements` read-back** (4.2) | Closes the measurement uncertainty open since v1.1.0 (3.10). Verification, not a feature | ~half day |
| 4 | **Baked animation** (4.6) | The interactive-cloth feel, without a browser solver or a second source of truth on fit | 1–2 weeks |
| 5 | **Simulation settings**, esp. `SetParticleDistanceOfPattern` (4.7) | Required for sarees to be affordable; quality/speed control per garment class | 2–3 days |
| 6 | **Elastic + topstitch** (4.9) | Waistbands and visible stitching. Jeans are not credible without both | 3–4 days |
| 7 | **`AttachPatternToAvatarMeasure`** (4.3) | Better arrangement primitive; the saree tuck-point mechanism; a per-point fit number in mm | 2–3 days |
| 8 | **Buttons + `GetButtonPairInfoAsJson`** (4.9) | Shirts and flies; "it won't button" is the clearest possible fit failure | 3–4 days |
| 9 | **Multi-view image export** (4.11) | A cheap try-on tier for weak devices; the output path for #1 | 2–3 days |
| 10 | **Grading** (4.8) | Native size recommendation instead of N hand-run simulations | 1–2 weeks |
| 11 | **`SetAvatarOpacityMap`** (4.1) | Runtime hair-alpha control — the live alternative to patching the `.avt` | 1–2 days |
| 12 | **`SetAvatarSoftBodyStiffness`** (4.1) | Body deforms under tight clothing. Realism nothing else on the roadmap gives | 1 day + tuning |
| 13 | **`CallbackRestRequest`** (4.10) | CLO pushes instead of us polling; removes poll latency | 2–3 days |
| 14 | **GUI ops panel** (4.12) | Debugging quality of life | 2–3 days |

Items 1 and 3 are the two I would do first regardless of roadmap: one is the product's
central claim, the other closes a months-old unknown. Both are under a day.

---

## Part 6 — Checklist for wiring anything new

1. **Confirm the SDK the running plugin was built against** (3.8). A function present in
   `2026.1.336` headers may not exist in the bound DLL, and will fail silently (1.1).
2. **Pick the call type** (1.2): mutation → Type 1; read needing an answer → Type 2;
   no SDK call → Type 3. Add the matching `ProcessCommandQueue` branch.
3. **Wrap `EXPORT_API` calls in the SEH guard** (3.1). Keep the guarded body free of
   C++ locals needing unwinding.
4. **Never pass an index you have not independently confirmed** (3.3, 3.4). Per-index
   avatar queries crash or hang on absent indices; the API will not validate for you.
5. **In Type 2, wrap each individual SDK call in its own `try/catch`** so the promise is
   always fulfilled (1.2).
6. **Verify the observable side effect in CLO**, not the return value (1.1).
7. **Compare against CLO's own GUI** when output looks wrong (3.5). The GUI is the
   reference implementation.
8. **Update `plugin_contract.json`, bump `clo_workspace/versions/`, and record
   `known_issues` with the exact reproducing condition** — not just "crashes". The
   condition is what makes an incident re-testable later instead of permanent folklore.
9. **Maintain Windows/Mac parity** or mark Mac `pending` explicitly (3.11).
10. **Never run a second worker against the same CLO** (1.3).

---

## Part 7 — What the SDK does not have

Stated so nobody searches twice. Verified absent from all 1,137 declarations:

- **Avatar vertex read or write.** No geometry access of any kind.
- **Morph targets / blendshapes on the avatar.** Export flags mention blendshape
  *animation* for imported object avatars, but there is no authoring API.
- **Hair geometry.** No hair creation, styling or replacement. Hair textures are
  swappable in the `.avt`; hair style is not reachable.
- **Direct physical-property setters on fabric.** Only via `.jfab` (4.4).
- **A safe avatar-count query.** Every route is ruled out (3.2).
- **Real-time cloth streaming.** Simulation is run-to-completion; there is no API to
  stream solver state out per frame. This is why browser-side interactivity must be
  baked (4.6) rather than live.

---

## Appendix — Provenance

- **SDK:** `C:/setup/CLO_SDK_v2026.1.336_Win/CLO_SDK_v2026.1.336_Win/CLOAPIInterface/`
  — 7 headers, 1,137 `virtual` declarations.
- **Only vendor documentation shipped:** `Documents/CLO_API_Overview_2020-05-14.pdf`
  (2020 — six years stale), plus `JFABSpec.json`, `TechPackSpec.json`,
  `fabric_sample.jfab`. The headers are the real reference, which is why the inventory
  file exists.
- **Wired-call detection:** `[A-Z_]+_API->(\w+)` across
  `clo_workspace/{windows,mac}/RestPlugin_*.cpp` → 34 distinct functions.
- **Incident history:** `clo_workspace/versions/v_1.1.0 … v_1.3.2.json`,
  [`.agent/website-launch-2/11-date-26_08_22.md`](../website-launch-2/11-date-26_08_22.md),
  [`.agent/website-launch-2/new-project-bug-writeup-26_8_9.md`](../website-launch-2/new-project-bug-writeup-26_8_9.md),
  [`.agent/clo-avatar-vto/known-issue-26_7_23.md`](../clo-avatar-vto/known-issue-26_7_23.md).
- **Two sources cited by the version JSONs are absent from this checkout:**
  `09-windows-plugin-commit-audit-new-project-hang.md` and `POST_MORTEM_v1.1.1.md`.
  The `EXPORT_API` exclusion (3.1) and the `NewProject()` hang (3.8) therefore rest on
  the version-JSON summaries alone. If either decision is ever reopened, that missing
  evidence is the gap to be aware of.
- **Threading taxonomy:** `.agent/saumy/after-1-jun/clo-api-call-types.md`.
- **Prior CLO API research:** `.agent/clo-research/02-clo-official-vs-inhouse-api.md`,
  `.agent/website-launch-2/12-clo-python-api-research.md`.

Both this file and the inventory were produced on 2026-10-29 against SDK
`2026.1.336`. The plugin in use was built against `2026.0.356` — see 3.8 before relying
on anything new here.
