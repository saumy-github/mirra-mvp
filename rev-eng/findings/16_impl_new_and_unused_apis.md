# Real implementations of new / unused-but-useful APIs (CLO 2026.1.336)

*Status: lane I, static disassembly only (dumpbin), nothing executed or hooked. Facts = read from instructions; INFERENCE = labelled.*
*Date: 2026-10-29*
*Target: CLO_Standalone_OnlineAuth_x64.exe 2026.1.336 (image base 0x140000000). All addresses are RVAs unless a full VA is shown.*
*Tools: scripts/slots_lookup.py (slot/RVA from the grouped model), scripts/disasm_fn3.py, scripts/fn3_brief.py (refcount noise removed). Caches: raw/disasm3/.*

## 0. Method correction: in-group overload order is REVERSED declaration order

The slot model in `scripts/abi_check.py` groups overloads of one name contiguously at the first declaration. It does not check order inside the group. Reading the bodies (each wrapper embeds its own `__FUNCSIG__` string) shows that **MSVC lays the overloads out in reverse declaration order** inside the group. Evidence:

| group | slot -> real signature (from embedded FUNCSIG string) |
|---|---|
| AddSeamlinePairGroupPartial | 164 = (pA,cA,lA,sA,eA,dA,pB,cB,lB,sB,eB,dB) [header decl #3]; 165 = (pA,lA,sA,eA,dA,pB,cB,lB,sB,eB,dB) [decl #2]; 166 = (pA,lA,...,pB,lB,...) [decl #1] |
| ExportStdViewImage | 105 = 6-arg `(int,const string&,int,int,int,bool)` @0x5fc3e00; 106 = 5-arg @0x5fc3b00 |
| GetFabricPBRMaterialBaseColor | 117 = `(uint,uint,uint)` colorway/fabric/face @0x5fe9420; 118 = `(uint,uint)` @0x5fe91d0 |
| SetGraphic*MapTexture | 219 BaseColor(str,int,int), 220 BaseColor(str,int), 221 Normal(uint,str), 222 Normal(str), 223 Disp(uint,str), 224 Disp(str), 225 Opac(uint,str), 226 Opac(str), 227 Rough(uint,str), 228 Rough(str), 229 Metal(uint,str), 230 Metal(str) |

Consequence: the slot **set** per name in findings/14 stays correct (and the plugin, compiled by MSVC against the same header, dispatches correctly). Only when mapping slot -> a specific overload by hand must the order be reversed. `abi_check.py` could add this as a stricter check (overload i of n -> slot first + n-1-i) using the embedded FUNCSIG strings.

Also: every API wrapper starts with the same logging prologue (`0x4e10dd0` get logger, `0x4e10fb0(logger, level 0/2/4, FUNCSIG string, ...)`), so each call is logged by CLO with its full signature text. FUNCSIG strings are the most reliable way to identify a slot in this exe.

## 1. Slot table (grouped model + reversal, all verified against FUNCSIG strings or header doc)

| class | function | slot(s) | exe RVA |
|---|---|---|---|
| Pattern | AddSeamlinePairGroupPartial | 164,165,166 | 0x5f94610, 0x5f94a30, 0x5f94e20 |
| Pattern | GetAllPatternToAvatarMeasures | 224 | 0x5fd1170 |
| Pattern | GetPatternToAvatarMeasureByAvatar / ByPatterns / ByMeasures | 225 / 226 / 227 | 0x600aed0 / 0x600b7f0 / 0x600b570 |
| Pattern | SetPatternEdgeToAvatarMeasure | 228 | 0x6062710 |
| Pattern | GetPatternEdgeToAvatarMeasureAttachment | 229 | 0x6002000 |
| Pattern | GetHiResTolerance / SetHiResTolerance | 222 / 223 | 0x5ff1900 / 0x6055890 |
| Pattern | FlipPatternNormal | 230 | 0x5fcd810 |
| Pattern | GetPatternComponents | 184 | 0x6000880 |
| Pattern | GetPatternGroupsBySeamlineConnectivity | 185 | 0x6002800 |
| Pattern | GetPatternLineInfo | 194 | 0x6006540 |
| Export | ExportThumbnail2D | 28 | 0x5fc53a0 |
| Export | ExportStdViewImage | 105 (6-arg), 106 (5-arg) | 0x5fc3e00, 0x5fc3b00 |
| Utility | GetActiveWorkspaceFileName / ...W | 6 / 7 | 0x5fd0890 / 0x5fd0bb0 |
| Utility | GetAvatarMeasurements | 401 | 0x5fd4180 |
| Utility | SetGraphic*MapTexture | 219..230 (table above) | 0x6050320, 0x60505d0, 0x6051700... |
| Fabric | GetFabricPBRMaterialBaseColor | 117 (3-arg), 118 (2-arg) | 0x5fe9420, 0x5fe91d0 |

Note: `SetGraphic*MapTexture` is in **UtilityAPI**, not FabricAPI (findings/09 filed it under Fabric).

## 2. AddSeamlinePairGroupPartial (NEW in 336)

Common helpers (all RVAs):
- `0x60fdf00(start:xmm0, end:xmm1)` ratio validator: returns **-5** if either is non-finite (exponent bits all 1, i.e. NaN/Inf) or `< 0.0` or `> 1.0` (constant 1.0f at 0x82703f8); else returns **-6** if `start >= end`; else 0. Direction flag is not involved.
- `0x1bf5e20` + `0x5cfe9f0`: fetch the pattern editor (shared_ptr); empty -> **-1**.
- `0x60b1f10(this,&out,int idx)`: pattern by index. Builds the "real pattern list" (`0x56e5930`) and returns element if `0 <= idx < size` (elements are 16-byte shared_ptr pairs), else empty. **0-based.**
- `0x60abbb0(this,&out,patIdx,childIdx)`: inner shape: pattern at `[pattern+0x238 .. +0x240)` (vector of 16-byte shared_ptr), same `0 <= idx < size` check, empty otherwise. **0-based.**
- `0x60af6f0(this,&out,shapeOrPattern,lineIdx)`: line of an outline / inner shape via `0x434d770(shape)->[+8..+0x10)` (16-byte elements), `0 <= idx < size`. **0-based**, ordering "matches GetLineLength / DeleteLine" per header.
- `0x55d5f80(editor, shapeA, lineA, startA, endA, dirA, shapeB, lineB, startB, endB, dirB)`: creates the stitch; returns bool.

Validation order (identical in all three overloads; verified in 0x5f94610, 0x5f94a30, 0x5f94e20):

```
r = validate(startA,endA); if r != 0 return r        # -5 RATIO_OUT_OF_RANGE or -6 EMPTY_SEGMENT (A checked first)
r = validate(startB,endB); if r != 0 return r
editor = GetPatternEditor();      if null return -1  # NO_PATTERN_EDITOR  (needs a project scene)
pA = pattern(patA); pB = pattern(patB)               # (164 skips fetching pB if pA is null; same result)
if pA null or pB null return -2                      # INVALID_PATTERN
[164]  shapeA = innerShape(pA,childA); shapeB = innerShape(pB,childB); either null -> -3 INVALID_INNER_SHAPE
[165]  shapeB = innerShape(pB,childB) null -> -3
lineA = line(...); lineB = line(...); either empty -> -4   # INVALID_LINE (line fetched on the shape or the pattern outline)
ok = CreateStitch(...) ; if !ok return -7                  # CREATE_FAILED
return 0                                                   # SUCCESS
```

Facts worth knowing:
- Ratio checks run **before** the editor check, so bad ratios return -5/-6 even with no project open (and -1 is only seen with valid ratios).
- `_directionX` is only a flag for validation: `-6` still requires `start < end` even for backward direction. In `0x55d5f80` the direction flag decides argument order (INFERENCE from the two code branches at 0x455D6080 / 0x455D612A: for `dir=true` it passes (start,end), for `dir=false` it passes (end,start) plus the flag byte, to the virtual at `[vtbl+0x40]` of each shape). Ratios are used verbatim (header: no notch snapping), 0 = line start, 1 = line end, fractions of the line length (not mm).
- Index bases: pattern, child (inner shape) and line indices are all 0-based, bounds `0 <= i < count`. Out-of-range pattern -> -2 (not -4), out-of-range child -> -3, out-of-range line -> -4. No distinction between "A bad" and "B bad".
- The generic plugin `AddSeamlinePairGroup` returns bool only; Partial gives a typed reason. The call itself returns only a code; the new seam's index is found by diffing `GetSeamlinePairGroupListInPattern(patternA)` before/after (header remark).
- Does not run the solver itself (no Simulate call seen in these bodies); header confirms "call from the scene-owning thread".

**Recommended use for Mirra.** Use the 10-arg (outline-outline) form as the preferred seam call in Step 3, with ratios `(0.0,1.0)` for a full-edge seam, and branch on the returned code instead of the single generic "Failed to create seam" message: -2/-4 mean our panel/line index mapping is wrong (log pattern and line names), -5/-6 mean our own ratio maths is wrong, -7 means CLO refused the geometry (e.g. already stitched or incompatible lines). Use ratio pairs only where a real partial seam is needed (pocket openings, darts, side-seam splits). Keep a fallback to `AddSeamlinePairGroup` only if the Partial call returns -7 on a full-edge request.

## 3. Pattern to avatar-measure family (NEW in 336)

Not disassembled to the data-structure level (time budget); facts from slot/FUNCSIG identification and one deep read of the setter.

### SetPatternEdgeToAvatarMeasure(patIdx, lineIdx, const string& measure, bool attach) @0x6062710, returns bool
Order of checks (facts from the call sequence, boolean meaning from header):
1. pattern editor present (`0x1bf5e20/0x5cfe9f0`) else false;
2. a second scene precondition (`0x1be0dc0 -> 0x5cba300 -> 0x1c09670`, INFERENCE: avatar / measure container present) else false;
3. `0x60b1f10` pattern by index (0-based, `0<=i<size`), null -> false;
4. `0x60af6f0` outline line by index (0-based, same ordering as GetPatternLineInfo / GetLineLength), null -> false;
5. `0x60a8410(this, measureString, avatarList)` resolves the measure by name **or by decimal index string** to an index; negative -> false (header: height/linear measures rejected; the attach branch additionally calls `0x60c1340` which returns false for unsupported measure kinds);
6. attach: builds a Line Pin (`0x54af680`) and executes it through the command manager `0x3b24740` (undo-able); detach branch at 0x62C3E removes it, false if the edge is not attached to that measure. The solver is then run (header says "runs the cloth solver afterwards"), so a Simulate call is not needed.
There is no validation of `lineIdx` that distinguishes "not an outline" from "out of range"; all failures are plain false.

### Getters (GetAllPatternToAvatarMeasures, GetPatternToAvatarMeasureBy*, GetPatternEdgeToAvatarMeasureAttachment)
Identified by FUNCSIG/slot only. Documented behaviour (header): results are `vector<pair<patternName, measureName>>` de-duplicated and sorted by pattern then measure, so same-named patterns collapse; an **empty input list selects nothing** (not "all"); `ByAvatar` uses a 0-based avatar index; `GetPatternEdgeToAvatarMeasureAttachment` returns JSON `{"is_attached":bool,"line_index":N}` with `-1` when absent. Not independently verified in disassembly.

**Recommended use for Mirra.** This is the only API that makes the garment follow an avatar measure inside CLO (a Line Pin on, say, a waistband edge to the waist measure). It is attractive for Step 3 only after Step 1 proves that the avatar measures really change per user (see memory note: exported GLBs identical across users). Plan: (1) `GetPatternLineInfo` to find the waist/hem line by `location`/`orientation`, (2) `SetPatternEdgeToAvatarMeasure(..., "Waist", true)`, (3) read back with `GetPatternEdgeToAvatarMeasureAttachment`. Because measures are circumference values on the avatar, pins make the waistband stretch/shrink to the avatar measure rather than to the Mirra size table, so test that this agrees with the intended "garment size vs body" fit story before using it. Always handle false (no reason is given).

## 4. GetHiResTolerance / SetHiResTolerance (NEW in 336)

Facts:
- Backed by persistent application settings, not scene data: org string `"CLO Virtual Fashion"` (0x8266750) with `QSettings`-style keys per row (`0x60af360`):
  - type 0: `"Particle Distance Tolerance Min"` / `"... Max"`
  - type 1: `"Collision Thickness Tolerance Min"` / `"... Max"`
  - type 2: `"Skin Offset Tolerance Min"` / `"... Max"`
  Any other `_toleranceType` makes `0x60af360` return false, so Get returns an **empty vector** and Set returns **false** (checked before anything else).
- Row descriptor constants (doubles, from 0x89bb820..0x89bb860, 0x8298378, 0x83d1458, 0x8269b38):
  - Particle Distance: default (5.0, 20.0); min spin range 1.0..700.0; max upper bound 700.0
  - Collision Thickness: default (1.0, 100.0); min spin range 0.0..99.99; max upper bound 999999999.0
  - Skin Offset: default (0.0, 100.0); min spin range 0.0..99.99; max upper bound 100.0
  (The meaning of each constant pair is INFERENCE from the header text: "Particle Distance 1.0 to 700.0 ... Collision min 0.0 to 99.99, max ... 999999999.0 ... Skin Offset min 0.0 to 99.99, max 0.0 to 100.0".) Units are **millimetres**, type double.
- Get returns `[min, max]` (2 doubles) read from settings with the default above when the key is absent.
- Set: each of min, max goes through `0x60cc550(x, lo, hi)` = round to 1 decimal (`round(x*10)/10`) then clamp into `[lo,hi]`; then if `min > max` (after normalisation) it returns **false and writes nothing**; otherwise it writes both keys and returns true. It does not apply Hi-Res to the garment (no scene call in the body).

**Recommended use for Mirra.** Low value for the current pipeline: the setters only change the filter range of the "Hi-Res Garment" dialog. Use only to snapshot (`Get`) and restore the user's CLO settings around a Hi-Res export, and to widen the range so the Hi-Res apply touches every piece. Remember it persists across CLO sessions (machine setting), so a worker should restore previous values.

## 5. FlipPatternNormal(vector<int>) @0x5fcd810, returns bool

Facts: empty vector -> false (checked first, `[rdi]==[rdi+8]`); no pattern editor -> false; a second scene precondition (`0x1be0dc0 ... 0x1c09670`) -> false; builds the real-pattern vector (`0x56e5930`); for each index `0 <= i < count` is required (0-based, signed compare), null entries are tolerated in the collection step but the header states one out-of-range index makes the whole call a no-op. Duplicates flip once. Patterns are left selected; undo stack entry created (header). Mesh-level change: simulate afterwards.

**Recommended use for Mirra.** Use as a repair step when a garment from a DXF has inside-out fabric (back faces textured instead of front) on a subset of panels: detect from the preview/GLB, call `FlipPatternNormal([ids])`, then `Simulate`. Pass only validated indices (from `GetPatternCount`), because a single bad index silently makes it a no-op returning false.

## 6. GetPatternComponents @0x6000880 / GetPatternGroupsBySeamlineConnectivity @0x6002800 (NEW in 336)

Both return JSON strings built with nlohmann::json. Strings found:
- GetPatternComponents: `"status"`, `"failed"`, `"success"`, `"message"`; failure messages `"Pattern editor is not available"`, `"Invalid pattern index: <n>"` (index printed), `"Unknown component type '<x>'. Supported: \"button\", \"buttonhole\", \"graphic\", \"print\", \"zipper\", \"trim\""`; keys `patternIndex`, `patternName`, `components`, type names `button/buttonhole/graphic/print/zipper/trim`. `_patternIndex == -1` means every pattern (header), `_types` empty = all.
- GetPatternGroupsBySeamlineConnectivity: `"Pattern editor is not available"` failure; keys `groupCount`, `groups`, `groupIndex`, `patternIndices`, `patternNames`, `patterns[{index,name}]`, `uid`, `patternIndex`, `components`.
- Index space = real pattern list (same as GetPatternCount); 0-based. The second `bool` (`_bIncludeComponents`) adds the `components` array; the first (`_bIncludeAttachments`) also merges pieces fastened by locked button/buttonhole pairs (header).
- Not verified in disassembly: the connectivity algorithm (connected components over seamline, glue, zipper, lacing edges) is documented in the header only.

**Recommended use for Mirra.** In Step 3 after importing several garments (or a garment plus an accessory), call `GetPatternGroupsBySeamlineConnectivity(false,false)` and use `patternIndices` of group 0 (largest) as `ImportExportOption.patternList` for a per-garment `ExportGLTF`. Use `GetPatternComponents(-1,["graphic","print"])` to verify that a graphic/print we placed is actually mounted on the expected panel (position is mm, pattern-local for graphics/prints, 2D-window world for buttons).

## 7. GetPatternLineInfo(patIdx) @0x6006540

Facts: returns a JSON string; failure shape `{"status":"failed","message":"Invalid pattern index: <n>"}` (pattern lookup via `0x60b1f10`, so 0-based and `0<=i<count`); success `{"status":"success","patternIndex","patternName","lineCount","boundingBox":{minX,minY,maxX,maxY,width,height},"lines":[{lineIndex,length,orientation,location,start,end,mid,midNorm}]}`.
- `orientation` strings: `horizontal`, `vertical`, `diagonal`, chosen by comparing slope ratios against two constants (0x364 -> 0.364 and 3.048 at 0x89bb810; INFERENCE: approx 20 and 72 degree thresholds). `location` strings: `top`, `bottom`, `left`, `right`, `center`, combined forms with `-` (e.g. `top-left`), chosen with thresholds 0.34 / 0.66 of the normalised midpoint (constants 0.66 at 0x8844164 and 0.34 at 0x884e470); `midNorm` is the line midpoint normalised into the bounding box. The line ordering is the same index used by `GetLineLength`, `DeleteLine` and `SetPatternEdgeToAvatarMeasure`.
- `length` is in millimetres per header (not re-derived; the 2D window coordinates are the same unit as `GetPatternOutlinePoints` per header).

**Recommended use for Mirra.** One call replaces the plugin's zero-length probing of `GetLineLength` and gives the data needed to map generated DXF edges (side seam, hem, armhole) to CLO line indices by `location`/`orientation`/`length`, which is exactly what Step 3 seam creation needs. Compare `length` to our DXF edge length (mm) as a sanity check before `AddSeamlinePairGroup[Partial]`.

## 8. GetAvatarMeasurements(avatarIdx) @0x5fd4180

Facts:
- Avatar list via `0x50ccb70`; **if no avatar is loaded**: logs `"[Python] Please Load Avatar"` and returns an empty vector. **Index out of range** (`idx < 0` or `>= count`): logs `"[Python] GetAvatarMeasurements: avatar index <n> is out of range (avatar count: <m>)"` and returns empty. 0-based.
- Unit string (`0x61541c0`): internal unit code 4 -> `"mm"`, 3 -> `"cm"`, 2 -> `"in"`, anything else -> empty string. It is the **current CLO display unit** (global), not a fixed unit.
- Per avatar two measurement lists are walked (`0x50d9050`: user measures, then `0x50db7a0`: avatar-default resizing measures) through `0x5f1f040`. Measures whose kind field (`[m+0x2AC]`) equals 6 are skipped.
- Type string from the kind field via jump table at RVA 0x5f1f500: 1 -> `Tape`, 2 -> `Circumference`, 3 -> `Height`, 4 -> `Circumference`, 5 -> `Tape`, 7 and 8 -> `Default`, 9 -> `Linear`, others `Unknown`.
- Values: `basicLength` = convert(`[m+0x2B0]`), `surfaceLength` = convert(`[m+0x2B4]`), `value` = basic when `[m+0x2A8]==0` else surface; `convert` = `0x6155bf0 -> 0x625bda0(value, from unit 4 (mm) to display unit)`. If the measure has a linked resizing item (result of `0x507df40` non-null) all three equal the single field `[item+0x2D4]` converted. So all float lengths are **in the display unit named in `unit`, full circumference for circumference types** (not half-girth), internal storage mm.
- The `measurementName` is obtained by virtual call `[vtbl+0xB0]` on the measure object (name shown in the Object Browser).

**Recommended use for Mirra.** Immediately after `ImportAvatarMeasurement`/`ImportAvatar` and the apply step in Step 1, call `GetAvatarMeasurements(0)` and compare bust/waist/hip `value` against the requested values after converting by the returned `unit` (mm/cm/in, never assume cm). Treat a mismatch above tolerance, or an unchanged value across different users, as a failed fit and fail the run. This is the direct test for the "GLB identical across users" suspicion without needing a GLB diff.

## 9. GetActiveWorkspaceFileName / ...W @0x5fd0890 / 0x5fd0bb0

Facts: gets the active workspace file name from a scene singleton (`0x1c5fb60 -> 0x5d74530`), compared against the literal `"NULL"` (0x825e6d0): if the internal string is empty or equals `"NULL"` the function returns an empty/short placeholder path (the header says the API returns "NULL" when no file is active; this is the expected sentinel). Otherwise the name is passed through a string transform (`0x66668a0 -> 0x40edd80 -> 0x6668370`) and returned. Name only with extension (header example "test.zprj"), not a full path. INFERENCE: the transform is a filename extraction (path stripped); not fully verified.

**Recommended use for Mirra.** Cheap guard in the worker: confirm that the project CLO has loaded is the one the job intended (compare to the expected `.zprj/.zpac/.avt` basename) and detect "no file active" (`"NULL"` or empty) before exporting; avoids exporting the previous job's scene.

## 10. ExportThumbnail2D @0x5fc53a0 and ExportStdViewImage @0x5fc3e00 / 0x5fc3b00

- ExportThumbnail2D: thin wrapper (logs FUNCSIG, then calls `0x60a7360(ret, path)`); returns string path, header says empty string when the 2D window is unavailable (headless). Captures the 2D window as displayed (no re-framing). PNG/JPEG chosen by extension.
- ExportStdViewImage (both overloads) -> if the output path string is empty returns the literal `"Invalid Output File Path"` (checked first, before any scene access); otherwise tail-calls the worker `0x5d5fb60` (shared with the other image exports). The worker contains the strings `"Please provide filepath with extension"`, `"Invalid Output File Path"`, `"Failed to Save Image - Image Path "`, JSON keys `colorwayFolderPath`, `colorwayName`, `imagePath`, `groupId`, `includeAllColorways`, `snapshotFolderPath`, `selectedColorwayName`, `imageExtension`, `images`, and `"Invalid ZCMR..."`. INFERENCE: errors are returned as plain message strings in the same std::string return (so a caller must test the result for being an existing image path, not just non-empty), and the success value contains the output path plus colorway name (header). The parameter named `_outputFolderPath` must in practice be a **file path with an extension** (header for the 6-arg form says "output file path including the image extension"; worker error text agrees). View index (header): 0 Bottom, 1 FrontRight, 2 Front, 3 FrontLeft, 4 Right, 5 Top, 6 Left, 7 Custom, 8 Back. The 5-arg form fits the camera to garment patterns only; the 6-arg form with `_bFitAllObjects=true` fits avatar + garment.

**Recommended use for Mirra.** For website previews use `ExportStdViewImage(2, "<dir>\\front.png", colorway, W, H, true)` and `(8, ".../back.png", ...)` right after Simulate in Step 3, and treat any return value that is not an existing file as an error message. `ExportThumbnail2D` is not useful for the 3D VTO (2D window only, headless-unsafe).

## 11. SetGraphic*MapTexture (Utility 219..230)

Facts: all wrappers log their FUNCSIG and then act on a *graphic style* by index. For `SetGraphicBaseColorMapTexture(path, graphicStyleIdx)` @0x6050320: resolves the style via `0x60af0a0` and, if the lookup yields nothing, **returns silently** (void API, no error); on success it sets the texture (`0x60fb230`) and touches the scene refresh (`0x1be0ec0`, `[+0x30]` check). Index base 0-based (header: "default index = 0" for the single-argument map overloads). The exe exposes both header forms: `(string)` using graphic index 0 and `(uint graphicIndex, string)`; the 3-arg BaseColor has an extra colorway index.

**Recommended use for Mirra.** To put a customer print on a garment without overwriting the fabric base colour: create/obtain a graphic style, then `SetGraphicBaseColorMapTexture(png, styleIdx, colorwayIdx)`. Because failures are silent, verify with `GetPatternComponents(-1,["graphic"])` (it lists `styleIndex`/`styleName`/size) that a graphic actually exists, and check the file exists before the call.

## 12. GetFabricPBRMaterialBaseColor(colorway, fabric, face) @0x5fe9420 (slot 117) and 2-arg @0x5fe91d0 (slot 118)

Facts: returns `tuple<float,float,float,float>`. Resolves the fabric/colorway object (`0x60ae0f0`, which uses `0x1d68b70`/vector size checks, so out-of-range indices are rejected) and copies the colour (`0x60adf90`). **Failure/default value is (1.0, 0.0, 0.0, 0.0)** (constant at 0x82823e0, written in the missing-object and "no PBR material" branches) with no error indication. On success the four floats are read from a 16-byte colour at `[material+0x220]` through `0x3a74bc0` and stored in reverse order, so the tuple comes out in R,G,B,A order (INFERENCE: internal layout is A,B,G,R; values not shown to be 0..1 vs 0..255 here, header says "RGBA float tuple"). Face is the same index as the setter (0 front, 1 back, 2 side per findings/09).

**Recommended use for Mirra.** Use immediately after `SetFabricPBRMaterialBaseColor` to confirm the colour took effect (the setter's bool is ignored by the plugin today). Treat exactly `(1,0,0,0)` as "invalid fabric/face" (a real colour never has alpha 0), then compare channel-wise with tolerance.

## 13. Gaps / not done

- The data structures behind the pattern-to-avatar-measure getters were not decoded.
- `0x55d5f80` (stitch creator) was only read for argument handling, not for the geometry rules that make it return false (-7).
- Units claimed for `GetPatternLineInfo.length` come from the header, not re-derived from the multiplier chain.
- Hi-Res: the exact meaning of the constant pairs in the row descriptor is inferred from the header ranges.
