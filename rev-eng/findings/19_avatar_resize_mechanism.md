# Lane K: why a patched `.avt` does not re-deform the mesh, but an `.avs` does

*Status: static disassembly only (dumpbin) of CLO_Standalone_OnlineAuth_x64.exe 2026.1.336; CLO not run*
*Date: 2026-10-29*
*Scripts added: `scripts/k_strscan.py` (NUL-delimited string finder + lea/mov xrefs), `scripts/k_xref2.py` (broad rip-relative xrefs incl. SSE inline-string loads), `scripts/k_callers.py` (E8/E9 callers and 8-byte pointers), `scripts/k_ann.py` (annotates a raw dumpbin listing), `scripts/k_dis.ps1` (dumpbin wrapper). Raw listings: `raw/k_*.txt`, `raw/k_*.ann.txt`.*
*Labels: **[V]** = read directly in the disassembly; **[I]** = inference. RVAs (image base 0x140000000); file-level notes only cite RVAs.*
*Cross-reference: `findings/15_measurement_import_internals.md` (lane H) decodes the size manager, `SetFeatureValue` 0x512d3a0 and the apply routine 0x50a0f70. This file adds the loader side and the exact gate.*

## 0. Answer in one paragraph

CLO keeps the measurement data (`MVresizingMap` / `mapResizingAvatar`) as a plain **data object embedded in the Avatar at +0x990**. Loading a `.avt` (the `.dan` stream) deserialises that object with a pure "store" reader (0x510b9d0 via wrapper 0x510cd70) and then **throws away the "previous state" snapshot and never calls the resize driver 0x511a1b0**. The `.avs` ("Load Avatar Size") handler calls the same reader/wrapper and then **does** call 0x511a1b0, which pushes the 67 feature floats into the global size manager, runs the two-stage recompute, and calls `Avatar::0x50a0f70` (mesh apply). The mesh vertex arrays (`baPosition`, `baInitPosition`, render positions) are simply loaded as saved. So patched `listFeatureValues` floats are stored (and re-saved) but never applied. No flag in the `.avt` found so far turns this on. [V for the two call chains; I for "no flag exists", see section 5]

## 1. The serialised object and its (de)serialiser

All key names occur **exactly once** in the exe (.rdata, ASCII); the string pool is shared by writer and reader. [V]

| String | RVA | Writer xref (lea) | Reader xrefs (SSE inline copy) |
|---|---|---|---|
| `bWidthLinked` | 0x89115b8 | 0x5125032 | 0x510ba21 |
| `bHeightLinked` | 0x89115c8 | 0x512506d | 0x510ba6c |
| `listMeasureMode` | 0x89115d8 | 0x5125116 | 0x510badb |
| `BaseFeature` / `ProportionBaseFeature` / `WidthBaseFeature` / `DetailFeature` | 0x89115e8 / f8 / 0x8911610 / 28 | 0x5125149..0x51251e2 | 0x510bb.. |
| `enLastUpdateMode` | 0x89116a8 | 0x512531a | 0x510c0d5 |
| `listFeatureValues` | 0x89116c0 | 0x51253b8 | 0x510c145 |
| `listMeasureDiffValues` | 0x89116d8 | 0x5125458 | 0x510c225 |
| `listMeasureLinkList`, `bUseCupSize`, `SelectedCupSizeIndex`, `listCupSizeName`, `listCupSizeValueList`, `utfSizeFileName` | 0x89116f0.. | 0x51255cd.. | 0x510c3.. - 0x510cc7f |
| `MVresizingMap` | 0x83cabe0 | 0x4ebf60d, 0x51259f8 | 0x2fa17df, 0x4ebb58f, 0x50fd59b |
| `mapResizingAvatar` | 0x883b188 | 0x3a0504a, 0x511d2d6, 0x57b43c3 (save/export paths) | 0x50f7364, 0x3f7e101 (load) |
| `listSkinController` | 0x88bb280 | (0x4e8e74b, 0x50f5f0b, 0x511cae4: mesh save/load, not decoded) | |
| `baInitPosition` | 0x88635e0 | (0x3f66a2f) | |
| `mapMesh` | 0x89d89b8 | (0x623fb86, 0x62424f4, 0x62468d5) | |

- **Writer** `ResizingInfo::ToMap(this, map)` = **0x5124ff0** (start; the push chain begins there, body 0x5125000..0x51259f8). Callers: 0x3a0502a, 0x4ebf5f0, 0x51258c7 (jmp), 0x51259e1. [V]
- **Reader** `ResizingInfo::FromMap(this, map)` = **0x510b9d0** (body to 0x510cd68; returns bool). Callers: 0x2fa1acb (size-file check), 0x4ebb60f (size-set loader), 0x510cdbd (wrapper below). It only calls `map.get(key)` helpers (0x62d1f70 bool, 0x62d2750 list, 0x5087110 int, ...) and stores into the object; **no resize call anywhere in it**. [V]
- Object layout (offsets inside the ResizingInfo; add 0x990 for the Avatar) [V from writer/reader]: +0x14 `bWidthLinked`, +0x15 `bHeightLinked`, +0x18 `listMeasureMode` (vector<int32>), +0x30 `BaseFeature`, +0x34 `ProportionBaseFeature`, +0x38 `WidthBaseFeature`, +0x3C `DetailFeature`, +0x48 **`listFeatureValues`** (vector<float>, 67 used), +0x60 `listMeasureDiffValues`, +0x7C **`enLastUpdateMode`**, +0x80 `listMeasureLinkList`, +0x98 `bUseCupSize`. The first byte at +0 is a validity/"resizable" flag (section 3). [byte meaning I]
- The Avatar class holds this object at **avatar+0x990** (features vector at avatar+0x9D8, lastUpdateMode at avatar+0xA0C). [V]

## 2. The two routes

### 2.1 `.avt` / `.dan` load: store only (explains the 0-byte mesh diff)

`.dan` avatar load function around 0x50f7200..0x50f76d5 (progress strings `Loading Size...` 0x89110a8, `Load Size` 0x89110b8): it looks up `mapResizingAvatar` (0x50f7365/0x50f738e). If present it does exactly:

```
0x50f73ba  r9d = 0; r8 = &mapResizingAvatarValue; rdx = &tmpSnapshot; rcx = avatar
0x50f73ce  call 0x510cd70(avatar, &tmpSnapshot, map, bWarn=0)   // = snapshot old state, FromMap, validate
0x50f73da  call 0x5092e60(&tmpSnapshot)                         // destroy snapshot
0x50f73df  jmp  0x50f76d5                                       // continue loading; NO call to 0x511a1b0
```
[V] If the key is absent it falls through to a template-name branch (`Template`, `New`, `Converted`, `Jinny`, `BabyTemplate`, `Manne`, `MHTemplate`, `HandTemplate`, `VRCTemplate` string tests at 0x50f73e4..0x50f75e0; legacy avatars). The mesh (`listSkinController[*]/mapMesh/baPosition`, `baInitPosition`, render `listSource[0]`) is deserialised independently from the same file, so positions come out exactly as saved. [V for the branch; I that the mesh load path is independent, consistent with lane F's 0-byte diff]

Wrapper **0x510cd70** `(avatar, outSnapshot, map, bWarn)` [V]:
1. `0x2e96bb0(outSnapshot, avatar+0x990)` copy current ResizingInfo as "old state";
2. `0x510b9d0(avatar+0x990, map)` read the new one;
3. `0x51574e0(avatar)` validity check A, else `0x5157660(avatar)` check B; if both fail: `string(avatar+0x530) += "_resaved"` and `byte [avatar+0x990] = 0`;
4. if `bWarn` and the read returned true and a check passed: `MessageBox "This sizing data was created in a lower version. The body shape and editable measurements options may have been changed according to the updated version."` (0x8911340).

### 2.2 `.avs` ("Load Avatar Size"): store then apply

Command handler at 0x50fd780..0x50fdfd8 (action strings `Reset Avatar Size` 0x890f140, `Load Avatar Size` 0x890f158; error strings `Failed to load the Avatar Size file. Invalid file path.` 0x83cab40 / `... created in a lower version.` 0x83cab80 / `No matching Avatar.` 0x8383520; settings key `LastAvatarSizingFilePath` 0x83cab00). It first reads the `.avs` top-level map (`MVresizingMap` at 0x50fd59b), then for **every avatar in the AvatarManager list** [V]:

```
0x50fd9e0  r9b=1 ; rcx = avatar
           call 0x510cd70(avatar, &snap, map, bWarn=1)     // store new sizing, snapshot old
0x50fda06  call 0x511a1b0(avatar, 0, &snap, progress)      // *** APPLY ***
0x50fda13  call 0x5092e60(&snap)
...
0x50fde40  call 0x5ccd3a0(Singleton 0x1be1040)             // post refresh (same as Simulate tail)
```
The `.avs` GUI path "Open avatar size file" (0x2fa1000.., strings `Avatar Size File (*.avs)` 0x83cab20) is a separate load-and-check function (0x2fa1acb reads into a local object); the programmatic `ImportFile(.avs)` route is assumed to land in 0x50fd780 (extension recognised in the open-file classifier at 0x1bab6f1, `.avs`). The ImportFile dispatcher itself was **not traced**. [I]

### 2.3 The resize driver **0x511a1b0** `(avatar, bool undoFlag, oldSnapshot*, progress*)` [V call structure, I semantics]

```
if (*(byte*)(avatar+0x990) == 0) goto skip;          // 0x511a1e9: gate #1 = ResizingInfo valid flag
if (!undoFlag && oldSnapshot && !progress) { create undo/"Load Avatar Size" command (string 0x890f158) }
tmp = avatar+0x990 copy ...
mgr = 0x50d6060()                                    // the global avatar size manager (lane H singleton 0xa320338) [I identity: same 0x512d3a0/0x51449e0 callees as lane H]
for i in 0..66 (cmp ebx,0x43):                        // loop 1
    if (mgr->0x50d27e0(i))                            // feature i "has a value / is enabled" [I]
        mgr->0x512d3a0(i, avatar.listFeatureValues[i])   // SetFeatureValue (clamped)
if (!avatar->0x50f2c60()) mgr->0x51449e0(1, 1)       // 0x511a47a  recompute pass "mode 1"
if (avatar+0xA0C /*enLastUpdateMode*/ != 1) {         // 0x511a48a  gate #2
    loop 2: same set-values loop over 0..66
    if (!avatar->0x50f2c60()) mgr->0x51449e0(enLastUpdateMode, 0)   // second pass with the stored mode
}
avatar->0x50a0f70(flag)                              // 0x511a509: mesh apply (lane H section 4)
...                                                  // undo-record bookkeeping, 0x50dced0 / 0x5507700 / 0x3b24740
```
`0x50f2c60(avatar)` is a predicate that suppresses the recompute passes (likely "avatar is static/non-resizable"; compare string `This avatar is a static type that cannot be resized.` 0x845b3d0 used in the GUI sizing dialog at 0x35f3a16). [I]
This is the same call set that lane H found in `ImportMeasurement` (`0x512d3a0` per feature, `0x51449e0(1,1)`, `0x51449e0(2,0)`, `0x50a0f70`). So **the CSV route and the `.avs` route share the apply engine; the `.avt` route is the only one that never reaches it.**

Other callers of 0x511a1b0 (not examined; none of them is the plain `.dan` loader 0x50f73ce): 0x50a6a64, 0x50c3ad6 (strings `Auto_`, `Auto_Converted_`, `PreSchool_Kid`, `Girl_Kid`, `Boy_Kid` around it: auto-fit of preset kids/templates), 0x50ee542 (strings `FemaleTemplate_FaceConverter`, `MaleTemplate_FaceConverter`, `New_001..004`: template conversion), 0x50fd450 (Reset Avatar Size), 0x55fa13c, 0x584b13e (also calls 0x510cd70), 0x62079b7.

## 3. Validity checks and what they say about `listMeasureMode`

`0x51574e0` (check A) [V]: fails if `BaseFeature(+0x30) == -1`, or (if `bUseProportionBase(+0x40)`) `ProportionBaseFeature(+0x34) == -1`, or `WidthBaseFeature(+0x38) == -1`, or `DetailFeature(+0x3C) == -1`; then every feature float must be in `[0, upper]` (`upper` const at 0x846c880), feature 1 is clamped to `[0, 50]` (0x42480000 = 50.0) when `WidthBaseFeature == 2`, and feature 58 (`0x3A`, Hand?) has a gender-specific default (0x419D3333 = 19.65 for `avatar+0x994 == 0`, 0x4180CCCD = 16.1 for `== 1`) if out of the range test. Check passes -> returns true.
`0x5157660` (check B, fallback) [V]: counts `listMeasureMode` entries equal to **3** and equal to **1**; requires exactly one of each (`cmp r9d,1; cmp eax,r9d`) plus the same float range test.
So a ResizingInfo is "valid" if either all base-feature selectors are set, or exactly one measure is mode 3 and exactly one is mode 1. Otherwise the loader zeroes the flag at +0x990 (gate #1 of the driver) and appends `_resaved` to the avatar name field at +0x530. [V]

`listMeasureMode` values (index = feature, 0-66) [I, from usage; no enum strings found]:
| Value | Evidence | Reading |
|---|---|---|
| 0 | `ImportMeasurement` resets all 67 entries to 0 via 0x512d2a0(i,0) | not an input/driver; derived |
| 1 | check B requires exactly one; `ImportMeasurement` sets Bust (male, idx 2) or Under Bust (female, idx 5) to 1; default avs idx 2 = 1 | primary girth driver ("Bust"/"Under Bust") |
| 2 | default male avs: idx 4, 6..9, 15 | user-editable / secondary measures |
| 3 | check B requires exactly one; `ImportMeasurement` sets Total Height (idx 0) to 3; default avs idx 0 = 3 | primary height driver |
| 4 | default avs idx 26 (Inseam), 36 (Across Shoulder), 47 (Arm Length) | length/width measure editing mode (meaning not found) |
| 5 | default avs idx 58..61; female under-bust slot | extra/secondary (hand/head...) (meaning not found) |
No enum-name strings exist for these (searched the `MVresizingMap` neighbourhood and `0x512d2a0` users; only integers). 2/4/5 stay inference.

`enLastUpdateMode` (default 4 in `.avs`) is only consumed by the driver: `==1` skips the second set-values loop and recompute; otherwise it is passed as the mode to the final `0x51449e0`. [V usage, I meaning: "which measurement the user edited last"]
`bHeightLinked` / `bWidthLinked` are written and read but I found **no consumer** in the driver or the loader. [V for the two read/write sites; I that they matter only to the GUI slider logic]

## 4. Why the observed experiments come out the way they do

| Observation (lane C/F) | Explained by |
|---|---|
| avt_patch: 0 position bytes differ after CLO re-save; floats stored | `.dan` load calls `FromMap` only; `ToMap` re-emits the (patched) stored floats; mesh arrays loaded as saved (section 2.1) |
| avs route: positions change (~73% of bytes), topology/UV/weights not | 0x50fd780 -> 0x511a1b0 -> 0x50a0f70 deforms vertices only |
| avs identical-input runs differ by <=0.0019 mm | float solver in the two-stage recompute (0x51449e0) [I] |
| avt_patch with `ImportAvatar` appeared fine, no crash | `ImportAvatar` ends in the store-only loader |
| avs route applies to *every* avatar loaded | the handler loops over all avatars (r14..rsi from 0x50a8710 list) [V] |

## 5. Ranked, testable hypotheses for the Mirra pipeline

Ordered by (probability that it works) x (cheapness to test). All are about CLO 2026.1.336; none was run.

1. **No `.avt` byte change will trigger it (high confidence, [I from [V] structure]).** Reason: the only consumers of `enLastUpdateMode`, `listMeasureMode` and the base-feature selectors are the validity checks (0x51574e0/0x5157660) and the driver 0x511a1b0, and the `.dan` loader never reaches the driver. Test to falsify: patch `enLastUpdateMode` 4 -> 1 or 2 and `bHeightLinked` true -> false in a copy, import, re-save and diff positions (expect 0 bytes differ). Cost: one run; value: closes the question.
2. **Keep the `.avs` route as the only supported way (high confidence it works, already observed).** Mechanism: `ImportFile(.avs)` -> `Load Avatar Size` handler. Notes for the pipeline: (a) it applies to **all** loaded avatars (delete or import avatars in an order so only the intended one is present); (b) the `.avs` must pass check A or B (default-template-derived files do); (c) feature 0 (height) has mode 3 and idx 2 (male bust) mode 1 in the stock files; keep those entries when generating `.avs`.
3. **Import the `.avt` first, then apply the measurements through the `.avs` route with the same floats** (medium-high). The `.avt` carries mesh/skin/texture for the avatar's template; the `.avs` then re-deforms it. Verify with `GetAvatarMeasurements` (lane B recommendation) that the circumferences match the requested values.
4. **Use `ImportAvatarMeasurement(csv, avt, opt)` / `ImportMeasurement(csv)` (medium)**: lane H shows these reach the same driver chain (0x512d3a0, 0x51449e0, 0x50a0f70) but are **headless-only** (`ImportMeasurement` returns false unless CLO was started with `headless`) and take a different value set (CSV keys only). Not usable in a GUI-launched CLO. See lane H doc.
5. **Exploit a template-conversion call site of 0x511a1b0 (low)**: callers 0x50ee542 (`*_FaceConverter`, `New_00x`) and 0x50c3ad6 (`Auto_Converted_`) apply the driver for avatars whose `qsAvatarID` is a recognised legacy template. Hypothesis: changing `qsAvatarID` in the `.dan` to such a name makes the load path call the driver. High risk of corrupting mesh/skeleton mapping; test only on a copy and diff positions. Not recommended unless 1-3 fail.
6. **Invalid-sizing trick is the opposite of what we want (low):** breaking validity makes loader set `[avatar+0x990]=0` (gate #1 closed) and appends `_resaved` to the name; the driver is then skipped on every route. Useful only as a way to force "static" behaviour if ever needed.
7. **Direct mesh edit (fallback, medium effort):** since the mesh is simply loaded as saved, a pipeline could scale `baPosition` / `baInitPosition` / render positions in the `.dan` itself. Not a CLO mechanism; needs skeleton matrix (`baItoL`, `m4LtoW`) consistency, which lane F observed also change on the avs route.

## 6. Open items / not done
- The ImportFile dispatcher path from the `.avs` extension to 0x50fd780 was not traced (assumed). A live `ImportFile(.avs)` already shows the mesh changes, which is consistent but not a proof of which handler runs.
- Bodies of 0x50a0f70 / 0x513f190 / 0x51449e0 / 0x50f2c60 / 0x50d27e0 not read (lane H covers 0x50a0f70 at call level).
- `bHeightLinked`, `bWidthLinked` consumers; meaning of modes 2/4/5; the `0x846c880` upper bound value; the byte at +0 of the ResizingInfo (who sets it to 1 initially: probably ctor 0x51164b0, called at the top of FromMap).
- Callers 0x50a6a64, 0x55fa13c, 0x584b13e, 0x62079b7 of the driver not classified.
