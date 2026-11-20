# Lane Y: the 30 unimplemented API slots, reachability, and workarounds

*Status: done (static analysis only; nothing run, hooked or downloaded)*
*Date: 2026-10-29*
*Target: CLO_Standalone_OnlineAuth_x64.exe 2026.1.336 (build 58954), installed CLOAPIInterface.dll (291,136 B), SDK 2026.1.336 headers*
*Scripts: `scripts/y_gen30.py` (table), `scripts/y_strscan.py` (exe ascii/utf16 string scan). Raw: `raw/y_unimpl_table.md`. Reused: `raw/verify_thunks.json`, `raw/python_proxy_map.json`, `raw/python_prefix_strings.txt`, `scripts/slots_lookup.py`, `scripts/abi_check.py`.*
*Tags: [V] verified from bytes/headers (this lane or a cited lane); [I] inference.*

## 0. Headline

1. The "30 unimplemented" set (25 Pattern slots 196-220, 5 Utility slots 388, 397-400) is confirmed [V]. Slot numbers from the grouped-overload model (`abi_check.slot_model` on the SDK 336 headers) reproduce the mangled import names in `raw/verify_thunks.json` one-for-one (30/30, in slot order).
2. **One of the 30 is not dead:** `UtilityAPI::RemoveGraphicStyle(int)` (slot 388). Its base-class body in the installed DLL (RVA 0xC880) calls vslot 16 (`GetCurrentColorwayIndex`, implemented) and then virtually calls slot 387 (`RemoveGraphicStyle(colorway, graphic, styleChip, overrideMode)`, implemented in the exe at 0x6037500) with `(colorway, idx, -1, 0)` [V]. So the effectively dead set is **29**.
3. The Python-binding proxies give no other route [V for AddGradingSizeGroup (+0x650 = 202*8) and SetGradingPairedAvatarSizing (+0x660 = 204*8); I for the rest]: each proxy logs `[Python] <Name> ` and tail-calls through the same vtable slot, into the same base stub.
4. The GUI has every one of the grading / cut / merge / activate / button features (strings in 2.3), so the engine code is in the exe; only the API wrappers are missing [V strings; I that the engine is reachable only from UI actions].
5. The 336 header marks these virtuals `[TestAPI]` ("New virtuals are appended at the end of the class ... DEV-20962 / 20964 / 20965 review"). The exe's vtable layout has their slots (compiled against a header that declares them) but no override [V]. Why (compiled out of the release build, or pending) is [I]; nothing on disk says.
6. No on-disk evidence of an edition or licence gate (section 2.5). No other CLO build exists on disk to compare (section 4).

## 1. The 30 slots (SDK 336 header signatures)

Slots: grouped-overload model on SDK 336 headers (Pattern 233 virtuals + dtor = 234 slots; Utility 408 + dtor = 409). Thunk RVA = 0x648f103 + 6*(slot-196) for Pattern; Utility thunks at 0x648f0e5/eb/f1/f7/fd. Each thunk is `ff 25 disp32` through the IAT entry to the `CLOAPIInterface.dll` export `?<Fn>@<Class>APIInterface@CLOAPI@@...` [V, lane M]. Stub bodies are from lane M (`20_verification_report.md` row 1d) and match the header default bodies (`return false`, `return {}`, `return -1`, `return ""`). `RemoveGraphicStyle` has two overloads; the thunk (388) is the 1-int one (mangled `...@@H@Z`), slot 387 is the 4-int one.

| # | Class | Slot | Function (SDK 336 header signature) | Thunk RVA | IAT RVA | Base stub body |
|---|---|---|---|---|---|---|
| 1 | Pattern | 196 | `bool SetGradingPairedAvatar(unsigned int _gradingIndex, const std::string& _avatarName)` | 0x648f103 | 0x822b540 | xor al,al; ret -> false |
| 2 | Pattern | 197 | `std::vector<std::vector<float>> GetGraphicGradingScaleRatios(int _graphicStyleIndex, int _patternIndex)` | 0x648f109 | 0x822b538 | returns empty vector |
| 3 | Pattern | 198 | `std::vector<std::vector<float>> GetGraphicGradingPositionOffsets(int _graphicStyleIndex, int _patternIndex)` | 0x648f10f | 0x822b530 | returns empty vector |
| 4 | Pattern | 199 | `bool SetGraphicGradingScaleRatios(int _graphicStyleIndex, int _patternIndex, const std::vector<std::vector<float>>& _scaleRatios)` | 0x648f115 | 0x822b528 | xor al,al; ret -> false |
| 5 | Pattern | 200 | `bool SetGraphicGradingPositionOffsets(int _graphicStyleIndex, int _patternIndex, const std::vector<std::vector<float>>& _offsets)` | 0x648f11b | 0x822b520 | xor al,al; ret -> false |
| 6 | Pattern | 201 | `bool AddGradingSize(unsigned int _gradingSizeGroupIndex, const std::string& _newSizeName)` | 0x648f121 | 0x822b518 | xor al,al; ret -> false |
| 7 | Pattern | 202 | `int AddGradingSizeGroup(bool _bAssignToAllPatterns)` | 0x648f127 | 0x822b510 | mov eax,-1; ret -> -1 |
| 8 | Pattern | 203 | `bool ImportGradeRuleToSizeGroup(unsigned int _gradingSizeGroupIndex, const std::string& _rulFilePath)` | 0x648f12d | 0x822b508 | xor al,al; ret -> false |
| 9 | Pattern | 204 | `bool SetGradingPairedAvatarSizing(unsigned int _gradingIndex, const std::string& _avsFilePath)` | 0x648f133 | 0x822b500 | xor al,al; ret -> false |
| 10 | Pattern | 205 | `bool SetGradingPairedAvatarFromFile(unsigned int _gradingIndex, const std::string& _avtFilePath)` | 0x648f139 | 0x822b4f8 | xor al,al; ret -> false |
| 11 | Pattern | 206 | `bool CutPatternAlongInternalShapes(int _patternIndex, int _internalShapeIndex, bool _bCutAndSew)` | 0x648f13f | 0x822b4f0 | xor al,al; ret -> false |
| 12 | Pattern | 207 | `bool MergeSewnPatterns(int _patternIndexA, int _patternIndexB)` | 0x648f145 | 0x822b4e8 | xor al,al; ret -> false |
| 13 | Pattern | 208 | `std::vector<std::vector<float>> GetPatternInternalShapePoints(int _patternIndex, int _internalShapeIndex)` | 0x648f14b | 0x822b4e0 | returns empty vector |
| 14 | Pattern | 209 | `std::vector<std::vector<float>> GetPatternBaselinePoints(int _patternIndex, int _baselineIndex)` | 0x648f151 | 0x822b4d8 | returns empty vector |
| 15 | Pattern | 210 | `bool AddButtonToPattern(int _patternIndex, float _x, float _y, float _angleDegree)` | 0x648f157 | 0x822b4d0 | xor al,al; ret -> false |
| 16 | Pattern | 211 | `bool AddButtonHoleToPattern(int _patternIndex, float _x, float _y, float _angleDegree)` | 0x648f15d | 0x822b4c8 | xor al,al; ret -> false |
| 17 | Pattern | 212 | `bool TraceBaselineAsInternalShape(int _patternIndex, int _baselineIndex)` | 0x648f163 | 0x822b4c0 | xor al,al; ret -> false |
| 18 | Pattern | 213 | `std::vector<std::vector<float>> GetButtonGradingPositionOffsets(int _buttonIndex)` | 0x648f169 | 0x822b4b8 | returns empty vector |
| 19 | Pattern | 214 | `bool SetButtonGradingPositionOffsets(int _buttonIndex, const std::vector<std::vector<float>>& _offsets)` | 0x648f16f | 0x822b4b0 | xor al,al; ret -> false |
| 20 | Pattern | 215 | `std::vector<std::vector<float>> GetButtonHoleGradingPositionOffsets(int _buttonHoleIndex)` | 0x648f175 | 0x822b4a8 | returns empty vector |
| 21 | Pattern | 216 | `bool SetButtonHoleGradingPositionOffsets(int _buttonHoleIndex, const std::vector<std::vector<float>>& _offsets)` | 0x648f17b | 0x822b4a0 | xor al,al; ret -> false |
| 22 | Pattern | 217 | `bool ActivateAllPatterns(bool _bActivate, bool _bIncludeSewing)` | 0x648f181 | 0x822b498 | xor al,al; ret -> false |
| 23 | Pattern | 218 | `std::vector<std::vector<float>> GetPatternOutlinePoints(int _patternIndex)` | 0x648f187 | 0x822b490 | returns empty vector |
| 24 | Pattern | 219 | `std::vector<std::vector<float>> GetPatternPointGradingPositionOffsets(int _patternIndex, int _pointIndex)` | 0x648f18d | 0x822b488 | returns empty vector |
| 25 | Pattern | 220 | `bool SetPatternPointsGradingPositionOffsets(int _patternIndex, const std::vector<int>& _pointIndices, const std::vector<std::vector<float>>& _offsets)` | 0x648f193 | 0x822b480 | xor al,al; ret -> false |
| 26 | Utility | 388 | `std::string RemoveGraphicStyle(int _graphicIndex)` | 0x648f0e5 | 0x822b568 | NOT dead: delegates to slot 387 (section 3) |
| 27 | Utility | 397 | `void SetAssetShareRoot(const std::string& _shareRoot)` | 0x648f0eb | 0x822b560 | ret (void no-op) |
| 28 | Utility | 398 | `std::string GetAssetShareRoot()` | 0x648f0f1 | 0x822b558 | returns empty string |
| 29 | Utility | 399 | `void SetBasePath(const std::string& _basePath)` | 0x648f0f7 | 0x822b550 | ret (void no-op) |
| 30 | Utility | 400 | `std::string GetBasePath()` | 0x648f0fd | 0x822b548 | returns empty string |

A caller sees `false` (16 bool functions), empty `vector<vector<float>>` (8 getters), `-1` (`AddGradingSizeGroup`), or nothing / empty string (path functions). Nothing raises or logs, so "unsupported" is indistinguishable from "failed" except by the constant pattern [I].

What each does in the GUI (header doc comments, 336): `AddGradingSizeGroup` = "Add (And Assign) Grading Rule Table"; `AddGradingSize` = "Add Size"; `ImportGradeRuleToSizeGroup` = "Open Grade Rule File" on a rule table; `SetGradingPairedAvatarFromFile` = "Pair 3D Form"; `SetGradingPairedAvatarSizing` = "Add Avatar Size" in the Pair Avatar tab (needs a resizable paired avatar and a v3+ .avs whose gender/avatar ID matches); `CutPatternAlongInternalShapes` = 2D "Cut" / "Cut & Sew"; `ActivateAllPatterns` = 3D "Deactivate (Pattern & Sewing)" / "Activate"; `Get/SetPatternPointsGradingPositionOffsets` = "Edit Grading" Distance table (mm, Y up); the path functions resolve project-relative `//folder/file` paths (header: opening a project sets the base path automatically).

## 2. Is the same feature reachable another way in the exe?

### 2.1 Python-binding proxies

All 30 names have `[Python] <Name> ` trace strings (`raw/python_prefix_strings.txt`, e.g. 0x898ddf0 AddGradingSizeGroup, 0x898de38 SetGradingPairedAvatarSizing, 0x898de60 SetGradingPairedAvatarFromFile, 0x899f728 RemoveGraphicStyle, 0x899f888-0x899f8e0 the four path functions) [V].

Proxy for `AddGradingSizeGroup` (code 0x5f12760-0x5f127cb): trace string, `APICommand::GetPatternAPI()` (IAT 0x822b578), `mov r8,[rcx+0x650]` (= 202*8), `jmp r8` [V]. `SetGradingPairedAvatarSizing` proxy loads `[rcx+0x660]` (= 204*8) [V]. `raw/python_proxy_map.json` decoded slots 197, 208, 209, 213, 215, 218, 219 equal to the model [V]. So the Python layer is a logging shim over the same vtable and lands in the same stub; no Python-only implementation [I for proxies not individually disassembled]. For `RemoveGraphicStyle` the 1-int proxy (0x5f24f07) calls slot 388 (`[r9+0xC20]`) and the 4-int proxy (0x5f24f9f) calls slot 387 (`[r10+0xC18]`) [V].

### 2.2 Implemented read-side grading APIs (slots < 196, real code)

[V] `Marvelous::PatternAPI::...` `__FUNCSIG__` strings at 0x8996dd0-0x8997f50 and slots from `slots_lookup.py`: `GetValidGradingSizeGroupCount` 137, `GetGradingSizeGroupInformation` 138, `GetGradingSizeGroupCount` 139, `GetGradingSizeTotalCount` 140, `GetCurrentGradingSizeIndex` 141, `GetGradingSizeListFromRuleTable` 142/143, `GetGradingSizeNameList` 144 (+W), `ChangeGradingSizeInformation` 146/147 (switch active size), `GetGradingPairedAvatar` 148, `Get/SetGradingSizeQuantityMix` 179/180, `GetGradingSizeTotalQuantity`. None of the 30 has a `Marvelous::PatternAPI::<name>` / `Marvelous::UtilityAPI::<name>` signature string in the exe (only the mangled import names) [V], consistent with "no override".

### 2.3 GUI-only code paths (engine exists, no API wrapper)

[V strings, `scripts/y_strscan.py`]: `Add Size` (0x83ca788), `Pair 3D Form` (0x83cac08), `Add Avatar Size` (0x83cac18), `Delete Pair Avatar Size` (0x83cac40), `Update Pair Avatar Grading Size`; slots `OnAddGradingRuleTable` / `OnAddAndAssignGradingRuleTable` / `OnDeleteGradingRuleTable` (0x83ca4d8-0x83ca810), `OnOpenGradingRuleFile` / `OnSaveGradingRuleFile` (0x830b0e8, 0x830b108); `actionAuto_Grading`, `action_Edit_Grading`, `Grading Distance`; `Cut & Sew` (0x827af98), `Cut & Sew Pattern (2D)`, `Merge Pattern By Seamline (2D)`, `Merge Patterns`, `Deactivate (Pattern & Sewing)` (0x8324cd8), `Activate Sewing (All)`; `Create Button`, `Create Buttonhole`, `Register Buttonhole`, `Convert To Buttonhole`, `Unlink Buttons/Buttonholes`. Messages: `Do not have a paired avatar.` (0x8291230), `No grading table is available` (0x8291250), `No graded size available to edit. Add a size in the Grading tab in the Object Browser.` (0x82909b0), `Grading rule (*.rul) files cannot be opened by drag and drop.` (0x8290ce8). Undo class `UnReAddPairAvatarResizingStatus`. [I] The wrappers would call the same code the GUI actions call (header says "API equivalent of the GUI ..."); they are not in the vtable subclass.

### 2.4 File-based routes

- Serialisation keys present in the exe [V strings]: `GradingRuleTableList` (0x8837110), `GradingInfo` (0x8867b08), `listGradingSizeNameList` (0x8882628), `iGradingRuleTableIndex` (0x8891358), `listGraphicGradingInfo`, `listGradingCalculatedKey`, `listGradingNode`, `mapGradingPatternList` (0x893ec50), and `clo.pattern.v1.GradingRuleTable{id,name,default_size,size_list}`. Literal `listGrading` / `mapGradingInfo` were not found (closest names above). A `.zprj` that already holds grading therefore carries rule tables and (by key names) pair-avatar data [I; `findings/23` does not decode them].
- `.rul`: opened by File > Open only when the rule name matches the patterns' rule name (header text), not by drag and drop (exe string) [V]. Whether `ImportFile` (Import slots 1-2, implemented) takes `.rul` was not decoded [unknown].
- Graded DXF: `ExportDxfOption::m_bExportWithoutGrading` and `ImportDxfOption::m_bRemoveNonGradingPoints` exist in CloApiData.h, so DXF carries grade points [V header]; whether `ImportDXF` (Import slot 21) builds a rule table from them was not decoded [unknown].
- There is no file route for per-size avatar pairing other than a saved `.zprj`.

### 2.5 Licence / edition gating (strings only; no licence/auth code analysed, no bypass)

Strings present: `This feature is not available in the trial version.` (0x85abf50), `isEnterpriseLicense` (0x83ddfe8), `Enterprise` (0x847b788), `license_edition` / `&license_edition=` (0x8266f08, 0x834c568), `Integration is deactivated for this license ID. Please contact us to activate` (UTF-16, 0x86f6025), `Alvanon Body Platform subscription is required ...`. None names any of the 30 functions or a grading/button feature. The stubs are dead by vtable construction (no wrapper exists at all), not by a runtime `if (licensed)` branch, which would leave a wrapper with a body [I]. The same build ships the GUI grading features. Treat "licence-gated" as unsupported by the evidence.

## 3. `RemoveGraphicStyle(int)` is functional

Installed DLL body (RVA 0xC880, `dumpbin /disasm`): saves rbx/rbp/rsi/rdi; `rbx=[rcx]`; `call [rbx+0x80]` (slot 16 `GetCurrentColorwayIndex`); `[rsp+28h]=0`, `[rsp+20h]=-1`, `r9d=idx`, `r8d=colorway`; `call [rbx+0xC18]` (slot 387, 4-int overload, exe 0x6037500); returns the string [V]. Equals the header text "Equivalent to RemoveGraphicStyle(GetCurrentColorwayIndex(), _graphicIndex, -1, 0)". Result is the JSON `status`/`message` string. For explicit colorway / mode call the 4-int overload.

## 4. Which exe build is this, and could another build implement them?

Evidence on disk only:
- `CLO_Standalone_OnlineAuth_x64.exe`: ProductName `CLO Standalone OnlineAuth`, FileVersion `2026, 1, 336, 58954`, 220,466,496 B, mtime 2026-10-29 14:52 [V]. The product string is also in-binary (0x827de30; UTF-16 0xd26d30c). So the main build **is** the Standalone OnlineAuth variant [V].
- `Uninstall.exe` and the only installer in Downloads (`CLO_Standalone_OnlineAuth_2026_1_224_Installer_x64.exe`, 2,296,754,456 B) are both `2026.1.224.58461` [V]. The 336 exe and DLL arrived via the in-app updater: `liveupdate.txt` (361,984 B) lists `clo_so:/CLO_Standalone_OnlineAuth_x64.exe:ff5e2aab...:220466496` and `clo_so:/CLOAPIInterface.dll:fbda7a50...:291136`, and the exe has `LiveupdateWorker` strings [V]. `clo_so` is read as the channel prefix for this product [I]. No `clo_sdk`-style or enterprise channel/file entry appears in `liveupdate.txt` or the exe strings [V].
- The SDK package (`CLO_SDK_v2026.1.336_Win`: headers, `Lib/CLOAPIInterface.dll` 169,472 B, six samples, 2020 overview PDF) holds no build matrix or release notes saying which CLO build implements which API [V]. The installed DLL (291,136 B) is larger than the SDK DLL but exports the same 921 names (lane M). `ChangeLog_CLO.html` in the install dir has no text [V].
- No other CLO installer or build is on disk, so there is **no evidence either way** that an SDK-enabled/full build implements the 30 [V absence]. Supported: header says `[TestAPI]` + DEV review tags; the exe has a slot for each but no override; the same exe has the full GUI features. Likely [I]: the shipping configuration omits the test-API overrides, or they land in a later build. Slot positions already match SDK 336, so a build that implements them would not need a plugin rebuild [I].
- Practical: pin to 336 and use the workarounds below; do not wait on a future build.

## 5. Plugin-author table: needed capability to alternative

| Needed Mirra capability | Dead API(s) it would have used | Available alternative / workaround | Confidence |
|---|---|---|---|
| Grading across sizes (S/M/L/XL of one garment) | `AddGradingSizeGroup` 202, `AddGradingSize` 201, `ImportGradeRuleToSizeGroup` 203, `Get/SetPatternPointsGradingPositionOffsets` 219/220, graphic/button grading offsets 197-200, 213-216 | (a) **One garment per size.** Step 2 already emits per-size block DXF (`output/<cloth_id>-<size_id>-<run>`); import each with `ImportDXF` (Import 21) into a fresh project and drape on the matching avatar. No grading engine needed. (b) **Pre-graded template `.zprj`:** build the rule table and sizes once in the CLO GUI, save, open via ImportFile, switch with `ChangeGradingSizeInformation(group,size)` (146/147), read `GetGradingSizeNameList` (144), `GetCurrentGradingSizeIndex` (141), `GetGradingSizeGroupCount` (139). (c) Graded AAMA/ASTM DXF import may create rules; untested. | (a) [V] APIs exist; (b) [V] APIs, workflow [I]; (c) unknown |
| Sizing a garment to an avatar (pair avatar per size, apply `.avs`) | `SetGradingPairedAvatar` 196, `SetGradingPairedAvatarFromFile` 205, `SetGradingPairedAvatarSizing` 204 (the plugin's `grading-avatar-size` experiment) | Keep the existing route: `ImportAvatar` (Import 37; `.avt` plus patched `.avs`/`listFeatureValues`, `findings/19`, `findings/15`), choose the garment size with Mirra's size model (`mirra_measurements`) and import that size's DXF (row above). Read-only `GetGradingPairedAvatar` (148) works if a template `.zprj` already has pairings. Remove or disable the `AddGradingSizeGroup` / `SetGradingPairedAvatar*` calls in `RestPlugin_windows.cpp` (lines ~1253, 1956-1965): they only return -1 / false. | [V] stub returns; workflow [I] |
| Buttons on a placket | `AddButtonToPattern` 210, `AddButtonHoleToPattern` 211, `TraceBaselineAsInternalShape` 212 | Implemented: `PlaceButtonPairsOnEdge` (Pattern 231) and `DistributeButtonPairsOnEdge` (232) (button/buttonhole pattern + line index, edge offset, count/spacing; return string), `ConvertTrimsToButtons` 314, `CreateButtonholesForButtonHeads` 315, `FastenButtons(maxDist)` 316, `UnfastenAllButtons` 317, `GetButtonPairInfoAsJson` 318, `OpenButtonHeadStyleFileByIndex`, `Get/SetButtonHeadStyleColor`, `Get/SetButtonHoleStyleColor`. Or bake buttons into a template `.zprj`, or create internal shapes (`CreateInternalShapeWithPoints` 93) and convert with `ConvertTrimsToButtons`. | slots [V]; behaviour [I] |
| Read pattern geometry (outline, baseline, internal shapes) | `GetPatternOutlinePoints` 218, `GetPatternBaselinePoints` 209, `GetPatternInternalShapePoints` 208 | `GetPatternLineInfo` (194, returns a string; format not decoded here), `GetPatternPiecePos` (78), `GetPatternPieceArea`; or `ExportDXF` and parse the DXF. | slots [V]; format unknown |
| Cut / merge pattern pieces | `CutPatternAlongInternalShapes` 206, `MergeSewnPatterns` 207 | No API. Produce cut / merged geometry in `clo_block` before DXF import. | [I] |
| Deactivate / activate all patterns | `ActivateAllPatterns` 217 | No pattern-level API in the header. Avatar-level `SetAvatarActivation` (Utility 306) exists. Workaround: import only the needed components (336 `ImportExportOption` component lists) or open a project without the pieces. | [I] |
| Remove a graphic from the current colorway | `RemoveGraphicStyle(int)` 388 | **Works** via delegation to slot 387; call the 4-int overload for explicit colorway / mode. | [V] |
| Fixed base / share path for `//folder/file` | `Set/GetBasePath`, `Set/GetAssetShareRoot` | No effect. Use absolute paths in Import/Export calls; the exe sets the base path itself when a project opens (header). | header [V], exe behaviour [I] |
| Earlier recommendations | `findings/09_unused_useful_apis.md` recommends `AddGradingSize`, `ImportGradeRuleToSizeGroup`, `SetGradingPairedAvatar`, `Get/SetPatternPointsGradingPositionOffsets` | Those are on the dead list; do not build on them. `GetGradingPairedAvatar`, `ChangeGradingSizeInformation`, `GetGradingSize*` remain valid. | [V] |

## 6. Limits

- Static only. Proxy disassembly was done for AddGradingSizeGroup, SetGradingPairedAvatarSizing and RemoveGraphicStyle; others rely on lane J's slot decode and the identical string-then-vtable pattern.
- "No wrapper" is judged from the thunk bytes (the exe supplies no override) and the absence of `Marvelous::<Class>API::<fn>` `__FUNCSIG__` strings.
- Whether `ImportFile` / `ImportDXF` build grading rules from `.rul` / graded DXF was not decoded.
- No licence/auth logic read; 2.5 is strings only.
- Build/variant statements rely on file metadata on disk; no other CLO build exists locally.
