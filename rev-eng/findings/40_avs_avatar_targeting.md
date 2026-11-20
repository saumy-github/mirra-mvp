# 40 - `.avs` avatar targeting: full decode of 0x50fcfe0 (lane AL)

*Static analysis, CLO 2026.1.336 exe, base 0x140000000. Tags: [V] = read in disassembly, [I] = inference. Script: `scripts/disasm_fn17.py` (copy of disasm_fn13, cache `raw/disasm17/`). Raw handler listing: `raw/ag_50fcfe0.txt`. Addresses are RVAs (add 0x140000000 for VAs). Supersedes the "applied to every avatar in the list" statement in findings 36 sec 4.2 and 19 sec 3.*

## 0. Result in one paragraph

`Load Avatar Size` (0x50fcfe0) does **not** loop over every avatar. For the format Mirra writes (3-field block, first dword 0x0D0E0A03) it builds a **target vector**: `[current avatar]` if the AvatarManager has a current avatar (`mgr+0x98`), else a **search result** (avatars with the resizing-valid flag at `avatar+0x990` and an id that "matches" `qsAvatarID`). Every avatar in the target vector is first **validated** (flag set AND id match); one failure aborts the whole load with the modal "No matching Avatar." and nothing is resized. Only then is the map applied to each target through 0x510cd70 + 0x511a1b0. Avatars not in the target vector are never touched. The id "match" is **not** string equality only: it is equality OR "same template category" (Male / Female / Boy / Girl / PreSchool / Baby / other), so `qsAvatarID` is a coarse gender/age gate, not a per-avatar selector.

## 1. Entry and version dispatch [V]

Args: rcx=mgr (AvatarManager 0x1bf5d20), rdx=&wstring path, r8=&shared_ptr<Avatar> `cur` (filled by caller via 0x50cf7c0(mgr): copies `[mgr+0x98]` ptr and `[mgr+0xA0]` control block = the **current avatar**; [V] 0x50cf7c0), r9=&bool `reset` flag, [rsp+20]=progress/undo owner (0 from ImportFile).

1. 0x50fd034: `cmp [mgr+0x88],0` -> zero (no scene object) -> box "No matching Avatar." (0x8383520) -> return false (0x50fd09d).
2. 0x50fd0ab..0x50fd0e8: path checks (0x6672730 / 0x6672eb0 / 0x6673a00). Fail -> 0x50fdf3c box "Failed to load the Avatar Size file. Invalid file path." -> false.
3. 0x50fd10d..0x50fd180: allocate file object (0x3ba17a0), open (0x625dfe0 with "rb" or 0x3bd13d0); null -> same "Invalid file path" box (0x50fd192).
4. 0x50fd1f7: **`fread(&ver,4,1,fp)`** (0x2e87b90 tail-jumps to the CRT `fread`, IAT 0x8237688). `ver` is the **first dword of the .avs file**:
   * `ver == 3` (0x50fd203) -> legacy path (section 4).
   * `ver` in {1,2} (0x50fd490: `dec eax; cmp eax,1; jbe`) -> box "Failed to load the Avatar Size file. The file was created in a lower version." (0x50fde61) -> false.
   * anything else -> current path (section 2). **Mirra's .avs starts with bytes `03 0a 0e 0d` (n=3 fields, types), i.e. dword 0x0D0E0A03, so it takes the current path.** [V logic, I that the dword is the block header; consistent with finding 13]
5. Current path reads the block: `qsAvatarID` (0x50fd4f0, via 0x4b74940 into string at rbp+0xA0) and `MVresizingMap` (0x50fd59b, via 0x62d2f00 into node rbp+0x60). The default male `.avs` holds `qsAvatarID = "5.1_MaleTemplate_07"` (`raw/avs_tree.json`). `qsAvatarIDUTF8` is ignored by this handler.

## 2. Target selection (current path) [V]

At 0x50fd624: `0x1bf1390(cur)` = `([cur.ptr]==0)` (0x1bf1390: `cmp [rcx],0; sete al`; its twin 0x1d68c80 is `setne`).

* **`cur` non-null (a current avatar exists):** `je 0x50fd756` -> `0x3555520(&vec, 0, cur)` = vector push_back -> **vec = { current avatar }**. Nothing else is considered.
* **`cur` null:** `vec = 0x50ccdc0(mgr, &out, title="Open Avatar Size", qsAvatarID, &nullSharedPtr, mode=1, filterStr="")` (0x50fd69b) - "find matching avatars":
  * 0x50ccdc0 first test: `0x1dcfbf0(mgr+0x88,0)` (empty list) -> returns empty vec silently.
  * Candidate collection 0x51647a0(mgr, &cand, qsAvatarID, sel=null, mode=1): iterates the scene avatar list (`[[mgr+0x88]+0x238 .. +0x240]`, 16-byte shared_ptr entries). With mode==1 [V 0x51648FE..0x4964A9 region]: **skip avatars whose `byte [avatar+0x990]==0`** (0x50f2010); keep avatar iff `0x50f2660(mgr, avatar.id(+0x530 via 0x50ca3b0), qsAvatarID)` is true. (mode 0 uses other matchers 0x50f1cc0/0x50f04c0/0x51713a0/0x51711a0 - not used here.)
  * Filter 0x515fe10(mgr,&out,"",&cand): avatars with `byte [avatar+0x618]==0` (0x50ef2f0) pass unconditionally; avatars with `+0x618==1` pass only if their string at `+0x660` equals the filter string (empty here). If some avatar had `+0x618==1` and none matched, box "This avatar pose file is not compatible with the current avatar." (0x890f260) [V text, I that +0x618 is a pose-tag flag; normally 0].
  * Result count: **0** -> box "No matching Avatar." (0x50cd017) + empty vec; **exactly 1** -> returned; **>1** -> `App(0x1be0ec0)+0x50 -> vtbl[0x238/8 = 71](&out, title, &candidates)` = a **user avatar-selection dialog** (modal, blocks unattended) [V call, I meaning].
  * An empty returned vec reaches 0x50fd775 (`cmp r14,rsi; je 0x50fdbab`) -> no loop, no further box, return false.

### 2.1 The match predicate 0x50f2660(mgr, idA, idB) [V]
`equal = 0x6665250(idA,idB)` (QString equals, jumps to 0x1bcb7f0); if equal -> true. Else `0x50d3680(mgr,idA) == 0x50d3680(mgr,idB)`.
0x50d3680 maps an id string to a **category** by case-sensitive `contains` (0x6666660 = QString indexOf != -1; checked in this order):

| Category | Substrings tested |
|---|---|
| 1 Female | `FemaleTemplate`, `New_001`, `New_003`, `FemaleVariant` |
| 0 Male | `MaleTemplate`, `New_002`, `New_004`, `MaleVariant` (tested after Female because "FemaleTemplate" contains "MaleTemplate") |
| 2 Boy | `Boy_KidTemplate`, `BoyTemplate` |
| 3 Girl | `Girl_KidTemplate`, `GirlTemplate` |
| 4 PreSchool | `PreSchool_KidTemplate`, `PreSchoolTemplate` |
| 5 Baby | `BabyTemplate` |
| 6 unknown | none of the above |

So `5.1_MaleTemplate_07` (the .avs) matches **any avatar whose id contains `MaleTemplate`/`New_002`/`New_004`/`MaleVariant`** (any template version, also `..._resaved`), and does not match a female/kid avatar. Two ids that are both unknown (category 6) match each other. [V]

## 3. Validation, confirmation, apply (current path) [V]

1. **Validation loop 0x50fd780..0x50fd7ec**: for each `a` in vec: `ok = 0x50f2010(a) (byte a+0x990 != 0)  &&  0x50f2660(mgr, a.id, qsAvatarID)`. If any `!ok` -> 0x50fda73: box "No matching Avatar." -> cleanup -> return **false**; **no avatar is resized** (the apply loop is after the whole validation).
2. 0x50fd7ee..0x50fd8eb: allocates 0x68-byte undo command (0x54a86b0) labelled **"Reset Avatar Size"** if `*reset` (r9 byte) != 0, else **"Load Avatar Size"** (0x890f140 / 0x890f158); copies the scene object (0x5cfe9f0) into it [I: undo snapshot].
3. 0x50fd990: `0x50a8710(mgr, copy-of-vec)`: softbody gate. For each avatar `byte [avatar+0x10B0]` (0x50dea30) - if set: **one** 2-choice modal "The Softbody Option will be turned off to adjust the avatar size. Do you want to proceed?" (0x82972a0, box type 0x11 via 0x4b786c0); answer 2 -> returns false (the path then ends with `r15=0`, nothing resized) [V text+branch, I answer semantics]. Returns true otherwise (and turns softbody off) [I].
4. **Apply loop 0x50fd9e0..0x50fda1f** over vec: `0x510cd70(avatar, &snapshot, mapNode, bWarn=1)` then **`0x511a1b0(avatar, 0, &snapshot, undoCmd)`** (call site 0x50fda06), then free snapshot (0x5092e60).
   * 0x510cd70 [V]: `0x2e96bb0(snap, avatar+0x990)` (copy old map) ; `0x510b9d0(avatar+0x990, map)` (read new map) ; **validity**: `0x51574e0(avatar)` else `0x5157660(avatar)`. **Both false -> `avatar.id (+0x530) += "_resaved"` and `byte [avatar+0x990] = 0`** (0x510cde4 / 0x510cdf0); the driver 0x511a1b0 is still *called* but its gate #1 (flag +0x990) makes it skip the work (finding 19) [V call, I skip]. If valid, `bWarn && reader returned true` -> box "This sizing data was created in a lower version. The body shape and editable measurements options may have been changed according to the updated version." (0x8911340), non-fatal.
   * For the default male .avs: `listMeasureMode` has exactly one 3 and one 1 (check B passes) and BaseFeature/WidthBase/DetailFeature = 0, `bUseProportionBase=false` (check A passes), so validity passes [V values from `raw/avs_tree.json`, finding 19 for the checks]. An invalid map would rename the avatar to `<id>_resaved` (category match still holds afterwards) and silently not resize.
5. Post-loop (0x50fda21): `[rsp+20]` owner (0 from ImportFile) null -> push undo command via singleton 0x3b24020 -> `0x3b24740(stack, cmd, 0,0,1)` (it frees the command instead of recording when a macro/no-document condition holds) [V call, I]; non-null owner -> `0x5507700(owner, cmd)`. `r15 = 1` (set at 0x50fd9cf).

## 4. Legacy path (`ver == 3`) [V], not used by Mirra
Reads the avatar id via 0x4b74ae0 (string at rbp+0xE0). If `cur` is null -> asks the user with `0x50cb060` ("Open Avatar Size" chooser). For the single resulting avatar: needs `a+0x990 != 0` AND `0x50f2660(mgr, a.id, fileId)`, otherwise "No matching Avatar." (0x50fd350) + false. On success: `0x510cf00(avatar,&snap,json)` (same store + validity -> `_resaved` as above but **without** the lower-version box) then **`0x511a1b0(avatar,0,&snap,0)` at 0x50fd450**, `r15b=1`. This is the single-avatar site; it is the legacy format branch, not a "qsAvatarID selects one avatar" branch.

## 5. After the resize (post block 0x50fdc7e..0x50fded1) [V]
Only if `r15 != 0`:
* Persist the path: settings key **`LastAvatarSizingFilePath`** -> value path (0x4b753f0 write; `0x625d850` normalises).
* `0x5d828b0(settings, path)`.
* For `cur.ptr` (if non-null) AND for every avatar in vec: `0x512b870(avatar, path)` (stores the .avs path at `avatar+0x750`) and `0x512b860(avatar, basename)` (stores the file base name at `avatar+0x770`). This is the `qsSizingSrcFileName` value later seen in saved `.dan` (finding 13) [I mapping +0x770 -> qsSizingSrcFileName]. **Note: it also stamps `cur` even when `cur` was not in vec** (only possible in the `cur == null` branch, where `cur.ptr==0` -> skipped) so effectively it stamps exactly the targets.
* UI refresh: `0x5ccd3a0(App)` -> calls `vtbl[+0x100]` on the 2D/3D view objects (0x61548a0/0x61548c0) and `vtbl[+0xB8]` on 0x61548b0 [V calls, I = redraw/refresh]. **No simulation reset or Simulate call is made here** [V: none in the span].
* Return value `al = r15b`: **true only if the apply loop ran** (and the softbody gate did not cancel); false for every early failure, validation failure, empty vec, cancelled softbody prompt. The wider ImportFile chain discards it (finding 36 sec 6).

## 6. Dialogs/messages in the handler (all modal info/choice boxes via 0x4b78600/0x4b786c0)

| # | Text | Where | Trigger | Result |
|---|---|---|---|---|
| 1 | No matching Avatar. | 0x50fd04a | `[mgr+0x88]==0` (no scene object/avatars) | false |
| 2 | Failed to load the Avatar Size file. Invalid file path. | 0x50fd192, 0x50fdf49 | path/file open fails | false |
| 3 | ...created in a lower version. | 0x50fde61 | first dword of .avs is 1 or 2 | false |
| 4 | No matching Avatar. | 0x50fda80 | validation: any target has `+0x990==0` or id category mismatch | false, nothing resized |
| 5 | No matching Avatar. | 0x50cd017 (inside 0x50ccdc0) | `cur==null` and zero valid+matching avatars | false |
| 6 | (avatar chooser, `App+0x50` vtbl[71]) | 0x50ccdc0 | `cur==null` and >=2 matching avatars | blocks for user selection |
| 7 | This avatar pose file is not compatible with the current avatar. | 0x515fe10 | `cur==null`, a matching avatar has `+0x618==1` with non-matching tag | [I] empty target |
| 8 | The Softbody Option will be turned off to adjust the avatar size. Do you want to proceed? | 0x50a87db (0x50a8710) | any target has softbody flag `+0x10B0` | choice; cancel -> false |
| 9 | This sizing data was created in a lower version. The body shape... | 0x510cd70 | valid map but reader flagged old data (`bWarn=1`) | info only |
| 10 | No matching Avatar. | 0x50fd350 | legacy path mismatch | false |

For unattended running: 1,2,3,4,5,8,9 need the watchdog's dismiss list (4/5 share one string); 6 is a real selection dialog.

## 7. Answers to the five questions
1. **Single vs loop:** 0x50fd450 is the *legacy (`ver==3`)* single-avatar path, not a `qsAvatarID` branch. The loop 0x50fda06 is the *current-format* path; it loops over the **target vector**, which is `{current avatar}` or the id-matching search result - not all loaded avatars. The comparison with `qsAvatarID` is `0x50f2660(avatar.id@+0x530, qsAvatarID)` = string equal OR same template category; yes, it is what produces "No matching Avatar.", together with the `+0x990` flag test. [V]
2. **Which avatars are resized when several are loaded:** if a current avatar exists (`mgr+0x98`): only it (and only if it validates). If no current avatar: all avatars with `+0x990!=0` that match; if exactly one -> it; if more than one -> a selection dialog first (the user's choice list becomes the targets) [V structure, I that the dialog returns a subset]. Never "every avatar".
3. **Non-matching avatars:** untouched. If a *target* (current avatar) does not match, the whole load aborts with the box; there is no partial application.
4. **Measure-mode validity failure (0x51574e0 and 0x5157660 both false):** in 0x510cd70 (apply path) and 0x510cf00 (legacy): `id += "_resaved"`, `+0x990 = 0`, driver skips, the handler still returns true and still stamps the sizing source and refreshes the UI (so a silent no-op, with a renamed avatar). Validation 1 above uses the flag *before* the map is loaded (old flag); the new map's validity is only evaluated afterwards.
5. **Post-resize:** settings write, source-name stamping, view refresh via 0x5ccd3a0, undo/redo command push; no simulation reset; return = apply loop ran.

## 8. Rule for the Mirra pipeline
* The `.avs` affects **only the current avatar** whenever one exists; it cannot hit "other" loaded avatars, and `qsAvatarID` cannot pick between two avatars of the same template category (e.g. two `MaleTemplate` avatars) - it only prevents male<->female<->kid cross-application. `qsAvatarID` must be in the same category as the target's `avatar+0x530` id (it is `5.1_MaleTemplate_07` for both the default male `.avs` and `.avt`; an `.avs` with a Female id applied to a male avatar yields "No matching Avatar." and no change).
* Do not rely on "current avatar" implicitly: finding 24 shows `mgr+0x98` is re-pointed to list[0] after a delete while other APIs use the last element. If a previous avatar is still loaded and is the current one, the `.avs` will resize **that** avatar and leave the newly imported one unchanged (or abort if it does not match).
* **Clearing other avatars is still necessary**: (a) to make `mgr+0x98` == the intended avatar, (b) to avoid the `cur == null` multi-match chooser dialog and the softbody prompt on an avatar you did not mean, and (c) the exporter still sees all avatars. Recipe: `clear-avatars` -> ImportAvatar/`ImportFile(.avt)` (exactly one avatar loaded, hence current = it [I that import sets current; single-avatar case is safe either way since `cur==null` + one match also works]) -> `ImportFile(.avs)` -> verify via measurements. Keep the `.avs` `qsAvatarID` equal to the `.avt`'s `qsAvatarID` (category must match), keep `listMeasureMode` with exactly one 3 and one 1 (or all base features set) so the map is valid and the avatar is not renamed `_resaved` / left unresized, and make sure `avatar+0x10B0` (softbody) is off or the softbody box is on the dismiss list.
* Unconfirmed: what sets `mgr+0x98` on import ([I]); the selection dialog's exact semantics (vtbl slot 71 of `App+0x50`); the meaning of `avatar+0x618`/`+0x660`.
