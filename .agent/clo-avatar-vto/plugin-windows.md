# CLO REST Plugin — Windows

**Current version:** v1.1.1 (in_sync)
**Source:** `clo_workspace/windows/RestPlugin_windows.cpp`
**Plugin type:** Windows DLL loaded by CLO
**Server:** `http://0.0.0.0:50505` (all interfaces)
**Status:** Active development target. This is the authoritative implementation — Mac must be brought to parity.

---

## Architecture

The plugin runs as a Windows DLL inside the CLO process. It starts an HTTP server (cpp-httplib) on a background thread. All CLO API calls must run on CLO's main thread, so write operations are queued via a thread-safe command queue (`g_commandQueue`). A Win32 `SetTimer` callback fires every **500ms** on the main thread to drain the queue — no menu click needed after the first invocation.

```
HTTP thread (background)
  → receives POST request
  → pushes APICommand into g_commandQueue (mutex-protected)
  → returns queued confirmation immediately

Main thread (500ms timer)
  → ProcessCommandQueue() drains g_commandQueue
  → executes CLO API calls
  → appends CommandResult to g_lastResults
```

Read-only GET endpoints call CLO APIs directly from the HTTP thread (safe for read-only ops).

---

## Build System

Shared entry point: `clo_workspace/build_plugin.py`
- Reads `.env` for `CLO_SDK_PATH`, `BUILD_CONFIG`, platform
- Generates `shared/PluginBuildInfo.h` with version constants baked in at compile time
- Copies sources to CLO SDK sample directory
- Runs CMake configure + build
- Optionally installs to CLO plugins folder

Build info injected as `#define` constants from `PluginBuildInfo.h`:
- `MIRRA_PLUGIN_NAME`, `MIRRA_PLUGIN_VERSION`, `MIRRA_PLUGIN_API_VERSION`
- `MIRRA_PLUGIN_RELEASE_DATE`, `MIRRA_PLUGIN_RELEASE_STATUS`
- `MIRRA_PLUGIN_PLATFORM`, `MIRRA_PLUGIN_PLATFORM_SYNC_STATE`
- `MIRRA_PLUGIN_CONTRACT_NAME`, `MIRRA_PLUGIN_CONTRACT_VERSION`
- `MIRRA_PLUGIN_BUILD_TIME`

---

## All Endpoints (v1.1.1)

### GET Endpoints (read-only, execute on HTTP thread)

---

#### `GET /health`
Returns plugin identity and build info.

**Response:**
```json
{
  "status": "ok",
  "plugin": "CLO REST Automation",
  "version": "1.1.1",
  "api_version": "v1",
  "release_date": "2026-04-07",
  "release_status": "unstable",
  "platform": "windows",
  "platform_sync_state": "in_sync",
  "contract_name": "...",
  "contract_version": "...",
  "plugin_built_at": "..."
}
```

---

#### `GET /capabilities`
Feature flags for the Python orchestration layer (`client.py`) to decide which apply routes are available.

**Response includes these flags:**
```json
{
  "has_scene_geometry_probe": true,
  "has_pattern_line_count": false,
  "has_pattern_bbox": true,
  "has_pattern_line_length_probe": true,
  "has_pattern_input_info": true,
  "has_arrangement_list": true,
  "has_pattern_arrangements": true,
  "has_avatar_debug": true,
  "has_native_avatar_import": true,
  "has_avatar_measurement_import": true,
  "has_native_avatar_debug": true,
  "has_avatar_property_set": true,
  "has_avatar_property_debug": true,
  "has_avatar_state_readback": true,
  "has_avatar_avt_export": true
}
```
Note: `has_pattern_line_count` is `false` — use `/patterns/{index}/line-lengths` probe instead.

---

#### `GET /status`
Queue state and last batch results.

**Response:**
```json
{
  "queue_size": 0,
  "queue_processing": false,
  "last_results": [
    {"type": "import-avatar-avt", "success": true, "message": "..."}
  ]
}
```

---

#### `GET /debug/import-scales`
Scales used in the last avatar/pattern imports (debugging).

**Response:**
```json
{
  "avatar_import": {"path": "...", "scale": 1.0, "success": true},
  "pattern_imports": [{"path": "...", "scale": 0.1, "success": true}]
}
```

---

#### `GET /avatar/debug`
Avatar + arrangement readiness summary. Computes `avatar_anchor_mode` and `arrangement_semantics_quality`.

**`avatar_anchor_mode` values:**
- `semantic_slots` — avatar loaded + slots populated (best)
- `generic_arrangement_point` — avatar loaded, no slots but pattern arrangements present
- `imported_mesh_avatar` — avatar loaded, no slots
- `none` — no avatar

---

#### `GET /avatar/native-debug`
State of the last native `.avt` import: success flag, last message, arrangement slot count and names, pattern count. Built from `g_nativeAvatarDebugState` (updated when `import-avatar-avt` command runs).

---

#### `GET /avatar/property-debug` ⭐ Windows-only (v1.1.1)
Snapshot of the last `set-properties` operation result. Used to inspect whether the property setter actually changed measurement values.

**Response:**
```json
{
  "success": true,
  "avatar_index": 0,
  "apply_success": true,
  "unit": "cm",
  "requested_properties": {"Total Height": "178"},
  "properties_before": {"Total Height": "170"},
  "properties_after": {"Total Height": "178"},
  "changed_keys": ["Total Height"],
  "missing_after_keys": [],
  "last_message": "..."
}
```

---

#### `GET /avatars/state`
Full avatar list with names, gender, and all CLO property values.

**Response:**
```json
{
  "avatar_count": 1,
  "avatars": [
    {
      "index": 0,
      "name": "Avatar_001",
      "gender_code": 0,
      "gender": "male",
      "properties": {"Total Height": "178", ...}
    }
  ]
}
```

---

#### `GET /patterns/count`
Returns `{"count": N}`.

---

#### `GET /patterns/{index}`
Pattern metadata from `GetPatternInformation(index)`.

---

#### `GET /patterns/{index}/bbox`
Bounding box + area from `GetBoundingBoxOfPattern` + `GetPatternPieceArea`.

---

#### `GET /patterns/{index}/input`
Raw pattern input info from `GetPatternInputInformation`. Returns parsed JSON if valid, raw string otherwise.

---

#### `GET /patterns/{index}/line-lengths`
Probes line lengths sequentially (up to 256, stops after 12 consecutive zero-length lines). Used to count edges when `line_count` is absent from pattern metadata.

Query param: `?max=N` to override 256 limit.

**Response:** `{"line_count": 8, "lines": [{"line_index": 0, "length": 12.4}, ...]}`

---

#### `GET /arrangement-list`
Returns CLO's avatar arrangement slots (`GetArrangementList`). Each slot has an `index` and metadata like `ArrangementName`, `name`, or `description`.

---

#### `GET /pattern-arrangements`
Returns current 3D arrangement state per pattern (`GetArrangementOfPattern` for each pattern index).

---

#### `GET /arrangement/debug`
Combined payload: raw slot list + per-pattern arrangement in one call. Used as fallback when `/arrangement-list` returns empty slots.

---

### POST Endpoints (queued, execute on main thread via timer)

All POST endpoints push an `APICommand` to the queue and return immediately. The 500ms timer drains the queue on CLO's main thread.

---

#### `POST /new-project`
Clears the CLO scene (new project).

**Body:** `{}` (no body required)

**CLO call:** `UTILITY_API->CreateNewProject()`

---

#### `POST /execute`
Returns queue status (does NOT execute manually — the timer drains automatically).

**Response:** `{"queue_size": 0, "queue_processing": false, "message": "..."}`

---

#### `POST /import-avatar`
Import an OBJ mesh avatar.

**Body:** `{"path": "/abs/path/to/avatar.obj", "scale": 1.0}`

**CLO call:** `IMPORT_EXPORT_API->ImportFile(path, scale)`

---

#### `POST /import-avatar-avt`
Import a native CLO avatar template (`.avt` file). This is the primary avatar import used by the Step 1 pipeline.

**Body:** `{"path": "/abs/path/to/avatar.avt"}`

**CLO call:** `IMPORT_EXPORT_API->ImportAvatarFromAVT(path)`

Updates `g_nativeAvatarDebugState` with import success/failure.

---

#### `POST /import-avatar-measurements`
Import measurement CSV into the loaded avatar.

**Body:**
```json
{
  "csv_path": "/abs/path/to/measurements.csv",
  "template_path": ""
}
```

**CLO call:** `IMPORT_EXPORT_API->ImportAvatarMeasurementFromCSV(csv, template)`

**Note:** This route is currently not reliable — see known issues.

---

#### `POST /avatar/set-properties` ⭐ Windows-only (v1.1.1)
Set avatar measurement properties via CLO's property setter API. Experimental route that did not reliably change body measurements.

**Body:**
```json
{
  "avatar_index": 0,
  "unit": "cm",
  "properties": {
    "Total Height": "178",
    "Chest": "98"
  }
}
```

**CLO call:** `UTILITY_API->SetAvatarProperties(index, unit, properties_map)`

Captures before/after state into `g_avatarPropertyDebugState` (readable via `/avatar/property-debug`).

Computed fields in debug state:
- `changed_keys` — properties that changed value
- `missing_after_keys` — properties in request that aren't readable afterward

---

#### `POST /import-pattern`
Import a DXF garment pattern piece.

**Body:** `{"path": "/abs/path/to/front_panel.dxf", "scale": 0.1}`

**CLO call:** `IMPORT_EXPORT_API->ImportFile(path, scale)`

Scale 0.1 = mm DXF → CLO cm scene.

---

#### `POST /arrange-pattern`
Position a pattern piece in 3D around the avatar using a slot index.

**Body:**
```json
{
  "pattern_index": 0,
  "arrangement_index": 5,
  "orientation": 0,
  "position": {"x": 0.0, "y": 0.0, "offset": 100.0}
}
```

**CLO call:** `PATTERN_API->SetArrangementOfPattern(pattern_index, slot_index, orientation, x, y, offset)`

---

#### `POST /set-fabric`
Assign a fabric to a pattern piece by CLO fabric library index.

**Body:** `{"pattern_index": 0, "fabric_index": 0}`

**CLO call:** `PATTERN_API->SetFabricOfPattern(pattern_index, fabric_index)`

---

#### `POST /create-seam`
Stitch two pattern edges together.

**Body:**
```json
{
  "patternA_index": 0,
  "lineA_index": 3,
  "patternB_index": 1,
  "lineB_index": 3,
  "directionA": true,
  "directionB": true
}
```

**CLO call:** `PATTERN_API->CreateSewingBetweenTwoPatterns(pA, lA, pB, lB, dA, dB)`

---

#### `POST /simulate`
Run CLO physics simulation.

**Body:** `{"steps": 150}`

**CLO call:** `PATTERN_API->Simulate(steps)`

---

#### `POST /export`
Export the current scene as GLB or GLTF.

**Body:** `{"path": "/abs/path/output.glb", "format": "glb"}`

**CLO call:** `IMPORT_EXPORT_API->ExportFile(path, format)`

---

#### `POST /save-project`
Save the CLO project as `.zprj`.

**Body:** `{"path": "/abs/path/result.zprj", "thumbnail": true}`

**CLO call:** `IMPORT_EXPORT_API->SaveFile(path)` + optional `GenerateThumbnail()`

---

#### `POST /export-avatar-avt` ⭐ Windows-only (v1.1.1)
Export the current loaded avatar as a `.avt` file. Used by Step 1 pipeline to retrieve the avatar after import.

**Body:** `{"path": "/abs/path/result_avatar.avt"}`

**CLO call:** `IMPORT_EXPORT_API->ExportAvatarToAVT(path)`

---

## Windows-only Endpoints (not yet in Mac)

These 3 endpoints were added in v1.1.1 and are currently Windows-only:

| Endpoint | Purpose |
|---|---|
| `GET /avatar/property-debug` | Read result of last `set-properties` call |
| `POST /avatar/set-properties` | Set avatar measurement properties via JSON |
| `POST /export-avatar-avt` | Export loaded avatar to `.avt` file |

The Mac plugin must add all three before the contract marks both platforms as `in_sync`.

---

## Known Issues (v1.1.1)

- **CSV measurement import is unreliable.** Both multi-field and single-field CSV imports via `/import-avatar-measurements` fail consistently. The `has_avatar_measurement_import` capability flag is still `true` but this route is not trusted.
- **`/avatar/set-properties` did not change body measurements.** The property setter API accepts the call and `changed_keys` shows keys that changed string value, but the resulting avatar geometry did not reflect the measurements. This route is kept for future investigation only.
- **AVT patch (done in Python) is the working solution.** The plugin is not involved in the measurement-apply step of the working pipeline — the patched `.avt` is prepared in Python and then imported via `/import-avatar-avt`.
