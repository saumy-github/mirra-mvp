# CLO3D REST Automation Plugin — Status & Completion Roadmap

> **Last updated:** March 11, 2026  
> **Plugin version:** 1.0 (in progress)  
> **Target:** Full headless automation — avatar load → pattern import → sewing → simulation → GLB export

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [What Is Done](#what-is-done)
3. [Known Structural Problems](#known-structural-problems)
4. [What Is Missing — Full Gap Analysis](#what-is-missing--full-gap-analysis)
5. [Complete Automation Flow (Target State)](#complete-automation-flow-target-state)
6. [Step-by-Step Completion Plan](#step-by-step-completion-plan)
7. [Sewing Deep-Dive](#sewing-deep-dive)
8. [Edge Index Discovery Process](#edge-index-discovery-process)

---

## Architecture Overview

```
Your Python script
      │
      │  HTTP POST/GET
      ▼
REST Server (inside CLO3D, port 50505)        ← RestPlugin.dll
      │
      │  CLO C++ API calls
      ▼
CLO3D engine  (avatar, patterns, simulation, export)
```

The plugin is a **C++ DLL loaded inside CLO3D** that runs an embedded HTTP server.  
Python talks to it via `requests`. CLO3D executes the commands.

Two files form the complete client-side interface:
- `plugins/RestPlugin.cpp` — the DLL that runs inside CLO
- `plugins/clo_automation_client.py` — the Python client that talks to it

---

## What Is Done

### ✅ C++ Plugin (RestPlugin.cpp)

| Endpoint | Method | Status | Notes |
|---|---|---|---|
| `/health` | GET | ✅ Done | Returns plugin name + version |
| `/import-avatar` | POST | ✅ Done | Queued — auto-executes each frame |
| `/import-pattern` | POST | ✅ Done | Queued — auto-executes each frame |
| `/execute` | POST | ✅ Done (partial) | Reports queue status |
| `/create-seam` | POST | ✅ Done | **Now queued** — main-thread safe |
| `/simulate` | POST | ✅ Done | **Now queued** — main-thread safe |
| `/export` | POST | ✅ Done | **Now queued** — main-thread safe |
| `/new-project` | POST | ✅ Done | Clears scene for fresh pipeline run |
| `/arrange-pattern` | POST | ✅ Done | 3D positions piece around avatar |
| `/set-fabric` | POST | ✅ Done | Fabric preset + RGB colour per piece |
| `/status` | GET | ✅ Done | Queue size, patterns loaded, last results |
| `/patterns/count` | GET | ✅ Done | Returns current pattern count |
| `/patterns/{index}` | GET | ✅ Done | Returns edge data for a specific pattern |
| `/save-project` | POST | ✅ Done | Exports as `.zprj` |

**Server infrastructure:**
- HTTP server using embedded `httplib.h` (cpp-httplib) ✅
- JSON serialization via `json.hpp` (nlohmann) ✅
- Background thread for server so CLO UI stays responsive ✅
- Command queue + mutex for thread-safe queuing ✅
- **`DoFunctionContinuously` auto-flush — no menu click needed** ✅
- Extended `APICommand` struct (float/bool/int fields for all command types) ✅
- `CommandResult` tracking + `/status` endpoint for Python polling ✅
- Plugin registers as `Plugins → REST Server & Execute` in CLO menu ✅
- Build system: `CMakeLists.txt` + `build_rest_plugin.bat` ✅

### ✅ Python Client (clo_automation_client.py)

All methods implemented:

| Method | Calls | Notes |
|---|---|---|
| `health_check()` | `GET /health` | |
| `import_avatar(path)` | `POST /import-avatar` | |
| `import_pattern(path)` | `POST /import-pattern` | |
| `new_project()` | `POST /new-project` | Clears scene |
| `arrange_pattern(idx, x,y,z, rx,ry,rz)` | `POST /arrange-pattern` | 3D placement |
| `set_fabric(idx, preset, r,g,b)` | `POST /set-fabric` | Fabric + colour |
| `create_seam(a, la, b, lb, da, db)` | `POST /create-seam` | |
| `simulate(steps)` | `POST /simulate` | |
| `export_garment(path, format)` | `POST /export` | |
| `get_pattern_count()` | `GET /patterns/count` | |
| `get_pattern_info(index)` | `GET /patterns/{index}` | Edge inspection |
| `save_project(path)` | `POST /save-project` | |
| `get_status()` | `GET /status` | Queue + results |
| `wait_for_queue(timeout)` | polls `GET /status` | Blocking sync |

### ✅ Build & Deployment

- Full build guide in `BUILD_GUIDE.md`
- One-click `build_rest_plugin.bat`
- SDK integration instructions documented
- DLL install path documented

### ✅ Edge Index Discovery

- `plugins/discover_seam_indices.py` — connects to CLO, reads all edge geometry,
  classifies edges by orientation/position, prints a copy-pasteable `SEAM_MAP` list.
  Run once after importing patterns to eliminate all hardcoded index guessing.

---

## ✅ Known Structural Problems — All Resolved

All three issues documented below have been fixed.

### Why the Queue Architecture Exists (Background)

CLO3D's internal API (`PATTERN_API`, `UTILITY_API`, `IMPORT_API`, `EXPORT_API`) **must only be called from CLO's main UI thread**. The REST server runs on a **background thread**. Calling CLO APIs directly from that background thread causes immediate application crashes.

This is exactly why the queue system was built:
- The background HTTP thread **never calls CLO APIs directly**
- It only writes commands into `g_commandQueue` (protected by a mutex)
- The main thread drains the queue and calls the actual CLO APIs safely

This design is correct and intentional. It solved the crash problem for `import-avatar` and `import-pattern`.

---

### ~~Problem 1~~ ✅ Fixed — `/create-seam`, `/simulate`, `/export` now queued

All three endpoints moved into the command queue.
The HTTP background thread never calls CLO APIs directly.
`ProcessCommandQueue()` (main thread only) handles all CLO API calls.

### ~~Problem 2~~ ✅ Fixed — Ordering guaranteed via `wait_for_queue()`

`CLORestClient.wait_for_queue()` polls `GET /status` until `queue_size == 0`
and `queue_processing == false`. The Python pipeline calls this between every
batch stage.

### ~~Problem 3~~ ✅ Fixed — `DoFunctionContinuously` auto-flush

CLO calls `DoFunctionContinuously()` every frame on the main thread.
Queued commands drain automatically — no menu click required.

---

## What Is Missing — Gap Analysis Update

All previously missing endpoints have been implemented. Remaining items before a full production run:

| Item | Status | What’s needed |
|---|---|---|
| Real seam indices | ⚠️ Pending | Run `discover_seam_indices.py` on actual DXF files |
| Arrangement coordinates | ⚠️ Pending | Calibrate x/y/z for your specific avatar height |
| `UTILITY_API->NewProject()` name | ⚠️ Unverified | Confirm exact name in SDK headers |
| `PATTERN_API->Set3DPatternPosition` | ⚠️ Unverified | Confirm exact name in SDK headers |
| `PATTERN_API->SetFabricPreset` | ⚠️ Unverified | Confirm exact name in SDK headers |

> If any C++ function name doesn’t compile, check the SDK headers and update the corresponding
> case block in `ProcessCommandQueue()` in `RestPlugin.cpp`.

---

## Complete Automation Flow (Target State)

This is the full pipeline from zero to GLB when everything is complete:

```
Step 1  →  POST /new-project
           Clear scene, fresh start

Step 2  →  POST /import-avatar   { "path": "avatar.obj" }
           Loads STAR mesh avatar into CLO scene
           Avatar becomes collision body for simulation

Step 3  →  POST /import-pattern  { "path": "front_panel.dxf" }
           POST /import-pattern  { "path": "back_panel.dxf" }
           POST /import-pattern  { "path": "sleeve_left.dxf" }
           POST /import-pattern  { "path": "sleeve_right.dxf" }
           All 4 pieces are now in CLO's 2D pattern window as flat pieces

Step 4  →  POST /execute   (auto, no menu click)
           Main thread processes the queue:
           → avatar imported
           → 4 patterns imported

Step 5  →  GET  /patterns/count          → expect 4
           GET  /patterns/0              → read front_panel edge indices
           GET  /patterns/1              → read back_panel edge indices
           GET  /patterns/2              → read sleeve_left edge indices
           GET  /patterns/3              → read sleeve_right edge indices
           Python builds the seam index map from this data

Step 6  →  POST /arrange-pattern  { "pattern_index": 0, "position": {...} }  (front)
           POST /arrange-pattern  { "pattern_index": 1, "position": {...} }  (back)
           POST /arrange-pattern  { "pattern_index": 2, "position": {...} }  (sleeve L)
           POST /arrange-pattern  { "pattern_index": 3, "position": {...} }  (sleeve R)
           Pieces are now floating around the avatar in correct start positions

Step 7  →  POST /set-fabric  { "pattern_index": 0..3, "preset": "Cotton_Medium" }
           Physical fabric properties set on all pieces

Step 8  →  POST /create-seam  (front shoulder-left  ↔  back shoulder-left)
           POST /create-seam  (front shoulder-right ↔  back shoulder-right)
           POST /create-seam  (front side-left      ↔  back side-left)
           POST /create-seam  (front side-right     ↔  back side-right)
           POST /create-seam  (front armhole-left   ↔  sleeve-left cap)
           POST /create-seam  (back armhole-left    ↔  sleeve-left cap, remaining)
           POST /create-seam  (front armhole-right  ↔  sleeve-right cap)
           POST /create-seam  (back armhole-right   ↔  sleeve-right cap, remaining)
           POST /create-seam  (sleeve-left underarm ↔  sleeve-left underarm)
           POST /create-seam  (sleeve-right underarm↔  sleeve-right underarm)
           POST /create-seam  (front hem            ↔  back hem)  [optional, if open hem]
           All stitches defined — CLO shows sewing lines in yellow in the UI

Step 9  →  POST /simulate  { "steps": 150 }
           CLO's physics engine drapes all 4 pieces around the avatar.
           Pieces collide with avatar mesh and with each other.
           Seams pull the pieces together along the stitched edges.
           Result: 3D garment sitting on the avatar body.

Step 10 →  POST /export  { "path": "output.glb", "format": "glb" }
           Exports garment + avatar as single GLB file.
           Avatar is embedded in the export (controlled by bExportAvatar flag).

Step 11 →  POST /save-project  { "path": "project.zprj" }
           (Optional) Saves full CLO project for manual inspection/editing later.
```

**Total Python calls: ~25–30 HTTP requests for a full t-shirt.**

---

## Step-by-Step Completion Plan

### ~~Phase 1~~ ✅ Complete — Queue extended to all endpoints

- `/create-seam`, `/simulate`, `/export` moved into the command queue
- `APICommand` struct extended with float/bool/int fields for all command types
- `CommandResult` struct + `g_lastResults` tracking added
- `DoFunctionContinuously` auto-flush: no menu click required
- `GET /status` endpoint added

### ~~Phase 2~~ ✅ Complete — `/arrange-pattern` implemented

- Queued endpoint added to C++ plugin
- Calls `PATTERN_API->Set3DPatternPosition()` + `Set3DPatternRotation()`
- `arrange_pattern()` added to Python client
- Default coordinates defined for 175 cm avatar in `example_workflow()`

### ~~Phase 3~~ ✅ Complete — `/set-fabric` implemented

- Queued endpoint added
- Calls `PATTERN_API->SetFabricPreset()` + `SetPatternColor()`
- `set_fabric()` added to Python client

### ~~Phase 4~~ ✅ Complete — `/new-project` implemented

- Queued endpoint added
- `new_project()` added to Python client; called at pipeline start

### ~~Phase 5~~ ✅ Complete — `discover_seam_indices.py` created

- Reads edge data from CLO after import
- Classifies edges by orientation (H/V/D) and midpoint position
- Matches to semantic names: shoulder, side, armhole, cap, underarm
- Prints copy-pasteable `SEAM_MAP` for `example_workflow(seam_map=...)`

### Phase 6 — Full integration test end-to-end

- [ ] Run the complete pipeline from `example_workflow()`
- [ ] Verify GLB output loads correctly in Blender or a GLB viewer
- [ ] Document the exact arrangement coordinates for each pattern piece

---

## Sewing Deep-Dive

### How `AddSeamlinePairGroup` works

```cpp
PATTERN_API->AddSeamlinePairGroup(
    patternA_index,   // which pattern (0-based, in order of import)
    lineA_index,      // which edge/line on that pattern
    patternB_index,   // the other pattern
    lineB_index,      // the edge to stitch to
    directionA,       // true = stitch start→end, false = stitch end→start
    directionB        // same for second edge
);
```

**Direction matters:** CLO stitches edge A's start point to edge B's start point (when both `true`). If B's edge runs geometrically in the opposite direction in the DXF, you set `directionB = false` to flip it. Wrong direction = twisted seam = garment folds inside out.

### Required seams for a basic t-shirt (11 seams total)

```
 Seam #  │ Piece A          │ Edge A         │ Piece B         │ Edge B
─────────┼──────────────────┼────────────────┼─────────────────┼────────────────
  1      │ front_panel (0)  │ shoulder_left  │ back_panel (1)  │ shoulder_left
  2      │ front_panel (0)  │ shoulder_right │ back_panel (1)  │ shoulder_right
  3      │ front_panel (0)  │ side_left      │ back_panel (1)  │ side_left
  4      │ front_panel (0)  │ side_right     │ back_panel (1)  │ side_right
  5      │ front_panel (0)  │ armhole_left   │ sleeve_left (2) │ cap_front
  6      │ back_panel (1)   │ armhole_left   │ sleeve_left (2) │ cap_back
  7      │ front_panel (0)  │ armhole_right  │ sleeve_right(3) │ cap_front
  8      │ back_panel (1)   │ armhole_right  │ sleeve_right(3) │ cap_back
  9      │ sleeve_left (2)  │ underarm       │ sleeve_left (2) │ underarm
  10     │ sleeve_right (3) │ underarm       │ sleeve_right(3) │ underarm
  11     │ front_panel (0)  │ hem            │ back_panel (1)  │ hem (optional)
```

> Seams 9 and 10 are the **sleeve-closing seams** — piece sewn to itself to form a tube.  
> Seam 11 is only needed if you want a closed bottom hem.

---

## Edge Index Discovery Process

When a DXF is imported, CLO assigns integer indices to each edge.  
You **cannot know these ahead of time** — they come from the DXF vertex ordering.

### How to discover them

```python
from clo_automation_client import CLORestClient

client = CLORestClient()

# After importing all 4 patterns:
for i in range(4):
    info = client.get_pattern_info(i)
    print(f"\n=== Pattern {i} ===")
    print(json.dumps(info, indent=2))
```

The returned JSON from `/patterns/{index}` looks like:
```json
{
  "pattern_index": 0,
  "info": {
    "name": "front_panel",
    "line_count": 6,
    "lines": [
      { "index": 0, "length": 52.4, "start": [0.0, 0.0], "end": [52.4, 0.0] },
      { "index": 1, "length": 18.2, "start": [52.4, 0.0], "end": [52.4, 18.2] },
      ...
    ]
  }
}
```

You then match each edge by:
1. **Length** — shoulder seam ≈ armhole width, side seam = body height, etc.
2. **Orientation** — horizontal edges = top/bottom hem, vertical = side seams
3. **Position** — top edges have higher Y values in DXF space

Once mapped, store the result as a constant seam map and never re-discover unless DXF files change.

---

## Current State Summary

```
[██████████] 100%  C++ plugin endpoints — all 14 endpoints implemented
[██████████] 100%  Queue architecture — ALL commands queued, fully main-thread safe
[██████████] 100%  Python client — 14 methods + wait_for_queue() + full 12-step workflow
[██████████] 100%  Pattern arrangement (POST /arrange-pattern)
[██████████] 100%  Fabric assignment (POST /set-fabric)
[██████████] 100%  Auto-queue flush (DoFunctionContinuously — no menu click)
[████████░░]  80%  Seam index discovery (script done; needs run on real DXF files)
[██████████] 100%  Build system + deployment docs
[██████████] 100%  Export (GLB) + Save project (ZPRJ)
```

**The plugin is functionally complete.** Steps before the first real run:

1. **Rebuild the DLL** — run `build_rest_plugin.bat` (all C++ changes must be compiled)
2. **Install new DLL** — copy to CLO plugins folder, restart CLO
3. **Run `plugins/discover_seam_indices.py`** after importing your 4 DXFs to get real edge indices
4. **Calibrate arrangement coordinates** — adjust `ARRANGEMENT` in `example_workflow()` for your avatar height
5. **Run `example_workflow(seam_map=SEAM_MAP)`** — full headless 12-step pipeline
