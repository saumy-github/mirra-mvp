# Lane AB: reachability of the Softbody / Divide resize dialogs

*Status: static disassembly only (dumpbin + stdlib Python) of CLO_Standalone_OnlineAuth_x64.exe 2026.1.336. Nothing was run or hooked. Read-only on repo `.avt`/`.avs` samples.*
*Date: 2026-10-29*
*Tools added: `scripts/disasm_fn12.py` (copy of disasm_fn9, cache `raw/disasm12/`), `scripts/reach12.py` and `scripts/xref_dialog12.py` (copies pointing at fn12; reach12 also lists sink 0x4b786c0), `scripts/ab_reach_flags.py` (reach with sinks = 0x50a8710 / 0x50fcfe0 / softbody and divide getters+setters), `scripts/ab_dan_flags.py` (prints softbody/divide leaves of the `.dan` in an `.avt`). Raw listings: `raw/disasm12_*.txt`.*
Tags: **[V]** read in the listing/data, **[I]** inference. Addresses are RVAs (VA = 0x140000000 + RVA).

## 0. Answer in short

1. **[V] Yes for the `.avs` route.** `ImportFile(.avs)` reaches `0x50a8710` by direct calls: `CLOFileIOImpl` slot 31/32 (0x1d99640 / 0x1d995d0) -> file-open worker 0x2d98980 -> 0x2d8f090 (case file-type 0x27, call at 0x2d911f9) -> **"Load/Reset Avatar Size" handler 0x50fcfe0** -> **0x50a8710 at 0x50fd9ac**, *before* the sizing is stored (0x510cd70) and before the resize driver 0x511a1b0. **[V] No for `ImportMeasurement` / `ImportAvatarMeasurement`** on the apply side: 0x50e41a0 -> 0x50e4d80 -> 0x50a0f70 has no direct path to 0x50a8710 and never tests the softbody/divide flags (see section 4). One indirect route exists for ImportAvatarMeasurement's *avatar-load* step (section 4.2) but only when the loaded avatar descriptor carries a `Size:` line, which modern `.avt` (zip with a `.dan`) does not.
2. **[V] Condition:** any avatar in the AvatarManager list with `byte [avatar+0x10B0] != 0` (**SoftBodySimulation on**, getter 0x50dea30) triggers the Softbody box; any with `byte [avatar+0xDE0] != 0` (**DivideMesh / subdivision on**, getter 0x50defb0) triggers the Divide box. It scans **all loaded avatars**, not only the target. **[V] Cancel aborts silently and leaves the avatar untouched** (no store, no driver call, handler returns false, no further message). Proceed turns the option off (undoable) and continues.
3. **[V] Not avoidable through `.avs`** (no such keys). **[V] Avoidable by the avatar's default state:** the stock `.dan` has `bSoftBodySimulation=0` and `bOnSubDivision=0` in all 5 repo samples, so a normal Mirra run never shows either box. **[V] SetAvatarProperties cannot set them** (only 3 keys), but two other Utility APIs can *clear* them: `SetAvatarSmooth(idx, 0)` clears Divide and `SetAvatarSoftBodyStiffness(idx, 0.0)` clears Softbody (section 5). The same two APIs can also *set* them, which is the only realistic way for a pipeline to cause the dialog.
4. Other prompts on the `.avs` path: "No matching Avatar.", "Failed to load the Avatar Size file. Invalid file path.", "... created in a lower version.", "This sizing data was created in a lower version ..." (section 6). No "size out of range" / "Resizable avatar only" / clamp message exists on this path.

## 1. What 0x50a8710 is

Signature [I from usage]: `bool PrepareAvatarsForResize(AvatarManager* mgr /*rcx*/, const vector<shared_ptr<Avatar>>& list /*rdx, 16-byte elements*/, QString/unused r8, r9)`. Returns `al`: **0 = abort, 1 = go on** (epilogue `xor al,al` at 0x50a963e, `mov al,1` at 0x50a96a9) [V].

Pseudo-code, verified from `raw/disasm12_50a8710.txt` (991 instructions):

```
asked = false
// ---- pass 1: Softbody
for each avatar in list:                                  // loop 0x50a87b0..0x50a8c55
    if (0x50dea30(avatar))            // movzx [avatar+0x10B0]  = SoftBodySimulation on
        if (!asked) {
            asked = true
            r = 0x4b786c0(text=0x82972a0 "The Softbody Option will be turned off to adjust the avatar size. Do you want to proceed?",
                          buttonset=0x11, parent=-1)       // call at 0x50a8820, sink = dialog service vtbl+0x10
            if (r == 2) goto CANCEL                        // cmp ebx,2 ; je 0x50a8e1b
        }
        push avatar into 'affected' vector;  0x5131bd0(avatar, false)   // 0x50a8c08: SetSoftbody(off) right after confirmation
// ---- undo record for softbody (string 0x8297300 "Soft Body Simulation", 0x1dd5d70, 0x3b24740)
asked = false
// ---- pass 2: Divide
for each avatar in list:                                  // loop 0x50a8fe0..
    if (0x50defb0(avatar))            // movzx [avatar+0xDE0]  = DivideMesh on
        if (!asked) { asked = true
            r = 0x4b786c0(text=0x8459770 "The Divide Option will be turned off to adjust the avatar size. Do you want to proceed?",
                          buttonset=0x11, parent=-1)       // call at 0x50a9056
            if (r == 2) goto CANCEL                        // cmp ebx,2 ; je 0x50a9555
        }
        push avatar;  0x512f800(avatar, false)             // 0x50a922e: SetDivide(off)
// ---- undo record "Divide Mesh" (string 0x83ff960)
return 1                                                   // 0x50a96a9
CANCEL: free temporaries; return 0                         // 0x50a8e1b / 0x50a9555 -> 0x50a9632 -> 0x50a963e
```
* [V] Getters are one-instruction leaves: 0x50dea30 `movzx eax,[rcx+0x10B0]`, 0x50defb0 `movzx eax,[rcx+0xDE0]`. Setters: 0x5131bd0 `(avatar, bool)` (early-out if the flag already equals the request, 0x5131c10; enabling path pushes an undo command named "Softbody Simulation", string 0x89104a8) and 0x512f800 `(avatar, bool)` (early-out if `[avatar+0xDE0]==dl`, 0x512f826).
* [I] Button id **2 = No/Cancel**, anything else (Yes) proceeds. Not decoded in the dialog service (vtbl+0x10 of the object from 0x5cc9d60); the `cmp ebx,2; je CANCEL` structure makes it the only sensible reading. Same unknown as in findings/29 for PreCheck.
* [V] The Softbody box and the Divide box can both appear in one call (separate `asked` flags). If Softbody is confirmed and Divide is then cancelled, softbody is **already off** (0x5131bd0 ran in pass 1), so "cancel leaves the avatar unchanged" is true only for the first box; after a Yes on the Softbody box the avatar's softbody flag is already cleared even if the resize is later cancelled. Both boxes block the UI thread until a human answers (no headless check).
* [V] Both setters can be silently refused for template avatars: 0x512f800 skips the change if `0x50f1c00` (avatar name at +0x530 equals "001"/"002"/"003"...) or `[avatar+0x618]` or `0x50f1100` ("MHTemplate") is true, and shows "The avatar mesh cannot be divided." (0x8910320) only when *enabling*. Irrelevant for Mirra's `5.1_MaleTemplate_07` / `5.1_FemaleTemplate_08`.

## 2. Callers of 0x50a8710 (direct E8, whole .text scan with `scripts/k_callers.py`)

| Call site | Containing function | Role |
|---|---|---|
| 0x50fd405 | 0x50fcfe0 (Load/Reset Avatar Size handler, mode branch type 3) | "Reset Avatar Size": then `0x510cf00` + driver 0x511a1b0 at 0x50fd450 |
| **0x50fd9ac** | 0x50fcfe0 | **"Load Avatar Size"**: `if (!0x50a8710) skip all; else for each avatar { 0x510cd70(store); 0x511a1b0 (driver) }` (0x50fd9bb `test al,al; je 0x50fda6b`; 0x50fda6b `xor r15b,r15b` -> handler returns 0) |
| 0x2fa162e, 0x2fa1a9b | 0x2fa1000 (GUI "Open avatar size file" check/apply) | GUI path, same prompt layer |

Only these 4 sites; 0 jmp, 0 pointer references to 0x50a8710 [V] (k_callers output for 50a8710 lists exactly those four call sites).

### The 8 driver (0x511a1b0) call sites vs 0x50a8710 (findings/26 list)
| Driver call site | Function | Preceded by 0x50a8710? |
|---|---|---|
| 0x50fd450 | 0x50fcfe0 (Reset) | **Yes**, 0x50fd405 |
| 0x50fda06 | 0x50fcfe0 (Load) | **Yes**, 0x50fd9ac |
| 0x50a6a64 | fn 0x50a6a10 | no direct call (not examined for softbody checks) |
| 0x50c3ad6 | fn 0x50c3230 (Auto_ presets) | no |
| 0x50ee542 | fn 0x50ed020 (template converters) | no |
| 0x55fa13c | fn 0x55fa0b0 | **own checks:** 0x55fa100 `0x50defb0` and 0x55fa10d/0x55fa152 `0x512f800` (divide-off) before the driver; no dialog, silently disables Divide [V call structure, I intent] |
| 0x584b13e | fn 0x584b0b0 | no |
| 0x62079b7 | fn 0x6207900 | no |
Conclusion: of the 8 sites only the two in the `.avs` handler are guarded by the dialog function [V].

## 3. ImportFile(.avs) path, now traced [V direct calls]
```
UtilityAPI::ImportFile 0x6022e80 -> CLOFileIOImpl vtbl[31]=0x1d99640 / vtbl[32]=0x1d995d0
  -> 0x2d98980 (file-open worker) -> 0x2d8f090 (type switch; `cmp ecx,27h` at 0x2d91199)
  -> 0x2d911f9: call 0x50fcfe0(AvatarManager 0x1bf5d20, QString path, vector<avatar> from 0x50cf7c0, bool* out, 0)
  -> 0x50fd9ac: call 0x50a8710(AvatarManager, vector from 0x35780f0)
  -> (ok) 0x510cd70 store -> 0x511a1b0 driver -> 0x50a0f70 mesh apply
```
* `ab_reach_flags.py 4 1d99640`: SINK 0x50fcfe0 depth 3, SINK 0x50a8710 depth 4 [V]. This closes findings/19 section 6 ("ImportFile dispatcher path not traced"). Type code 0x27 == `.avs` is **[I]** (consistent with lane K's extension classifier at 0x1bab6f1).
* The avatar set that is checked and resized is **every avatar in the manager** (vector built by 0x50cf7c0 / 0x35780f0), matching findings/19: a second loaded avatar with softbody on is enough to raise the box.

## 4. ImportMeasurement / ImportAvatarMeasurement

### 4.1 Apply side: no softbody/divide check [V]
`ab_reach_flags.py 6 50e4d80`: only hit is `0x50dea30` at depth 4 via `0x50a0f70 <- 0x5146a40 <- 0x50f1c80`. **That hit is a false positive of the tool:** 0x50f1c80 is a 2-instruction leaf (`movzx eax,[rcx+0x998]; ret`) with no `.pdata` entry, so the tool scanned 0x200 bytes past it into the next function. Same artefact explains "question box via 0x50ef2f0 / 0x512f7b0" in the reach12 output for 0x50a0f70/0x50e4d80 (both are 2-instruction leaves: `[avatar+0x618]` getter, `[avatar+0x790]` setter). Findings/29 style direct-call depth results through leaf functions without `.pdata` must be re-read with this in mind. So **0x50e41a0 -> 0x50e4d80 -> 0x50a0f70 never calls 0x50a8710 and never reads the softbody/divide flags** [V at direct-call depth 6]. If an avatar has Divide/Softbody enabled, ImportMeasurement resizes it **without prompting** (the meshes then stay consistent or not is unknown) [I].

### 4.2 Load side of ImportAvatarMeasurement (`.avt` argument)
`ab_reach_flags.py 6 50e41a0` finds 0x50a8710 at depth 5: `0x50e41a0 -> 0x50e3fc0 ("Avatar Load Failed.") -> 0x39fed10 -> 0x39fc9f0 -> 0x50fcfe0 -> 0x50a8710`. 0x39fc9f0 is the legacy **MVAvatarLoader meta-file parser** (`Version:`, `AvatarID:`, `Model:`, `Size:`, `Pose:`, `Measure:`, ... lines; strings 0x883a6a0..0x883a8f8; "Invalid Avatar Size file path." 0x883a9a8). Its call 0x39fe5c3 passes the `Size:` path (rbp+0x268) to 0x50fcfe0 **only if a Size line is present and non-empty** (0x39fe55f `0x6672730` test, then 0x6269130 duplicate check) [V call, I trigger]. Modern Mirra `.avt` files are a zip with a single `.dan` + textures (`first.dan`, `random-weight-female.dan`; checked), i.e. no meta file with a `Size:` line, so this route is **[I] not taken**. Lane H already says ImportAvatarMeasurement is headless-only anyway.

## 5. Property fields, defaults, and how to set/clear them

### 5.1 Keys and defaults [V, `scripts/ab_dan_flags.py`]
`.dan` loader 0x50f5c00 reads `bSoftBodySimulation` (0x8910ec8, ref 0x50f794d -> `0x5131bd0(avatar, value)` at 0x50f79dc), `fSoftBodyStiffness` (0x8910ef8), `bNeedToUpdateSoftBodyStiffness`, `bNeedToUpdateSoftBodyMesh`, `iSoftBodyMeshQuality`, and `bOnSubDivision` / `iDivisionLevel` (0x8910c60 / 0x8910c50, ref 0x50f85a9 -> `0x512f800(avatar, value)` at 0x50f863b; if Divide is on it then calls `0x5131bd0(avatar,false)` at 0x50f864c, so the two are mutually exclusive on load). Values in the repo files:

| File | bSoftBodySimulation | bOnSubDivision | iDivisionLevel | fSoftBodyStiffness |
|---|---|---|---|---|
| clo_avatar_generation/input/base-1.avt (male, 5.1_MaleTemplate_07) | 0 | 0 | 1 | 1000.0 |
| .agent/saumy/research_files/first.avt, clo_test.avt, MV2.1_Jinho.avt | 0 | 0 | 1 | 1000.0 |
| input/female_research/random-weight-female.avt (5.1_FemaleTemplate_08) | 0 | 0 | 1 | 3000.0 (+ iSoftBodyMeshQuality 0) |
| output/field_probes_20260407/chest.exported.avt (CLO re-save) | 0 | 0 | 1 | 1000.0 |

So **stock avatars are loaded with both options off; no dialog under the normal Mirra flow** [V]. `iDivisionLevel=1` is just the stored level; it is only applied if `bOnSubDivision` is true [I].

### 5.2 `.avs` carries neither [V]
`raw/avs_tree.json`: top level has only `qsAvatarID`, `qsAvatarIDUTF8`, `MVresizingMap` (keys listed in findings/19). There is no softbody/divide field, so the `.avs` cannot preset them.

### 5.3 SetAvatarProperties cannot set them; two other Utility APIs can [V]
* `SetAvatarProperties` = 0x6041900 (slot 349); none of the 45 direct call sites of the four flag functions (0x5131bd0, 0x512f800, 0x50dea30, 0x50defb0; `k_callers.py` output) lies in its body, consistent with lane D (3 numeric keys only).
* **`SetAvatarSmooth(idx, level)`** = 0x60420c0 (slot 347): `level==0` -> `0x512f800(avatar, false)` at 0x6042446 (**clears Divide**); `level 1..3` -> if softbody on: message "Subdivision is not available when Soft Body Simulation is checked." and no change, else `0x512f800(avatar,true)` (0x6042583) + `0x512b8b0(level)`; `level>3` ignored.
* **`SetAvatarSoftBodyStiffness(idx, stiffness)`** = 0x6042680 (slot 351): first `if (Divide on) -> message "Soft Body Simulation is not available when Divide Mesh is checked."` and return with no change (0x60429ee); else `stiffness == 0.0` -> `0x5131bd0(avatar,false)` (0x6042b19, **clears Softbody**); otherwise `0x5131bd0(avatar,true)` + `0x5132250(stiffness)` (**turns Softbody ON**). (`comiss` bounds 5000.0 / 10000.0 at 0x891d110 / 0x828f054 read; the inner guard `5000 > s > 10000` is never true, so every non-zero value enables [I].)
* Both log with `[Python]` prefix and are no-ops with no avatar loaded ("Please Load Avatar").
* `GetAvatarProperties` (slot 350, likely fn 0x5fd59f0, which calls 0x50defb0 at 0x5fd60be and 0x50dea30 at 0x5fd62e3) reports `DivideMesh` / `SoftBodySimulation` from the same two bytes [I: function identity not decoded; the call pattern fits].
* No Utility/API function sets these flags besides these two [V: callers of 0x5131bd0 are 0x1e23564 area GUI, 0x2645f0b, 0x34ab5dc, 0x50a8c08, 0x50f79dc, 0x50f864c, 0x5bf273e, 0x6042b19, 0x6042b41; of 0x512f800 are 0x3651594, 0x50a922e, 0x50f863b, 0x511c755/0x511e115 (avatar `.dan` writer/loader region), 0x55fa10d/0x55fa152, 0x6042446, 0x6042583].

## 6. Other prompts on the resize path
| Where | Text | Condition | Blocks? |
|---|---|---|---|
| 0x50fcfe0 @0x50fd04a / 0x50fd350 / 0x50fda80 (0x4b78600) | "No matching Avatar." (0x8383520) | AvatarManager list empty (`[mgr+0x88]==0`) or list empty | info box, blocks |
| 0x50fcfe0 @0x50fd192 | "Failed to load the Avatar Size file. Invalid file path." (0x83cab40) | cannot open/parse the `.avs` (0x3bde140 / 0x625dfe0) | info box |
| 0x50fcfe0 @0x50fde61 | "Failed to load the Avatar Size file. The file was created in a lower version." (0x83cab80) | handler type 1/2 branch (`dec eax; cmp eax,1; jbe`) | info box |
| 0x510cd70 @0x510ce0b (bWarn=1 on `.avs`) | "This sizing data was created in a lower version. The body shape and editable measurements options may have been changed according to the updated version." (0x8911340) | `FromMap` (0x510b9d0) returns true AND sizing check A/B passes. `FromMap` returns `!contains(key)` for a key read right before `enLastUpdateMode` (0x510c000; candidates `fBaseFeatureBustCircum`/`bUseTotalRise`) i.e. an *old-format* `.avs` | info box |
| 0x50a8710 | Softbody / Divide boxes | section 1 | question box |
| 0x511a1b0 -> 0x3b24740 | "If you directly edit a parametric pattern, it can no longer be edited in the Pattern Drafter. Are you sure you want to proceed?" (0x884ae40) | only if the driver records an undo command for a parametric pattern; the `.avs` handler passes `undoFlag=0, progress!=0`, and the scene has no parametric patterns at that point | not expected [I] |
| 0x512f800 | "The avatar mesh cannot be divided." (0x8910320) | enabling Divide on a non-divisible avatar | n/a for resize |
| GUI only | "This avatar is a static type that cannot be resized." (0x845b3d0, fn 0x35f2190 at 0x35f3a16) | GUI sizing dialog; the headless/API path has no such box. For a "Static" named avatar (`0x50f2c60`) the driver just skips its recompute passes [V call, I name test] | not on API path |
No "size out of range", "Resizable avatar only", or clamp messages were found in 0x50fcfe0, 0x510cd70, 0x511a1b0 or 0x50a0f70 (strings listed per function above; `0x512d3a0` SetFeatureValue clamps silently per findings/15) [V].
Assert box (E11000) via `0x50cadc0` / `0x50cab40` exists at depth 2-4 in these functions; it fires only on invariant violations (null scene objects), no normal trigger [I].

## 7. Mitigation (what to do in Mirra's pipeline)

1. **Default state is already safe.** Keep using `.avt` files whose `.dan` has `bSoftBodySimulation=0` and `bOnSubDivision=0` (all current inputs do). Do not call `SetAvatarSoftBodyStiffness(idx, nonzero)` or `SetAvatarSmooth(idx, 1..3)` on an avatar before the `.avs` import.
2. **Pre-flight guard in the plugin/pipeline** (before `ImportFile(.avs)`): for every loaded avatar index call `GetAvatarProperties`; if `DivideMesh == 'true'` call `SetAvatarSmooth(idx, 0)` **first**; then if `SoftBodySimulation == 'true'` call `SetAvatarSoftBodyStiffness(idx, 0.0)` (order matters: the stiffness call refuses while Divide is on, section 5.3). Re-read the properties to confirm both are 'false'. This removes both boxes without any dialog, and costs nothing when already false.
3. **Keep exactly one avatar loaded** at resize time (the check and the resize cover all avatars, findings/19 and section 3). A leftover avatar with softbody on would raise the box for the whole call.
4. If a pre-existing `.dan` ever needs the flags forced off offline: set the `bSoftBodySimulation` (0x01, 1 byte) and `bOnSubDivision` (0x01, 1 byte) leaves to 0 in the `.dan` (same grammar as findings/13). Not needed for current inputs.
5. **Keep every `MVresizingMap` key** the stock `.avs` has (`bUseCFNeckToWaist`, `bUseCBNeckToWaist`, `bUseTotalRise`, `fBaseFeatureBustCircum`, `enLastUpdateMode`, ...). Omitting a newer key makes `FromMap` return true and pops the "lower version" info box (section 6).
6. Keep a watchdog (findings/29 section 7) as a backstop: a dialog here blocks the UI thread; the Softbody/Divide boxes are question boxes, so a dismissing watchdog must answer the *non-cancel* button (id != 2) to proceed or id 2 to abort, mapping unverified [I].

## 8. Open items
* Button id meaning of the 0x4b786c0 dialog service (2 assumed = No/Cancel); verify empirically or in the dialog implementation behind vtbl+0x10.
* Identity of `GetAvatarProperties` (fn 0x5fd59f0) and exact meaning of the `FromMap` return (`!contains(key)`) not fully decoded.
* The type-code 0x27 -> `.avs` mapping in 0x2d8f090 is inferred.
* Lesson for earlier lanes: `reach*.py` scans 0x200 bytes after any target without a `.pdata` entry (leaf functions); results that pass through such leaves (0x50ef2f0, 0x512f7b0, 0x50f1c80 here) are false positives.
