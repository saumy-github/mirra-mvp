# Post-Mortem: v1.1.1 Plugin — Avatar Pipeline Failures (runs 017–023)

**Date:** 2026-05-17  
**Affected:** Step-1 avatar generation pipeline (`step_11_save_outputs`, `step_09_readback`)  
**Status:** Resolved

---

## What Was Broken

Every pipeline run from 017 onwards failed at `step_11_save_outputs` with:

```
CLO queue did not drain within 30s. Last status: {
  'success': False,
  'error': 'WinError 10061 No connection could be made because the
            target machine actively refused it'
}
```

Port 50505 was actively refused — meaning the HTTP server had fully stopped listening. Runs 014 and 016 (old plugin) succeeded. The failure started exactly when v1.1.1 was installed.

---

## What We Tried (and Why It Didn't Work)

### 1. Timer interval: 500ms → 200ms → 500ms (reverted)
**Hypothesis:** Faster timer caused re-entrancy or timing issues in the queue drain.  
**Result:** No effect. Run 020 failed identically after reverting to 500ms.  
**Why it was wrong:** The server was already dead before `step_11` even started — nothing to do with drain timing.

### 2. Mac sync changes as suspect
**Hypothesis:** The Mac plugin changes (`RestPlugin_macOS.cpp`) somehow affected Windows behaviour.  
**Result:** Irrelevant. Mac source files are never compiled into the Windows DLL.

### 3. Dual DLL in plugins folder
**Hypothesis:** Both `RestPlugin.dll` and `RestPlugin_v1.1.1.dll` present, causing conflict.  
**Result:** User confirmed only one DLL in the folder. Ruled out.

---

## Root Cause (Two Separate Crashes)

Both failures had the same underlying mechanism: **Windows SEH exceptions from CLO API calls not caught by `catch(std::exception&)` under `/EHs` compilation**.

Under MSVC's default `/EHs` (synchronous exception handling), `catch(...)` and `catch(std::exception&)` do **not** intercept Windows Structured Exception Handling (SEH) exceptions — access violations, null pointer dereferences, etc. These propagate up the call stack unchecked and terminate the thread or process.

### Crash 1: `/avatars/state` — killed the HTTP server thread

Added in v1.1.1. The handler called CLO API directly from the HTTP thread:

```cpp
svr.Get("/avatars/state", [](const Request&, Response& res) {
    try {
        avatarCount = EXPORT_API->GetAvatarCount();     // SEH crash here
        avatarNames = EXPORT_API->GetAvatarNameList();
        // ...
    }
    catch (const std::exception& e) { ... }  // SEH not caught
});
```

`GetAvatarCount()` raised an SEH exception. `catch(const std::exception& e)` did not catch it. The exception propagated out of the httplib request handler and crashed the server thread. Port 50505 stopped listening.

**Evidence:** `readback_measurements.json` showed:
- `get_native_avatar_debug()` → success  
- `get_avatar_property_debug()` → success  
- `get_avatar_state()` → `ConnectionResetError(10054)` — server reset mid-request  
- `get_status()` → `WinError 10061` — server completely gone  

The server died during `step_09`, so by the time `step_11` ran, the port was already dead.

### Crash 2: `ExportAVT` — killed CLO's main thread

Also added in v1.1.1. The `export-avatar-avt` command was processed via the command queue on CLO's main thread:

```cpp
else if (cmd.type == "export-avatar-avt") {
    std::string out = EXPORT_API->ExportAVT(cmd.param1);  // SEH crash here
    // ...
}
// catch(std::exception&) does not catch SEH
```

`ExportAVT()` raised an SEH exception on the CLO main thread. This propagated through `ProcessCommandQueue` → `QueueDrainTimer` (Win32 TIMERPROC callback) → unhandled → CLO crashed. When CLO exits, the HTTP server thread dies with it.

**Evidence:** `save_outputs.json` from run 023 showed:
- `save_project` → queued and drained successfully  
- `export_avatar_avt` → queued successfully, then drain timed out with `WinError 10061`

---

## What Finally Fixed It

### Immediate Python fixes (no rebuild, instant effect)

**`step_09_readback.py`** — Skip the `/avatars/state` call entirely:
```python
# Was: avatar_state = ctx.client.get_avatar_state()
avatar_state = {"success": False, "error": "skipped: unsafe CLO API call from HTTP thread on Windows"}
```

**`step_11_save_outputs.py`** — Disable direct AVT export:
```python
# Was: direct_export_available = bool(ctx.capabilities.get("has_avatar_avt_export"))
direct_export_available = False  # ExportAVT crashes CLO main thread
```

**`step_11_save_outputs.py`** — Catch `TimeoutError` from `wait_for_queue` so `save_outputs.json` is always written (was propagating unhandled, leaving no diagnostic file).

**`step_11_save_outputs.py`** — Use project-extracted AVT (`result_avatar_from_project.avt`) for `verify_avatar_fields` instead of the direct export, since that function requires the binary-header + embedded-zip AVT format.

### Plugin source fixes (staged, require next rebuild)

**`RestPlugin_windows.cpp`** — `/avatars/state` stubbed to return an error without calling CLO API.

**`RestPlugin_windows.cpp`** — `export-avatar-avt` command stubbed to return an error without calling `ExportAVT`.

**`RestPlugin_windows.cpp`** — `has_avatar_avt_export` capability set to `false`.

---

## Rules for Next Time

### 1. Never call CLO API from the HTTP thread on Windows
The HTTP server runs on a background thread. CLO API functions (`EXPORT_API->*`, `UTILITY_API->*`, `PATTERN_API->*`) are not thread-safe and raise SEH exceptions when called off the main thread. `catch(std::exception&)` will **not** save you.

**Safe pattern for reads on Windows:** Cache data on the main thread (e.g., after an import completes) and serve the cached value from the HTTP handler. Do not call CLO API inline in a GET handler.

**Safe pattern for writes on Windows:** Use the command queue — queue the command in the HTTP handler and let `QueueDrainTimer` process it on the main thread.

### 2. SEH exceptions require `/EHa` or `__try/__except` — not `catch(...)`
If you must call CLO API from a non-main thread, wrap with `__try { } __except(EXCEPTION_EXECUTE_HANDLER) { }`. But do not mix `__try/__except` with C++ objects (destructors won't run). Compile with `/EHa` only if you understand the performance implications.

### 3. Test every new CLO API call end-to-end through the pipeline before shipping
A new endpoint that works in isolation can still crash the server mid-pipeline because the API behaves differently depending on CLO's internal state (loaded avatar, loaded project, etc.).

### 4. When adding a new capability, set it to `false` until proven stable
`"has_avatar_avt_export": true` was advertised before `ExportAVT` was confirmed crash-free. If the pipeline sees `true`, it will call it. Default new capabilities to `false` and flip to `true` only after successful end-to-end runs.

### 5. Diagnostic resilience: always write output files before raising
`step_11_save_outputs` was propagating `TimeoutError` before writing `save_outputs.json`, making it impossible to tell whether `save_project` had succeeded or what stage the failure was at. Every step should catch its own errors, write whatever partial data it has, then return `False` — never let an exception skip the output file.

### 6. The server dying mid-pipeline points to an HTTP-thread CLO API call
If the pipeline succeeds through step N but the server is dead by step N+1, look at what step N called. If any call in step N gets `ConnectionResetError (10054)` followed by `WinError 10061`, the server thread crashed inside that request handler.
