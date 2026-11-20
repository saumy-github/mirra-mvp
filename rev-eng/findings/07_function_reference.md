# Function reference: CLO API functions called by RestPlugin_windows.cpp

*Status: complete (static, docs-only)*
*Date: 2026-10-29*
*Sources: SDK 2026.1.336 headers (doc comments), `raw/hdrdiff_*.diff` (224 -> 336), plugin source (line numbers = `clo_workspace/windows/RestPlugin_windows.cpp`).*

Conventions and global caveats:
- Behaviour here is what the **header doc comments** promise. Real implementation is in the CLO exe (not disassembled; see FINDINGS.md). Where docs are silent it is stated as "undocumented".
- **Base-class stub return values matter.** The header bodies are what you get if vtable dispatch hits an un-overridden slot (e.g. SDK/app version skew). Several stubs return `true` (`ImportFile`, `ImportDXF`) so a skewed build can report false success. Flagged per function.
- **Threading.** Headers contain no explicit main-thread statement for these APIs except: `GuiAPIInterface` (main/GUI thread), and the 336 note on `AddSeamlinePairGroupPartial` ("Call from the thread that owns the scene, as with the other pattern-editing APIs"). Treat every scene-mutating call as main-thread-only. The plugin runs them from the CLO timer drain / `MirraWndProc` (CLO main thread) - consistent.
- **Exceptions.** None of the headers declare error throwing; the plugin wraps in `try/catch(...)`, but SEH access violations (e.g. `ExportAVT`) are not caught by C++ `catch`; plugin uses `RunSEHGuarded` for ExportAVT only.
- **Units.** CLO internal unit is millimetres. glTF/GLB expect metres (use `scale=0.001`). Pattern-space coordinates are mm. Grading/offset APIs are mm.
- **Indexing.** Pattern index = "RealPatternList order" (0-based, same as `GetPatternCount`). Fabric index = Object Browser fabric index (0-based). Line index = outline line of the pattern (0-based; order of `GetPatternLineInfo`/`GetLineLength`).

---

# IMPORT_API (`ImportAPIInterface.h`, accessed as `IMPORT_API`)

## ImportOBJ
`virtual bool ImportOBJ(const std::string& _filePath, const Marvelous::ImportExportOption& _options)` (h:86)
- Params: `_filePath` input OBJ; `_options` - if given, import follows options with no dialog.
- Return: true on success (stub returns false).
- Relevant option fields for import: `scale`, `ImportObjectType` (0 Avatar, 1 Trim, 2 Garment), `bAutoTranslate` (align bottom to ground), `bAdd`, `bMoveGarment`, `bAddArrangementPoints`, `bAutoCreateFittingSuit`, translationValueX/Y/Z (mm), `axisX/Y/Z`, `bInvertX/Y/Z`. See 08_struct_reference.
- Plugin use (l.1714, `import-avatar`): `scale = floatParam1>0 ? floatParam1 : 1.0`, `ImportObjectType=0`, `bAutoTranslate=true`. Return stored as success.
- Notes: `scale` is a multiplier on the object as authored; docs say default CLO unit is mm for obj/fbx, so a metre-authored OBJ needs `scale=1000`. The plugin passes through caller's scale; correctness depends on the Python caller (not verifiable here). Return true does not prove the avatar is usable.

## ImportFile (two overloads)
`virtual bool ImportFile(const std::string& filePath)` (h:27) - "Load File (zprj, zpac, avt, obj, fbx, zcmr). **This function will show up the dialog per the file type.**" Stub returns **true**.
`virtual bool ImportFile(const std::string& filePath, const Marvelous::ImportExportOption& _options)` (h:235) - "Load File (obj, fbx, gltf) by obj type. This function will show up the dialog per the file type." `ImportExportOption::ImportObjectType` 0 avatar, 1 trim (header note; the struct also lists 2 garment). Stub returns **true**.
- Plugin use (l.1757/1759, `import-avatar-avt`, `method=import_file` / `import_file_opts`): debug experiments, not the default path (default is `ImportAvatar`).
- FLAG: both are documented to open **modal dialogs** (blocks the REST drain until user clicks); the 2-arg doc even lists gltf but says dialog shown. Unsuitable for unattended automation. Stub `return true` means a vtable skew silently "succeeds".

## ImportAvatar
`virtual bool ImportAvatar(std::string _avtPath, Marvelous::ImportExportOption _opt)` (h:348)
- `_avtPath` .avt file; `_opt` load options. **ImportExportOption is passed by value** (class with virtual dtor + 4 `std::vector` members since 336) - ABI/layout-sensitive across 224/336 (see FINDINGS #5). Doc does not state return semantics beyond bool (stub false).
- Plugin use (l.1761): default method for `import-avatar-avt`; options default `scale=1.0` plus caller-supplied knobs (`ImportObjectType`, `bAdd`, `bAutoTranslate`, `bMoveGarment`, `bAddArrangementPoints`, `bAutoCreateFittingSuit`, `bSizeAndPoseFromAvatar`, `bIncludeAvatarShape`, `bIncludeSkeleton`). On success `g_avatarsLoaded++`.
- FLAG: `bAdd=false` default means "replace" vs `true` "add"; the SDK doc for `SetGradingPairedAvatarFromFile` says "Unlike ImportAvatar (which replaces the scene avatar)". Our `g_avatarsLoaded` counter increments on every success even if a replace occurred -> counter can exceed real avatar count; `clear-avatars` then deletes indices 0..counter-1 (see DeleteAvatar). `ImportObjectType` default 0 (avatar) is OK.
- Memory: user's note that exported GLBs are identical across users implies `.avt` import path may ignore measurements; not documented either way.

## ImportAvatarMeasurement
`virtual bool ImportAvatarMeasurement(std::string _csvPath, std::string _avtPath, Marvelous::ImportExportOption _opt)` (h:339)
- "Import Avatar Measurement CSV file". Params: CSV path, avatar file path, options. Return bool (stub false). **Undocumented:** CSV column format, units, whether `_avtPath` is loaded fresh or an already-loaded avatar, which options matter, whether a resize triggers simulate.
- Plugin use (l.1782): only when `param2` (avatar path) non-empty; options `scale=1.0` (otherwise default).
- FLAG: `scale=1.0` default is also the struct default - harmless. The CSV unit convention must be taken from the CLO sample CSV (not in SDK docs).

## ImportMeasurement
`virtual bool ImportMeasurement(std::string _csvPath)` (h:357)
- Same CSV, applies to the current avatar (implied; not stated). Return bool (stub false).
- Plugin use (l.1785) when no avatar path given. Same undocumented-format caveat. Return true does not say measurements actually changed shape; verify via `GetAvatarMeasurements` (unused API, see 09) or by re-exporting.

## ImportDXF
`virtual bool ImportDXF(const std::string& _filePath, const Marvelous::ImportDxfOption& loadOption)` (h:188)
- Return: true on success. **Stub returns true.**
- ImportDxfOption fields (defaults): `m_bAppend=false`, `m_bAutoScale=true`, `m_Scale=1.0`, `m_Angle=0`, `m_bImportPatternAnnotation=true`, `m_bAutoTraceAsInternalLines=false`, `m_SwapCuttingLineAndSewingLine=false`, `m_bIncludeNotchs=false`, `m_bAutoDistribute=false`, `m_bOptimizeAllCurvePoints=false`, `m_bImportAllDrawCurvePoint=false`, `m_bRemoveNonGradingPoints=false`, `m_bConvertToSeamAllowance=false` (deprecated, now automatic), `m_bImportNotchTo=true`, `m_eNotchImportPlacement=2` (0 outline, 1 seam allowance, 2 both).
- Plugin use (l.1856): `m_Scale = floatParam1>0 ? floatParam1 : 1.0`, `m_bAppend=true`. Others default.
- FLAGS:
  1. `m_bAutoScale=true` (default) is left on while also setting `m_Scale`. Docs do not say how they interact (does auto-scale detect DXF units and then multiply by `m_Scale`?). If the DXF is in mm or cm and units are written in the header, auto-scale may rescale and the explicit scale compounds. Needs a live test; suspect for any garment-size mismatch.
  2. `m_bAppend=true` always: patterns accumulate across imports unless `NewProject` is called; the plugin tracks `g_patternsLoaded`.
  3. `m_bIncludeNotchs=false` (default): notches not imported. If Mirra DXF writer emits notches (seam matching, grading), they are dropped.
  4. `m_bRemoveNonGradingPoints=false`. Fine.
  5. Return `true` from the stub = false success on skew.

---

# EXPORT_API (`ExportAPIInterface.h`, `EXPORT_API`)

## ExportGLTF
`virtual std::vector<std::string> ExportGLTF(const std::string& _filePath, const Marvelous::ImportExportOption& _options, bool _bGLBinary)` (h:126)
- `_bGLBinary` true = .glb, false = glTF separate (json + .bin + loose textures). Return: output file paths (empty vector = failure; stub returns empty).
- 336 delta: signature unchanged. **Doc now states** component selection lists (`patternList`, `buttonList`, `graphicList`, `zipperList`) restrict output to the listed components; all empty = whole scene. Wide variant `ExportGLTFW` mirrors it. (Struct grew: ABI break vs 224.)
- Plugin use (l.1944): `_bGLBinary=false` for `format=gltf`, `scale=0.001`, `bExportGarment = (g_patternsLoaded>0)`, `bExportAvatar=true`.
- FLAGS: `bExportGarment` is derived from the plugin's own counter, not from `GetPatternCount()`; stale counter (e.g. after `NewProject` race, manual CLO edits) silently drops garment. All other options at defaults: `bThin=true` (thin mesh), `weldType=FULLY_UNWELDED`, `bEmbedded=false`, `bSaveInZip=false`, `bExportFabric=false`, `bCreateMetallicRoughnessMap=false`, no unified UV / baked maps, `bSaveColorWays=false`, `bIncludeHiddenObject=false`, no axis conversion. Per-garment export is now possible via `patternList` (not used).

## ExportGLB
`virtual std::vector<std::string> ExportGLB(const std::string& _filePath, const Marvelous::ImportExportOption& _options)` (h:715)
- Same options; return output paths (docs: "Output file paths"). Empty = failure.
- Plugin use (l.1943): same option set as GLTF. `asyncResult.success = !out.empty()`.
- Note: ExportGLB docs list no component-selection statement (only ExportGLTF/ExportGLTFW were updated in 336). Whether ExportGLB honors `patternList` is **undocumented**; `ExportGLTF(path, opts, true)` is the documented route for filtered binary output. Prefer it for per-garment GLBs.

## ExportZPrj (3 overloads; plugin uses `(path, bool)`)
`virtual std::string ExportZPrj(const std::string& _filePath, bool _bCreateThumbnail)` (h:58)
- `_bCreateThumbnail` true also writes a .png beside the .zprj. Return: path; **empty string on error**.
- Plugin use (l.2129 `save-project`): `thumb = (param3 != 0)`; success = `!out.empty()`.
- Fine; no mismatch. Zero-arg overload writes to CLO temp folder.

## ExportAVT
`virtual std::string ExportAVT(const std::string& _filePath)` (h:936)
- Return output path, empty string on error.
- Plugin use (l.618) inside SEH guard (`CallExportAVTOnce`) because it is known to raise access violations. Return is only tested `!empty()`. 336 header has no change. The crash hazard is not documented in SDK.

## GetAvatarCount
`virtual unsigned int GetAvatarCount()` (h:637) - number of avatars loaded in CLO.
- Plugin use (l.2378 `read-avatar-state`) in try/catch. FLAG: comment at `clear-avatars` (l.~1990) says "never ask CLO how many avatars exist - every query API either hangs or crashes on an absent index", yet `read-avatar-state` does exactly that. Inconsistent policy; safe only when avatars exist? Unverified.

## GetAvatarNameList
`virtual std::vector<std::string> GetAvatarNameList()` (h:643) - names of all loaded avatars. Used l.2379 with bounds fallback `avatar_i`. Good (`SetGradingPairedAvatar` needs these names).

## GetAvatarGenderList
`virtual std::vector<int> GetAvatarGenderList()` (h:663) - 0 male, 1 female, -1 unknown. Used l.2380, mapped via `AvatarGenderLabel`. Matches docs (assuming the label function uses this mapping).

---

# PATTERN_API (`PatternAPIInterface.h`, `PATTERN_API`)

## GetPatternCount
`virtual int GetPatternCount()` (h:68) - number of patterns on the pattern editor **and avatar window**. Stub 0. `GetPatternSize()` is the deprecated alias. Used widely (l.269, 482, 1888, 2150...). Ambiguity: "and avatar window" - unclear whether non-fabric objects are counted; plugin treats as garment piece count.

## GetPatternInformation
`virtual std::string GetPatternInformation(int patternIndex)` (h:55) - JSON string. Schema undocumented in header. Plugin parses with nlohmann and passes through (l.2168); falls back to raw string on parse failure. Out-of-range index behaviour undocumented; plugin range-checks first. Good practice.

## GetPatternInputInformation
`virtual std::string GetPatternInputInformation(int _patternIndex)` (h:75) and no-arg overload (h:89, all patterns presumably). JSON; schema undocumented. Plugin l.2202 range-unchecked (no `total` guard, unlike read-pattern-info) -> invalid index behaviour unknown; header says nothing.

## GetBoundingBoxOfPattern
`virtual std::map<std::string,std::string> GetBoundingBoxOfPattern(int _patternIndex)` (h:237)
- "BoundingBox Size each width, height". Map of strings; **keys not documented** (the vector overload says "width, height, pattern index, pattern count"). On error returns an empty map (not an exception). Unit presumably mm (2D pattern space) - undocumented.
- Plugin (l.2185) copies all key/values to JSON, treats `bboxOk=true` even when the map is empty. FLAG: success flag is true for empty map; caller must check for `width`/`height`.

## GetPatternPieceArea
`virtual float GetPatternPieceArea(int _patternIndex)` (h:102) - "pattern piece area"; unit undocumented (likely mm^2, a guess). Returns 0.0 stub/error indistinguishable. Plugin l.2190 passes to JSON.

## GetLineLength
`virtual float GetLineLength(int _patternIndex, int _lineIndex)` (h:108); inner-shape overload `(pattern, childrenIndex, line)` (h:114). Returns line length (unit presumably mm); stub/invalid returns 0.0.
- Plugin l.2227: scans line indices 0..N (default 256) and stops after 12 consecutive zeros; line must be >0.0001 to be reported.
- FLAG: probing by zero-length is a heuristic; a genuine zero-length segment is indistinguishable from out-of-range. `GetPatternLineInfo(patternIndex)` (documented, returns JSON with `lineCount`) gives the true count and was already in 224 (not used).

## GetArrangementList
`virtual std::vector<std::map<std::string,std::string>> GetArrangementList()` (h:321) - avatar arrangement slots (name, type, offset x/y/z, orientation); empty vector on error. Plugin l.472, 2249, 2297, 2347. Keys undocumented beyond the comment text.

## GetArrangementOfPattern
`GetArrangementOfPattern()` (all, h:333), `(int _patternIndex)` (h:345), `(const std::string& name)` (h:357). Returns map of arrangement info for the pattern (Arrangement Name, Type, Offset x,y,z, Orientation); empty on error. Plugin uses the int overload (l.485, 2271, 2303, 2360).

## SetArrangement
`virtual void SetArrangement(int _patternIndex, int _arrangementIndex)` (h:413) - index into `GetArrangementList()`. `void`, no validation/return. Plugin l.2027: only when `param4>=0`.

## SetArrangementPosition
`virtual void SetArrangementPosition(int _patternIndex, int _positionX, int _positionY, int _offset)` (h:397)
- Doc: "positionX, positionY, offset : the value to determine pattern arrangement" - **units and meaning of `_offset` undocumented**, all `int`.
- Plugin l.2028: `(int)floatParam1, (int)floatParam2, (int)floatParam3`; message says "mm". FLAG: header never states mm; `offset` presumably the distance from the avatar surface (z). Float->int truncation loses sub-mm precision. Verify with `GetArrangementOfPattern` (returns "Offset x,y,z").

## SetArrangementOrientation
`virtual void SetArrangementOrientation(int _patternIndex, int _orientation)` (h:405) - enum values undocumented; plugin passes `param5` raw, skipped when 0. `void`.

## SetPatternPieceFabricIndex
`virtual void SetPatternPieceFabricIndex(int _patternPieceIndex, int _fabricIndex)` (h:572) - assigns fabric to a pattern; `void`, no validation. Plugin l.2045 reports success unconditionally. The richer `AssignFabricToPattern(fabricIdx, patternIdx, option)` returns bool (unused).

## AddSeamlinePairGroup (3 overloads)
Used: `bool AddSeamlinePairGroup(int _patternAIndex, int _lineAIndex, int _patternBIndex, int _lineBIndex, bool _directionA, bool _directionB)` (h:1317 declaration at 1320).
- Others: pattern A line <-> inner shape of pattern B (7 args: adds `_childIndex`), inner shape <-> inner shape (8 args).
- Return: bool, false stub. **The doc comments are stale/contradictory**: first says `@return name of sewing group (wide string)` and `@fn ...(…, bool _bReverse)` but the signature returns `bool` and takes two direction flags. Trust the signature.
- `_direction*` : true forward, false backward (stitch direction along the line).
- 336 delta: this signature unchanged. NEW `AddSeamlinePairGroupPartial` (3 overloads) with start/end ratios, returns `int` `SeamlinePairGroupResult` (0 success, -1..-7 failures). Remark: "reports only a status code; to find the new seam diff `GetSeamlinePairGroupListInPattern(_patternAIndex)`". Also 336 note: Pattern editing APIs run the solver afterward in some cases (not stated for AddSeamlinePairGroup).
- Plugin use (l.1899): passes `param3,param4,param5,param6,boolParam1,boolParam2`; success = returned bool. Self-seam (A==B pattern index; sleeve tube) is used (comment l.1876 says it is the leading crash hypothesis).
- FLAGS: (1) docs describe no self-seam behaviour (same pattern both sides) at all; nothing guarantees it is supported. (2) Direction semantics ("forward") relative to line vertex order are undefined; mismatched directions cause twisted seams that simulate badly - not detectable from return. (3) The plugin cannot learn the seam index/name; `GetSeamlinePairGroupCount/ListInPattern` available. (4) `AddSeamlinePairGroupPartial` gives error codes (INVALID_LINE etc.) which would help diagnose the "Failed to create seam" generic message.

## AddGradingSizeGroup
`virtual int AddGradingSizeGroup(bool _bAssignToAllPatterns)` (h:1853)
- Creates a new rule table with a single default size; returns new group index (0-based), **-1 on failure (no pattern editor)**. New table starts with **all avatar slots empty** (does not auto-pair); GUI widgets are not refreshed.
- Plugin use (l.1956 `grading-avatar-size`, experiment): result stored in `group` but never validated/used (-1 not checked).

## SetGradingPairedAvatarFromFile
`virtual bool SetGradingPairedAvatarFromFile(unsigned int _gradingIndex, const std::string& _avtFilePath)` (h:1880)
- Loads .avt **additively** (not replacing scene avatar) and pairs it to grading size `_gradingIndex` (size index, order of `GetGradingSizeNameList`). Replaces an existing pairing. Returns false if no grading table, index out of range, or load fails.
- Plugin use (l.1961): index hard-coded 0; only if `boolParam2 && !param1.empty()`.

## SetGradingPairedAvatarSizing
`virtual bool SetGradingPairedAvatarSizing(unsigned int _gradingIndex, const std::string& _avsFilePath)` (h:1871)
- Loads a .avs file as avatar sizing for that grading size. Requires avatar already paired to that size that is resizable; .avs gender/avatar ID must match; v1/v2 (4.x-era) .avs not supported; applied immediately only if that size is currently selected, else stored and applied on switching; returns false for missing/empty/unsupported file, mismatch, non-resizable avatar, or "table currently suppresses resizing-status updates (sizing silently dropped)" (note: that last case returns false).
- Plugin use (l.1965): index hard-coded 0, success = sized (the final result).
- FLAGS: when `boolParam2` is false the code assumes pairing exists, but `AddGradingSizeGroup` documents slots empty -> sizing returns false. `paired` result is logged but does not gate `sized`. Grading-group index returned by `AddGradingSizeGroup` is not related to size index 0; fine, but intent is implicit. This API is the documented route to apply an .avs (see memory "Step 1 .avs route").

---

# UTILITY_API (`UtilityAPIInterface.h`, `UTILITY_API`)

## Simulate
`virtual bool Simulate(unsigned int _steps)` (h:737) - simulate garment for `_steps` frames using current simulation properties. Return true on success.
- Plugin l.1914: `(unsigned int)cmd.param3`. FLAG: negative `param3` would wrap to ~4 billion steps and hang; no clamp in plugin. Blocking call on main thread for long runs (no progress/timeout in API).

## NewProject
`virtual void NewProject()` (h:451) - clear current garment and start new. `void`. Per plugin comments avatars survive (undocumented); earlier hang attributed to vtable skew. Plugin (l.1973) resets counters except `g_avatarsLoaded`.

## DeleteAvatar
`virtual bool DeleteAvatar(std::vector<int> _avatarIndexList)` (h:1998) - delete avatars by index; bool (stub 0). Doc silent about index shift after deletion (deleting all at once is the safe pattern; the plugin does delete a list in one call).
- Plugin l.2009: indices `0..g_avatarsLoaded-1`. FLAG: relies on a counter that increments per successful import even for replace-imports (see ImportAvatar) and on avatar order; deleting an index that does not exist is documented nowhere (comment says it crashes/hangs). Safer: `GetAvatarCount()` or `GetAvatarNameList().size()` before deleting.

## GetAvatarProperties / SetAvatarProperties
`virtual std::map<std::string,std::string> GetAvatarProperties(unsigned int _avatarIndex) = 0;` (h:2745)
`virtual void SetAvatarProperties(unsigned int _avatarIndex, const std::map<std::string,std::string>& avatarPropertyMap) = 0;` (h:2738)
- Pure virtual in the header (no stub body). Get example keys: `DivideMesh` ('true'/'false'), `KineticFriction` ('0.05'), `SkinOffsetMM` ('3.0'), `SoftBodySimulation` ('true'/'false'), `StaticFriction` ('0.8'). Values are strings. Set example: `{'KineticFriction':'0.05','SkinOffsetMM':'3.0','StaticFriction':'0.8'}`. Unit: key name says MM for skin offset. `void`: no success/failure signal, unknown keys silently ignored (undocumented but implied by plugin's before/after diff).
- Plugin (l.1809-1816): Get before, Set, Get after, then `ComputeChangedPropertyKeys`/`MissingAfterKeys`; reports `success=true` regardless of effect (apart from exceptions). Good defensive design. FLAG: `debugState.unit` ("raw") is recorded but does not convert; any caller sending cm/in for `SkinOffsetMM` will be interpreted as mm.
- These two could not be resolved to vtable slots by name (FINDINGS #7) - ICF folding.

## DisplayMessageBox
`virtual void DisplayMessageBox(std::string str)` (h:34) - modal message dialog in CLO "can be used for debugging". Plugin l.2489, 2569-2580 at startup/menu click. FLAG: modal; blocks the main thread (and timer) until dismissed; do not call from automated paths.

---

# FABRIC_API (`FabricAPIInterface.h`, `FABRIC_API`)

## GetFabricIndexForPattern
`virtual int GetFabricIndexForPattern(int patternIndex)` (h:418); `(int _patternIndex, int _colorwayIndex)` (h:426). Returns fabric index (object-browser) assigned on the pattern. Base stub returns **0**.
- Plugin l.2065/2093/2116: `if (fabric_idx < 0) fabric_idx = 0;`. FLAG: the API never documents a negative error value, and the stub returns 0, so the guard is both unnecessary and cannot detect failure. Colorway-less overload resolves for the current colorway only.

## SetFabricPBRMaterialBaseColor (4 overloads)
Used: `virtual bool SetFabricPBRMaterialBaseColor(unsigned int fabricIndex, unsigned int materialFace, float r, float g, float b, float a)` (h:942).
- `materialFace`: "Front","Back","Side" (docs give strings but param is unsigned; other APIs: 0 Front, 1 Back, 2 Side; `MaterialTargetComponent` COMPONENT_FRONT=0, BACK=1, SIDE=2). Color floats: **range not documented** (0..1 assumed; others in the SDK treat PBR colors as 0..1). Return true on success. Other overloads: colorway-aware, and by color-name string.
- Plugin l.298/400: face `0u` (Front only), `r,g,b` = 0..255 clamped /255, `a=1.0`. Return value is **ignored** (`g_fabricStatus.lastSuccess=true` set unconditionally after the call, l.299). Exceptions caught.
- FLAGS: (1) return value discarded, so a false return still reports "Color applied". (2) Only Front face is set; garment inner side (Back) and Side keep old colors, visible if a GLB renders the inside (thin mesh, two-sided). Consider setting face 1 as well (or check `GetUseSameColorAsFront`, an existing getter). (3) sRGB vs linear is undocumented; passing /255 sRGB values into a linear PBR base color may shift colors. (4) With `PostMessage`, `set-fabric-color` returns success at dispatch time; actual result visible only through `/fabric-status`.

## SetBaseTextureMapImageGivenFilePath (4 overloads)
Used: `virtual void SetBaseTextureMapImageGivenFilePath(const std::string _imageFilePath, int _fabricIndex)` (h:1777): "Set base texture map image for specified fabric". `void`.
- Other overloads: current selected fabric (h:1692); with colorway (h:1786); and `(path&, colorway, fabric, styleChip, materialFace)` returning `std::string` (names of other colorways sharing the fabric; empty path removes texture) (h:2044).
- Plugin l.319/416. FLAGS: (1) `void` return - no failure signal at all, so status reports rely on absence of exception; file validity was only checked by `CLOGuard::fileExists`. (2) The 2-arg overload does not state which material face; likely Front. The 5-arg overload gives explicit face control. (3) Format support (PNG/JPEG) not listed in the header. (4) This API sets the **base color map**, not an AOP/print texture - `set-fabric-graphic` in the plugin uses the same call and therefore *replaces* the fabric base texture; there are separate graphic APIs (`SetGraphicBaseColorMapTexture`, see 09). (5) Colorways: texture changes in colorway may be shared with other colorways (hence the returned string in the 5-arg form). This was unresolved in vtable analysis (ICF fold).

---

# Cross-cutting issues to prioritize

1. `SetFabricPBRMaterialBaseColor`: ignored `bool` return + Front-only face.
2. `ImportDXF`: `m_bAutoScale=true` combined with explicit `m_Scale` (possible double scaling) and `m_bIncludeNotchs=false`; base stub returns true.
3. `AddSeamlinePairGroup`: contradictory docs, undefined self-seam, no error detail; consider `AddSeamlinePairGroupPartial` (336) for diagnosable status codes.
4. `ExportGLB` vs `ExportGLTF(.., true)`: only the latter is documented for component filtering in 336.
5. `GetFabricIndexForPattern < 0` guard cannot trigger (stub/real returns 0).
6. `SetArrangementPosition` ints in unspecified units; truncating cast.
7. `DeleteAvatar` index list driven by a counter that over-counts on replace-imports.
8. `Simulate((unsigned)param3)` with negative values.
9. `ImportFile` 1-/2-arg versions show dialogs (blocking).
10. `AddGradingSizeGroup` -1 unchecked; `SetGradingPairedAvatarSizing` requires pairing the plugin may skip.
