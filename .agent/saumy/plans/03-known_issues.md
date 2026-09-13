# 03 — Known issue: avatars accumulating across pipeline runs in one CLO session

Status: *known, not fixed — currently protected only by a post-hoc backstop*
First documented: *2026-08-22* (this file just consolidates existing
documentation, nothing new was investigated to write it)
Sources: `clo_workspace/versions/v_1.3.2.json` known_issues,
`clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py:12`,
`.agent/website-launch-2/11-date-26_08_22.md` Part 2 (original root-cause
evidence, not re-derived here)

## The problem

CLO's `NewProject()` only clears the current **garment** — it does not
clear avatars. The SDK header states this explicitly
(`UtilityAPIInterface.h:419-421`: "Clear the current garment and begin a
new garment"). So every time the pipeline calls `new-project` between
runs, any avatar already in the scene survives.

This was confirmed to actually happen, not just theoretically possible:
five back-to-back pipeline runs in one CLO session once left 3, 4, 1, 1,
and 2 avatars in the scene respectively. In every one of those runs, the
*correct* avatar for that run's user was genuinely present in the scene —
but Step 11 (save/export) was extracting the wrong one, exporting a base
avatar or a previous user's avatar under the current run's ID. Root cause
was confirmed by reading the saved `.zprj` projects directly: passing runs
contained exactly one `.avt` member, failing runs contained two or three.

## Why it can't just be fixed by asking CLO "how many avatars exist"

Every CLO SDK API that could answer that question is unsafe:

- `GetAvatarCount` / `GetAvatarNameList` — live in `EXPORT_API`, already
  excluded from use per an earlier postmortem (SEH-crash-prone when called
  off CLO's main thread).
- `GetAvatarProperties(index)` — **crashes the entire CLO process** if no
  avatar exists at that index. Confirmed live: a bare probe against an
  empty scene logged "begin" with no matching "end," and the process was
  gone.
- `DeleteAvatar()` — **hangs CLO's main thread** if the index list contains
  any index with no avatar at it. Confirmed live the same day. Recovery
  requires killing and relaunching CLO.
- `IsShowAvatar` — can't distinguish "hidden" from "absent"; its default
  body returns `false` for both, so it can't be used to detect presence
  either.

So there is currently **no safe way to query or clear avatar count from
the plugin at all.** This isn't a gap that just hasn't been gotten to yet —
every known approach has been tried and specifically ruled unsafe.

## What was built as a workaround, and why it's not actually used

The plugin added a manual counter, `g_avatarsLoaded` (an atomic int),
incremented on every successful `import-avatar-avt` and meant to be reset
to 0 by a `/clear-avatars` route calling `DeleteAvatar()`. But:

- `g_avatarsLoaded` only tracks avatars imported **through this plugin**.
  An avatar loaded by hand through the CLO GUI is invisible to it.
- The pipeline imports twice per run but the scene often ends with one
  avatar (the patched import replaces rather than adds) — so counting
  imports doesn't even reliably match what's really in the scene.
- Since `DeleteAvatar()` hangs CLO if any index in the list is empty, and
  there's no safe way to confirm the list is accurate first, calling
  `/clear-avatars` is itself a live hazard.

Result: **`/clear-avatars` is not called by the pipeline.** The route and
the counter still exist in the plugin source but are dead code as of
2026-08-22 (`step_07` no longer invokes them). Do not re-enable this
without first solving the underlying "how do we safely know what's in the
scene" problem — none of the above workarounds actually solve it.

## The fix we're currently depending on instead

Not a fix — a **backstop**, at the very end of the pipeline. Step 11
(`step_11_save_outputs.py`) now:

1. Selects the **highest-numbered** `.avt` member from the saved project
   file, rather than the first one (the original bug — always taking the
   first member is what silently picked the wrong avatar).
2. **Hard-fails the run** if the saved project contains anything other
   than exactly one avatar, instead of silently proceeding with whatever
   it found.

So a leak is now *reported* (the run fails loudly) rather than *silently
corrected with the wrong data*. This is a real improvement — it converts
"wrong avatar exported and nobody notices" into "run fails and you know
something's wrong" — but it does not prevent the leak from happening, and
it's post-hoc: by the time it fires, the entire apply/save cycle for that
run has already spent real CLO time on a run that then has to be thrown
away and redone (after restarting CLO to actually clear the accumulated
avatars).

## Current status (verified tonight, not newly investigated)

Both pipeline runs done tonight checked cleanly:
- Step 3 (Import Avatar): `Scene holds exactly 1 avatar.`
- Step 11 (Save Project): `Project holds exactly 1 avatar.`

So this is **not currently happening** in the present CLO session. It
remains a live risk for any future session where the pipeline is run
multiple times without restarting CLO in between — restarting CLO between
test sessions is the practical mitigation available today, not a fix to
the underlying problem.

## Related, separately documented finding (not re-solved here)

Tonight's broader audit (`02-false-success-reporting-audit.md`,
`clo_avatar_generation` section, finding #1) found that
`step_07_import_base_avatar.py`'s current default scene-clear path
(`IMPORT_BASE_AVATAR_INTO_CLO = False`) trusts the plugin's immediate
`new-project` REST acknowledgement, which is hardcoded `success: true`
the instant the command is *queued* — not once `NewProject()` has actually
run. So step 7 itself has no way to detect a repeat of the original
scene-clear race before it happens; only Step 11's backstop above catches
it, after the fact.
