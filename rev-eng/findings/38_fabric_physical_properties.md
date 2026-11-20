# 38 - Fabric PHYSICAL property APIs (lane AJ)

*Static analysis, CLO 2026.1.336. Date: 2026-10-29. Tags: [V] verified from header/spec/disassembly/zprj, [I] inferred. Scripts: `scripts/disasm_fn15.py` (copy of disasm_fn4, cache `raw/disasm15/`), `scripts/zprj_probe.py`. Exe base 0x140000000; RVAs below are the wrapper addresses from `slots_lookup.py` (grouped-overload slot model).*

## 1. Headline

1. **FabricAPIInterface.h has NO per-property physical setter or getter** [V]. A case-insensitive grep of all 285 virtuals (and of all other SDK headers) for stretch / bending / buckl / densit / thickness / friction / shrink / damp / shear / physical finds nothing in Fabric. The only way the public API changes a fabric's drape physics is to **load a whole `.jfab` / `.zfab`** (which overwrites the entire `mapPhysical` block, plus appearance).
2. The relevant calls are all **implemented** (none are import thunks; `raw/verify_thunks.json` lists 0 Fabric thunks, and the Utility/Pattern thunks are grading / asset-share / graphic-style only) [V].
3. Two small physical-adjacent knobs exist outside Fabric: `PatternAPI::Set/GetAddlThicknessCollision` (per pattern) and `UtilityAPI::SetSimulationAirDamping` (global), plus `SetSimulationGravity` etc. No shrinkage API exists anywhere [V].
4. The plugin today exposes **no physical control**: `/set-fabric` takes a `pattern_index` + `fabric_index` (default 0), calls `PATTERN_API->SetPatternPieceFabricIndex`, and ignores the `preset` string (the comment promises "Cotton_Medium" names, but `cmd.param1` is never filled and no fabric-by-name API is used) [V, RestPlugin_windows.cpp 1370-1395, 2044]. Every VTO run therefore drapes with CLO's built-in "Default" fabric [V, zprj].

## 2. API table: API -> JFAB key -> unit -> implemented? -> notes

JFAB physical keys live under `mapPhysical` (JFABSpec.json). The spec gives **no units** for any of them [V]; units below are [I] from CLO conventions (mm / g / s world; gravity in the project is -9800 mm/s^2).

### 2a. Loading / presets (the only route to physical values)

| API (slot; wrapper RVA) | JFAB / file key touched | Unit | Impl? | Notes |
|---|---|---|---|---|
| `AddFabric(path)` (15; 0x5f8f580) / `AddFabricW` (17; 0x5f8f800) | whole fabric incl. `mapPhysical` | n/a | yes | Accepts zfab or jfab. Extension dispatcher at 0x5cf6c30 handles `fab`,`zfab`,`jfab`,`xtex`,`axf`,`sbsar`,`gltf`,`glb` [V]. Returns `fabricCount-1` read **after** the load (`lea eax,[rbx-1]` at 0x145F8F7D6), so a failed load returns the previous last index (or 0xFFFFFFFF on an empty list): **indistinguishable from success** [V]. Appends to the object browser; does not assign to patterns. |
| `ChangeFabricWithJson(fabricIdx, path)` (22 or 23; 0x5fa33d0) / `(colorway,fabric,path)` (0x5fa3650) / `W` variants (24,25) | overwrites all of `mapPhysical`, `mapColorwayInfo`, names | n/a | yes | `bool`. Resolves the fabric `shared_ptr` from the fabric list (0x60ac160, bounds-checked; out of range -> null -> **false**). 0x6097e80 then opens the file and calls the "Load Fabric" loader 0x4998730 (flag args `1,1`); false if file unreadable [V]. The 1-arg-index overload uses the **current** colorway [I]. Index base 0 [V]. Header says "overwrite all the properties", so appearance is replaced too (re-apply colour/texture after) [V header]. |
| `ReplaceFabric(idx, path)` (16; 0x6038110) | whole fabric | n/a | yes | Header documents **zfab only**; returns `bool` (header body returns `""`, a header quirk). Core 0x60f1cf0 [V]; behaviour on jfab not decoded. |
| `CombineZfab(out, baseZfab, targetZfab)` (122; 0x5fa6950) | physical from base zfab, image from target zfab | n/a | yes | `void`, writes a new `.zfab`; the only API that mixes a physics source with a texture source offline [V header]. Needs zfab inputs, not jfab. |
| `AssignFabricToPattern(fabricIdx, patternIdx, option)` (26; 0x5f9bd50) / `(colorway, fabric, pattern, option)` (27; 0x5f9bf90) | `mapFabricShape2D/iFabricIndex` per pattern | n/a | yes | `bool`. Core 0x6090d60 returns false on null fabric, on a range check of the option (`cmp eax,2; ja` -> valid option 1..3 if the compare is on option-1 [I]) and on pattern index > count [V]. Options: 1 current colorway, 2 all colorways unlinked, 3 all linked [V header]. Prefer this to the plugin's `SetPatternPieceFabricIndex` because it handles colorways. |
| `GetFabricIndexForPattern`, `GetFabricCount`, `GetFabricName`, `SetFabricName`, `DeleteFabric`, `ExportFabric/ExportZFab` | `qsFabricName` etc. | n/a | yes | Bookkeeping. `ExportFabric` writes `.jfab` or `.zfab` by extension [V header] -> the way to **read back** the physical values (there is no getter). |
| `ChangeMetaDataValueForFabric` (46/47; 0x5fa4a60) | `qsAPIMetaData` (JSON string) | n/a | yes | Free-form key/value, not physics [I]. |

### 2b. Physical keys (JFAB `mapPhysical`, no API setter/getter exists for any of them)

| JFAB key (spec label) | Meaning | Spec example | CLO "Default" in a Mirra zprj [V] | Unit [I] |
|---|---|---|---|---|
| `fSuK` ("Stretch-Weft") | weft stretch stiffness | 100000 | 100000 | model units (no unit stated) |
| `fSvK` ("Stretch-Warp") | warp stretch stiffness | 100000 | 100000 | same |
| `fHK` ("Shear", bias) | shear/stretch along bias | 10000 | 5000 (plus `fLeftShearK`=5000, `fLeftShearK_v2`/`fRightShearK_v2`=10000) | same |
| `fBuK` ("Bending-Weft") | bending weft | 2000 | **100** | same |
| `fBvK` ("Bending-Warp") | bending warp | 2000 | **600** | same |
| `fBhK` ("Bending-Bias") | bending bias | 2000 | **150** | same |
| `fBuLR` / `fBvLR` / `fBhLR` ("Buckling Ratio" weft/warp/bias) | buckling ratio | 0.8 | 0 | ratio |
| `fBucklingStiffnessU` / `V` / `H` | buckling stiffness weft/warp/bias | 0.8 | 0 | ratio-like |
| `fDensity` | mass density | 0.0003 | 0.0003 | spec silent; 0.0003 is the value CLO stores for default fabric [I: g/mm^2 = 300 g/m^2 is implausibly heavy for a shirt, so the unit is probably not g/mm^2; unresolved] |
| `fThickness` | fabric thickness | 0.5 (spec says default 0.5) | 0.5 | mm [I] |
| `fFriction` | fabric friction | 0.03 | 0.03 | dimensionless coefficient |
| `fIDS` ("Internal Damping") | internal damping scale | 0.0001 | 0.0001 | dimensionless |
| `enFabricType` | preset class: 0 Default, 1 Silk, 2 Cotton, 3 Wool, 4 Denim, 5 Leather, 6 Cashmere, 7 Satin, 8 Spandex, 9 Rayon, 10 Linen, 11 Taffeta, 12 Polyester, 13 Terrycloth, 14 Flannel, 15 Burlap, 16 Rubber | 0 | 0 | enum |
| `listNonlinearSuK/SvK/HK` | nonlinear stiffness curves "generated from Emulator" | [] | [] (also `listNonlinearLeftShearK`) | n/a |
| `mapRawData.*` | read-only fabric-kit raw measurement (force/length lists, sample size 200x30 mm) | empty | n/a | n/a |
| `qsPhysicalPropertyName` (+UTF8) | label | "Default" | "Default" | n/a |
| (no key) bending angle, shrinkage | **not present in the spec** [V]; no shrinkage key anywhere in JFAB or the zprj `mapPhysical` | | | |

Extra keys found only in the zprj (not in the JFAB spec) [V]: `fLeftShearK`, `fBLeftShearK`, `fBLeftShearLR`, `fBucklingStiffnessLeftShear`, `fLeftShearK_v2`, `fRightShearK_v2`, `fBvK_v2`, `fBuK_v2`, `fBLeftShearK_v2`, `fBRightShearK_v2`, `fexpSuK/SvK/RightShearK/LeftShearK` (0.1), `bUseExpApproximation`, `bEband`, `bFromDefault`=True, `enActivatePPType`, `qsMLModelVersion`, `qsSoftwareVersion`, `mapStrainRangeProperty` (4 entries: maxForce 15, maxStrain 120). The `_v2` values equal `k * pi` for bending (600 -> 1884.96, 100 -> 314.159, 150 -> 471.239) [V arithmetic]; shear `_v2` is 2x the v1 value (5000 -> 10000) [V]. So a jfab with only the spec keys will leave the `_v2`/`LeftShear` keys to be derived by the loader [I: the loader must regenerate or default them; not decoded].

### 2c. Physical-adjacent setters outside Fabric

| API | Unit / range | Impl? | Notes |
|---|---|---|---|
| `PatternAPI::SetAddlThicknessCollision(patternIdx, value)` (176; 0x603cb90) / `GetAddlThicknessCollisionValue` (177; 0x5fd0eb0) | float, mm [I] | yes | Per-pattern extra collision thickness; the closest per-pattern "thickness" knob. Not range-decoded. |
| `UtilityAPI::SetSimulationAirDamping(float)` (93; 0x606f480) | header default 1.0 | yes | **Decoded:** after the log prologue it gets the sim settings object (0x1c23080) and calls 0x673b6b0 which is literally `movss [rcx+10h],xmm1; ret`: a raw float store, **no clamp, no re-simulation** [V]. Takes effect on the next Simulate. |
| `SetSimulationGravity`, `...TimeStep`, `...CGIterationCount`, `...Quality`, `...SelfCollision*`, `...Nonlinear...` | see header | yes | Same family (global sim settings object); zprj `mapSMP` shows the stored values (gravity -9800, step 0.0333, 50 CG iterations). |
| `UtilityAPI::Set/GetAvatarProperties(avatarIdx, map<string,string>)` | keys `KineticFriction` 0.05, `StaticFriction` 0.8, `SkinOffsetMM` 3.0, `DivideMesh`, `SoftBodySimulation` (header examples) | yes | Avatar-side friction/skin offset; strongly affects drape fit and is not fabric physics. Strings, not floats. |
| `PatternAPI::SetParticleDistanceOfPattern(s)` | mm | yes | Mesh resolution; zprj `fEdgeLength` 20 mm [I]. |

## 3. Decoded wrappers (return conventions, index bases, re-simulation)

Common prologue for every wrapper [V]: `0x4e10dd0` (get API logger/ctx) -> build a log string of the demangled signature (`Marvelous::FabricAPI::X(...)`, copied from `.rdata`) -> `0x4e10fb0(ctx, level=3 or 2, str, ...)` -> `0x5ef27e0`... stack cookie `0x14A172D40`. Logging is the only common side effect.

| Wrapper | Index base / bounds | Return | Re-simulates? |
|---|---|---|---|
| `AddFabric` | n/a; returns `count-1` after load | unsigned; no error signal (see table) | **No** simulation call in the path; the load runs through the "Add Fabric" command at 0x5cdc610 (strings "Add Fabric"/"Copy Fabric"), a UI-command routine that may create an undo item. Does not touch patterns [V]. |
| `ChangeFabricWithJson` | 0-based object-browser index; out-of-range -> false (list is a vector of 16-byte shared_ptr pairs, `size = (end-begin)>>4`) [V] | bool: false = bad index or unreadable file; true = loaded | No sim call in the wrapper or in 0x6097e80; the loader 0x4998730 (1389 instructions, "Load Fabric", creates a progress/wait object when flag r8b=1) was **not** read to the end; whether it marks cloth for re-init is unknown [I: physics change is picked up on the next Simulate step because the fabric object is shared by pointer]. |
| `AssignFabricToPattern` | fabric/pattern/colorway 0-based; option 1..3 | bool | No sim call; just rewrites the pattern's fabric link [V]. |
| `SetSimulationAirDamping` | n/a | void | No. |
| `Set/GetAddlThicknessCollision` | pattern 0-based | void / float | No sim call visible; not decoded further. |

Threading [I]: like lane N, these touch UI/document objects; call from the CLO UI thread (the plugin's PostMessage queue pattern is right).
Modal-dialog risk [I]: the loader shows a progress object, not a confirmation box, in the part seen; a jfab with a missing texture path (spec sample has absolute `D:/CLO Library/...jpg` paths) might warn. Mirra should strip/replace `listTexture` paths in generated jfabs [I].

## 4. Compare with the zprj (lane Q) [V]

* Run read: `clo_vto/output/u_001/c_001/s_001/002/simulation.zprj`, member `simulation.zpac!simulation.pac`, path `listFabric/0/mapPhysical` (`zprj_probe.py tree ... --path listFabric/0/mapPhysical`). The same block is replicated per pattern in `mapOriginPatternPhysicalProperty` (46 keys, from findings/23).
* Stored default: `qsPhysicalPropertyName`="Default", `bFromDefault`=True, `enFabricType`=0, Su=Sv=100000, Bu=100, Bv=600, Bh=150, shear 5000, buckling all 0, density 0.0003, friction 0.03, thickness 0.5, IDS 0.0001. This is a very soft, low-bending, no-buckling default; it will drape like a limp cloth and has no fabric-type character.
* Discrepancy to note: the JFAB spec/sample example shows bending 2000 and buckling 0.8, i.e. the spec example is a different (stiffer) fabric than CLO's built-in Default. The sample `fabric_sample.jfab` ("merong", 1044 bytes, a trimmed file with only `mapPhysical`, `qsFabricName`, versions 100) shows that a **minimal jfab needs only `mapPhysical` + `qsFabricName` + `uiFabricVersion`/`uiVersion` = 100** [V file]; it has `fBuK`=8000, `fBvK`=2000, `fSuK`=10, `fSvK`=10, `fHK`=10000, `fBhK`=8000, `fBuLR`=`fBhLR`=1.8, `fBvLR`=0.8, buckling stiffness 1.8, IDS 0.0001 and no colorway info. (Its `qsPhysicalPropertyName` is a CP949 string; its `fSuK`=10 is clearly a test value, not a real fabric.)
* The zprj `.pac` writes the fabric under `listFabric`, keys not including `fabricContent`/`fabricType` strings; names `FABRIC 1`.

## 5. Plugin coverage (read-only grep of RestPlugin_windows.cpp) [V]

| Plugin route | Underlying API | Physical effect |
|---|---|---|
| `POST /set-fabric` {pattern_index, fabric_index=0} | `PATTERN_API->SetPatternPieceFabricIndex` | selects fabric slot only; `preset` field echoed empty |
| `/set-fabric-color`, `/set-fabric-texture`, `/set-fabric-graphic` | `SetFabricPBRMaterialBaseColor`, `SetBaseTextureMapImageGivenFilePath` | appearance only |
| `/fabric-status` | counters | n/a |
| (missing) | `AddFabric`, `ChangeFabricWithJson`, `AssignFabricToPattern`, `ExportFabric`, `SetSimulationAirDamping`, `SetAddlThicknessCollision` | none exposed |

`clo_vto/native_vto/step_08_apply_fabric.py` calls `set_fabric(idx, fabric_index=0)` for every piece, so all four pieces share the one default fabric (and, per lane Q, share its single texture entry).

## 6. Recommended minimal fabric-preset flow for Mirra

Goal: realistic, selectable drape with the smallest plugin change. All steps on the CLO UI thread.

1. **Author presets offline** as small `.jfab` files (`mapPhysical` + `qsFabricName` + versions 100 only; no colorway/texture paths). Source the numbers by (a) opening a CLO fabric in the GUI and `ExportFabric`/Save to jfab once, or (b) copying a library fabric. Keep one file per preset (cotton knit, denim, silk, etc.); set `enFabricType` to match [V enum]. Do not invent stiffness values from the spec example. [I]
2. **Add a plugin command** `/load-fabric-preset {path}`:
   * once per run: `idx = FABRIC_API->AddFabric(path)`; **verify** by `GetFabricCount()` before/after and `GetFabricName(idx)` == expected, because the return value cannot signal failure [V].
   * alternatively overwrite the existing fabric 0 in place: `ChangeFabricWithJson(0, path)` and check the `bool`. This is the safest minimal change because the pipeline already assumes fabric index 0 and shared-fabric semantics [V].
3. **Assign** with `AssignFabricToPattern(fabricIdx, patternIdx, 1)` for each of the 4 pieces (check bool), instead of (or after) `SetPatternPieceFabricIndex`. Verify with `GetFabricIndexForPattern(pattern, colorway)` (0-based; remember lane N: the 1-arg form returns 0 on failure).
4. **Re-apply appearance after the load** (colour via float 0..1 overload, texture path), since `ChangeFabricWithJson` overwrites "all the properties" [V header].
5. Optionally set `SetSimulationAirDamping` and per-pattern `SetAddlThicknessCollision` from the preset; read back with `GetAddlThicknessCollisionValue` (no getter for air damping) [V].
6. **Simulate** (lane R: synchronous, always returns true). Then confirm by saving the project and reading `listFabric/0/mapPhysical` with `zprj_probe.py` (there is no API getter; this is the verification route) [V].

Python side (`clo_vto/native_vto`): add `load_fabric_preset(path)` and a preset-name -> jfab-path map; run it before Step 8's `set_fabric`; no other pipeline change needed.

## 7. Open items

* Loader 0x4998730 not decoded to the end: unknown whether loading a jfab with an incomplete `_v2`/LeftShear key set regenerates them (needed for a spec-only jfab to behave like the GUI). Falsify by loading `fabric_sample.jfab`-style minimal file and diffing the saved zprj `mapPhysical` (test needs a live CLO, out of scope here).
* Physical units for `fDensity`/stiffness are undocumented; treat as opaque and copy from CLO-exported fabrics.
* `ReplaceFabric` with a jfab, and the exact option range check of `AssignFabricToPattern`, are unconfirmed.
* No evidence of a fabric-by-preset-name API in the public header; the plugin's "preset name" comment is aspirational [V].
