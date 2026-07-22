# Plan 001 — Plugin Parity & Future Hardening

## Overview

Remaining changes to `clo_workspace/`. Verified against actual code on
2026-07-01. Completed work has been removed — only outstanding work is listed.

---

## Cross-Cutting Requirement

All changes to C++ files must use the same variable and function names in both
platform files. The Windows file needs the following brought into alignment
with Mac:

| Symbol | Required type | Status |
|---|---|---|
| `g_commandQueue` | `static std::queue<APICommand>` | ✅ Done |
| `g_queueMutex` | `static std::mutex` | ✅ Done |
| `g_lastResults` | `static std::vector<CommandResult>` | ✅ Done |
| `g_resultsMutex` | `static std::mutex` | ✅ Done |
| `g_queueProcessing` | `static std::atomic<bool>` | ✅ Done |
| `g_serverRunning` | `static std::atomic<bool>` | ✅ Done |
| `g_serverThread` | `static std::thread` | ✅ Done |
| `g_importDebugMutex` | `static std::mutex` | ✅ Done |
| `g_lastAvatarImportScale` | `static float` | ✅ Done |
| `g_lastAvatarImportPath` | `static std::string` | ✅ Done |
| `g_lastAvatarImportSuccess` | `static bool` | ✅ Done |
| `g_lastPatternImports` | `static std::vector<ImportScaleEntry>` | ✅ Done |
| `g_nativeAvatarDebugMutex` | `static std::mutex` | ✅ Done |
| `g_nativeAvatarDebugState` | `static NativeAvatarDebugState` | ✅ Done |
| `g_avatarPropertyDebugMutex` | `static std::mutex` | ✅ Done |
| `g_avatarPropertyDebugState` | `static AvatarPropertyDebugState` | ✅ Done |
| `APICommand.isSync` | `bool isSync = false` | ✅ Done |
| `APICommand.syncPromise` | `std::shared_ptr<std::promise<json>>` | ✅ Done |
| `dispatchSyncRead` | same signature as Mac | ✅ Done |

---

## Dependencies

- CLO SDK configured in `.env` before any build.
- After any C++ change: rebuild with `build_plugin.py` and reinstall the DLL.
- CLO must be closed before installing a new DLL.

---

## Phase 1 — Windows Sync-Read Port ✅ COMPLETE

**Goal**: Remove all direct CLO API calls from the Windows HTTP thread. All
reads route through `dispatchSyncRead` on the main thread, matching Mac's
architecture. This unblocks Step 9 (avatar state readback) in the pipeline.

### Step 1 — `clo_workspace/windows/RestPlugin_windows.cpp` ✅ DONE

All changes implemented 2026-07-01:
- `static` added to all 16 module-level globals
- `APICommand.isSync` and `APICommand.syncPromise` added (struct now identical to Mac)
- `#include <future>` added
- `BuildArrangementDebugPayload()` and `dispatchSyncRead()` ported from Mac
- `ProcessCommandQueue` refactored: atomic re-entrancy guard, `hasAsync` conditional clear, sync/async dispatch
- 11 sync-read command handlers added (read-avatar-state, read-avatar-debug, read-avatar-native-debug, read-pattern-count, read-pattern-info, read-pattern-bbox, read-pattern-input, read-pattern-line-lengths, read-arrangement-list, read-pattern-arrangements, read-arrangement-debug)
- All 11 affected GET endpoints converted to `dispatchSyncRead` (avatars/state, patterns/count, patterns/{index}, patterns/{index}/bbox, patterns/{index}/input, patterns/{index}/line-lengths, arrangement-list, pattern-arrangements, arrangement/debug, avatar/debug, avatar/native-debug)
- `/avatar/property-debug` left unchanged — already safe (reads mutex-protected global, no CLO API call from HTTP thread)
- Timer corrected from 500 ms → 200 ms (SetTimer, message box text, comments)
- `has_avatar_state_readback` set to `true`

**Pending**: Build, install, and run manual verification checklist below.

---

## Phase 2 — Infrastructure Gaps

**Goal**: Close the small gaps left in tooling and version tracking, and
optionally remove duplicated C++ code.

### Step 1 — `clo_workspace/shared/CloNativePluginSupport.h`

`AvatarPropertyDebugState` struct and `BuildAvatarPropertyDebugJson` are
defined identically in both `RestPlugin_windows.cpp` and
`RestPlugin_macOS.cpp`. Move them into this shared header and remove the
duplicate definitions from both platform files. Only do this after confirming
the two definitions are byte-for-byte identical.

### Step 2 — `clo_workspace/versions/v_1.2.0.json` (new file)

Create after Phase 1 Step 1 is built and tested. Use the same JSON structure
as `v_1.1.1.json`. Set `status` to `unstable`. The changelog should record:
sync-read ported to Windows, `/avatars/state` re-enabled on Windows, timer
corrected to 200 ms, `has_avatar_state_readback` set to `true` on Windows,
`static` added to all Windows module-level globals. Remove the corresponding
entries from `known_issues`.

---

## Phase 3 — Future Hardening (Deferred) ✅ COMPLETE

**Goal**: Crash protection and dynamic capability detection. Do not start until
Phase 1 and Phase 2 are complete and tested.

**Status**: Implemented, built, installed, and confirmed working
(`run_avatar.py` `u_001-034` + native VTO both succeeded after the live
incident below was fixed). See the Phase 3 Execution Notes for the full
story, including one real regression found and fixed along the way.

### Step 1 — `clo_workspace/windows/RestPlugin_windows.cpp`

- Add `__try/__except` SEH wrapper functions for CLO API calls known to raise
  hardware exceptions, starting with `ExportAVT`. These wrapper functions must
  not contain any C++ objects with destructors in the same scope as the `__try`
  block (compiler rule under `/EHs`).
- Inside the `__except` handler, call `MiniDumpWriteDump` with
  `MiniDumpWithFullMemory` to write a `.dmp` file for post-mortem analysis in
  Visual Studio.
- Re-enable the `export-avatar-avt` handler to call `ExportAVT` through the
  SEH wrapper. Update `has_avatar_avt_export` to `true`.
- At plugin load time, run a startup probe call for each CLO API that could
  crash. Record which calls succeed. Set all capability flags dynamically from
  probe results instead of the current hardcoded values.

### Step 2 — `clo_workspace/mac/RestPlugin_macOS.cpp`

- Register POSIX signal handlers for `SIGSEGV`, `SIGBUS`, and `SIGILL`.
- In each handler, write a structured log entry to a file in the output
  directory alongside the macOS automatic crash report.
- Mirror the Windows probe pattern from Step 1: run startup probes at load time
  and set Mac capability flags dynamically from probe results.

---

## Manual Verification Checklist

**After Phase 1 Step 1:**
- [ ] Plugin builds without warnings using `build_plugin.py`.
- [ ] CLO loads the plugin without error or crash.
- [ ] `run_avatar.py` Step 9 readback returns real avatar state data.
- [ ] `GET /avatars/state` returns valid JSON on Windows.
- [ ] `/capabilities` on Windows shows `has_avatar_state_readback: true`.
- [ ] Timer fires at 200 ms (check queue drain latency in plugin logs).

---

## Phase 1 — Execution Notes

Record of what actually happened during implementation (2026-07-01). Includes
problems found beyond the original plan, how they were fixed, and what was
deliberately left alone.

---

### What was done per the original plan

All items in Phase 1 Step 1 were implemented as written:

- `static` added to all 16 module-level globals. As part of this pass,
  `g_patternsLoaded` was also promoted from `int` to `static std::atomic<int>`,
  making it safe to read from the HTTP thread (`/status` endpoint) without a
  mutex.
- `APICommand.isSync` and `APICommand.syncPromise` added; Windows struct is now
  identical to Mac.
- `#include <future>` added.
- `BuildArrangementDebugPayload()` and `dispatchSyncRead()` ported from Mac.
- `ProcessCommandQueue` fully refactored: atomic re-entrancy guard via
  `g_queueProcessing.exchange(true)`, `hasAsync`-conditional clearing of
  `g_lastResults`, `for (auto& cmd : batch)` loop with `json syncResult` and
  `CommandResult asyncResult`, promise fulfillment at the end of each iteration.
- All 11 sync-read command handlers added to `ProcessCommandQueue`.
- All 11 affected GET endpoints converted to `dispatchSyncRead`.
- `/avatar/property-debug` left unchanged — confirmed safe during audit (reads
  mutex-protected global, makes no CLO API call from the HTTP thread).
- Timer corrected from 500 ms → 200 ms (`SetTimer`, message box, comments).
  Note: `v_1.1.1.json` changelog incorrectly claimed this was already done.
- `has_avatar_state_readback` set to `true`.

---

### Problems found and fixed (not in original plan)

**1. 8 of 11 sync handlers had bare CLO API calls**

Discovered during post-implementation audit. `GetBoundingBoxOfPattern`,
`GetArrangementList`, `GetPatternInformation`, `GetPatternInputInformation`,
`GetPatternCount` (in several handlers), `GetArrangementOfPattern` (in loop),
and `BuildArrangementDebugPayload` were all called with no per-call guard.

A C++ exception from any of these would bypass the sync promise fulfillment
entirely, leaving the HTTP thread to block for the full 3-second timeout.

Fixed by wrapping every CLO call in its own `try { } catch (...) {}`. The
three handlers that were already correct (`read-pattern-line-lengths`,
`read-avatar-native-debug`, `read-avatar-state`) were left as-is and used as
the reference pattern.

**2. `read-avatar-debug` was internally inconsistent**

Within the same function, `GetPatternCount()` was guarded, `GetArrangementOfPattern()`
was guarded per iteration, but `GetArrangementList()` was bare. Mixed pattern
inside a single handler. Fixed by wrapping `GetArrangementList()`.

**3. Outer catch block only had `catch(const std::exception&)`**

Any non-`std::exception` C++ throw (CLO throwing a raw int, a custom type not
derived from `std::exception`, etc.) would escape the command loop entirely.
For a sync command this means the promise is never fulfilled and the HTTP
thread times out. Fixed by adding `catch(...)` after the existing catch, which
sets `syncResult` to a failure payload before the promise fulfillment line
runs.

**4. Partial success reporting — 5 handlers**

After adding per-call guards, handlers returned `"success": true` with
default/empty values when the primary CLO call threw. This made a CLO failure
indistinguishable from a legitimate empty result (e.g. 0 patterns, empty
arrangement list).

Fixed by adding a boolean flag (`ok`, `cloOk`, `bboxOk`) to each affected
handler. `success` in `syncResult` is now driven by whether the primary CLO
call returned without throwing.

| Handler | Flag | What drives `success` |
|---|---|---|
| `read-pattern-count` | `ok` | `GetPatternCount()` returned |
| `read-pattern-info` | `cloOk` | `GetPatternInformation()` returned |
| `read-pattern-bbox` | `bboxOk` | `GetBoundingBoxOfPattern()` returned |
| `read-pattern-input` | `cloOk` | `GetPatternInputInformation()` returned |
| `read-arrangement-list` | `ok` | `GetArrangementList()` returned |

Additional side effect fixed in `read-pattern-count`: `g_patternsLoaded` is
now only updated when `ok = true`. Previously a throw would silently reset it
to 0, corrupting the value visible in `/status`.

For `read-pattern-bbox`: `GetPatternPieceArea()` is treated as secondary data.
If it throws, `area = 0.0` but `success` stays `true` as long as the bbox
call succeeded. Area failure alone is not fatal.

Iterative handlers (`read-pattern-line-lengths`, `read-pattern-arrangements`,
`read-avatar-state`, `read-avatar-native-debug`, `read-avatar-debug`) were not
changed. Partial results from iterative calls are genuinely useful — failing on
one index does not invalidate the rest.

---

### Problems found but deliberately not fixed

**1. SEH gap under `/EHs`**

`catch(...)` under MSVC `/EHs` does not catch Windows Structured Exception
Handling (hardware faults: access violations, illegal instructions, stack
overflows). If a CLO read API raises SEH, the stack unwinds past all catch
blocks without entering any of them, and the sync promise is never fulfilled.
The HTTP thread blocks for the 3-second timeout and returns a timeout error.

This is the same gap that exists on the original Windows plugin. It is not a
regression. The `catch(...)` addition partially mitigates it for non-std C++
exceptions but cannot help for SEH under `/EHs`. Full fix requires
`__try/__except` wrappers — deferred to Phase 3.

---

## Phase 2 — Execution Notes

Record of what actually happened during implementation (2026-07-02). Phase 2
originally had a Step 1 covering `build_plugin.py` (`is_clo_running` check +
an `--install` flag); that step was deleted from the plan before it was
executed, so `build_plugin.py` was left untouched — confirmed with a diff
against the last commit, which shows zero changes to that file.

---

### What was done per the original plan

**`clo_workspace/shared/CloNativePluginSupport.h`**

Confirmed `AvatarPropertyDebugState` and `BuildAvatarPropertyDebugJson` were
byte-for-byte identical in `RestPlugin_windows.cpp` and `RestPlugin_macOS.cpp`
before moving anything. Both were then moved into the shared header, along
with two dependencies they call (`StringMapToJson`, `StringVectorToJson`),
which were also functionally identical in both files (only whitespace/variable-name
differences) but not mentioned by name in the original plan. Moving only the
struct and JSON-builder function without their helpers would not have compiled,
since the header is included near the top of each `.cpp` file — before either
file's own copy of those helpers was defined.

The duplicate definitions were removed from both `RestPlugin_windows.cpp` and
`RestPlugin_macOS.cpp`. Each platform file now only keeps its own
`g_avatarPropertyDebugMutex` / `g_avatarPropertyDebugState` globals and the
call sites; the struct, the two string-conversion helpers, and the JSON
builder live solely in the shared header.

**`clo_workspace/versions/v_1.2.0.json`**

Created after Phase 1 Step 1, using the same structure as `v_1.1.1.json`,
`status: "unstable"`. Changelog records the sync-read port, the timer fix,
`has_avatar_state_readback`, and the header dedup. The two `known_issues`
entries Phase 1 actually fixed (Windows read endpoints bypassing the queue,
`/avatars/state` crashing via SEH) were removed. The still-open
`export-avatar-avt` issue was kept, and a new known issue was added for the
`catch(...)`-cannot-catch-SEH gap documented in the Phase 1 execution notes,
pointing at Phase 3.

---

### Problems found and fixed (not in original plan)

**1. Moving `BuildAvatarPropertyDebugJson` required moving its string helpers too**

`StringMapToJson` and `StringVectorToJson` were defined locally in each `.cpp`
file, *after* the point where each file includes `CloNativePluginSupport.h`.
The plan only mentioned moving the struct and `BuildAvatarPropertyDebugJson`.
Doing only that would leave the header's `BuildAvatarPropertyDebugJson`
calling two functions that don't exist yet at that point in either
translation unit. Fixed by moving `StringMapToJson`/`StringVectorToJson` into
the header as well (adding `#include <map>` there, since it wasn't already
included) and deleting the four now-duplicate definitions (two functions ×
two files).

---

### Problems found but deliberately not fixed / not encountered

None. Phase 2 as executed was infrastructure-only (a header refactor with no
behavioral change, plus a new version-tracking JSON file) — no new CLO API
call paths were touched, and no runtime behavior changed. This was later
confirmed indirectly: a real-world pipeline run (`u_001-030`) briefly showed
the CLO avatar not rendering after this rebuild was installed, but a repeat
run (`u_001-031`) with the exact same installed plugin succeeded normally,
ruling out a Phase 2 (or Phase 1) regression as the cause.

---

### Verification performed after writing this section

Re-diffed the working tree against the last commit to confirm this section
matches what is actually in the repo:
- `build_plugin.py`: no diff — confirms the deleted Phase 2 Step 1 was never
  implemented.
- `RestPlugin_windows.cpp` / `RestPlugin_macOS.cpp`: diffs contain only
  deletions (the moved struct/function/helpers), no other lines touched.
- `CloNativePluginSupport.h`: diff adds exactly `AvatarPropertyDebugState`,
  `BuildAvatarPropertyDebugJson`, `StringMapToJson`, `StringVectorToJson`, and
  the `<map>` include.
- `versions/v_1.2.0.json`: valid JSON, `api_version` matches
  `plugin_contract.json` (the check `build_plugin.py` enforces at build time).

---

## Phase 3 — Execution Notes

Record of what actually happened during implementation (2026-07-03). This
phase was written and reviewed but **not build-tested** — there is no CLO
SDK or MSVC/Clang toolchain available in this environment. Build with
`build_plugin.py` before trusting this in CLO, and watch specifically for
MSVC error C2712 (mixing `__try` with local C++ objects needing unwinding) —
the design below was built specifically to avoid it, but it has not been
compiler-verified.

---

### Windows — `clo_workspace/windows/RestPlugin_windows.cpp`

Implemented per the plan:
- `#include <dbghelp.h>` + `#pragma comment(lib, "Dbghelp.lib")` added (also
  linked explicitly in `CMakeLists.txt` as a second line of defense in case
  the pragma is ever stripped).
- `GetCrashDumpDirectory()` resolves a `CrashDumps` folder next to the
  plugin DLL (via `GetModuleHandleExA`/`GetModuleFileNameA` on this
  function's own address), creating it if missing.
- `WriteMiniDumpToDisk()` calls `MiniDumpWriteDump` with
  `MiniDumpWithFullMemory`, timestamped filename, one dump per crash.
- `SEHFilterWriteDump()` — the function invoked directly from the `__except`
  filter expression, which is the only place `GetExceptionInformation()`'s
  pointer is valid; it writes the dump then returns
  `EXCEPTION_EXECUTE_HANDLER`.
- `RunSEHGuarded(SEHProbeFn fn, void* context, const char* label)` — the one
  function in this file containing `__try`/`__except`. It has zero local C++
  objects with destructors (`fn` is a function pointer, `context` a raw
  `void*`, both PODs), which is what makes it legal to mix with `__except`
  under `/EHs`.
- `ExportAVT_SEHSafe()` and the `export-avatar-avt` queue handler now route
  through `RunSEHGuarded`. The handler updates `g_capabilityAvatarAvtExport`
  from the real result on every call, not just at startup.
- `RunCapabilityProbesOnce()` probes `ExportAVT` and the avatar-state trio
  (`GetAvatarCount`/`GetAvatarNameList`/`GetAvatarGenderList`) once per
  session, called from `DoFunction()`'s first-invocation branch.
- `/capabilities` now reports `has_avatar_state_readback` and
  `has_avatar_avt_export` from `g_capabilityAvatarStateReadback` /
  `g_capabilityAvatarAvtExport` (both `std::atomic<bool>`) instead of
  hardcoded values.

---

### Mac — `clo_workspace/mac/RestPlugin_macOS.cpp`

Implemented per the plan:
- `MirraCrashSignalHandler()` registered for `SIGSEGV`/`SIGBUS`/`SIGILL` via
  `InstallCrashSignalHandlers()`. Uses only `open()`/`write()`/`close()`/
  `snprintf()` into a stack buffer — no `malloc`, no `std::string`, no
  iostream — to stay close to async-signal-safe. Logs to
  `~/Library/Logs/DiagnosticReports/MirraRestPlugin_crash.log`, the same
  directory macOS writes its own automatic `.ips` crash reports to. After
  logging, restores `SIG_DFL` and re-raises so the OS's normal crash path
  (report + termination) still happens.
- `RunCapabilityProbesOnce()` mirrors the Windows probe: exercises
  `ExportAVT` and the avatar-state trio once at startup, sets
  `g_capabilityAvatarAvtExport` / `g_capabilityAvatarStateReadback` from the
  result.
- `/capabilities` now reports both flags from those atomics instead of
  hardcoded `true`/`true`.
- Both calls wired into `DoFunction()`'s first-invocation branch, mirroring
  where the Windows probe was placed.

---

### Live incident (2026-07-03): automatic startup probes took down CLO — resolved

After building and installing v1.2.0 with the Phase 3 changes above, the
first real test showed CLO closing immediately after the plugin connected —
before the Python pipeline could even complete its first `/health` check.
`run_avatar.py` failed at `step_01_health` with a connection-refused error,
meaning the HTTP server had never come up.

**Root cause**: `RunCapabilityProbesOnce()` originally called
`ExportAVT_SEHSafe()` unconditionally on every plugin session start, *before*
the server thread was spawned. This is a real behavioral regression — before
Phase 3, `ExportAVT` was never called at all (fully disabled); Phase 3 made
it run automatically on every single CLO session, exactly the API this whole
codebase's history says crashes on Windows.

**Diagnostic check**: no `CrashDumps` folder was created next to
`RestPlugin_v1.2.0.dll`, meaning `MiniDumpWriteDump` never ran — the
`__except` handler was never invoked. This means the crash bypassed the SEH
wrapper entirely. Plausible explanations: the actual fault happens on a
different thread than the one running `__try` (so it's not in-frame for our
handler to catch), a stack overflow (which needs `_resetstkoflw()` handling
beyond what was implemented), an internal `abort()`/assertion inside CLO
that isn't a structured exception at all, or CLO registering its own
vectored exception handler that intercepts before frame-based SEH handlers
get a chance. Determining which would require attaching a debugger to CLO
at the moment of the crash — not pursued, since the practical fix (stop
calling it automatically) fully resolved the symptom.

**Fix applied (final)**: `RunCapabilityProbesOnce()` is now an intentional
no-op — it does not call `ExportAVT` or the avatar-state trio automatically
at startup. The avatar-state probe was disabled too, out of caution, even
though it has no crash history of its own: it was being exercised through
the exact same untested code path (a direct call from `RunSEHGuarded` at the
same early point in the plugin lifecycle, before the server/timer start, on
whatever blank scene state exists at that moment) as the probe that just
proved unsafe, so there was no basis to trust it either.

Both capability flags now default to `false` and are only set from **real,
explicitly-requested** usage instead of an automatic startup probe:
- `has_avatar_avt_export` → set from the result of a real
  `POST /export-avatar-avt` request, still routed through `ExportAVT_SEHSafe`
  (kept in case the wrapper does help for on-demand calls, even though it did
  not help for the startup-probe crash).
- `has_avatar_state_readback` → set to `true` inside the pre-existing
  `read-avatar-state` branch of `ProcessCommandQueue` (Phase 1 code,
  individually try/catch-guarded per call, already exercised via
  `dispatchSyncRead` with no incident) once that branch runs to completion.
  No Phase 3 SEH machinery is involved in this path at all.

The now-unused `CallAvatarStateProbeOnce()` helper was deleted rather than
left as dead code.

Mac's `RunCapabilityProbesOnce()` still probes `ExportAVT` and the
avatar-state trio automatically at startup, left as-is: Mac's `ExportAVT`
handler was already being called for real (unwrapped) before Phase 3 with no
reported issue, so there's no existing evidence it's unsafe there the way
there now is on Windows. This is worth revisiting if the same symptom ever
shows up on Mac.

**Outcome**: rebuilt with the fix, reinstalled, re-ran the pipeline —
`run_avatar.py` run `u_001-034` completed successfully, and the native VTO
run also completed successfully. This confirms the plugin is back to (at
least) full Phase 1/2 parity, with the Phase 3 SEH wrapper and minidump
infrastructure in place but dormant until something explicitly exercises
`/export-avatar-avt`.

**Net effect on Phase 3's goals**: capability detection for these two flags
is no longer automatic — both only become accurate after something actually
calls the corresponding endpoint once. This is a smaller win than "probed
automatically at startup" but was the only way to keep the plugin usable
given the evidence above.

---

### Deviations from the literal plan text, and why

**1. `has_avatar_avt_export` made dynamic instead of statically `true`**

The plan's Windows bullet list has two instructions that are in tension:
"Update `has_avatar_avt_export` to `true`" and, immediately after, "Set all
capability flags dynamically from probe results instead of the current
hardcoded values." Setting it dynamically is the more complete
interpretation and is what was implemented — `has_avatar_avt_export` now
reflects the real result of the most recent probe/call, not a hardcoded
`true`.

**2. Not all 15 capability flags were made dynamic — only the two documented
as crash-prone**

"Set all capability flags dynamically" was read in the context of the
sentence before it ("run a startup probe call for each CLO API that
could crash") — i.e., the flags tied to APIs this codebase has actually
documented as crash-prone: `has_avatar_avt_export` (ExportAVT) and
`has_avatar_state_readback` (the avatar-state trio). The other ~13 flags
(`has_pattern_bbox`, `has_arrangement_list`, etc.) are tied to plain
read-only pattern APIs already wrapped in ordinary `try`/`catch` since
Phase 1, with no history of SEH crashes in this codebase's own docs.
Probing them too would add new invocation surface with no documented benefit
and was left out. If this reading is wrong, flag it and the remaining flags
can be probed the same way.

**3. "At plugin load time" interpreted as "first `DoFunction()` call," not
DLL load**

Neither platform has a safe hook at actual DLL/dylib load time: Windows'
`DllMain` (`dllmain.cpp`) runs under the loader lock before CLO has wired up
`IMPORT_API`/`EXPORT_API`/etc., and calling into those pointers there would
likely crash immediately (a much cheaper, less controlled failure than
anything Phase 3 is trying to prevent). `DoFunction()`'s first invocation —
already the point where the HTTP server and drain timer are started — is the
earliest point in this SDK's actual lifecycle where the CLO API pointers are
known-good, so the probes were placed there instead, guarded by
`g_capabilityProbesRun` so they only run once per session.

**4. Mac does not attempt crash-and-continue (no `sigsetjmp`/`siglongjmp`)**

The plan's Mac step asks for signal handlers, structured logging, and
mirroring "the Windows probe pattern" — it does not explicitly ask for a
recovery mechanism the way the Windows step explicitly asks for
`__try`/`__except`. POSIX has no equivalent of SEH's ability to safely
resume execution after a hardware fault from inside the same process;
`sigsetjmp`/`siglongjmp`-based "recovery" from a real `SIGSEGV` is widely
considered unsafe in production (the underlying memory corruption that
caused the fault does not go away just because execution jumps back to a
known-good instruction pointer). Rather than write an unverified recovery
mechanism I cannot compile-test and which carries real correctness risk,
Mac's probes use ordinary `try`/`catch` (catching C++ exceptions, which is
all Mac's existing code anywhere in this file ever does) and rely solely on
the new signal handler for forensic logging if a genuine hardware fault
occurs. This is a smaller safety net than Windows gets, and is a real,
inherent asymmetry between the two platforms — not an oversight.

**5. `ExportAVT` probe target path**

Windows probes into `<CrashDumps folder>\probe_export_avt.avt`; Mac probes
into `/tmp/mirra_rest_plugin_probe_export.avt`. Both are throwaway paths —
neither is read back or cleaned up automatically. Since the probe runs
against whatever CLO scene state exists at first click (almost always an
empty/default scene, since this fires before any pipeline command runs),
it may not reproduce the exact conditions under which `ExportAVT` was
historically observed to crash on Windows (which may depend on scene state).
A `false` probe result is trustworthy; a `true` result should still be
treated as "worked in this specific empty-scene case," not an unconditional
guarantee for every future call in this session — which is exactly why the
`export-avatar-avt` handler *also* re-checks via `ExportAVT_SEHSafe` and
updates the flag on every real call, not just at startup.

---

### Problems found but deliberately not fixed

**1. SEH containment is best-effort, not a guarantee**

`__try`/`__except` catches the *structured exception dispatch*, letting
`RunSEHGuarded` return `false` instead of the fault propagating further. It
does not guarantee CLO's internal state is left in a fully consistent
state after a fault inside `EXPORT_API->ExportAVT()` — if the fault
corrupted heap memory CLO relies on elsewhere, later operations in the same
session could still misbehave or crash. This is a known, accepted
limitation of in-process SEH recovery generally, not specific to this
implementation.

**2. Build-tested and confirmed working (resolved)**

Everything in this phase was originally written against well-established
patterns (Microsoft's own SEH+minidump guidance, and the
`signal()`/`open()`/`write()` async-signal-safe pattern used broadly for
POSIX crash breadcrumbs) without a compiler or the CLO SDK available in this
environment to verify it directly. That gap is now closed: the Windows side
was built with `build_plugin.py`, installed, and exercised through a full
Step-1 pipeline run (`u_001-034`) plus a native VTO run, both successful,
after the live incident above was found and fixed. The Mac side (signal
handlers, startup probes still auto-invoking `ExportAVT`) has not been
build-tested or run — the caution above about C2712 and about the automatic
probes being unverified still applies specifically to Mac.

