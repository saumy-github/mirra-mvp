"""write_17.py (lane J) - assembles findings/17_log_message_catalog.md from raw/*.json (+ hand-written commentary)."""
import json, os, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.join(HERE, "..", "raw"); OUT = os.path.join(HERE, "..", "findings", "17_log_message_catalog.md")
msg = json.load(open(os.path.join(R, "msg_by_function.json")))
px = json.load(open(os.path.join(R, "python_proxy_map.json")))
names = collections.defaultdict(set)
for e in px: names[e["api"]].add(e["name"])
JSONFN = {"Fabric.AddTextureToPatterns", "Fabric.TransformAOPOnFabric", "Pattern.AttachPatternToAvatarMeasure", "Pattern.GetPatternComponents",
          "Pattern.GetPatternGroupsBySeamlineConnectivity", "Pattern.GetPatternLineInfo", "Pattern.GetPatternUVSpace",
          "Pattern.MoveNonFabricObjectsToUVSpace", "Pattern.MovePatternsToUVSpace"}
RULES = [
 (r"Please Load Avatar", "AvatarManager list is empty (`vector::empty` test, then `qInfo() << \"[Python]\" << tr(...)`); the call is a no-op / returns empty.", "Call `ImportAvatar` (and check `GetAvatarCount() > 0`) before any avatar getter/setter; treat an empty result as 'no avatar', not as an error."),
 (r"Invalid pattern index|invaild pattern index|invaild point index|Invalid line index|Invalid UV tile|Invalid scale", "Argument validation inside a JSON-returning Pattern API.", "Bounds-check against `GetPatternCount()` / pattern point count first; read the JSON `status`/`message` of the return value."),
 (r"Pattern editor is not available|UV editor is not available|Cloth controller is not available|NO_EDITOR", "The relevant editor/controller object is absent (no document, or panel never created).", "Make sure a project is open (NewProject/ImportFile) and the 2D pattern/UV view has been initialised; retry after a short wait."),
 (r"No avatar measures exist|Avatar measure not found|does not support pattern attachment", "Attach-to-avatar-measure precondition failed.", "Load an avatar that carries measures, or call `ImportMeasurement`/`ImportAvatarMeasurement` first; height/linear measures cannot be attached."),
 (r"Invalid Inputs\. Fabric Index", "Index tuple (fabric, colorway, style chip, material face) out of range; printed, then the texture set is aborted (setter returns void).", "Query fabric/colorway/style-chip counts; check the material-face value is valid (front/back/side)."),
 (r"cannot apply to Substance material", "Texture-map setters refuse Substance (procedural) materials.", "Convert the fabric to a non-Substance material or skip texture-map calls for it."),
 (r"Failed to change the (back|side) color", "Colour change on the Back/Side face while 'use same material as front' is on.", "Disable 'use same material as front' before colouring Back/Side; the Mirra plugin sets Front only and is unaffected."),
 (r"invalid stof argument|stof argument out of range", "`std::stof` on a property value string threw (no handler seen at wrapper level).", "Only pass numeric strings in `SetAvatarProperties` / `SetTrimMaterialProperties`; a non-numeric value may terminate CLO (lane D inference)."),
 (r"Subdivision is not available|Soft Body Simulation is not available", "Mutually exclusive avatar options (DivideMesh vs SoftBodySimulation).", "Do not enable both; disable one before enabling the other."),
 (r"Coudln't find Avatar Part|Avatar don't have part|Texture couldn't load|file couldn't load", "Avatar part name not found, or the texture/opacity file could not be loaded.", "Verify the part name and the file path (absolute, readable, supported image type)."),
 (r"No Avatars found", "`ImportPose` needs a loaded avatar.", "Import an avatar first."),
 (r"This api call is deprecated", "`GetPatternSize` is deprecated.", "Use `GetPatternCount()`."),
 (r"Invalid style chip|Invalid colorway|Fabric not found|Invalid aopMode|Invalid material side|Failed to (load|create|apply)|Style chip not found|Material not found|PBR material not found|Print (fabric|material)|Texture not found|No style chips|ColorwayIndex is -1|Cannot apply AOP|skipped|applied", "Step-by-step status text of the JSON-returning Fabric texture/AOP APIs (new in 336). Returned inside the result JSON (`status` success/failed, `message`), not logged.", "Parse the returned JSON; use `-1` for 'all colorways/style chips' only when 'Show all Colorways' is ON; read `message` for the failing step."),
 (r"Unknown component type|Supported:", "Component-type filter string not in the accepted list.", "Use one of button, buttonhole, graphic, print, zipper, trim (UV move: button, zipper, trim)."),
 (r"No UV dummies|No valid patterns with UV|No non-fabric object", "UV-space operation found nothing to move.", "Make sure the patterns are UV-mapped / contain the requested component type."),
 (r"Invalid Hash|Invalid Signature", "File-validation result strings inside a JSON `{isValid,fileType,error}` reply.", "Re-export the file from CLO; do not edit .zprj/.zpac you intend to validate."),
 (r"unknown MaterialType name", "Trim material type name not recognised.", "Use a MaterialType name accepted by CLO (see header doc)."),
 (r"is out of range \(avatar count", "`GetAvatarMeasurements` avatar index >= avatar count.", "Use `GetAvatarCount()` and a 0-based index."),
]
def rule(m):
    for pat, mean, act in RULES:
        if re.search(pat, m): return mean, act
    return None
def esc(s): return s.replace("|", "\\|").replace("\n", "\\n")

L = []
w = L.append
w(r"""# Log / diagnostic message catalog (CLO 2026.1.336, static)

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
""")

w(r"""## 1. Code-region span (the Marvelous::*API implementation)

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

""")

w("## 3. The `[Python] <Name> ` proxy traces (channel B)\n")
w("Each API function has a trace string `\"[Python] <Name> \"` (and a `W` variant for wide-string overloads). Distinct names per class (from `raw/python_proxy_map.json`): " + ", ".join("%s %d" % (k, len(v)) for k, v in sorted(names.items())) + " (these equal the header function-name counts of `findings/14` except for 1 Rest function without a proxy, `GetByteArrayFromStream`). The proxy at e.g. 0x5f06130 does:\n")
w(r"""```
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

""")

w("## 4. Messages by API function (channels C and D, from the wrapper bodies)\n")
w("Rows list strings referenced from each wrapper body (heuristic bounds, section 1). 'Function' is the SDK header name derived from the vtable slot (`scripts/abi_check.py` slot model). 'Kind': **J** = function returns JSON (text is returned to the caller), **Q** = Qt-logged `[Python]`/message text, **D** = UI label / undo-step / option text, **-** = literal or key only.\n")
w("### 4.1 Avatar functions printing `[Python] Please Load Avatar` (Utility)\n")
w("| Function (slot, RVA) | Message(s) | Meaning / trigger | What a plugin should do |\n|---|---|---|---|")
for k, v in msg.items():
    if k.startswith("Utility.") and any("Load Avatar" in m for m in v["msgs"]):
        ms = [m for m in v["msgs"] if m != "Please Load Avatar"]
        mean, act = rule("Please Load Avatar")
        extra = ("; also " + "; ".join("`%s`" % esc(m[:70]) for m in ms)) if ms else ""
        w("| `%s` (%d, %s) | `[Python] Please Load Avatar`%s | %s | %s |" % (k, v["slot"], v["rva"], extra, mean, act))
w("")
w("`Please Load Avatar` is test-and-return (`AvatarManager::Instance()->GetAvatarList()` empty -> message -> return; `0x1bf1390` is the `empty()` test). Get* return empty containers and Set* do nothing. Only `GetAvatarMeasurements` prints a separate out-of-range message.\n")
w("### 4.2 All other wrapper messages\n")
w("| Function (slot, RVA) | Kind | Message(s) | Meaning / likely trigger | Plugin developer action |\n|---|---|---|---|---|")
UI = r"Graphic Option|CLO Virtual Fashion|Convert Trim|Create Buttonholes|Unfasten|Wide Format|Thickness|weight \(g\)|Seam Taping|Shirring|Activate Avatar"
for k, v in msg.items():
    ms = [m for m in v["msgs"] if m != "Please Load Avatar"]
    if not ms: continue
    joined = " ".join(ms)
    if k in JSONFN: kind = "J"
    elif re.search(UI, joined): kind = "D"
    elif re.search(r"Python|stof|Soft Body|Subdivision|Coudln|couldn|deprecated|Avatar|Invalid Inputs|Substance", joined): kind = "Q"
    else: kind = "-"
    shown = ms[:6]; more = len(ms) - len(shown)
    mtxt = "; ".join("`%s`" % esc(m[:90]) for m in shown) + (" (+%d more)" % more if more > 0 else "")
    mean = act = None
    for m in ms:
        r_ = rule(m)
        if r_: mean, act = r_; break
    if mean is None:
        if kind == "D": mean, act = "UI label / undo-step name / option text used by the function, not an error.", "None."
        else: mean, act = "Literal used by the function (key name or format); no error semantics seen.", "None."
    w("| `%s` (%d, %s) | %s | %s | %s | %s |" % (k, v["slot"], v["rva"], kind, mtxt, mean, act))
w("")
w(r"""### 4.3 JSON-returning functions (new in 336): read `status` / `message`

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
""")

w(r"""## 5. Where CLO writes logs on this machine (read-only survey)

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
""")
open(OUT, "w", encoding="utf-8").write("\n".join(L))
print("written", OUT, len("\n".join(L)))
