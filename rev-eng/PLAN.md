# CLO3D API Reverse-Engineering Plan

*Status: done - see FINDINGS.md*
*Created: 2026-10-29*

## Scope and rules
- All work and outputs stay inside `rev-eng/`. No changes to other repo code. No git operations.
- Static analysis only: SDK headers, `CLOAPIInterface.dll` and `.lib`, and the installed CLO binaries (`dumpbin`, strings). No license/auth bypass, no patching, no runtime hooking of CLO.
- Goal: document the CLO API functions our plugin uses, with signatures, semantics, and gaps between the header and observed behaviour.
- No new Python deps. Use stdlib, `dumpbin`, bash.

## Targets (functions used by `clo_workspace/windows/RestPlugin_windows.cpp`)
UTILITY_API: NewProject, Simulate, GetAvatarProperties, SetAvatarProperties, DeleteAvatar, DisplayMessageBox
IMPORT_API: ImportFile, ImportOBJ, ImportDXF, ImportMeasurement, ImportAvatarMeasurement, ImportAvatar
EXPORT_API: ExportZPrj, ExportGLTF, ExportGLB, ExportAVT, GetAvatarNameList, GetAvatarGenderList, GetAvatarCount
PATTERN_API: GetPatternCount, GetArrangementList, GetArrangementOfPattern, SetArrangement, SetArrangementPosition, SetArrangementOrientation, GetPatternInformation, GetPatternInputInformation, GetPatternPieceArea, GetLineLength, GetBoundingBoxOfPattern, AddSeamlinePairGroup, AddGradingSizeGroup, SetGradingPairedAvatarSizing, SetGradingPairedAvatarFromFile, SetPatternPieceFabricIndex
FABRIC_API: GetFabricIndexForPattern, SetFabricPBRMaterialBaseColor, SetBaseTextureMapImageGivenFilePath

## Steps
1. Extract call sites from the plugin source: per function, arguments passed, how the return value is used. -> `findings/01_call_sites.md`
2. Extract declarations and doc comments for each target from the SDK 336 headers (and diff against SDK 224 headers). -> `findings/02_header_signatures.md`, `findings/03_header_diff_224_336.md`
3. `dumpbin /exports` and `/headers` on `CLOAPIInterface.dll`, the `.lib` (decorated names), and the SDK interface vtable layout. -> `findings/04_dll_exports.md`
4. Inspect how the interface DLL reaches the CLO app (imports, strings, any IPC/exports into the main exe). -> `findings/05_dll_to_app_bridge.md`
5. Inspect the installed CLO exe: exported symbols, version info, strings related to target functions (error messages, param names, file formats). -> `findings/06_app_strings.md`
6. Synthesize: per-function reference table, unknowns, and next-step suggestions. -> `FINDINGS.md`

## Reproducibility
Helper scripts go in `rev-eng/scripts/`; raw tool output in `rev-eng/raw/`.
