# Log / diagnostic message catalog (CLO 2026.1.336, static)

*Status: static analysis of `CLO_Standalone_OnlineAuth_x64.exe` (mmap, no execution) plus read-only look at CLO's on-disk logs. Items marked (inference) are not runtime-verified.*
*Date: 2026-10-29*
*Lane J. Scripts: `scripts/log_catalog.py`, `scripts/proxy_map.py`, `scripts/msg_catalog_gen.py`, `scripts/write_17.py`. Raw: `raw/log_catalog.json`, `raw/python_prefix_strings.txt` (907 strings), `raw/python_str_xrefs.json`, `raw/python_proxy_map.json`, `raw/msg_by_function.json`, `raw/cloapi_iat.json`.*

All addresses are RVAs (VA = 0x140000000 + RVA).

## 0. Headline discoveries

1. **`Logger::Log(level, msg)` is an analytics/usage-event emitter, not a debug log, and `level` is the API-group index.** `Logger::Log` (0x4e10fb0) calls 0x390e2c0, which builds `{"time":..,"category":"API","subcategory":"CLO API","group":<group>,"feature":<msg>,"additional_json":{}}`; the group names sit at 0x88316f8 in the order `ExportAPI, ImportAPI, UtilityAPI, FabricAPI, PatternAPI, RestAPI, GuiAPI` and the builder does a map lookup keyed on `level`. This matches lane D's observed levels (Export* = 0, Import* = 1, Utility* = 2), so lane D's "0 = debug, higher = info" reading in `findings/11` is probably wrong: the number selects the group. On-disk evidence: `%LOCALAPPDATA%\CLO Virtual Fashion\CLO Standalone OnlineAuth\<n>\log\log_0.json` holds exactly this shape, e.g. `"group":"UtilityAPI","feature":"void __cdecl Marvelous::UtilityAPI::DisplayMessageBox(...)"` (section 5). (The group-index reading is inference from the string order plus the three matching levels; the map contents were not dumped.)
2. **A second, separate set of `[Python] <Name> ` messages (about 850 strings, one per API function plus `...W` variants).** They are `QMessageLogger::info()` traces emitted by the **Python-binding layer** of the exe (code sites 0x5db840b-0x5f8a820, immediately *below* the Marvelous::*API wrappers), which then forwards through `CLOAPI::APICommand::getInstance().Get<X>API()->vfn(...)`. A plugin that calls the vtable directly does **not** produce them; it produces the FUNCSIG analytics event instead. 542 of 546 proxy functions whose vtable slot could be decoded use exactly the slot the SDK header predicts (the 4 outliers are decode noise: Gui AddNumberInput/AddSlider/SetWindowCloseCallback, Rest CallbackRestRequest), an independent confirmation of the slot model in `findings/14`.
3. **Real diagnostics inside the wrappers are of three kinds:** (a) `qInfo() << "[Python]" << tr("Please Load Avatar")`-style Qt messages (avatar getters/setters, `GetAvatarMeasurements`, `ImportPose`); (b) nothing at all (most wrappers fail silently with false/0/empty, see lane D); (c) **new in 336, JSON results**: nine Fabric/Pattern functions return a JSON string with `status` (`success`/`failed`) and `message`, so their error text is *in the return value* and never logged (section 4.3).
4. **Headless mode changes where Qt messages go.** A Qt message handler at RVA 0x62b3ee0 prints `yyyy-MM-dd hh:mm:ss [Level] msg` as `[Headless][%s] %s` (stdout/console); `[Python] Running on Headless Mode`, `Initialize Headless Mode ...`, `Exit Headless mode.` come from the headless init at 0x62b2c80. In GUI mode the `[Python]` messages go to the default Qt sink (debugger/stderr), invisible in a normal CLO session (inference; no handler install site was looked for).
5. **CLO writes its own plug-in lifecycle log**: `C:\Users\Public\Documents\CLO\CLO Assets\api_plugin_log.txt` (format string `dd.MM.yyyy, hh:mm:ss`; the file shows the text `dd.MM.yyyy` literally because the pattern is mis-cased inside CLO, so only the time is meaningful). It is the best CLO-side marker for "DoFunction started / returned".

## 1. Code-region span (the Marvelous::*API implementation)

From `raw/exe_vtables.json` (7 classes, 1148 distinct slot targets):

| Item | RVA |
|---|---|
| lowest vtable-referenced function | 0x5f8c9d0 (tiny Export/Fabric/Gui/Import/Pattern/Rest/Utility slot-0 stubs at 0x5f8c9d0-0x5f8cb50) |
| main cluster upper end | 0x60fd570 (`UtilityAPI` slot 13, contains `__pybind11_module_local_v4_msvc__`) |
| main cluster size | 0x60fd570 - 0x5f8c9d0 = 0x170ba0 = **1,510,304 bytes (~1.44 MiB), 1111 of 1148 slot targets** |
| outliers | 0x60f0010/0x60f0020 (RestAPI trivial stubs), 0x60fc9c0, then 0x648f0e5 ... 0x64941d3 (scalar-deleting-destructor thunks, 6-byte spacing, and Rest/Pattern dtor area) |
| overall span incl. outliers | 0x5f8c9d0 .. 0x64941d3 |

Python-proxy layer (`"[Python] <Name>"` strings at 0x8969f50-0x899fxxx): code sites between **0x5db840b and about 0x5f8a820**, just below the wrapper cluster. `[Python]` strings outside the API tables: auth/login (0x8266ab0-0x8267830, code near 0x1bdf000-0x1bed000), OpenGL/GLEW init (0x8919138, code 0x5228d4f), headless init (0x8a372b8-0x8a37350).

Method and limits: function bodies were bounded heuristically (end at the first `int3` after `ret`/`jmp`, or the next known slot target); strings are found only via RIP-relative `lea`. Inline-xmm string copies and strings reached only through callee helpers (e.g. the shared validation helper 0x60fb5d0 called by every `Set*MapImageGivenFilePath`, and 0x60fbe90 for the colour helper) are not attributed, so the per-function tables below are lower bounds. 471 of 1148 wrapper bodies reference at least one string.

## 2. Channel overview

| # | Channel | Producer | Sink | Visible to a plugin developer? |
|---|---|---|---|---|
| A | FUNCSIG analytics event (`feature` = `__FUNCSIG__`, `group` from the level index) | `Marvelous::*API::<fn>` wrappers via `Logger::Log` (0x4e10fb0 -> 0x390e2c0 -> 0x4e1cb80) | `...\CLO Standalone OnlineAuth\<n>\log\log_<k>.json` (maybe also uploaded; inference) | Only by reading that file. Gated by `[logger+0x28]` (enabled flag). |
| B | `[Python] <FnName> ` (trailing space) | Python-binding proxies (not the vtable wrappers) | Qt message handler (`QMessageLogger::info`) | Only for calls that came through Python; headless prints `[Headless][Info] ...` |
| C | `[Python]` + translated text (`Please Load Avatar`, `GetAvatarMeasurements: avatar index N is out of range (avatar count: M)`, `No Avatars found.`) | inside the vtable wrappers, `qInfo()` | Qt message handler | Normally invisible in GUI mode |
| D | JSON `{"status","message",...}` return values | 9 new-in-336 Fabric/Pattern functions | return value (std::string) | **Yes, parse it** |
| E | Modal dialogs | `DisplayMessageBox`, GuiAPI `Ask*`, license / login dialogs | GUI | Blocks unattended runs |
| F | `api_plugin_log.txt` | CLOPlugInManager (strings near 0x83b2298) | file | **Yes** |
| G | Headless Qt handler `[Headless][Level] ...` | 0x62b3ee0 | stdout | Only if launched with `-headless <file>` |


## 3. The `[Python] <Name> ` proxy traces (channel B)

Each API function has a trace string `"[Python] <Name> "` (and a `W` variant for wide-string overloads). Distinct names per class (from `raw/python_proxy_map.json`): Export 92, Fabric 135, Gui 39, Import 39, Pattern 217, Rest 7, Utility 366 (these equal the header function-name counts of `findings/14` except for 1 Rest function without a proxy, `GetByteArrayFromStream`). The proxy at e.g. 0x5f06130 does:

```
QMessageLogger(file,line,func).info() << "[Python] ExportGLTF "     // Qt6Core IAT: QMessageLogger ctor / info / QDebug::operator<<(const char*)
APICommand::getInstance().GetExportAPI()->vtbl[N](this, args...)    // IAT CLOAPIInterface.dll ?GetExportAPI@APICommand@CLOAPI@@
```
This is the `CLOAPI::APICommand` that the SDK DLL exposes to plugins, so Python scripts and the REST plugin end up in the same `Marvelous::*API` implementation; Python merely adds the `[Python] Name` trace first. Decoded slot examples: `ExportGLB` -> Export slot 78 (matches `abi_check`), `NewProject` -> Utility slot 55, `ExportZPac` -> Export slot 2.

Other `[Python]`-prefixed strings that are not API-name traces:

| String | RVA | Code | Meaning / trigger | Plugin developer action |
|---|---|---|---|---|
| `[Python] RequestHeadlessLogin error : ` / `[Python] RequestHeadlessLogin is failed.` / `[Python] Http connection failed.` / `[Python] Accees key verified.` (sic) / `[Python] Create Success accessKey : %1 , secretKey : %2` | 0x8266ab0, 0x8267800, 0x8266c50, 0x8267830, 0x82675d8 | 0x1bdf42d-0x1be520a | Headless API-key login flow (`-headless*` options, see `18_cli_options.md`). Not reachable from a running plugin. | None. Never log or store the access/secret key shown by `Create Success`. |
| `[Python] %1` | 0x8267618 | 0x1be4d60 | generic translated message in the same flow | none |
| `[Python] Failed to initalize GLEW` / `OpenGL version is lower than 1.3 (found none / 1.1 / 1.2)` | 0x8919138-0x89191d8 | 0x5228d4f-0x5228e39 | OpenGL context init failed (driver / remote desktop / no GPU) | On servers/RDP sessions, calls that render (thumbnails, snapshots) will fail; use a GPU session. |
| `[Python] Running on Headless Mode`, `[Python] Initialize Headless Mode ... `, `[Python] Exit Headless mode.` | 0x8a372b8, 0x8a37328, 0x8a37350 | 0x62b2cf5, 0x62b2ff5, 0x62b30ce | headless startup/shutdown | Seeing these means CLO was started with `-headless <file>`, which also enables `ImportMeasurement` (lane D). |
| `[Python] ` (bare prefix + space) | 0x83ddc10 | 0x602642e (`ImportPose`), 0x6026bbf (`ImportPoseW`), also 0x3153582, 0x38d000f, 0x7735af2... | prefix for `No Avatars found.` | Import an avatar before `ImportPose`. |
| `[Python]` (bare, no space) | 0x8862210 | 0x5fd43c7 and the avatar getters/setters (section 4.1), also 0x3f390ba, 0x3fad96e | prefix for translated text (channel C) | see 4.1 |
| `[Python] The input is an empty string. ` | 0x882fe70 | no `lea` xref found (inline/table reference) | an API got an empty path/string | Validate non-empty arguments before calling. |
| `[Python] Failed to change the back color. Please check if SetUseSameMaterialAsFront() is set to True.` and the `side color` twin | 0x8985730, 0x89857a0 | 0x60fbf87, 0x60fc003 (helper 0x60fbe90-0x60fc195, direct callers seen: `SetUseSameColorAsFront`) | colour set on Back/Side while 'use same as front' is on | Disable 'use same material as front' first (the Mirra plugin sets Front only). |
| `[Python] GetAvatarMeasurements: avatar index ` ... ` is out of range (avatar count:` | 0x89aeeb8, 0x89aeee8 | 0x5fd4180 (Utility slot 401) | index >= avatar count | Use a 0-based index < `GetAvatarCount()`. |


## 4. Messages by API function (channels C and D, from the wrapper bodies)

Rows list strings referenced from each wrapper body (heuristic bounds, section 1). 'Function' is the SDK header name derived from the vtable slot (`scripts/abi_check.py` slot model). 'Kind': **J** = function returns JSON (text is returned to the caller), **Q** = Qt-logged `[Python]`/message text, **D** = UI label / undo-step / option text, **-** = literal or key only.

### 4.1 Avatar functions printing `[Python] Please Load Avatar` (Utility)

| Function (slot, RVA) | Message(s) | Meaning / trigger | What a plugin should do |
|---|---|---|---|
| `Utility.GetAvatarMeasurements` (401, 0x5fd4180) | `[Python] Please Load Avatar`; also `[Python] GetAvatarMeasurements: avatar index`; `is out of range (avatar count:` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.GetAvatarOpacityMaps` (295, 0x5fd52d0) | `[Python] Please Load Avatar` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.GetAvatarProperties` (350, 0x5fd59f0) | `[Python] Please Load Avatar` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.GetAvatarSoftBodyStiffness` (352, 0x5fd6540) | `[Python] Please Load Avatar` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.GetAvatarSubdivisionLevel` (348, 0x5fd69a0) | `[Python] Please Load Avatar` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.GetAvatarTexureMap` (303, 0x5fd6de0) | `[Python] Please Load Avatar` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarActivation` (306, 0x603dff0) | `[Python] Please Load Avatar`; also `Activate Avatar`; `Deactivate Avatar` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarMeshTexture` (109, 0x603f770) | `[Python] Please Load Avatar`; also `Coudln't find Avatar Part you want`; `Please Check Texture Path, Texture couldn't load`; `Avatar don't have part what you want change texture` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarOpacityMap` (294, 0x6040200) | `[Python] Please Load Avatar`; also `Please Check file Path, file couldn't load` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarOpacityMapByIndex` (293, 0x6040bc0) | `[Python] Please Load Avatar`; also `Coudln't find Avatar Part you want`; `Avatar don't have part what you want change texture`; `Please Check Texture Path, Texture couldn't load` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarProperties` (349, 0x6041900) | `[Python] Please Load Avatar`; also `invalid stof argument`; `stof argument out of range` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarSmooth` (347, 0x60420c0) | `[Python] Please Load Avatar`; also `Subdivision is not available when Soft Body Simulation is checked.` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarSoftBodyStiffness` (351, 0x6042680) | `[Python] Please Load Avatar`; also `Soft Body Simulation is not available when Divide Mesh is checked.` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |
| `Utility.SetAvatarTexureMap` (302, 0x6042c40) | `[Python] Please Load Avatar`; also `Please Check file Path, file couldn't load` | AvatarManager list is empty (`vector::empty` test, then `qInfo() << "[Python]" << tr(...)`); the call is a no-op / returns empty. | Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error. |

`Please Load Avatar` is test-and-return (`AvatarManager::Instance()->GetAvatarList()` empty -> message -> return; `0x1bf1390` is the `empty()` test). Get* return empty containers and Set* do nothing. Only `GetAvatarMeasurements` prints a separate out-of-range message.

### 4.2 All other wrapper messages

| Function (slot, RVA) | Kind | Message(s) | Meaning / likely trigger | Plugin developer action |
|---|---|---|---|---|
| `Fabric.AddTextureToPatterns` (284, 0x5f96610) | J | `Invalid style chip index: `; `. Use -1 for all applicable style chips or >= 0 for a specific style chip`; `Fabric not found for colorway `; ` and fabric index `; `Invalid material side value. Use Front, Back, or Side`; `Failed to load texture as base color for colorway ` (+14 more) | Step-by-step status text of the JSON-returning Fabric texture/AOP APIs (new in 336). Returned inside the result JSON (`status` success/failed, `message`), not logged. | Parse the returned JSON; use `-1` for 'all colorways/style chips' only when 'Show all Colorways' is ON; read `message` for the failing step. |
| `Pattern.AttachPatternToAvatarMeasure` (195, 0x5f9c1c0) | J | `Cloth controller is not available`; `Invalid pattern index: `; `Invalid line index: `; ` for pattern `; `No avatar measures exist in the scene. Load an avatar with measures or import measurements`; `Avatar measure not found: ` (+3 more) | The relevant editor/controller object is absent (no document, or panel never created). | Make sure a project is open (NewProject/ImportFile) and the 2D pattern/UV view has been initialised; retry after a short wait. |
| `Utility.ConvertTrimsToButtons` (314, 0x5fa8070) | D | `Convert Trim to Button` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Utility.CreateButtonholesForButtonHeads` (315, 0x5fa99e0) | D | `Create Buttonholes` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.ExportObjectBrowserMaterialsList` (132, 0x5fbd7b0) | - | `finalData = %s\n` | Literal used by the function (key name or format); no error semantics seen. | None. |
| `Utility.GenerateZippersFromObj` (389, 0x5fce5e0) | - | `Custom Slider_`; `Custom Puller_`; `Custom Slider & Puller_`; `Custom Teeth_`; `Custom Stopper_Top_`; `Custom Stopper_Bottom_Open_` (+1 more) | Literal used by the function (key name or format); no error semantics seen. | None. |
| `Utility.GetAvatarMeasurements` (401, 0x5fd4180) | Q | `[Python] GetAvatarMeasurements: avatar index`; `is out of range (avatar count:` | `GetAvatarMeasurements` avatar index >= avatar count. | Use `GetAvatarCount()` and a 0-based index. |
| `Utility.GetButtonPairInfoAsJson` (318, 0x5fdb4e0) | - | `NO_EDITOR` | The relevant editor/controller object is absent (no document, or panel never created). | Make sure a project is open (NewProject/ImportFile) and the 2D pattern/UV view has been initialised; retry after a short wait. |
| `Pattern.GetHiResTolerance` (222, 0x5ff1900) | D | `CLO Virtual Fashion` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.GetPatternComponents` (184, 0x6000880) | J | `Pattern editor is not available`; `Invalid pattern index: `; `Unknown component type '`; `'. Supported: "button", "buttonhole", "graphic", "print", "zipper", "trim"` | The relevant editor/controller object is absent (no document, or panel never created). | Make sure a project is open (NewProject/ImportFile) and the 2D pattern/UV view has been initialised; retry after a short wait. |
| `Pattern.GetPatternGroupsBySeamlineConnectivity` (185, 0x6002800) | J | `Pattern editor is not available` | The relevant editor/controller object is absent (no document, or panel never created). | Make sure a project is open (NewProject/ImportFile) and the 2D pattern/UV view has been initialised; retry after a short wait. |
| `Pattern.GetPatternLineInfo` (194, 0x6006540) | J | `Invalid pattern index: ` | Argument validation inside a JSON-returning Pattern API. | Bounds-check against `GetPatternCount()` / pattern point count first; read the JSON `status`/`message` of the return value. |
| `Pattern.GetPatternSize` (0, 0x6009ea0) | Q | `This api call is deprecated. Please use 'GetPatternCount()' function` | `GetPatternSize` is deprecated. | Use `GetPatternCount()`. |
| `Utility.GetPatternSnapShotSizeOption` (356, 0x600ac00) | D | `Wide Format (24 inches)`; `Wide Format (36 inches)`; `Wide Format (44 inches)` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.GetPatternUVSpace` (189, 0x600ba60) | J | `No UV dummies found for pattern `; `Invalid pattern index: ` | UV-space operation found nothing to move. | Make sure the patterns are UV-mapped / contain the requested component type. |
| `Import.ImportPose` (40, 0x60261e0) | Q | `No Avatars found.` | `ImportPose` needs a loaded avatar. | Import an avatar first. |
| `Import.ImportPoseW` (42, 0x6026980) | Q | `No Avatars found.` | `ImportPose` needs a loaded avatar. | Import an avatar first. |
| `Utility.LoadLibraryColorSwatchList` (42, 0x602f770) | - | `Added from API` | Literal used by the function (key name or format); no error semantics seen. | None. |
| `Pattern.MoveNonFabricObjectsToUVSpace` (192, 0x602fb30) | J | `Invalid scale: must be > 0`; `Unknown component type '`; `'. Supported: "button", "zipper", "trim"`; `Invalid pattern index`; `No non-fabric object UV islands found for the given patterns`; `UV editor is not available` (+2 more) | Argument validation inside a JSON-returning Pattern API. | Bounds-check against `GetPatternCount()` / pattern point count first; read the JSON `status`/`message` of the return value. |
| `Pattern.MovePatternPoint` (178, 0x6031f90) | - | `invaild point index`; `invaild pattern index` | Argument validation inside a JSON-returning Pattern API. | Bounds-check against `GetPatternCount()` / pattern point count first; read the JSON `status`/`message` of the return value. |
| `Pattern.MovePatternsToUVSpace` (191, 0x60324f0) | J | `Invalid scale: must be > 0`; `No UV dummies for pattern`; `Invalid pattern index`; `No valid patterns with UV dummies to move`; `UV editor is not available`; `Invalid UV tile (` (+1 more) | Argument validation inside a JSON-returning Pattern API. | Bounds-check against `GetPatternCount()` / pattern point count first; read the JSON `status`/`message` of the return value. |
| `Utility.SetAvatarActivation` (306, 0x603dff0) | D | `Activate Avatar`; `Deactivate Avatar` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Utility.SetAvatarMeshTexture` (109, 0x603f770) | Q | `Coudln't find Avatar Part you want`; `Please Check Texture Path, Texture couldn't load`; `Avatar don't have part what you want change texture` | Avatar part name not found, or the texture/opacity file could not be loaded. | Verify the part name and the file path (absolute, readable, supported image type). |
| `Utility.SetAvatarOpacityMap` (294, 0x6040200) | Q | `Please Check file Path, file couldn't load` | Avatar part name not found, or the texture/opacity file could not be loaded. | Verify the part name and the file path (absolute, readable, supported image type). |
| `Utility.SetAvatarOpacityMapByIndex` (293, 0x6040bc0) | Q | `Coudln't find Avatar Part you want`; `Avatar don't have part what you want change texture`; `Please Check Texture Path, Texture couldn't load` | Avatar part name not found, or the texture/opacity file could not be loaded. | Verify the part name and the file path (absolute, readable, supported image type). |
| `Utility.SetAvatarProperties` (349, 0x6041900) | Q | `invalid stof argument`; `stof argument out of range` | `std::stof` on a property value string threw (no handler seen at wrapper level). | Only pass numeric strings in `SetAvatarProperties` / `SetTrimMaterialProperties`; a non-numeric value may terminate CLO (lane D inference). |
| `Utility.SetAvatarSmooth` (347, 0x60420c0) | Q | `Subdivision is not available when Soft Body Simulation is checked.` | Mutually exclusive avatar options (DivideMesh vs SoftBodySimulation). | Do not enable both; disable one before enabling the other. |
| `Utility.SetAvatarSoftBodyStiffness` (351, 0x6042680) | Q | `Soft Body Simulation is not available when Divide Mesh is checked.` | Mutually exclusive avatar options (DivideMesh vs SoftBodySimulation). | Do not enable both; disable one before enabling the other. |
| `Utility.SetAvatarTexureMap` (302, 0x6042c40) | Q | `Please Check file Path, file couldn't load` | Avatar part name not found, or the texture/opacity file could not be loaded. | Verify the part name and the file path (absolute, readable, supported image type). |
| `Fabric.SetBaseTextureMapImageGivenFilePath` (211, 0x6044000) | Q | `Invalid Inputs. Fabric Index :`; `, Colorway Index :`; `, Style Chip Index :`; `, Material Face :` | Index tuple (fabric, colorway, style chip, material face) out of range; printed, then the texture set is aborted (setter returns void). | Query fabric/colorway/style-chip counts; check the material-face value is valid (front/back/side). |
| `Fabric.SetDisplacementMapImageGivenFilePath` (219, 0x6048f40) | Q | `Invalid Inputs. Fabric Index :`; `, Colorway Index :`; `, Style Chip Index :`; `, Material Face :` | Index tuple (fabric, colorway, style chip, material face) out of range; printed, then the texture set is aborted (setter returns void). | Query fabric/colorway/style-chip counts; check the material-face value is valid (front/back/side). |
| `Utility.SetEnvironmentDisplayProperties` (300, 0x604ad80) | D | `CLO Virtual Fashion`; `Graphic Option` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.SetHiResTolerance` (223, 0x6055890) | D | `CLO Virtual Fashion` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Fabric.SetMetalnessMapImageGivenFilePath` (231, 0x6058260) | Q | `Invalid Inputs. Fabric Index :`; `, Colorway Index :`; `, Style Chip Index :`; `, Material Face :` | Index tuple (fabric, colorway, style chip, material face) out of range; printed, then the texture set is aborted (setter returns void). | Query fabric/colorway/style-chip counts; check the material-face value is valid (front/back/side). |
| `Utility.SetNormalBlendingMethod` (365, 0x605b100) | D | `CLO Virtual Fashion`; `Graphic Option` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Fabric.SetNormalMapImageGivenFilePath` (215, 0x605b3a0) | Q | `Invalid Inputs. Fabric Index :`; `, Colorway Index :`; `, Style Chip Index :`; `, Material Face :` | Index tuple (fabric, colorway, style chip, material face) out of range; printed, then the texture set is aborted (setter returns void). | Query fabric/colorway/style-chip counts; check the material-face value is valid (front/back/side). |
| `Fabric.SetOpacityMapImageGivenFilePath` (223, 0x605de50) | Q | `Invalid Inputs. Fabric Index :`; `, Colorway Index :`; `, Style Chip Index :`; `, Material Face :` | Index tuple (fabric, colorway, style chip, material face) out of range; printed, then the texture set is aborted (setter returns void). | Query fabric/colorway/style-chip counts; check the material-face value is valid (front/back/side). |
| `Pattern.SetPatternPieceSametapingWidth` (91, 0x6065e90) | D | `Seam Taping Width` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.SetPatternPieceSeamtaping` (90, 0x60661e0) | D | `Seam Taping` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.SetPatternPieceShirringExtend` (89, 0x6066870) | D | `Shirring Extend` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.SetPatternPieceShirringHeight` (88, 0x6066bc0) | D | `Shirring Interval` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Pattern.SetPatternPieceShirringInterval` (87, 0x6066f00) | D | `Shirring Interval` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Utility.SetPatternSnapShotSizeOption` (355, 0x6068490) | D | `Wide Format (24 inches)`; `Wide Format (36 inches)`; `Wide Format (44 inches)` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Utility.SetRenderImageVideoProperties` (209, 0x6069a40) | - | `Render/Background Image/` | Literal used by the function (key name or format); no error semantics seen. | None. |
| `Fabric.SetRoughnessMapImageGivenFilePath` (227, 0x606a2b0) | Q | `Invalid Inputs. Fabric Index :`; `, Colorway Index :`; `, Style Chip Index :`; `, Material Face :` | Index tuple (fabric, colorway, style chip, material face) out of range; printed, then the texture set is aborted (setter returns void). | Query fabric/colorway/style-chip counts; check the material-face value is valid (front/back/side). |
| `Utility.SetTrimMaterialProperties` (363, 0x6076e20) | Q | `[API] SetTrimMaterialProperties: unknown MaterialType name '`; `stof argument out of range`; `invalid stof argument` | Trim material type name not recognised. | Use a MaterialType name accepted by CLO (see header doc). |
| `Utility.SetViewControlDefaults` (297, 0x6079ac0) | D | `CLO Virtual Fashion` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Utility.SetZipperStyleTapeThickness` (345, 0x607d460) | D | `Thickness (mm)` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Utility.SetZipperStyleWeight` (343, 0x607e1c0) | D | `weight (g)` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Fabric.TransformAOPOnFabric` (283, 0x607fdd0) | J | `Invalid colorway index: `; `. Use -1 to target all colorways, or 0 to `; ` for a specific colorway`; `. Valid range is 0 to `; `Fabric not found for colorway index `; ` and fabric index ` (+24 more) | Step-by-step status text of the JSON-returning Fabric texture/AOP APIs (new in 336). Returned inside the result JSON (`status` success/failed, `message`), not logged. | Parse the returned JSON; use `-1` for 'all colorways/style chips' only when 'Show all Colorways' is ON; read `message` for the failing step. |
| `Utility.UnfastenAllButtons` (317, 0x60840e0) | D | `Unfasten Buttons` | UI label / undo-step name / option text used by the function, not an error. | None. |
| `Utility.ValidateCLOFile` (62, 0x60859c0) | - | `Invalid Hash`; `Invalid Signature` | File-validation result strings inside a JSON `{isValid,fileType,error}` reply. | Re-export the file from CLO; do not edit .zprj/.zpac you intend to validate. |
| `Utility.ValidateCLOFileW` (63, 0x6086300) | - | `Invalid Hash`; `Invalid Signature` | File-validation result strings inside a JSON `{isValid,fileType,error}` reply. | Re-export the file from CLO; do not edit .zprj/.zpac you intend to validate. |

### 4.3 JSON-returning functions (new in 336): read `status` / `message`

These return a `std::string` holding JSON built with nlohmann::json (keys `status`, `message`, plus `results`, `groups`, `boundingBox`, `lines`, `uvSpace`, `fitScale`, ...; values `"success"` / `"failed"`):
`Fabric::AddTextureToPatterns` (0x5f96610), `Fabric::TransformAOPOnFabric` (0x607fdd0), `Pattern::AttachPatternToAvatarMeasure` (0x5f9c1c0), `Pattern::GetPatternComponents` (0x6000880), `Pattern::GetPatternGroupsBySeamlineConnectivity` (0x6002800), `Pattern::GetPatternLineInfo` (0x6006540), `Pattern::GetPatternUVSpace` (0x600ba60), `Pattern::MovePatternsToUVSpace` (0x60324f0), `Pattern::MoveNonFabricObjectsToUVSpace` (0x602fb30).
Plugin implication: nothing is logged for their failures; the REST layer must forward the returned string. The Mirra plugin currently uses none of them (`findings/09`).

### 4.4 Other fixed strings worth knowing

| String | RVA | Where | Note |
|---|---|---|---|
| `Invalid Inputs. Fabric Index :` + `, Colorway Index :` + `, Style Chip Index :` + `, Material Face :` | 0x8984028.. | `Set*MapImageGivenFilePath` / `SetCustomImage*` (Fabric slots 76, 211, 215, 219, 223, 227, 231 ...) | printed, not returned; these setters return void so the plugin cannot see it |
| `cannot apply to Substance material` | 0x8984048 | same setters | Substance fabrics reject image-map replacement |
| `NO_EDITOR`, `NO_PAIRS_AVAILABLE`, `ALREADY_FASTENED`, `TOO_FAR`, `MISALIGNED`, `PAIRS_NOT_FASTENABLE`, `NO_BUTTONS_OR_HOLES`, `BUTTONS_ONLY`, `HOLES_ONLY` | 0x899a490, 0x89afad8-0x89afc08 | `GetButtonPairInfoAsJson` (318), `GetButtonHoleStyleColor` (269) | reason codes inside a JSON result |
| `[API] SetTrimMaterialProperties: unknown MaterialType name '` | 0x89af180 | Utility slot 363 | the only `[API]`-prefixed message found |
| `Soft Body Simulation is not available when Divide Mesh is checked.` / `Subdivision is not available when Soft Body Simulation is checked.` | 0x89aecd0 / 0x89ae6c0 | `SetAvatarSoftBodyStiffness` / `SetAvatarSmooth` | mutually exclusive options |
| `Invalid Hash` / `Invalid Signature` | 0x89a5098.. | `ValidateCLOFile(W)`, `UsePlugInFromList` | JSON `{isValid,fileType,error}` |
| fixed GUIDs `476a626b-...`, `21adf277-...` | 0x8972228, 0x8291180 | `ExportMVSData`, Utility slot 216 | constants; not investigated |
| `output.glb` / `.gltf` / `.zprj` / `.json` / `.png` ... | 0x8970470, 0x8984e88, 0x896e088 ... | Export functions | default file names used when the caller gives an empty path (inference) |

## 5. Where CLO writes logs on this machine (read-only survey)

Machine: Windows 11, user `Saumy`, CLO Standalone OnlineAuth 2026.1.336, instance directory `892`.

| Location | What | Written by | Notes |
|---|---|---|---|
| `C:\Users\Public\Documents\CLO\CLO Assets\api_plugin_log.txt` | plug-in lifecycle trace (900 bytes, overwritten per click) | CLOPlugInManager (strings 0x83b2298 `dd.MM.yyyy, hh:mm:ss`, 0x83b22b0) | Lines: *User clicked to run a plug-in action* / *## Action title : REST Server & Execute* / *## Plug-in file path : C:/Program Files/CLO Standalone OnlineAuth/plugins/RestPlugin_v1.3.2.dll* / *loaded into the plug-in manager successfully* / *Trying to find DoFunction* / *Succeeded* / *Trying to run the DoFunction* / *Succeeded*. Date prints as literal `dd.MM.yyyy`; time is local (UTC+05:30). The final *Succeeded* is stamped when `DoFunction` returns (15:08:12 -> 15:08:14: the plugin starts its server/timer and returns). Only the last click is kept. |
| `%LOCALAPPDATA%\CLO Virtual Fashion\CLO Standalone OnlineAuth\892\log\log_0.json` | channel A events, one JSON object per line: `time` (ns since Unix epoch; 1793266681628632800 = 2026-10-29 09:38:01 UTC = 15:08:01 local), `category` (`Feature` or `API`), `subcategory` (`CLO API`), `group` (`UtilityAPI`...), `feature` (`Login`, `App Inactive`, or the `__FUNCSIG__`), `additional_json` | `Logger::Log` -> 0x390e2c0 | 501 bytes, 3 events (Login, DisplayMessageBox, App Inactive), mtime 15:37:59 although the REST plugin ran many calls after 15:08 (open question O1) |
| `%LOCALAPPDATA%\CLO Virtual Fashion\CLO Standalone OnlineAuth\892\logs\` | auth/network log | CLO login module | **Not read** (auth). Existence only. |
| `...\892\1000 ... 1020\` | unpacked default library assets (fabrics, trims, HDR, webp) | first-run cache | not logs |
| `%LOCALAPPDATA%\CLO Virtual Fashion\Patches\` | updater patches | updater | empty |
| `%APPDATA%\CLO Virtual Fashion\CLO Standalone OnlineAuth\QtWebEngine\*Profile` | QtWebEngine profiles (login/closet/connect/AI web views) | Chromium | |
| `C:\Users\Public\Documents\CLO\Configuration\Autosaves`, `...\python311`, `...\python311.zip` | autosaves; embedded Python 3.11 runtime | CLO | autosave timestamps help after a crash |
| `C:\Users\Public\Documents\CLO\Plugins\pluginSettings.json` | plug-in registry (`m_PlugInFileName` = `C:/Program Files/CLO Standalone OnlineAuth/plugins/RestPlugin_v1.3.2.dll`, title `REST Server & Execute`, version 2); rewritten at each CLO start | CLOPlugInManager | CLO loads the DLL from its own `plugins` folder, not from the repo; verify the deployed DLL matches the latest build |
| `C:\Users\Public\Documents\CLO\Configuration\API_Plug_in\{readme,defaultPlugInFolders}.txt` | legacy plug-in folder list (placeholder paths) | CLO | |
| `C:\Program Files\CLO Standalone OnlineAuth\` | no `.log` files; crash reporter plug-ins present (`carb.crashreporter-breakpad.plugin.dll`) | | no dump files found under the user profile |

Other log-like names inside the exe (not observed on disk): `authentication.log`, `languagetable.log`, `mvfile.log`, `/cadlink_validate.log` (0x82650f0, 0x88308e0, 0x88393c0, 0x88b2158) and the headless options `-headlesslog` / `-performlog` (see `18_cli_options.md`).

### 5.1 Plugin-side logs (read-only): `C:\D-drive-data\mirra-mvp\clo_workspace\logs\`

* `plugin_crash_trace.log` (~37 MB, ~291k lines), written by `RestPlugin_windows.cpp` (`MIRRA_PLUGIN_LOG_DIR/plugin_crash_trace.log`). Format `[HH:MM:SS] [tid=N] <text>`, **local time, no date**. Markers: `DoFunction: g_cloMainWnd discovered hwnd=...` (new CLO process), `StartRESTServer:` / `EnsureServerStarted:` / `EnsureWndProcSubclass:`, `QueueDrainTimer tick=N draining queue` / `drain call returned`, `BEGIN <cmd> ...` / `END   <cmd> success=...`, `DoFunction: ProcessCommandQueue() returned normally (no crash)`, `WARNING: host CLO version differs from the SDK this plugin was built against; ...`.
* `build_plugin_windows_<UTC stamp>.log`: build logs; file names are **UTC**, the trace is local (offset +5:30 here).

### 5.2 Correlation recipe

1. **Align clocks.** Trace: local time, date from file mtime / build-log stamp. `api_plugin_log.txt`: local time, broken date. `log_*.json`: epoch ns (`datetime.fromtimestamp(t/1e9)` gives local time). `tid` is CLO's DoFunction/UI thread id and changes with every CLO process.
2. **Find the CLO process boundary.** A new `tid` plus a fresh `DoFunction: g_cloMainWnd discovered hwnd=` line = CLO (re)started (10 such lines in the current trace). `api_plugin_log.txt` has the same minute as the latest one but holds only the last click.
3. **Detect a crash mid-command.** A `BEGIN <cmd>` with no `END` before the next `BEGIN` or a new `tid` means CLO died (or was killed) inside that command. The existing trace shows 9 such cases: 3x `clear-avatars` (line 44724 at 21:23:01, 45250, 45294) and 6x `import-avatar-avt` (lines 278065, 278082, 278127, 278178, 281024, 287602); the 278xxx cluster (15:44-16:18) sits next to the `WARNING: host CLO version differs...` lines at 278158/278180, which fits lane D's SDK-mismatch/ImportAvatar-by-value crash mechanism.
4. **Map a plugin command to a CLO event.** `export` -> `ExportAPI::ExportGLTF/GLB`, `import-avatar-avt` -> `ImportAPI::ImportAvatar`, `set-fabric-*` -> `FabricAPI::...` in `log_N.json`; match on time within a second. Because of O1 this works only when the JSON file is flushed.
5. **A silent false/0/empty** is the norm (lane D): read the trace line before the failing `END` for the arguments (path, index) and compare with the rules in section 4.
6. **Console messages** (`[Python]...`, `[Headless][Info] ...`) appear only when CLO is started from a terminal / with `-headless`; for GUI runs use a debugger output viewer (OutputDebugString) to see channels B/C.

### 5.3 Open questions (need a live run; not inferred)

* **O1:** why `log_0.json` holds only the `DisplayMessageBox` API event although `import-avatar-avt` etc. ran later. `Logger::Log` has no level filter in the code seen (only `[logger+0x28]` and the group-map lookup). Hypotheses: buffered/flushed later, only some groups kept, file rewritten per N events. Test: call `GetAvatarCount` then re-read the file.
* **O2:** whether channel A events are uploaded (telemetry). The shape and the `Login` / `App Inactive` features suggest usage analytics; unverified, nothing here touched the network.
* **O3:** whether the enabled flag `[logger+0x28]` follows a preference (`Preference` / `CLO API` strings at 0x83b6888, 0x8555a9f).

## 6. Quick guide for plugin developers

* A `false` / `0` / empty return almost never comes with a message; check preconditions yourself (avatar loaded, document present, index in range, extension correct, `-headless` for `ImportMeasurement`).
* For the nine JSON-returning functions, log the returned string.
* Never pass non-numeric strings to `SetAvatarProperties` / `SetTrimMaterialProperties` (`std::stof` throws, no handler seen).
* `DisplayMessageBox`, `AskForm`, `AskConfirm` are modal with no headless check; avoid them in unattended flows (and note `DisplayMessageBox` is the one API event present in `log_0.json`).
* Use `plugin_crash_trace.log` BEGIN/END pairs plus the `WARNING: host CLO version differs` line to triage crashes before blaming an API.
