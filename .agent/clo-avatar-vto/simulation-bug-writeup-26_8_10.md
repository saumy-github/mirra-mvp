# The Simulation Bug — Why the Pipeline Never Produces a Final Sewed/Draped Product

Written 2026-08-10. Consolidates `vto-pipeline-debug-plan-26_7_24.md` (Bugs 3
& 4's original root-cause analysis), `vto-pipeline-status-26_7_24.md`
(what got live-tested), and the current uncommitted code on this branch
(`client.py`, `step_10_simulate.py`, `RestPlugin_windows.cpp`,
`RestPlugin_macOS.cpp`) as of this writing.

**Status: still open.** The pipeline currently produces, at best, 4 correctly
*arranged* but unsewn/undraped panels with no avatar in the export — not a
finished garment. The blocking issue is that `Simulate()` either (a) runs
against a scene that can't produce a real drape, or (b) hangs CLO's main
thread outright and never returns. Both have been observed on different runs.

---

## 1. The symptom

`step_10_simulate.py` calls `Simulate(150 steps)`, `wait_for_queue()`
reports the command drained, and the step returns `True` unconditionally.
But the final export (`step_11_export_note.py`) shows:
- 4 panels, individually positioned/oriented correctly around where the
  avatar should be (arrangement/slot placement is confirmed working), but
  **not stitched together into a worn shape**.
- **No avatar mesh** in the export at all.

So visually: "curved and placed around the avatar, but not sewn" — topology
is right, physics never visibly happened.

## 2. Why this is hard: `Simulate()` "succeeding" doesn't mean what it sounds like

Confirmed from the real SDK header (`UtilityAPIInterface.h`):
```cpp
/// @fn Simulate(unsigned int _steps)
/// @brief Simulate the garment in multi steps...
/// @return if it succeeds, return true.
virtual bool Simulate(unsigned int _steps) { return false; }
```
This is a genuinely synchronous, blocking call — not fire-and-forget like
`NewProject()`. So `Simulate()` returning `true` most likely means CLO's
cloth solver really did run 150 steps against *whatever was in the scene* —
the open question was never "did the call complete," it's "was there
anything valid to drape onto." A solver with no visible avatar collision
body can run its steps and still report success while producing flat,
barely-moved geometry.

The Python side (pre-fix) had no way to distinguish those two outcomes:
```python
# step_10_simulate.py (original)
try:
    ctx.client.wait_for_queue(timeout=300)
except Exception as exc:
    print(f"  [WARN] Simulation drain timed out: {exc}")
return True   # unconditional, regardless of what actually happened
```
Same "queue-empty ≠ CLO-actually-finished-real-work" gap as the other bugs
in this pipeline (`new-project`'s scene-clear check, see the sibling
`new-project-bug-writeup-26_8_9.md`).

**A tempting but confirmed-dead-end fix:** diff `/patterns/{i}/bbox`
before/after simulate. Ruled out directly from the SDK header —
`GetBoundingBoxOfPattern` returns the **2D flat pattern outline**
(width/height), not 3D world-space post-drape geometry. Draping doesn't
change a pattern piece's own 2D definition, so this endpoint can never prove
or disprove simulation happened.

---

## 3. Timeline of what we tried

### 3.1 Fix avatar visibility first (Bug 2), on the theory Bug 3 would resolve itself
Wired in `SetShowHideAvatar` / `IsShowAvatar` / `Refresh3DWindow` (confirmed
real SDK functions): new plugin routes `POST /avatar/ensure-visible` and
`GET /avatar/visible`, called from `step_09_create_seams.py` (after sewing)
and `step_10_simulate.py` (right before `simulate()`). Plugin rebuilt clean.
**Outcome:** user reported the avatar no longer visibly disappeared during
sewing — a good sign — but the `/avatar/visible` readback printed
`before=None -> after=None` in that same run, meaning the route was likely
still 404ing (new DLL not actually installed yet). **Never conclusively
confirmed as the fix that closed the loop** — see `has_avatar_visibility_set`
capability-flag check in the sibling status doc, still outstanding.

### 3.2 Discovered `Simulate()` doesn't just silently under-perform — it can permanently hang
Live testing gave direct, repeatable evidence, confirmed from
`clo_workspace/logs/plugin_crash_trace.log` (not inferred): `Simulate(150
steps)` did not return within 5 minutes, and `queue_processing` stayed stuck
`True` afterward, in two consecutive full runs, same relative spot, after a
clean CLO restart each time.
```
[10:52:03] tick=59 draining queue
[10:52:03] tick=59 drain call returned      ← normal
[10:52:05] tick=71 draining queue
                                              ← never returns, ever again
```
Key confirmed facts:
- This is CLO's real main UI thread (`hwndKnown=true`), not a background
  thread.
- Windows does **not** flag the process "Not Responding" and CPU sits near
  0% — looks completely healthy from Task Manager, easy to misdiagnose as a
  Python-side problem unless the trace log is checked directly.
- Once `g_queueProcessing` gets stuck `true` inside a hang, it never
  recovers — the RAII reentrancy guard only resets on return, and a hang
  never returns. No retry, no amount of clicking the Plugins menu, fixes it
  — CLO must be killed and restarted.
- This is the same general fragility class as the original
  `.claude/research/step-1/POST_MORTEM_v1.1.1.md` SEH crashes in
  `EXPORT_API` calls off the main thread — except manifesting as a silent
  hang instead of a crash, arguably worse (a crash at least visibly kills
  the process; a hang looks like nothing is wrong).
- Two distinct confirmed triggers so far: repeated `/avatars/state` calls
  shortly after `new-project` (removed, see the sibling writeup), and
  `Simulate()` itself — **still unresolved**.

This reframed Bug 3 from "simulation is silently no-op-ing" to "simulation
may not be completing at all, some fraction of the time."

### 3.3 Added `TraceLog` BEGIN/END instrumentation around the simulate handler (2026-07-25)
Previously `simulate` had no forensic logging at all (unlike `create-seam`),
so a hang could only be inferred from "the next drain tick never returned,"
not proven to be inside `Simulate()` itself specifically. Now:
```cpp
TraceLog("BEGIN simulate steps=" + ... + " livePatternCount=" + ...);
asyncResult.success = UTILITY_API->Simulate((unsigned int)cmd.param3);
TraceLog("END   simulate success=" + ...);
```
**Status: done, plugin rebuilt clean, but — same as the visibility fix —
still needs a confirmed admin install + CLO restart before it actually takes
effect.** Not yet used to catch a live hang in the act.

### 3.4 Tested the "avatar far from world origin" hypothesis via `AlignAvatarsAndGarmentToCenter()` — tried and reverted (2026-07-25)
Found a real, applicable, no-arg SDK call in `UtilityAPIInterface.h` that
recenters both avatar and garment to CLO's world origin. Wired it into both
plugin platforms (`POST /align-to-center`, capability flag
`has_align_to_center`) and called it from `step_10_simulate.py` immediately
before `simulate()`.

**Live test result: this broke the scene outright.** The 3D window
collapsed to a single-point "starburst" of degenerate lines — avatar and
garment silhouette both gone. `AlignAvatarsAndGarmentToCenter()` is **not
safe to call on patterns that are still in their pre-simulation arranged
(not-yet-draped) state.**

Current state on this branch (uncommitted): the call to it has been removed
from `step_10_simulate.py` — a `# Do NOT call ... here (or anywhere
pre-simulate)` comment sits in its place — but `client.align_to_center()`,
the plugin route, and the capability flag are all still defined/left in
place as dead code, documented as unsafe pre-simulate. **Net effect: the
off-origin hypothesis for the hang is untested, not ruled out** — this only
proved that specific call site (right before simulate, on arranged-not-yet-
draped geometry) is wrong. Whether avatar position matters to the hang at
all is still an open question.

### 3.5 Built a GLB-content verification layer (`glb_inspect.py`) instead of trusting queue-drain
Since neither `wait_for_queue()` nor a bbox diff can prove a real drape
happened, and re-triggering an export mid-`step_10` was judged not worth
duplicating, verification was pushed to the export step, using the one
artifact that unambiguously reflects real post-simulation 3D geometry: the
exported GLB itself (`pygltflib` was already a hard dependency of
`step_12_texture_glb.py`).

Two independent checks landed in `step_11_export_note.py`:
- **Mesh count check** — an avatar + sewn garment should yield a
  meaningfully different mesh count than 4 independent flat panels + zero
  avatar meshes.
- **`mesh_is_draped()` planarity heuristic** — flags meshes whose
  thinnest-axis extent is suspiciously near-zero relative to the other two
  axes (a flat, unsimulated pattern piece is planar; a draped garment or a
  human-shaped avatar is not).

**Outcome, tested against a real confirmed-bad export
(`clo_vto/output/simulation.glb`, the exact "4 floating unsewn panels, no
avatar" failure):**
- ✅ **Mesh count check works and is now the live blocking/loud-failure
  gate.** Correctly and loudly failed with `"[FAIL] Export has only 4
  mesh(es) — avatar mesh is likely missing"` on the last two real runs.
- ❌ **`mesh_is_draped()` does NOT reliably distinguish arranged-only from
  arranged-and-simulated.** Every panel in the known-bad export came back
  with a flatness ratio of 0.26–0.64 — nowhere near planar. Turns out
  `arrange-pattern` already gives each piece real 3D curvature (positioned/
  oriented to wrap the body) even before any simulation runs, so planarity
  alone can't tell "just arranged" from "arranged and draped." **Downgraded
  to diagnostic-only, not a pass/fail gate** — still logged, still cheap and
  harmless, just not trusted to block on.

### 3.6 Applied `bIncludeHiddenObject = true` to the export options
`ImportExportOption` in the real SDK confirms CLO's export pipeline
generally excludes hidden objects (pattern meshes, at minimum — not
name-confirmed for avatars specifically, but a well-supported inference)
unless told otherwise. Set on both platforms (`RestPlugin_windows.cpp:1887`,
`RestPlugin_macOS.cpp:864`) as a cheap defensive addition regardless of
whether it turns out to be the actual mechanism for the missing avatar mesh.
**Status: applied. Not yet isolated/tested independently** — i.e., nobody
has run one export with the avatar deliberately left hidden, with this flag
on, to confirm whether it alone makes the avatar appear.

---

## 4. What's confirmed vs. still a hypothesis

**Confirmed, directly, not inferred:**
- `Simulate()` is a synchronous, blocking SDK call — not fire-and-forget.
- `GetBoundingBoxOfPattern` returns 2D flat-pattern dimensions, not 3D
  post-drape geometry — cannot be used to verify simulation happened.
- CLO's main thread can hang **permanently**, with no crash and no OS-level
  "Not Responding" symptom, inside `Simulate()` — observed directly via
  `plugin_crash_trace.log` in two consecutive runs.
- `AlignAvatarsAndGarmentToCenter()` called pre-simulate on arranged (not
  yet draped) patterns destroys the scene (collapses to a degenerate point).
- The mesh-count export check correctly catches the known-bad "4 panels, no
  avatar" case; the planarity heuristic does not.
- `arrange-pattern` alone produces panels with real (non-planar) 3D
  curvature, before any simulation runs — this is why planarity can't be
  used as the drape signal.

**Still hypothesis, not confirmed:**
- Whether the avatar being far from world origin is actually a factor in
  the `Simulate()` hang at all — the one attempt to test this
  (align-to-center immediately pre-simulate) was itself unsafe and had to be
  reverted before it could answer the question.
- Whether the `Simulate()` hang and the "reports success but doesn't
  visibly drape" symptom are the *same* bug or two separate bugs that both
  block the same step — a hang obviously prevents completion, but the
  original "succeeds numerically, drapes onto nothing" theory (a solver
  with no avatar collision body) was never separately ruled out on a run
  where `Simulate()` didn't hang.
- Whether `bIncludeHiddenObject = true` alone is sufficient to make a hidden
  avatar appear in the GLTF export, independent of Bug 2's visibility fix.
- Whether Bug 2's avatar-visibility fix is actually installed and active —
  `has_avatar_visibility_set` capability flag has never been confirmed
  `true` post-install.

---

## 5. Ideas to try next, in priority order

1. **Manually trigger Simulate from CLO's own GUI**, not via the plugin, on
   the exact same avatar+garment scene state that hangs via the API. This
   is the single highest-leverage unblock: if it also hangs in the GUI,
   it's a CLO/SDK-level issue no amount of plugin code can fix (and the
   pipeline needs a different strategy entirely — see #7). If it completes
   fine manually, the bug is specific to how/when the plugin invokes it
   (wrong thread context, timing relative to other queued commands, scene
   state left by prior queued commands). **Still not done — needs a human
   at the CLO window.**

2. **Confirm the rebuilt plugin DLL is actually installed** before crediting
   any fix. Check `GET /capabilities` for `has_avatar_visibility_set` and
   `has_align_to_center` — if either reads `false`, the admin copy-and-restart
   step hasn't taken effect and every "fixed" claim above is unverified.

3. **Use the new TraceLog BEGIN/END instrumentation to catch a live hang in
   the act.** Once confirmed installed (#2), reproduce a run and check
   `plugin_crash_trace.log` for `BEGIN simulate ...` with no matching `END`
   — this converts "simulate hangs" from a strong inference to direct proof,
   and rules out (or confirms) that the hang is specifically inside
   `UTILITY_API->Simulate()` rather than something queued around it.

4. **Test the off-origin hypothesis properly, not destructively.** The one
   attempt broke the scene because it called `AlignAvatarsAndGarmentToCenter()`
   pre-simulate on un-draped geometry — that only proves *that* call site is
   wrong, not that avatar position is irrelevant to the hang. Two safer
   ways to actually test it:
   - First just check whether the avatar genuinely *is* far from origin in
     a hanging run (log avatar position) before assuming it matters at all.
   - If it is, try aligning **before import/arrangement** (i.e., recenter
     the avatar itself at avatar-load time, not the garment mid-pipeline)
     rather than recentering both right before simulate.

5. **Add a settle delay + bounded retry before `Simulate()`**, reusing the
   pattern already proven in `clo_avatar_generation/avatar_runtime/step_11_save_outputs.py`
   for the structurally identical "CLO's internal work isn't done when the
   API call returns" problem there (2.5s settle delay, sanity check, up to
   3 bounded retries). No need to invent a new mitigation if one already
   works for the same underlying class of bug in this codebase.

6. **Build a watchdog for `queue_processing` stuck `True`.** Trivially
   checkable via `/status` (already polled by `wait_for_queue()`). Right
   now a hang just looks like a generic 300s timeout exception —
   indistinguishable from ordinary slowness. Surface a specific "CLO has
   hung, kill and restart it" signal instead, so whoever is running the
   pipeline doesn't have to go dig through the trace log to figure out
   what happened, and doesn't waste time retrying the pipeline into an
   already-wedged CLO process.

7. **If the GUI repro (#1) shows this is a genuine CLO/SDK-level hang, not
   fixable in plugin code:** investigate whether CLO's own simulation
   properties need to be set before calling `Simulate()`. The SDK doc
   comment mentions the call "follows the current simulation properties
   (time step, CG iteration count, ...)" — if those are unset or left at an
   invalid/default state on a freshly-created project, the solver could be
   looping pathologically rather than genuinely hanging. Nobody has checked
   whether CLO's GUI sets these implicitly on project creation in a way the
   plugin's `new-project` flow doesn't replicate. Also worth trying a
   smaller step count (e.g. 10–20 instead of 150) as a cheap diagnostic —
   if a short simulate reliably completes, the issue may be duration/step-
   count-related rather than a fixed pathological state, which would point
   at a different fix (chunked simulate calls) than an outright hang would.

8. **Once Simulate() completes reliably, isolate `bIncludeHiddenObject`'s
   real effect** — export once with the avatar deliberately left hidden
   (skip `ensure-avatar-visible`) with the flag on, to settle definitively
   whether it was ever load-bearing for the avatar case specifically, vs.
   Bug 2's visibility fix being the only thing that mattered.

9. **Revisit `mesh_is_draped()` with a better signal than planarity**, per
   `glb_inspect.py`'s own notes: check whether panel meshes' geometry
   actually touches/overlaps at shared seam edges (truly sewn) vs. remains
   spatially separate (merely arranged) — this would distinguish "draped"
   from "arranged" in a way flatness ratio can't, and could become a real
   blocking gate in `step_10` itself instead of a step_11-only diagnostic.

10. **Longer-term:** this hang, the `new-project`/`/avatars/state` hang, and
    the original `ExportAVT`/`GetAvatarCount` SEH crashes are three separate
    instances of the same underlying fragility — certain CLO SDK calls are
    unsafe under certain scene states or thread contexts, with no in-process
    recovery once one hangs. Worth treating "first request after a fresh
    CLO restart" as a known-riskier window generally, and considering a
    proactive throwaway warm-up run after every CLO restart.

---

## 6. Where to look for more detail
- Original Bug 3/4 root-cause analysis, SDK header excerpts, first-pass
  fix proposals: `vto-pipeline-debug-plan-26_7_24.md`
- Session-by-session status, the hang discovery, the align-to-center
  live-test failure: `vto-pipeline-status-26_7_24.md`
- The sibling `new-project` hang investigation (same failure class,
  different call site — useful for cross-referencing the hang mechanism):
  `new-project-bug-writeup-26_8_9.md`
- Historical SEH-crash precedent: `.claude/research/step-1/POST_MORTEM_v1.1.1.md`
- Current verification code: `clo_vto/native_vto/glb_inspect.py`,
  `clo_vto/native_vto/step_10_simulate.py`,
  `clo_vto/native_vto/step_11_export_note.py`
- Live hang evidence: `clo_workspace/logs/plugin_crash_trace.log`
- Known-bad reference export used to validate the GLB checks:
  `clo_vto/output/simulation.glb`
