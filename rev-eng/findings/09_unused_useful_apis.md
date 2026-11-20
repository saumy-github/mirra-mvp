# Header functions relevant to Mirra but not yet used by the plugin

*Status: complete (from header doc comments only; not runtime-tested)*
*Date: 2026-10-29*
*Source: SDK 336 headers. "NEW" = added in 336 vs 224.*

## Avatar measurement fitting (Step 1)
- `UtilityAPI::GetAvatarMeasurements(int avatarIndex)` -> `vector<CloApiAvatarMeasurement>` (name, type, value, basicLength, surfaceLength, unit): the only documented read-back of avatar measures; lets Step 1 verify that an imported measurement CSV / .avs actually produced the requested bust/waist/hip (full circumference, display unit). Directly addresses the "GLB identical across users" suspicion.
- `UtilityAPI::GetAvatarSubdivisionLevel/SetAvatarSmooth/GetAvatarSoftBodyStiffness/SetAvatarSoftBodyStiffness` : avatar mesh smoothing/softness for fit quality and export.
- `UtilityAPI::SetAvatarMeshTexture/SetAvatarTexureMap/SetAvatarOpacityMap` and NEW `OB_TYPE_AVATAR` material context: set avatar skin texture/colour, relevant to the planned face/skin-colour scope.
- `PatternAPI::SetGradingPairedAvatar(index, name)` / `GetGradingPairedAvatar`: pair an already-loaded avatar by name (cleaner than FromFile when avatar was imported by ImportAvatar).
- `ImportAPI::ImportPose` : apply pose files to avatar.

## Grading / sizing
- `PatternAPI::AddGradingSize(groupIdx, name)`: append sizes (S/M/L...) with propagation through all patterns, trims, pair-avatar table.
- `PatternAPI::ImportGradeRuleToSizeGroup(groupIdx, .rul)`: load a .rul grading rule file unconditionally; fastest route to a graded size set from a rule file.
- `PatternAPI::GetGradingSizeNameList/GetGradingSizeGroupCount/GetGradingSizeGroupInformation/GetCurrentGradingSizeIndex/ChangeGradingSizeInformation(groupIdx, sizeIdx)`: select a size so draping/export happens for that size.
- `PatternAPI::Get/SetPatternPointsGradingPositionOffsets`, `GetPatternPointGradingPositionOffsets(pattern, point)`: per-point, per-size grading deltas (mm, Y up) - allows writing grade rules from our size tables.
- `PatternAPI::GetPatternOutlinePoints(pattern)`: outline vertices in mm from bounding-box top-left (Y down) - verify imported DXF geometry.
- `PatternAPI::GetPatternLineInfo(pattern)`: JSON with lineCount and per-line info, replaces the plugin's zero-length probing of `GetLineLength`.

## Garment from DXF / pattern verification
- `ExportAPI::ExportDXF(path, ExportDxfOption)`: round-trip a CLO-adjusted pattern (e.g. after grading) for validation against our block generator; options include AAMA/ASTM format, with/without grading, metric, scale.
- `ImportAPI::ImportDXF` options we leave default: `m_bIncludeNotchs`, `m_bAutoScale` (see 07 flags).
- `ExportAPI::ExportPOM/ExportTechPack`: POM (points of measure) and tech pack JSON (`TechPackSpec.json` in Documents) - garment measurement read-back for fit scoring.
- `PatternAPI::GetPatternComponents` (NEW 336), `GetPatternGroupsBySeamlineConnectivity` (NEW 336): group patterns into connected garments; helps split a multi-garment scene before per-garment export.

## Seams
- `PatternAPI::AddSeamlinePairGroupPartial` (NEW 336, 3 overloads): partial-edge seams with ratio ranges and a typed `SeamlinePairGroupResult`; gives actionable errors (INVALID_LINE, RATIO_OUT_OF_RANGE...). Use for diagnosing the "Failed to create seam" generic path and for partial seams like pockets/darts.
- `PatternAPI::GetSeamlinePairGroupCount/GetSeamlinePairGroupListInPattern/GetSeamlinePairGroupName`: post-hoc verification that expected seams exist and to find the new seam's index.
- Pattern-to-avatar-measure family (NEW 336): `GetAllPatternToAvatarMeasures`, `GetPatternToAvatarMeasureByAvatar/ByPatterns/ByMeasures`, `SetPatternEdgeToAvatarMeasure`, `GetPatternEdgeToAvatarMeasureAttachment`, existing `AttachPatternToAvatarMeasure`: attach pattern edges to avatar measures so the garment follows avatar size. Potentially the cleanest way to make fit track user measurements.
- `Utility/Pattern::ReDrape3DArrangement(ImportExportOption)`: redrape arrangement after avatar change.

## GLB export per garment
- `ImportExportOption::patternList/buttonList/graphicList/zipperList` + `ExportGLTF(path, opts, true)` (NEW 336 doc): one GLB per garment from a multi-garment project. Documented route (ExportGLB lacks the doc statement).
- `ExportAPI::ExportGLTFAsFabric`: GLB of a fabric (material) selected in the Object Browser - for material previews.
- `ImportExportOption::bCreateMetallicRoughnessMap`, `bClothUnifiedUVCoordinates` + `bUnified*Map` flags: bake PBR maps into a unified UV for web viewers; `bSaveColorWays` + `bSaveColorWaysSingleFile` (KHR_materials_variants): colour variants in a single GLB.
- `ExportThumbnail3D`, NEW `ExportThumbnail2D`, `ExportStdViewImage` (6-arg NEW, fit-all option): preview renders for the website.

## PBR materials / fabrics
- `FabricAPI::GetFabricPBRMaterialBaseColor(fabric, face)` -> RGBA tuple: read back so SetFabricPBRMaterialBaseColor success can be verified (return of the setter is ignored).
- `FabricAPI::SetMetalness`, `SetRoughnessValueIntensity/SetRoughnessType/SetReflectionRoughness`, `SetNormalMapImageGivenFilePath` / `SetNormalMapIntensity`, `SetOpacityMapImageGivenFilePath`, `SetPBRMaterialDisplacementMap`, `SetMetalnessMapImageGivenFilePath`, `SetRoughnessMapImageGivenFilePath`: full PBR channels per fabric/face (face 0 front, 1 back, 2 side; the 5-arg path variants return shared-colorway names).
- `FabricAPI::AutoGenerateFabricNormalMap/RoughnessMap/OpacityMap/DisplacementMap`: derive PBR maps from a base texture for garments lacking them.
- `FabricAPI::ChangeFabricWithJson(fabric, .jfab)` / `AddFabric(.zfab|.jfab)` / `ReplaceFabric`: load a complete fabric definition (physical + PBR) from `.jfab` (see Documents/JFABSpec.json, fabric_sample.jfab): one call sets drape properties and textures; ideal for fabric presets per product category.
- `FabricAPI::AssignFabricToPattern(fabricIdx, patternIdx, option)` -> bool: returns success, unlike `SetPatternPieceFabricIndex` (void).
- `FabricAPI::SetSubstancePreset/ImportSubstanceFile*`: Substance materials.
- `FabricAPI::SetGraphicBaseColorMapTexture` and other `SetGraphic*Texture`: apply prints as graphics rather than replacing the base texture (plugin's `set-fabric-graphic` overwrites base).
- Colorway APIs (`GetColorwayCount`, `SetColorwayColorItem`, `SetCurrentColorwayIndex`, ...): multi-colour products without separate projects; combine with `bSaveColorWays`.
- `FabricAPI::TransformAOPOnFabric/SetMaterialTextureTransformations`: tile/offset/scale of textures (pattern scale control).

## Misc / robustness
- `UtilityAPI::GetActiveWorkspaceFileName` (NEW 336): confirm current file.
- `PatternAPI::Get/SetHiResTolerance` (NEW 336): hi-res garment tolerances (collision thickness, skin offset), relevant to garment-avatar clipping quality.
- `GetPatternSize` is deprecated alias for `GetPatternCount`.
