# VTO Pipeline — Status as of 2026-07-24 (end of day)

Companion to `vto-pipeline-debug-plan-26_7_24.md` (the full research/root-cause
doc) and `known-issue-26_7_23.md` (prior findings). This doc is the quick
"where are we" reference — what's fixed, what's confirmed vs. still
suspected, and what's left.

---

## TL;DR

Today's session found and fixed the new-project/avatar-visibility bugs as
originally scoped, but along the way surfaced a **more serious, still-open
problem**: CLO's main thread can permanently hang (not just run slowly)
inside certain plugin-triggered SDK calls, and this is now the thing
actually blocking the pipeline from completing — currently on `Simulate()`.
That's the top priority for tomorrow.

---

## Status by original bug

### Bug 1 — `new-project` scene-clear verification
**Status: disabled/non-blocking, not fixed.** Attempted a real fix (poll
`/patterns/count` + `/avatars/state` after `new-project`), but live testing
showed the verification layer itself was unreliable and, worse, calling
`/avatars/state` repeatedly appears to have been the trigger for a
plugin-wedging hang (see "New, bigger finding" below). Current state:
- `new_project()` is called exactly once per run (not retried).
- Scene-clear check only polls `/patterns/count` now (`/avatars/state` was
  removed from this path entirely — too risky).
- Any verification failure is logged as `[WARN]`/`[SKIPPED]` and **never
  blocks the pipeline** — this was an explicit instruction mid-session
  rather than a technical fix.
- Pattern count itself (`{'patterns': 0, ...}`) has read back correctly and
  quickly in every run since — that part works fine.

### Bug 2 — avatar disappears after sewing
**Status: fix implemented and built; visually reported working; not yet
confirmed via the plugin's own readback.** `SetShowHideAvatar`/`IsShowAvatar`/
`Refresh3DWindow` (confirmed real SDK functions, from the actual CLO SDK
header) are now wired in on both the plugin and Python sides:
- New plugin commands: `POST /avatar/ensure-visible` (off→on toggle +
  forced redraw), `GET /avatar/visible` (readback).
- Called from `step_09_create_seams.py` (after sewing) and
  `step_10_simulate.py` (before simulating).
- **Plugin rebuilt successfully** (`python clo_workspace/build_plugin.py`,
  clean compile, no errors) — DLL at
  `C:\setup\CLO_SDK_v2025.2.236_WIN\...\Samples\RestPlugin\build\Release\RestPlugin.dll`.
- User confirmed manual install instructions were provided (admin copy into
  CLO's plugins folder + restart CLO) — **not yet confirmed those steps were
  actually completed**.
- User reports (2026-07-24, latest run): avatar did not disappear during
  sewing — good sign.
- **Caveat worth resolving:** in that same run, `avatar visible: before=None
  -> after=None` still printed at both call sites, meaning `/avatar/visible`
  is still failing/unreachable — the same as every pre-rebuild run. That's
  most consistent with the new DLL not actually being loaded yet (old plugin
  doesn't have this route → 404 → `None`). Worth explicitly confirming the
  install happened before fully crediting this fix — the visual "didn't
  disappear" result might be real, or might be coincidental/intermittent.
  Easiest confirmation: check `GET /capabilities` for
  `"has_avatar_visibility_set"` — only a rebuilt+installed+exercised plugin
  will ever report that `true`.

### Bug 3 — simulation reports "done" but doesn't actually happen
**Status: root cause deepened, NOT fixed — this is the current blocker.**
Live testing gave direct, repeatable evidence: `Simulate()` (150 steps)
does not return within 5 minutes, and `queue_processing` stays stuck `True`
afterward — i.e., not "slow," but the same category of permanent hang seen
elsewhere today (see below). This happened in two consecutive full runs, in
the same relative spot, after a clean CLO restart each time. Screenshot
evidence from the user: patterns arrange and sew correctly (topology is
right), but the garment looks rigid/flat rather than draped — consistent
with physics never actually running.

### Bug 4 — export is floating unsewn panels, no avatar
**Status: verification gate confirmed working; underlying cause still
blocked on Bug 3.** `step_11_export_note.py`'s mesh-count check
(`glb_inspect.py`) is now live and has correctly, loudly failed the last two
runs — `"[FAIL] Export has only 4 mesh(es) — avatar mesh is likely
missing"` — instead of silently reporting success on a broken export. This
is exactly the fix working as designed. The export still doesn't contain a
real result because step 10 never actually finishes simulating.

### Logging
**Status: done, working.** `run.log` has been generated and readable for
every run today; `ctx.logger` output confirmed in every log excerpt shown
throughout the session.

---

## New, bigger finding this session: CLO's main thread can permanently hang

Not one of the original 4 bugs, but the most significant thing found today.
Confirmed directly from `clo_workspace/logs/plugin_crash_trace.log` (not
inferred):

```
[10:52:03] tick=59 draining queue
[10:52:03] tick=59 drain call returned      ← normal
[10:52:05] tick=71 draining queue
                                              ← never returns. Ever again,
                                                for the rest of that CLO
                                                process's life.
```

Key facts, all confirmed from the trace log or Task Manager, not guessed:
- The 200ms drain timer (`QueueDrainTimer`) is healthy and fires on schedule
  throughout — it is not the problem. (Earlier in the session this was
  wrongly suspected — corrected once the log was actually checked.)
- The hang is on CLO's real main UI thread (`hwndKnown=true` throughout,
  ruling out the `/execute` no-HWND cross-thread fallback as the cause).
- Once `g_queueProcessing` gets stuck `true` inside a hung call, it **never
  recovers** — the RAII reentrancy guard only resets on return, and a hang
  (as opposed to a crash or a merely-slow call) never returns. No amount of
  retrying, clicking the Plugins menu, or waiting fixes this — the process
  must be killed and restarted.
- Windows does **not** flag the process "Not Responding" and CPU sits near
  0% — this looks completely healthy from the OS/Task Manager's point of
  view, which makes it easy to misdiagnose as a Python-side problem if you
  don't check the trace log directly.
- Confirmed two distinct triggers so far, in two separate incidents:
  1. Repeated `/avatars/state` calls shortly after `new-project` (this
     session's own Bug-1 verification code, since removed).
  2. `Simulate()` itself, in the two most recent runs — this one is **not
     yet fixed or worked around**.

This is very likely the same underlying class of fragility already
documented in `.claude/research/step-1/POST_MORTEM_v1.1.1.md` (SEH crashes
in `EXPORT_API` calls off the main thread) — except manifesting as a hang
instead of a crash, and this time from the correct thread, which is a worse
failure mode in one sense (a crash at least kills the process and lets you
notice immediately and restart; a silent hang looks like nothing is wrong
until you dig).

---

## What's left (priority order)

1. **Confirm the new plugin DLL is actually installed and running.** Check
   `GET /capabilities` → `has_avatar_visibility_set`. If `false`, the admin
   copy step hasn't taken effect yet — Bug 2's fix is unverified until this
   reads `true` after actually exercising `/avatar/ensure-visible`.
2. **Investigate the `Simulate()` hang — the current blocker.** Concretely:
   - Manually trigger Simulate from CLO's own GUI (not via the plugin) on
     the same avatar+garment scene state. If it also hangs there, this is a
     CLO/SDK-level issue, not something fixable in our plugin code. If it
     completes fine manually, the issue is specific to how the plugin calls
     it (wrong thread context, wrong timing relative to other queued
     commands, etc.).
   - Add `TraceLog` `BEGIN`/`END` instrumentation around the `simulate`
     command handler (currently has none, unlike `create-seam`) so future
     hangs are unambiguous in the log instead of inferred from "the next
     tick never returned."
   - Check whether the avatar's position ("very ahead of grid," per the
     user's observation, not yet independently confirmed) is a factor —
     an avatar transform far from CLO's world origin is a plausible way to
     make a physics/collision solver degrade or loop pathologically. Avatar
     import itself is out of scope to change, but worth checking whether
     this is cause or coincidence.
3. **Once Simulate() completes reliably**, re-run and confirm Bug 4's export
   gate passes on its own (avatar mesh present, real drape) — expected to
   resolve automatically once 2 is fixed, per the original causal-chain
   theory (Bug 2 → Bug 3 → Bug 4).
4. **Bug 1's scene-clear verification** remains intentionally disabled
   (warn-only). Low priority relative to the above — pattern-count readback
   works fine; only the (now-unused) avatar-count path was ever the problem.
5. **Deferred, not started:** per-run output directories, full print→logger
   migration (logging "Phase B"). Explicitly lowest priority, flagged as its
   own isolated change in the original debug-plan doc.

---

## Where to look for more detail
- Root-cause research, SDK findings, original 4-bug analysis:
  `vto-pipeline-debug-plan-26_7_24.md`
- Prior-session findings (fabric graphic API gap, segmentation/dependency
  issues, first-run-after-restart avatar sizing): `known-issue-26_7_23.md`
- Historical SEH-crash incident this session's hang findings likely relate
  to: `.claude/research/step-1/POST_MORTEM_v1.1.1.md`
- Live evidence for every claim above: `clo_workspace/logs/plugin_crash_trace.log`
