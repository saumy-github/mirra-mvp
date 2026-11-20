# Lane AF: implemented grading / size-group APIs and size switching on CLO 2026.1.336

*Status: done (static only; nothing run, hooked or downloaded)*
*Date: 2026-10-29*
*Target: CLO_Standalone_OnlineAuth_x64.exe 2026.1.336, SDK 336 headers (`CLOAPIInterface/include/PatternAPIInterface.h`)*
*Scripts: `scripts/af_enum.py` (enumeration), `scripts/disasm_fn14.py` (copy of disasm_fn3, cache `raw/disasm14/`). Raw: `raw/af_grading_enum.txt`, `raw/af_0x*.txt` (annotated disassembly summaries). Reused: `scripts/abi_check.py` slot model, `raw/abi_exe_vtables_cache.json`, `raw/verify_thunks.json`.*
*Tags: [V] verified from bytes/headers; [I] inference.*

## 0. Headline

1. Grading-related virtuals exist only on `PatternAPI` (no Utility/Import/Export/Fabric/Gui/Rest virtual contains Grading / GradeRule / SizeGroup; Utility's only "Size" names are `Set/GetPatternSnapShotSizeOption`, unrelated) [V grep + enumeration]. 16 slots are implemented (136-148, 179-181) and 16 are dead thunks (196-205 plus 213-216, 219, 220; the grading-offset ones beyond 196-205 are in lane Y's 206-220 set). All implemented ones are READ/SWITCH APIs; every API that CREATES or EDITS a size group (AddGradingSizeGroup, AddGradingSize, ImportGradeRuleToSizeGroup, pairing) is a thunk [V].
2. **A size switch on a template `.zprj` that already contains a grading size group can be driven purely through the API** with `GetGradingSizeGroupCount` / `GetGradingSizeGroupInformation` / `GetGradingSizeListFromRuleTable` / `GetGradingSizeNameList` to discover, `ChangeGradingSizeInformation` to switch, and `GetCurrentGradingSizeIndex` to confirm. The group only has to exist in the loaded document; it does NOT have to have been created in the GUI session, just authored by something CLO can save (GUI-built `.zprj`) because the API cannot author one [V that the wrappers read the document's group list; I that a `.zprj` round-trips it, which is standard CLO behaviour and not re-verified here].
3. The switch wrapper is the same routine the GUI uses (undo-step label "Change Grading Size", UI context "PatternEditorGrading") [V strings]. It rebuilds the patterns; **no Simulate call is made in the wrapper chain I traced** (depth 2), so a `Simulate()` afterwards is needed to re-drape [I]. Caveats in section 4 (paired avatar swap, modal parametric-pattern prompt).
4. **Graded DXF import**: the DXF reader parses `GRADE RULE TABLE`, `NUMBER OF SIZES`, `SIZE LIST`, `SAMPLE SIZE`, `RULE:` and keeps per-piece multi-size records, and the build step names a "Size Group". So a graded ASTM DXF very probably yields graded pieces that are in a size group. Whether `ImportDXF` registers an editor-level group that `ChangeGradingSizeInformation` can switch is **not proven** by static reading [I]. Mirra's own DXF writer emits no rule table, so it never creates one.

## 1. Table: every grading / size-group / rule virtual in PatternAPI (SDK 336)

Slots from the grouped-overload model (`abi_check.slot_model`), exe RVAs from the cached exe vtable. "Overload order": MSVC puts the later-declared overload at the lower slot (see section 2).

| Slot | Function (SDK signature) | Status | Exe RVA / thunk | Notes |
|---|---|---|---|---|
| 136 | `std::vector<std::wstring> GetValidGradingSizeGroupInformation()` | impl | 0x601d940 | groups valid for the loaded patterns |
| 137 | `unsigned int GetValidGradingSizeGroupCount()` | impl | 0x601d6b0 | |
| 138 | `std::vector<std::wstring> GetGradingSizeGroupInformation()` | impl | 0x5feb310 | names of ALL groups |
| 139 | `unsigned int GetGradingSizeGroupCount()` | impl | 0x5feafa0 | = (vec end - vec begin)/16 of the document grading-manager list at manager+0x200/0x208 [V] |
| 140 | `unsigned int GetGradingSizeTotalCount()` | impl | 0x5fecc70 | returns 1 when no table [V: `test al; mov esi,1` branch] |
| 141 | `unsigned int GetCurrentGradingSizeIndex()` | impl | 0x5fe19c0 | no table -> alternative branch (0 expected [I]) |
| 142 | `GetGradingSizeListFromRuleTable(unsigned int _group)` | impl | 0x5febae0 | wstring names of sizes in group |
| 143 | `GetGradingSizeListFromRuleTable(const std::wstring& _groupName)` | impl | 0x5feb6c0 | |
| 144 | `std::vector<std::string> GetGradingSizeNameList()` | impl | 0x5febf20 | sizes of the current table; defines "grading index" order used by all per-size APIs |
| 145 | `std::vector<std::wstring> GetGradingSizeNameListW()` | impl | 0x5fec310 | |
| 146 | `bool ChangeGradingSizeInformation(unsigned int _group, unsigned int _size)` | impl | 0x5fa41f0 | 0-based indices |
| 147 | `bool ChangeGradingSizeInformation(const std::wstring& _group, const std::wstring& _size)` | impl | 0x5fa3dd0 | by names (UTF-16) |
| 148 | `std::string GetGradingPairedAvatar(unsigned int _gradingIndex)` | impl | 0x5fead90 | read-only |
| 179 | `std::map<std::string,int> GetGradingSizeQuantityMix(int _group)` | impl | 0x5fec720 | |
| 180 | `bool SetGradingSizeQuantityMix(int _group, const std::map<std::string,int>&)` | impl | 0x604fed0 | false if group index invalid (header) |
| 181 | `int GetGradingSizeTotalQuantity(int _group)` | impl | 0x5fece90 | |
| 196 | `SetGradingPairedAvatar(uint, const std::string&)` | THUNK -> false | 0x648f103 | |
| 197-200 | `Get/SetGraphicGradingScaleRatios`, `Get/SetGraphicGradingPositionOffsets` | THUNK | 0x648f109..11b | |
| 201 | `AddGradingSize(uint, const std::string&)` | THUNK -> false | 0x648f121 | |
| 202 | `int AddGradingSizeGroup(bool)` | THUNK -> -1 | 0x648f127 | |
| 203 | `ImportGradeRuleToSizeGroup(uint, const std::string&)` | THUNK -> false | 0x648f12d | |
| 204 | `SetGradingPairedAvatarSizing(uint, const std::string&)` | THUNK -> false | 0x648f133 | |
| 205 | `SetGradingPairedAvatarFromFile(uint, const std::string&)` | THUNK -> false | 0x648f139 | |
| 213-216 | `Get/SetButtonGradingPositionOffsets`, `Get/SetButtonHoleGradingPositionOffsets` | THUNK | 0x648f169..17b | |
| 219-220 | `GetPatternPointGradingPositionOffsets`, `SetPatternPointsGradingPositionOffsets` | THUNK | 0x648f18d/193 | |

Non-grading virtuals matched by the name filter and ignored: `GetPatternSize` (deprecated count), `GetPinListSize`. No Utility virtual mentions Grading, GradeRule or SizeGroup; the only grading-adjacent data types are `ImportDxfOption::m_bRemoveNonGradingPoints`, `ExportDxfOption::m_bExportWithoutGrading` (CloApiData.h lines 588, 750) and the Object-Browser tab enum `OB_TYPE_GRADING` [V].

## 2. Decoded wrappers

### 2.1 Common prologue [V]
Every wrapper first logs `Marvelous::PatternAPI::<signature>` (string visible in each body), then fetches the document's pattern-editor grading manager via `0x141BF5E20` + `0x145CFE9F0` (returns a `shared_ptr`; global-singleton chain). A null result makes getters return their default (0 / empty) and setters return false. The size-group list is the vector of 16-byte shared_ptr entries at manager+0x200..0x208 (group = element index, 0-based).

### 2.2 `ChangeGradingSizeInformation(uint group, uint size)` @ 0x5fa41f0 (slot 146)
- Bounds: loads `count = (end-begin)/16`; `if (count < group) return false` then reads element `group`. This is an off-by-one: `group == count` passes the check and reads one entry past the end (a null/garbage shared_ptr) [V `cmp rax,rdi; jb` at 0x145FA43D1]. Callers must pass `group < GetGradingSizeGroupCount()`.
- Validates the group object with `0x14571E250` (looks the group up in manager+0x5B8; false -> returns false).
- Calls worker `0x1455FF1E0(manager, &group_sp, size_index)` and returns its bool. Return values: true = switched, false = bad manager/group/size or worker failure [V].
- The size index is validated inside the worker chain (`0x145609EA0` returns false -> the undo step is dropped and the function returns false) [V flow, I exact check].

### 2.3 `ChangeGradingSizeInformation(wstring group, wstring size)` @ 0x5fa3dd0 (slot 147)
Loops the group list comparing names (wstring equality via `0x146666A30`/`0x146665250`), then loops that group's size names; if either is not found the result is false (`jle`/`cmp` falls through to return 0). On a match it calls the same worker `0x1455FF1E0` [V]. Names are exact wide strings, so use `GetGradingSizeGroupInformation()` / `GetGradingSizeListFromRuleTable()` output verbatim.

### 2.4 Worker `0x1455FF1E0` (the real switch) [V partially]
Creates an undo command labelled "Change Grading Size" (context string "PatternEditorGrading"), builds a pre-change snapshot, runs the size change (`0x145609EA0`), pushes the undo step, calls a per-item refresh over the returned pattern list (`0x1456C1ED0` + loop `0x144CBA820`) and a view refresh (`0x145CD0220`). Both overloads therefore go through the GUI undo stack; there is no simulation-step call in this chain [I from call list; the chain was followed two levels only].

### 2.5 Overload order [V]
Slot 142 (0x5febae0) has no string-equality call (index version) and 143 (0x5feb6c0) has one (name version); 146 takes the index (`mov r14d,r8d; mov edi,edx` are uints) and 147 the names. So MSVC lays the later-declared overload at the lower slot. The plugin compiled against the 336 header resolves this automatically; only a hand-written vtable call would need to know.

### 2.6 Getters
`GetGradingSizeGroupCount/Information`, `...TotalCount`, `...CurrentIndex` need only the grading manager; no table gives 0 / 1 / empty (140 returns 1 when the "no table" predicate `0x141C09700` is true). `GetGradingSizeNameList` (144) returns the sizes of the current table in the order that per-size indices (`_gradingIndex`) refer to. `GetGradingPairedAvatar(i)` returns the paired avatar name, empty when none.

## 3. Can a size-switch on a template `.zprj` be driven purely through the API?

Yes, for any size group that is already stored in the project:

1. `OpenFile`/`ImportFile` (open the `.zprj`) - group list appears in the grading manager [I standard behaviour].
2. `GetGradingSizeGroupCount()` > 0 else abort (the API cannot create one; `AddGradingSizeGroup` returns -1) [V].
3. Discover names: `GetGradingSizeGroupInformation()`, `GetGradingSizeListFromRuleTable(groupIdx)`.
4. `ChangeGradingSizeInformation(groupIdx, sizeIdx)` (or the name form). Returns bool.
5. Confirm: `GetCurrentGradingSizeIndex() == sizeIdx`.

Requirements and risks:
- A size group must exist in the `.zprj`; it must be authored in the CLO GUI (or arrive via a graded DXF, see section 5). It does not have to be created in the same session.
- **Paired avatar swap [I from header docs of the thunked APIs]**: the header says "the paired avatar activates automatically on switching to its size". If the template was saved with Pair 3D Form entries, a switch replaces the scene avatar with the paired one, clobbering Mirra's measured avatar. Author the template with NO pairings (check each size with `GetGradingPairedAvatar(i)` == "") and import/apply the Mirra avatar AFTER the switch.
- **Simulate**: not called by the wrapper (see 2.4). After the switch the 2D patterns/3D mesh are rebuilt at the new size; the cloth is un-draped relative to the avatar until `Simulate()` runs [I]. Do the switch before the simulation, never after a drape.
- **Modal prompts**: the undo-push routine `0x143B24740` contains the string "If you directly edit a parametric pattern, it can no longer be edited in the Pattern Drafter. Are you sure you want to proceed?" [V string]. Whether the grading switch can reach it (only for parametric-drafter patterns) is not established. Mirra block patterns imported from DXF are not parametric, so the risk is low but not zero [I].
- GUI widgets are not refreshed (header note on the thunked APIs says the same; headless is fine).

## 4. Other behaviours worth knowing

- Per-size quantity mix (179-181) is the only write API on groups; it needs an existing group index (header: false if invalid).
- Per-size item offsets (buttons, graphics, points) are all dead (213-220, 197-200), so garments must carry their grading from the GUI/DXF.
- `GetGradingSizeNameList` is group-less (current table); use `GetGradingSizeListFromRuleTable(group)` for other groups.

## 5. Does graded DXF import create a switchable size group?

Evidence [V]:
- The annotation parser `0x144096C80` recognises `UNITS`, `GRADE RULE TABLE`, `NUMBER OF SIZES`, `SIZE LIST`, `SAMPLE SIZE`, `RULE:` / `RULE :` and hands rule text to `0x144099000` (string `RULE`) which builds rule-table entries.
- Reader helper `0x144095E40` returns "first piece has more than one size record" (record stride 0x118): the reader models graded pieces explicitly.
- Build step `0x1440988E0` references the string "Size Group" (0x88687C0) and iterates per-piece size records, defaulting the group name when empty.
- `ImportDxfOption::m_bRemoveNonGradingPoints` and `ExportDxfOption::m_bExportWithoutGrading` exist, i.e. grading is a first-class part of the DXF path. Post-process `0x14476BFD0` also has a `.rul` branch (strings `rul`, `.rul`).

Not proven: that the group appears in the manager list at +0x200 (what `GetGradingSizeGroupCount` reads) after `ImportDXF`, and that sizes switch correctly. [I] likely yes (CLO's GUI imports graded AAMA DXF as a rule table, and the importer wrapper is the same path as File-Open), but a one-time live check (`GetGradingSizeGroupCount()` after importing a graded ASTM DXF) is the only way to settle it. `findings/32` shows Mirra's DXF writer would need to emit `GRADE RULE TABLE:`, `NUMBER OF SIZES:`, `SIZE LIST:`, `SAMPLE SIZE:` plus per-size grade-point data (layers 5/6 grade-reference lines) in the AAMA grade block, whose exact grammar is not decoded in this repo.

## 6. Recommended Mirra size-switching flow

Option A (recommended now, uses only [V] mechanics): template `.zprj` per garment with a GUI-authored size group and NO avatar pairings.
1. Open template `.zprj` [V implemented]. 
2. `n = GetGradingSizeGroupCount()`; require `n >= 1` [V]. `names = GetGradingSizeListFromRuleTable(0)` [V].
3. Map Mirra size label to index (exact wstring match) using Mirra's size model [V API, I mapping].
4. `ChangeGradingSizeInformation(0, idx)`; require true and `GetCurrentGradingSizeIndex() == idx` [V]. Guard `group < n` because of the off-by-one in 2.2 [V].
5. Verify no pairing: `GetGradingPairedAvatar(i) == ""` for all `i` in `GetGradingSizeNameList()`; if non-empty, treat the template as invalid [V getter, I swap behaviour].
6. Apply Mirra avatar (ImportAvatar .avs/.avt) AFTER the switch [I ordering].
7. `Simulate()` [I that it is needed], then export/fabric steps as today.
8. On false from step 4: fall back to the existing per-size block DXF route (one garment per size) [V route exists].

Option B (needs one live test): author graded ASTM DXF (rule table) in `clo_block`, `ImportDXF`, then steps 2-7. Gate on `GetGradingSizeGroupCount() >= 1` after import; if 0, the DXF did not register a group and Option A or per-size DXF must be used [I].

Do not call: `AddGradingSizeGroup`, `AddGradingSize`, `ImportGradeRuleToSizeGroup`, any `SetGradingPaired*` (all no-ops returning -1/false). `findings/09` recommendations for them remain dead.

## 7. Open items

- Live confirm: `Simulate` required after a switch, avatar-swap behaviour, and `GetGradingSizeGroupCount` after graded DXF import (all need one CLO run, out of scope).
- Worker `0x145609EA0` / `0x14578A150` were not decoded; the exact size-index validation and the mesh-rebuild path are inferred from call counts.
