# clo_workspace Merge Follow-ups (patterns → saumy)

Written after analyzing the `git merge patterns` conflicts in `clo_workspace/`
(2026-07-23). The 4 marked conflicts (`.gitignore`, `PluginBuildInfo.h`,
`RestPlugin_windows.cpp`, `RestPlugin_macOS.cpp`) are being resolved by hand.
This file lists everything else worth doing **in addition to** resolving the
`<<<<<<<` markers themselves — some of it is not marked as a conflict by git
at all, but needs attention anyway.

---

## Decisions (2026-07-23)

- **Port: 50505.** All 7 locations listed in §1 need to change together
  (both `svr.listen()` calls, all 3 Python client defaults, both message
  strings) — not just the conflicting text.
- **Timer: 200ms.** Matches what's already live on both platforms; only the
  message string needs to be fixed to stop saying 500ms.

---

## 1. Port: 50505 vs 50600 — needs a decision, not just a merge

**Current state (already agreed by both branches, not part of the conflict):**
- `RestPlugin_windows.cpp:1493` — `svr.listen("127.0.0.1", 50600)`
- `RestPlugin_macOS.cpp:1888` — `svr.listen("127.0.0.1", 50600)`
- `clo_avatar_generation/avatar_runtime/client.py:12` — default `http://localhost:50600`
- `clo_avatar_generation/adapters/clo_native_client.py:18` — default `http://localhost:50600`
- `clo_vto/native_vto/client.py:10` — default `http://localhost:50600`
- `clo_vto/native_vto/pipeline.py:122` — displays `http://127.0.0.1:50600`

**Only the DoFunction() message string is in conflict** — HEAD's copy says
`50505`, `patterns`' copy says `50600`. Both are just `DisplayMessageBox` text;
neither changes what port the server actually binds to.

**Relevant history:** `.claude/research/step-1/POST_MORTEM_v1.1.1.md`
documents a real incident on port 50505 — the SEH crashes in v1.1.1
(`/avatars/state`, `ExportAVT`) killed the HTTP server thread, and 50505
stopped accepting connections. **The port number itself was not the bug** —
the crash was. That crash is separately handled now by the Phase 3
`RunCapabilityProbesOnce()` guards on both platforms, independent of which
port is used.

**What this means:** the port was apparently changed to 50600 at some point
after the post-mortem, and that change is already baked into *both* branches'
own commits (yours and your friend's) — this isn't "his branch changed it and
I'm rejecting that," it's "we both moved to 50600 already, and now you want to
move back." That's fine to do, but it's a **functional** change if you want it
everywhere, not just a text fix in the conflict:

- If you only fix the conflicting message string to say `50505`, the server
  will still actually listen on `50600` (line 1493 / 1888, unconflicted) —
  the message would be actively wrong.
- If you want the whole thing on `50505`, all 7 locations above need to
  change together, on both platforms, or client and server will simply fail
  to connect (mundane connection-refused, not a crash).

**Decided: 50505** (see Decisions above). All 7 locations need to change
together, on both platforms — not just the conflicting message string.

---

## 2. Timer interval: 200ms vs 500ms — same kind of decision

**Current state (unconflicted, both branches agree):**
`RestPlugin_windows.cpp:2303` — `SetTimer(NULL, 0, 200, QueueDrainTimer)`.
Comments at lines 423 and 2300 both say "200ms" already.

**Conflicting text:** the `DoFunction()` message conflict also has a second
half — HEAD's string says "200 ms", patterns' says "500 ms". Same situation
as the port: the real `SetTimer` call isn't part of the conflict, and it's
200ms already on both sides.

**Relevant history:** the post-mortem's "What We Tried" section says the team
went **500ms → 200ms → 500ms (reverted)** during the v1.1.1 crash
investigation, and concluded the timer interval had no effect on that crash
(it was unrelated — the SEH exceptions killed the server/CLO outright,
regardless of drain cadence). So as of that incident, 500ms was the "final"
value.

Since then, current code has moved to 200ms again — most likely from the
"Port sync-read architecture to Windows plugin, matching Mac" commit
(`7e52927`), matching Mac's own `QTimer` interval (also 200ms,
`RestPlugin_macOS.cpp:1958`) for cross-platform parity.

**Recommendation:** 200ms looks like a deliberate, later decision (parity
with Mac) rather than a stray leftover — the post-mortem's revert-to-500ms
was about an unrelated crash, not a preference for 500ms specifically. Unless
you have a reason to prefer 500ms, keep 200ms and just fix the conflicting
message string to match.

---

## 3. Two real bugs hiding outside the conflict markers (Windows only)

These aren't marked `<<<<<<<` by git because only one side touched these
lines, but they won't compile / won't behave correctly as currently merged.
Mac does not have either problem — it merged clean.

### 3a. Undefined variable `result` in the fabric handlers

`RestPlugin_windows.cpp` renames the per-command result variable from
`result` to `asyncResult` (see the declaration at the top of
`ProcessCommandQueue`, ~line 1606) — but only on the lines that side actually
touched. The three fabric handlers your friend added
(`set-fabric-color` ~1874, `set-fabric-texture` ~1898, `set-fabric-graphic`
~1918) are new code merged in untouched, and still reference `result.success`
/ `result.message` — a name that no longer exists after the rename. This is
a hard compile error, not a style nit.

**Fix:** rename `result.` → `asyncResult.` in all three fabric handler
blocks (6 occurrences total, 2 per handler).

### 3b. Duplicate `catch (...)` block

`ProcessCommandQueue`'s per-command try block currently has **two**
`catch (...)` handlers back to back (~line 2234 and ~line 2239) — one from
each branch, doing the same job. MSVC will reject this (C2739, duplicate
catch handler for the same type). The second one also still uses
`result.success` / `result.message` (same bug as 3a) and — unlike the
first — never sets `syncResult`, so a sync-read command that throws a
non-`std::exception` would fulfill its promise with an empty/null JSON
instead of an error payload.

**Fix:** merge into a single `catch (...)` block. Keep the more detailed
comment (explains why catching here matters for queue draining), fix the
variable name to `asyncResult`, and keep the `syncResult` assignment so
sync-read callers still get a real error response:

```cpp
catch (const std::exception& e) {
    asyncResult.success = false;
    asyncResult.message = "Exception in '" + cmd.type + "': " + std::string(e.what());
    syncResult = {{"success", false}, {"error", e.what()}};
}
catch (...) {
    // Non-std::exception throw (e.g. a CLO SDK internal type). Record it
    // and keep draining the rest of the batch instead of letting it
    // escape the loop — ReentrancyResetGuard would still reset the flag
    // either way, but catching here keeps subsequent queued commands
    // from being silently dropped along with the crashing one.
    asyncResult.success = false;
    asyncResult.message = "Exception in '" + cmd.type + "': non-standard exception (unknown type)";
    syncResult = {{"success", false}, {"error", "unknown exception — CLO threw a non-std type"}};
}
```

---

## 4. TraceLog coverage: add it to the new fabric endpoints

**Correction (confirmed via `git log` on `patterns`):** `TraceLog` was added
by Anant (commit `96d9be2`, 2026-07-17), not by you — it comes in on the
`patterns` side of the conflict, same commit that added the hardcoded
`C:/Users/Anant/...` path below. Noting this since it was mis-attributed to
"you" earlier in this doc's drafting.

`TraceLog(...)` crash-forensic calls (Windows only,
`RestPlugin_windows.cpp:49`) currently wrap `import-avatar-avt`,
`import-pattern`, and `create-seam` with BEGIN/END markers. The three new
fabric handlers Anant added (`set-fabric-color/texture/graphic`) have none.
Given the whole point of TraceLog is pinpointing exactly which CLO API call
the plugin was inside when it died, these should get the same BEGIN/END
treatment — they call into `FABRIC_API`/`FabricDispatcher`, which is exactly
the kind of CLO SDK surface that's crashed before.

Suggested pattern per handler (matches the existing `create-seam` style):

```cpp
else if (cmd.type == "set-fabric-color") {
    TraceLog("BEGIN set-fabric-color pattern=" + std::to_string(cmd.param3) +
        " rgb=(" + std::to_string((int)cmd.floatParam1) + "," +
        std::to_string((int)cmd.floatParam2) + "," +
        std::to_string((int)cmd.floatParam3) + ")");
    // ... existing guard + dispatch logic, using asyncResult (see 3a) ...
    TraceLog("END   set-fabric-color success=" + std::string(asyncResult.success ? "true" : "false"));
}
```

Same shape for `set-fabric-texture` (log `path=` + `cmd.param1`) and
`set-fabric-graphic` (same).

**One existing issue worth flagging while touching this code:** `TraceLogPath()`
(line 43-47) is hardcoded to `C:/Users/Anant/mirra-mvp/clo_workspace/logs/plugin_crash_trace.log`
— an absolute, machine-specific path (a different collaborator's username),
despite the comment claiming it's "repo-relative." This will silently fail
`create_directories`/write on any other machine (caught by the internal
`catch (...)`, so it fails silent rather than crashing — but you get no log
at all).

**Resolution — finalized (2026-07-23): keep the log inside the repo, not
next to the installed DLL.** Two things confirmed this is the right call
over mirroring `GetCrashDumpDirectory()`:

1. `clo_workspace/` has its own nested `.gitignore` with `logs/*` (only
   `.gitkeep` tracked) — confirmed via `git check-ignore -v
   clo_workspace/logs/plugin_crash_trace.log`. Anything written to
   `clo_workspace/logs/` is already excluded from commits, no new ignore
   rule needed.
2. `GetCrashDumpDirectory()` (line 529) writes *next to wherever CLO
   actually loaded the DLL from* — which per `.env.example`'s
   `CLO_PLUGINS_DIR` is normally under `C:\Program Files\CLO Standalone
   OnlineAuth\plugins`, a UAC-protected folder ordinary processes may not
   be able to write to. Copying that pattern for `TraceLogPath()` risks
   trading one silent-failure mode (wrong hardcoded username) for another
   (permission denied, still silently swallowed by TraceLog's own
   `catch (...)`).

Instead, reuse `build_plugin.py`'s own repo-relative path logic — it
already computes `LOGS_DIR = Path(__file__).resolve().parent / "logs"` at
build time, correctly, on whichever machine runs the build. Bake that into
`PluginBuildInfo.h` (which `build_plugin.py`'s `generate_build_info_header()`
already generates at every build) as one more `#define`:

```python
#define MIRRA_PLUGIN_LOG_DIR "{LOGS_DIR.as_posix()}"
```

Then in `RestPlugin_windows.cpp`:

```cpp
static std::string TraceLogPath()
{
    return std::string(MIRRA_PLUGIN_LOG_DIR) + "/plugin_crash_trace.log";
}
```

Two small edits (one line in `build_plugin.py`, one function body in
`RestPlugin_windows.cpp`), no new WinAPI calls, no Program-Files permission
risk. This still bakes an absolute path into the compiled DLL — but it's
generated fresh by Python from the real filesystem at each person's own
build time, not hand-typed once and forgotten, so it's automatically
correct per machine. Everyone needs to **rebuild** after this change for
their installed plugin to pick up their own correct path — same
"requires next rebuild" caveat as any other plugin source change.

---

## 5. Mac/Windows structural differences relevant to the new fabric feature

The fabric feature (`set-fabric-color/texture/graphic` + `FabricDispatcher`)
already exists on **both** platforms and is structurally consistent — same
`CLOGuard` pattern, same command types, same dispatch-then-report shape. The
one real asymmetry is:

| | Windows | Mac |
|---|---|---|
| Crash-forensic `TraceLog` | Yes (file-based, see §4) | **No — does not exist at all** |
| Reentrancy guard on `ProcessCommandQueue` | Yes (`g_queueProcessing.exchange(true)`) | Yes, already had it (this was the "parity" reference point HEAD's comment cites) |
| Sync-read dispatch (`dispatchSyncRead`) | Yes (added later, matching Mac) | Yes (original design) |
| Capability probing (`RunCapabilityProbesOnce`) | Yes | Yes |

So the only real gap for parity is: **Mac has no equivalent of `TraceLog`.**
Confirmed directly — there is no file-logging function of any kind in
`RestPlugin_macOS.cpp` (no `ofstream`, no log path), and no mention of
`TraceLog`/a Mac port anywhere in the repo's docs. It isn't a deliberate
"do it later" decision on record — it just hasn't been built yet.

> ### TODO (deferred — not part of this merge)
> Port a Mac equivalent of `TraceLog` (same file-append, mutex-protected,
> thread-id + timestamp format, using `GetCrashDumpDirectory()`-style
> module-relative pathing — see §4 — rather than a hardcoded path) and add
> the same BEGIN/END calls into Mac's `set-fabric-*` handlers plus
> `import-avatar-avt` / `import-pattern` / `create-seam`, for parity with
> Windows.
>
> **Do this only after the Windows plugin (this merge, the fabric-handler
> fixes in §3, and the port/timer decisions above) has been checked and
> confirmed working correctly.** No need to duplicate the diagnostic
> machinery onto a second platform before knowing the first one is solid.

---

## Summary of recommended action order

1. ✅ Resolve the 4 marked conflicts by hand.
2. ✅ Push the port (50505) and timer (200ms) decisions to all 7
   non-conflicted locations from §1, and make the `DoFunction()` message
   strings match (also fixed 2 stale "500ms"/"500 ms" comments found during
   the pass, unrelated to the conflict but describing the same timer).
3. ✅ Fix the `result` → `asyncResult` rename in the 3 fabric handlers (§3a).
4. ✅ Merge the duplicate `catch (...)` block (§3b).
5. ✅ Add `TraceLog` BEGIN/END to the 3 fabric handlers on Windows (§4).
6. ✅ Fix `TraceLogPath()`: `#define MIRRA_PLUGIN_LOG_DIR` added to
   `build_plugin.py`'s `generate_build_info_header()` and to the currently
   committed `PluginBuildInfo.h` (as a placeholder for Saumy's machine, so
   the code compiles now — will be correctly regenerated per-machine on
   each person's next real build), `TraceLogPath()` in
   `RestPlugin_windows.cpp` rewritten to use it.
7. ⬜ **Not done — needs a human with the actual build environment:**
   rebuild on Windows via `python clo_workspace/build_plugin.py`, confirm
   the plugin loads in CLO and `/health` responds.
8. ⬜ Separate task, later, only once step 7 is confirmed working: port
   `TraceLog` to Mac for crash-diagnostic parity (§5, tracked as a TODO).

**Bonus finds during implementation (2026-07-23), not originally listed in
this doc:** the manual conflict resolution for `import-avatar-avt`,
`import-pattern`, and `create-seam` had kept *both* sides of those specific
hunks instead of merging them — meaning each of those CLO SDK calls
(`ImportAvatar`, `ImportDXF`, `AddSeamlinePairGroup`) was being invoked
**twice** per request, and the `create-seam` block additionally had a
dangling, unclosed `PATTERN_API->AddSeamlinePairGroup(` fragment sitting in
front of the real call (a hard syntax error, comments and local variables
stuffed inside an open argument list) plus a broken `asyncResult.message =
asyncResult.success` with no ternary continuation. All fixed as part of
this pass — see the diff. Worth double-checking `RestPlugin_macOS.cpp` by
eye too if any further hand-editing happens there, since this class of
"kept both sides" mistake doesn't show up in a `grep` for conflict markers
or stray variable names — it only surfaces on a careful read-through.
