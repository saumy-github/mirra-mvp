# 016 — Versioned Plugin Artifacts & Vault

## Goal

When a developer builds and installs the CLO REST plugin, the installed file should
carry its version number in the filename (`RestPlugin_v1.1.1.dll`) rather than the
generic `RestPlugin.dll`. Older builds are kept in a machine-local vault folder so
the developer can roll back to any previous version without rebuilding.

---

## Background & Constraints

- CLO loads **every DLL** found in its plugins directory. Two versioned DLLs present
  at the same time = two servers fight over port 50505. Only **one** versioned DLL
  may live in the active CLO plugins dir at a time.
- The vault (`CLO_PLUGIN_VAULT_DIR`) is outside the CLO plugins dir so CLO never
  auto-loads from it.
- `CLO_PLUGIN_VAULT_DIR` is a new env key — not hard-coded anywhere in source.
- CMake target name stays `RestPlugin` (produces `RestPlugin.dll`). The rename to
  versioned name happens in Python after the build, not in CMake.

---

## Files to Change

### 1. `clo_workspace/.env.example`

Add `CLO_PLUGIN_VAULT_DIR` to both platform blocks.

Windows block:
```
# Vault — stores every installed build so you can roll back.
# Must be OUTSIDE the repo. CLO never loads from here.
# Only one versioned DLL lives in CLO_PLUGINS_DIR at a time.
# CLO_PLUGIN_VAULT_DIR=C:/Program Files/CLO Standalone OnlineAuth/plugins/mirra-vault
```

macOS block:
```
# CLO_PLUGIN_VAULT_DIR=/Users/yourname/Documents/CLO/Plugins/mirra-vault
```

`.env` (local, gitignored) — user adds the path that matches their OS.

---

### 2. `clo_workspace/build_plugin.py`

**`validate_config`** — read `CLO_PLUGIN_VAULT_DIR` from env into the returned config
dict. Optional (no hard error if absent), but emit a warning when `--install` is used
without it. Also validate that `CLO_PLUGIN_VAULT_DIR`, if set, is **not** inside the
repo root — raise a clear error if it is, to prevent compiled DLLs from being
accidentally committed.

**`versioned_artifact_name(version, platform)`** — new helper that maps:
- `windows` → `RestPlugin_v{version}.dll`
- `mac`     → `libRestPlugin_v{version}.dylib`

Same `_v{version}` suffix pattern on both platforms, different extension only.

**`versioned_plugin_glob(platform)`** — new helper that returns the glob pattern used
to find existing Mirra versioned plugins in a directory:
- `windows` → `RestPlugin_v*.dll`
- `mac`     → `libRestPlugin_v*.dylib`

Used by both `install_artifact` and the note about `switch_plugin.py` to ensure the
pattern is always platform-correct and defined in one place.

**`is_clo_running(platform)`** — new helper. On Windows, checks whether a process
named `CLO Standalone OnlineAuth.exe` (or similar) is running using
`psutil.process_iter()` or a `tasklist` subprocess call. On Mac, checks for the CLO
process via `pgrep`. Returns `True` if CLO is running. Used before any file write to
the plugins dir. If CLO is running, abort with:
`"CLO is running. Close CLO before installing or switching the plugin."`

**`install_artifact(artifact, version_data, config)`** — replaces current
`maybe_install_artifact`. Steps:
1. Derive versioned name using `versioned_artifact_name`.
2. **CLO check**: call `is_clo_running` — abort immediately if CLO is open.
3. **Vault copy**: if `CLO_PLUGIN_VAULT_DIR` is set, create the vault dir if needed,
   copy artifact there as the versioned name. Note: rebuilding the same version
   overwrites the vault entry — always bump the version before a meaningful build.
4. **Active slot copy — safe order**:
   a. Copy the new versioned DLL into `CLO_PLUGINS_DIR` first.
   b. Only after the copy succeeds, delete any other `RestPlugin_v*.dll`
      (or dylib) found in `CLO_PLUGINS_DIR` via `versioned_plugin_glob`.
   This order ensures the plugins dir is never left empty if the copy fails.
5. Log vault path and active slot path.

`version_data` is already available in `main()` — thread it into the install call.

---

### 3. New script: `clo_workspace/scripts/switch_plugin.py`

Purpose: activate a vault version without rebuilding.

**CLI surface:**
```
python clo_workspace/scripts/switch_plugin.py --list
python clo_workspace/scripts/switch_plugin.py --activate 1.1.0
```

Uses `load_env_file`, `versioned_plugin_glob`, and `is_clo_running` helpers from
`build_plugin.py` — import or duplicate as needed. Both `CLO_PLUGINS_DIR` and
`CLO_PLUGIN_VAULT_DIR` must be set or the script exits with a clear message.

**`--list`** output:
- Active version: file matching `versioned_plugin_glob(platform)` in `CLO_PLUGINS_DIR`
  (or "none" if missing).
- Available in vault: sorted list of versioned files in `CLO_PLUGIN_VAULT_DIR`
  matching the same platform glob.

**`--activate <version>`** steps:
1. Confirm `versioned_artifact_name(version, platform)` exists in vault — exit with
   clear error if not.
2. **CLO check**: call `is_clo_running` — abort immediately if CLO is open.
3. **Safe order — copy-then-delete**:
   a. Copy chosen version from vault → `CLO_PLUGINS_DIR` as the versioned name.
   b. Only after the copy succeeds, delete any other files matching
      `versioned_plugin_glob(platform)` in `CLO_PLUGINS_DIR` (skipping the file just
      copied). Does not touch unrelated plugins.
4. Print: active version, path installed to, reminder to restart CLO.

---

### 4. `clo_workspace/scripts/get_installed_plugin_info.py`

**`find_plugin_artifact`** — extend to scan for versioned filenames:
- Current pattern: exact names `RestPlugin.dll`, `libRestPlugin.dylib`, etc.
- New: also glob `RestPlugin_v*.dll` / `libRestPlugin_v*.dylib` in the plugins dir.
- Prefer the versioned match; fall back to unversioned for backward compat.
- If multiple versioned DLLs are found, report all of them (conflict warning).

**Add vault section to output JSON:**
```json
{
  "active": { "path": "...", "version_in_name": "1.1.1", ... },
  "vault": {
    "vault_dir": "...",
    "available_versions": ["1.1.0", "1.1.1"]
  }
}
```

`CLO_PLUGIN_VAULT_DIR` is read from `.env` — if absent, vault section is omitted
from output with a note.

---

### 5. `clo_workspace/README.md`

Add a **"Versioned Builds & Vault"** section under "Local Generated Folders":
- Explain the vault dir, its env key, and that it's machine-local.
- Show the `--list` and `--activate` commands.
- Warn: CLO must be restarted after switching; two versioned DLLs in plugins dir
  at the same time causes a port conflict.

---

### 6. `clo_workspace/mac/RestPlugin_macOS.cpp` — Sync missing endpoints from Windows

Three endpoints exist in Windows v1.1.1 but are absent from the Mac plugin. Add them
using Mac's existing architecture (queue for writes, `dispatchSyncRead` for reads):

**`POST /avatar/set-properties`** (write → queued)
- Parses `{avatar_index, unit, properties}` from request body
- Pushes an `APICommand` of type `"avatar-set-properties"` with the property map in
  `stringMapParam1`
- Mac's `APICommand` struct needs `std::map<std::string, std::string> stringMapParam1`
  added (it's absent on Mac)
- `ProcessCommandQueue` handles it: snapshot before/after, calls
  `UTILITY_API->SetAvatarProperties()`, stores debug state
- Needs `AvatarPropertyDebugState` struct (copy from Windows, same fields)
- Needs `g_avatarPropertyDebugState` global + mutex (copy from Windows)

**`GET /avatar/property-debug`** (read → sync via `dispatchSyncRead`)
- Add `"read-avatar-property-debug"` handler inside `ProcessCommandQueue`
- Returns `BuildAvatarPropertyDebugJson(g_avatarPropertyDebugState)` as syncResult
- Also needs the helper functions: `JsonPrimitiveToString`, `JsonObjectToStringMap`,
  `StringMapToJson`, `StringVectorToJson`, `ComputeChangedPropertyKeys`,
  `ComputeMissingAfterKeys` — copy from Windows (pure C++, no platform dep)

**`POST /avatar/set-properties`** also needs `UTILITY_API->SetAvatarProperties` in
the Mac editor stub. Add to `UtilityAPI` stub block:
```cpp
void SetAvatarProperties(unsigned int, const std::map<std::string, std::string>&) {}
```

**`POST /export-avatar-avt`** (write → queued)
- Parses `{"path": "..."}` from body
- Pushes `APICommand` of type `"export-avatar-avt"` with path in `param1`
- `ProcessCommandQueue` handles it: calls `EXPORT_API->ExportAVT(cmd.param1)`
- Add to `ExportAPI` editor stub block:
  ```cpp
  std::string ExportAVT(const std::string&) { return std::string(); }
  ```

Also update the `/capabilities` response on Mac to add:
```
{"has_avatar_property_set", true},
{"has_avatar_property_debug", true},
{"has_avatar_avt_export", true},
```
(These 3 are currently `false`/absent in the Mac capabilities response.)

---

### 7. Architecture unification — adopt better solution on both platforms

Several design differences exist where one platform made a clearly better choice.
Apply the better solution to whichever platform is behind.

All 5 changes are in `clo_workspace/windows/RestPlugin_windows.cpp` only.

**1. Listen address — change `0.0.0.0` to `127.0.0.1`**

In `StartRESTServer`, the final listen call:
```cpp
// before
svr.listen("0.0.0.0", 50505);
// after
svr.listen("127.0.0.1", 50505);
```

**2. Atomic globals — replace plain `bool` with `std::atomic<bool>`**

Add `#include <atomic>` at the top (already pulled in transitively on Mac; add
explicitly on Windows for clarity).

Replace the two global declarations:
```cpp
// before
bool g_serverRunning = false;
// ... (g_serverThread in between)
bool g_queueProcessing = false;  // inside ProcessCommandQueue scope — actually a local

// after
std::atomic<bool> g_serverRunning{false};
```
Note: `g_queueProcessing` on Windows is a bare global `bool` set inside
`ProcessCommandQueue`. Replace it with `std::atomic<bool> g_queueProcessing{false}`
alongside `g_serverRunning`. All read/write sites are already single-expression
assignments so no other call-site changes are needed.

**3. `/status` pattern count — add `g_patternsLoaded` atomic counter**

Add global next to the other globals:
```cpp
static std::atomic<int> g_patternsLoaded{0};
```

In `ProcessCommandQueue`, inside the `"import-pattern"` branch, after a successful
import set it:
```cpp
if (result.success)
    g_patternsLoaded++;
```

In the `"new-project"` branch, reset it:
```cpp
g_patternsLoaded = 0;
```

In the `/status` HTTP handler, replace the live CLO API call:
```cpp
// before
try { patternsLoaded = PATTERN_API->GetPatternCount(); } catch (...) {}
// after
patternsLoaded = g_patternsLoaded.load();
```
Remove the `int patternsLoaded = 0;` local and use the atomic directly in the
response JSON.

**4. Timer interval — change 500ms to 200ms**

In `DoFunction`, the `SetTimer` call:
```cpp
// before
g_timerId = SetTimer(NULL, 0, 500, QueueDrainTimer);
// after
g_timerId = SetTimer(NULL, 0, 200, QueueDrainTimer);
```

**5. Shutdown — add `PluginShutdown()` + `DllMain DLL_PROCESS_DETACH`**

**Decision**: use a `PluginShutdown()` free function in `RestPlugin_windows.cpp`
(not extern declarations in `dllmain.cpp`). Keeps all plugin state in one file.

In `RestPlugin_windows.cpp`:

Add `static Server* g_server = nullptr;` alongside the other globals.

At the top of `StartRESTServer`, before `Server svr;` is constructed:
```cpp
// svr is a local; store its address so PluginShutdown can call stop().
// Cleared to nullptr before svr is destroyed.
```
At the **very end** of `StartRESTServer`, before the function returns (i.e. after
the listen loop exits and before `svr` goes out of scope):
```cpp
g_server = nullptr;  // svr is about to be destroyed — clear before it goes out of scope
```
Set `g_server = &svr` immediately after `Server svr;` is constructed (not before,
since `svr` doesn't exist yet).

Add the free function after `ProcessCommandQueue`:
```cpp
void PluginShutdown()
{
    g_serverRunning = false;
    if (g_timerId != 0) {
        KillTimer(NULL, g_timerId);
        g_timerId = 0;
    }
    if (g_server != nullptr) {
        g_server->stop();
        // g_server is cleared to nullptr by StartRESTServer before svr is destroyed
    }
}
```

In `clo_workspace/windows/dllmain.cpp`, forward-declare and call it:
```cpp
void PluginShutdown();  // defined in RestPlugin_windows.cpp

// inside DllMain:
case DLL_PROCESS_DETACH:
    PluginShutdown();
    break;
```

`Server` type is from `httplib.h` which is already included in
`RestPlugin_windows.cpp`. No extra includes needed in `dllmain.cpp`.

**Keep platform-specific (mechanism must differ, behavior can align):**

| Difference | Reason to keep separate |
|---|---|
| Queue drain mechanism (Win32 SetTimer vs QTimer) | Windows has no Qt; Mac has no Win32 |
| DoFunction message box on Windows | Windows UX convention; not a correctness issue |

**Larger item — Windows reads on HTTP thread (deferred, not in this plan):**
Mac routes all read operations through `dispatchSyncRead` (promise/future to main
thread). Windows calls CLO read APIs directly from the HTTP thread, which is
technically unsafe. Bringing Windows reads onto the main thread is the right long-term
fix but is a significant rewrite of the Windows read path. Track separately.

---

## What Does NOT Change

- CMake target name (`RestPlugin`) and internal build directory names — untouched.
- `build-local/` situation — this plan does not touch it.
- `.env` structure for `CLO_PLUGINS_DIR` — still required, still the same key.

---

## Rollout / Usage After This Plan

```
# Build and install latest (goes to vault + active slot):
python clo_workspace/build_plugin.py --install

# See what's installed and what's in the vault:
python clo_workspace/scripts/get_installed_plugin_info.py

# List available vault versions:
python clo_workspace/scripts/switch_plugin.py --list

# Roll back to a previous version (then restart CLO):
python clo_workspace/scripts/switch_plugin.py --activate 1.1.0
```

---

## Open Questions

None — all resolved.
