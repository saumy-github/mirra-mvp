# CLO REST Plugin — Mac

**Current version:** v1.1.0 equivalent (platform sync: pending)
**Source:** `clo_workspace/mac/RestPlugin_macOS.cpp`
**Plugin type:** macOS dylib (`libRestPlugin.dylib`) loaded by CLO
**Server:** `http://127.0.0.1:50505` (localhost only)
**Status:** Behind Windows. Mac is missing the 3 endpoints added in v1.1.1. Must be brought to parity before both platforms are marked `in_sync`.

---

## Architecture

Same concept as Windows but with macOS-specific threading mechanisms.

```
HTTP thread (background, cpp-httplib)
  → receives POST request
  → pushes APICommand into g_commandQueue (mutex-protected)
  → returns queued confirmation immediately

Main thread (Qt QTimer, 200ms interval)
  → timer fires → drains g_commandQueue
  → executes CLO API calls
  → appends CommandResult to g_lastResults
```

For read-only GET endpoints: uses `std::promise` / `std::future` pattern to dispatch to the main thread and wait (3-second timeout). This is the key difference from Windows — Mac does not call CLO read APIs directly from the HTTP thread.

**Lifecycle:** `__attribute__((constructor))` and `__attribute__((destructor))` on the dylib handle initialization and clean shutdown.

---

## Build System

**Build entry:** `clo_workspace/build_plugin.py` (shared with Windows)
**Mac wrapper:** `clo_workspace/mac/build_plugin.sh`
**CMake:** `clo_workspace/mac/CMakeLists.txt`

CMake specifics:
- Target: `libRestPlugin.dylib`
- Links Qt5::Core headers only — Qt symbols resolved at runtime from CLO's own Qt5 (`-undefined dynamic_lookup`)
- No explicit Qt5 link target needed since CLO already has Qt loaded

Same `.env`-driven build as Windows: `PLUGIN_PLATFORM=mac`, `CLO_SDK_PATH`, `BUILD_CONFIG`.

---

## Current Endpoints (v1.1.0 parity, 27 total)

### GET Endpoints (15)

These match Windows v1.1.0 but are implemented with promise/future dispatch to main thread.

| Endpoint | Description |
|---|---|
| `GET /health` | Plugin identity, version, build info |
| `GET /capabilities` | Feature flags (see below for what's missing) |
| `GET /status` | Queue state and last batch results |
| `GET /debug/import-scales` | Scales used in last avatar/pattern imports |
| `GET /avatar/debug` | Avatar + arrangement readiness, anchor mode |
| `GET /avatar/native-debug` | State of last `.avt` import |
| `GET /avatars/state` | Full avatar list with names, gender, properties |
| `GET /patterns/count` | Pattern count |
| `GET /patterns/{index}` | Pattern metadata |
| `GET /patterns/{index}/bbox` | Bounding box + area |
| `GET /patterns/{index}/input` | Raw pattern input info |
| `GET /patterns/{index}/line-lengths` | Edge count probe (sequential line length scan) |
| `GET /arrangement-list` | Avatar arrangement slots |
| `GET /pattern-arrangements` | Per-pattern arrangement state |
| `GET /arrangement/debug` | Combined slots + per-pattern arrangement |

### POST Endpoints (12)

| Endpoint | Description |
|---|---|
| `POST /new-project` | Clear CLO scene |
| `POST /execute` | Return queue status (queue drains via QTimer) |
| `POST /import-avatar` | Import OBJ mesh avatar |
| `POST /import-avatar-avt` | Import native `.avt` template |
| `POST /import-avatar-measurements` | Import measurement CSV (unreliable) |
| `POST /import-pattern` | Import DXF pattern piece |
| `POST /arrange-pattern` | Position pattern in 3D using slot index |
| `POST /set-fabric` | Assign fabric by CLO library index |
| `POST /create-seam` | Stitch two pattern edges |
| `POST /simulate` | Run physics simulation |
| `POST /export` | Export GLB/GLTF |
| `POST /save-project` | Save `.zprj` project |

---

## Mac vs Windows: `/capabilities` Differences

The Mac `/capabilities` response is missing the flags for the 3 Windows-only endpoints:

| Capability flag | Windows v1.1.1 | Mac current |
|---|---|---|
| `has_avatar_property_set` | `true` | `false` / missing |
| `has_avatar_property_debug` | `true` | `false` / missing |
| `has_avatar_avt_export` | `true` | `false` / missing |

The Python client (`avatar_runtime/client.py`) reads these flags to decide which apply routes are available. Until Mac adds these, Step 1's AVT export verification won't work on Mac.

---

## What Needs to Be Added to Mac (to reach v1.1.1 parity)

### 1. `GET /avatar/property-debug`
Returns the snapshot of the last `set-properties` operation.

Windows implementation reads from `g_avatarPropertyDebugState` (a global updated when the `avatar-set-properties` command runs). Returns:
- `avatar_index`, `apply_success`, `unit`
- `requested_properties`, `properties_before`, `properties_after`
- `changed_keys` (properties whose value changed)
- `missing_after_keys` (requested properties not readable afterward)
- `last_message`

Mac needs the same `AvatarPropertyDebugState` struct and the `BuildAvatarPropertyDebugJson()` helper.

### 2. `POST /avatar/set-properties`
Sets avatar measurement properties via JSON.

**Request body:**
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

Windows implementation:
1. Reads `properties_before` via `UTILITY_API->GetAvatarProperties(avatar_index)`
2. Converts JSON object → `std::map<std::string, std::string>`
3. Queues `avatar-set-properties` command to main thread
4. Main thread calls `UTILITY_API->SetAvatarProperties(index, unit, map)`
5. Reads `properties_after` from `UTILITY_API->GetAvatarProperties(avatar_index)`
6. Computes `changed_keys` and `missing_after_keys`
7. Saves full debug state to `g_avatarPropertyDebugState`

Mac needs identical command type added to the queue processing switch-case.

### 3. `POST /export-avatar-avt`
Exports the currently loaded avatar as a `.avt` file.

**Request body:** `{"path": "/abs/path/result_avatar.avt"}`

Windows implementation queues `export-avatar-avt` command. Main thread calls:
`IMPORT_EXPORT_API->ExportAvatarToAVT(path)`

Mac needs this command type added to the queue processor.

### 4. Update `/capabilities` flags
After adding the 3 endpoints, set these to `true` in the Mac capabilities response:
- `has_avatar_property_set`
- `has_avatar_property_debug`
- `has_avatar_avt_export`

### 5. Update `PluginBuildInfo.h` at build time
After the update:
- `MIRRA_PLUGIN_VERSION` → `"1.1.1"`
- `MIRRA_PLUGIN_PLATFORM_SYNC_STATE` → `"in_sync"`
- `MIRRA_PLUGIN_RELEASE_DATE` → `"2026-04-07"` (match Windows)

---

## Implementation Notes for Mac Port

### Threading model difference
Windows reads CLO APIs directly from the HTTP thread for GET endpoints.
Mac uses `std::promise` / `std::future` with a 3-second timeout for all CLO reads. Follow the same pattern for the new endpoints:

```cpp
// Example pattern for GET endpoints on Mac
auto promise = std::make_shared<std::promise<json>>();
auto future = promise->get_future();
dispatch_async(dispatch_get_main_thread(), ^{
    // CLO API call here
    promise->set_value(result);
});
if (future.wait_for(std::chrono::seconds(3)) == std::future_status::ready) {
    res.set_content(future.get().dump(), "application/json");
}
```

For POST endpoints: the command queue approach is identical to Windows — push to queue, return immediately, QTimer drains on main thread.

### Global state needed
Add these globals (same as Windows):

```cpp
struct AvatarPropertyDebugState {
    unsigned int avatar_index = 0;
    bool success = false;
    std::string unit = "raw";
    std::string last_message;
    std::map<std::string, std::string> requested_properties;
    std::map<std::string, std::string> properties_before;
    std::map<std::string, std::string> properties_after;
    std::vector<std::string> changed_keys;
    std::vector<std::string> missing_after_keys;
};
std::mutex g_avatarPropertyDebugMutex;
AvatarPropertyDebugState g_avatarPropertyDebugState;
```

### Helper functions to port
Copy directly from `windows/RestPlugin_windows.cpp`:
- `JsonPrimitiveToString()`
- `JsonObjectToStringMap()`
- `StringMapToJson()`
- `StringVectorToJson()`
- `ComputeChangedPropertyKeys()`
- `ComputeMissingAfterKeys()`
- `BuildAvatarPropertyDebugJson()`

---

## Known Issues (Mac, current)

- **CSV measurement import is unreliable** — same as Windows, `/import-avatar-measurements` does not reliably change avatar body shape.
- **`/avatar/set-properties` not yet implemented** — Step 1's property route will always be skipped on Mac until this is added.
- **`/export-avatar-avt` not yet implemented** — Step 1 cannot export the avatar directly on Mac. The project-extract workaround (reading `.avt` from inside the saved `.zprj`) is used instead.
- **Platform sync state is `pending`** — the Python client (`step_01_health.py`) checks `has_native_avatar_import` and `has_avatar_measurement_import` only; it does not currently block on the missing v1.1.1 flags, so Step 1 runs on Mac but skips the property debug and direct AVT export paths.
