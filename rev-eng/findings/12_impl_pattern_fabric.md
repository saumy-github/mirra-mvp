# Exe implementations: PatternAPI / FabricAPI target functions (lane E)

*Status: static analysis only (dumpbin disassembly), CLO_Standalone_OnlineAuth_x64.exe 2026.1.336*
*Date: 2026-10-29*
*Helpers: `scripts/disasm_fn2.py`, `calls_view.py`, `slice.py`, `rd.py`, `iat_name.py`, `fab_scan.py`. Cached disassembly: `raw/disasm2/`. Slot to log-name table: `raw/disasm2/_pattern_slot_names.txt`, `_fabric_slot_names.txt`.*

All addresses are RVAs (VA = 0x140000000 + RVA). Confidence: H = read directly from code, M = read from code plus one inference, L = inferred from structure only.

## 0. Corrections to earlier findings (read first)

1. **Overloaded virtuals are in REVERSE declaration order** in the MSVC vtable. Confirmed from the exe's own log strings and bodies:
   - slot 8 = `GetPatternInputInformation(void)`, slot 9 = `(int)`
   - slot 13 = `GetLineLength(int,int,int)` (pattern, child shape, line), slot 14 = `(int,int)` (pattern, line)
   - slot 24 = `GetBoundingBoxOfPattern(string)`, 25 = `(int)`, 26 = `()`
   - slot 35 = `GetArrangementOfPattern(string)`, 36 = `(int)`, 37 = `()`
   - slot 50 = `GetFabricIndexForPattern(int,int)` (pattern, colorway), slot 51 = `(int)`
   - slot 161 = `AddSeamlinePairGroup` 8-arg (patA, childA, lineA, patB, childB, lineB, dirA, dirB); 162 = 7-arg; 163 = 6-arg (patA, lineA, patB, lineB, dirA, dirB)
   - Fabric `SetFabricPBRMaterialBaseColor`: 113 = (uint,uint,uint,const string&), 114 = (uint,uint,const string&), 115 = (uint,uint,uint,float x4), 116 = (uint,uint,float x4)
   Finding 06 assumed `slot == declaration index` for overload groups. That is wrong for overloads; the names above come from the exe's log strings (`fab_scan.py`).
2. **The slot numbers listed in the task for `SetBaseTextureMapImageGivenFilePath` (205, 217, 218, 247) are wrong.** Per the log strings those slots are `GetRoughnessMapImageFilePathW(int,int)` (205), `SetNormalMapImageGivenFilePath` (217, 218) and `SetRoughnessMapImageGivenFilePathW` (247). The real ones are:
   - 211 `string SetBaseTextureMapImageGivenFilePath(const string&,int,int,int,int)` at 0x6044000
   - 212 `(const string,int,int)` at 0x60451f0
   - 213 `(const string,int)` at 0x6044f10
   - 214 `(const string)` at 0x6044c80
   - 235/236/237 the `...W(const wstring,...)` forms at 0x60459c0 / 0x6045720 / 0x60454d0
   `findings/06` rows for these four "header order" entries should be treated as wrong (and so is the row's "SetBaseTextureMapImageGivenFilePath 205/217/218/247" mapping in `findings/04` if it came from the same source).
3. **Grading functions are NOT implemented in the exe's PatternAPI.** PatternAPI vtable slots 196-220 (25 contiguous slots) are `jmp [IAT]` stubs (bytes `ff25 ...`, RVAs 0x648f10f.. step 6) that import the SDK base-class methods from `CLOAPIInterface.dll`. Via the import table (`scripts/iat_name.py`) they are: 196 SetGradingPairedAvatar, 197-200 Get/SetGraphicGrading{ScaleRatios,PositionOffsets}, 201 AddGradingSize, **202 AddGradingSizeGroup**, 203 ImportGradeRuleToSizeGroup, **204 SetGradingPairedAvatarSizing**, **205 SetGradingPairedAvatarFromFile**, 206 CutPatternAlongInternalShapes, 207 MergeSewnPatterns, 208 GetPatternInternalShapePoints, 209 GetPatternBaselinePoints, 210 AddButtonToPattern, 211 AddButtonHoleToPattern, 212 TraceBaselineAsInternalShape, 213-216 Get/SetButton(Hole)GradingPositionOffsets, 217 ActivateAllPatterns, 218 GetPatternOutlinePoints, 219-220 Get/SetPattern(Point)GradingPositionOffsets. Slots 221-233 are real exe code. FabricAPI, ExportAPI, ImportAPI and GuiAPI have no such stubs. Utility has 5 (388, 397..400) and Rest has 7 (4,5,9,10 + 3), which are outside this lane.

## 1. Shared infrastructure (used by almost every function below)

| Helper | RVA | Meaning | Conf |
|---|---|---|---|
| global scene accessor | 0x1bf5e20 | returns address of a global singleton (.data 0xa2a5348, TLS-guarded lazy init) | H |
| `5cfe9f0(global, out)` | 0x5cfe9f0 | copies the shared_ptr stored at global+8/+0x10 into `out` = "current document/scene" | H |
| null checks | 0x1c09700, 0x1c09730, 0x1d68bd0, 0x1d68be0, 0x2398d00, 0x42dfb70 | `cmp qword [x],0 ; sete al` (shared_ptr is empty) | H |
| `56e5930(scene, vec&, excl=0)` | 0x56e5930 | builds `vector<shared_ptr<Pattern>>` (16-byte elements) from the vector at **scene+0x5C0..+0x5C8**, keeping only entries for which `474dcc0(p)` is true. With `excl==0` there is no exclusion list. This is the canonical **pattern list** | H |
| `474dcc0(pattern)` | 0x474dcc0 | predicate "is a normal pattern piece": true only if `4749c70(p)`, virtual `+0x8F8`, `474f3c0(p)`, virtual `+0x900` and virtual `+0x68` are all false. The exact exclusions (probably internal/hidden/trim/guide objects) were not decoded | M |
| `60b1f10(this,out,idx)` **GetPatternByIndex** | 0x60b1f10 | scene null -> null. Builds the list above, then `0 <= idx < size` ? element[idx] : null. **0-based, no clamping, out of range gives null shared_ptr** | H |
| `60b1e50()` | 0x60b1e50 | count of that list = GetPatternCount | H |
| `60abbb0(this,out,patIdx,childIdx)` | 0x60abbb0 | pattern by index, then child (inner) shape from vector at **pattern+0x238..+0x240** with `0 <= childIdx < size` | H |
| `60af6f0(this,out,shapePtr,lineIdx)` | 0x60af6f0 | line/edge by index: `shapePtr` empty or `lineIdx<0` -> null; else vector accessed via `434d770(shape)` (+8..+0x10, 16-byte elements) with `lineIdx < size` | H |
| log wrapper | 0x4e10dd0, 0x4e10fb0 | most API entry points start with a scoped logger that stores the signature string (e.g. `"int __cdecl Marvelous::PatternAPI::GetPatternCount(void)"`) and then run the body. Useful for identifying slots | H |

Consequence: **every `patternIndex` accepted by the PatternAPI functions below is an index into the filtered `scene+0x5C0` list, 0-based, in vector (creation/load) order.** This is the same list `GetPatternCount` counts. Whether this list is the one the task called "RealPatternList" was not named in the exe (no symbols); it is the only pattern list used, so it is almost certainly it (M).

## 2. PatternAPI

### GetPatternCount (slot 7, 0x6001e40 -> impl 0x60b1e50)
Log wrapper, then `return count(56e5930 list, excl=0)` = `(end-begin)>>4`. No scene -> 0. (H)
Evidence: 0x60b1e62-0x60b1ebf, wrapper call at 0x6001fd0.

### GetPatternInformation(int) (slot 5, 0x6005520)
Builds a serializer context, then `4101660` (collects the pattern list into a selection vector at ctx+0x208, same 56e5930 filter) and `413c260(ctx, idx, ...)` produces a JSON (nlohmann-style, "cannot use push_back() with" strings) object for ONE pattern, converted to std::string by `6668370`.
- Index validation: inside 0x413c260: `idx >= 0 && idx < size(vec at ctx+0x210)`, else jumps to 0x413e274 (error/empty path). 0-based into the same list. (H)
- JSON keys seen (strings in 0x413c260, cached `raw/disasm2/_patinfo_full.txt`): name, itemNo, isTrimItem, isSeamlessBlock, uuid, trimType, loadedUuid, thumbnail (file `pattern2d_<..>.png`), symmetryPatternId, isHalfSymmetric, instanceLinkedPatternIdList, layerCloneOverIdList, layerCloneUnderIdList, allLinkedPatternIdList, annotation, bonded, bondType, **consumptionArea**, matMeshIdList, **boundingBoxList**, markerList, **fabricId**, fabricMaterialId, buttonHead*/buttonHole*/graphic* (patternTopToGraphicCenter ... customGraphicMeasurements, placement), topStitch* (type, length), zipperLength, zipperInstanceList, trim*, printFabric_/styleChip thumbnails. (H)
- `consumptionArea = areaFn(...) * 1e-6f` (constant 0x833a9d4 = 9.99999975e-07 at 0x413d765). The area function used is the same `pattern+0xCC8` virtual `+0x38` as GetPatternPieceArea (see below; 0x4139350 also looks up a per-fabric override map at ctx+0x2F8 first). So CLO reports consumption in m2 from an internal value in **mm2**. (M - the mm2 conclusion is an inference from the 1e-6 factor)
- `fabricId` = `413bf20(ctx, fabricRef)`: null -> -1; else `*(int*)(fabric+0x10)` or `+0x14` depending on `ctx+0x48` (2 modes). So the JSON `fabricId` is a stored fabric id, not necessarily the Object Browser order index. (M)

### GetPatternInputInformation (slots 8 `()` 0x6005cf0, 9 `(int)` 0x6005ad0)
- 8 -> impl 0x60b2220; 9 -> impl 0x60b2070. Both: scene null -> empty string (0x6665010).
- `()`: builds the full filtered list (56e5930) and calls `56dae10`.
- `(int)`: `60b1f10(idx)` (0-based); if null pattern -> empty string; else single-element vector -> `56dae10`.
- 0x56dae10/0x56daef0 build JSON: top-level key `"Pattern InputInformation"`, per pattern (0x472cb50): `Pattern name`, `Pattern index`, `Children shape count`, `InnerShape` / `Children Information` (`Shape name`, `Shape index`, `Binding Shape`, `Hole Shape`, `Base Line`, `Reference Line`, `Shape type`). No numeric unit conversion (no mul/div). (H)

### GetPatternPieceArea(int) (slot 12, 0x6008bb0)
```
p = GetPatternByIndex(idx)            // 0x60b1f10, 0-based
if (p == null) return 0.0f            // path at 0x6008d5f-0x6008d64 skips the call, xmm6=0
a = (p + 0xCC8)->vtbl[+0x38]()        // 0x6008d6c-0x6008d76, float
if (a <= 1e-5f) a = 0.0f              // constant 0x82703c0 = 9.99999975e-06
return a
```
- Computed from a stored/derived geometry object on the pattern (2D pattern data), not from the draped 3D mesh. No scene mutation, no solver. (M - what the +0xCC8 object is was not decoded; it is embedded in the pattern, so it is pattern-owned 2D data)
- **Unit: mm2 (inferred, M).** The same value is multiplied by 1e-6 for the JSON `consumptionArea` (m2). It is not cm2 (that would be 1e-4). Nothing in the function converts units, so the SDK returns the internal value as is. Negative/tiny values clamp to 0.
- Out-of-range index returns 0.0 silently (same as a degenerate piece). (H)

### GetLineLength (slot 14 `(patIdx,lineIdx)` 0x5ff3470; slot 13 `(patIdx,childIdx,lineIdx)` 0x5ff3750)
```
p    = GetPatternByIndex(patIdx)                 // 0x60b1f10
line = p.outlineLine[lineIdx]  (slot13: child shape's line via 60abbb0 + 60af6f0)
if (p==null || line==null) return 0.0f
M    = 3e916d0(p)                                // 2D affine of the pattern, composed with parent chain
return 5277b80(line, M)                          // length of the polyline/segment after M
```
- 5277b80: if `52b2f30(line)` (straight: control-point vector `+0x388..+0x390` has < 2 entries / flag) -> transform the two end points (point object `+0x2EC` = x,y floats; 2x3 matrix: `x' = x*m[0]+y*m[3]+m[6]`, `y' = x*m[1]+y*m[4]+m[7]`) and return `sqrtss(dx^2+dy^2)`; otherwise (curve) sum the transformed segment lengths over the point vector at `+0x388`. (H for structure, M for the curve branch)
- **Computed in 2D pattern space** (x,y only, no z, no 3D mesh, no simulation state). `3e916d0` builds the matrix from the pattern's own 2D placement data (`pattern+0x264`) and parent (`+0x218/+0x220`); a rigid matrix preserves length, so this is effectively the seam-line length in the 2D pattern unit. Whether the matrix contains a unit scale was not decoded (L).
- **Unit: almost certainly the 2D internal unit (mm).** No conversion inside the function. Not proven independently for lengths; area evidence above implies a mm internal unit (M).
- Index validation: pattern null or line null -> returns 0.0f. Line index `<0` or `>= size` -> null -> 0.0f. 0-based. (H)
- Note: the line list is the pattern's **outline** edge list (`434d770(shape)`) in definition order, not a sewn-seam order.

### GetBoundingBoxOfPattern (slots 24 string, 25 `(int)` 0x5fd9460 -> impl 0x60aad60, 26 `()` 0x5fd96a0)
Returns `map<string,string>` with keys `"PatternIndex"`, `"PatternName"`, `"Width"`, `"Height"`.
- Pattern by `60b1f10(idx)` (0-based); null -> map left EMPTY (path 0x60aae47 not taken; function returns the empty map). (H)
- `Width = |box[+8] - box[+0x10]|` of the rect stored at **pattern+0x7F8** (0x436d070, `andps` abs); `Height` via 0x434abe0 on the same rect. Both are formatted with the printf format at 0x847de80 = `"%f"` (6 decimals) via 0x38adbd0. (H)
- It is a **2D pattern-space** axis-aligned box stored on the pattern, not a draped 3D box. The unit is the internal 2D unit, no conversion (mm, M). The values are strings.
- The name variant (slot 24) resolves name -> index by scanning the same filtered list (0x60b26c0, string compare) and then uses the same builder (0x60aa900). `()` loops over `GetPatternCount()` entries.

### GetArrangementList (34, 0x5fd2880) / GetArrangementOfPattern (35 string, 36 `(int)`, 37 `()`)
Each arrangement entry is a `map<string,string>` (0x60a9e50 builds the `Arrangement*` keys; 0x60aa900 adds `PatternIndex/PatternName/Width/Height` for the pattern on that slot). Keys: `ArrangementName`, `ArrangementType` (`"Flat"` or `"Curved"`, from int at arrangement `+0x290`), `ArrangementIndex`, `ArrangementOffsetX/Y/Z`, `ArrangementOrientation`, `PatternIndex`, `Width`, `Height`, `PatternName`.
Arrangement offsets are **not millimetres**; they are 0-100 normalised slider values derived from float fields of the arrangement object:
- `OffsetX = 50 - trunc(-100 * f(+0x294))` = `50 + trunc(100*f)` (0x4fd1790)
- `OffsetY = 50 - trunc(-100 * f(+0x298))` (0x4fd17c0)
- `OffsetZ = (trunc(f(+0x29C)) + 100) >> 1` (0x4fd1890; f range -100..100 -> 0..100)
- `ArrangementOrientation = trunc(f(+0x2A0)) + 180` (0x60aa692; degrees, 0..360)
(H). `GetArrangementOfPattern(int)` (36, 0x5fd2ef0) = `60aa900(scene, out, patIdx)`; pattern null -> empty map; the arrangement is found through `470e810(pattern)` (pattern's current arrangement). Index = same 0-based list. (H/M)

### SetArrangementPosition(int pat, int x, int y, int z) (slot 41, 0x603d730)
Silent no-op (void) unless the pattern exists AND `x <= 100 && y <= 100 && z <= 100` (unsigned compares at 0x603d8ff/0x603d908/0x603d912, so negative values also fail). Then `470e810(pattern)` -> arrangement; setters 0x4fd9460/0x4fd9480/0x4fd94d0 apply X, Y, Z (inverse of the getters above, i.e. 0-100 slider coordinates). No simulation call. (H)

### SetArrangementOrientation(int pat, int angle) (slot 42, 0x603d4f0)
No-op unless pattern exists and `angle <= 360` (unsigned `cmp edi,168h; ja`). Stores `(float)(angle-180)` via 0x4793520(pattern, f, true). Input 0-360 maps to -180..+180. (H)

### SetArrangement(int pat, int arrangementIdx) (slot 43, 0x603d060)
Pattern by index (0-based, null -> no-op). Arrangement list from the global (0x1bf5d20 -> 0x50d1640 etc.); `0 <= arrangementIdx < size` else no-op (0x603d354-0x603d368). Assigns via `47935f0(pattern, arrangement, 0, true)` (virtual `pattern+0x838` is used to fetch the pattern's current arrangement for the swap). Not validated further. (M)

### SetPatternPieceFabricIndex(int pat, int fabricIdx) (slot 62, 0x6064db0)
`p = 60b1f10(pat)`; null -> return (void, no error). Else `57d32b0(scene, p, fabricIdx)` (large function, ~0x700 bytes, collects the pattern into a vector, applies the fabric to it and runs the scene update). Fabric index bounds are checked inside 57d32b0 against the document fabric list (not decoded in detail). Index base of `fabricIdx`: same fabric order as GetFabricIndexForPattern returns (see Fabric). (M)

### AddSeamlinePairGroup (161/162/163 = 0x5f93d70 / 0x5f94000 / 0x5f942d0)
Slot 161 (8 arg): `A = 60abbb0(patA, childA)`, `B = 60abbb0(patB, childB)` (child vectors at pattern+0x238), then `lineA = 60af6f0(A, lineA)`, `lineB = 60af6f0(B, lineB)`; if either is null -> return **false**. Otherwise `55d5dd0(scene, out, lineA, lineB, dirA, dirB)` creates the sewing and returns **true** (sil=1 at 0x5f93ec9). Scene null -> false. Slot 163 (6 arg) uses `60b1f10` for both patterns and `60af6f0` directly on the pattern outline (3e72d80 fetches the outline container). All indices 0-based; direction bools are passed through unchanged. Invalid index = return false, no exception. The call 55d5dd0 -> 55d5f80 validates the two lines belong to editable shapes and appends a sew pair (not decoded further). (H for control flow, L for what 55d5dd0 validates)
Note: SDK 336 header says the return is the "name of sewing group" but the exe returns bool.

### AddGradingSizeGroup (202), SetGradingPairedAvatarSizing (204), SetGradingPairedAvatarFromFile (205)
**Not implemented in the exe.** The vtable entries are import thunks (RVA 0x648f127, 0x648f133, 0x648f139: `jmp [0x14822B510 / 0x14822B500 / 0x14822B4F8]`) into `CLOAPIInterface.dll` exports `?AddGradingSizeGroup@PatternAPIInterface@CLOAPI@@UEAAH_N@Z`, `?SetGradingPairedAvatarSizing@...`, `?SetGradingPairedAvatarFromFile@...`. Those DLL functions are the base-class stubs (per `findings/01` / Key finding 1): `AddGradingSizeGroup` returns **-1**, the others return **false**. Therefore, in this build, calling them through the exe-provided PatternAPI vtable just returns the failure value and does nothing; no avatar lookup exists to analyse. (H, 3-for-3 thunk target verified via import table, see `scripts/iat_name.py`). This applies to all of slots 196-220 (list in section 0).
Caveat (L): this is what the 336 exe's *PatternAPI object* has. A plugin built with a newer SDK would hit the same stubs; if CLO ships these features in a later build, the exe vtable would change.

## 3. FabricAPI

### GetFabricIndexForPattern (slot 50 `(int pat,int colorway)` 0x5fe4d90; slot 51 `(int pat)` 0x5fe4a50)
- slot 51: `r14d = 0` (default). Scene null/empty -> 0. Builds the pattern list (56e5930, excl=0), `pat >= 0 && pat < size` else result stays **0**. Gets the pattern's fabric reference via pattern virtual `+0x878`, then `60ad0d0(fabricRef)`: null -> 0; else `4988a30(fabric)`, if negative `4988940(fabric)`, if still negative -> 0. Returns that index. (H)
- slot 50: same with colorway: `49fadc0(colorwayContainer, colorwayIdx)` null -> default; `49fb610(colorway, patternRef)` -> fabric ref -> `60ad0d0`. Default result **-1** in this overload (`ebx=-1` at 0x5fe4f3d) when the scene/colorway/pattern is invalid, but **0** on `60ad0d0` failure. (M)
- 0-based indices for both pattern and colorway. Since failure inside `60ad0d0` yields 0, a returned 0 is ambiguous (valid first fabric vs unresolved). Index base of the result: `4988a30` is a position in the document fabric list (Object Browser order, 0-based; M).

### SetFabricPBRMaterialBaseColor (113/114/115/116 = 0x604e000 / 0x604dcb0 / 0x604e350 / 0x604e5e0)
All return bool. Parameters: fabric index (unsigned), then optionally colorway index (unsigned, the "3 uint" forms 113/115), then a color: `const string&` (113, 114, hex-like string) or four floats (115, 116, r,g,b,a).
- String form (114, 0x604dcb0): parse color string `39d1da0`/`1ba82a0` (components via `39d58d0`, `39d5ee0`, `39d6570`), `60b1300(...) == 1` validity check, else return false (0x604dee1-0x604dee3); gets fabric via `49ffd90`/`49fb510` (fabric list, index), applies via `60ac160` then `60f9480` (material update). Returns true when the fabric object was found and set. (M)
- Float form (116, 0x604e5e0): the four floats are clamped/scaled using constant vectors at .rdata 0x897e620/0x897e630/0x897e640 (not decoded), then material update `60ae0f0`/`61543e0`. (L)
- The first uint is a fabric index in Object Browser order (0-based, same `49ffd90` list used by GetFabricIndex*). Invalid fabric index -> false, no change. (M)

### SetBaseTextureMapImageGivenFilePath (real slots 211-214; 0x6044000 / 0x60451f0 / 0x6044f10 / 0x6044c80)
Not the slots from the task. 214 `(const string path)`: constructs a context (0x1bdd3c0), copies the path (0x66668a0), picks the current fabric through `49ffd90`/`49fb510` (current/selected fabric), loads the image through `6664e10` and applies with `60fafe0`; the whole body is the same shape as `SetNormalMapImageGivenFilePath` (0x605c020). 213 adds a fabric index, 212 adds colorway, 211 adds more ints and returns a string (error text / result). The string is a plain narrow path; no unit logic. Failure behaviour (missing file, invalid fabric index) was not decoded. (L)

## 4. Unit and index conventions for the Mirra half-girth / seam pipeline

| Item | Finding | Conf |
|---|---|---|
| Pattern index base | 0-based, into the filtered `scene+0x5C0` list in vector order (`GetPatternCount` counts the same list). Applies to Information, Area, LineLength, BoundingBox, Arrangement*, SetPatternPieceFabricIndex, AddSeamlinePairGroup, GetFabricIndexForPattern | H |
| List membership | Only entries passing `474dcc0` (excludes some special objects, probably trim/internal/hidden). Indices are not a plain "all objects" index | M |
| Out of range | Pattern functions return 0.0f / empty map / empty string / false / no-op. `GetFabricIndexForPattern(int)` returns 0 (ambiguous with a valid index 0) | H |
| Child (inner shape) index | 0-based, vector at pattern+0x238; line index 0-based in the shape's outline vector | H |
| `GetPatternPieceArea` unit | internal value returned unchanged, clamped to >= 1e-5; **mm2** inferred (ratio 1e-6 to m2 used for `consumptionArea`) | M |
| `GetLineLength` unit | 2D polyline length in the pattern's internal 2D unit, **mm** inferred; 2D only (x,y), no 3D / simulation dependence | M |
| `GetBoundingBoxOfPattern` | 2D box stored on pattern (+0x7F8), `%f` strings, same internal unit; keys PatternIndex, PatternName, Width, Height | H |
| Arrangement offsets | 0-100 normalised, orientation 0-360 (stored -180..180). Not mm/cm | H |
| Grading APIs | Not implemented in this exe: no-ops returning -1/false | H |
| Slot numbers | Overloads are in reverse declaration order; trust the names in `raw/disasm2/_*_slot_names.txt`, not `findings/06` "header order" rows | H |

Practical consequences for the half-girth pipeline (inference): the 2D lengths reported by `GetLineLength` are in the same unit as the pattern coordinates CLO imports from DXF (mm if the DXF/block builder writes mm, M); the area is mm2; outline edges are in definition order, so a seam-length lookup must map the plugin's `edge index` to outline order, not to sewing order. Do not rely on `AddGradingSizeGroup` / `SetGradingPaired*` for this build.

## 5. Not done / limits
- Virtual objects (`pattern+0xCC8` vtable `+0x38`, `0x3e916d0` matrix content, `0x57d32b0` fabric validation, `0x55d5dd0` seam validation) were not followed beyond the first level; unit conclusions rest on constants (1e-6, 1e-5, 100, 180) and field arithmetic.
- No runtime check; confidence H/M/L above is static-only.
