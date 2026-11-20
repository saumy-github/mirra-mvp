# Struct / enum reference (CloApiData.h, SDK 336)

*Status: complete (static)*
*Date: 2026-10-29*
*Source: `CLOAPIInterface/include/CloApiData.h`; deltas from `raw/hdrdiff_CloApiData.diff`. Namespace `Marvelous`.*

## ImportExportOption (class, virtual dtor) - used by ImportOBJ/ImportFile/ImportAvatar/ImportAvatarMeasurement/ExportGLTF/ExportGLB
Passed **by value** to ImportAvatar/ImportAvatarMeasurement, by const-ref elsewhere. 336 appended four `std::vector` members -> size/layout differ from 224 (ABI break).

Defaults (constructor) and meaning:

| Field | Default | Meaning / notes |
|---|---|---|
| bExportGarment | true | export cloth meshes |
| bExportAvatar | true | export avatar meshes |
| bSingleObject | false | OBJ single vs multiple object |
| weldType | FULLY_UNWELDED (0) | enum: FULLY_UNWELDED 0, DEFAULT_WELDED 1 (do not use), FULLY_WELDED 2, SELECTED_WELDED 3 |
| bThin | true | thin mesh vs thick mesh |
| bUnifiedUVCoordinates | false | deprecated -> use bCloth/AvatarUnifiedUVCoordinates |
| bCreateUnifiedTexture | false | deprecated |
| unifiedTextureSize | 2048.0 | px, square; only if unified UV |
| unifiedTextureFillSeamSize | 10 | px |
| bUseInifinteSeams | false | (sic) infinite seam fill |
| unifiedTextureBakeMargin | 0.01 | |
| unifiedTextureBakeRelateive | true | (sic) |
| bUnifiedDiffuse/Normal/Metalness/Roughness/Opacity/DisplacementMap | false | export baked maps in unified UV |
| bIncludeHiddenObject | false | include hidden 3D pattern meshes |
| bIncludeInnerShape | false | export internal-line geometry |
| scale | 1.0 | multiplier. CLO unit mm for obj/fbx, m for gltf: "use 0.001 for gltf in default" |
| axisX/Y/Z | 0/1/2 | axis remap indices (no conversion) |
| bInvertX/Y/Z | false | axis inversion |
| bSaveColorWays | false | export all colorways |
| bSaveInZip | false | zip with textures |
| bDiffuseColorCombined | false | combine diffuse color into texture |
| bExcludeAmbient | false | MTL |
| bOpacityMap | false | generate opacity map from diffuse alpha |
| bMetaData | false | |
| bSizeAndPoseFromAvatar | true | (import avatar) |
| bEmbedded | false | embedded glTF |
| bExportLight | false | glTF lights |
| bExportFabric | false | glTF fabric info |
| bSaveColorWaysSingleFile | (not initialised in ctor!) | KHR_materials_variants; only with bSaveColorWays |
| bAscii, fbxSdkVersion, textureSaveMethod, bIncludeSceneProp | false,0,RELATIVE_PATH,true | FBX only, not in API |
| timeScale, fps | 1.0, 30 | vertex cache |
| m_bWeldTurnedSewingLines | true | |
| anim_step, bExportShutterSpeed, shutter_low/high, m_bExportStrain/StressColorMap, m_alembicType | 1.0,false,0,0,false,false,OGAWA | Alembic |
| bIncludeAvatarShape / bIncludeSkeleton | true / true | ZBrush/Alembic |
| m_AuthenticationKeyForAPI | "" (string) | Alvanon extended functionality |
| ImportObjectType | 0 | 0 Avatar, 1 Trim, 2 Garment |
| bAutoTranslate | false | align bottom to ground |
| bCreateCamera / AvatarJointAnimation / AvatarCacheAnimation / AvatarBlendShapeAnimation / ClothCacheAnimation | false | import toggles |
| bMoveGarment | false | move garment to start position |
| bAddArrangementPoints | false | auto add arrangement points |
| bAutoCreateFittingSuit | false | |
| bAdd | false | true = add rather than replace |
| translationValueX/Y/Z | 0 | mm offsets in 3D window (X left-right, Y up-down, Z monitor-user) |
| bTrace2DPatternsUVMap | false | |
| bCreateMetallicRoughnessMap | false | glTF; non-unified-UV metallic-roughness from diffuse alpha |
| bClothUnifiedUVCoordinates / bAvatarUnifiedUVCoordinates | false | |
| **patternList** (NEW 336) | empty | `std::vector<int>` pattern indices (RealPatternList order) |
| **buttonList** (NEW 336) | empty | `std::vector<unsigned>` uid from `GetNonFabricComponentsOnPattern`/`GetAllNonFabricComponents` |
| **graphicList** (NEW 336) | empty | uids of graphics/prints |
| **zipperList** (NEW 336) | empty | uids of zippers (expanded to tapes+hardware) |

Plugin sets: import-avatar: `scale`, `ImportObjectType=0`, `bAutoTranslate=true`; import-avatar-avt: any of `scale, ImportObjectType, bAdd, bAutoTranslate, bMoveGarment, bAddArrangementPoints, bAutoCreateFittingSuit, bSizeAndPoseFromAvatar, bIncludeAvatarShape, bIncludeSkeleton`; export: `scale=0.001, bExportGarment, bExportAvatar`.
Observation: `bSaveColorWaysSingleFile` is not initialised by the ctor or the visible init list; harmless unless bSaveColorWays is used. `copy init()` in 336 copies the four new vectors.

## ImportDxfOption (struct)
`m_bAppend=false`, `m_bAutoScale=true`, `m_Scale=1.0`, `m_Angle=0.0`, `m_bImportPatternAnnotation=true`, `m_bAutoTraceAsInternalLines=false`, `m_SwapCuttingLineAndSewingLine=false`, `m_bIncludeNotchs=false`, `m_bAutoDistribute=false`, `m_bOptimizeAllCurvePoints=false`, `m_bImportAllDrawCurvePoint=false`, `m_bRemoveNonGradingPoints=false`, `m_bConvertToSeamAllowance=false` (deprecated; seam allowance conversion is automatic when the DXF contains a detected one), `m_bImportNotchTo=true`, `m_eNotchImportPlacement=2` (0 PatternOutline, 1 SeamAllowance, 2 Both; default changed to Both to preserve old behaviour, BUG-28639).
No 224->336 delta noted in the diff. Plugin sets `m_Scale`, `m_bAppend=true`.

## ExportDxfOption (struct; not used by plugin yet)
`m_bDuplicateNotch` (336 default **true**; 224 left it uninitialised in the ctor list -> docs: "duplicate sewing-line notches on the seam allowance"), `m_bCheckedConvertCtoS=false`, `m_bExportWithoutGrading=false`, `m_bOptimizeCurvePoints=false`, `m_bExportWithoutBaselines=false`, `m_bExportSelectedPatterns=false`, `m_ExportDXFFormatType=1` (0 DXF-AAMA, 1 DXF-ASTM, 2 Gerber(DXF-AAMA)), `m_ExportBBType=1` (1 one box for all, 2 box per pattern), `m_fScale=1.0`, `m_RotateAngle=0.0`, `m_bMetric=true`.

## Enums / result types
- `SeamlinePairGroupResult` (NEW 336): `SEAMLINE_PAIR_SUCCESS=0`, `NO_PATTERN_EDITOR=-1`, `INVALID_PATTERN=-2`, `INVALID_INNER_SHAPE=-3`, `INVALID_LINE=-4`, `RATIO_OUT_OF_RANGE=-5`, `EMPTY_SEGMENT=-6` (start >= end), `CREATE_FAILED=-7`. Returned by `AddSeamlinePairGroupPartial`; test `== 0`.
- `WELD_TYPE`: see ImportExportOption.
- `MaterialTargetComponent`: `COMPONENT_FRONT=0, BACK=1, SIDE=2, BUTTON=3, THREAD=4, NONE=-1` (NONE now also for Avatar). Useful to define `materialFace` (0 front, 1 back, 2 side).
- `ObjectBrowserType`: ... `OB_TYPE_ZIPPER=6` (doc expanded), `OB_TYPE_TOPSTITCH=10`, **`OB_TYPE_AVATAR=11` NEW** (objectIndex = avatar index, subItemIndex = mesh index).
- `HI_RES_TOLERANCE_TYPE` (NEW): PARTICLE_DISTANCE 0, COLLISION_THICKNESS 1, SKIN_OFFSET 2.
- `ButtonPairEdgeOrigin` (NEW) plus `ButtonPairPlacementOption` (button placement helpers, not relevant).

## CloApiAvatarMeasurement (struct, returned by `UtilityAPI::GetAvatarMeasurements(int avatarIndex)`)
`std::string measurementName`, `measurementType` ("Tape", "Circumference", "Height", "Linear" or "Default"), `float value` (active-shape length: basic or surface fit, in `unit`), `float basicLength` (convex-fit), `float surfaceLength` (surface-fit), `std::string unit` ("mm", "cm" or "in" = current CLO display unit). Defaults 0.0f. Empty list if no avatar or bad index. **Important for Mirra:** value is a *full circumference length for Circumference-type measures* (not half-girth), expressed in the CLO display unit (not necessarily mm).

## Other structs relevant to the SDK but unused by the plugin
- `ObjectBrowserContextOptions`, `MaterialContextOptions` (material-level get/set by object browser context: type, targetPrint, styleChipIndex, subItemIndex, folderName; targetComponent, materialType).
- `CloApiPoint` (2D coordinate for internal-line geometry APIs).
- `ExportUSDOption`, `RenderImageVideoOptions`, `ExportTechpackOption` (not used).
