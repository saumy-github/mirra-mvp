# The `new-project` Scene-Clear Bug — What We Tried, Why It's Still Broken, and Ideas to Actually Fix It

Written 2026-08-09. Consolidates everything found across
`vto-pipeline-debug-plan-26_7_24.md` (Bug 1 + its "New open issue" addendum),
`known-issue-26_7_23.md`, `.claude/research/step-1/POST_MORTEM_v1.1.1.md`, and
a fresh read of the current code while writing this doc — which turned up one
concrete, currently-live logic bug that none of the earlier docs caught (see
§4).

**Status: still open.** The pipeline does not fail loudly on this anymore,
but that's because the check was disabled, not because the underlying
problem was solved.

---

## 1. The original symptom

Running the VTO pipeline a second time inside the same CLO session left
patterns from the previous run in the scene. Confirmed live:
`clo_vto/output/base-1__native_vto_report.json` (2026-07-23T11:29:18Z run) —
`step_05_verify_patterns` failed with `"loaded_patterns": 8` when 4 were
expected. `new-project` itself reported success; nothing caught that the
scene wasn't actually clear until 3 steps later, by accident, in an unrelated
check.

## 2. Why this is hard: `NewProject()` cannot tell you if it worked

Confirmed directly from the real CLO SDK header
(`UtilityAPIInterface.h:334-336`), not the local mock stub:

```cpp
/// @fn NewProject()
/// @brief Clear the current garment and begin a new garment
virtual void NewProject() {}
```

It's `void`. There is no success/failure signal to check — `asyncResult.success = true` in the plugin's `new-project` handler isn't discarding a real
return value, because there isn't one. The only way to know whether the
scene actually cleared is to read it back afterward. Everything below is
about how to do that read-back safely, and why every attempt so far has
either not worked or introduced a worse problem.

This is the same underlying design gap across most of this pipeline's
bugs (see the sibling doc `vto-pipeline-status-26_7_24.md`): **the command
queue reporting empty only proves the command was dequeued and the
synchronous SDK call returned — not that CLO's internal engine work is
actually done.**

---

## 3. Timeline of what we tried

### Attempt 1 (2026-07-24) — poll `/patterns/count` + `/avatars/state` after `new-project`

The first real fix. Added to `client.py`:

```python
def get_scene_object_counts(self) -> dict:
    patterns = self._get("/patterns/count")
    avatars = self._get("/avatars/state")
    return {
        "patterns": patterns.get("count", -1) if patterns.get("success") else -1,
        "avatars": avatars.get("avatar_count", -1) if avatars.get("success") else -1,
    }

def wait_for_scene_clear(self, timeout=10.0, poll_interval=0.3) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        last = self.get_scene_object_counts()
        if last["patterns"] == 0 and last["avatars"] == 0:
            return last
        time.sleep(poll_interval)
    return last
```

and `step_02_new_project.py` was rewritten to call `new_project()` once, wait
for the queue to drain, then poll `wait_for_scene_clear()` with up to 3
retries before failing loudly.

At the time, this looked safe: an earlier known-issues doc had claimed
`GET /avatars/state` was permanently disabled on Windows due to the SEH
crash in `POST_MORTEM_v1.1.1.md`. Rereading the actual current plugin source
showed that claim was **stale** — `/avatars/state` had since been rewritten
to go through the safe `dispatchSyncRead` main-thread-queue pattern (the
same one used for `/patterns/count`), with its own `try/catch` and a
`g_capabilityAvatarStateReadback` probe flag proving it had run to
completion at least once without crashing. So the fix looked not just
plausible but low-risk. It was live-tested anyway. It wasn't safe.

### Attempt 1, live test — two failure modes in two consecutive runs

- **Run 1:** `new-project` itself succeeded, but all 3 scene-clear readback
  attempts came back `{"patterns": -1, "avatars": -1}` — completely
  unverifiable. Root cause: `dispatchSyncRead`'s internal 3-second wait was
  timing out because `QueueDrainTimer` (a 200ms Win32 `SetTimer`) wasn't
  ticking reliably that session — something the plugin's own source
  comments already admit ("does not fire reliably in every session").

### Attempt 2 (same day) — force a drain via `_get_with_drain_nudge()`

To fix Run 1's unreliable timer, added a helper that runs the GET in a
background thread and, if it hasn't returned within 0.3s, fires a
`POST /execute` concurrently to force a queue drain. This is now defined in
`client.py` but **dormant** — see why below.

### Attempt 2, live test — this made things catastrophically worse

**Run 2** (immediately after Run 1, same CLO session, nudge fix applied):
`new-project` succeeded again, but this time `wait_for_queue()` itself timed
out — `queue_processing` stuck `True`, `queue_size: 7`.

**Run 3** (same session, no restart): got worse and clearer at the same
time. `queue_size` climbed every step — `7 → 8 → 9 → 12` — with
`queue_processing` stuck `True` throughout, meaning **nothing was draining
from some point in step 2 onward, not just the scene-clear reads.** By step
4, a completely unrelated, pre-existing, unmodified call
(`step_04_import_patterns.py`'s plain `get_pattern_count()`) hung with
**zero response bytes** for over 30 seconds and needed a manual Ctrl+C —
something `dispatchSyncRead`'s own bounded 3-second internal wait should
make impossible in isolation. That pointed at something below CLO's main
thread also being out of capacity: the HTTP server's own worker thread pool.

**The leading theory, built from the `queue_size=7` arithmetic:** `7` matches
exactly "1 `new-project` (run 2) + 3 attempts × 2 leftover reads from run 1"
— as if *none* of Run 1's failed reads ever actually drained and just kept
accumulating across runs in the same CLO session. `_get_with_drain_nudge()`
was being called from inside `wait_for_scene_clear()`'s poll loop — every
0.3s, for up to 10s, across up to 3 attempts — which could fire roughly 100
`POST /execute` calls in a single `step_02` run. `/execute` has a documented
fallback: if it can't find CLO's window handle, it calls
`ProcessCommandQueue()` **directly on the HTTP server's own worker thread**
(the plugin's own comment calls this a "cross-thread CAPI risk"). If that
batch contains a command that hangs, it doesn't just wedge CLO's main
thread — it permanently consumes an httplib worker thread. Repeat that
~100 times in one run and the server's whole thread pool can plausibly
exhaust, which would fully explain the zero-byte hang on a request that had
nothing to do with this step's own code.

This was never fully proven at the time — see §5 for what later confirmed
part of it directly.

### Attempt 3 (same day) — the fix currently deployed

1. `get_scene_object_counts()` no longer calls `/avatars/state` at all —
   `"avatars"` is hardcoded to `-1` (unverifiable), pattern count is the
   only live signal.
2. `_get_with_drain_nudge()` is no longer called anywhere. Both call sites
   reverted to a plain `_get()`. The method is kept defined (documented as
   dormant, not deleted) — the concept isn't inherently wrong for a single,
   non-looped call, it's specifically unsafe inside a poll loop.
3. `step_02_new_project.py`'s scene-clear check was made **entirely
   non-blocking**: any verification failure — unverifiable readback, queue
   drain timeout — is logged as `[WARN]`/`[SKIPPED]` and the step returns
   `True` regardless, so the rest of the pipeline isn't gated on a
   verification layer that isn't reliable yet. `new_project()` itself is
   still called exactly once per run — retrying it into an already-stuck
   queue was tried and confirmed to make things worse, not better.

This is the state deployed today.

---

## 4. Why it's still not actually fixed

### 4a. The core fix was avoidance, not root-causing

Dropping `/avatars/state` from this path didn't fix a bug — it stopped
calling a code path that seemed to be triggering one. The actual mechanism
(see §5) was never conclusively confirmed, just circumstantially
implicated. If something else in this pipeline ever needs avatar-count
verification again, the same risk is still there, unaddressed.

### 4b. New finding while writing this doc: the scene-clear gate can no longer succeed at all, even when it should

This wasn't caught by any prior doc. Current `client.py`:

```python
def get_scene_object_counts(self) -> dict:
    patterns = self._get("/patterns/count")
    return {
        "patterns": patterns.get("count", -1) if patterns.get("success") else -1,
        "avatars": -1,   # always, now — see Attempt 3 above
    }

def wait_for_scene_clear(self, timeout=10.0, poll_interval=0.3) -> dict:
    ...
    if last["patterns"] == 0:      # <- only checks patterns
        return last
    ...
```

`wait_for_scene_clear()` itself is fine — it only checks `patterns == 0` and
correctly returns as soon as that's true. The bug is one layer up, in
`step_02_new_project.py`, which was never updated after Attempt 3 removed
the avatars signal:

```python
counts = ctx.client.wait_for_scene_clear(timeout=10)
if counts["patterns"] == 0 and counts["avatars"] == 0:   # <- avatars is ALWAYS -1 now
    print(f"  Scene confirmed clear (readback attempt {attempt}).")
    return True

if counts["patterns"] == -1 or counts["avatars"] == -1:  # <- ALWAYS true now
    print(f"  [WARN] Scene-clear readback unverifiable ({counts}, attempt {attempt}).")
```

Since `counts["avatars"]` is hardcoded to `-1` forever, the success branch's
`and counts["avatars"] == 0` can **never** be true again — not because the
scene isn't clearing, but because the field it's checking was intentionally
neutered in a different file and this file was never told. Every single run
since Attempt 3 shipped falls through to the `[WARN]`/`[SKIPPED]` branch and
logs "Scene-clear readback unverifiable," **even on runs where
`patterns == 0` read back correctly and quickly** — which the status doc
elsewhere correctly notes has been happening reliably. The pipeline has been
silently downgrading a real success signal into a false "unverifiable"
warning on every run since 2026-07-24.

This is a quick, low-risk fix on its own (see §6.1) and should happen
regardless of anything else in this doc.

### 4c. No forensic instrumentation exists on the actual hang site

`TraceLog` `BEGIN`/`END` instrumentation already exists for `create-seam`,
`import-pattern`, and `import-avatar-avt` — but **not** for `new-project`,
`read-pattern-count`, or `read-avatar-state`, which are exactly the commands
implicated in this bug. When `plugin_crash_trace.log` was checked directly
during Attempt 2's investigation, the hang was confirmed unambiguously —

```
[10:52:03] [tid=47776] QueueDrainTimer tick=59 draining queue
[10:52:03] [tid=47776] QueueDrainTimer tick=59 drain call returned
[10:52:05] [tid=47776] QueueDrainTimer tick=71 draining queue
```

— with no `tick=71 drain call returned` ever appearing again, for the rest
of that CLO process's life (confirmed still ticking, still skipped, 40+
minutes later). `tid=47776` is CLO's real main UI thread. But **which
specific command was in that batch is still not known** — there's no
`BEGIN`/`END` pair around it to say so. The timing (shortly after
`new-project`, matching when this session's avatars-state polling would
have fired) is consistent with the `read-avatar-state` theory, but "timing
lines up" is not the same as "confirmed." This is the single biggest gap
between "we have a strong theory" and "we know what's actually happening."

### 4d. The deeper design question was never answered

Nobody has actually confirmed whether `NewProject()`'s internal teardown is
reliably finished by the time the command queue reports empty, under normal
(non-hanging) conditions. Attempt 1 was built to answer exactly that
question and got derailed by the hang before it could. The pipeline today
works around not knowing the answer by not checking — which is different
from having established that it's safe.

---

## 5. What's confirmed vs. still a hypothesis

**Confirmed, directly, not inferred:**
- `NewProject()` is `void` — no success signal exists in the SDK itself.
- The command queue reporting empty does not guarantee CLO's internal scene
  teardown is finished.
- CLO's main thread can hang **permanently** (not just run slowly) inside
  certain plugin-triggered SDK calls — this doesn't show as "Not Responding"
  in Task Manager and CPU sits near 0%, so it looks completely healthy from
  the OS's point of view. Once `g_queueProcessing` gets stuck `true` inside
  a hang, it never recovers on its own (the RAII reentrancy guard only
  resets on return, and a hang never returns) — the CLO process must be
  killed and relaunched. No amount of retrying or clicking the Plugins menu
  helps.
- This is the same general failure class already documented for `Simulate()`
  (see `vto-pipeline-status-26_7_24.md`) and for the original v1.1.1
  `/avatars/state` / `ExportAVT` SEH crashes (`POST_MORTEM_v1.1.1.md`) — a
  recurring pattern of specific `EXPORT_API`/`UTILITY_API` calls being
  unsafe under certain scene states or thread contexts, not a one-off.

**Still hypothesis, not confirmed:**
- That `read-avatar-state` (`EXPORT_API->GetAvatarCount()` /
  `GetAvatarNameList()` / `GetAvatarGenderList()`) specifically is the
  command inside the hung batch. This is circumstantial — same API family
  already known to be SEH-crash-prone from the wrong thread
  (`POST_MORTEM_v1.1.1.md`'s Crash 1), and the timing lines up — but no
  `TraceLog` instrumentation has ever confirmed it directly.
- That the trigger is specifically "calling this shortly after `new-project`,
  while the scene is mid-teardown" rather than a hang that could happen at
  any time this API is called. These would call for different fixes (a
  timing fix vs. an outright avoidance fix) and the difference has never
  been tested.
- The `/execute`-thread-pool-exhaustion theory for the Run 3 zero-byte hang
  on an unrelated call — plausible and internally consistent with the
  documented `/execute` fallback behavior, but never directly proven either.

---

## 6. Ideas to actually solve this, in priority order

### 6.1 Fix the dead-condition bug in `step_02_new_project.py` (do this regardless of anything else)
Cheapest possible fix, and it's actively wrong today. Either drop the
`and counts["avatars"] == 0` condition (pattern count is the only live
signal now, per Attempt 3's own design) or have `get_scene_object_counts()`
stop returning a fake `-1` for avatars and instead have `step_02` branch on
patterns alone explicitly. Either way, restores the "Scene confirmed clear"
success path that has been unreachable since 2026-07-24 and correct a
misleading `[WARN]` that's been printing on every good run since.

### 6.2 Add `TraceLog` `BEGIN`/`END` to `new-project`, `read-pattern-count`, and (if it's ever reinstated) `read-avatar-state`
The single highest-value next step for actually confirming (rather than
inferring) what's inside a stuck batch. This is a small, low-risk, additive
change — the same pattern already applied to `create-seam` and, as of the
`Simulate()` investigation, to `simulate` too. Without this, every future
hang investigation starts back at "which tick never returned" instead of
"which command."

### 6.3 Deliberately reproduce the hang once, safely, with the new instrumentation
Re-run the exact Attempt-1/2 sequence (poll `/avatars/state` shortly after
`new-project`, in a throwaway test — not wired into the real pipeline) with
§6.2's logging in place. This either confirms `read-avatar-state` as the
hang site directly, or rules it out and reopens the investigation. Do this
in isolation, not by re-enabling the real pipeline's gate, since a
reproduced hang requires killing and relaunching CLO.

### 6.4 If confirmed, test whether it's timing-specific or unconditional
Call `read-avatar-state` at a point in the pipeline with no `new-project`
nearby (e.g., mid-run, well after a scene is already stable) and see if it
still hangs. If it only hangs shortly after `new-project`, the real fix is a
short, bounded settle delay before the first post-`new-project` read — not
permanent avoidance. If it hangs unconditionally, permanent avoidance (the
current state) is the right call, but should be documented as a confirmed
decision rather than a workaround pending more data.

### 6.5 If a settle delay is the answer, reuse the pattern already proven elsewhere in this codebase
`clo_avatar_generation/avatar_runtime/step_11_save_outputs.py` already
solves a structurally similar problem — "CLO's internal work isn't done
when the API call returns" — with a small settle delay (2.5s) before the
first read, a structural sanity check, and up to 3 bounded retries. That
mitigation is proven out in production for avatar-gen's undersized-mesh
race (see `known-issue-26_7_23.md`). No need to invent a new pattern for
`new-project` if this one already works for the same underlying class of
bug.

### 6.6 If `GetAvatarCount()` really is unsafe here, look for a safer avatar-count signal instead of giving up on verification entirely
`UtilityAPIInterface.h` exposes other avatar-related calls
(`IsShowAvatar`, `GetAvatarProperties`) that go through the plain
`UTILITY_API` virtual-call surface, not the `EXPORT_API` family already
twice implicated in crashes/hangs (`ExportAVT` in the original post-mortem,
`GetAvatarCount` here). It may be possible to infer "scene has 0 avatars"
indirectly and more safely — e.g., `GetAvatarProperties(0)` returning an
empty map, or `IsShowAvatar(0)` behavior on an empty scene — worth checking
against the real SDK header rather than assuming pattern-count-only
verification is the ceiling. Needs the same end-to-end proof-before-trust
discipline as any other new call (Rule 3/4 below).

### 6.7 Longer-term: build resilience around the hang class, not just prevention of specific triggers
This bug, the `Simulate()` hang, and the original `ExportAVT`/`GetAvatarCount`
SEH crashes are now three separate instances of the same underlying
fragility: certain CLO SDK calls are unsafe under certain scene states or
thread contexts, and CLO provides no way to recover once one hangs — only
an external kill-and-restart. Chasing down every individual trigger is
necessary but may never be complete. Worth considering, separately from any
single bug fix:
- A watchdog that detects `queue_processing` stuck `True` for more than a
  few seconds (trivially checkable via `/status`, already polled by
  `wait_for_queue()`) and surfaces a clear "CLO has hung, kill and restart
  it" signal to whoever is running the pipeline, instead of a generic
  30-second timeout exception that looks like ordinary slowness.
- Treating "first request after a fresh CLO restart" as a known-riskier
  window generally (this already has one documented precedent — the
  undersized-mesh race in `known-issue-26_7_23.md` — and now a second,
  circumstantial one here), and considering whether pipeline tooling should
  proactively recommend one throwaway warm-up run after every CLO restart.

---

## 7. Applying the existing "Rules for Next Time" from the original post-mortem

`POST_MORTEM_v1.1.1.md` already wrote down 5 rules from the first time this
exact class of bug appeared (`/avatars/state`'s SEH crash, `ExportAVT`'s SEH
crash). Worth checking this investigation against them directly:

1. *Never call CLO API from the HTTP thread on Windows* — not violated here;
   `read-avatar-state` already goes through `dispatchSyncRead`'s main-thread
   queue pattern, same as the safe calls.
2. *SEH exceptions require `/EHa` or `__try/__except`* — not directly
   relevant; this bug is a **hang**, not a crash, so no exception is even
   being thrown to fail to catch. This is arguably a **new, quieter failure
   mode** in the same family, not covered by the original rules at all —
   worth adding a Rule 7 in a future revision of that doc: *"A CLO API call
   can also hang the calling thread forever, with no exception and no
   Task-Manager-visible symptom — this defeats `catch(...)` entirely, since
   there's nothing to catch. Reentrancy guards prevent a second hang from
   compounding the first, but do not prevent or recover from the first
   one."*
3. *Test every new CLO API call end-to-end before shipping* — this is
   exactly what Attempt 1's live test was doing, and it's why the problem
   was caught before shipping broadly rather than after.
4. *New capabilities default to `false` until proven stable* — followed;
   `has_avatar_state_readback` is probe-gated, not hardcoded true.
5. *Diagnostic resilience: always write output before raising* — followed;
   `step_02_new_project.py` never raises past the pipeline, it always
   returns and lets the run continue with a warning logged.

---

## 8. Where to look for more detail

- Full attempt-by-attempt narrative (source for most of §3): `vto-pipeline-debug-plan-26_7_24.md`, "Bug 1" section and its "New open issue" addendum.
- Comparison with Step 1's equivalent (and lack of) safety net: `known-issue-26_7_23.md`, "Step 3 has a stale-scene safety check... Step 1 does not."
- Original SEH-crash incident and the 5 rules referenced in §7: `.claude/research/step-1/POST_MORTEM_v1.1.1.md`.
- The sibling hang investigation for `Simulate()` (same failure class, different call site): `vto-pipeline-status-26_7_24.md`.
- Live evidence for the confirmed hang in §5: `clo_workspace/logs/plugin_crash_trace.log`.
- Current (buggy per §4b) code: `clo_vto/native_vto/client.py` (`get_scene_object_counts`, `wait_for_scene_clear`) and `clo_vto/native_vto/step_02_new_project.py`.

---

# 9. Update 2026-08-20 — the hung command is now identified directly, and it is `new-project` itself

Added after a live reproduction during avatar-generation testing. **This closes
§4c's gap for this occurrence**: that section said *"which specific command was
in that batch is still not known — there's no `BEGIN`/`END` pair to say so."*
For this hang it is known, by elimination rather than by instrumentation.

## 9.1 What happened

A website-triggered avatar generation (`aj_f2511fd23c777267`, user
`u_5c939be0e3cff36f`) failed at `step_07_import_base_avatar`:

```
CLO queue did not drain within 30s.
Last status: {'queue_processing': True, 'queue_size': 0, ...}
```

Steps 01-06 all passed. The failure was on the **first CLO command of the run**.

## 9.2 The trace evidence

From `clo_workspace/logs/plugin_crash_trace.log`:

```
[10:40:38] [tid=17564] QueueDrainTimer heartbeat tick=187301 queueProcessing=false
[10:40:39] [tid=17564] QueueDrainTimer tick=187306 draining queue
[10:40:39] [tid=17564] QueueDrainTimer tick=187307 SKIPPED — g_queueProcessing already true
[10:40:40] [tid=17564] QueueDrainTimer tick=187308 SKIPPED
   ... every tick thereafter, still SKIPPED 40+ minutes later
```

**No `tick=187306 drain call returned` exists anywhere in the file.** The last
successful return in the whole log is `[00:31:30] tick=99730` — a previous
session.

CLO was healthy and idle for nine unbroken minutes before this
(`queueProcessing=false` heartbeats from 10:31:09 through 10:40:38), so this
was not a pre-existing wedge that the run merely walked into.

## 9.3 Why the command is identifiable this time

`clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py` does
exactly this before the failure point:

```python
ctx.logger.info("Starting new CLO project")
new_project_result = ctx.client.new_project()
ctx.client.wait_for_queue(timeout=30)      # <- raised here
```

`wait_for_queue` only polls `GET /status`, which is a read and not a queued
command. So **the batch that started draining at 10:40:39 contained exactly one
command: `new-project`**, sent at 10:40:37.

`NewProject()` hung CLO's main thread (`tid=17564`) on its own.

## 9.4 What this means for §5's open hypothesis

§5 lists as *"still hypothesis, not confirmed"* that `read-avatar-state`
(`GetAvatarCount()` / `GetAvatarNameList()` / `GetAvatarGenderList()`) is the
command inside the hung batch.

**That theory cannot explain this occurrence.** Step 07 never calls
`/avatars/state`, and no scene-clear readback exists on the avatar-generation
path at all. `NewProject()` alone is sufficient to hang CLO permanently.

This does **not** disprove the avatar-state theory for the *earlier* VTO-side
hangs — those had a different call sequence, and both may be true. What it does
establish is that **`new-project` is a hang site in its own right**, which §4d
suspected (*"nobody has confirmed whether `NewProject()`'s internal teardown is
reliably finished"*) but never demonstrated.

It also means avoiding `/avatars/state` — Attempt 3's central mitigation — does
not make `new-project` safe. The current pipeline avoids the wrong thing.

## 9.5 A concrete asymmetry this exposed: avatar-gen never got Attempt 3's mitigation

Attempt 3 (§3) made the VTO pipeline's `clo_vto/native_vto/step_02_new_project.py`
entirely non-blocking — every verification failure logs `[WARN]`/`[SKIPPED]` and
the step returns `True`.

**`clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py` was never
given that treatment.** It calls `wait_for_queue(timeout=30)`, which raises
`TimeoutError` (`clo_avatar_generation/adapters/clo_native_client.py:104`). So
the identical underlying bug is *tolerated* in one pipeline and *fatal* in the
other.

To be fair to the mitigation: it would not have saved this run. CLO was
genuinely wedged, so the subsequent `import_avatar_avt` would have failed too.
The gain would have been an accurate failure message instead of something that
reads like ordinary slowness.

## 9.6 ~~Session age as a risk factor~~ — REFUTED the same day, keep reading

The first version of this section noted that the hung run happened ~10.4 h into a
CLO session while the 2026-08-09 success was ~5.5 h in, and suggested session age
might be a risk factor.

**That is wrong. See §9.9 — a six-minute-old CLO instance hung identically.**

The refuted table is kept only so nobody re-derives the same dead end:

| Run | Tick | CLO session age | Outcome |
|---|---|---|---|
| 2026-08-09 guest avatar | ~99,700 | ~5.5 h | succeeded |
| 2026-08-20 10:40 run | 187,306 | ~10.4 h | hung |
| 2026-08-20 11:10 run | **1,824** | **~6 min** | **hung** |

Session age does not predict this. Do not spend time on it.

## 9.7 What this adds to §6

§6.2 (add `TraceLog` `BEGIN`/`END` to `new-project`) is **more valuable than the
original priority order suggests**, and should now be considered confirmed-useful
rather than speculative: this occurrence was only identifiable because the batch
happened to contain a single command. Any batch with two or more commands would
have been just as ambiguous as before.

Two additions:

- **§6.8 — give `step_07_import_base_avatar.py` the same non-blocking treatment
  as `step_02_new_project.py`, or deliberately decide not to and record why.**
  The current split looks accidental rather than chosen.
- **§6.9 — implement §6.7's watchdog now, not "longer-term."** `queue_processing`
  stuck `true` with `queue_size == 0` is trivially detectable from `/status`,
  which `wait_for_queue` already polls every 0.3 s. Surfacing *"CLO has hung —
  kill and restart it"* instead of a generic 30-second timeout would have made
  this diagnosis immediate rather than a log-forensics exercise. It matters more
  now that website users trigger runs: a wedged CLO fails every queued job in 30
  seconds each, silently, with no operator present.

## 9.8 Recovery, confirmed again

As §5 states and this occurrence re-confirms: **CLO must be killed and
relaunched.** `g_queueProcessing` never resets, because the RAII reentrancy guard
only clears on return and a hung call never returns. Retrying, reloading the
plugin, or clicking the Plugins menu does nothing. The process shows no
"Not Responding" state and near-zero CPU, so it looks perfectly healthy from
outside.
