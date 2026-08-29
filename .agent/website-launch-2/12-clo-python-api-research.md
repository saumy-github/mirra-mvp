# CLO3D Python API Research

Source: developer.clo3d.com ("CLO API 0.1 documentation") — the same public developer portal referenced in the task. Pages fetched directly (curl, since the site's largest page, `list.html`, is ~2.2MB and gets truncated by summarizing fetchers): `python.html`, `list.html`, `optiontype.html`, `scenario.html`, `environment.html`, `changelog.html`. `support.clo3d.com/.../CLO-API-SDK-Guide` returned HTTP 403 and could not be read.

Legend: **[DOC]** = directly stated in the docs, quoted or closely paraphrased. **[INFER]** = my inference/interpretation, not stated outright. **[UNKNOWN]** = not found anywhere in the public docs I could reach.

---

## 1. The Python API itself

**[DOC]** The entirety of `python.html`'s substantive content is this (https://developer.clo3d.com/python.html):

> Python API
> This document describes how to use API via Python Script within CLO.
>
> **Access Python Editor**
> Main Menu → Edit → Python Script → Run Python Script
> (screenshots of "Python Script Editor" and "Log Console")
>
> **Drag and Drop**
> If python script is ready to be used, directly drag & drop the .py file into CLO

That is the complete page — no version-support table, no Python interpreter version, no third-party-package guidance, no threading notes.

- **CLO versions**: **[UNKNOWN]** which CLO version first shipped Python scripting. The changelog's oldest Python-tagged entry is v4.2.0 (June 2023, "Added ApiStubFiles within CLO.exe Folder (For Python API)" appears at v4.3.0 Nov 2023, and "Python API Editor Improvement" at v4.2.1 Aug 2023) — so Python scripting existed by mid-2023 at the latest, likely earlier. **[INFER]** Given the presence of stub files and an editor by 2023, the feature is not new; the doc site simply doesn't date its introduction.
- **Embedded vs external**: **[DOC]** It's embedded inside the CLO application — invoked from CLO's own Edit menu or by dragging a `.py` file into the running CLO window. There is no evidence of an external/standalone Python module that drives CLO out-of-process.
- **Headless/batch capability**: **[DOC]** The changelog repeatedly references a "headless mode" / "Headless Export API" as a real, distinct execution mode (see §4 below: "Headless ImportFile," "Headless Authentication Registry Path," "ExportAnimationVideo (Headless)," "Graphic Placement ExportType (Headless)," "Zpac was not loaded properly via ImportFile API in Headless Mode"). This means CLO (or its API surface) can run without full interactive UI — **[INFER]** this headless mode is likely usable by scripts run via API/plugin, potentially including Python, though the changelog entries don't specify whether "headless" here means the C++ SDK, Python, or both equally. The site gives no separate doc page describing what headless mode is, how to invoke it, or its constraints.
- **Invocation**: **[DOC]** Only two documented ways: menu action (Edit → Python Script → Run Python Script) and drag-and-drop of a `.py` file onto the CLO window. **[UNKNOWN]** Whether a script can be invoked via CLI flag, watched folder, or REST call. The changelog (v8.0.3, Aug 2025) does add "Add Python Script as Plugin — Allows Python scripts to be loaded as plugins, similar to C++ DLLs," and v10.0.0 (May 2026) adds "Python Plugin Auto-Load on Startup." **[INFER]** This means a Python script can now be registered as a plugin and auto-loaded when CLO starts — a materially different invocation model from the original menu/drag-drop, closer to how the current C++ plugin is loaded. This could be a path to replacing the C++ DLL with a Python plugin that auto-loads and hosts a REST-like control surface, but no doc describes how a Python "plugin" receives events or exposes callbacks (e.g. whether it can run its own HTTP listener).
- **Main thread / blocking UI**: **[UNKNOWN]** Nothing in the docs states whether Python scripts run on CLO's main/UI thread or a worker thread, nor whether a long-running Python call blocks the UI. **[INFER]** Given the Python API is described as calling the same underlying functions as the C++ SDK (see §2 — same function names, same option structs), it's plausible Python scripts execute synchronously on the same thread the C++ plugin uses, meaning the same category of hang/blocking risk (e.g. `DeleteAvatar` on an invalid index) would very plausibly still block Python the same way. But this is not documented and not verified.
- **Python version / third-party packages**: **[UNKNOWN]** No mention anywhere of which CPython version is embedded, whether it's a full CPython distribution or an embedded interpreter, or whether `pip install` / third-party packages (pymongo, requests) work. This is a real gap — if the embedded interpreter can't reach `pip`-installed packages, any Python-side replacement for the plugin would need to talk to Mongo/HTTP via CLO-provided APIs only, or via manual `sys.path` hacks of unknown feasibility.

---

## 2. Feature parity with what Mirra uses

The Python API is **not a separate API** — `list.html` shows Python signatures and C++ signatures side by side for every function, e.g.:

```
python
def ImportAvatar(_avtPath : str, _opt : ImportExportOption) -> bool
"""
@ingroup IMPORT_API
@brief Import Avatar
@param _avtPath : input Avatar file path, _opt : input load options
"""

c++
 ImportAvatar(std::string _avtPath, ImportExportOption _opt)
```

**[DOC]** So Python and C++ are two language bindings over the same underlying engine calls, sharing the same option types (`ImportExportOption`, `ImportZPRJOption`, `ImportDxfOption`, etc.) — this is confirmed structurally across every function checked in `list.html`. **[INFER]** This strongly implies Python does **not** get an independently safer implementation of any given call — if `GetAvatarProperties` crashes on an out-of-range index in C++, the Python binding almost certainly calls the identical underlying code path and would crash the same way. Nothing in the docs contradicts this, and nothing confirms it either — no call in the docs is annotated with different Python-only behavior for error/bounds handling.

Per-feature findings (source: https://developer.clo3d.com/list.html unless noted):

### New project / clearing the scene
**[DOC]**
```
def NewProject() -> None
"""
@ingroup UTILITY_API
@brief Clear the current garment and begin a new garment
"""
```
No parameters, no return value, no mention of avatars specifically (only "garment"). **[UNKNOWN]** whether `NewProject()` clears avatars too, or only garment/pattern state — the one-line brief doesn't say.

### ImportAvatar — replace vs add (the active bug)
**[DOC]** Exact signature:
```
def ImportAvatar(_avtPath : str, _opt : ImportExportOption) -> bool
"""
@ingroup IMPORT_API
@brief Import Avatar
@param _avtPath : input Avatar file path, _opt : input load options
"""
```
That is the **entire** documentation for this function — no description of add-vs-replace semantics, no example showing multiple ImportAvatar calls, no return-value semantics beyond the generic "if it succeeds, return true" boilerplate used elsewhere (this function's docstring doesn't even restate that).

**[DOC]** `ImportExportOption` (from `optiontype.html`) has a field:
```
bAdd:bool
```
listed alongside dozens of other fields, with **no description whatsoever** — the option-type page is a bare field:type list, not annotated per-field. This field is a strong candidate for controlling add-vs-replace behavior on import (its name and its co-location with avatar-import-relevant fields like `bAutoTranslate`, `bMoveGarment`, `translationValueX/Y/Z`, `ImportObjectType` — "0: avatar, 1: trim" per the `ImportFile` docstring — all suggest an avatar/object import context), but **this is inference, not documented fact**. The docs never say "set `bAdd = False` to replace the existing avatar" or anything equivalent.

**[DOC]** `ImportZPRJOption` (used for `ImportZprj`, not `ImportAvatar`) separately has:
```
bAppend:bool
bLoadGarment:bool
bLoadAvatar:bool
...
```
Again, no field descriptions. `bAppend` here plausibly governs whether a `.zprj` project load appends to or replaces the current scene, but this is the project-import option struct, not the avatar-import one, and again this is **[INFER]**, not stated.

**[DOC]** One changelog entry directly touches `ImportAvatar`:
> **V9.1.1, March 2026 — ImportAvatar API**: "Improved ImportAvatar API to load without Size and Pose dialog."

This is about suppressing a UI dialog during import, not about add-vs-replace behavior. No changelog entry anywhere mentions fixing or adding replace-semantics to `ImportAvatar`.

**Bottom line on this specific question**: **[UNKNOWN]** — the public docs do not document any add-vs-replace flag for `ImportAvatar`. The `bAdd` field on `ImportExportOption` is circumstantial evidence such a flag exists, but its actual effect on `ImportAvatar` (vs. other importers that also take `ImportExportOption`, like `ImportOBJ`, `ImportFBX`, `ImportGLTF`, `ImportZpac`) is not documented and would have to be tested empirically inside CLO.

### Deleting avatars, counting avatars, querying properties
**[DOC]** From `list.html` (UTILITY_API section):
```
def DeleteAvatar(_avatarIndexList : list[int]) -> bool
"""
@ingroup UTILITY_API
@brief Delete Avatars
@param _avatarIndexList: List of indices for avatars to delete
"""
```
No mention of behavior for an invalid/nonexistent index — no bounds-check note, no exception documentation, nothing. The changelog (v8.0.0, April 2025) says only:
> "DeleteAvatar — Added support to delete one or more avatars via index. Accepts a list of avatar indices. Returns true on success, false otherwise."
Still nothing about invalid indices. **[INFER]** Given this is the same underlying call the C++ plugin uses, and the docs never warn about the hang, this is consistent with the hang being an undocumented C++-side bug reachable identically from Python — there's no reason from the docs to expect Python calling `DeleteAvatar` with a bad index would behave any better.

**[DOC]**
```
def GetAvatarCount() -> int
def GetAvatarNameList() -> list[str]
def GetAvatarNameListW() -> list[str]
def GetAvatarGenderList() -> list[int]   # 0=male, 1=female, -1=unknown, per avatar
```
(EXPORT_API section of `list.html`, despite being avatar getters — the site's grouping by `@ingroup` doesn't always match intuition.)

**[DOC]**
```
def GetAvatarProperties(_avatarIndex : int) -> map[str, str]
"""
@ingroup UTILITY_API
@brief Get multiple properties for the avatar at the specified index.
@param _avatarIndex: The index of the avatar to get properties for.
@return A map containing property names and their corresponding values for the avatar.
Such as {'DivideMesh': 'true/false', 'KineticFriction': '0.050000', 'SkinOffsetMM': '3.000000',
'SoftBodySimulation': 'true/false', 'StaticFriction': '0.800000'}
"""
```
Added in v9.0.0 (Sept 2025) per changelog. Again — no documented behavior for an out-of-range index, no crash warning. This is the exact function named in the CONTEXT as crashing the process when no avatar exists at that index. **[INFER]** the doc's silence on error handling for an invalid index (here and for `DeleteAvatar`) is consistent across the whole site: none of the Get/Set-by-index avatar functions document bounds checking anywhere I found (`SetAvatarProperties`, `SetAvatarSmooth`, `GetAvatarSubdivisionLevel`, `SetAvatarSoftBodyStiffness`, `GetAvatarSoftBodyStiffness` all have the identical pattern — index parameter, no bounds documentation).

**[DOC]** Safe counting is available and documented cleanly: `GetAvatarCount()`. **[INFER]** Given the crash-on-invalid-index behavior described in CONTEXT, the only documented safe pattern would be: call `GetAvatarCount()` first, then only call `GetAvatarProperties(i)` / include index `i` in `DeleteAvatar([...])` for `i` in `range(GetAvatarCount())` — the docs don't say this explicitly, but it's the only defensive pattern available given what's documented.

### Importing/exporting .zprj project files
**[DOC]**
```
def ImportZprj(filePath : str, loadOption : ImportZPRJOption) -> bool
"""
@ingroup IMPORT_API
@brief Load zprj File without the dialog but the loadOption
"""
```
and:
```
def ExportZPrj() -> str                                    # exports to temp folder
def ExportZPrj(filePath : str) -> str
def ExportZPrj(filePath : str, bCreateThumbnail : bool) -> str
```
`ImportZPRJOption` fields (undocumented individually): `bAppend`, `bLoadGarment`, `bLoadAvatar`, `translationValueX/Y/Z`, `translationUnit`, `bLoadSceneAndProps`, `bLoadRenderProperties`, `bLoadCustomView`, `bLoadDisplaySettings` (the last one added per changelog v8.0.5, Sept 2025: "ImportZprjOption — Added the bLoadDisplaySettings option, allowing DisplaySettings saved in a zprj to be loaded.").

### Setting avatar measurements / sizing
**[DOC]**
```
def ImportAvatarMeasurement(_csvPath : str, _avtPath : str, _opt : ImportExportOption) -> bool
"""
@ingroup IMPORT_API
@brief Import Avatar Measurement CSV file
"""

def ImportMeasurement(_csvPath : str) -> bool
"""
@ingroup IMPORT_API
@brief Import Avatar Measurement CSV file
"""
```
Two distinct functions with nearly identical briefs and no explanation of how they differ (does `ImportMeasurement` apply to the currently-loaded avatar, while `ImportAvatarMeasurement` loads/creates from a specified `.avt` + CSV pair? **[INFER]**, not stated). Changelog: "Fixed incorrect avatar height when using ImportAvatarMeasure" (undated section around the v9.0.x/v8.0.x window in the file) confirms this call has had bugs. Both take CSV input — **[UNKNOWN]** the exact CSV schema/column names are not shown in any fetched page.

### Exporting glTF and GLB
**[DOC]**
```
def ExportGLTF(_filePath : str, options : ImportExportOption, bGLBinary : bool) -> list[str]
def ExportGLTFW(_filePath : str, options : ImportExportOption, bGLBinary : bool) -> list[str]
def ExportGLB(_filePath : str, options : ImportExportOption) -> list[str]
def ExportGLBW(_filePath : str, options : ImportExportOption) -> list[str]
```
These are the same underlying calls the C++ plugin uses (same `ExportGLTF`/`ExportGLB` names, same `ImportExportOption` struct) — so a Python-side `ExportGLB` call is very likely to hit the identical "returns empty" behavior described in CONTEXT, since it's not a different code path, just a different language binding. Relevant changelog entries:
- v10.0.2 (June 2026): "ExportGLTF GLB with Zip Output — Fixed an issue where the ExportGLTF API failed to create a GLB file when zip output was enabled."
- v10.0.3 (July 2026): "GLB Export Graphic Z-Offset — Fixed an issue where the GLB exporter set the z-offset of graphics to -1..."; "GLB Export Missing 'Source' Field — Fixed the GLB exporter omitting the source field on the textures array."
- An earlier entry: "Fixed the issue of ExportGLB API where the Garment was not being exported when Colorway Option is included."

**[INFER]** This is a pattern of repeated, ongoing GLB-export bugs across versions (empty/missing garment, missing texture fields, wrong z-offset) — the GLB exporter itself appears to be immature/actively-being-fixed engine code, independent of language binding. Switching from C++ to Python would not sidestep these bugs since they live in the underlying exporter, not the SDK binding layer.

### Importing garment patterns (DXF), seams, simulation
**[DOC]**
```
def ImportDXF(_filePath : str, loadOption : ImportDxfOption) -> bool
def ImportDXFW(_filePath : str, loadOption : ImportDxfOption) -> bool
```
`ImportDxfOption` fields (undocumented individually): `m_bAppend`, `m_bAutoScale`, `m_Scale`, `m_Angle`, `m_bImportPatternAnnotation`, `m_bAutoTraceAsInternalLines`, `m_SwapCuttingLineAndSewingLine`, `m_bIncludeNotchs`, `m_bAutoDistribute`, `m_bOptimizeAllCurvePoints`, `m_bImportAllDrawCurvePoint`, `m_bRemoveNonGradingPoints`, `m_bConvertToSeamAllowance`, `m_bImportSeamAllowanceNotchOnly`. Note `m_bAppend` here too — the same append/replace-style flag pattern recurs across every import-option struct (`ImportZPRJOption.bAppend`, `ImportExportOption.bAdd`, `ImportDxfOption.m_bAppend`), but none of the three is documented beyond its name.

**[DOC]** Seam creation:
```
def AddSeamlinePairGroup(_patternAIndex : int, _lineAIndex : int, _patternBIndex : int,
                          _lineBIndex : int, _directionA : bool, _directionB : bool) -> bool
```
(with two additional overloads taking child-pattern indices, for garments with sub-patterns). Supporting queries: `GetSeamlinePairGroupCount()`, `GetSeamlinePairGroupListInPattern(_patternIndex)`, `GetSeamlinePairGroupName(...)`, `GetSeamlinePairGroupIndexFromName(...)`.

**[DOC]** Simulation:
```
def Simulate(_steps : int) -> bool
"""
@ingroup UTILITY_API
@brief Simulate the garment in multi steps. All dynamics properties (time step, CG iteration
count, ...) follow the current simulation properties
@param _steps: how many steps(=frames) to simulate
"""
```
And a full working example is given in `scenario.html`:
```python
cloAssetFolderPath = "C:/Users/Public/Documents/CLO/Assets/Avatar/Avatar/"
avtfilePath = cloAssetFolderPath + "/Female_V2/FV2_Feifei.avt"
import_api.ImportFile(avtfilePath)
zpacfilePath = cloGarmentFolderPath + "/Female_T-shirt.zpac"
import_api.ImportFile(zpacfilePath)
utility_api.Simulate(100)
```
This scenario uses generic `ImportFile` (not `ImportAvatar`) to load the avatar, then `ImportFile` again for the garment `.zpac`, then simulates 100 steps. A second scenario ("Animation Render") does use `ImportAvatar` explicitly:
```python
AvatarOp = ApiTypes.ImportExportOption()
import_api.ImportAvatar(avatar_path, AvatarOp)
import_api.ImportFile(hair_path)
import_api.ImportFile(motion_path)
import_api.ImportFile(garment_path)
utility_api.SetAnimationRecording(True)
export_path = export_api.ExportZPrj(output_zprj_path)
```
Note: `AvatarOp` is constructed with all-default field values (`ApiTypes.ImportExportOption()`), so this official example does **not** demonstrate setting `bAdd`/replace behavior at all — it's a fresh-scene single-avatar-import scenario, which sidesteps the exact question we care about.

---

## 3. ImportExportOption and import options — structure

**[DOC]** Full field list of `ImportExportOption` per `optiontype.html` (https://developer.clo3d.com/optiontype.html#importexportoption) — types only, **no per-field descriptions anywhere on the page**:

```
bExportGarment:bool            bExportAvatar:bool           bSingleObject:bool
weldType:WELD_TYPE             bThin:bool
bUnifiedUVCoordinates:bool     bCreateUnifiedTexture:bool   unifiedTextureSize:float
unifiedTextureFillSeamSize:int bUseInifinteSeams:bool       unifiedTextureBakeMargin:float
unifiedTextureBakeRelateive:bool
bUnifiedDiffuseMap:bool  bUnifiedNormalMap:bool  bUnifiedMetalnessMap:bool
bUnifiedRoughnessMap:bool  bUnifiedOpacityMap:bool  bUnifiedDisplacementMap:bool
bIncludeHiddenObject:bool      bIncludeInnerShape:bool       scale:float
axisX:int  axisY:int  axisZ:int
bInvertX:bool  bInvertY:bool  bInvertZ:bool
bSaveColorWays:bool             bSaveInZip:bool               bDiffuseColorCombined:bool
bExcludeAmbient:bool            bOpacityMap:bool              bMetaData:bool
bSizeAndPoseFromAvatar:bool     bEmbedded:bool                bExportLight:bool
bExportFabric:bool              bSaveColorWaysSingleFile:bool fbxSdkVersion:int
bIncludeAvatarShape:bool        m_AuthenticationKeyForAPI:str
ImportObjectType:int            bAutoTranslate:bool           bCreateCamera:bool
bCreateAvatarJointAnimation:bool  bCreateAvatarCacheAnimation:bool  bCreateClothCacheAnimation:bool
bMoveGarment:bool                bAddArrangementPoints:bool    bAutoCreateFittingSuit:bool
bAdd:bool
translationValueX:float  translationValueY:float  translationValueZ:float
bTrace2DPatternsUVMap:bool      bCreateMetallicRoughnessMap:bool
bClothUnifiedUVCoordinates:bool bAvatarUnifiedUVCoordinates:bool
```

**[DOC]** This is one struct, used for both import and export calls (`ImportOBJ`, `ImportFBX`, `ImportGLTF`, `ImportZpac`, `ImportFile`, `ImportAvatar`, `ImportAvatarMeasurement` **and** `ExportGLTF`, `ExportGLB`, `ExportFBX`, etc. all take it). It is **not** split into a distinct import-only vs export-only option type — everything import- or export-relevant is mixed into this one struct. The only piece of documentation on how a specific field is interpreted for a specific call comes from the calling function's own one-line brief, e.g. `ImportFile`'s docstring: `"@param filePath: the input file path to load, ImportExportOption - loadObjectType 0 : avater, 1 : trim"` (sic — "avater" is a typo in the source docs, quoted verbatim).

**[DOC]** There IS a genuinely separate, import-specific option object for `.zprj` and DXF: `ImportZPRJOption` and `ImportDxfOption` (both distinct from `ImportExportOption`; full field lists in §2 above). So the picture is: `ImportExportOption` is the shared generic struct used by most import/export calls including `ImportAvatar`, while `.zprj` and DXF imports get their own specialized option structs.

**[DOC/INFER]** Regarding "any documented flags controlling replace-vs-add on import": `bAdd` (on `ImportExportOption`), `bAppend` (on `ImportZPRJOption`), and `m_bAppend` (on `ImportDxfOption`) are the three candidate fields by name. **None of the three has a description anywhere in the fetched docs.** This is the single most actionable finding for the CONTEXT's stated bug — it is plausible `bAdd:bool` on `ImportExportOption`, set appropriately, causes `ImportAvatar` to replace rather than add, but this is unverified and would need a controlled test inside CLO (e.g. set `bAdd = False`/`True`, call `ImportAvatar` twice, check `GetAvatarCount()`).

---

## 4. Stability and limits

**[DOC]** No page discusses Python-specific threading, UI-blocking, or crash risk. The closest relevant material:

- `environment.html` (https://developer.clo3d.com/environment.html) is entirely about the **C++ plugin build environment** — it documents exactly the Qt-version problem in CONTEXT:
  > "Qt Version Compatibility Notice — For CLO 2026 and later versions: Use Qt 6.10.1. For CLO 2025 and earlier versions: Use Qt 5.15.16. Please ensure you are using the correct Qt version for your target CLO version."
  > "Build configuration requirement: Plugins must be built in Release. Debug binaries (.dll/.dylib) will not load in CLO."

  **[INFER]** This page is exclusively about C++ plugin (DLL/dylib) builds — there is no equivalent "Python version compatibility" page anywhere on the site. This is consistent with Python scripts **not** requiring a matching-SDK-version rebuild the way a compiled C++ plugin ABI does (a `.py` file has no ABI to break), which would remove exactly the failure mode described in CONTEXT #1 ("must be rebuilt whenever CLO's app version changes... a stale plugin hang CLO permanently"). This is a reasonable inference but is not stated anywhere as an explicit guarantee — CLO could in principle still change Python function signatures/behavior between versions (see `ExportGLTFAsFabric` note below), it just wouldn't hard-crash from a stale binary the way a DLL would.

- **[DOC]** The changelog does show the Python/C++-shared API surface changing behavior across versions in backward-incompatible ways, e.g. v8.0.1 (May 2025): "Improved ExportGLTFAsFabric call in FabricAPI instead of ExportAPI. If you have previously used this API, please make changes." — i.e., a function moved modules, breaking existing scripts. **[INFER]** So while Python scripts don't suffer the DLL-ABI-mismatch class of failure, they are **not immune to breaking changes** between CLO versions; they just fail as ordinary Python `AttributeError`s/logic bugs instead of as an unrecoverable native crash/hang. That's a real reliability improvement (fails loud and recoverable vs. fails as a silent hang) but not "version-proof."

- **[UNKNOWN]** No rate limits, no "do not call from X" warnings, no documented thread-safety rules anywhere in the fetched pages.

- **[DOC]** "Headless mode" is real and actively maintained (multiple changelog fixes target it specifically, see quotes in §1/§2), which is a positive signal that CLO's own engineering treats non-interactive/scripted execution as a first-class, ongoing-support path — not an unsupported edge case.

---

## 5. Changelog — every Python-API-related entry found

Full read of https://developer.clo3d.com/changelog.html. Entries explicitly naming "Python" (there is no separate Python-only changelog section; these are scattered across version entries):

| Version | Date | Entry |
|---|---|---|
| v4.2.1 | Aug 2023 | "Python API Editor Improvement" — Editor Re-Sizing and IntelliSense added to the Python API editor interface. |
| v4.3.0 | Nov 2023 | "Added ApiStubFiles within CLO.exe Folder (For Python API)" — i.e. `.pyi`-style stub files shipped for IDE autocomplete against the API. |
| v8.0.0 | Apr 2025 | "Python Editor" listed among v8.0.0 changes (brief entry, no detail beyond the heading in the fetched text). |
| v8.0.3 | Aug 2025 | "Add Python Script as Plugin — Allows Python scripts to be loaded as plugins, similar to C++ DLLs." |
| v9.1.0 | Dec 2025 | "Python Script Menu (macOS) — Fixed an issue where Python script menu actions were not registering correctly on macOS." |
| v10.0.0 | May 2026 | "Python API for Library Window & Library Folder Management — Added Python API support for Library Window and Library Folder Management (New & Old Library)." and "Python Plugin Auto-Load on Startup — Added support for auto-loading Python plugins on application startup." |

**[INFER]** Reading this timeline together: Python scripting has existed since at least 2023 as an editor/manual-run tool, and only became a first-class **plugin mechanism** (loadable like a DLL, auto-loading at startup) starting Aug 2025 (v8.0.3) through May 2026 (v10.0.0). This is a meaningfully recent capability — if Mirra wants to replace the C++ plugin with an always-running Python-based controller (not just one-off scripts), that architecture has only been documented as supported for roughly a year as of "today" (per system context, Aug 2026), which is worth flagging as relatively unproven/immature versus the multi-year-old C++ plugin path.

No other changelog entries name "Python" explicitly; all other entries (GetAvatarProperties, DeleteAvatar, ExportGLB fixes, etc.) are listed generically as "New APIs" / "Issue Resolved" without a language tag, consistent with §2's finding that Python and C++ share one API surface — a fix to `ExportGLB` is a fix to the underlying call both languages invoke, not a Python-specific changelog category.

---

## 6. Honest assessment

**Could a Python approach have avoided the specific failures in CONTEXT?**

1. **Qt 6.10 rebuild-on-upgrade hang** — **Likely yes, partially.** Python scripts have no compiled ABI, so they can't hang CLO the way a stale `.dll` built against an old Qt/SDK can. This class of failure is a direct consequence of choosing a compiled plugin; Python sidesteps it structurally. But (§4) the underlying API can still change function locations/behavior between versions (e.g. `ExportGLTFAsFabric` moving modules), so "no rebuild needed" does not mean "no changes needed" — a Python controller would still need re-validation against new CLO versions, just without the catastrophic silent-hang failure mode.

2. **`GetAvatarProperties(index)` crashing on invalid index / `DeleteAvatar([...])` hanging on invalid index** — **Almost certainly no.** §2 establishes Python and C++ are two bindings over the identical underlying calls, using the identical option/parameter types, with identical (silent) documentation about error handling. Nothing in the docs suggests Python gets bounds-checking, exceptions, or any safety net the C++ SDK lacks. **[INFER]** these two specific crash/hang bugs would almost certainly reproduce identically from Python, since they're engine-level bugs exposed through both bindings, not C++-binding-specific bugs. The fix is architectural regardless of language: never call these with unvalidated indices — always gate on `GetAvatarCount()` first — which the C++ plugin should also be doing today.

3. **`ExportGLB` returning empty** — **Likely no, or only incidentally.** The changelog shows a string of GLB-exporter bugs (missing garment, wrong z-offset, missing texture source field, zip-output failures) spanning multiple recent versions — this reads as immature/actively-being-fixed exporter code at the engine level, not a C++-binding artifact. Calling `ExportGLB` from Python hits the same exporter. If Mirra's specific empty-export symptom matches one of the changelog's fixed bugs, upgrading CLO (not switching language) is the fix; if it doesn't match a listed fix, Python wouldn't help either.

**What would it cost to find out, concretely?**

- A same-day spike: inside a running CLO instance, use the Python Editor (Edit → Python Script → Run Python Script) to call, in order: `GetAvatarCount()`, `ImportAvatar(path, opt)` twice with `opt.bAdd` toggled between calls, `GetAvatarCount()` again, and `GetAvatarNameList()` — to empirically determine whether `bAdd` (or its absence) controls replace-vs-add. This directly answers the single most valuable open question (§2) and costs roughly an hour, no rebuild/deploy needed since it's just typed/dragged into the running app.
- A second spike, same session: repeat `GetAvatarProperties(99)` (an obviously invalid index) from the Python console and observe whether CLO crashes the same way the C++ SDK does. This directly tests the "no safety net either way" hypothesis in finding #2 above.
- If both spikes confirm the hypotheses (bAdd controls replace; invalid index still crashes/hangs), the cost/benefit becomes: adopting Python removes the Qt-rebuild-hang class of failure and the C++-toolchain maintenance burden, but does **not** remove the need for defensive index-bounds-checking in the calling code, and does not fix `ExportGLB` (an engine bug, fix via CLO version upgrade). That is a real but partial win, achievable for the cost of ~1 day of spike testing plus rewriting the plugin's control logic in Python (the REST-server-on-50505 role would need to move to a Python "plugin," which per §5 has only been a documented, supported pattern since Aug 2025/May 2026 — worth a stability gut-check before committing, since it's a newer part of the API than the rest).

---

## Addendum: why does the developer page exist when most functions are undefined?

Follow-up question, researched separately. Two things prompted it, both independently verified in our own repo before I re-checked them against CLO's public materials: (1) the SDK's C++ headers ship nearly every function with an empty/stub body — e.g. `virtual void NewProject() {}` in `UtilityAPIInterface.h`, and every `ExportAPIInterface.h` method likewise — yet these calls work correctly at runtime; (2) the online reference frequently lists a field or function name with zero explanation, the clearest case being `ImportExportOption.bAdd` / `ImportZPRJOption.bAppend` / `ImportDxfOption.m_bAppend`, all documented only as a name and a type (or, per the user's own header excerpt, a single trailing comment: `/// If true, set load type as add`).

Sources for this addendum: our own repo (`clo_workspace/windows/CMakeLists.txt`, `clo_workspace/windows/RestPlugin_windows.cpp`, `clo_workspace/mac_plugin_setup.md`), plus `developer.clo3d.com` (`register.html`, `download.html`), plus `support.clo3d.com` articles fetched via curl (WebFetch gets HTTP 403 on this Zendesk-hosted domain; curl with a browser `User-Agent` works): "CLO API/SDK Guide" (`360017616633`), "How to use Python Script in CLO?" (`115014409267`), "Register API Plug-In" (`360013316493`). The official SDK Guide PDFs linked from that support page are Flate-compressed and could not be extracted with the tools available in this environment (no `pdftotext`/`poppler`, no Python PDF library installed, and installing one would mean writing to `requirements.txt`, which is out of scope for this file-only task) — noted as a real gap, not silently skipped.

### a) The empty-body pattern — confirmed, from our own build setup

**[DOC, from our repo, not from CLO's docs]** This is a standard interface/import-library pattern, and our own plugin build already depends on it working this way — it isn't a theory we have to take on faith. `clo_workspace/windows/CMakeLists.txt` does exactly this:

```cmake
find_library(CLO_API_INTERFACE NAMES CLOAPIInterface HINTS ${CLO_API_INTERFACE_DIR}/Lib REQUIRED)
find_file(CLO_API_INTERFACE_DLL NAMES CLOAPIInterface.dll HINTS ${CLO_API_INTERFACE_DIR}/Lib REQUIRED)
...
target_link_libraries(RestPlugin PRIVATE ${CLO_API_INTERFACE} Dbghelp.lib)
```

The plugin links against `CLOAPIInterface.lib`/`.dll` — a binary CLO itself ships inside the SDK package and that the running CLO application provides at runtime. The headers (`UtilityAPIInterface.h`, `ExportAPIInterface.h`, etc.) declare the interface classes with empty/no-op or trivially-failing default bodies (`{}`, `return false;`). Our own `RestPlugin_windows.cpp` already carries a comment documenting this exact mechanism in the specific case that bit us:

```
// ...the installed CLO app is 2026.0.374 while this plugin builds
// against CLO_SDK_v2025.2.368, and ExportGLB's declared body in that SDK's
// header is a bare stub (returns an empty vector) - consistent with this
// CLO version simply not implementing it yet, rather than an options bug.
```

**[INFER, standard C++ practice, consistent with all evidence above]** So: an interface header with an empty body is not a promise of "unimplemented" or "no-op" — it's a placeholder default that exists so the header compiles standalone. At runtime, when CLO loads the plugin (or runs a Python script through its own embedded interpreter), the *real* implementation — living inside CLO's own executable/DLL, not the header — is what actually executes. The header's empty body tells a plugin author literally nothing about whether, or how, the real function behaves; it is purely a C++ mechanical requirement (a virtual method needs *some* body or the class is abstract and can't be default-constructed/linked cleanly in the header-only interface pattern used here). Our comment above is itself evidence this can go the other way too: the empty body *can* mean the currently-installed CLO version genuinely hasn't implemented that call yet (as with `ExportGLB` on 2026.0.374) — so the header gives zero signal either way, and the only way to know is to call it against the specific CLO build in use and observe the result.

**[UNKNOWN]** I could not find any CLO document that states this architecture explicitly in prose (see §b/§c below — the closest is the "must rebuild against matching SDK" warnings, which are a symptom of this architecture, not an explanation of it). This is inference from standard C++ SDK/plugin conventions plus our own repo's working build setup, not a quote from CLO.

### b) Is the online reference auto-generated? — Yes, strong evidence

**[DOC]** Every page on `developer.clo3d.com` ends with: *"Built with Sphinx using a theme provided by Read the Docs."* Sphinx is a documentation generator, not a hand-authored wiki.

**[DOC, structural evidence from the raw HTML of `list.html`]** Each function entry is rendered as a matched pair of syntax-highlighted code blocks — one `highlight-python` block containing a Python stub (`def FuncName(...) -> ReturnType:`) with the docstring reproduced as a Python triple-quoted string, and one `highlight-c++` block containing the C++ signature with the *identical* text reproduced as `///`-prefixed Doxygen comments (`@ingroup`, `@brief`, `@param`, `@return`). Concretely, for every single function checked while building this research (dozens, across IMPORT_API, EXPORT_API, UTILITY_API, PATTERN_API), the Python docstring and the C++ `///` comment block are word-for-word identical, down to typos (e.g. `"ImportExportOption - loadObjectType 0 : avater, 1 : trim"` — "avater" misspelled identically in both the Python and C++ renderings of `ImportFile`'s doc). That is not something a human documentation writer produces by hand twice; it is the signature of a generator that parses the SDK's own Doxygen-style header comments once and renders them into two side-by-side language views.

**[INFER]** Put together: the reference site is a generated artifact — almost certainly a custom Sphinx extension/script that walks the C++ SDK headers, extracts each function's `@brief`/`@param` Doxygen comment block, and mechanically emits both a synthesized Python-stub view and the original C++ view from that one source comment. This fully explains the pattern in the user's question: **when a header field or function has no Doxygen comment (or only a bare one-line comment, as `bAdd`'s `/// If true, set load type as add`), the generator has nothing more to render than the name, type, and whatever fragment of comment exists.** There is no separate "meaning" the doc site is withholding — the generator is not summarizing or omitting; it is reproducing the entirety of what exists in the header. The header comment *is* the documentation, and for many fields (especially option-struct fields, as opposed to top-level functions) that comment is one line or absent entirely.

### c) Is there better documentation anywhere? — No, not publicly, as far as I could reach

Checked, and results:

- **`register.html` / `download.html`** (developer.clo3d.com) — **[DOC]** Purely procedural (how to register a `.dll`/`.dylib`/`.py` as a plugin in CLO's UI; version-to-SDK download table). No architecture or behavior explanation.
- **Support article "CLO API/SDK Guide"** (`support.clo3d.com/hc/en-us/articles/360017616633`) — **[DOC]** This is the landing page for downloading the SDK zip + a PDF "manual" per CLO version, going back to CLO 5.1.290 (API v2.3, pre-2019) through the current v9.0.0. It contains one substantive prose passage confirming the *symptom* our CONTEXT names, but not the *mechanism*:
  > "CLO 5.1.436 supports CLO API/SDK V2.5. You should rebuild the plug-in dll and/or dylib from the previous version. Some API calls has been added into this version to support Unicode but CLO is not fully compatible with Unicode while saving/loading/exporting files so these Unicode related API calls might not work as expected."

  **[INFER]** This confirms the "must rebuild against the matching SDK per CLO version" requirement is not new or specific to the Qt 6.10 migration — it's been CLO's standing plugin contract since at least 2019 (API v2.3/v2.5 era). It also candidly admits behavior gaps ("might not work as expected") without further detail — consistent with CLO's own documentation culture of naming a limitation without explaining it. The linked per-version PDF "manual" files (e.g. `CLO_API_SDK_GUIDE_20230406.pdf`) could not be text-extracted in this environment (Flate-compressed PDF, no `pdftotext`/PDF library available) — **[UNKNOWN]** whether those PDFs contain narrative behavioral documentation beyond what's on developer.clo3d.com; I could not rule this out, but given the support page's own framing ("refer to the API/SDK Guide directly attached... in order to develop a customized feature"), these read as build/setup guides paired with the header-derived reference, not a separate behavioral spec — this is inference from the surrounding page, not confirmed by reading the PDF itself.
- **Support article "How to use Python Script in CLO?"** (`115014409267`) — **[DOC]** The entire "how to get help writing a script" guidance given by CLO's own support team is: *"Lastly, to generate the Python code, you can either use CLO AI chat or refer to the API source."* This is a direct, official acknowledgment that beyond the (Sphinx-generated, header-derived) reference, there is no other documentation — the recommended fallback is either an AI assistant or reading the SDK source/headers yourself. A 2021-era user comment on that same page also notes Python Script was "only a Windows feature" at that time — **[UNKNOWN]** whether that's still true today; not restated anywhere current.
- **Community/forum** — `support.clo3d.com` community posts (e.g. "IMPORTING AVATAR," "Import original avatars, file path") returned HTTP 403 to WebFetch and were not reachable via curl either in the time available for this addendum (search-result snippets only); I could not confirm or rule out whether any forum thread discusses `bAdd`/`bAppend` semantics specifically. **[UNKNOWN]**, not resolved.
- **SDK sample projects** — **[DOC, referenced not inspected]** The support page states sample plugin projects (e.g. "ExportPlugin") ship inside each SDK zip download. **[UNKNOWN]** whether their source code exercises `bAdd`/`bAppend` in a way that would reveal semantics by example — we did not download an SDK zip to check; this is a concrete next step if the empirical test in the base report (§ "What would it cost to find out") doesn't fully resolve the question.

**Bottom line for (c): no, there is nothing publicly available beyond the auto-generated, header-derived reference.** The reference, the PDFs, and the support articles all ultimately point back to the same source (the header comments) or explicitly defer to "read the source" / community trial-and-error. This is worth stating plainly rather than treating as a research gap: **CLO does not publish a behavioral specification for its API; the header comments are the entire public specification, and where a header comment is thin or absent, so is the documentation.**

### d) Practical consequence for us

**[INFER, synthesizing the above]** Given (a)–(c), the realistic way to work with this API is:

1. **Treat every undocumented-behavior field/function as untested until we've tested it against the specific installed CLO build.** The header/doc gives a name and a type signature and, at best, a one-line description — never a contract for edge cases (invalid index, empty scene, second call after a first). This matches exactly what we've already hit three times today (`GetAvatarProperties` crash, `DeleteAvatar` hang, `ImportAvatar` add-not-replace) — none of these are documentation failures on our part; they are genuinely undocumented anywhere CLO publishes.
2. **Empirical testing is the only reliable path**, and it's cheap relative to reading more docs: the base report's spike plan (toggle `ImportExportOption.bAdd` across two `ImportAvatar` calls, watch `GetAvatarCount()`; call `GetAvatarProperties` with a known-invalid index and watch for a crash) is still the right next step — no further public document is going to answer these more authoritatively than running the call.
3. **Pin behavior to a specific CLO build, always.** Because the underlying implementation lives in CLO's own binary (not the header), and CLO has a documented history (since 2019) of requiring plugin rebuilds and warning that some calls "might not work as expected" per version, any behavior we confirm empirically is only confirmed *for that installed CLO version* — exactly the same versioning discipline the C++ plugin already has to observe, and which Python does not exempt us from (per §5 of the base report).
4. **Support channels**: `support.clo3d.com` offers "Submit a request" (presumably a ticket queue) and a "Discord" link in its header nav, plus a "CLO Chatbot." **[UNKNOWN]** whether a submitted support ticket would actually get a substantive behavioral answer (e.g. "what does `bAdd` do on `ImportAvatar`") rather than a boilerplate reply — I found no evidence either way (no visible archive of answered API tickets). The Discord server is a plausible channel for developer-to-developer answers (other plugin authors would have hit the same undocumented fields) but I did not join/search it as part of this research — flagged as a concrete, low-cost next step if the empirical spike test doesn't fully resolve `bAdd`/`bAppend` semantics.

