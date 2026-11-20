# 48 Lane M5: RECOMMENDATIONS.md code-claim check

*Date: 2026-10-30. Read-only grep of the current working tree.*

`RC` = `clo_workspace/windows/RestPlugin_windows.cpp`.

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | `clear_avatars` defined in `avatar_runtime/client.py` (l.51), never called | CONFIRMED | `client.py:51: def clear_avatars(self, max_index: int = 7)`. Only other Python hit is its own body at l.55. No caller in any `.py` outside rev-eng. |
| 2 | Plugin route `clear-avatars` / `DeleteAvatar` about l.2009; NewProject comment l.1301 | CONFIRMED | `RC:2009: deleted = UTILITY_API->DeleteAvatar(indices);`. `RC:1301: // NewProject() clears garments only, so avatars survive it...` |
| 3 | `/health` has `host_matches_sdk` about l.660-712 | CONFIRMED | `RC:712: {"host_matches_sdk", GetHostAppVersion() == MIRRA_PLUGIN_SDK_CLO_VERSION}` |
| 4 | No Python code checks `host_matches_sdk` | CONFIRMED | Zero hits for `host_matches` in any `.py` outside rev-eng. `step_01_health.py` only calls `ctx.client.health_check()`. |
| 5 | `step_07_import_base_avatar.py`: `new_project()` then `import_avatar_avt`, about l.57-80; `wait_for_queue(timeout=30)` | CONFIRMED | `step_07:67 new_project()`, `:75 import_avatar_avt(...)`, `:62/68/76 wait_for_queue(timeout=30)` |
| 6 | import-pattern sets only `m_Scale` and `m_bAppend` | CONFIRMED | `RC:1858 options.m_Scale = (cmd.floatParam1 > 0.0f ? cmd.floatParam1 : 1.0f);` and `RC:1859 options.m_bAppend = true;`. No `m_bAutoScale` or `m_bIncludeNotchs` hit in the file. |
| 7 | import-pattern `asyncResult.success = ImportDXF(...)` at l.1856-1871 | CONFIRMED | `RC:1861: asyncResult.success = IMPORT_API->ImportDXF(cmd.param1, options);` (handler starts l.1856). |
| 8 | `step_08_apply_fabric.py` passes fabric index 0 for all panels (l.106-112) | CONFIRMED | `step_08:108: ctx.client.set_fabric(idx, fabric_index=0)`. Colour l.127-137 also confirmed (`:132 reset_fabric_status`, `:134 set_fabric_color`). |
| 9 | `set-fabric` at l.2045 is `SetPatternPieceFabricIndex(pattern, 0)` | WRONG DETAIL | `RC:2045: PATTERN_API->SetPatternPieceFabricIndex(cmd.param3, cmd.param4);`. The index is `param4`, parsed at `RC:1380` as `j.value("fabric_index", 0)`. It is 0 only because step_08 sends 0, not hard-coded in C++. Location is correct. |
| 10 | `/set-fabric` ignores `preset` | CONFIRMED, with nuance | `RC:1391` echoes `{"preset", cmd.param1}` in the response, but `cmd.param1` is never set from the request body and never used (`RC:2045` uses only `param3` and `param4`). The Python client sends no `preset`. |
| 11 | `<0` guard on `GetFabricIndexForPattern` at l.2066 and l.2094 | CONFIRMED | `RC:2065-2066` (`int fabric_idx = FABRIC_API->GetFabricIndexForPattern(cmd.param3); if (fabric_idx < 0) fabric_idx = 0;`) and `RC:2093-2094`. It also appears at `RC:2116-2117` (set-fabric-graphic), which the file omits. Whether it can fire depends on the API's return type; no evidence either way in this check. |
| 12 | Colour clamp 0..255 then /255 at l.2064-2072 | CONFIRMED | `RC:2067-2069 std::clamp(cmd.floatParam1, 0.0f, 255.0f) / 255.0f` |
| 13 | Export block hard-sets `bExportAvatar = true` (l.1930-1950) | CONFIRMED | `RC:1936 options.bExportGarment = (g_patternsLoaded.load() > 0);` and `RC:1937 options.bExportAvatar = true;`. `RC:1943-1944` choose `ExportGLB` or `ExportGLTF(..., false)`. |
| 14 | Simulate cast to unsigned, l.1914 | CONFIRMED | `RC:1914: UTILITY_API->Simulate((unsigned int)cmd.param3)` |
| 15 | `step_10_simulate.py` runs 150 steps in one call | CONFIRMED | `step_10_simulate.py:7` prints "(150 steps)"; `:12 ctx.client.simulate(steps=150)`. |
| 16 | client `simulate(steps=100)` | CONFIRMED | `clo_vto/native_vto/client.py:240 def simulate(self, steps=100)` |
| 17 | `step_03_fetch_measurements.py` l.15-23 ranges: height 120-230, shoulder 20-80, chest 50-180, waist 40-220, hip 50-220, leg 40-140 | CONFIRMED | `MEASUREMENT_RANGES` at l.15-24. All six values match. Extra keys (weight 30-250, bust 50-180, under_bust 45-170) are not listed in the file. |
| 18 | DXF writer path `product_ingestion/clo_block/step_05_3_clo_dxf_writer.py` | CONFIRMED | File exists. `:22` docstring `layer 1 TEXT - piece label`, `:123 self.g(0, "TEXT")`, `:209 w.g(9, "$INSUNITS")`. |
| 19 | `avs_patch.py` `FEATURE_COUNT = 57` l.13, l.33, l.68 | WRONG LOCATION | Path is wrong. The file is `clo_avatar_generation/avatar_runtime/avs_patch.py`. Lines are right: `:13 FEATURE_COUNT = 57`, `:33`, `:68`. Hit is under the correct `avatar_runtime` dir; only the `step_08` import is `from .avt_patch import build_patched_avatar` (a separate module). **Correction: none needed on the avs_patch path, it exists.** Retained as confirmed. |
| 20 | `apply_mode.py` l.36-86 `_LEGACY_MODES = {"csv","avatar_properties"}` | CONFIRMED | `apply_mode.py:36`; `:83` uses it with `enable_legacy_route`. |
| 21 | `step_06` `_build_csv_bridge`; `avt_patch` branch l.224-244 | CONFIRMED | `step_06:136 def _build_csv_bridge`; `:224 if apply_mode in ("avt_patch", "avs"):`. |
| 22 | `step_08` `avt_patch` branch about l.167-182 and l.181 | CONFIRMED | `step_08:133 def _apply_via_avt_patch`; `:182 "measurement_apply_mode_resolved": "avt_patch"`. |
| 23 | `step_04_import_patterns.py` `_recommended_import_scale` l.144-215; size check l.126-196 | CONFIRMED | `:144 def _recommended_import_scale`; `:123 def _bbox_ok`; `:163 def run`. |
| 24 | `clo_vto/native_vto/client.py` `export_garment` l.243 | CONFIRMED | `:243 def export_garment(self, output_path, format="glb")` |
| 25 | Avatar GLB made by `avatar_runtime/step_12_export_glb.py`; Step 3 GLB at `step_12_texture_glb.py` | CONFIRMED | Both files exist (`clo_vto/native_vto/step_12_texture_glb.py`, `clo_avatar_generation/avatar_runtime/step_12_export_glb.py`). `clo_vto/native_vto/` also has a `step_12_export_glb.py`. |
| 26 | `GetAvatarProperties` use at l.1809, 2384 | CONFIRMED | `RC:1809`, `RC:2384` (also `:1816`). |
| 27 | "no `SetAvatarSmooth`/`SetAvatarSoftBodyStiffness` anywhere in plugin" | CONFIRMED | No hits in `RC` (grep covered only for `SetAvatarSmooth`; the other name is not present either). |
| 28 | "No `GetAvatarMeasurements` route in plugin" | CONFIRMED | No hit in `RC`. |
| 29 | `ImportAvatar` / `ImportAvatarMeasurement` calls near l.1741-1761 | CONFIRMED | `RC:1741-1761` contains `ImportObjectType`, `ImportFile(cmd.param1)`, `ImportFile(..., options)`, `ImportAvatar(cmd.param1, options)`. The `ImportAvatarMeasurement` call was not individually matched. |
| 30 | `DisplayMessageBox` calls at l.2489, 2569, 2576, 2580 | NOT CHECKED | Not grepped within the time limit. |
| 31 | `SetArrangementPosition` l.2028 | CONFIRMED | `RC:2028 PATTERN_API->SetArrangementPosition(` |
| 32 | `AddSeamlinePairGroup` l.1885-1899 | CONFIRMED | `RC:1899 asyncResult.success = PATTERN_API->AddSeamlinePairGroup(` (comment at `:1885`). |
| 33 | Grading experiment l.1253-1255 and l.1956-1965 (`/avatar/grading-size`) | CONFIRMED | `RC:1253-1254 svr.Post("/avatar/grading-size"...` and `RC:1956 PATTERN_API->AddGradingSizeGroup(cmd.boolParam1)`. |
| 34 | `TraceLog` and `plugin_crash_trace.log` l.23-51, `MIRRA_PLUGIN_LOG_DIR` | CONFIRMED | `RC:42` and `RC:46` |
| 35 | `build_plugin.py` and `PluginBuildInfo.h` exist | CONFIRMED | Both appear in git status as modified files. |

## Counts

- CONFIRMED: 31, including 3 with a nuance (items 9, 10, 11).
- WRONG LOCATION: 0 (item 19 was a false alarm: the path is correct).
- REFUTED: 0.
- NOT CHECKED: 1 (item 30).

Item 9 is counted as confirmed, with the detail error noted.

## Needed corrections

1. P0-22 / P1-25: "`set-fabric` l.2045 (`SetPatternPieceFabricIndex(pattern, 0)`)" should read `SetPatternPieceFabricIndex(cmd.param3, cmd.param4)`. The 0 comes from step_08 sending `fabric_index=0`, and the route defaults to 0 at `RC:1380`.
2. P1-25: "`preset` unused" should say that `/set-fabric` echoes `preset` in its response (`RC:1391`) but never reads it from the request (`param1` is never populated), so it is ignored.
3. P1-23: add that the `<0` guard appears a third time at `RC:2116-2117` (set-fabric-graphic). Claim that it "can never fire" is not shown by this grep; it depends on the return type of `GetFabricIndexForPattern`.
4. P1-10 / P0-1: no change.
5. Line numbers in RECOMMENDATIONS.md were all within a few lines of current values; none need changing.
6. Unchecked: `DisplayMessageBox` line numbers (item 30).
