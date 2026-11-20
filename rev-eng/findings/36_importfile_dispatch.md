# 36 - ImportFile dispatch: extension -> handler (lane AG)

*Static analysis, CLO 2026.1.336 exe, base 0x140000000. Tags: [V] = read in disassembly, [I] = inference. Scripts: `scripts/disasm_fn13.py` (copy of disasm_fn9, cache `raw/disasm13/`), `scripts/ag_typemap.py`. Raw: `raw/ag_5d76840.txt` (extension classifier), `raw/ag_typemap.txt` (ext -> type code), `raw/ag_2d98980.txt` (file-open worker), `raw/ag_2d8f090.txt` (type dispatcher, truncated at 0x2d95090 by the cut heuristic), `raw/ag_50fcfe0.txt`.*

## 1. Call chain (verified)

```
ImportAPI::ImportFile(path, opt)  slot 1   0x6022e80
   [App+0x30]==0 -> return false
   -> CLOFileIOImpl(App+0x38) vtbl[31] = 0x1d99640(wpath, opt)
ImportAPI::ImportFile(path)       slot 2   0x6022a80
   [App+0x30]==0 -> return TRUE (does nothing)
   IsHeadless (0x6268a40) ? vtbl[32]=0x1d995d0(wpath)  : GUI branch (section 5)
   then post-step: if ext == "zprj" -> App+0x38 vtbl[44](path); return true

0x1d995d0 (slot 32): builds default option block (type -1) -> worker 0x2d98980(wpath, edx=0, r8b=1, r9d=0, [rsp+20]=default, [rsp+28]=-1)
0x1d99640 (slot 31): type = 0x5d76840(path); allowed = 0x6154bf0(0x1bf5ea0(), &type);
                     ONLY types 0x0B (obj), 0x38 (fbx), 0x55 (gltf/glb) proceed -> worker 0x2d98980(... int = opt+0xA8)
                     every other type -> return false
worker 0x2d98980:    zip/dna/"dir" pre-checks, type = 0x5d76840(path) (at 0x2d98f20), then a type switch (section 3),
                     document-class types -> descriptor -> 0x1d76190 (copy) -> 0x2d8f090;
                     everything else (incl. avs, avt, mtn, pos) -> descriptor -> 0x2d8f090 as well
0x2d8f090 (big type dispatcher): type 0x27 (avs) at 0x2d91199 -> 0x50fcfe0 (Load Avatar Size handler)
                                 type 0x03 (avt/avac/avte) at 0x2d9033b -> avatar loader 0x39fbdd0/0x39fed10
0x50fcfe0 -> per avatar: 0x510cd70-family -> 0x511a1b0 (resize driver; call sites 0x50fd450, 0x50fda06)
```
[V] for every arrow above (call/jump targets read). The `.avs` call at **0x2d911f9**: `call 0x50fcfe0(rcx=AvatarManager 0x1bf5d20(), rdx=&wstring(descriptor+0x20 = full path), r8=&tmp(0x50cf7c0(mgr)), r9=&byte flag, [rsp+20h]=0)`. On true it copies the descriptor path string (+0x20 -> +8) and calls `App+0x60 ->vtbl[3]` with zero args (refresh/notify) [V call, I meaning]. The return value of 0x50fcfe0 is *not* the return value of the whole chain (see section 6).

**Lane K's assumed link is confirmed**: ImportFile(.avs) -> worker -> 0x2d8f090 -> 0x50fcfe0 (previously "~0x50fd780" = a code region inside the function 0x50fcfe0-0x50fdfd9).

## 2. Extension classifier 0x5d76840 (extension -> type code)

Lower-cases the extension (`0x6668300`) and runs a linear chain of `0x6665260` (string equals) compares; no match -> type -1. Selected rows ([V], full list in `raw/ag_typemap.txt`):

| Extension(s) | Type | Extension(s) | Type |
|---|---|---|---|
| mtn, avacm | 0x01 | zprj | 0x1C |
| pos, avacp | 0x02 | zpac | 0x20 |
| **avt, avac, avte** | **0x03** | pacx | 0x23 |
| dae | 0x06 | tco | 0x24 |
| anm | 0x07 | smp | 0x26 |
| pan | 0x08 | **avs** | **0x27** |
| arr | 0x09 | cmp / cmt | 0x28 / 0x29 |
| mea | 0x0A | fab / zfab | 0x31 / 0x32 |
| obj | 0x0B | stp | 0x33 |
| dxf, aam, aama | 0x0E | sap | 0x35 |
| ai, pdf | 0x0F | sew | 0x36 |
| amx | 0x10 | **fbx** | **0x38** |
| mc, mcx | 0x17 / 0x18 | btn / bth | 0x3A / 0x3B |
| pc2 / mdd | 0x19 / 0x1A | sst | 0x3F |
| cak | 0x6E | zblc | 0x44 |
| gltf, glb | 0x55 | zmod / zmdr | 0x45 / 0x47 |
| vrm | 0x75 | hpos | 0x6C |
| usd/usda/usdc | 0x67 | jean, jean5 | 0x5B |
| zvrp | 0x59 | zacs / acs | 0x3E / 0x5D |
| others (cpt 0x48, zcmr 0x49, cfg 0x4C, py 0x4F, trm 0x50, axf 0x56, sbsar 0x5C, rul 0x63, grp 0x66, zse 0x6D, uix 0x71, zsl 0x5F, zss 0x5E, zpu 0x60, zst 0x61, zsd 0x4A, zpl 0x4B, zsp 0x54, ssp 0x6F, abc 0x42, rdp 0x40, ptp 0x41) | as listed | | |

**Not in the classifier: `.csv`, `.osw`, `.jfab`, `.zip`** (zip/dna are special-cased earlier in the worker, section 3). So ImportFile with a `.csv` yields type -1 (slot 31 -> false; slot 32 -> worker -> "This file format is not supported in this version." box path, see section 3) [V classifier, I for the box]. `.csv` measurement import is ImportMeasurement, not ImportFile.

## 3. Worker 0x2d98980 type switch

Pre-steps ([V]): copies path; if extension is `dna` (0x2d98a37) and a global (0x149FBC370 flag) is clear and ... returns false early; `zip`: if the zip is not openable -> modal "Please apply the file directly to the Zipper." (0x2d98d9d, only when 0x3be1450 says it is a zipper file) and return false; else for `dna` files a fast path (0x2d98e6b..0x2d98ef0) returns true; otherwise type = 0x5d76840 (0x2d98f20).

Switch on type (bit-test masks decoded):
- **0x49**: 0x519db60 -> 0x51a2a90 (camera/zcmr-like).
- **{0x0E dxf/aam/aama, 0x1C zprj, 0x20 zpac, 0x23 pacx}** (mask 0x910004000): feature gate `0x6154bf0` (returns false -> return false, no box); `App+0x38 vtbl[6]()==2` -> return; builds descriptor (type at +0, path at +0x20, bytes +0x84=0, +0x85=edx, +0x8C=1) -> 0x1d76190 -> **0x2d8f090**.
- **0x44 zblc / 0x45 zmod**: scene queries then 0x5740390 / 0x5d57990 (modular/pattern block).
- **{0x31,0x32,0x36,0x3A,0x3B,0x3F,0x41,0x56,0x5C,0x66}** (fabric/sew/button/buttonhole/sbsar/...): 0x625df70 existence check, then per-type loader (0x5cdcca0, 0x5cda8e0, 0x5cdbaa0, 0x5cdfbc0, 0x5cdd570, 0x5ce0cb0 ...) and a UI refresh via `App+0x78` vtable; on success may show "The file has been added to the Object Browser." (0x2d99a87). These are the "added to object browser" types; `ImportFile` of a `.fab`/`.zfab` etc. lands here.
- **0x6F ssp**: feature check `0x6154de0` (0xC2).
- **{0x03 avt, 0x0F ai/pdf, 0x2A, 0x2B, 0x2C}** (mask 0x1C0000008008): `App+0x38 vtbl[6]()==2` -> return (no-op); descriptor (+0x84=0, +0x8C=1) -> 0x1d76190 -> **0x2d8f090**.
- **default (everything else, including avs 0x27, mtn 0x01, pos 0x02, mea 0x0A, obj 0x0B, fbx 0x38, gltf 0x55, anm 0x07 ...)**: identical descriptor build at 0x2d99d22 (+0x80 = int param [rbp+0x918] = -1 for slot 32; +0x85 = edx(0); +0x87/+0x88 from the stack/r9 params; +0x8C=1) -> 0x1d76190 -> **0x2d8f090**. *No* vtbl[6]==2 test, and no 0x6154bf0 feature gate, for these types in the worker; but 0x2d8f090 itself re-runs 0x6154bf0 (see below).

Hence **the worker has no direct handler per extension; it routes almost everything to 0x2d8f090 with a descriptor whose first dword is the type code.**

## 4. Dispatcher 0x2d8f090 (descriptor -> handler)

Entry gates ([V], at 0x2d8f0f7..0x2d8f1b0), any failure -> return false silently (0x2d940a8..0x2d940ba `xor al,al`):
1. `0x6154da0(0x1be10c0())` = byte `[obj+0x24]` must be 0 (a "busy/locked" flag) [I meaning].
2. If App+0x40-ish object type 0x50 and type in {0x0C,0x10...}: skip (special case).
3. `0x50ef380(AvatarManager)` = byte `[AvatarManager+0x3FB]`; nonzero -> return false [I: "avatar operation in progress / locked"].
4. `0x6154e10(0x1be0fc0())` (virtual call `[obj+0x10]->vtbl+0x20`) nonzero -> return false [I].
5. `0x5cca470(0x1c22f90())` must be non-null (a scene object) else return false.
6. `0x6154bf0(0x1bf5ea0(), &type)` feature/permission switch; false -> **modal info box "This file format is not supported in this version."** and return false [V]. (`0x6154bf0` is a licence/feature table, not examined further - no licence work.)
7. `0x2d8d9a0(type)`: for types in mask 0x0FE00026 (types 1 mtn, 2 pos, 5, 0x15..0x1B) and 0x6C (hpos) it requires >=1 avatar in the AvatarManager (`0x50db800`); if none -> info box **"No Avatars found."** (0x83826b0) and return false [V]. **avs (0x27) and avt (0x03) are NOT in this set.**

Then per-type handlers (selection; the function is 5000+ instructions and was only scanned for the types Mirra uses):

| Type | Handler | What it does |
|---|---|---|
| 0x02 pos | block at 0x2d8f579 | pose; settings key `CurrentPoseFilePath` |
| 0x03 avt/avac/avte | 0x2d9033b | see section 4.1 |
| **0x27 avs** | **0x2d91199 -> 0x50fcfe0** | Load Avatar Size (section 4.2) |
| 0x0A mea | 0x2d91251 | measurement file (not examined here) |
| 0x0B obj | 0x2d90eaf.. | object import ("Failed to load OBJ.", `CurrentOBJFilePath`) |
| 0x01 mtn | 0x2d8fd53.. | motion: prompt "Loading a motion will delete all existing avatar animation layers. Do you want to proceed?" (0x2d900cb), `CurrentMotionFilePath` |
| 0x20 zpac / 0x44 zblc | 0x2d93753.. | `.png`/zpac garment, `CurrentPacFilePath`, "File not found - " |
| 0x0E dxf/aam/aama | 0x2d9480a | "This file is not a DXF format.", `CurrentDxfFilePath` |
| other | strings for Env/Collada/MorphTarget/USD/Animation/Placement/Board/AI paths | unmapped |

### 4.1 `.avt` (type 0x03) behaviour ([V] structure, [I] interpretation)
- Descriptor flags: `+0x84` (call it "append/keep" flag) = **0** and `+0x8C` = 1 as built by the worker for ImportFile; `+0x87` = byte param, `+0x85` = edx.
- **Graded-size prompt (0x2d903af)** runs when ALL hold: `0x5cfe9f0(0x1bf5e20())` object valid (0x1c098c0), `+0x84 == 0`, `+0x8C == 1`, and `0x4eb85e0(obj+0xC28)` true [I: "graded-size avatars exist in the document"]. Then a 2-choice box (`0x4b786c0`, "Added avatars for graded size will be replaced. Would you like to proceed?"). If the button id == 2 [I: cancel/No] -> `App+0x38 vtbl[0x250/8]`, release and **return without loading**. Any other answer continues and the import proceeds. **This is a blocking modal for an unattended ImportFile(.avt) when graded avatars are in the document.**
- Extension handling uses string-ends-with checks for `.dae`, `.avt` (flag 0x2/0x4), `.avac` (0x8/0x10), `.avte` (0x20/0x40): a `.dae` takes a different (collada avatar) path; `.avt`/`.avac`/`.avte` fall to the "single avatar" loader.
- Loader: `0x50888e0()`; `0x39f6b20()`; for plain `.avt` (r14d==0) **`0x39fbdd0(this, &path, &opts)`** (load one avatar and *add* it); for `.avac` (collection) `0x39fed10(..., &listA, &listB)` which returns lists of loaded avatars. After success: `0x50d1640` / `0x1d68c80` / `0x512a250` (conditional: only if `+0x68` string non-empty = a size file?), then, if `+0x8C != 0` and flag +0x84 == 0: `0x577fb30(obj)` (a post-load step on the scene object) and `App+0x30 vtbl[0x2B8/8]`; writes settings `CurrentAvatarFileType` and `CurrentAvatarFilePath`; refresh `App+0x60 vtbl[0x15]`.
- **No explicit "delete all avatars" call is on the plain `.avt` path.** The only deletion hint is the graded-size message (replacing *graded-size* avatars), so `.avt` via ImportFile **appends** an avatar to the AvatarManager [I, from the absence of any clear call in the traced span 0x2d9033b-0x2d91199; the callee 0x39fbdd0 was not opened]. This matches the plugin's observation that `ImportAvatar` and `ImportFile(.avt)` leave previous avatars unless cleared (`clear-avatars` command).
- Is it the same as `ImportAPI::ImportAvatar`? **No**: ImportAvatar (lane D) goes straight to AvatarManager without the document guard; ImportFile(.avt) goes via the worker with the `[App+0x30]` document guard, `vtbl[6]==2` guard, the graded-size prompt, settings writes and the refresh. Both end in the avatar loader family (0x39fbdd0 area) [I].

### 4.2 `.avs` (type 0x27) -> 0x50fcfe0 ([V])
Signature: `bool 0x50fcfe0(AvatarManager* mgr, std::wstring* path, void* snap, bool* flag, void* progress)`.
- **Entry test (0x50fd034): `cmp qword [mgr+0x88], 0`** - the avatar-list element count/pointer. If **zero (no avatar loaded)** -> modal info box **"No matching Avatar."** (0x8383520, via 0x4b78600) and return **false** at 0x50fd09d. So with no avatar loaded `ImportFile(.avs)` **blocks on a modal box in GUI mode** and loads nothing [V; modal behaviour I - 0x4b78600 is the shared modal info sink per lane X].
- Otherwise: opens/parses the file (`Open Avatar Size`, 0x50fd24b), invalid path -> "Failed to load the Avatar Size file. Invalid file path." (0x50fd192 / 0x50fdf49), lower-version file -> "...created in a lower version." (0x50fde61). Version check `cmp eax,3` / `eax-1 <= 1`.
- Reads `MVresizingMap` (0x50fd59b) and `qsAvatarID` (0x50fd4f0) [V strings]. Two application sites:
  * **0x50fd450**: single-avatar path inside a branch that uses `qsAvatarID` (`0x510cf00`, then **0x511a1b0**(avatar, 0, snapshot, 0)); then `r15b=1` (success).
  * **0x50fda06**: per-avatar loop over the AvatarManager list (lane K), preceded by the "No matching Avatar." test at 0x50fda80 for the case that no avatar accepted the map.
- Therefore the `.avs` is applied to **every avatar in the list** (loop) unless the `qsAvatarID` branch (0x50fd450) selects a specific one [V structure; the selection condition between the two was not decoded -> I]. Settings key `LastAvatarSizingFilePath` written at 0x50fdca7; undo labels "Reset Avatar Size"/"Load Avatar Size".
- Preconditions summary: (a) at least one avatar in the manager, (b) file readable and not from a lower version, (c) per-avatar validity gate inside 0x511a1b0 (`avatar+0x990` flag, lane K).

## 5. Headless vs GUI for `ImportFile(path)` (slot 2, 0x6022a80)

[V] after `[App+0x30]!=0`:
- `IsHeadless() == true` (0x6022c7f..9f): `App+0x38 vtbl[0x100/8 = 32](wpath)` -> worker path above. Return value discarded.
- `IsHeadless() == false` (GUI, **Mirra's case**): lower-case ext -> `0x3bb3640(ext)`: a static set of known file extensions {amx, aam, aama, **avt, avs**, arr, anm, cak, cmt, cmp, obj, mdd, mc/mcx, mea, zip, mtn, pc2, pos, hpos, pan, pacx, tco, zpac, zprj, btn, bth, sew, sst, fbx, zacs, fab, zfab, smp} [V].
  * ext in set -> `App+0x50 ->vtbl[0x250/8 = 74](vector<wstring>{path}, &opts)`; if that returns **false** the API returns false (0x6022da8..ad). On true it falls to the zprj post-step and returns true.
  * ext not in set -> `App+0x38 vtbl[32](wpath)` (same as headless).
  * **So in GUI mode `.avs` and `.avt` do NOT go through slot 32 / worker 0x2d98980 directly; they go through the `App+0x50` object's virtual method #74.** That object's class and the method body were *not* resolved here (App+0x50 is used elsewhere as `[rax+0x110]`, `[+0x1B0]`, `[+0x250]` UI-style virtuals, i.e. it looks like the main-window/command object) [I]. The same method name `[+0x250]` is also called on `App+0x38`'s cousin in 0x2d9042x; both are "open files" style entry points that very plausibly re-enter the same worker 0x2d98980 per file (the worker has exactly the signature `(path, bool, bool, bool, ...)` of a GUI open-with-flags call) [I, unverified]. Lane K's empirical observation (ImportFile(.avs) changes the mesh in GUI mode) is consistent with that.
- Open items: body of `App+0x50 vtbl[74]` (resolve its RTTI class via the vtable at `[[App+0x50]]`).

## 6. Return values

| Call | Returns |
|---|---|
| slot 1, no document `[App+0x30]==0` | false [V] |
| slot 1, with document | return value of `CLOFileIOImpl::vtbl[31]`: false for any type other than obj/fbx/gltf/glb (also when the 0x6154bf0 gate rejects), else the worker's result. `.avs`, `.avt` and every other non-mesh type => **false and nothing happens** [V]. |
| slot 2, no document | **true**, nothing done [V] |
| slot 2, headless | `vtbl[32]` result discarded; zprj post-step; **returns true always** [V: `mov al,1` at 0x146022E4D is the only success exit after the call] |
| slot 2, GUI | false only if the extension is in the 0x3bb3640 set and `App+0x50 vtbl[74]` returned false; otherwise **true** [V]. |
| worker 0x2d98980 | result of 0x2d8f090 for routed types (a `bool`, `xor al,al` epilogue = false on the early gates; the success epilogue at 0x2d9787A is beyond the disassembled span) |

**So `ImportFile(path)` (slot 2) returning true says nothing about success** for avatar/avs files (no document -> true; failure boxes -> true if the GUI member returns false only in special cases). Verify by reading avatar state afterward (e.g. `GetAvatarMeasurements`) as the plugin already does.

## 7. Implications for the Mirra pipeline

1. **`.avs` ordering**: ImportAvatar (or `ImportFile(.avt)`) must come first. With no avatar, `.avs` shows the "No matching Avatar." modal and loads nothing; if the watchdog does not dismiss it, the REST worker blocks [V]. This is a new *blocking* risk beyond lane X's catalogue - add "No matching Avatar." (0x8383520, from 0x50fcfe0) to the dismiss list.
2. **Clearing other avatars**: `.avs` is applied to all avatars in the manager (loop at 0x50fda06) [V structure]; ImportFile(.avt)/ImportAvatar do not clear existing avatars [I], so run `clear-avatars` (DeleteAvatar) before importing the target avatar, then `.avs`. Prefer one avatar only at any time.
3. **GLB/avt from slot 1 is impossible**: `ImportFile(path, ImportExportOption)` only accepts obj/fbx/gltf/glb; use slot 2 (the plugin already calls the 1-arg form) for avt/avs [V].
4. **Prompts on `.avt` via ImportFile**: if a document contains graded-size avatars, ImportFile(.avt) pops "Added avatars for graded size will be replaced..." (blocking). Mirra's flow starts from NewProject/clear, so normally absent, but guard it. `ImportAvatar` avoids this document-level path.
5. `.avs` has a **feature gate** (0x6154bf0 type table) before the handler; it passed in the observed live runs (licence/feature table not analysed).
6. Return value is not usable as success signal; verify state afterwards, and detect modal boxes with the watchdog.
7. Not in dispatch: `.csv` (no classifier entry), `.osw`/`.jfab` (no such strings in the classifier; probably Mirra/other formats) - ImportFile of them gives type -1 and the unsupported-format box (slot 32) or `false` (slot 1).

## 8. Caveats
- 0x2d8f090 was disassembled to 0x2d95090 only (cut heuristic); handlers after that and the success epilogue 0x2d9787A are unread.
- `App+0x50 vtbl[74]` (GUI route for avs/avt in slot 2) is unresolved; its relation to the worker is inferred.
- Meaning of the `+0x84/+0x8C` descriptor bytes, of the `0x6154da0/0x50ef380/0x6154e10` gates, and of the button id 2 in the graded-size prompt are inferred from usage.
