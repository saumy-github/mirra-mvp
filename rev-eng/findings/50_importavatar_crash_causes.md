# 50 - Non-version-mismatch crash/hang causes of ImportAvatar(.avt) and clear-avatars (lane BB)

*Status: complete within the time limit; static analysis only, CLO not run. Tags: [V] = seen in disassembly or earlier verified finding, [I] = inference, [E] = empirical (from the logs/other findings). Script: `scripts/disasm_fn21.py` (cache `raw/disasm21/`). Date: 2026-10-30.*

## 0. What the code actually does (new in this lane)

ImportAvatar worker `0x50e3fc0` (RVA, exe base 0x140000000) is thin [V, full body read]:
* No guard of any kind: it does not test `[App+0x30]`, `[AvatarManager+0x88]`, `[AvatarManager+0x3fb]` or the busy flags that the `ImportFile` dispatcher (0x2d8f090) tests. It never even calls `App::Instance()`.
* Builds two empty `std::list`-style sentinels (0x38-byte nodes via `operator new` 0x70d91b8, **no null check after the allocation**), constructs a loader context `0x39f6b20 -> 0x39f6090`, converts the path to a `std::wstring` (0x66668a0), then calls `0x39fed10(ctx, wpath, imp, &listB, &listA)`.
* If `0x39fed10` returns false: calls `0x1d68810` + a function pointer at `[0x14822be8 8]` with string `"Avatar Load Failed."` (ref 0x890f790), then cleans up and returns **false**. This is a UI report (message/toast, [I] possibly modal) not an exception. Success returns true.
* No try/catch in the body (only the stack cookie at 0x14a172d40); the `.pdata` handler cannot be seen with dumpbin /disasm. [V no inline handlers; [I] whether a C++ unwind handler is registered].

`0x39fed10` [V]: logs `"Load Avatar ... %s [%0.2f]"` with elapsed time (xmm6 from timer 0x6822210/0x68223d0), builds a loader object `0x39f6090` (calls `0x1c22f90` = scene singleton getter then `0x5cca470`; the result is stored in `ctx+8` **with no null test**), then `0x39fc9f0` = the real loader in `MVAvatarLoader.cpp`.

`0x39fc9f0` [V]: stack frame 0x63F8 bytes (~25.5 KB, `__chkstk` 0x70d9720), `operator new(0x3A0)` for an archive object (null-tested, ctor `0x3ba17a0`), then `0x3bd0d90` (extract/unzip), and on failure the strings `"Failed to read the Avatar file. Unzip error."`, `"Unzip error - %1, log=%2, free disk space=%3"` (so a disk-space problem during decompress is explicitly considered), then `goto 0x1439FEC20` (return false). On success it parses the text metadata with `sscanf` style formats (`Version: %d|^^|`, `AvatarID: %[^|^^|]|^^|`, `Model: ...`, `ModelParameter: %f %d x7`, `Property: ...`, `Size:`, `Pose:`, `ArrangementBV:`, `Accessory: n`, `Measure:`, `AvatarTape:`), errors `"Failed to load. The file was created in a higher version."`, `"Failed to read the Avatar meta file - avatarModelPath"`, `"Invalid Avatar file path."` (and Hair, Left/Right Shoe, Size, Arrangement BV/Point). Its callee list contains `0x1bf5d20` (AvatarManager) x9, `0x50d1640` (current avatar) x5, and the 0x4b78600 (modal info box) x10, i.e. **many error paths pop modal boxes**.

Container side (`0x3bd0d90` [V]): if `[arch+0x1c0]==0` (not yet decrypted) it calls `0x4b70a00` (test) and, if false, `0x6260840` (decrypt/prepare, 6 args); then `0x4b707b0` (singleton) and `0x4b6e390` (extractor with a **HIT / MISS / "HIT (race-resolved)"** cache, strings at 0x88a5fd8..). No read of header bytes 0x20 or 0x24 was found in `0x3bd0d90`, `0x3ba18d0` or the visible part of `0x4b6e390`. `0x3ba1a70` is only the **initializer** of the magic-kind table (writes the `" AVT        CLO "` etc. strings at rdata 0x884c128..0x884c470 into a map), it is not the reader. The reader that parses 0x20/0x24 was **not located** in the time (it is in the archive-open chain below 0x3ba2250/0x3ba17a0/0x6260840).

## 1. Ranked causes

### 1. No-document / no-UI state at the moment of the call (HIGH likelihood for a crash that is not version related) [V no guard, I fault site]
* `ImportAvatar` has no `[App+0x30]` document guard (confirmed by the worker above, which has no guards at all), unlike `ImportFile`. The loader fetches the scene singleton `0x1c22f90 -> 0x5cca470` and stores it unchecked ([V], 0x439F60D5..0x439F60E2). Later code in `0x39fc9f0` uses AvatarManager (`0x1bf5d20` x9), `0x1be0fc0` (a global object, at 0x439FCB0E) and `0x6155870` with the object returned. Anything dereferenced there while CLO has just started, is showing a modal dialog, or is between `NewProject` and the scene being rebuilt faults. 
* Evidence in log: the 6 `import-avatar-avt` crashes are ones where the session had 0 completed commands (file 49), i.e. the import was the **first command after CLO start** - exactly the "no fully initialised document/scene" state. The 287602 crash happened with 224/224 and a library avatar (FV...), still first command in session [E].
* Test (experiments harness): (a) `health` then immediately `import-avatar-avt` of the small base avatar with no prior command, repeated over cold CLO starts; (b) the same after `new-project`; (c) wait N seconds after CLO start (poll until main window + a trivial `get-avatar-count` succeeds) then import. If (c) never crashes and (a) does, it is the startup race.

### 2. Re-entrancy / called while CLO is busy (modal box, mid-load, Qt event nesting) (HIGH) [V flags exist for other paths, I for this one]
* `ImportAvatar` never tests `[mgr+0x3fb]`, which `ImportFile` (via `0x50ef380`) and `DeleteAvatar` (0x50c00b0, [V] file 24) both do; and it skips the dispatcher gates (`0x6154da0` busy byte `[obj+0x24]`, `0x6154e10`). So a plugin call arriving from a timer / `WM_` message while CLO is in an ImportFile load, a project load, a modal info box (many in the loader: 0x4b78600 x10, 0x4b786c0) or a simulation step will run the loader nested inside another avatar operation, in the same thread. The loader mutates the AvatarManager list and the scene (adds to `scene+0x238` list), which the interrupted operation may be iterating -> iterator invalidation / use after free [I].
* Specific amplifier: the loader opens modal boxes on every failure path ("Invalid Avatar ... file path", "Failed to load. The file was created in a higher version."). A modal box pumps the Qt event loop, so the plugin's next timer tick can fire the **next queued command inside the box** (re-entrancy into AvatarManager). That matches "BEGIN with no END" followed by a dead process [I].
* Test: queue two `import-avatar-avt` commands back to back (concurrency 1 should serialise them; the harness should assert only one `BEGIN` without `END` at a time); import of a deliberately invalid path (expect "Invalid Avatar file path" box) followed by another command; observe whether the log shows a nested BEGIN.

### 3. clear-avatars (DeleteAvatar 0x50c00b0) UI cleanup storm with null/partial UI (MEDIUM-HIGH) [V code, I fault]
* Wrapper: `0x5fad0e0` copies shared_ptrs first, so stale pointers are not an issue [V file 24]. The worker then performs the unguarded "UI cleanup storm" through `App->[0x60]` vtable slots (0x18/0xA8/0x30/0x28), `App->[0x30]` vtable (0x78/0x48/0x20/0x220), `0x61548a0`, `0x61548b0`, `App->[0x68]` and `0x5d52120(0x1c23000())` (sim reset) with no null tests on `[0x60]/[0x68]` (file 24: only `[App+0x30]` is ever tested, and only in NewProject). Fault if any of these UI objects is null (CLO not fully built, headless) or if the sim shared_ptr (`sim+0x6a0`) refers to a solver being destroyed [I].
* `mgr+0x3fb==1` makes it silently do nothing but the wrapper still returns true [V]; this is a **silent no-op**, not a crash, but it makes the harness believe avatars were cleared, so the following `import` stacks on top (see 6).
* The 3 observed `clear-avatars` crashes are in the early 44724..45294 region where each was in a fresh session, i.e. again before the scene was settled (cause 1) [E].
* Test: `clear-avatars` on empty scene (should return false cleanly); `clear-avatars` immediately after CLO start; `clear-avatars` while a garment is simulating (`simulate N` queued before); `clear-avatars` twice back-to-back.

### 4. Importing while an avatar is selected / animation or pose layer / garment sim exists (MEDIUM) [I]
* `ImportFile(.motion)` explicitly warns "Loading a motion will delete all existing avatar animation layers" (file 36), so animation layers are a known source of state that other operations must handle. `ImportAvatar` `0x39fc9f0` calls `0x50d1640` x5 (current-avatar getter = last in `scene+0x238` list) and reads `Pose:`/`UseOldPose:` metadata; with an animation/pose layer attached to the previous avatar, the new avatar's pose application plus `0x577fb30`-style post steps (ImportFile path) have undefined interplay. The `mgr+0x98` current pointer is re-pointed to list[0] on delete but `0x50d1640` returns the **last** (file 24), so two parts of the loader can disagree about which avatar is "current" -> wrong-object access after a clear that leaves several avatars [V mismatch, I effect].
* Test: import A, `simulate` a few steps with a garment, import B (no clear); import with the avatar selected via UI; import after a `.pos` load.

### 5. Same avatar twice / stacking without clear (MEDIUM-LOW, memory) [V append behaviour via file 36, I crash]
* The loader appends (no delete-all call on the plain `.avt` path). Each 34 MB .avt allocates a decompressed model, so repeated imports without `clear-avatars` raise commit; AvatarID duplicates are not rejected anywhere visible (strings show `AvatarID: %[^|^^|]` is only parsed). The cache in `0x4b6e390` is keyed with HIT/MISS/race-resolved, a **race-resolved path** suggests that a second import of the same blob while the first extraction cache entry is still being filled goes down a different branch [I].
* Test: import the same patched .avt 5 times with working-set logging (`GetProcessMemoryInfo` sampled by the harness, 34 MB file); expect linear growth, find if a crash threshold (32-bit counters? no, x64) occurs; then import twice after `clear-avatars` to test stale cache interplay.

### 6. Huge .avt (34 MB) / disk space / memory (MEDIUM-LOW) [V explicit error path, I as crash]
* The loader has a dedicated message `"Unzip error - %1, log=%2, free disk space=%3"` [V]: decompression writes into a temp directory, so low free disk space on the temp drive is a designed failure case; it returns false (not a crash) unless the error box is raised while another operation is mid-flight (cause 2). The 0x63F8 stack frame plus nested std::string is fine on the main thread (1 MB+), but if the command is ever run on a worker thread with a small stack it is a risk [I, low].
* Test: import with temp drive nearly full (harness cannot do that safely; instead log free space before each import and correlate with the 9 unmatched BEGINs).

### 7. Malformed / stale header (0x24 ZIP length) (LOW) [E strongly, V partial]
* Empirical: 113 of 379 files with a stale 0x24 (-593..-610 bytes) are imported fine (files 10, 13, 31) and the digest over the prefix stays valid. In code, no read of header bytes 0x20/0x24 was found in the extract path (`0x3bd0d90`, `0x3ba18d0`); the ZIP is evidently located via 0x20 (offset), and the zip end-of-central-directory is found by scanning, so a stale length is harmless [I - reader not located, so not [V]]. Stale 0x24 is therefore **not** a plausible crash cause for the observed failures; a **wrong 0x20 offset or truncated ZIP** would give the handled "Unzip error" branch (returns false), not a crash. 
* Version/metadata text parse errors are handled by the "created in a higher version" / "Invalid Avatar ... path" boxes [V]. The sscanf-style `Model:`/`Measure:` field parsing uses `%[^|^^|]` into fixed buffers on the 0x63F8 frame; an over-long field in a patched file could overflow (the stack cookie would turn this into a fast-fail, i.e. a crash that looks like a hang) [I, needs a patched file with long fields].
* Test: import a copy with 0x24 zeroed (expect success), with 0x20 off by 1 (expect "Unzip error" and clean false), with a truncated ZIP, and with an over-long `Model:` string; the harness must catch the modal box (cause 2) so use CLO log, not the box.

### 8. Exceptions without handlers (LOW-MEDIUM) [V no inline handler, I rest]
* No try/catch in the wrapper or worker; failures that throw (std::bad_alloc from `operator new` in the loader, `stod`-like conversions, STL out_of_range) propagate to whoever calls into the plugin API. The plugin's own REST thread/queue code would need a handler around the API call; an escaped C++ exception across the Qt/Windows boundary terminates CLO silently (no END). The `0x70d91b8` allocations in 0x50e3fc0 are unchecked, so true OOM is a null deref rather than an exception.
* Test: inspect plugin `RestPlugin_windows.cpp` for try/catch around `ProcessCommandQueue` (not done here, outside rev-eng); in the harness, import with memory pressure.

### 9. Stale shared_ptr after DeleteAvatar (LOW) [V]
* Wrapper copies shared_ptrs before removal; removed avatars are pushed to the `mgr+0xD0` vector to be kept alive until later cleanup (file 24) [I]. A later `ImportAvatar` reusing `mgr+0x98` after all avatars were deleted starts from null current and scene pointer reset by `0x50c0b90`; the loader goes through `0x1c22f90`/`0x5cca470` again, which is the null-scene risk of cause 1 if the scene pointer has not been rebuilt [I].

## 2. Summary table

| Rank | Cause | Evidence | Status |
|---|---|---|---|
| 1 | Import before document/scene ready; no guards on the worker | 0x50e3fc0 full body; 0x39f6090 stores `0x5cca470(0x1c22f90())` unchecked; 6 crashes were first commands of fresh sessions | guard absence [V]; fault site [I] |
| 2 | Re-entrancy via modal boxes / timers / 0x3fb ignored | no `0x3fb` test in worker, 10+ modal sites in loader (0x4b78600) | [V] sites, [I] mechanism |
| 3 | DeleteAvatar UI cleanup with null UI objects | file 24 + 0x50c00b0 unguarded `App+0x60/0x68`; 3 crashes in fresh sessions | [V] code, [I] |
| 4 | Pose/animation/sim state, current-avatar mismatch (+0x98 vs 0x50d1640) | file 24 | [V] mismatch, [I] effect |
| 5 | Repeated import / same avatar twice, extraction cache race | HIT/MISS/race-resolved in 0x4b6e390 | [I] |
| 6 | 34 MB file, disk space, memory | "free disk space" message in loader | [V] message, [I] |
| 7 | Header 0x24 / malformed ZIP | 113 stale-0x24 files load; no read of 0x24 in extract path | [E]; reader not located |
| 8 | Unhandled exceptions | no inline handlers | [V]/[I] |
| 9 | Stale shared_ptr | wrapper copies ptrs | [V] unlikely |

## 3. Open items (not done in the 12 minutes)
* Locate the actual reader of header 0x20/0x24 (look under `0x6260840` and `0x3ba2250 -> 0x3c27860/0x40ef3a0`).
* Inspect `.pdata` unwind handlers of 0x50e3fc0/0x39fc9f0 (needs a pdata parser, not dumpbin /disasm).
* Check the plugin source for a try/catch around API calls and for whether commands are marshalled to the CLO UI thread (not part of rev-eng).
* Raw artifacts: `out/bb_50e3fc0.txt`, `raw/disasm21/*`.
