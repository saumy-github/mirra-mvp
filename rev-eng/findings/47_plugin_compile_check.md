# 47 Plugin compile check (lane AX)

*Status: complete. Static/syntax-only; nothing built, deployed or launched.*
*Date: 2026-10-30*

## 1. Build logs (clo_workspace/logs, read-only)

| log | outcome |
|---|---|
| build_plugin_windows_20261029T093626Z.log (latest) | SUCCESS. cmake configure + `--build . --config Release` ran; artifact `...CLO_SDK_v2026.1.336_Win\Samples\RestPlugin\build\Release\RestPlugin.dll`, vault copy `C:\D-drive-data\plugins\mirra-vault\RestPlugin_v1.3.2.dll` |
| build_plugin_windows_20261029T093215Z.log | Incomplete: cmake configure line only, no build step, no artifact line (738 bytes). Superseded by the run above. |
| 20261015 logs | older SDK-era builds (not examined further) |

- Plugin: CLO REST Automation 1.3.2 (status unstable), built against SDK folder CLO_SDK_v2026.1.336_Win.
- DLL: 738816 bytes, timestamp 2026-10-29 15:06:41 (log id 09:36:26Z), identical in build dir and vault.
- Installed CLO: CLO_Standalone_OnlineAuth_x64.exe ProductVersion 2026.1.336.58954. The DLL is already present as `C:\Program Files\CLO Standalone OnlineAuth\plugins\RestPlugin_v1.3.2.dll` (same timestamp 15:06:41), so it is installed. Plugin SDK version (336) matches the CLO app (336). (Note: Uninstall.exe in that folder still reports 224; irrelevant.)
- plugin_crash_trace.log (37 MB, last modified 20:22 on 10-29) exists; not analysed here.

## 2. Syntax-only compile (MSVC, /Zs)

Commands (batch file wrapper per SDK in out/compile_check/run_336.bat and run_224.bat; cwd = rev-eng\out\compile_check):

```
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
cl /nologo /EHsc /std:c++17 /W3 /Zs ^
  /I"<SDK>\CLOAPIInterface" /I"<SDK>\CLOAPIInterface\include" ^
  /I"C:\D-drive-data\mirra-mvp\clo_workspace\windows" /I"C:\D-drive-data\mirra-mvp\clo_workspace\shared" ^
  /DUNICODE /D_UNICODE /DBOMAPIDLL_EXPORTS C:\D-drive-data\mirra-mvp\clo_workspace\windows\RestPlugin_windows.cpp
```
`<SDK>` = `C:\Users\Saumy\Downloads\CLO_SDK_v2026.1.336_Win` or `...\CLO_SDK_v2026.1.224_Win`. Run from PowerShell via `cmd /c <bat>`. (First attempt with `/W0` default and inline `cmd /c "call vcvars64 && cl ..."` also gave 0 errors; vcvars prints a harmless "vswhere.exe not recognized" line.) Raw output: raw/compile_check_336.txt, raw/compile_check_224.txt.

| SDK | verdict | errors | warnings |
|---|---|---|---|
| 336 | PASS (EXITCODE=0) | 0 | 1: C4267 at RestPlugin_windows.cpp(2560) size_t to int (pre-existing, unrelated to API) |
| 224 | PASS (EXITCODE=0) | 0 | same single C4267 |

No error appears only against one SDK. The source compiles against both header sets.

## 3. API drift analysis (header diff 224 vs 336)

Files that differ: CloApiData.h, ExportAPIInterface.h, PatternAPIInterface.h, UtilityAPIInterface.h (plus GuiAPIInterface.h hash differs).

- ExportGLTF: signature `ExportGLTF(const std::string&, const Marvelous::ImportExportOption&, bool _bGLBinary)` unchanged; in 336 only doc comments are added (ExportGLTFW, component-selection lists). Arity matches the plugin's call at cpp:1944 (`ExportGLTF(cmd.param1, options, false)`).
- ImportExportOption: 336 adds members `patternList`, `buttonList`, `graphicList`, `zipperList` (component-selection export; empty = whole scene). The plugin does not reference them (grep: none), so no compile impact. They are an additive field opportunity (per-garment GLB export) but change struct size/layout.
- By-value ImportExportOption: the plugin declares `Marvelous::ImportExportOption options;` locally (cpp:1714, 1731, 1780, 1932) and passes by const reference to the export API; the 336 API takes `const&`. No by-value-parameter warning from /W3 (only the C4267 above). Because the struct grew in 336 (4 vectors), any plugin built against 224 and run in a 336 host (or vice versa) would have a size mismatch; with the 336 rebuild plus host 336 this is consistent.
- RemovePatternFromAvatarMeasure: present in 224 PatternAPIInterface.h (lines 1731, 1740), absent from 336. The plugin does not call it (grep: none), so no break. Anything else (pipeline code) depending on it should be checked separately.
- Additive in 336: ExportThumbnail2D, ExportStdViewImage with _bFitAllObjects, single custom-view render virtuals (appended at end of Export), AddSeamlinePairGroupPartial x2 and SeamlinePairGroupResult enum, GetActiveWorkspaceFileName(W), ConvertTrimsToButtons, CreateButtonholesForButtonHeads, FastenButtons, UnfastenAllButtons, GetButtonPairInfoAsJson, ExportDxfOption m_bDuplicateNotch, OB_TYPE_AVATAR/ZIPPER/TOPSTITCH, subItemIndex.
- Caveat: /Zs against 224 passing is a syntax result only; it says nothing about vtable/ABI correctness of a 224-built DLL in a 336 host. The 336-built DLL is what is deployed.

## 4. ABI status (scripts/abi_check.py)

Command (run from rev-eng; non-default tag so findings/14_* is not overwritten; report redirected to out/):
```
python -I scripts/abi_check.py --tag cc47 --out-dir C:\D-drive-data\mirra-mvp\rev-eng\out\compile_check
```
Outputs: out/compile_check/14_abi_check_report_cc47.md, raw/abi_check_cc47.json.

Verdict: PASS (fails 0, unverified 0). SDK folder 2026.1.336 matches exe ProductVersion 2026.1.336.58954; PluginBuildInfo.h SDK folder matches. Vtable slot counts header vs exe all within expected deltas (Export 124/124, Utility 408/409 +1, Fabric 285/285, Gui 39/40 +1, Import 45/45, Pattern 233/234 +1, Rest 9/11 +2). Named-anchor agreement 100% with no divergence for Export, Utility, Fabric, Gui, Import, Pattern, Rest.

## Verdict summary

- Build log: latest build (09:36:26Z) succeeded, produced RestPlugin.dll / RestPlugin_v1.3.2.dll v1.3.2 vs SDK 336 = installed CLO 336; already present in CLO plugins folder.
- Compile 336: PASS. Compile 224: PASS. Same single unrelated warning.
- ABI check: PASS.
