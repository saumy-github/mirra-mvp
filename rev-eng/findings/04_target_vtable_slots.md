# Vtable slots of plugin-used functions (installed CLOAPIInterface.dll)

*Slot numbers include the extra vtable entries MSVC emits for overloaded functions; byte offset = slot*8.*

| API | Function | vtable slot(s) | byte offset of first |
|---|---|---|---|
| EXPORT | ExportAVT | 102 | 0x330 |
| EXPORT | ExportGLB | 78 | 0x270 |
| EXPORT | ExportGLTF | 13 | 0x68 |
| EXPORT | ExportZPrj | 4,5,6 | 0x20 |
| EXPORT | GetAvatarCount | 71 | 0x238 |
| EXPORT | GetAvatarGenderList | 74 | 0x250 |
| EXPORT | GetAvatarNameList | 72 | 0x240 |
| FABRIC | GetFabricIndexForPattern | 50,51 | 0x190 |
| FABRIC | SetBaseTextureMapImageGivenFilePath | unresolved | - |
| FABRIC | SetFabricPBRMaterialBaseColor | unresolved | - |
| IMPORT | ImportAvatar | 37 | 0x128 |
| IMPORT | ImportAvatarMeasurement | 36 | 0x120 |
| IMPORT | ImportDXF | 21 | 0xA8 |
| IMPORT | ImportFile | 1,2 | 0x8 |
| IMPORT | ImportMeasurement | 38 | 0x130 |
| IMPORT | ImportOBJ | 11 | 0x58 |
| PATTERN | AddGradingSizeGroup | 202 | 0x650 |
| PATTERN | AddSeamlinePairGroup | 161,162,163 | 0x508 |
| PATTERN | GetArrangementList | 34 | 0x110 |
| PATTERN | GetArrangementOfPattern | 35,36,37 | 0x118 |
| PATTERN | GetBoundingBoxOfPattern | 24,25,26 | 0xC0 |
| PATTERN | GetLineLength | 13,14 | 0x68 |
| PATTERN | GetPatternCount | 7 | 0x38 |
| PATTERN | GetPatternInformation | 5 | 0x28 |
| PATTERN | GetPatternInputInformation | 8,9 | 0x40 |
| PATTERN | GetPatternPieceArea | 12 | 0x60 |
| PATTERN | SetArrangement | 43 | 0x158 |
| PATTERN | SetArrangementOrientation | 42 | 0x150 |
| PATTERN | SetArrangementPosition | 41 | 0x148 |
| PATTERN | SetGradingPairedAvatarFromFile | 205 | 0x668 |
| PATTERN | SetGradingPairedAvatarSizing | 204 | 0x660 |
| PATTERN | SetPatternPieceFabricIndex | 62 | 0x1F0 |
| UTILITY | DeleteAvatar | 264 | 0x840 |
| UTILITY | DisplayMessageBox | 2 | 0x10 |
| UTILITY | GetAvatarProperties | unresolved | - |
| UTILITY | NewProject | 55 | 0x1B8 |
| UTILITY | SetAvatarProperties | unresolved | - |
| UTILITY | Simulate | 85 | 0x2A8 |

Unresolved (export-name lookup lost to identical-code-folding of stubs): ['FABRIC::SetBaseTextureMapImageGivenFilePath', 'FABRIC::SetFabricPBRMaterialBaseColor', 'UTILITY::GetAvatarProperties', 'UTILITY::SetAvatarProperties']
