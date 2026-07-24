# VTO Pipeline Debugging & Fix Plan — 2026-07-24

Status: **research complete, no code changed yet.** This is a debugging/design
doc for 5 problems in the `clo_vto` native VTO pipeline, written for
decision-making before implementation starts.

**Update (same day, after initial write-up):** the real CLO SDK
(`C:\setup\CLO_SDK_v2025.2.236_WIN\...\CLOAPIInterface\include\*.h`) was
located and checked directly. This confirms several things the first pass of
this doc could only mark as "hypothesis, needs the header" — those sections
have been rewritten below with confirmed signatures and doc comments instead
of guesses. The corrections are significant enough that **Bug 2 now has a
concrete, SDK-confirmed fix path**, not just an investigation plan.

**Explicit non-goals (per instruction — do not touch):** avatar import,
DXF/pattern import + arrangement into slots, and seam/edge index mapping.
All three are confirmed working (avatar imports correctly, panels land in the
correct slots, edge-to-edge seam mapping is correct). Every fix proposed below
is additive — new verification steps and new plugin capabilities — not a
rewrite of any of that working code.

## Methodology / what was and wasn't examined

Examined directly, line-by-line:
- `clo_vto/native_vto/pipeline.py`, `context.py`, `client.py`, `helpers.py`
- `clo_vto/native_vto/step_02_new_project.py`, `step_03_import_avatar.py`,
  `step_09_create_seams.py`, `step_10_simulate.py`, `step_11_export_note.py`,
  `step_12_texture_glb.py`
- `clo_workspace/windows/RestPlugin_windows.cpp` (2349 lines, full read of the
  command-queue dispatcher) and a targeted diff-by-symptom pass over
  `clo_workspace/mac/RestPlugin_macOS.cpp` (confirms every finding below is
  cross-platform, not Windows-specific)
- `clo_avatar_generation/avatar_runtime/logging_setup.py`, `pipeline.py`,
  `run_manifest.py`, `context.py` (the logging system to model VTO's on)
- `.agent/clo-avatar-vto/known-issue-26_7_23.md`,
  `.claude/research/step-1/POST_MORTEM_v1.1.1.md` (prior findings — one of
  which this doc corrects, see Bug 1 below)

**Also examined (added after the initial pass):** the real CLO SDK headers at
`C:\setup\CLO_SDK_v2025.2.236_WIN\CLO_SDK_v2025.2.236_WIN\CLOAPIInterface\include\`
— `UtilityAPIInterface.h`, `ExportAPIInterface.h`, `CloApiData.h`,
`PatternAPIInterface.h`. This repo only ships a **mock/stub** version of
these declarations (`clo_workspace/mac/RestPlugin_macOS.cpp:31-68`, used for
local compilation without the real SDK linked) which returns hardcoded
`false`/empty values and proves nothing about real behavior — the actual
headers above are the ones that matter, and are not part of this repo (they
live in the separate SDK install). Confirmed findings from them are called
out inline below wherever they replace an earlier hypothesis. Everything
else (queue architecture, thread model, what the plugin currently calls and
when) was already confirmed directly from the shipped `.cpp`.

---

## Executive summary — these are not 4 independent bugs

Reading the plugin source end to end shows Bugs 2, 3, and 4 are very likely
**one causal chain**, and Bug 1 is a second, separate instance of a pattern
that already has a documented fix elsewhere in this codebase.

```
Bug 2 (avatar hidden after sewing)
        │  cloth-avatar collision has nothing to collide against
        ▼
Bug 3 (simulate reports success, no visible drape)
        │  patterns never actually move from their post-arrangement flat pose
        ▼
Bug 4 (export = 4 floating curved-but-unsewn panels, no avatar)
```

And separately:

```
Bug 1 (new-project) is the SAME root-cause family as two issues already
found and partially mitigated elsewhere in this repo:
  - "First avatar-gen run after CLO restart produces undersized mesh"
    (known-issue-26_7_23.md) — CLO SDK call returns success before its
    internal work is actually finished.
  - "Step 3 has a stale-scene check after new-project; Step 1 does not"
    (known-issue-26_7_23.md) — new-project's queue-drain is explicitly
    documented as "best-effort only," with no verification of scene state.
```

The single unifying design flaw across all 4 bugs: **every step in this
pipeline treats "the CLO plugin's command queue reported empty" as proof that
CLO's internal engine work is done.** It isn't. The queue only proves the
*command was dequeued and the synchronous SDK call returned*; several CLO SDK
calls (`NewProject()`, and very likely `Simulate()`) either kick off internal
async work that outlives the call, or depend on scene state (avatar
visibility) that nothing currently asserts or verifies. None of the 4 bugs
can be conclusively fixed by "wait longer" alone — each needs a **real
verification signal**, and the good news is the plugin already exposes (or
can cheaply expose) most of what's needed.

---

## Bug 1 — `new-project` doesn't actually reset the CLO scene

### Symptom
Running VTO a second time in the same CLO session shows leftover patterns
from the previous run — confirmed live in
`clo_vto/output/base-1__native_vto_report.json` (2026-07-23T11:29:18Z run):
`step_05_verify_patterns` failed with `"loaded_patterns": 8` when 4 were
expected. The command itself reports success; the failure is silent from the
`new-project` step's own point of view.

### Where
- Python: `clo_vto/native_vto/step_02_new_project.py:1-16`
- Plugin (Windows): `RestPlugin_windows.cpp:1200-1210` (HTTP handler, just
  queues the command) and `:1787-1807` (`ProcessCommandQueue`'s actual
  handler)
- Plugin (macOS): `RestPlugin_macOS.cpp:681-` — identical shape, confirmed
  cross-platform

### Root cause
```cpp
// RestPlugin_windows.cpp:1787
else if (cmd.type == "new-project") {
    UTILITY_API->NewProject();
    g_patternsLoaded = 0;                    // plugin's OWN counter, reset unconditionally
    { /* clear import-debug state */ }
    { /* clear native-avatar-debug state */ }
    { /* clear avatar-property-debug state */ }
    asyncResult.success = true;              // ALWAYS true — NewProject() return value
    asyncResult.message = "New project created";  //   is never even checked
}
```

Two independent problems stack here:

1. **`NewProject()` cannot signal failure at all — confirmed from the real
   SDK header, not the mock stub.** `UtilityAPIInterface.h:334-336`:
   ```cpp
   /// @fn NewProject()
   /// @brief Clear the current garment and begin a new garment
   virtual void NewProject() {}
   ```
   It returns `void`. `asyncResult.success = true` isn't discarding a real
   success/failure signal — there isn't one to discard. This rules out "just
   check the return value" as a fix entirely; the *only* way to know whether
   the clear-and-begin-new-garment actually finished is to read the scene
   back afterward, which is exactly what the fix below does.
2. **`g_patternsLoaded = 0` is the plugin's own bookkeeping variable, not a
   readback from CLO.** It's reset in software regardless of what CLO's
   scene graph actually contains. If `NewProject()` is asynchronous
   internally (teardown happening on a later frame/tick), a pattern import
   queued immediately after could land in a scene that hasn't finished
   clearing — exactly what the 8-vs-4 pattern count run shows.

The Python side already knows this is a race —
`step_02_new_project.py:8-10`'s own comment says so explicitly ("The drain is
best-effort only... this step must never gate on queue drain") — but nothing
downstream of the comment actually verifies the scene is clear. It only
verifies the *command was accepted*.

### Why Step 1 (avatar-gen) doesn't help as a model here
`known-issue-26_7_23.md`'s "Step 3 has a stale-scene check, Step 1 does not"
entry already covers this comparison. Step 3's `step_05_verify_patterns.py`
*does* check pattern count post-import — but only downstream, several steps
after `new-project`, so by the time it fires (if it fires — `use_default_panels`
paths and error branches can skip it) the pipeline has already spent several
steps operating on a dirty scene.

### Correction to a claim in `known-issue-26_7_23.md`
That doc's last entry states `GET /avatars/state` (`GetAvatarCount`) "is the
endpoint disabled on Windows due to the SEH crash documented in
`POST_MORTEM_v1.1.1.md`." **This is no longer true in the current
`RestPlugin_windows.cpp`.** The post-mortem's Crash 1 was calling
`EXPORT_API->GetAvatarCount()` directly from the HTTP thread (SEH exceptions
aren't caught by `catch(std::exception&)`, and the wrong-thread call itself
is the documented "never call CLO API from the HTTP thread" violation). The
*current* code has since been fixed properly:

```cpp
// RestPlugin_windows.cpp:775-779 — HTTP thread, no CLO API call
svr.Get("/avatars/state", [](const Request&, Response& res) {
    json r = dispatchSyncRead("read-avatar-state");   // posts to main-thread queue
    res.set_content(r.dump(), "application/json");
});

// RestPlugin_windows.cpp:2158-2200 — main thread, individually try/catch-guarded
else if (cmd.type == "read-avatar-state") {
    try { avatarCount = EXPORT_API->GetAvatarCount(); } catch (...) {}
    ...
    g_capabilityAvatarStateReadback = true;   // flips true once this has run without crashing
    syncResult = {{"success", true}, {"avatar_count", avatarCount}, {"avatars", avatars}};
}
```

This is the exact same `dispatchSyncRead` main-thread-queue pattern already
used safely for `/patterns/count`, `/patterns/{i}/bbox`, `/arrangement-list`,
etc. It is live, reachable, and exercised (the `g_capabilityAvatarStateReadback`
probe flag proves it has run to completion at least once without SEH). **The
known-issues doc's "structurally can't easily add a check" conclusion for
Step 1 should be revisited** — the capability it assumed was permanently
disabled is not. (Confirm on the next real run that
`capabilities.has_avatar_state_readback` reports `true` before relying on
this — it's probe-gated, so if it has genuinely never fired in the running
CLO session it'll still read `false`.)

### Proposed fix (modular)

**New `CLORestClient` method** (`clo_vto/native_vto/client.py`) — a real
post-condition check, not a timing guess:

```python
def get_scene_object_counts(self) -> dict:
    """Return {'patterns': int, 'avatars': int} from CLO's actual scene state.

    Unlike get_status()['queue_size'], this reads CLO's own object counts —
    proof the scene is clear, not just proof the command queue is empty.
    """
    patterns = self._get("/patterns/count")
    avatars = self._get("/avatars/state")
    return {
        "patterns": patterns.get("count", -1) if patterns.get("success") else -1,
        "avatars": avatars.get("avatar_count", -1) if avatars.get("success") else -1,
    }

def wait_for_scene_clear(self, timeout: float = 10.0, poll_interval: float = 0.3) -> dict:
    """Poll until CLO reports 0 patterns and 0 avatars, or timeout.

    Returns the last-seen counts dict regardless of outcome; caller decides
    whether to retry new_project() or fail loudly.
    """
    deadline = time.time() + timeout
    last = {"patterns": -1, "avatars": -1}
    while time.time() < deadline:
        last = self.get_scene_object_counts()
        if last["patterns"] == 0 and last["avatars"] == 0:
            return last
        time.sleep(poll_interval)
    return last
```

**Rewritten `step_02_new_project.py`** — same "gate on acceptance, not on
drain" philosophy the existing comment already argues for, but now backed by
a real post-condition instead of nothing:

```python
_MAX_ATTEMPTS = 3

def run(ctx):
    print("\n[2] New project ...")
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        ok = print_result(ctx.client.new_project(), f"new-project (attempt {attempt})")
        if not ok:
            return False  # command itself was rejected — real failure, not a race

        try:
            ctx.client.wait_for_queue(timeout=30)
        except Exception as exc:
            print(f"  [WARN] queue drain timed out ({exc}) — checking scene state anyway.")

        counts = ctx.client.wait_for_scene_clear(timeout=10)
        if counts["patterns"] == 0 and counts["avatars"] == 0:
            print(f"  Scene confirmed clear (attempt {attempt}).")
            return True

        print(f"  [WARN] Scene not clear after new-project: {counts} — retrying.")

    print(f"  [FAIL] Scene still not clear after {_MAX_ATTEMPTS} attempts: {counts}")
    return False
```

Notes:
- `counts["patterns"] == -1` (readback itself failed, e.g. probe never fired
  this session) should be treated as "can't verify" — log it distinctly from
  "verified dirty" so a future debugging session doesn't confuse "the check
  didn't run" with "the check ran and found 8 patterns." Recommend a
  3-way return (`clear` / `dirty` / `unverifiable`) rather than a bool, so
  step_02 can decide whether "unverifiable" should still hard-fail or just
  warn — that's a product decision, not a technical one.
- This mirrors the exact shape of the avatar-gen mitigation already proven
  out in `step_11_save_outputs.py:23-31` (settle + structural check +
  bounded retries) — same pattern, applied to a different symptom of the
  same underlying "SDK call finishes before CLO does" class of bug.

---

## Bug 2 — avatar disappears after sewing (only a manual Show-Avatar toggle brings it back)

### Symptom (as reported)
During/after seam creation, the avatar vanishes from the CLO viewport. The
*only* way to bring it back is manually clicking CLO's "Show Avatar" toggle
off then on. Nothing in the automated pipeline does this.

### Confirmed from the real SDK header — this is the exact function the user is manually clicking

`RestPlugin_windows.cpp` and `RestPlugin_macOS.cpp` contain **zero** calls to
anything resembling a visibility setter (confirmed by grep across both files
— no matches). But the real SDK (not the mock stub) does expose one, in
`UtilityAPIInterface.h:446-460`:

```cpp
/// @fn SetShowHideAvatar(bool _bShow)
/// @brief Set all avatars' show/hide status
virtual void SetShowHideAvatar(bool _bShow) {}

/// @fn SetShowHideAvatar(bool _bShow, int _avatarIndex)
/// @brief Set show/hide status of avatar that matches the index
virtual void SetShowHideAvatar(bool _bShow, int _avatarIdex) {}

/// @fn IsShowAvatar(int _avatarIndex)
/// @brief Get show status of avatar that matches the index
/// @return if avatar is shown, return true. if avatar is hidden, return false.
virtual bool IsShowAvatar(int _avatarIndex) { return false; }
```

This is, in all likelihood, the literal function backing CLO's "Show Avatar"
GUI toggle the user is clicking manually. **The plugin has never called it —
not once, in any command handler.** Nothing in the automated pipeline ever
asserts avatar visibility; the only place it gets set is whatever internal
CLO behavior triggers during/after sewing, and nothing corrects it
afterward. This turns Bug 2 from "needs investigation" into "needs one
missing call," modulo one remaining nuance below.

Also confirmed available, worth using defensively: `Refresh3DWindow()`
(`UtilityAPIInterface.h:886-888`, `"Refresh 3D Garment Window"`) — a genuine
forced-repaint call, useful if the issue turns out to be render-cache
staleness rather than the visibility flag itself (see below).

### The one remaining nuance: does `IsShowAvatar` reflect what actually renders?

The user's workaround is to toggle the GUI checkbox **off, then on again** —
not just click "show" once. If the underlying `IsShowAvatar` flag were
simply stuck at `false` after sewing, calling `SetShowHideAvatar(true, idx)`
once should be sufficient. The fact that a real off→on *transition* is
needed suggests one of two variants, and it matters which for how the fix is
written:

- **(a) The flag itself is genuinely `false`** after sewing — a single
  `SetShowHideAvatar(true, idx)` call fixes it, and `IsShowAvatar(idx)` would
  correctly report `false` if you queried it right after sewing (this is
  now cheaply checkable — no longer a guess).
- **(b) The flag still reports `true`, but the renderer isn't honoring it**
  — a stale-render-state bug, and only a real off→on *transition* forces
  CLO to rebuild whatever internal render list it uses. In this case a
  single "make sure it's shown" call would silently no-op (SDK thinks
  nothing changed) and the avatar would stay invisible.

This is now a 10-minute empirical test instead of an open-ended
investigation: call `GET /avatar/visible` (new endpoint, see below) right
after a sewing batch that's known to trigger the bug, before touching
anything else. If it reports `false` → case (a), fix is a single `SetShowHideAvatar(true, idx)`
call. If it reports `true` → case (b), fix must be the off→on pair
regardless of what `IsShowAvatar` says (matching exactly what the user does
by hand), since trusting the flag would be trusting a signal already shown
to be disconnected from the actual render.

### A concrete, related lead already in the code
This exact scene-mutation/render-state class of bug is called out explicitly
by name in the plugin's own comments — worth reading as a serious prior
finding, not a coincidence:

```cpp
// RestPlugin_windows.cpp:1728-1737, in the create-seam handler
// Investigating a hard CLO crash that happens during/after the 10-seam batch
// this pipeline sends. ... A plausible contributor to both the seam-creation
// crash and corrupted seam ordering ("avatar distortion").
```
and, in `ProcessCommandQueue`'s reentrancy-guard comment
(`RestPlugin_windows.cpp:1534-1560`):
```
if a CLO SDK call inside the batch below pumps the Win32 message loop
internally (the same reentrancy class that forced fabric calls off the
timer callback onto PostMessage in the first place), a pending
WM_MIRRA_DRAIN_QUEUE could dispatch and re-enter this function on the
same thread mid-batch.
```

Put together: this team has *already* found that CLO SDK calls made during
sewing/simulation can pump Windows' message loop internally, and that
overlapping/reentrant queue drains during that window were "a plausible
contributor to... 'avatar distortion.'" A reentrancy guard was since added
(it resets `g_queueProcessing` via RAII), which stops two `ProcessCommandQueue()`
calls from executing *simultaneously* — but it does **not** stop the
underlying trigger (an SDK call pumping messages mid-batch) from happening,
it just makes the *second* call a no-op instead of a crash. If avatar
visibility state is sensitive to *when* in that pumped-message window a
redraw/state-sync happens, the guard papering over the crash wouldn't
necessarily paper over a visibility glitch — it would just stop it from also
segfaulting.

### Remaining investigation (much smaller now — one empirical test, not a header hunt)
1. **Reproduce with `TraceLog` + the new `/avatar/visible` readback (below)
   around the exact moment of disappearance.** `TraceLog` already exists and
   is used exactly this way elsewhere (`clo_workspace/logs/plugin_crash_trace.log`,
   per `known-issue-26_7_23.md`'s avatar-gen entry). Add a `TraceLog` line
   immediately before and after every `create-seam` command, and poll
   `IsShowAvatar` right after each one. This settles the (a)-vs-(b) question
   above with a real reading instead of a guess, and also shows whether the
   disappearance correlates with a specific seam index (e.g. the first
   self-seam — sleeve-tube seams are flagged as architecturally different in
   the comment above), all seams collectively, or the first `simulate` call
   instead of sewing itself (worth not assuming the user's own timing
   attribution is pixel-perfect — "while sewing, and that part is almost
   done" leaves room for the actual trigger being the first post-sewing
   action).

### Proposed fix

**New plugin command + readback, same shape as existing 1-arg commands**
(`RestPlugin_windows.cpp`, alongside the other `ProcessCommandQueue` branches):

```cpp
// Write: force avatar visible. Always does the off→on transition (see the
// nuance above) rather than trusting IsShowAvatar's own report, since that
// report may not reflect what's actually rendered.
else if (cmd.type == "ensure-avatar-visible") {
    int avatarIndex = cmd.param3;  // -1 = all avatars, via the 1-arg overload
    if (avatarIndex < 0) {
        UTILITY_API->SetShowHideAvatar(false);
        UTILITY_API->SetShowHideAvatar(true);
    } else {
        UTILITY_API->SetShowHideAvatar(false, avatarIndex);
        UTILITY_API->SetShowHideAvatar(true, avatarIndex);
    }
    UTILITY_API->Refresh3DWindow();   // belt-and-braces against case (b)
    asyncResult.success = true;       // SetShowHideAvatar is void — nothing to check
    asyncResult.message = "Avatar visibility re-asserted (off->on)";
}

// Read (via dispatchSyncRead, same pattern as read-pattern-count):
else if (cmd.type == "read-avatar-visible") {
    int avatarIndex = cmd.param3;
    bool visible = false;
    try { visible = UTILITY_API->IsShowAvatar(avatarIndex); } catch (...) {}
    syncResult = {{"success", true}, {"avatar_index", avatarIndex}, {"visible", visible}};
}
```

Plus the two REST routes (`POST /avatar/ensure-visible`, `GET /avatar/visible`)
following the exact existing patterns for queued writes and `dispatchSyncRead`
gets, respectively. Add a capability probe (`has_avatar_visibility_set`),
following the discipline already used for `has_avatar_avt_export` and
`has_avatar_state_readback` — **default it to `false` until proven crash-free
end-to-end**, per Rule 4 in `POST_MORTEM_v1.1.1.md`. `SetShowHideAvatar`/`IsShowAvatar`
are plain virtuals (not behind the SEH-crash-prone `EXPORT_API` calls that
caused the original post-mortem incident), but Rule 3's discipline — test
end-to-end before trusting it — still applies to any new CLO API call.

**Python side:** call `ensure_avatar_visible()` from `client.py` at the end
of `step_09_create_seams.py` (after the seam queue drains) and once more at
the top of `step_10_simulate.py`, matching exactly what the user does
manually today (toggle after sewing, confirm before simulating). Use the
`/avatar/visible` readback in both places to log the before/after state into
the pipeline report — this turns "avatar was invisible" from something only
discoverable by eyeballing the CLO window into something visible in
`native_vto_report.json` the next time this regresses.

---

## Bug 3 — simulation reports "done" but never actually happens in CLO

### Symptom
`step_10_simulate.py` returns `True`, `wait_for_queue()` doesn't time out —
by every signal this pipeline currently checks, simulation succeeded. But
nothing visibly drapes/moves in CLO.

### Where
- Python: `clo_vto/native_vto/step_10_simulate.py:1-24`
- Plugin: `RestPlugin_windows.cpp:1046-1054` (HTTP handler, queues the
  command) and `:1764-1770` (`ProcessCommandQueue` handler)

### Root cause

```cpp
// RestPlugin_windows.cpp:1765
else if (cmd.type == "simulate") {
    asyncResult.success = UTILITY_API->Simulate((unsigned int)cmd.param3);
    asyncResult.message = asyncResult.success
        ? "Simulation complete (" + std::to_string(cmd.param3) + " steps)"
        : "Simulation failed";
}
```

This is a **single, blocking SDK call**, dispatched on the main thread like
everything else. Confirmed from the real SDK header
(`UtilityAPIInterface.h:493-497`):
```cpp
/// @fn Simulate(unsigned int _steps)
/// @brief Simulate the garment in multi steps. All dynamics properties
///        (time step, CG iteration count, ...) follow the current
///        simulation properties
/// @return if it succeeds, return true.
virtual bool Simulate(unsigned int _steps) { return false; }
```
This is documented as genuinely synchronous — it runs the requested steps
and returns whether *that* succeeded, not a fire-and-forget dispatch. That
shifts the most likely explanation compared to the first pass of this doc:
this is probably **not** the same "async work outlives the call" class as
`NewProject()`. `Simulate()` returning `true` most likely means CLO's cloth
solver genuinely ran 150 steps against whatever was in the scene — the
problem is almost certainly **what was in the scene**, not whether the call
itself completed. A cloth simulation with an invisible/absent collision body
(Bug 2) can still run its steps and report success while visibly draping
onto nothing, or barely moving under gravity alone. This makes fixing Bug 2
first the single highest-leverage move for Bug 3 — there's a real chance
Bug 3 resolves on its own once the avatar is reliably visible before
`Simulate()` runs.

The failure mode this pipeline is built to catch — "command rejected" —
genuinely isn't happening; `Simulate()` is returning `true`. The remaining
gap is entirely on the Python side, which has no way today to distinguish
"simulated onto a real avatar" from "simulated onto nothing":

```python
# step_10_simulate.py:17-23
try:
    ctx.client.wait_for_queue(timeout=300)
    print("     Simulation complete.")
except Exception as exc:
    print(f"  [WARN] Simulation drain timed out: {exc}")
return True   # <-- unconditional, regardless of what actually happened
```

`wait_for_queue()` only proves the command was dequeued — it says nothing
about whether the 150 simulation steps CLO ran actually produced a draped
garment, vs. e.g. simulating against an empty/hidden scene (see Bug 2 — a
cloth solver with no avatar collision body to drape against will still
"succeed" numerically; it just has nothing to settle onto) or a scene where
patterns aren't actually sewn (if Bug 2's mid-sewing disruption also affected
seam registration in a way that doesn't surface as a `create-seam` command
failure).

This is the exact same "queue-empty ≠ CLO-actually-finished" gap as Bug 1,
just manifesting as a different symptom. There's no reason to expect
`Simulate()` behaves any more synchronously under the hood than `NewProject()`
already doesn't.

### Why the obvious "check pattern bbox before/after" idea doesn't work — confirmed, not just suspected
The tempting fix is: read `/patterns/{i}/bbox` before and after simulate,
diff it, fail if unchanged. **Confirmed from the real SDK header that this
will not work as evidence of simulation.** The bbox endpoint is backed by
`PATTERN_API->GetBoundingBoxOfPattern` (`RestPlugin_windows.cpp:1971`), whose
own doc comment (`PatternAPIInterface.h:193-213`) is explicit about what it
returns:
```cpp
/// @fn GetBoundingBoxOfPattern(int _patternIndex)
/// @brief Get BoundingBox Size each width, height which is using pattern index
/// @return Output map string BoundingBox Size width, height; If an error occurs, return infoMap
virtual std::map<std::string, std::string> GetBoundingBoxOfPattern(int _patternIndex) { ... }
```
Only **width and height** — the flat 2D pattern-piece outline used for
DXF-derived metrics, not a 3D world-space post-drape position. A flat
pattern piece's own outline doesn't change shape just because it got draped
in 3D — draping moves/deforms the piece in 3D space, not its 2D pattern
definition. This rules the endpoint out entirely as a simulation-verification
signal; no further empirical check needed to confirm this one.

### Proposed fix (modular) — reuse the export pipeline as the verification signal
The one thing this pipeline can already inspect that unambiguously reflects
post-simulation 3D geometry is **the exported GLB itself** — and
`pygltflib` is already a hard dependency of `step_12_texture_glb.py`. This
gives a verification approach that needs no new, unconfirmed SDK capability:

```python
# New shared helper, e.g. clo_vto/native_vto/glb_inspect.py
def mesh_is_draped(gltf: "GLTF2") -> tuple[bool, str]:
    """Heuristic: does this GLB look like a simulated drape, or 4 flat panels?

    A flat, unsimulated pattern piece is planar — all its vertices lie
    (near-)exactly on one plane. A draped garment is not. Check per-mesh
    vertex-position variance along each mesh's own thinnest axis; a mesh
    that is suspiciously flat (thinnest-axis stddev near zero relative to
    its other two axes) suggests it never got simulated.
    """
    ...  # decode each mesh's POSITION accessor, compute bbox extents per axis,
         # flag meshes whose smallest extent is < ~1% of their largest extent
```

Wire this into **both** `step_10_simulate.py` and `step_11_export_note.py`,
since they need the same signal for different purposes:

- `step_10_simulate.py`: after `wait_for_queue()`, trigger a *throwaway*
  low-cost export (or reuse step_11's real export if reordering steps is
  acceptable — see note below) and call `mesh_is_draped()`. If it comes back
  false, retry `simulate()` once or twice (bounded, like Bug 1's retry
  pattern) before failing loudly instead of returning `True` unconditionally.
- `step_11_export_note.py`: same check, reused as the real "did this export
  actually contain a sewn/draped garment" gate described in Bug 4 below —
  same helper, no duplicated logic.

This turns two silent-success bugs (3 and 4) into one shared, testable
verification primitive, instead of two separate ad-hoc guesses.

**Practical note on ordering:** verifying *during* step_10 requires an
export capability at that point in the pipeline, which today only exists in
step_11. The pragmatic option is to *not* duplicate export logic — instead
make step_10 optimistic (as today) but make **step_11's post-export check
the authoritative gate**, and have step_11 report failure (not silently
return `True`) when `mesh_is_draped()` comes back false, since by that point
CLO's own export has already given us the real 3D geometry to inspect. This
avoids adding a second export call, at the cost of surfacing the "simulation
didn't really run" failure one step later than ideal. Cheaper and — since
it reuses code already required for Bug 4 — arguably the more scalable
choice; flagging both options rather than presupposing which the team
prefers.

---

## Bug 4 — export is 4 floating, curved, correctly-placed-but-unsewn panels, no avatar

### Symptom
The exported `.glb` shows the 4 panels in their correct arranged
positions/orientation around where the avatar should be — confirming
arrangement and slot placement are correct, as already established — but no
avatar mesh is present, and the panels are not stitched/draped together.

### Where
- Python: `clo_vto/native_vto/step_11_export_note.py:1-66`
- Plugin: `RestPlugin_windows.cpp:1772-1785` (`ProcessCommandQueue`'s export
  handler)

### Root cause — this is downstream of Bugs 2 and 3, plus one independent gap

```cpp
// RestPlugin_windows.cpp:1772
else if (cmd.type == "export") {
    bool asGLB = (cmd.param2 == "glb");
    Marvelous::ImportExportOption options;
    options.scale          = 1.0f;
    options.bExportGarment = true;
    options.bExportAvatar  = true;   // <-- requested, but avatar may be hidden (Bug 2)
    options.bEmbedded      = asGLB;
    std::vector<std::string> out = EXPORT_API->ExportGLTF(cmd.param1, options, asGLB);
    asyncResult.success = !out.empty();
    ...
}
```

`bExportAvatar = true` is correctly set — the plugin *is* asking CLO to
include the avatar. The real SDK's `ImportExportOption` struct
(`CloApiData.h:89-202`) does confirm a related, but not identical, concept:
```cpp
EXPORT_PYTHON bool bIncludeHiddenObject;  /// if true, export all the pattern
                                           /// meshes include 'hidden pattern
                                           /// meshes on 3D' to OBJ
// ...constructor default:
bIncludeHiddenObject = false;
```
This confirms CLO's export pipeline **does** have a real, general concept of
"hidden objects get excluded from export unless told otherwise" — and the
plugin never sets this flag, so it's `false` (excluded) by default. However,
read literally, this specific field's doc comment says **pattern** meshes
(garment panels hidden in the 3D view) and **OBJ** export specifically —
not avatars, and not confirmed to apply to `ExportGLTF`. So this is real,
confirmed evidence that CLO's export logic *generally* treats hidden objects
as excluded by default, which makes "a hidden avatar gets excluded from a
GLTF export too" a well-supported inference rather than a bare guess — but
it stops short of being a direct, name-matching confirmation for the avatar
case. **Cheap to settle for real:** once Bug 2's fix lands, set
`options.bIncludeHiddenObject = true` in the `export` handler
(`RestPlugin_windows.cpp:1772-1785`) as a one-line defensive addition
regardless, and separately test one export while the avatar is deliberately
left hidden (`ensure-avatar-visible` not called) to see whether the avatar
appears or not — that single test fully resolves whether this was ever part
of the mechanism for the avatar specifically, independent of whether Bug 2's
fix already made the question moot in practice.

Separately, **Bug 3 fully explains "curved and placed... but not sewn"** —
`AddSeamlinePairGroup` (already run successfully in step 9, per the user)
registers *seam topology* — which edges connect to which — but the actual
3D draping/stitching-together of the pieces into a worn garment shape is
`Simulate()`'s job. If simulate never really executes (Bug 3), the panels
stay in whatever pose `arrange-pattern` put them in — individually
positioned and oriented correctly (which is why they land in the right
*slots* around the avatar), but never pulled together into a sewn 3D shape.
That matches "curved and placed... around the avatar" (arrangement working)
+ "panels not sewn" (simulation not working) exactly.

**The independent gap**, on top of both of the above: `step_11_export_note.py`
only ever checks **file existence and byte size**
(`step_11_export_note.py:50-58`) — never the export's actual contents. A
280KB GLB of 4 flat, unsewn, avatar-less panels passes this check exactly as
cleanly as a correct simulated export would, provided it clears the 1KB
floor. This is the same "trust the surface signal, not the content" gap as
Bugs 1 and 3, just at the export step.

### Proposed fix (modular)
Two independent layers, since this bug has two independent causes:

1. **Fix Bugs 2 and 3 first.** If the avatar is genuinely visible at export
   time and simulation genuinely ran, this bug's symptom should disappear on
   its own without any export-specific code change.
2. **Add real content verification to `step_11_export_note.py` regardless**
   — don't rely on upstream fixes alone holding forever; a regression in
   either upstream step should be caught here too, loudly, not silently.
   Using the same `pygltflib` dependency already available:

```python
# step_11_export_note.py, after the existing size check
from .glb_inspect import mesh_is_draped, count_meshes_by_role  # new helper module

gltf = GLTF2().load(str(glb_path))
mesh_count = len(gltf.meshes)
draped_ok, drape_reason = mesh_is_draped(gltf)

# Heuristic: an avatar + 4 garment panels sewn into a shape typically yields
# fewer, larger, differently-shaped meshes than 4 independent flat panels
# plus zero avatar meshes. Exact expected count needs confirming against a
# known-good manual CLO export as ground truth — don't hardcode a number
# without that reference point.
if mesh_count < ctx.expected_min_export_meshes:  # new ctx field, e.g. default 2
    print(f"  [WARN] Export has only {mesh_count} mesh(es) — avatar mesh may be missing.")
if not draped_ok:
    print(f"  [WARN] Export geometry looks unsimulated: {drape_reason}")
```

Whether these warnings should become hard `return False` failures (matching
the "loud failure over silent success" principle used elsewhere, e.g.
`step_05_verify_patterns.py`'s pattern-count gate) or stay non-blocking
warnings (matching this step's current documented philosophy — "export
failure is logged but never aborts the pipeline") is a product decision. Given
the whole point of this bug report is "it shows done but silently isn't,"
the recommendation is to make this specific check blocking — that is the
actual complaint being fixed — while keeping the *existing* non-blocking
behavior for true infrastructure failures (missing pygltflib, corrupt file,
CLO not reachable).

Get a **known-good reference GLB** (export once from the CLO GUI manually,
with a correctly draped, avatar-visible result) to calibrate the exact
mesh-count / flatness thresholds against, rather than guessing numbers. This
is a 10-minute manual step that turns "heuristic, unverified" into "measured
against ground truth."

---

## Cross-cutting fix — a real logging system for VTO, modeled on avatar-gen's

### Current state
Every VTO step (`helpers.py:16-61` and all 12 `step_*.py` files) uses plain
`print()`. There is:
- No `run.log` file — output only exists in whatever terminal/process
  captured it live. Debugging a run after the fact (exactly what this whole
  document is doing for the 4 bugs above) has nothing to read except the
  final JSON report (`_build_report()` in `pipeline.py:45-74`), which
  captures structured diagnostics but not the narrative step-by-step console
  output.
- No per-run directory. `create_context()` (`context.py:168-171`) uses one
  flat, shared `clo_vto/output/` for every run — contrast with avatar-gen's
  `output/<user_id>-<run_number>/` (`run_manifest.py:30-31`), where every run
  gets its own directory and nothing gets overwritten or conflated between
  runs.
- No structured JSON logging of intermediate state beyond the final report —
  avatar-gen's `ctx.log_json(label, payload)` (`context.py:88-89`, avatar-gen)
  writes labeled JSON snapshots into the run's logger at each major
  milestone; VTO has no equivalent.

### Proposed design — near-identical port of the avatar-gen system

**1. `clo_vto/native_vto/logging_setup.py`** — copy avatar-gen's
`logging_setup.py` almost verbatim; the design (console + `MemoryHandler`
buffer before a run dir exists, flushed into a real `FileHandler` once one
does) already solves VTO's exact chicken-and-egg problem, since VTO's
`step_01_health` also runs before any per-run directory exists today. Only
change: `LOGGER_NAME = "mirra.vto"` instead of `"mirra.step1"`.

**2. Per-run output directories.** Add a `run_manifest.py` analog for VTO —
same shape as avatar-gen's (`RunIdentity`, `get_next_run_number`,
`get_run_dir`), keyed by whatever VTO's natural run identity is (e.g.
avatar-stem + running counter, since VTO runs are per-avatar/per-garment
rather than per-user like Step 1). This is the bigger structural change of
the two — currently `ctx.output_dir` is a single shared directory reused by
every run (`context.py:168`), which means **two runs on the same machine can
race on the same output files**, and there is no way to look back at "what
did last Tuesday's failed run actually produce" once a later run has
overwritten `simulation.glb`, `simulation_textured.glb`, and the pipeline
report at the same paths. Given `output_dir` is threaded through nearly
every step file, migrating this is the single highest-blast-radius change in
this whole document — recommend doing it as its own isolated PR, separate
from the 4 bug fixes above, precisely because of that blast radius.

**3. Wire into `pipeline.py`.** Mirror avatar-gen's `pipeline.py:114-115`
(`ctx.logger = configure_console_logger()` at the very top of `run_pipeline()`)
and the per-step logging already built into avatar-gen's loop
(`pipeline.py:146-160`: `ctx.logger.info("Step %s: starting", ...)` /
`_record_step_result()` logs pass/fail with `ctx.logger.info`/`.error`). VTO's
`pipeline.py` loop (`pipeline.py:274-294`) already does the structural
equivalent with `print()` and `step_results.append(...)` — the refactor is
mostly swapping `print` for `ctx.logger.info`/`.error` at the same call
sites, not a new design.

**4. Migration path for the ~80 existing `print()` calls across step files.**
Given the volume, a phased approach is more scalable than a single
big-bang rewrite:

- **Phase A (low-effort, immediate parity):** keep every existing `print()`
  call as-is, but have `helpers.py:step_header`/`step_footer`/`print_result`
  — the 3 functions already funneling nearly all step output — also write
  through to `ctx.logger` (requires threading `ctx` into these helpers,
  which they don't currently take). This alone captures the large majority
  of output into `run.log` with a minimal-diff change, since most step files
  route their prints through these 3 helpers already.
- **Phase B (full parity):** migrate the remaining bare `print()` calls
  (mostly `[WARN]`/`[OK]`/`[FAIL]` inline lines inside step bodies, e.g.
  `step_02_new_project.py:15`, `step_10_simulate.py:22`) to `ctx.logger.warning`/
  `.info` directly, matching avatar-gen's convention of `logger.error` for
  failures rather than plain warn-level text.

Recommend Phase A only for this round — it directly serves every bug fix
above (all of them benefit from a persisted `run.log` to debug against next
time) without taking on the full-file migration and the per-run-directory
change in the same pass.

---

## Cross-cutting principle tying all 5 items together

The plugin's own C++ code already demonstrates the right discipline in
places the Python pipeline doesn't yet follow: **capability probes that
default to `false` until proven safe** (`g_capabilityAvatarStateReadback`,
`g_capabilityAvatarAvtExport`, both gated behind "not hardcoded... only set
from a real request," per `RestPlugin_windows.cpp:644-651`), and **loud,
structured failure over silent success** where it's been applied (`create-seam`'s
`fail_count` gate in `step_09_create_seams.py:107-109`,
`step_05_verify_patterns.py`'s pattern-count check). Every fix proposed above
is really just extending that same discipline to the 4 places it's currently
missing: new-project, avatar visibility, simulate, and export. None of these
fixes require new architecture — they require **verifying a real
post-condition instead of trusting a queue-drain or a hardcoded `true`**,
using signals the plugin either already exposes (`/patterns/count`,
`/avatars/state`) or can cheaply add following the exact probe pattern
already established for the two capabilities named above.

---

## New open issue found during implementation — scene-clear verification (Bug 1's fix) is itself unreliable, gate disabled

Status: **open, not fixed. Bug 1's verification gate has been made
non-blocking (warn + proceed) rather than removed, so the pipeline isn't
stuck failing every run while this is unresolved.**

## What happened

Implemented Bug 1's fix (`step_02_new_project.py` polling `/patterns/count` +
`/avatars/state` via `client.py`'s `get_scene_object_counts()`), then tested
against a live CLO instance. Two consecutive runs, fresh CLO restart in
between:

- **Run 1**: `new-project` itself succeeded (`last_results` confirmed
  `"New project created"`), but all 3 scene-clear readback attempts came
  back `{"patterns": -1, "avatars": -1}` (unverifiable) — root-caused to
  `dispatchSyncRead`'s internal 3s wait timing out because `QueueDrainTimer`
  (a 200ms `SetTimer`) wasn't ticking that session, a limitation the
  plugin's own source comments already admit ("does not fire reliably in
  every session"). Fixed by adding `client.py`'s `_get_with_drain_nudge()`,
  which forces a `POST /execute` drain concurrently with the read.
- **Run 2** (immediately after, nudge fix applied): `new-project` again
  succeeded, but this time `wait_for_queue()` itself timed out — CLO
  reported `queue_processing: True` stuck, `queue_size: 7`.

## The queue_size=7 arithmetic is a real lead, not yet chased down

`7` is suspicious: it matches exactly "1 new-project (run 2) + 3 attempts ×
2 reads left over from run 1" — as if **none of run 1's failed
`/patterns/count`/`/avatars/state` reads ever actually drained**, and just
kept accumulating across runs within the same CLO session. That would mean
`QueueDrainTimer` wasn't merely "unreliable" here but not firing **at all**
for the rest of that session, and/or CLO's main thread genuinely hung
(not just ran slowly) inside one of those queued read commands — the
leading suspect being `read-avatar-state`
(`EXPORT_API->GetAvatarCount()`/`GetAvatarNameList()`/`GetAvatarGenderList()`),
the same API family `POST_MORTEM_v1.1.1.md` already found to be
SEH-crash-prone from the wrong thread. A silent main-thread hang (rather
than a crash) while the scene is mid-teardown from a just-issued
`new-project` would be a new, quieter variant of that same underlying
fragility — plausible given both stalls occurred shortly after a
`new-project` call, but **not confirmed** — this is a hypothesis from the
arithmetic, not a reproduced root cause.

**Important:** this is a bug in the *currently-deployed* plugin build, not
something introduced by this session's C++ source changes — `read-avatar-state`
already existed before any of Bug 2's edits, and the plugin hasn't been
rebuilt/redeployed yet at the time this was found. This step's polling just
started exercising that code path more than anything before it did.

## Current state

`step_02_new_project.py` still calls `new_project()` exactly once per run
(never retried — retrying it into an already-stuck queue was tried first and
confirmed to make things worse, not better). Scene-clear verification is
attempted but **never blocks the pipeline** — any failure (unverifiable
readback, queue-drain timeout) is logged as `[WARN]`/`[SKIPPED]` with a
pointer back to this section, and the step returns success regardless, so
the rest of the pipeline can be tested without being gated on this unsolved
problem.

## Update — deeper root-cause theory, and the fix actually applied

A third live run (same session, no CLO restart in between) made the picture
worse and clearer at the same time: `queue_size` climbed every step
(7 → 8 → 9 → 12) with `queue_processing` stuck `True` throughout — meaning
**nothing drained at all from some point in step 2 onward**, not just the
scene-clear reads. By step 4, a completely unrelated, pre-existing,
unmodified call (`step_04_import_patterns.py`'s `get_pattern_count()`, a
plain `_get()`, not routed through any of this session's new nudge code)
hung with **zero response bytes** for over 30 seconds, requiring a manual
`Ctrl+C` — `dispatchSyncRead`'s own internal `future.wait_for(3s)` should
make that impossible in isolation (it's a bounded, self-contained C++ wait
that doesn't depend on CLO's main thread responding), which means something
below that — the HTTP server itself — was also out of capacity to service
requests, not just CLO's main thread being slow.

Leading theory: `_get_with_drain_nudge()` (added earlier in this session to
fix the scene-clear readback's false failures) was called from inside
`wait_for_scene_clear()`'s poll loop — every 0.3s, for up to 10s, across up
to 3 attempts — firing up to roughly 100 `POST /execute` calls in a single
`step_02` run. `/execute`'s handler has a documented fallback
(`RestPlugin_windows.cpp`): if it can't find CLO's window handle, it calls
`ProcessCommandQueue()` **directly on the HTTP server's own worker thread**
("cross-thread CAPI risk," the plugin's own comment). If that batch contains
a command that hangs (the `read-avatar-state` suspicion above, or something
else), it doesn't just wedge CLO's main thread — it permanently consumes an
httplib worker thread. Repeat that ~100 times in one run and the server's
whole thread pool can plausibly exhaust, which would fully explain the
zero-byte hang on a request that has nothing to do with any of this step's
own code.

**Not proven** — this is the leading theory built from the evidence
available (queue growth arithmetic, the documented `/execute` fallback, the
otherwise-inexplicable zero-byte hang on an unrelated call), not a confirmed
root cause. No `TraceLog` instrumentation exists yet on `read-pattern-count`,
`read-avatar-state`, or `/execute` itself to see exactly which command a
stuck batch is inside when it hangs — that's the concrete next step to
actually confirm this rather than infer it.

**Fix applied now, pending that confirmation:**
1. `get_scene_object_counts()` no longer calls `/avatars/state` at all —
   `"avatars"` is hardcoded to `-1` (unverifiable), pattern count is the only
   live signal.
2. `_get_with_drain_nudge()` is no longer called anywhere — both call sites
   (`get_scene_object_counts()`, `get_avatar_visible()`) reverted to a plain
   `_get()`. The method is kept defined (documented as dormant, not deleted)
   since the concept isn't inherently wrong for a single, non-looped call —
   it's unsafe specifically when invoked repeatedly inside a poll loop.
   `wait_for_queue()` (called once per step, throttles itself to at most one
   `/execute` call per 3 seconds within its own bounded loop) remains the
   only thing in this pipeline that actively triggers a drain.

## Update — confirmed via plugin_crash_trace.log, not just theorized

Checked `clo_workspace/logs/plugin_crash_trace.log` directly (the deployed
plugin writes here regardless of install location — the path is a
compile-time constant). Found the exact hang, unambiguously:

```
[10:52:03] [tid=47776] QueueDrainTimer tick=59 draining queue
[10:52:03] [tid=47776] QueueDrainTimer tick=59 drain call returned
[10:52:03] [tid=26512] /execute called: qsize=0 processing=false hwndKnown=true -> queue empty
[10:52:05] [tid=47776] QueueDrainTimer tick=71 draining queue
```
— and no `"tick=71 drain call returned"` line ever appears. Every tick from
71 onward (thousands of them, confirmed still ticking on schedule 40+
minutes later) logs `SKIPPED — g_queueProcessing already true`. `tid=47776`
is CLO's actual main UI thread (the same tid that logged discovering
`g_cloMainWnd` moments earlier). `hwndKnown=true` on every subsequent
`/execute` call, ruling out the cross-thread "no HWND fallback" theory
speculated earlier — this is simpler and worse: **the main thread itself
hung**, synchronously, inside whatever command was in that batch, and
`ProcessCommandQueue()` never returned. Since the RAII reentrancy guard only
resets `g_queueProcessing` when the function *returns*, a hang (as opposed
to a crash or a slow-but-finite call) defeats it completely — the flag
stays `true` for the remaining lifetime of the process, no matter how many
times `/execute` or a menu click try again afterward (they all correctly
see `processing=true` and no-op immediately, "working as designed" but
unable to help).

Timing lines up with (though doesn't 100% prove) the `/avatars/state`
hypothesis above — 10:52:05 is shortly after a `new-project` call, exactly
when this session's Bug-1 verification code (at that point still calling
`/avatars/state`) would have been polling. Given `GetAvatarCount()` was
already documented as crash-prone from the wrong thread in
`POST_MORTEM_v1.1.1.md`, a hang instead of a crash under a different
triggering condition (scene mid-teardown, called from the *correct* thread
this time) is a very plausible sibling failure mode of the same underlying
fragility — but this log excerpt alone doesn't identify *which* command was
in the tick-71 batch, since `read-pattern-count`/`read-avatar-state` have no
`TraceLog` `BEGIN`/`END` instrumentation (unlike `create-seam`,
`import-pattern`, `import-avatar-avt`, which do — visible earlier in the
same log). Adding that instrumentation is the concrete next step to move
this from "consistent with" to "confirmed."

**Practical consequence:** a CLO process that hits this cannot recover on
its own — it must be killed (Task Manager → End Task, not the window close
button) and relaunched. No amount of retrying, re-clicking the Plugins menu,
or Python-side changes can unstick an already-hung main thread.

## Next steps (not done)

1. Get a `TraceLog` capture of a session that reproduces the stuck-queue
   state, specifically watching whether `"BEGIN"`/`"END"` pairs exist around
   `read-avatar-state` (neither `new-project` nor `read-pattern-count`
   currently have `TraceLog` instrumentation either — worth adding to all
   three to see exactly which command a stuck batch is inside when it
   hangs).
2. If `read-avatar-state` is confirmed as the hang site, consider dropping
   it from `get_scene_object_counts()` entirely (verify pattern-count only)
   rather than trying to make it safe — `/patterns/count` alone may be
   sufficient for Bug 1's original purpose and doesn't touch the
   `EXPORT_API` avatar-listing calls at all.
3. Re-test whether the stuck state is specific to calling these reads
   *shortly after* `new-project` (scene mid-teardown) vs. reproducible at
   any time in a session — determines whether the fix is "don't read avatar
   state right after new-project" (a timing fix) or "don't call
   `read-avatar-state` from this pipeline at all" (an avoidance fix).

---

## Suggested implementation order

1. **Bug 1 fix** (new-project verification) — self-contained, uses an
   already-available endpoint (`/avatars/state` is live, contradicting the
   prior known-issue doc), no new plugin capability needed. Lowest risk,
   ship first.
2. **Logging Phase A** — do this alongside/right after Bug 1, since every
   subsequent investigation (Bug 2 in particular) benefits enormously from a
   persisted `run.log` instead of relying on someone watching a terminal
   live.
3. **Bug 2 fix** — the SDK functions are now confirmed
   (`SetShowHideAvatar`/`IsShowAvatar`/`Refresh3DWindow`), so this is
   implementable directly: add the plugin command + readback, wire the
   Python calls into `step_09`/`step_10`, and do the one remaining empirical
   test (does `IsShowAvatar` read `false` or `true` right after sewing —
   decides whether a single show-call or the off→on pair is needed) during
   that same rebuild-and-test cycle rather than as a separate investigation
   phase.
4. **Bug 3 + Bug 4 shared verification helper** (`glb_inspect.py`) — build
   once Bug 2 is fixed, so "does the export look right" is being measured
   against a scene that *should* produce a correct result, not one still
   broken upstream. Calibrate thresholds against a manually-exported
   known-good GLB before wiring in as a blocking gate. Also do the
   one-line `bIncludeHiddenObject = true` test called out in Bug 4 in this
   same pass.
5. **Per-run output directories + logging Phase B** — largest blast radius,
   least urgent relative to the 4 correctness bugs; do last, as its own
   isolated change.
