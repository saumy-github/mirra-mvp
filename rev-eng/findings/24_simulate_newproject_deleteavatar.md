# Simulate / NewProject / DeleteAvatar: second-level analysis (lane R)

*Status: static disassembly only (dumpbin), CLO_Standalone_OnlineAuth_x64.exe 2026.1.336; nothing was run or hooked.*
*Date: 2026-10-29*
*Tooling: `scripts/disasm_fn6.py <RVA> [maxbytes] [--full]`, cache `raw/disasm6/`. Builds on `findings/11_impl_util_import_export.md`.*

Tags: **[V]** = visible in the listing; **[I]** = inference (not directly visible). Addresses are RVAs (VA = 0x140000000 + RVA). Time-boxed, so the cloth-solver internals (anything under 0x5cbfda0 / MVTimer) were NOT followed to the bottom.

## 0. Singletons and object layouts discovered

| RVA / global | Meaning | Tag |
|---|---|---|
| 0x1c23080 -> .data 0xa2a6c40 | **Simulation object** ("sim"), Meyers singleton. This is the same static that `Simulate` passes to the per-step function. Fields: `[+8]` enabled/running byte, `[+9]` last "has cloth" state, `[+0x6a0]` / `[+0x6a8]` = shared_ptr (ptr, ctrl) to the cloth-solver object (accessor 0x5cbb4b0 returns a copy and add-refs the control block; 0x5cbb480 returns `solver+0x28` if `solver+0x30==0`), `[+0x6b0]/[+0x6b8]` another shared_ptr (checked by 0x5cbbcc0) | [V] offsets, [I] names |
| 0x1c22f90 -> 0x9fba540, 0x1c22b10 -> 0xa2a68b0 | two further simulation-side singletons (property holder / "current sim state"). 0x5cc1fc0 reads a double at `[state+0x2b8]` (time / frame counter) before and after one step | [V]/[I] |
| 0x5cbae80 -> `*(0xa32b9e0)` | lazily `new`ed 0x3c-byte object (ctor 0x5cb5cf0) = the **MVTimer** (source path string `...\CloScene\GlobalSingleton\Simulation\MVTimer.cpp` at 0x895f540). `[timer+0x34]` = "running" byte, cleared when Simulate stops | [V] |
| 0x5cbae00 -> 0xa32c190 | another simulation singleton (sim-properties container used by 0x5cbbd70 / 0x5cbee80) | [I] |
| 0x1be0ec0 (`App::Instance`) | `[+0x30]` main window/document present, `[+0x38]` document controller object (vtable), `[+0x60]` 3D-view/UI controller (vtable), `[+0x68]` another UI object (vtable[1](0) = refresh/update) | [V] offsets |
| 0x1be0dc0 | another singleton (Scene/Document holder); 0x5cba300 returns a copy of its `shared_ptr` at `+8/+0x10` (add-ref). `[doc+0x23c]` is a flag byte checked in sim start | [V]/[I] |
| 0x1bf5d20 AvatarManager | `[+0x88]` = shared_ptr to scene object whose **avatar list** is a `vector<shared_ptr<Avatar>>` at `[scene+0x238 .. +0x240]` (16-byte elements). `[+0x98/+0xA0]` = shared_ptr **current avatar**. `[+0xD0/+0xD8/+0xE0]` = vector<shared_ptr> (begin/end/cap) used by 0x5153bf0 (a "deleted/pending" list). `[+0x3fb]` = a bool flag read by 0x50ef380 | [V] |

## 1. Simulate(steps) - RVA 0x607f070 (slot 85)

### 1.1 What a "step" is
```
bool Simulate(unsigned steps):
  sim = Sim::Instance()                 // 0x1c23080 (a2a6c40)
  SimStartStop(sim, 1, 0, 0, 0)         // 0x5cbfb40: start
  for (i = 0; i < steps; ++i)           // pure counter loop, nothing else tested
      SimOneStep(&a2a6c40)              // 0x5cc1fc0
  SimStartStop(sim, 0, 0, 0, 0)         // stop
  UIPostSim(AvatarMgr/doc singleton 0x1be1040)  // 0x5ccd3a0
  return true                           // always
```
- `SimOneStep` (0x5cc1fc0) **[V]**:
  ```
  st  = SimState::Instance()  (0x1c22b10 -> a2a68b0) -> shared_ptr copy (0x5cb9dd0)
  t0  = Repeat-holder{vtbl 0x827f760, double = st->[+0x2b8]}      // frame/time snapshot
  ok  = MVTimer_Update(MVTimer::Instance())   // 0x5cbae80 -> 0x5cc1da0   (returns bool, kept in ebp)
  t1  = Repeat-holder{ ..., st->[+0x2b8] }
  changed = !(t0 == t1)               // 0x538ba40 = !equal
  if (changed && App->[0x30] != 0)
      App->[0x68]->vtbl[1](0)         // viewport/UI refresh after every step whose time advanced
  return ok
  ```
  `Simulate` ignores the return value of `SimOneStep`, so a failed/no-op step is invisible.
- `MVTimer_Update` (0x5cc1da0) **[V]** structure: `solver = sim->[+0x6a0] shared_ptr`; if solver non-null and `0x3f40e60(solver)` true ("has something to simulate" *(I)*): reads elapsed time from a Qt-style timer (0x68223d0 ctor via IAT 0x822ba68, 0x6822210 elapsed = `(now - last)/freq` returned as double; last := now), calls `0x5cbfda0(timer, state)` (the real per-frame update; contains the "Folding" and "Draping" strings, so it distinguishes simulation modes), stores the frame dt as `float` into `timer[0]`, reads 5 doubles from solver vtable slot `+0x108` into `timer[4..0x14]`, returns 1. Else-branch (no solver / nothing to simulate): `0x5cbbd70(0x5cbae00())` (reload sim properties); if true -> `0x5cbee80(0x1c22b10())` (re-reads properties) and returns 1, otherwise returns 0 **[V]**.
- So a "step" is **one MVTimer frame update** (one call of the CLO "simulate frame" routine, which internally uses `uiSubStepCount` sub-steps and `fEntireTimeStep`). It is neither a raw CG iteration nor a wall-clock tick *(I)*: the property names read by 0x5cbee80 are `fGravity`, `fEntireTimeStep`, `uiSubStepCount`, `uiCGIterationCount`, `fCGResidual`, `uiSelfColIterationCount`, `fAirDamping`, `bNonlinearSimulation`, `fStrength`, `bApplyFabricToAll`, plus stiffness keys `fSuK fSvK fRightShearK fLeftShearK fBuK ...` (strings 0x895f730..0x895f7e0) **[V]**. Gravity and time step therefore live in the sim property set, not in the Simulate argument.

### 1.2 Start / stop (0x5cbfb40 `SimStartStop(sim, bool start, bool, ptr, ?)`) **[V]**
```
if (start && PreCheck()) return;          // 0x5cbb700
sim->vtbl... 0x4fc1170(0x5cca470(0x1c22f90()), start, r8, r9, stackbool)   // enable/disable the sim in the AvatarManager/solver:
        // 0x4fc1170 touches AvatarManager (0x1bf5d20), 0x50ef390/0x50f2830 (avatar queries), 0x5cbf8a0 (= sim->[+8]=flag; propagate to solver), 0x6153f00/0x6154e10 (UI), 0x5cd0220/0x3f2b840/0x3f09640 (solver reset), 0x5130c10 (avatar side), App->[0x60]... vtbl[+0x2f8]
if (start) { if (scene present && scene->[+0x23c]==0 ...) } ; if (!started-condition) timer->[+0x34] = 0
on stop: MVTimer->[+0x34] = 0
```
- **PreCheck 0x5cbb700 contains a modal dialog**: if the scene has any "Button" whose thread length is negative (`list from 0x5cfe9f0(0x1bf5e20())`, per-element test 0x4749c70 then vtable `+0x910`), it shows a question box with text `"Buttons with negative thread lengths may cause Simulation to be unstable. Would you like to proceed?"` (string 0x895f6c0) through `0x4b78650(..., 6/7 buttons)`; the result decides whether start is skipped. **A modal `QMessageBox` runs its own nested event loop and blocks `Simulate` forever on an unattended machine.** Only reachable when a garment has buttons with negative thread length. **[V]** (dialog), **[I]** (reachability).
- `Simulate` has **no guard** for "no avatar"/"no garments": `Simulate(N)` on an empty scene runs N cheap no-op steps (else-branch of MVTimer_Update returns 0) and still returns `true`. **[V]/[I]**
- `steps == 0`: start, loop skipped, stop, post-refresh, return true. It is a harmless "toggle on/off + refresh". **[V]**

### 1.3 Blocking, Qt events, cancel
- It is a **synchronous loop on the calling thread**; control returns only after `steps` frame updates (+ stop + refresh). **[V]** No `Sleep`, no wait on a worker visible in `Simulate`/`SimOneStep`/`MVTimer_Update` top level. Whether 0x5cbfda0 internally waits on a worker pool (3a29c60 -> 0x143a5f820, 6739ac0 not resolved) is **not determined**.
- **Qt event processing**: no `processEvents`/`sendPostedEvents` call appears in Simulate, SimStartStop, SimOneStep, MVTimer_Update top levels, or in AvatarManager::DeleteAvatars. Remaining re-entrancy sources: (a) the per-step `App->[0x68]->vtbl[1](0)` refresh (if it is `QWidget::repaint()` it paints synchronously but does not dispatch queued events; unresolved), (b) the modal message box in PreCheck (nested event loop = definite re-entrancy), (c) 0x5cbfda0 internals (unanalysed). **Net: re-entrancy risk is low but not zero**; the plugin's WM_ message pump is only dangerous if it dispatches the same REST command queue while a modal box is up.
- **No cancel path**: the loop reads no flag besides the counter. The only stop is finishing the loop (or killing the process). **[V]**
- Return value is constant `true`; the plugin cannot tell success from failure (`asyncResult.success` for "simulate" is meaningless).

## 2. NewProject - RVA 0x60342c0 (slot 55)
```
log(2, "...NewProject(void)")
if (App->[0x30] != 0) {                       // 0x14603442D..37; skipped silently otherwise (no crash)
    App->[0x38]->vtbl[3]()                    // call [rax+18h]: the "new/clear document" worker
    App->[0x60]->vtbl[1]()                    // call [rax+8]: (3D/UI controller) reset, NOT null-checked
    FileNameHolder::Instance() (0x1c5fb60)->Set(std::string("NULL"))   // 0x5d827f0; literal 0x4C4C554E
}
```
- **[V]** sequence and the "NULL" file-name reset. **[I]** (virtual targets not resolved without the exact dynamic type of `App[0x38]`): vtable slot 3 clears garments/patterns/scene state; the plugin author's empirical comment ("NewProject() clears garments only, so avatars survive it and accumulate", RestPlugin_windows.cpp ~l.1301/1976) agrees with the fact that **NewProject never touches AvatarManager** (0x1bf5d20 is not referenced in the function or its direct code). Avatars are held by AvatarManager (`[+0x88]` scene list), not by the document that vtbl[3] resets.
- Does not take an undo-stack/unsaved-changes prompt at this level (no message box call in the wrapper). Whether vtbl[3] prompts is unknown. **[I]**
- Crash conditions: `App->[0x60]` is dereferenced without a null test (only `[+0x30]` is tested). In a headless run (`--headless` option exists, IsHeadless 0x6268a40) if `[+0x30]` is non-null but `[+0x60]` is null this would fault; not expected in the GUI standalone. **[I]**

## 3. DeleteAvatar(indices) - RVA 0x5fad0e0 (slot 264) and AvatarManager::DeleteAvatars - RVA 0x50c00b0

### 3.1 Semantics of the argument
- `indices` are **positions in `AvatarManager::GetAvatarList()` at the moment of the call** (0x50ccb70, the vector at `scene+0x238`), NOT uids. **[V]** (wrapper from file 11.) The wrapper first converts *all* valid indices to `shared_ptr<Avatar>` copies (`selected`), and only then calls `0x50c00b0(mgr, &selected, ...)`. Because pointers (not indices) are captured before any removal, **ordering and index shifting while deleting several avatars is not a problem**: `[0,1,2]` removes the first three of the list as it was; duplicates would be processed twice (second deletion finds nothing; harmless? *I*). Out-of-range indices are skipped; if none valid, `false`.
- A second dedup is not done, so `[0,0]` calls the remover twice on the same avatar *(I)*.

### 3.2 What 0x50c00b0 does **[V]**
```
DeleteAvatars(mgr, vector<shared_ptr<Avatar>>* sel, ?, bool, bool recordUndo):
  if (sel.empty() || scene(mgr+0x88)==null || mgr->[+0x3fb]==1) goto done      // flag at +0x3fb: re-entrancy/busy/"loading" guard *(I)*
  snapshot = copy of scene avatar list (for undo)
  if (Scene exists (0x1c098c0) && recordUndo) undoCmd = new 0x68-byte command titled "Delete Avatar" (0x8279790)
  for each a in sel (given order):
      0x50bcb10(a, undoCmd)                     // per-avatar detach: releases per-avatar attachments at avatar+0x798.., calls avatar vtbl[+0x2b0] (remove from scene)
      if (a.ptr == mgr->[+0x98].ptr) {          // equality 0x2a504c0 on raw pointer
          if (scene.avatarList.size() > 0)  mgr->current = dynamic_cast<Avatar*>(scene.avatarList[0]) // 0x1d73760 on [+0x238] = FIRST element
          else                               mgr->current = null (ptr=0, ctrl=0)
      }
      0x5153bf0(mgr, a)                         // push_back a into vector at mgr+0xD0 (keeps it alive until later cleanup) *(I)*
  0x50c0b90(mgr)       // if list now empty: reset scene ptr and call 0x5130430 / 0x512c5d0 (clears current/selection)
  UI cleanup storm via App->[0x60] vtbl +0x18/+0xA8/+0x30/+0x28, App->[0x30] vtbl +0x78/+0x48/+0x20/+0x220,
     0x61548a0->vtbl+0x100, 0x61548b0->vtbl+0xB8 / +0xD0, App->[0x68] vtbl+0x10, 0x5d52120(0x1c23000()) (sim/scene reset), App->[0x30] vtbl+0x20
  if (undo) push undoCmd to the undo stack (0x3b24020 -> 0x3b24740)
```
- All of this is **synchronous**; when `DeleteAvatar` returns, the AvatarManager list is already updated, so `GetAvatarCount/GetAvatarNameList` do not lag *(I; no deferred posting seen)*. (The old crash on "absent index" came from query APIs, not from stale caches.)
- **Current avatar after deletion** (relates to lane H's `0x50d1640`): 0x50d1640 returns the **last** element of the scene avatar list (`[scene+0x240]-0x10`, null shared_ptr if scene null or list empty). Separately the manager stores an explicit current avatar at `mgr+0x98`. On deletion of the current avatar the manager re-points it to **list[0]** (first remaining), not to the last. Consequently: after deleting a subset, the "current avatar" (`+0x98`) may be a different avatar from the one 0x50d1640 would return (last). APIs using 0x50d1640 (Get/SetAvatarProperties, avatar-index lookups as described in file 11) therefore operate on the **last** avatar, whereas operations using `mgr+0x98` operate on the first remaining. **[V]** code, **[I]** which API uses which.
- Deleting *every* avatar leaves current = null and the scene pointer reset (0x50c0b90). A following `ImportAvatar` must recreate it; the plugin already tolerates this.
- The undo flag: the wrapper passes defaults (r8/r9/[rsp+20] zero), so likely **no undo command** is created from the API *(I; wrapper args not re-checked)*.

## 4. Crash / hang conditions
| Condition | Effect | Tag |
|---|---|---|
| `Simulate` with unresolved negative-thread-length buttons | modal confirmation dialog, blocks forever | [V]/[I] |
| `Simulate` with a huge `steps` and no avatar/garments | cheap no-ops, but cannot be cancelled; returns true | [V] |
| `Simulate` right after NewProject/DeleteAvatar in the same command batch | sim holds a shared_ptr to the old solver (`+0x6a0`); safe because shared_ptr (ref-counted), the else-branch handles null | [I] |
| `NewProject` when `App->[0x60]` is null | unguarded vtable call -> access violation | [I] |
| `DeleteAvatar` with empty list or bad indices | returns false (no crash) | [V] |
| `DeleteAvatar` while `mgr+0x3fb==1` | silently does nothing but wrapper still returns true | [V]/[I] |
| `DeleteAvatar` on stale avatar *pointer* | not possible through the API: wrapper copies shared_ptrs before removal | [V] |
| Calls from a non-GUI thread | No thread assertion anywhere; but the delete path calls many UI objects (App->[0x30]/[0x60]/[0x68] vtables, undo stack), so a non-UI thread risks a Qt thread-affinity crash | [I] |

## 5. Plugin recommendations (RestPlugin_windows.cpp)
1. **Never trust `Simulate`'s return value**; the REST layer should always verify by an observable (e.g. export the GLB and check the cloth moved, or `GetAvatarCount`-free probes). Rename the log "Simulation complete" to "Simulate returned (always true)".
2. **Cap and chunk `steps`** (e.g. 25-50 per request, repeated by the client). There is no cancel, so a single huge call freezes CLO and the WM_ pump; chunking keeps the watchdog/health endpoint alive between chunks.
3. **Avoid the modal**: before `Simulate`, make sure garments with Buttons have positive thread length (or skip simulation if the scene has buttons), otherwise the confirmation box can deadlock an unattended session. Consider a watchdog that detects "simulate running > N s" and logs it.
4. **`clear-avatars` is correct to pass all indices `0..n-1`**: the wrapper resolves them to shared_ptrs before deleting, so shifting is not an issue. The risk is the *count*: `g_avatarsLoaded` is only the plugin's own tally. If CLO holds extra avatars (project load, failed import that still created one), `0..loaded-1` leaves leftovers; if fewer exist, out-of-range indices are skipped (safe) and the call returns false only if none were valid. Recommended: set `deleted = true` if DeleteAvatar returns false AND tally is 0; otherwise treat false as "list already empty" and reset `g_avatarsLoaded = 0` (a false here means no valid index existed, i.e. nothing to delete).
5. **Do not rely on "current avatar" after a partial delete**; the manager re-points `+0x98` to the first remaining avatar while index-based lookups (0x50d1640) use the last. Always `clear-avatars` fully before importing a new one (already the plugin's pattern), or always address avatars by explicit index.
6. **NewProject then clear-avatars order** is correct: NewProject only resets document/garment state and the file name, never avatars; the existing "do not zero g_avatarsLoaded in new-project" comment is consistent with the disassembly (AvatarManager untouched).
7. Keep all three calls on the CLO UI thread (as the WM_ pump does). Do not call them from the HTTP worker thread.
8. No simulation of "gravity/time step" via Simulate arguments: set `fGravity`, `fEntireTimeStep`, `uiSubStepCount`, `uiCGIterationCount` through the sim property set (strings listed above) if those need tuning; not exposed by the public API in this build as far as this lane saw.

## 6. Open items (not resolved in the time box)
- Real class and target of `App->[0x38]` vtable slot 3 (what exactly NewProject wipes) and whether it can show an unsaved-changes prompt.
- Internals of 0x5cbfda0 (per-frame solver, thread-pool waits) and the exact meaning of `App->[0x68]->vtbl[1](0)` (repaint vs update).
- Which Get/Set APIs use `mgr+0x98` versus 0x50d1640 (lane H).
- Callers of 0x5cbb700's return semantic (1 = proceed or cancel).
