# Lane Q: structure of a garment-bearing CLO project (.zprj) from Step 3 / ExportZPrj

*Status: done (static analysis only; CLO not run; nothing written outside rev-eng/)*
*Date: 2026-10-29*
*Code: `scripts/zprj_probe.py` (`info`, `tree`, `diff`; reuses `scripts/avs_grammar.py`). Run `python -I scripts/zprj_probe.py info FILE.zprj`.*
*Tags: [V] = reproduced by code on real files; [I] = inference, not proven.*

All integers little-endian. Offsets decimal unless `0x`. 2D lengths are millimetres, 3D positions are millimetres, Y up.

## 1. Which .zprj files exist

Searched read-only under `output/` (does not exist at repo root), `clo_vto/` and `clo_avatar_generation/output`.

| Group | Count | Garments? | Notes |
|---|---|---|---|
| `clo_vto/output/<u>/<c>/<s>/<run>/simulation.zprj` | 8 (36.9-37.0 MB, 2026-09-12 and 2026-10-14) | **yes**, all 8 | u_001/c_001/002, u_001/c_005/002, u_011/c_001/001, u_012/c_001-s_002/001, u_013/c_002/001, u_014/c_003/001, u_015/c_004/001, u_adhoc/004 |
| `clo_avatar_generation/output/*/result_project.zprj` | 51+ (32.5-36.3 MB, 2026-04-07 .. 2026-10-18) | no (avatar only) | covered by file 10 section 2.2 |

Every garment project was produced by the `default_panels` mode (`run_report.json` `"mode": "default_panels"`; patterns from `clo_vto/default_panels/dxf`). So all 8 contain the **same 4-piece T-shirt geometry** (identical 2D bounding boxes and vertex counts, section 5) regardless of the ingestion output (`c_00x`) they were notionally built for. [V]

## 2. Outer container and member table [V]

`simulation.zprj` = CLO header (`" ZPRJ       CLO "`, version 12) + ZIP. u_001/c_001/002: PNG thumbnail at 242 (78,179 B), ZIP at 268,161 (header 0x20), ZIP length 36,716,911 (0x24), timestamp 0x28 = 2026-09-12T14:49:32Z. Id string at 0x40 = `ce79e2364d4404e9798a` (same id as the base avatar). Layout of the header: see file 10 section 2.

The project name is the file stem (`simulation`; avatar-only runs use `result_project`). Members (u_001/c_001/002; sizes identical in kind across the 8 runs):

| Member | Bytes | Format | Role |
|---|---|---|---|
| `img_3dwindow_bg_Modelist.png` | 1,274 | PNG | 3D window background |
| `simulation.osw` | 1,928 | typed stream | scene object list: avatar + cloth links (section 7) |
| `simulation.xml` | 2,533 | XML | Environment 6.0 |
| `simulation.cmt` / `.cmp` | 178 / 63 | text, fields separated by `\|^^\|` | camera transform (16 floats = 4x4, tz=8161.67) / camera params `15.0 100.0 100000.0` = Fov, Near, Far |
| `simulation.cpt` | 671 | typed stream | camera list (`Default Camera`, `fSensorWidth`, `Fov` ...) |
| **`simulation_0.avt`** | 34.3 MB | CLO `AVT` (header + ZIP, one `.dan`) | the avatar as CLO re-saved it (not byte-identical to the pipeline's `result_avatar_from_project.avt`: 34,303,754 vs 34,304,172 B, header timestamps differ) |
| **`simulation.zpac`** | 582,832 | CLO `ZPAC` container (header + ZIP) | **the garment** (section 3) |
| `simulation.smp` | 1,686 | typed stream | simulation properties; the same `mapSMP` content is also inside the .pac (section 6) |
| `simulation.vmp` / `.vlp` / `.vrp` | 417 KB / 1.6 MB / 979 | CLO `VMP`/`VLP`/`VRP` (header + ZIP) | V-Ray render/media, light, render presets (vignette jpg, `Studio_LowContrast.hdr`); identical in kind to avatar-only projects |
| `displaysettings.json`, `snapshotoptionsettings.json`, `fitmapsettings.json` | 2.2 KB, 7.6 KB, 4.2 KB | JSON | UI/display state |
| `clofiles.json` | 1,882 | JSON | member name -> absolute path in CLO's temp cache |

Compared with an avatar-only `result_project.zprj` (e.g. g_e5c37ff7a450d060-001): the only structural additions are the `.zpac` member and the larger `.osw` (1,928 vs 1,910 B, which now has `qsClothFilePath = "simulation.zpac"`, `uiClothLink = 1`). All other members keep the same sizes (+/- a few bytes). [V]

## 3. The `.zpac` (garment) container [V]

`simulation.zpac` is again a CLO container: magic `" ZPAC       CLO "`, version 12, PNG at 242 (86,665 B), ZIP at 87,909. Members:

| Member | Bytes | Format | Role |
|---|---|---|---|
| **`simulation.pac`** | 1,495,821 | **typed stream**, whole file parses and re-encodes byte-identically with `avs_grammar.py` (`roundtrip` ok 1/1) | all garment data: patterns, seams, fabric, colorway, avatar link, simulation settings |
| **`simulation.pos`** | 166,678 | CLO `POS` header (PNG thumb at 261, 37,550 B) + **raw typed stream at 38,542** (header 0x20/0x24; not a ZIP) | avatar posture (`qsAvatarID`, `mapInitPoseData`, `mapTransformer3D`, `listTf3DToHIKNodeId` ...); no cloth data |
| `sleeve_right_texture.png` | 2,367 | PNG 373x242 (u_001 run) | the texture that survived on the fabric (section 6) |
| `seam_puckering_2ol97pf293f2sdk98.png`, `sijub01.jpg` | 114 KB, 22 KB | PNG, JPEG | default puckering resources CLO always bundles |
| `displaysettings.json`, `clofiles.json` | | JSON | `clofiles.json` records `sleeve_right_texture.png` -> `C:/D-drive-data/mirra-mvp/product_ingestion/output/c_001/s_001/001/panels/textures/sleeve_right_texture.png`: the absolute ingestion path, i.e. the only link from a project to its `cloth_id`/`size_id` |

`.pac` is a stream of the same grammar as file 13 (u8 n, namelen[n], type[n], u32 size[n], interleaved name/value). Types used beyond file 13's table: 0x05 u32, 0x07 f64 (`dAnimationFPS`), 0x0d 3x3 matrix (36 B, `m3LtoUV`, `m3Matrix`), 0x08 (68 B and 224-240 B opaque blobs: `sFilePath`, `sEncKey2`), 0x17 not seen here. 0x15 arrays carry `u32 count, u8 elemtype, packed`. [V]

## 4. `.pac` top-level layout (offsets are key paths) [V]

Top-level keys in file order: `qsClothIDListUTF8` ("Default"), `mapObjectBrowserGroup`, `uiTSSVersion`=1, `uiVersion`=1001 (0x3e9), `uiSaveType`=0, `qsClothIDList`, `mapGarmentRiggingManager`, `mapGarmentInformation` (JSON strings `{colorway,description,fabric,name,pattern}` all empty, `ItemOrder` list of 9 strings), `listClothFileInfo` (encryption-key blobs `qsEncKey`, `sEncKey2` that change at every save), `mapColorWay`, `mapClothController` (empty), `mapUserSettings` (`enLengthUnit`=4), **`mapPatternEditor`** (53 keys), **`listFabric`**, button/trim/zipper style lists (all empty), `mapAvatar`, `listTemplateSkinsuitPosition`, **`mapSMP`**, `mapKeyFrame`, `mapSketchManager`, `mapMetaverseConverterMap`.

`enLengthUnit = 4` is stored but the 2D data is millimetres (section 5). [V for value, I for the enum meaning]

## 5. Patterns, outlines, seams [V unless noted]

`mapPatternEditor/mapPatternList` has `listPattern` (4 items), `listInstance` (4 items, each `arrInstanceIndex`; all 0), `arrSymmetricIndex` (`04 | 04 | -1 x4` i.e. n=4 int array with all -1 = no symmetry partners), `listSizeName` (empty).

`listPattern[i]` has 74 keys. The ones that matter:

| Key (relative to `listPattern[i]`) | Content |
|---|---|
| `mapElement/qsName` | **the SDK pattern name**: `"1"`, `"2"`, `"3"`, `"7"` for index 0..3 (equals `run_report.json diagnostics.sdk_pattern_names`). Not "front_panel": the DXF piece names are not stored. |
| `mapElement/uiID`, `qsUuid` | per-session numeric id; random uuid (changes on every run) |
| `mapArrange` (12 keys) | arrangement slot used: `qsName`, `qsPanName`, `enType`=1 (Curved), `fOffset`, `fAngle`, `fNormalizedHeight/ArcLength`. Index 0 = `Body_Front_Center_3`/`Body_R`; 1 = `Body_Back_Center_3`/`Body_R`; 2 = `Arm_Outside_1_L`/`Arm_L`; 3 = `Arm_Outside_1_R`/`Arm_R` (matches `slot_map` 61, 44, 18, 19 in the run report) |
| `mapShape2D/listPoint[k]/v2Position` | **2D outline vertices**, 2 x float32, **mm**, pattern-local, origin at the piece centre. Front: 10 points `(0,258.2) (97.9,359.3) (233.3,305.2) (290.1,53.0) (270.0,-359.3) (0,-359.3) (-270,-359.3) (-290.1,53.0) (-233.3,305.2) (-97.9,359.3)`; bbox 580.2 x 718.6 mm. Sleeves: 5 points, bbox 490.3 x 245.1 mm |
| `mapShape2D/listLine[k]` | edge k: `uiStartIndex`, `uiEndIndex` (point indices), `iLineType` (0 straight, 2 curve), `listPoint` (23-28 curve control points, present on curves only), `listMeshPoint`, `mapGID` (`uiPatternGID`, `uiLineGID` = k+1, `sFilePath` blob), `mapSALineOptions`, seam-allowance options |
| `mapShape2D/baSAPositions`, `baSAPointTypes`, `nSAPointCount`=160 | seam-allowance outline points (160 per front piece) |
| `mapFabricShape2D/iFabricIndex` | **fabric index assigned to this pattern** (0 for all four; the sibling `mapShape2D/iFabricIndex` = -1 means "none/inherit") |
| `mapFabricShape2D/mapMesh2D` | triangulated 2D mesh: `uiVertexCount2D` (1626/1717/401/406), `uiTriangleCount` (3118/3306/737/747), `baRest` (vertices x 8 B: x,y floats, rest-pose 2D position in the 2D window, mm), `baTex` (vertices x 8 B: texture/pattern-local 2D, same frame as `v2Position`, e.g. first vertex `(-0.0001, 258.2)`), `baTri` (3 x u32 per triangle), `listMeshPoint` |
| `baPosition3D` | **simulated 3D vertex positions**, 3 x float32 per mesh vertex (19,512 B = 1626 x 12), mm. Front bbox X -224.6..228.2, Y 931.9..1620.2, Z -57.5..151.4 (garment hangs on a ~188 cm avatar). This is the draped result of the 150-step simulation. |
| `fEdgeLength` | **20.0** on all pieces; this is the mesh edge length, i.e. CLO's "Particle Distance" in mm [I: name inferred from value/role; no exe string `ParticleDistance` exists] |
| `mapOriginPatternPhysicalProperty` | per-pattern copy of the fabric physical property (46 keys) |
| `m4OffsetMatrix` | identity (pieces are positioned by the arrangement + simulation, not by this matrix) |
| `bVisible3D`, `bSymmetricSewing`, `GrainLineOrientation`, `mapSymmetry`, `listPin` (0), `listInnerShape` (0) | flags |

Pattern index order (0 = front, 1 = back, 2 = sleeve_left, 3 = sleeve_right) is the load order and equals the `piece_to_index` map in the run report. This is the `patternIndex` that PatternAPI takes (file 12 section 1: 0-based index into the filtered scene pattern list). [V that the stored order matches; the API link is from file 12]

### Seams: `mapPatternEditor/mapSeamLinePairGroup/listSeamLinePairGroup` (10 items) [V]

Each seam group has `listParamLineGroup0` and `listParamLineGroup1` (one `ParamLine` each) with `uiSelfIndex` = **pattern index**, `uiStartIndex`/`uiEndIndex` = **edge index in that pattern** (equal for a whole-edge seam), `fRatioStart/End` (0..1 along the edge; reversed 1..0 gives the opposite direction), `bDirection`, `uiDepth`=1; plus `listThickParamLineGroup0/1` (seam allowance rendering), `mapElement/qsName` = `Sewing_<id>`, `fSeamlineRipResistance`. The creation order equals the list order:

| # | Group0 (pattern.edge) | Group1 (pattern.edge) | Matches `seams.py DEFAULT_SEAMS` |
|---|---|---|---|
| 0 | 0.1 | 1.3 | shoulder-right (front 1, back 3) |
| 1 | 0.8 | 1.6 | shoulder-left |
| 2 | 0.3 | 1.1 | side-right |
| 3 | 0.6 | 1.8 | side-left |
| 4 | 2.0 | 2.3 | sleeve_left tube (cuff <-> cap_back) |
| 5 | 3.0 | 3.3 | sleeve_right tube |
| 6 | 0.7 | 3.1 | front armhole <-> sleeve_right edge 1 |
| 7 | 1.7 | 3.2 | back armhole <-> sleeve_right edge 2 |
| 8 | 0.2 | 2.1 | front armhole <-> sleeve_left edge 1 |
| 9 | 1.2 | 2.2 | back armhole <-> sleeve_left edge 2 |

A second copy (`mapSeamLinePairGroupWithHalfSymmetry`, 10 items) and `mapEditLinkPairGroup` (empty) exist. So `AddSeamlinePairGroup(patA, edgeA, dirA, patB, edgeB, dirB)`-style API arguments map one-to-one onto `uiSelfIndex/uiStartIndex/bDirection` of the two param lines (`bDirection` True with ratio 0->1, False with ratio 1->0). [V for fields; I that no extra transform is applied]

## 6. Fabric, colorway, PBR, simulation [V]

`listFabric` has **one** fabric, `FABRIC 1` (`uiID`, `qsUuid`, `fWidth` 1117.6, `fHeight` 359.294, `mapPhysical`, `mapColorwayInfo`, `mapMaterial2D`, `listFabricFileInfo`, `mapCostInfo`). All four patterns point to it (`iFabricIndex` 0). Step 8's `set_fabric(idx, fabric_index=0)` therefore does not create per-piece fabrics.

| Concept | Path | Value (u_001/c_001 run) |
|---|---|---|
| Colorway list | `mapColorWay/listColorway[0]` | `qsName` "Default Colorway", `qsUuid`, `uiID`, `v4MainColor` (-1,-1,-1,1 = unset), `uiColorwayMainFabricUID` = the fabric's `uiID` |
| Colorway count/selection | `mapColorWay/uiCurrentCoordinationIndex` = 0; `mapColorwayInfo/uiCurrentCoordinationIndex` = 0 | colorway index 0 is the only one; `bIsTheNewColorway`=True |
| Per colorway fabric material | `listFabric[0]/mapColorwayInfo/listColorwayInfo[c]/listMaterial2D[0]/listFaceMaterial[0]` and `.../listFaceMaterial[0]` (front face); the same material is mirrored in `mapMaterial2D/listFaceMaterial[0]` | **indexed by colorway c then face** |
| Base colour | `.../v3BaseColor` (3 x float32, sRGB/255) and `mapDiffuseColor/v4Color`, `mapAmbientColor/v4Color` with `qsName` = hex string | 27283B -> (0.1529, 0.1569, 0.2314). `v4Diffuse` = base x `fDiffuseIntensity` 0.8196 (0.1254..), `v4Ambient` = base x 0.2571 |
| PBR | `bUseMetalnessRoughnessPBR`=True, `fMetalness`=0, `fGlossiness`=0.5 (roughness-like), `fShininess`=28.76, `fReflectionIntensity`=0.15, `fIOR`=1.5, `fFresnelIOR`=1.5, `fAlphaCutoff`=0.5, `v4Specular` 0.075 grey, `iMaterialType`=0 | defaults of a plain fabric |
| Texture | `.../listTexture[0]`: `qsFileName` `sleeve_right_texture.png`, `enWrapS/T`=10497 (GL_REPEAT), `enMinFilter` 9987, `enMagFilter` 9729, `v2Size`=`v2PhysicalSize` (153.8 x 111.5), `fUnifiedScale` 0.001, `bTileTexture`=False | **one** texture on the **shared** fabric |
| Physical (drape) | `mapPhysical`: `fSuK`=`fSvK` 100000 (stretch), `fBuK` 100, `fBhK` 150, `fLeftShearK` 5000, `fBLeftShearK` 150, `fDensity` 0.0003, `fFriction` 0.03, `fThickness` 0.5, `fIDS` 0.0001, `qsPhysicalPropertyName` "Default" | CLO default fabric ("Default"); not set by the pipeline |
| Simulation | `mapSMP`: `mapDeforMarvelProperty/fGravity_y` **-9800** (mm/s^2), `fGravity_x/z` 0; `fEntireTimeStep` 0.033333, `uiSubStepCount` 1, `uiCGIterationCount` 50, `uiThreadCount` 11, `bGroundCollisionHandling` True, `bNonlinearSimulation` False; `mapPinchingOverride` (`fGravity` -9800, `fEntireTimeStep` 0.01, `fAirDamping` 100000, `fFriction` 0.03, `fDensity` 0.0003) | the same dictionary is stored a second time in `simulation.smp` |
| Particle distance | `listPattern[i]/fEdgeLength` | 20.0 mm [I name] |
| Simulated state | `listPattern[i]/baPosition3D` | positions, no velocities saved [V: no other per-vertex array found] |

### Finding: the fabric carries only the last texture [V observation, I cause]

Step 8 calls `set_fabric_texture(piece_idx, ...)` for four panel textures but the project has one fabric and one `listTexture` entry, always `sleeve_right_texture.png` (the last piece applied). Across the 7 textured runs the saved `listTexture[0].qsFileName` is `sleeve_right_texture.png`; the only run without a texture (u_adhoc/004) has an empty list and base colour FFFFFF. This agrees with step_08's own comment that the atlas "renders wrong". [I] the texture API acts on the shared fabric, not on the pattern.

### Colours observed (hex name = `colors.json` `base_colour_hex`, written verbatim into `qsName`)

u_001/c_001: 27283B; u_001/c_005: C51A29; u_011/c_001: 27283B; u_012/c_001: 27283B; u_013/c_002: F44C83; u_014/c_003: 182C2A; u_015/c_004: 3C2925; u_adhoc: FFFFFF (no colours.json). `set_fabric_color(idx, r, g, b)` writes into **colorway 0 / fabric 0** (there is only one). [V]

## 7. Garment <-> avatar link [V]

* `simulation.osw`: `listAvatarFilePath = ["simulation_0.avt"]` (relative member name), `uiAvatarCount = 1`, `uiAvatarLink = 1`, `qsClothFilePath` / `qsClothFilePathUTF8 = "simulation.zpac"`, `uiClothLink = 1`, `uiScenePropCount = 0`, `qsAnimationFileName = "NULL"`. The link is by member file name; no uuid.
* In the `.pac`: `mapAvatar/qsAvatarID` and `mapPatternEditor/mapPose/qsAvatarID` = `5.1_MaleTemplate_07` (the **template id**, identical for every user), and `mapAvatar/mapResizingAvatar` embeds a full copy of the avatar's size state: `listFeatureValues` (67 floats) etc. Examples (height/chest/waist/low hip, cm): u_001/c_001 187.96/96.52/82.55/95.25 (the unpatched base), u_001/c_005 178.5/100/85/98, u_011 168/92/76/92, u_012 175/98/82/96, u_013 181/106/92/104, u_014 186/100/84/98, u_015 186/112/98/108. So the **only** per-user identity inside the project is the measurement vector (plus `iPelvisID` and node uiIDs in `.pos`, which are session-random). There is no user id, avatar uuid or run id string anywhere in the project. [V by scan of `.pac`, `.osw`, `.pos`, JSON members]
* The cloth id/size id survive only inside `clofiles.json` paths (`.../product_ingestion/output/c_001/s_001/001/panels/textures/...`). [V]
* `simulation.pos` repeats `qsAvatarID` and the pose transforms (`mapInitPoseData`, `mapDefaultTransformer3D`, `mapTransformer3D`, 94 `listTf3DToTposeLtoW`, 80 `listTf3DToHIKNodeId`): it is the posture the garment was draped on.

## 8. Run-to-run differences (what is session noise) [V]

`zprj_probe.py diff` of u_011 vs u_012: the 4 pattern geometries are identical; 2190 `.pac` leaves differ, all of these classes: random `qsUuid`s, `uiID` counters (443532 vs 930061, grow with session age), `FABRIC 1_FRONT_<id>`, save time `listFabricFileInfo/qsTime`, per-save `sEncKey2`, `v2Size` (follows the PNG size) and the user-specific `listFeatureValues`. Also **uninitialised memory is serialised**: `mapDenim/enPaintState`, `iShadowGray`, `iShadowIntensity` and `knitwearMap/graph/p0,p1` read as ASCII fragments (`stEv`, `tion`, `t:ac`, `ange`, `"/> `, `d="/`) that differ from save to save, so a byte-exact comparison of two saves is never clean.

## 9. Mapping to API concepts used by the plugin

| Plugin/API concept | Field in project | Notes |
|---|---|---|
| `patternIndex` (all PatternAPI) | position in `mapPatternList/listPattern` | 0 = front, 1 = back, 2 = sleeve_left, 3 = sleeve_right. Pattern *name* returned by SDK = `mapElement/qsName` ("1","2","3","7") |
| `GetArrangementOfPattern`, `SetArrangement(pat, slot)` | `listPattern[i]/mapArrange` (`qsName`, `qsPanName`, offsets, `fAngle`) | slot names match run-report slot_map |
| Edge index (`lineIdx`, seam edge) | order of `mapShape2D/listLine`, `mapGID/uiLineGID` = edge+1 | `uiStartIndex`/`uiEndIndex` of a seam param line index this list |
| `AddSeamlinePairGroup` | one `listSeamLinePairGroup` item; `uiSelfIndex` (pattern), `uiStartIndex` (edge), `fRatioStart/End`+`bDirection` | creation order preserved |
| `SetPatternPieceFabricIndex(pat, fabricIdx)`, `GetFabricIndexForPattern(pat, colorway)` | `mapFabricShape2D/iFabricIndex` | fabric order = `listFabric` order (here only 0) |
| colorway argument of fabric calls | index into `mapColorWay/listColorway` and `listFabric[f]/mapColorwayInfo/listColorwayInfo[c]` | the pipeline always uses colorway 0 ("Default Colorway") |
| `SetFabricPBRMaterialBaseColor(fabric, colorway, r,g,b)` | `listFaceMaterial[0]/v3BaseColor` (+ `mapDiffuseColor`, `mapAmbientColor`, `v4Diffuse`, `v4Ambient` recomputed) | note: values stored as sRGB/255, the hex string becomes `qsName` |
| `SetBaseTextureMapImageGivenFilePath` | `listTexture[0]/qsFileName` (+ the PNG added to the .zpac) | file name only; the absolute path lives in `clofiles.json` |
| simulate(steps) | `baPosition3D`, `mapSMP` | steps count is not stored; gravity/time step are |

## 10. What was NOT determined

* Whether `fEdgeLength` is exactly the UI "Particle Distance" (only value/role evidence, section 6).
* The meaning of `enLengthUnit = 4`, `uiSaveType`, `iLineType` values other than 0 and 2.
* Which of `baRest` and `baTex` is read by a loader (both x,y floats; `baRest` has translated coordinates, `baTex` is pattern-local).
* Anything about garments produced by real product-ingestion panels: no such .zprj exists (all `default_panels`).
* Exe `.rdata` check: all the key strings above (`listPattern`, `mapPatternList`, `listSeamLinePairGroup`, `listParamLineGroup0`, `listFabric`, `mapColorWay`, `mapColorwayInfo`, `listFaceMaterial`, `v3BaseColor`, `fEdgeLength`, `mapSMP`, `fGravity_y`, `qsClothFilePath`, `listAvatarFilePath`, `baPosition3D`, `baRest`, `mapArrange`, `qsPanName`, `listTexture`, `mapPhysical`, `mapAvatar`, `listClothFileInfo`) occur in `CLO_Standalone_OnlineAuth_x64.exe` (read-only mmap scan, first hits 0x828fc88 .. 0x8a5b850 in file offsets), so the property names are CLO's own serialisation keys and not Mirra-specific. [V]
