# CLO SDK check for all three pipelines: what we use, what the SDK offers, and the gaps

*Status: read-only analysis of the SDK headers, the plugin source and the pipeline code. Nothing was run in CLO and no code was changed*
*Written: 2026-10-18*

---

## 0. What was compared

| Item | Detail |
|---|---|
| **SDK** | `CLO_SDK_v2026.1.224_Win`, headers in `CLOAPIInterface/include/` (`ImportAPIInterface.h`, `ExportAPIInterface.h`, `PatternAPIInterface.h`, `UtilityAPIInterface.h`, `FabricAPIInterface.h`, `CloApiData.h`, `RestAPIInterface.h`) |
| **Size of the SDK surface** | about 1,058 declared functions: Import 45, Export 119, Pattern 210, Utility 399, Fabric 285 |
| **Our plugin** | `clo_workspace/windows/RestPlugin_windows.cpp`, built against the same SDK version (`PluginBuildInfo.h`: `CLO_SDK_v2026.1.224_Win`, plugin 1.3.2) |
| **What the plugin calls** | only **38 distinct SDK functions**: Export 7, Fabric 3, Import 6, Pattern 16, Utility 6 |
| **Pipelines compared** | Step 1 avatar (`clo_avatar_generation/avatar_runtime`), Step 2 product ingestion (`product_ingestion`), Step 3 VTO (`clo_vto/native_vto`) |

**Method.** For each process I (1) listed which SDK calls it reaches through the plugin, (2) searched the SDK for functions on the same topic, (3) read the doc comments of the promising ones, and (4) noted what each gap would let us do. Everything below marked "doc comment" comes from the headers and has **not been tested**.

**All 38 calls the plugin uses**

- Export: `ExportAVT`, `ExportGLB`, `ExportGLTF`, `ExportZPrj`, `GetAvatarCount`, `GetAvatarGenderList`, `GetAvatarNameList`
- Fabric: `GetFabricIndexForPattern`, `SetBaseTextureMapImageGivenFilePath`, `SetFabricPBRMaterialBaseColor`
- Import: `ImportAvatar`, `ImportAvatarMeasurement`, `ImportDXF`, `ImportFile`, `ImportMeasurement`, `ImportOBJ`
- Pattern: `AddGradingSizeGroup`, `AddSeamlinePairGroup`, `GetArrangementList`, `GetArrangementOfPattern`, `GetBoundingBoxOfPattern`, `GetLineLength`, `GetPatternCount`, `GetPatternInformation`, `GetPatternInputInformation`, `GetPatternPieceArea`, `SetArrangement`, `SetArrangementOrientation`, `SetArrangementPosition`, `SetGradingPairedAvatarFromFile`, `SetGradingPairedAvatarSizing`, `SetPatternPieceFabricIndex`
- Utility: `DeleteAvatar`, `DisplayMessageBox`, `GetAvatarProperties`, `NewProject`, `SetAvatarProperties`, `Simulate`

---

## 1. Summary: the findings that matter most

| # | Process | Finding | Why it matters | Where |
|---|---|---|---|---|
| 1 | **Avatar** | `Get/SetAvatarProperties` handle **physics and surface properties** (the doc comment's examples are `KineticFriction`, `SkinOffsetMM`, `StaticFriction`, `DivideMesh`, `SoftBodySimulation`), **not body measurements** | The "properties" apply mode cannot resize a body; the only SDK routes that change body size are the measurement CSV import and the grading/`.avs` sizing route. It also explains why Step 1's own readback note calls the property map "not yet a trustworthy body-measurement readback source" | section 2.2 |
| 2 | **Avatar** | **`GetAvatarMeasurements(avatarIndex)` exists** and returns, per measurement, name, type (Tape / Circumference / Height / Linear), value, basic length, surface length and unit. Our plugin does not expose it | This is the missing trustworthy **readback** of what CLO actually produced, which Step 1's "compute error" step needs | section 2.2 |
| 3 | **Avatar** | Native **avatar texture API**: `SetAvatarTexureMap(path, type)` and `SetAvatarMeshTexture(shape, 0 face / 1 body / 2 arm / 3 leg, path)` | Fits Step 1's new scope (face and skin colour) without leaving CLO | section 2.3 |
| 4 | **Product ingestion / VTO** | `ImportDxfOption` has `m_bIncludeNotchs` (default **false**), `m_bAutoTraceAsInternalLines` (default false) and `m_bAutoScale` (default **true**). Our plugin sets only `m_Scale` and `m_bAppend` | The notches, internal lines and grainlines that `clo_block` writes with care are probably **ignored on import** because the defaults are off; and `m_bAutoScale` may interact with our 0.1 import scale | section 3.2 |
| 5 | **Product ingestion** | **Native size grading**: `AddGradingSizeGroup`, `AddGradingSize`, `ImportGradeRuleToSizeGroup(.rul)`, `ChangeGradingSizeInformation` | We store ten separate size rows and regenerate patterns per size; CLO can hold one pattern with graded sizes | section 3.3 |
| 6 | **Product ingestion / VTO** | **Programmatic pattern creation** `CreatePatternWithPoints` with vertex types 0 straight, 2 spline, 3 Bezier | Exact Bezier control points instead of 98-144 tessellated polyline vertices per DXF; an alternative to DXF import | section 3.3 |
| 7 | **Product ingestion / VTO** | **Measurement reports**: `ExportPOM(include3DLength)` (point-of-measure sheet) and `ExportGarmentInformation()` (JSON of the Garment Information dialog) | An automatic "measured vs requested size chart" check, and the closest thing the SDK has to a fit number | sections 3.4, 4.4 |
| 8 | **VTO** | Real **graphic placement**, **per-piece fabrics**, **Unified/Repeat texture mapping**, and **fabric physics through `.jfab`** are all in the SDK and unused | Fixes the logo and texture problems; adds per-fabric physics | `02-graphic-overlay-finding.md`, section 4.2 |
| 9 | **VTO** | `AttachPatternToAvatarMeasure(pattern, line, measureName)` pins a pattern line to an avatar measurement so the garment follows the avatar's size | A native way to keep a garment proportional to an avatar | section 4.3 |
| 10 | **VTO** | Simulation controls are unused (`SetSimulationQuality`, time step, gravity, CG iterations, self-collision, air damping, ground collision) and `Simulate(steps)` "follows the current simulation properties" | The pipeline runs 150 steps with whatever the project defaults are | section 4.3 |
| 11 | **VTO** | Outputs we do not use: rendering images, turntable images and video, 3D snapshots, FBX, USD, Alembic, and GLB **unified-texture baking options** | CLO's own renders could replace or supplement the Python GLB texture injection (Step 12 says CLO exports a grey, untextured GLB) | section 4.5 |
| 12 | **All** | The SDK also ships a **Python API** (`pattern_api`, and a menu-registered script plug-in sample) | A quick way to probe unfamiliar calls from inside CLO without writing C++ (scripts are started from a CLO menu, not at startup) | section 5 |

Not found in the SDK: a function that **returns numeric stress, strain or pressure values**. `GetStressMapStatus` / `SetStressMapStatus` and the strain-map equivalent only toggle the on-screen map. Fit therefore cannot be measured from stress through this API.

---

## 2. Process 1: Avatar generation (Step 1)

### 2.1 How the pipeline maps to SDK calls

| Step | What it does | Plugin endpoint | SDK call |
|---|---|---|---|
| 01 health, 02 run setup | checks CLO, creates the run folder | `/health`, `/capabilities` | none |
| 03 fetch measurements, 04 resolve base avatar, 05 normalise, 06 build payloads | Mongo data, picks a `.avt` template, builds CSV or property payloads | none | none |
| 07 import base avatar | `NewProject`, then import the `.avt` template | `/new-project`, `/import-avatar-avt` | `NewProject`, `ImportAvatar` (or `ImportFile`) |
| 08 apply measurements | one of three modes | `/import-avatar-measurements` (csv), `/avatar/set-properties` (properties), `/execute` with grading experiment | `ImportAvatarMeasurement` / `ImportMeasurement`; `SetAvatarProperties`; `AddGradingSizeGroup` + `SetGradingPairedAvatarSizing` / `FromFile` |
| 09 readback | reads native and property debug | `/avatars/state`, `/avatar/property-debug` | `GetAvatarCount`, `GetAvatarNameList`, `GetAvatarGenderList`, `GetAvatarProperties` |
| 10 compute error | compares requested vs read-back | none | none |
| 11 save outputs | saves `.avt` and the project | `/export-avatar-avt`, `/save-project` | `ExportAVT`, `ExportZPrj` |
| 12 export GLB | exports the avatar mesh | `/export` | `ExportGLB` with `scale=0.001`, `bExportAvatar=true`, `bExportGarment` only if patterns exist |

### 2.2 Gaps and findings

1. **Body-size change routes in the SDK** (from the headers):
   - `ImportAvatarMeasurement(csv, avt, options)` and `ImportMeasurement(csv)`: import a measurement CSV. Used.
   - Grading-based sizing: `AddGradingSizeGroup`, `SetGradingPairedAvatarSizing(gradingIndex, avsPath)`, `SetGradingPairedAvatarFromFile`. Used only in an experiment (`grading-avatar-size`).
   - `ImportAvatar` / `ImportFile` with options such as `bSizeAndPoseFromAvatar` (the plugin already forwards this flag from `/import-avatar-avt`). The header gives no description of what it does.
   - **No other function resizes an avatar.** `SetAvatarProperties` is not one of them.
2. **`Get/SetAvatarProperties` are not measurements.** The doc comments give `KineticFriction`, `SkinOffsetMM`, `StaticFriction`, `DivideMesh`, `SoftBodySimulation` as examples. The "properties" apply mode in Step 1 therefore has nothing to act on for body size, and its readback cannot show size. This matches Step 1's own comment in `step_09_readback.py`.
3. **Trustworthy readback is available and unused:** `GetAvatarMeasurements(avatarIndex)` ("all measurements (user measures and avatar-default resizing measurements) on the avatar") with `value`, `basicLength` (convex-fit), `surfaceLength` (surface-fit) and `unit`. Exposing it would give Step 1 a real "measured on the CLO avatar" number for each measurement name and let the error step compare like with like. *Unknown until tested: which names the template avatar defines, and how they line up with our measurement fields.*
4. **GLB export sets few options.** The plugin passes `scale`, `bExportGarment`, `bExportAvatar` and leaves every other `ImportExportOption` flag at its default. The option class also has `bSizeAndPoseFromAvatar`, `bIncludeHiddenObject`, `bThin`, weld options, unified-texture options and more. I have **not** established whether any of these relate to the known problem that exported avatar GLBs look identical across users, so treat that as a question to test, not a cause.
5. **Other avatar functions unused:** `SetAvatarSmooth` / `GetAvatarSubdivisionLevel` (subdivision 1-3, affects mesh smoothness), `SetAvatarSoftBodyStiffness`, `ImportPose` / `ExportPose` (pose files), `AlignAvatarsAndGarmentToCenter`, `SetAvatarActivation`, `SetShowHideAvatar`, `GetAvatarMeasurements`.

### 2.3 Skin and face (Step 1's expanding scope)

| Function | Doc comment |
|---|---|
| `SetAvatarTexureMap(imagePath, textureType)` | sets avatar maps: 0 BaseColorMap, 1 MetalnessMap, 2 NormalMap, 3 GlossinessMap, 4 AlphaMap, 5 DisplacementMap |
| `SetAvatarMeshTexture(shapeName, meshIndex, texturePath)` | changes the texture of a body part: 0 face, 1 body, 2 arm, 3 leg |
| `SetAvatarOpacityMap`, `GetAvatarTexureMap` | opacity map; read the current maps |

So a skin tone or a face texture can be applied natively. *Unknown until tested: how the template avatar's UV layout and part names look, and whether a plain colour image is enough for skin.*

---

## 3. Process 2: Product ingestion (Step 2)

Step 2 runs without CLO today. The SDK matters for it in four places: how the DXF is **imported**, how patterns could be **created or graded** natively, how results are **verified**, and how the **fabric** is defined.

### 3.1 What Step 2 produces that CLO consumes

DXF R12 `POLYLINE` files with layer 1 (boundary), 2 and 3 (points), 4 (notches), 7 (grainline), 8 (internal lines), mm units, plus `edge_manifest.json` and per-piece textures.

### 3.2 DXF import: options we leave at default

`ImportDxfOption` (from `CloApiData.h`) and the plugin's use of it:

| Option | Default | Our plugin sets | Meaning for us |
|---|---|---|---|
| `m_bAppend` | false | **true** | add to the project |
| `m_Scale` | 1.0 | the import scale (0.1 for mm) | unit scaling |
| `m_bAutoScale` | **true** | not set (stays true) | "auto scale": may interact with `m_Scale`; `clo_vto` step 4 already works around scale problems |
| `m_bIncludeNotchs` | **false** | not set | **notches (layer 4) are probably not imported** |
| `m_bImportNotchTo`, `m_eNotchImportPlacement` | true, 2 (both) | not set | where imported notches go (outline, seam allowance, both) |
| `m_bAutoTraceAsInternalLines` | **false** | not set | internal lines (layer 8) are probably not converted to internal lines |
| `m_bImportPatternAnnotation` | true | not set | text labels |
| `m_SwapCuttingLineAndSewingLine` | false | not set | which line is the sewing line when a DXF has both |
| `m_bOptimizeAllCurvePoints`, `m_bImportAllDrawCurvePoint`, `m_bRemoveNonGradingPoints`, `m_bAutoDistribute` | false | not set | curve and grading point handling |

**Why this matters:** `clo_block` documents that notches are placed the same arc distance from the underarm on the panel and the sleeve so the sleeve "sews in without rotating", and writes internal lines and a grainline. If notches and internal lines are dropped on import, that work does not reach CLO. *To confirm:* import a DXF with `m_bIncludeNotchs = true` and compare with the current import.

### 3.3 Creating and grading patterns natively

| Capability | SDK functions | Notes |
|---|---|---|
| **Create a piece from points** | `CreatePatternWithPoints(points)`, each point `(x, y, type)` with type 0 straight, 2 spline, 3 Bezier; also `CreateInternalShapeWithPoints`, `CreateBaseShapeWithPoints` | a path that keeps true curve control points instead of tessellated polylines. The SDK's own Python sample builds rectangles and curved polygons this way |
| **Size grading in CLO** | `AddGradingSizeGroup`, `AddGradingSize(group, name)`, `ImportGradeRuleToSizeGroup(group, .rul)`, `ChangeGradingSizeInformation`, `GetGradingSizeNameList`, `GetGradingPairedAvatar` | one pattern with graded sizes and a rule table, as the Lyu et al. review describes for industry grading. We currently make ten separate size rows |
| **Pattern editing helpers** | `UnfoldPatternPiece`, `SymmetryPatternPiece`, `OffsetAsInternalLine`, `AddPatternAnnotation`, `FitPatternUVToUDIM`, `SetParticleDistanceOfPattern` | useful for half-pattern workflows and mesh density |

### 3.4 Verification we could automate

| Function | Gives |
|---|---|
| `ExportPOM(include3DLength, path)` | the point-of-measure sheet of the garment, optionally including 3D info |
| `ExportGarmentInformation()` | JSON identical to CLO's File > Information > Garment dialog |
| `GetPatternPieceArea`, `GetBoundingBoxOfPattern`, `GetLineLength` | per-piece geometry (the plugin already exposes the last three) |
| `ExportDXF(path, ExportDxfOption)` | export patterns back out (formats: 0 DXF-AAMA, 1 DXF-ASTM, 2 Gerber AAMA) |

A **round trip** is possible: import our DXF into CLO, export it again with `ExportDXF`, and compare with CLO's own reference tee. That would answer, with CLO's own writer, how our DXFs differ from CLO's. It would also check that what CLO read equals what we wrote.

### 3.5 Fabric definition

Covered in `02-graphic-overlay-finding.md` section 5.3: the `.jfab` format (stretch, shear, bending, buckling, density, thickness, friction, damping, and an `enFabricType` label with 17 values) and `AddFabric` / `ChangeFabricWithJson`. This is the SDK side of fabric-property estimation.

---

## 4. Process 3: Virtual try-on (Step 3)

### 4.1 How the pipeline maps to SDK calls

| Step | What it does | SDK call reached |
|---|---|---|
| 01 health, 02 new project | check CLO, new project | `NewProject`, `GetAvatarCount` |
| 03 import avatar | `.avt` plus measurement CSV | `ImportAvatar`, `ImportAvatarMeasurement` |
| 04 import patterns | DXF files with a computed scale | `ImportDXF` (options: scale and append only) |
| 05 verify patterns | size sanity check | `GetPatternInformation`, `GetPatternInputInformation`, bounding box |
| 06 read edges and slots | arrangement slots, edge lengths, warm-up simulation | `GetArrangementList`, `GetArrangementOfPattern`, `GetLineLength`, `Simulate` |
| 07 arrange patterns | place pieces on avatar slots | `SetArrangement`, `SetArrangementPosition`, `SetArrangementOrientation` |
| 08 apply fabric | preset, colour, texture, graphic | `SetPatternPieceFabricIndex(0)`, `SetFabricPBRMaterialBaseColor`, `SetBaseTextureMapImageGivenFilePath` (the "graphic" call is the same texture function) |
| 09 create seams | the 10 T-shirt seams by edge index | `AddSeamlinePairGroup(patternA, lineA, patternB, lineB, dirA, dirB)` |
| 10 simulate | 150 steps | `Simulate(150)` |
| 10b save, 11 export, 12 texture GLB | project, GLB, Python texture injection | `ExportZPrj`, `ExportGLB`, then pygltflib |

### 4.2 Fabric and graphic

See `02-graphic-overlay-finding.md` (sections 2 to 5). Short version: all pieces share fabric 0; the "graphic" call replaces the base texture; the SDK has per-piece fabrics, Unified texture mapping and true graphic placement.

### 4.3 Seams, arrangement, simulation and fit

| Area | Used | Available and unused |
|---|---|---|
| **Seams** | `AddSeamlinePairGroup` (three overloads, with or without child indices) | `GetAllStitchProperty` (stitch properties), seam taping, topstitch functions, `GetSeamlinePairGroupCount/Name`, so seams could be read back and checked |
| **Arrangement** | slot list, set slot, position, orientation | `SetArrangementShapeStyle`, `ReDrape3DArrangement` (re-drape all patterns after a change), `AlignAvatarsAndGarmentToCenter` |
| **Simulation** | `Simulate(steps)` only | `SetSimulationQuality`, `SetSimulationTimeStep`, `SetSimulationGravity`, `SetSimulationCGIterationCount`, `SetSimulationCGResidual`, `SetSimulationSelfCollisionIterationCount`, `SetSimulationAirDamping`, `SetSimulationGroundCollision`, `SetSimulationNumberOfCPUInUse`, `SetSimulationLayerBasedCollisionDetection`. Per the doc comment, `Simulate` follows whatever these are set to |
| **Fit** | none | `AttachPatternToAvatarMeasure(pattern, line, measureName)`, which pins a pattern line to an avatar measurement (the programmatic version of "Attach to Measure (Avatar)") and runs the solver; `GetPatternsAttachedToAvatarMeasures`; `GetAvatarMeasurements`; `ExportPOM(true)` including 3D length; `SetSimulationLayerBasedCollisionDetection` for layered garments |
| **Stress and strain** | none | only on-screen toggles (`SetStressMapStatus`, `SetStrainMapStatus`), plus `ExportSnapshot3D` to capture an image. **No numeric stress or pressure readout was found** |

The review paper (Lyu et al.) recommends reading CLO pressure maps for fit. With this API the realistic fit signals are geometric: POM with 3D length, line lengths, bounding boxes, pattern areas, and avatar measurements.

### 4.4 Measurement checks on the draped garment

`ExportPOM(true, path)` and `ExportGarmentInformation()` are the SDK's own reports. Using them after simulation would give a per-run table of garment measurements on the avatar that we could compare to the size chart. *Unknown until tested: which points the default POM measures for our four-piece T-shirt.*

### 4.5 Outputs

| Output | SDK function | Today |
|---|---|---|
| GLB / glTF | `ExportGLB`, `ExportGLTF` with `ImportExportOption` | used; Step 12 says CLO exports a grey, untextured GLB and the texture is injected in Python |
| **Unified texture bake inside the export** | `ImportExportOption`: `bCreateUnifiedTexture`, `unifiedTextureSize`, `bUnifiedDiffuseMap` (and normal, roughness, metalness, opacity, displacement maps), `bDiffuseColorCombined`, `bExportFabric`, `bSaveInZip` | not used; could produce a textured GLB natively (the header comments mention newer `bClothUnifiedUVCoordinates` flags, but I did not find them declared in the class, so check against the real build) |
| Images and video | `ExportRenderingImage`, `ExportTurntableImages(path, count, width, height)`, `ExportTurntableVideo`, `ExportAnimationVideo`, `ExportSnapshot3D`, `ExportCustomViewSnapshot`, `ExportStdViewImage` | not used |
| Other 3D formats | `ExportFBX`, `ExportUSD`, `ExportAlembic`, `ExportOBJ` | not used |
| Reports | `ExportPOM`, `ExportBOM`, `ExportTechPack`, `ExportGarmentInformation` | not used |

---

## 5. Practical notes

- **Adding any of these means plugin work.** New endpoints, queue handlers and client methods; fabric and some other calls must run on CLO's main thread like the existing fabric calls. The repo's contract file (`plugin_contract.json`) requires the Windows and macOS plugins to match.
- **Python route for probing.** The SDK ships a Python API (functions marked `EXPORT_PYTHON`, e.g. `pattern_api.CreatePatternWithPoints`) and a sample that registers `.py` scripts under a CLO menu. It is a low-effort way to try a call such as `GetAvatarMeasurements` or `ExportPOM` inside CLO before deciding to expose it in the REST plugin. Scripts are started from the menu; CLO does not run them at startup.
- **SDK and app versions must match.** The plugin is built against `2026.1.224` and records it in `PluginBuildInfo.h`. The plugin source itself documents an earlier vtable-skew problem when the SDK and app differed.

---

## 6. Suggested order of checks (no code needed for the first three)

1. In CLO's Python console (or a menu script), call `GetAvatarMeasurements` on the template avatar and list the names. This tells us whether a trustworthy readback is usable for Step 1.
2. Import one of our DXFs twice, with default options and with `m_bIncludeNotchs = true` and `m_bAutoTraceAsInternalLines = true`; compare what appears.
3. Call `ExportPOM(true)` and `ExportGarmentInformation()` on a draped garment and read what they contain.
4. Then decide which gaps to turn into plugin endpoints, starting with the avatar readback, DXF import options and per-piece fabric with real graphic placement.

---

## 7. Where the evidence is

| Claim | Source |
|---|---|
| Plugin calls 38 functions | `grep` of `*_API->` calls in `RestPlugin_windows.cpp` |
| `Get/SetAvatarProperties` examples | `UtilityAPIInterface.h`, doc comments of `SetAvatarProperties` and `GetAvatarProperties` |
| `GetAvatarMeasurements`, `CloApiAvatarMeasurement` | `UtilityAPIInterface.h` (about line 3218), `CloApiData.h` (about line 2064) |
| Avatar texture functions | `UtilityAPIInterface.h`, `SetAvatarTexureMap`, `SetAvatarMeshTexture` |
| `ImportDxfOption` and `ExportDxfOption` | `CloApiData.h` (about lines 553 and 724) |
| Plugin's DXF import options | `RestPlugin_windows.cpp`, `import-pattern` handler (about line 1861) |
| Grading, `CreatePatternWithPoints`, `AttachPatternToAvatarMeasure` | `PatternAPIInterface.h` |
| Simulation setters, stress and strain toggles, `ReDrape3DArrangement` | `UtilityAPIInterface.h` |
| `ExportPOM`, `ExportGarmentInformation`, render and turntable exports, `ImportExportOption` | `ExportAPIInterface.h`, `CloApiData.h` (about line 133) |
| Step 12 "CLO exports a grey, untextured GLB" | docstring of `clo_vto/native_vto/step_12_texture_glb.py` |
| Python sample | `Samples/PythonPluginAutoRegister/README.md` and `sample.py` |
