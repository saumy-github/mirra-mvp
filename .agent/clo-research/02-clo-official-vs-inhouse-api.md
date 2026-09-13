# CLO Official API vs Mirra's In-House Plugin

Research date: 2026-08-29

---

## Short answer

**No — a no-parameter signature in CLO's docs does not mean you can run it directly.** Every function on `developer.clo3d.com` (e.g. `NewProject() -> None`, `GetAvatarCount() -> int`, `Simulate(_steps: int) -> bool`) is a bound method on an API object (`utility_api.NewProject()`, `export_api.GetAvatarCount()`) that only exists inside a **running, licensed CLO application with a project open**. There is no shell command, no CLI flag, and no bare executable that lets you invoke these from outside CLO. "No parameters" just means the call takes no *arguments* once you're already inside CLO's process — it says nothing about how you get there. To actually run one you need one of exactly two hosts CLO provides: (1) CLO's built-in Python console/drag-and-drop script runner, or (2) a compiled C++ plugin DLL linked against CLO's SDK and loaded by the running app — which is what Mirra built. So the commands "given on the web" and the commands Mirra built are, structurally, **the same underlying engine calls** (the public reference site is auto-generated from the SDK's own header comments — Python and C++ share identical docstrings, including shared typos). Mirra did not reinvent what CLO offers; it built the **transport, orchestration, and safety layer CLO does not ship**: an HTTP server inside the plugin, a command queue for thread safety, index-bounds workarounds for calls CLO's own SDK documents nowhere as crashing (`GetAvatarProperties` on a bad index kills the process; `DeleteAvatar` on a bad index hangs CLO's main thread), and a way to know how many avatars exist when no CLO API can safely tell you. That work had no CLO-provided substitute at the time it was built.

---

## What Mirra built

Two Python REST clients talk to one C++ plugin (`clo_workspace/windows/RestPlugin_windows.cpp`, 2457 lines; Mac port `clo_workspace/mac/RestPlugin_macOS.cpp`, 1982 lines — Mac is missing `/clear-avatars` only, otherwise route-parity). The plugin links against `CLO_SDK_v2026.0.356_WIN` (SDK v10.0.3) and hosts an `httplib`-based HTTP server on `localhost:50505`. Mirra's own orchestration code: `clo_vto/native_vto/` = 3512 lines across 20 files; `clo_avatar_generation/avatar_runtime/` client + step files add roughly 250+ more lines. (The 45,946 lines in `clo_workspace/shared/httplib.h` + `json.hpp` are vendored third-party libraries, not authored by Mirra.) Build logs (`clo_workspace/logs/`) show at least 20 rebuild cycles from 2026-04-07 through 2026-08-29 — consistent with the SDK-rebuild-per-CLO-version burden CLO's own docs describe as standing practice since ~2019.

| Endpoint | What it does | Backing | Used by |
|---|---|---|---|
| `GET /health` | Liveness + build metadata | `RestPlugin_windows.cpp:670` | `clo_vto/native_vto/client.py:37`, `clo_avatar_generation/avatar_runtime/client.py:39`, `step_01_health.py` (both pipelines) |
| `GET /capabilities` | Advertises which features this build supports | `:688` | `client.py:40` (both) |
| `GET /debug/import-scales` | Debug: import scale tracking | `:719` | `native_vto/client.py:43`, `step_05_verify_patterns.py:80` |
| `GET /avatar/debug` | Debug: avatar scene state | `:752` | `native_vto/client.py:49`, `step_06_read_edges_and_slots.py:235` |
| `GET /avatar/native-debug` | Debug: native avatar internals | `:758` | both clients; `step_03_import_avatar.py:81`, `avatar_runtime/step_07_import_base_avatar.py:50` |
| `GET /avatar/property-debug` | Debug: avatar property values | `:764` | `avatar_runtime/client.py:65`; `step_08_apply_measurements.py:72` |
| `GET /avatars/state` | Avatar count/list in scene | `:780` | `native_vto/client.py:268` (`get_avatar_count`), `avatar_runtime/client.py:68` |
| `POST /import-avatar` | Import OBJ avatar with scale | `:786` | `native_vto/client.py:55` — **no call site found in either step_*.py** (defined, unused in practice; superseded by `import-avatar-avt`) |
| `POST /import-avatar-avt` | Import `.avt` avatar file | `:818` | both clients; `step_03_import_avatar.py:22`, `avatar_runtime/step_07_import_base_avatar.py:43`, `step_08_apply_measurements.py:157` |
| `POST /import-avatar-measurements` | Import avatar measurement CSV | `:847` | both clients; `step_03_import_avatar.py:53`, `avatar_runtime/step_08_apply_measurements.py:25`, `resize_avatar.py:106` |
| `POST /avatar/set-properties` | Set named avatar properties (skin offset, friction, etc.) | `:881` | `avatar_runtime/client.py:86` only; `step_08_apply_measurements.py:73` — **not used by `clo_vto`** |
| `POST /import-pattern` | Import DXF pattern | `:924` | `native_vto/client.py:69`; `step_04_import_patterns.py:226` |
| `POST /execute` | Force-drain the command queue | `:967` | `native_vto/client.py:178` (inside `wait_for_queue`); `avatar_runtime/client.py:59` |
| `POST /create-seam` | Join two pattern edges into a seam | `:1015` | `native_vto/client.py:219`; `step_09_create_seams.py:81` |
| `POST /simulate` | Run N physics steps | `:1051` | `native_vto/client.py:240`; `step_10_simulate.py:12`, `step_06_read_edges_and_slots.py:349` |
| `POST /export` | Export garment/avatar to GLB | `:1079` | both; `step_11_export_note.py:41`, `avatar_runtime/step_12_export_glb.py:103` |
| `GET /patterns/count` | Pattern count in scene | `:1109` | `native_vto/client.py:253`; `step_04_import_patterns.py:173` |
| `GET /patterns/{i}` | Pattern info | `:1115` | `client.py:256`; `step_05/06` |
| `GET /patterns/{i}/bbox` | Pattern bounding box | `:1122` | `client.py:259` — **no call site found** (defined, unused) |
| `GET /patterns/{i}/input` | Pattern input metadata | `:1129` | `client.py:262` — **no call site found** (defined, unused) |
| `GET /patterns/{i}/line-lengths` | Edge line lengths for a pattern | `:1136` | `client.py:265`; `step_06_read_edges_and_slots.py:264,330` |
| `POST /save-project` | Save `.zprj` | `:1147` | both; `step_10b_save_project.py:42`, `avatar_runtime/step_11_save_outputs.py:173` |
| `POST /export-avatar-avt` | Export avatar directly to `.avt` | `:1175` | `avatar_runtime/client.py:108`; `step_11_save_outputs.py:189` — **documented as SEH-crash-stubbed on Windows as of v1.1.1** (see below); not used by `clo_vto` at all |
| `POST /new-project` | Clear garment/pattern state | `:1204` | both; `step_02_new_project.py:28`, `avatar_runtime/step_07_import_base_avatar.py:35` |
| `POST /clear-avatars` | Delete tracked avatars from scene | `:1227` | defined in both Python clients, **called by neither pipeline** — confirmed dead code by `clo_workspace/versions/v_1.3.2.json` itself ("step_07 no longer invokes them... dead code as of 2026-08-22") |
| `POST /arrange-pattern` | Position a pattern on/around the avatar | `:1259` | `native_vto/client.py:76`; `step_07_arrange_patterns.py:43` |
| `POST /set-fabric` | Assign a fabric preset to a pattern | `:1297` | `native_vto/client.py:101`; `step_08_apply_fabric.py:108` |
| `POST /set-fabric-color` | Set diffuse RGB color of a pattern's fabric | `:1328` | `client.py:110`; `step_08_apply_fabric.py:134` |
| `POST /set-fabric-texture` | Load a texture image onto a pattern's fabric | `:1360` | `client.py:121`; `step_08_apply_fabric.py:167` |
| `POST /set-fabric-graphic` | Overlay a logo/print graphic | `:1390` | `client.py:133`; `step_08_apply_fabric.py:190` |
| `GET /fabric-status` | Poll async fabric-CAPI dispatch completion | `:1424` | `client.py:195` (`wait_for_fabric`) |
| `POST /fabric-status/reset` | Clear fabric dispatch counters | `:1445` | `client.py:187`; `step_08_apply_fabric.py:132,163` |
| `GET /arrangement-list` | List pattern arrangement slots | `:1459` | `client.py:95`; `step_06/07` |
| `GET /pattern-arrangements` | Current pattern-to-avatar arrangement | `:1465` | `client.py:98`; `step_06/07` |
| `GET /arrangement/debug` | Debug: arrangement internals | `:1471` | `client.py:46`; `step_06/07` |
| `GET /status` | Queue depth / processing flag | `:1477` | both; used pervasively for `wait_for_queue` polling |

Endpoints registered in C++ but with **no Python call site anywhere in either pipeline**: `POST /import-avatar` (OBJ path — superseded by AVT import), `GET /patterns/{i}/bbox`, `GET /patterns/{i}/input`. These represent built-but-unused surface — not necessarily wasted (they may be debug/future-use), but they are not load-bearing for either pipeline today.

---

## What CLO officially offers

This section is built primarily on an existing, thorough research pass already in this repo — `.agent/website-launch-2/12-clo-python-api-research.md` — which I re-read and verified rather than re-deriving from scratch, plus two new targeted searches to close a gap that prior pass didn't cover (CLO-SET/Enterprise cloud APIs).

### 1. CLO's embedded Python API — **[DOC]**, exists, but not a standalone automation surface
- Source: https://developer.clo3d.com/python.html — "Main Menu → Edit → Python Script → Run Python Script" or drag-and-drop a `.py` file onto the running CLO window.
- Publicly documented, free with any CLO license (no separate tier mentioned).
- Existed since at least 2023 per changelog (v4.2.1 Aug 2023 "Python API Editor Improvement"); became loadable as an **auto-starting plugin** (comparable to a compiled DLL) only as of v8.0.3 (Aug 2025) and v10.0.0 (May 2026, "Python Plugin Auto-Load on Startup") — https://developer.clo3d.com/changelog.html. This plugin-hosting mode postdates most of Mirra's plugin-architecture decisions.
- **Critical finding, confirmed structurally**: the public API reference (https://developer.clo3d.com/list.html) is Sphinx-generated directly from the SDK's own C++ header Doxygen comments. Every function is shown with matched Python and C++ signatures sharing identical docstring text, including shared typos (e.g. "loadObjectType 0 : avater, 1 : trim"). **Python and C++ are two bindings over the identical underlying engine calls — not separate, independently-safer implementations.**
- This means: the crash/hang bugs Mirra hit (`GetAvatarProperties(index)` crashing the process on an invalid index; `DeleteAvatar([...])` hanging CLO's main thread on an invalid index) are almost certainly present identically in the Python binding, since nothing in the docs suggests Python gets bounds-checking the C++ SDK lacks. Switching implementation language would not have avoided these.
- `GetAvatarCount()` is documented as the only safe way to learn how many avatars exist — matching exactly what Mirra's own `v_1.3.2.json` and `client.py:271-284` (`get_avatar_count`) independently concluded from live crash reproduction.

### 2. CLO's C++ SDK — this is what Mirra's plugin is built on
- Source: `support.clo3d.com` "CLO API/SDK Guide" article (fetched via curl in prior research; WebFetch gets HTTP 403 on this Zendesk-hosted domain).
- Requires downloading a per-CLO-version SDK zip and rebuilding the plugin to match; this rebuild-on-upgrade requirement is confirmed as CLO's standing plugin contract since at least 2019 (API v2.3/v2.5 era), not something specific to Mirra's setup.
- No behavioral specification beyond header comments exists publicly — CLO's own support article for "How to use Python Script in CLO?" states the only additional guidance beyond the (generated) reference is "use CLO AI chat or refer to the API source." There is no independent narrative documentation of edge-case behavior (invalid indices, empty scenes, repeated calls) anywhere public.

### 3. CLO-SET / CLO Enterprise APIs — **[DOC]** exists, but does not do what Mirra needs
- Source: https://style.clo-set.com/docs/closetapi and https://closetapiv2.docs.apiary.io/ (the latter returned HTTP 502 on fetch attempt; description below is from the landing doc page).
- CLO-SET API is described explicitly as available "only for CLO-SET Enterprise Plan" and covers **file upload/download to/from Workrooms and file metadata retrieval only** — it converts uploaded `.zprj`/`.zpac`/`.avt` files into a compact viewer format for CLO-SET's 3D Viewer.
- **It does not expose programmatic avatar generation, garment pattern import, physics simulation, or virtual try-on rendering.** It is a cloud storage/viewer-conversion API, not a computation API. This directly rules out CLO-SET as an alternative to what Mirra built — there is no official cloud REST endpoint that runs the simulation Mirra's pipeline needs.

### 4. Official headless / batch / command-line mode
- **[UNKNOWN as a standalone product feature]**. The CLO changelog references "headless" repeatedly as an internal execution mode for specific API calls (e.g. "Headless ImportFile," "ExportAnimationVideo (Headless)," "Zpac was not loaded properly via ImportFile API in Headless Mode") — this indicates CLO's own engine treats non-interactive execution as a first-class internal concept. But no page found (public search, developer.clo3d.com, or the existing repo research) documents a standalone CLI executable, command-line flags, or a batch-mode invocation surface independent of loading a plugin or running a script inside the app. A fresh web search for "CLO3D official command line headless batch mode automation documentation" (2026-08-29) returned no CLO-specific results at all beyond the changelog page already covered.

### 5. Official REST/automation server
- **No evidence found that CLO ships a localhost HTTP/REST server as a product feature.** The `localhost:50505` server is entirely Mirra's construction, using a vendored third-party library (`httplib.h`) inside the compiled plugin. CLO's own architecture requires a plugin (C++ DLL or, since Aug 2025, an auto-loading Python plugin) to be the thing that receives control inside the process — CLO does not itself expose a network listener.

### 6. Official file-format tooling
- `.zprj`: `ImportZprj`/`ExportZPrj` — documented, same SDK/Python-shared calls Mirra's plugin wraps via `/save-project`.
- `.avt`: `ImportAvatar`, and an `export-avatar-avt`-equivalent (`ExportAVT`) — documented in the SDK, but Mirra's own `v_1.1.1.json` records `ExportAVT` as **SEH-crash-stubbed on Windows** as of that version ("ExportAVT crashes CLO main thread via SEH exception — stubbed out... use zprj extraction"). This is a documented CLO-side engine bug, not a Mirra implementation gap.
- DXF import: `ImportDXF`/`ImportDXFW` with `ImportDxfOption` (undocumented per-field semantics, e.g. `m_bAppend`) — same underlying call Mirra's `/import-pattern` wraps.
- glTF/GLB export: `ExportGLTF`/`ExportGLB` — documented, but the CLO changelog shows a string of ongoing GLB-exporter bugs (empty/missing garment, wrong z-offset, missing texture fields) spanning multiple recent CLO versions, independent of C++ vs Python binding. Mirra's own code comments (`RestPlugin_windows.cpp`) independently confirm hitting an `ExportGLB` stub-body issue tied to an SDK/CLO version mismatch.

---

## Endpoint-by-endpoint comparison

| Mirra endpoint | Underlying CLO call | Classification | Notes |
|---|---|---|---|
| `/import-avatar`, `/import-avatar-avt` | `ImportAvatar` (SDK/Python, identical binding) | OFFICIAL-EQUIVALENT-EXISTS | The underlying call is CLO's own; what's not official is the HTTP transport and queueing around it. |
| `/import-avatar-measurements` | `ImportAvatarMeasurement` / `ImportMeasurement` | OFFICIAL-EQUIVALENT-EXISTS | Same call; CSV schema itself is undocumented publicly on either side (`[UNKNOWN]` per prior research). |
| `/avatar/set-properties` | `SetAvatarProperties` | OFFICIAL-EQUIVALENT-EXISTS | Direct SDK/Python call. |
| `/import-pattern` | `ImportDXF`/`ImportDXFW` | OFFICIAL-EQUIVALENT-EXISTS | Direct SDK/Python call; `bAppend`-style semantics undocumented on both sides. |
| `/new-project` | `NewProject()` | OFFICIAL-BUT-INSUFFICIENT | The call exists, but its documented brief ("Clear the current garment and begin a new garment") omits that avatars survive it — Mirra had to discover this behavior empirically and build `/clear-avatars` + `g_avatarsLoaded` tracking to compensate, because no CLO API safely reports current avatar count either. |
| `/clear-avatars` (dead code) | `DeleteAvatar([...])` | NO-OFFICIAL-EQUIVALENT | `DeleteAvatar` exists officially, but is confirmed to hang CLO's main thread on an invalid index, with no documented safe-probe pattern; Mirra's route is disabled as a result. There is no official, safe "clear all avatars" call. |
| `/avatars/state`, `get_avatar_count` | `GetAvatarCount()` (safe) vs `GetAvatarProperties`/`GetAvatarNameList` (unsafe) | NO-OFFICIAL-EQUIVALENT | CLO provides no safe way to enumerate/inspect avatars beyond a bare count; Mirra's own `g_avatarsLoaded` counter and avoidance logic exist because every per-index CLO query is either crash-prone (`GetAvatarProperties`) or ambiguous (`IsShowAvatar` can't distinguish hidden from absent). |
| `/create-seam` | `AddSeamlinePairGroup` | OFFICIAL-EQUIVALENT-EXISTS | Direct SDK/Python call. |
| `/simulate` | `Simulate(_steps)` | OFFICIAL-EQUIVALENT-EXISTS | Direct SDK/Python call, documented with a working example in `scenario.html`. |
| `/export` (GLB) | `ExportGLB`/`ExportGLTF` | OFFICIAL-BUT-INSUFFICIENT | The call exists but has a documented history of engine-level bugs (empty output, missing fields) across CLO versions, independent of binding language — Mirra's retries/validation around this are compensating for CLO's own exporter immaturity. |
| `/export-avatar-avt` | `ExportAVT` | OFFICIAL-BUT-INSUFFICIENT | Documented call, but confirmed by Mirra's own testing to crash via SEH exception on Windows in the SDK version they used — a CLO-side defect, not something Mirra could route around except by falling back to zprj extraction. |
| `/save-project` | `ExportZPrj`/`ImportZprj` | OFFICIAL-EQUIVALENT-EXISTS | Direct SDK/Python call. |
| `/patterns/*` (count, info, bbox, input, line-lengths) | Pattern query APIs (`GetSeamlinePairGroupCount`, etc., pattern-side getters) | OFFICIAL-EQUIVALENT-EXISTS | Direct SDK/Python calls; bbox/input variants are unused by either pipeline today. |
| `/arrange-pattern`, `/arrangement-list`, `/pattern-arrangements` | Arrangement APIs (pattern placement) | UNKNOWN | Prior research did not specifically confirm public documentation of arrangement-placement functions by name; classify as unknown rather than guess. |
| `/set-fabric`, `/set-fabric-color`, `/set-fabric-texture`, `/set-fabric-graphic` | Fabric/material APIs | UNKNOWN | Not specifically checked against `list.html` in the prior research pass or this one; plausible SDK equivalents exist (CLO has fabric APIs) but not verified here. |
| `/health`, `/capabilities`, `/status`, `/execute`, `/fabric-status*`, debug routes | — | NO-OFFICIAL-EQUIVALENT | These have no CLO equivalent by design — they are Mirra's own HTTP server plumbing (liveness, command queue draining, async-dispatch polling). CLO does not ship a server, a queue, or an HTTP transport at all. |
| The REST server itself (`httplib` on `localhost:50505`) | — | NO-OFFICIAL-EQUIVALENT | Confirmed: no official CLO product (SDK, Python API, or CLO-SET/Enterprise) provides a network-accessible automation server. CLO-SET's API is cloud file storage/conversion only, not a simulation control surface. |

**Bucket counts**: OFFICIAL-EQUIVALENT-EXISTS: 8 · OFFICIAL-BUT-INSUFFICIENT: 3 · NO-OFFICIAL-EQUIVALENT: 4 · UNKNOWN: 2 (grouped rows above; individual endpoints within a grouped row share one classification).

---

## Was the effort avoidable?

**Mostly no — the engineering that actually took time was not duplicating CLO's API, it was working around what CLO's API doesn't safely provide.** Every "OFFICIAL-EQUIVALENT-EXISTS" row above is a thin wrapper: Mirra's plugin calls the exact same `ImportAvatar`, `Simulate`, `AddSeamlinePairGroup`, `ExportZPrj` functions that are on the public reference page. Nobody re-implemented CLO's garment engine. Building those wrappers in C++ instead of Python was a smaller, more defensible choice than it might first look: CLO's Python-as-auto-loading-plugin mechanism (the only way Python could have played the same "always-on control surface" role as the compiled DLL) has only existed since August 2025, and per the existing research, would not have avoided the crash/hang bugs anyway, since Python and C++ call the identical underlying engine code.

The genuinely load-bearing, time-consuming work — the REST server, the command queue for thread safety, the `g_avatarsLoaded` counter, the decision to never call `GetAvatarProperties`/`DeleteAvatar` on an unverified index, the `/clear-avatars` route now correctly left dead pending a safe way to know how many avatars exist — has **no official CLO substitute at all**. CLO ships no server, no CLI, no documented safe avatar-enumeration API, and its own SDK guide gives zero behavioral specification beyond one-line header comments. CLO-SET's API, the one plausible "maybe we didn't need to build a server" candidate, turned out to be a file-storage/viewer-conversion product, not a simulation-control API — so it could not have replaced any part of this pipeline.

Where some effort plausibly *was* avoidable: the dead code (`/clear-avatars`, `POST /import-avatar` OBJ path, `/patterns/{i}/bbox`, `/patterns/{i}/input`) represents built-but-unused surface — not large, but real overhead from iterating toward the current design. That is normal engineering churn, not evidence of duplicating something CLO already offered.

**Verdict: the team did not spend months rebuilding something CLO ships for free.** They spent that time building the transport and safety layer CLO does not ship at all, informed by direct, reproducible crash/hang evidence (documented in `clo_workspace/versions/v_1.3.2.json` and `v_1.1.1.json`) rather than guesswork.

---

## What could be replaced going forward

- **Nothing should be replaced defensively based on this research alone.** The one candidate — migrating from the compiled C++ plugin to CLO's Python-plugin-auto-load mechanism (available since v8.0.3/v10.0.0) — would remove the Qt-ABI/SDK-rebuild-on-upgrade burden (a `.py` file has no compiled ABI to go stale), which is a real, if secondary, maintenance win. It would **not** remove the need for the avatar-count workaround, the index-bounds discipline, or the command-queue/thread-safety logic, since those are engine-level behaviors shared by both bindings. This is architecture-level and should go through the same empirical-spike process the existing research doc already recommends (§"What would it cost to find out" in `.agent/website-launch-2/12-clo-python-api-research.md`) before any migration decision, not be treated as settled by this document.
- The unused endpoints (`/clear-avatars`, `POST /import-avatar` OBJ, `/patterns/{i}/bbox`, `/patterns/{i}/input`) could be pruned from the plugin surface as housekeeping, independent of the CLO-vs-inhouse question.

---

## Could not verify

- **CLO-SET API V2 full endpoint list** (`closetapiv2.docs.apiary.io`) — returned HTTP 502 on fetch; only the landing-page summary at `style.clo-set.com/docs/closetapi` was readable. It is possible V2 has capabilities beyond what the landing page describes, though the landing page's framing ("upload/download... retrieve information") is consistent with a storage API, not a compute API.
- **Whether `/arrange-pattern`, `/set-fabric*` map to specific documented SDK/Python functions by name** — plausible CLO equivalents exist (pattern placement and fabric/material APIs are known CLO feature areas) but neither this pass nor the prior research pass specifically located and quoted the matching `list.html` entries. Marked UNKNOWN rather than assumed.
- **Official PDF SDK guide content** (`CLO_API_SDK_GUIDE_*.pdf`, linked from `support.clo3d.com`) — Flate-compressed, no PDF-extraction tool available in this environment; could contain narrative behavioral documentation beyond the auto-generated header reference, but this could not be confirmed or ruled out.
- **CLO's embedded Python interpreter internals** (CPython version, whether `pip`-installed third-party packages are reachable) — not documented anywhere found.
- **Whether an official standalone CLI/headless executable exists as a distinct product feature** (as opposed to "headless mode" as an internal execution path for specific API calls) — not found in this or the prior research pass; genuinely unresolved, not assumed to be absent beyond "not found publicly."
- **CLO-SET Enterprise plan pricing/tier boundaries** — not stated in the fetched documentation.

---

## Sources

**Official CLO sources:**
- https://developer.clo3d.com/python.html — Python API entry page (official)
- https://developer.clo3d.com/list.html — full function reference, Python + C++ (official)
- https://developer.clo3d.com/optiontype.html — option-struct field lists (official)
- https://developer.clo3d.com/scenario.html — worked Python API examples (official)
- https://developer.clo3d.com/environment.html — plugin build/Qt-version requirements (official)
- https://developer.clo3d.com/changelog.html — full version changelog, Python/headless/API entries (official)
- https://style.clo-set.com/docs/closetapi — CLO-SET API landing/overview page (official)
- https://closetapiv2.docs.apiary.io/ — CLO-SET API V2 reference (official; **fetch failed, HTTP 502, not independently verified this pass**)
- `support.clo3d.com` "CLO API/SDK Guide" (article id 360017616633) — SDK download/version table (official; fetched via curl in prior research, WebFetch returns HTTP 403)
- `support.clo3d.com` "How to use Python Script in CLO?" (article id 115014409267) — official support guidance (fetched via curl in prior research)

**Unverified / could not confirm:**
- Whether an official standalone headless CLI exists as a distinct product (searched 2026-08-29, no CLO-specific result found)
- CLO-SET API V2 full endpoint list (502 on fetch)
- Official PDF SDK guide narrative content (could not extract)

**Repo-internal sources (Mirra's own code, cited as `file:line` throughout):**
- `clo_vto/native_vto/client.py`
- `clo_avatar_generation/avatar_runtime/client.py`
- `clo_workspace/windows/RestPlugin_windows.cpp`
- `clo_workspace/mac/RestPlugin_macOS.cpp`
- `clo_workspace/versions/v_1.1.0.json`, `v_1.1.1.json`, `v_1.3.2.json`
- `clo_workspace/plugin_contract.json`
- `.agent/website-launch-2/12-clo-python-api-research.md` — prior in-repo research this document builds on and re-verifies rather than duplicates
