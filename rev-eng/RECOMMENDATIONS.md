# CLO3D reverse-engineering: prioritised recommendations

*Status: lane AY rewrite, supersedes the earlier version. Static analysis only; nothing here has been run in CLO unless stated.*
*Date: 2026-10-30*
*Target: CLO Standalone OnlineAuth 2026.1.336 (build 58954), SDK 2026.1.336*

Precedence: lane M/M2/M3/M4 verification reports and these corrections win over earlier lanes.
(a) `.avs` import resizes only the CURRENT avatar (lane AL), not every loaded avatar; clearing other avatars is still needed.
(b) DXF unit source is `$INSUNITS` (lanes AA/M3), not the `UNITS:` text; `m_Scale` is ignored while `m_bAutoScale` is true (no double scaling).
(c) The GLB's 606,659 vertices is a counting artefact (lane T); real count 200,134.
(d) 29 APIs are effectively dead (30 thunks; `RemoveGraphicStyle(int)` delegates, lane Y/M).
(e) Grading size-switch off-by-one is `jb`, so only group > count fails (lane M4); still pass `group < count`.
(f) Simulate does not block on the SRW lock (lane X) but each call may restart the Folding/Draping phase.
(g) The SDK 336 plugin build succeeded and is installed (lane AX).

Code locations are in `C:\D-drive-data\mirra-mvp` and were re-grepped on 2026-10-30. The working tree has uncommitted edits, so line numbers are approximate; use the quoted symbol names. `RestPlugin_windows.cpp` = `clo_workspace/windows/RestPlugin_windows.cpp`. Findings paths are under `rev-eng/findings/`. Rules for this file: edits to repo code are NOT made here; this is a to-do list.

Priority key: P0 = correctness or crash risk on the current pipeline, do first. P1 = quality or robustness with clear evidence. P2 = optional or needs a live test before any investment.

Tools: `scripts/abi_check.py` (slot and version PASS/FAIL), `scripts/dxf_validate.py`, `scripts/avt_patch_tool.py`, `scripts/glb_slim.py`, `scripts/glb_probe.py`, `scripts/zprj_probe.py`, `scripts/avs_grammar.py`, `experiments/e01..e08`, `PLUGIN_COMMAND_SPEC.md`.

---

## 1. Version and ABI safety

### P0-1 Gate every run on host/SDK version match
- Evidence: findings/14 (lane G; 224 build FAIL, 19 items), 11 (lane D crash mechanism, inference), 47 (lane AX; 336 PASS). `ImportExportOption` sizeof 200 -> 296 (lane M, computed by hand). Crash trace has 9 `BEGIN` without `END` next to "host CLO version differs" warnings (lane J, findings/17).
- Code: `RestPlugin_windows.cpp` `/health` handler (`host_matches_sdk`, `GetHostAppVersion() == MIRRA_PLUGIN_SDK_CLO_VERSION`, about l.660-712); `clo_workspace/shared/PluginBuildInfo.h`; `clo_workspace/build_plugin.py`. Python side: no caller checks `host_matches_sdk` (grep in `clo_avatar_generation`, `clo_vto` returned nothing).
- Action: in `clo_avatar_generation/avatar_runtime/client.py` and `clo_vto/native_vto/step_01_health.py`, abort the run if `/health` reports `host_matches_sdk` false; plugin should return 409 on mutating routes (spec group `GET /preflight`).
- Risk: low. A false negative only blocks a run.
- Verify: `python -I scripts/abi_check.py` exit 0 after every CLO auto-update; compare `/health` with the exe version. Experiments' `_common.py` preflight already does this check.
- Tools: `abi_check.py`, `PLUGIN_COMMAND_SPEC.md` (preflight), `out/compile_check/`.

### P1-2 Re-run abi_check after each CLO update, rebuild plugin on mismatch
- Evidence: findings/47 (lane AX: 336 build installed, `RestPlugin_v1.3.2.dll`), findings/14. `liveupdate.txt` shows the in-app updater moved the app 224 -> 336 (lane Y).
- Code: `clo_workspace/build_plugin.py`; installed DLL under `C:\Program Files\CLO Standalone OnlineAuth\plugins\`. The plugin comments near l.27 and l.1925-1935 already record past vtable skew.
- Action: add `abi_check.py` to the plugin build/deploy step; disable CLO auto-update during pilots if possible.
- Risk: low. Verify: PASS with 0 fails and 0 unverified. Caveat: it checks slot sets, not order within overload groups (lane G, I).

### P2-3 Do not call by-value `ImportExportOption` overloads from a stale build
- Evidence: lanes B, D, AX (the plugin builds a local option and passes `const&`; no by-value warning).
- Code: `ImportAvatar` / `ImportAvatarMeasurement` calls near l.1741-1761.
- Action: none now; only a reminder to re-run abi_check if the struct changes again.

---

## 2. Avatar pipeline (Step 1)

### P0-4 Clear all avatars before importing the avatar and `.avs`
- Evidence: findings/40 (lane AL: `.avs` resizes the CURRENT avatar `mgr+0x98`, otherwise a search; >=2 candidates -> modal chooser; category mismatch -> "No matching Avatar."), 24 (lane R: `DeleteAvatar` semantics, current pointer re-points to the first remaining), 36 (lane AG). Pipeline comment in `step_07` records five runs leaving 3,4,1,1,2 avatars.
- Code: `clo_avatar_generation/avatar_runtime/step_07_import_base_avatar.py` (`new_project()` then `import_avatar_avt`, about l.57-80); `client.py` `clear_avatars(max_index=7)` (l.51) is defined but grep shows **no caller** anywhere. Plugin: `DeleteAvatar` at `RestPlugin_windows.cpp` about l.2009; NewProject comment l.1301 says avatars survive it.
- Action: order `clear-avatars` (delete 0..n-1 with n from `GetAvatarCount`) -> `new-project` -> import single avatar -> verify `GetAvatarCount == 1` -> `ImportFile(.avs)`. Treat a count != 1 as a hard failure. Reset the plugin avatar tally on false.
- Risk: medium (the older plugin lacks the route; a false from `DeleteAvatar` means no valid index existed).
- Verify: e01 scenarios S1-S3 (only the current avatar changes); `/avatars/state` count after clearing.
- Tools: `experiments/e01_avs_single_avatar.py`, spec group `POST /avatar/import-sequence`.

### P0-5 Softbody / Divide pre-flight before `ImportFile(.avs)`
- Evidence: findings/33 (lane AB: boxes "Softbody Option will be turned off" and "Divide Option", reached from `ImportFile(.avs)` via `0x50a8710`), 29 (lane X), 40. Stock repo `.avt` files have both flags 0, so risk is for user-modified or CLO-resaved avatars.
- Code: `RestPlugin_windows.cpp` `GetAvatarProperties` use (l.1809, 2384); no `SetAvatarSmooth` / `SetAvatarSoftBodyStiffness` anywhere in the plugin.
- Action: new plugin command that, per loaded avatar, reads `GetAvatarProperties` and if Divide or Softbody is true calls `SetAvatarSmooth(idx,0)` then `SetAvatarSoftBodyStiffness(idx,0.0)`. Never call them with non-zero values. Keep exactly one avatar loaded.
- Risk: low-medium (new calls, GUI thread only).
- Verify: e01 plus e07 (watchdog) with an avatar that has softbody on; flags read back.
- Tools: `PLUGIN_COMMAND_SPEC.md` (`/avatar/properties`), e01, e07.

### P0-6 Modal-dialog watchdog with an allow-list
- Evidence: findings/29 (lane X), 33, 36, 40: "No matching Avatar.", avatar chooser, softbody/divide prompts, graded-size avatar prompt on `.avt`, "Failed to load the Avatar Size file", "created in a lower version", disk-space `<10GB`, `DisplayMessageBox` (modal, no timeout). Crash trace shows commands that never END (lane J).
- Code: queue timeouts in `clo_avatar_generation/avatar_runtime/client.py` (`wait_for_queue`) and `step_07` (`wait_for_queue(timeout=30)`); plugin `DisplayMessageBox` calls at l.2489, 2569, 2576, 2580 (menu paths, not pipeline).
- Action: external watchdog (window-title/text allow-list) that logs and, where safe, dismisses; per-step timeout that turns "queue stuck" into a clear "modal dialog?" failure. Do not auto-dismiss unknown boxes.
- Risk: medium (dismissing the wrong button is unverified; button ids unmapped).
- Verify: e07 in a second terminal during every live experiment (dry-run first).
- Tools: `experiments/e07_modal_watchdog.py`, spec watchdog section.

### P0-7 Verify measurements after `.avs` (do not trust import return)
- Evidence: findings/36 (slot-2 return not a success signal; GUI mode may return false), 40 (silent no-op when measure-mode validity fails, `_resaved` appended), 09/16 (`GetAvatarMeasurements`).
- Code: `step_08_apply_measurements.py` (`avt_patch` branch about l.167-182 reads queue result of `import-avatar-avt`); `avs_patch.py` (`FEATURE_COUNT = 57`, l.13). No `GetAvatarMeasurements` route exists in the plugin.
- Action: add `GetAvatarMeasurements` read-back (spec `/avatar/measurements`); compare height and bust to requested within tolerance; check avatar name for `_resaved`. Keep exactly one `listMeasureMode` ==3 and one ==1 in the `.avs`.
- Risk: low.
- Verify: e01 `--need-measurements`; `avs_grammar.py tree` on the generated `.avs`.
- Tools: `avs_grammar.py`, e01.

### P1-8 Fix `FEATURE_COUNT` (57 vs 62/67) and keep the byte layout intact
- Evidence: findings/13, 15, 27 (`.avs` holds 62 floats, `.dan` 67; 57 was a prefix), 28.
- Code: `clo_avatar_generation/avatar_runtime/avs_patch.py` l.13, l.33, l.68.
- Action: confirm only indices 0,2,6,8,26,36 are authoritative; treat other 51 as ridge-model predictions. Prefer locating floats by name via `avs_grammar.py` rather than a fixed offset (offset 1718 is only valid for the male default).
- Risk: low. Verify: round-trip with `avs_grammar.py roundtrip`.

### P1-9 Tighten sanity ranges using CLO's training data
- Evidence: findings/34 (lane AE): male p1/p99 ranges; CLO only clamps 0.1-300 cm and silently extrapolates; ridge model valid only for chest 86-132, waist 72-123 (findings/27).
- Code: `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py` l.15-23 (`height 120-230`, `shoulder 20-80`, `chest 50-180`, `waist 40-220`, `hip 50-220`, `leg 40-140`). Compare male training ranges: waist 65.5-145.7, shoulder 33-54, inseam 64-100, height 142.8-211.3.
- Action: add hard/warn tiers (hard: training min/max; warn: p1/p99), plus relational rules (hard reject `waist > bust + 6`, warn `waist > bust - 0.5`, inseam/height 0.375-0.487, shoulder/height 0.208-0.299, Mahalanobis p99 5.1). Apply the leg/shoulder tiers only after confirming Mirra's `leg_length_cm` = Inseam Height and `shoulder_width_cm` = Across Shoulder (Curvilinear) (open item in findings/34).
- Risk: low; false rejections of real users if tiers are too tight, so warn first, reject later.
- Verify: unit-test with edge values; compare with `raw/ae_out.txt`.
- Caveat: the "<5% error" accuracy claim has no validation (memory note); do not cite.

### P1-10 Weight, female and wiring gaps
- Evidence: findings/27, 34: `weight_kg` has no CLO key; slot idx 1 is body weight (sqrt kg) but not settable via the CSV importer; female bust/under-bust (idx 5) unwired; `step_03` rejects non-male.
- Code: `step_03_fetch_measurements.py`, `step_06_build_payloads.py`.
- Action: drop weight as a driver; when female is needed use Under Bust idx 5 as the second driver. Set only if live tests confirm `.avs` accepts it.
- Risk: medium; needs the female template and e01.

### P1-11 The csv route is broken: keep it legacy
- Evidence: findings/15, 20 (parser: line 1 discarded, line 2 `Xxx(cm)`, rows `Name,Type,Value`; bad value throws), 27; needs `-headless` for the 1-arg `ImportMeasurement` (findings/11, 18).
- Code: `step_06 _build_csv_bridge`; `apply_mode.py` l.36-86 (`_LEGACY_MODES = {"csv","avatar_properties"}`, `--enable-legacy-route`).
- Action: leave guarded; do not extend. If revived, write the real layout and test headless.
- Risk: none if left alone.

### P1-12 `.avt` patching: use `avt_patch_tool.py` and do not expect re-deform
- Evidence: findings/13, 19, 20, 46 (lanes F/K/M/AV): patching `listFeatureValues` in `.avt` never re-deforms the mesh; the digest covers only the header (findings/31); pipeline-patched files have stale field 0x24 (-600 to -610 bytes).
- Code: `step_06_build_payloads.py` (`avt_patch` branch l.224-244); `step_08` `avt_patch` branch l.181.
- Action: either use `.avs` (mesh deforms) or accept identical meshes per user (`avt_patch` GLBs are identical across users, memory note). If `.avt` writing continues, use `avt_patch_tool.py` semantics (correct 0x24, recomputed SHA-256 with salt `scrampling&$%!@#mvfileheader`).
- Risk: low. Verify: e02 (compare vertex positions after CLO re-save); `z_verify_digest.py`.
- Tools: `avt_patch_tool.py`, e02.

### P2-13 Anchor interpolation as an offline alternative (needs ~15-30 CLO runs)
- Evidence: findings/28 (lane W): re-implementing CLO's solver not feasible; linear-in-height model rms 1.0 mm.
- Action: only if CLO latency or licensing blocks live avs. Park until e01 results are in.

### P2-14 `-headless` option
- Evidence: findings/18: only `headless <file>` changes plugin-visible behaviour; modal boxes have no headless guard. Not recommended as it removes nothing needed.

---

## 3. Garment ingestion (Step 2 -> Step 3)

### P0-15 Add AAMA annotation TEXT entities to the DXF writer
- Evidence: findings/32 (lane AA: key table `PIECE NAME`, `SIZE`, `SAMPLE SIZE`, `UNITS`, `QUANTITY`...; non-AAMA file converted to baselines with a message), 44 (lane AT: 20 newest pipeline DXFs WARN, no FAIL, gaps are annotations only; older output FAIL 20 because of named layers).
- Code: `product_ingestion/clo_block/step_05_3_clo_dxf_writer.py` (layer-1 TEXT label near l.22 and the TEXT emitter near l.123-130; header writes `$INSUNITS` near l.209). Note: a missing annotation is not proven to be rejected (findings/32, 44).
- Action: (1) inside each BLOCK replace the free label with layer-1 `PIECE NAME:`, `SIZE:`, `QUANTITY: 1`; (2) after the INSERT add layer-1 `STYLE NAME:`, `SAMPLE SIZE:`, `UNITS: METRIC`; (3) keep `$INSUNITS 4` or mirror the CLO reference by dropping it; (4) optional: `$DWGCODEPAGE ANSI_1252`, layer-14 copy, layers 85/87 allowance polylines.
- Risk: low-medium (changes the file CLO reads; could alter piece names). Verify: `python -I scripts/dxf_validate.py <dir>` (WARN -> PASS) then import and compare pattern count.
- Tools: `dxf_validate.py`, `experiments/e05_importdxf_units.py` (the annotation entity layout is its TODO), `product_ingestion/clo_block/reference_dxf/`.

### P0-16 Verify import by pattern count, never by return value
- Evidence: findings/22, 26 (`ImportDXF` returns true even for empty or invalid files; inner function returns false only when global `0x14A2ABF10` is null).
- Code: `RestPlugin_windows.cpp` `import-pattern` l.1856-1871 (`asyncResult.success = IMPORT_API->ImportDXF(...)`); `clo_vto/native_vto/step_05_verify_patterns.py` already verifies the count, keep it a hard fail.
- Action: make the plugin result include `GetPatternCount` before and after; fail if the delta != expected pieces.
- Risk: low. Verify: e05 variants (empty file, bad units).

### P1-17 Autoscale and units: stop sending a meaningless `scale`
- Evidence: findings/22 (lane P; `m_Scale` used only when `m_bAutoScale` false), corrected units source in 32/35 (lanes AA/M3: `$INSUNITS` 1 -> x25.4, 5 -> x10, 6 -> x1000, 4 and others -> x1.0, applied only when the valid flag at ctx+0x2AC098 equals 1).
- Code: `RestPlugin_windows.cpp` l.1858 (`options.m_Scale = floatParam1 > 0 ? floatParam1 : 1.0f`; `m_bAutoScale` untouched); `clo_vto/native_vto/step_04_import_patterns.py` `_recommended_import_scale` (l.144-215; comment says mm DXF -> scale 0.1).
- Action: either drop `scale` from the call or set `m_bAutoScale=false` together with `m_Scale`. Default to autoscale true and a DXF with `$INSUNITS 4`. Check piece size sanity (existing size check in step_04 l.126-196 is good) and bounding boxes with `GetBoundingBoxOfPattern`.
- Risk: medium; a changed unit path could scale garments wrongly. Verify: e05 (units x scale matrix; read bbox for the 520 x 710 mm front panel).
- Tools: e05, `dxf_validate.py` (scale rule check).

### P1-18 Notches: set `m_bIncludeNotchs = true`
- Evidence: findings/22, 32 (layer 4 and 80-83 are notches; `m_bIncludeNotchs` at +0x0F; placement +0x18 clamped <= 2).
- Code: `RestPlugin_windows.cpp` l.1857-1860 (only `m_Scale`, `m_bAppend` set).
- Action: set true once the writer emits layer-4 notch points; keep `m_bConvertToSeamAllowance` untouched (never read).
- Risk: low-medium (notches may add stitching hints or clutter). Verify: e05 variant with notch; compare piece geometry.

### P1-19 Pre-validate DXFs; drop old output
- Evidence: findings/44: the older pipeline output (named layers `CutLine`/`GrainLine`) FAIL 20 and would import empty; reader parses layer names as integers.
- Code: `product_ingestion/clo_block/validate_against_reference.py`; `generate_block.py`. 
- Action: run `dxf_validate.py` as a gate before `import-pattern`; delete or ignore the old `c_00N-s_00N-00M` directories.
- Risk: low.

### P2-20 Seams: switch to `AddSeamlinePairGroupPartial`
- Evidence: findings/07, 16, 35 (lane I/M3): typed negative error codes (-1..-7); validator order.
- Code: `RestPlugin_windows.cpp` l.1885-1899 (`AddSeamlinePairGroup`), `clo_vto/native_vto/seams.py` (`DEFAULT_SEAMS`), `step_09_create_seams.py`.
- Action: only if seam failures need diagnosis; do not change if seams work (all 8 garment runs used the default T-shirt panels, findings/23).
- Risk: medium (new API in 336, never used). Verify: live seam creation, compare `listSeamLinePairGroup`.

### P2-21 Arrangement units
- Evidence: findings/12: X/Y/Z are 0-100 normalised, orientation 0-360; values >100 silently ignored; the plugin truncates floats to int.
- Code: `RestPlugin_windows.cpp` `SetArrangementPosition` l.2028; `step_07_arrange_patterns.py`.
- Action: check that arrangement values stay in range; log ignored calls.

---

## 4. Fabrics

### P0-22 Per-panel textures currently overwrite each other
- Evidence: findings/23 (lane Q: one shared fabric; all 7 textured runs hold `sleeve_right_texture.png`), 41 (lane AQ: one fabric per panel via `ExportFabric` + `AddFabric` x3, then `AssignFabricToPattern`).
- Code: `clo_vto/native_vto/step_08_apply_fabric.py` (`set_fabric(idx, fabric_index=0)` for all pieces, l.106-112; colour l.127-137); `RestPlugin_windows.cpp` `set-fabric` l.2045 (`SetPatternPieceFabricIndex(cmd.param3, cmd.param4)`; the 0 comes from `step_08` sending `fabric_index=0`, and the route also defaults it to 0 at l.1380), `set-fabric-color` l.2064-2072, `set-fabric-texture` l.2093-2095, FabricDispatcher l.298/319/400/416. `step_12_texture_glb.py` injects textures into the GLB offline (single merged material prefix `fabric 1`, l.57-70).
- Action: new plugin commands `AddFabric`, `ExportFabric`, `GetFabricCount`, `GetPatternPieceFabricIndex`, `AssignFabricToPattern`; sequence per findings/41: `n0 = GetFabricCount` -> `ExportFabric(tmp.zfab,0)` -> `AddFabric` x3 checking count == n0+k (never the return value) -> `AssignFabricToPattern(i, piece, 1)` -> read back `GetPatternPieceFabricIndex` -> existing colour/texture commands. Expect 4 materials in the GLB.
- Risk: medium-high (untested copy path; `AddFabric` failure looks like success).
- Verify: save project and read `listFabric` count 4 and each `iFabricIndex` 0-3 with `zprj_probe.py`; GLB `glb_probe.py` shows 4 materials.
- Tools: spec group `/fabric/physical`, `zprj_probe.py`, no existing experiment (propose e09b, see section 8).

### P1-23 Colour semantics: floats 0..1, Front and Back, check bool, read back
- Evidence: findings/21 (lane N: no gamma; 0..255 would be stored unscaled; unknown name -> false; Back may alias Front; face has no bounds check), 26 (M2: no pow in float overloads), 07.
- Code: plugin `set-fabric-color` l.2064-2072 (clamps to 0..255 then divides by 255 - correct); FabricDispatcher l.298-308 and l.400 (bool return ignored; only Front set); `if (fabric_idx < 0)` guard l.2066, l.2094 and l.2116-2117 (`set-fabric-graphic`) is expected never to fire for the 1-arg `GetFabricIndexForPattern`, which returns 0 on failure (findings/21; grep alone does not prove it, it depends on the return type).
- Action: check the bool; set Front and Back (compare Back aliasing Front first); read back with `GetFabricPBRMaterialBaseColor` (returns (1,0,0,0) for invalid); drop the `<0` guard or limit to the 2-arg overload; reset base colour to white before texturing if true texture colours are needed [I].
- Risk: low. Verify: e06 (GLB `baseColorFactor` proxy; Front/Back untestable until the plugin exposes the face).
- Tools: `experiments/e06_fabric_colour_readback.py`.

### P1-24 Texture call hygiene
- Evidence: findings/21: 212-214 set Front only and return void; a bad fabric index in 213 textures the currently selected fabric; missing file is a silent no-op; `set-fabric-graphic` overwrites the base texture.
- Code: `RestPlugin_windows.cpp` l.319, 416, `set-fabric-graphic` handler about l.2116.
- Action: pre-check the file exists and the fabric index < `GetFabricCount`; use overload 211 (face + error string) via new wrapper; use `AddGraphicStyleFromImageFile` + `AddGraphicStyleToPatternV2` for decals (findings/41 C1, GLB baking unknown).
- Risk: medium. Verify: e06 variants.

### P1-25 Physical presets: the pipeline always drapes with CLO's "Default" fabric
- Evidence: findings/38 (lane AJ: no API for physical properties; `ChangeFabricWithJson(index, path)` overwrites the whole fabric; `/set-fabric` ignores `preset`); Default values: bending 100/600/150, shear 5000, density 0.0003, friction 0.03, thickness 0.5.
- Code: `RestPlugin_windows.cpp` l.1391 (the route echoes `preset` in its response, but `param1` is never filled from the request and never used) and l.2045; `step_08_apply_fabric.py` l.106-112.
- Action: author small `.jfab` presets from CLO-exported fabrics (not the spec example); plugin command `ChangeFabricWithJson(0, path)` (check bool) or `AddFabric` + count check; apply colour and texture after; verify by saving the project and reading `listFabric/0/mapPhysical`. Also consider `SetAddlThicknessCollision` and `SetSimulationAirDamping` (raw store, no clamp).
- Risk: medium (spec-only jfab may lack `_v2`/`LeftShear`). Verify: new experiment e09 (physics read-back, proposed in PLUGIN_COMMAND_SPEC.md, not written).
- Tools: `zprj_probe.py`.

---

## 5. Simulation and export

### P0-26 Do not trust `Simulate` return; verify state
- Evidence: findings/24, 26, 29 (always returns true; no cancel; plugin casts `(unsigned)param3`), lane X (negative-thread-length box when a Button object fails the check; GPU box; null scene assert).
- Code: `RestPlugin_windows.cpp` l.1914 (`UTILITY_API->Simulate((unsigned int)cmd.param3)`); `clo_vto/native_vto/step_10_simulate.py` (150 steps in one call); client `simulate(steps=100)`.
- Action: clamp `steps >= 0`; keep CPU simulation; avoid garments with buttons until the box is characterised; after simulate, save the project/export and check sanity (non-NaN, draped height) instead of reading the bool.
- Risk: medium. Verify: e03.

### P1-27 Chunking caveat: each Simulate call may restart Folding/Draping
- Evidence: findings/29 (lane X: Folding frames 0-9, Draping to 50 total frames (40 without folding), then solver; each Simulate may re-arm), 35 (lane M3: not verified); lane R advised chunking, which now conflicts.
- Code: `step_10_simulate.py` (single 150-step call is the safe default); any future chunk loop.
- Action: do not chunk into small calls until e03 shows the restart does not occur; if chunking is needed use chunks >= 50 frames.
- Risk: medium. Verify: e03 (single call vs 3 x 50 vs 15 x 10; compare vertex hashes or GLB bin sha256).
- Tools: `experiments/e03_simulate_chunking.py`.

### P1-28 Per-garment GLB and avatar-once flow
- Evidence: findings/39 (lane AK): `ExportGLTF(path, opts, bGLBinary)`; `bExportAvatar=false` + `bExportGarment=true` + `scale=0.001` + `bThin=true`; empty selection -> empty vector, no error; materials BLEND with `KHR_texture_transform` required; `ExportGLB == ExportGLTF(...,true)`.
- Code: `RestPlugin_windows.cpp` export block l.1930-1950 (`options.bExportGarment = patterns loaded`, `bExportAvatar = true` always; `ExportGLB` for glb); `clo_vto/native_vto/client.py` `export_garment` l.243; `step_11_export_note.py`, `step_12_texture_glb.py`.
- Action: add route params `bExportAvatar`, `bExportGarment`, component lists; export the avatar once, then garment-only; check non-empty vector and file size > 0; viewer must support `KHR_texture_transform` and force opaque.
- Risk: medium (stale list indices return nothing).
- Verify: e08; `glb_probe.py` (no skins, 1-2k vertices per piece, embedded images); compare garment bounds with avatar bounds.
- Tools: e08, spec group `/export`.

### P1-29 Remove hair and slim the avatar GLB
- Evidence: findings/25, 42, 45 (lanes T, AP, AU): hair is 71% of vertices (141,426 of 200,134) and about 10.5 MB of a 30.5 MB packed GLB; no API hides parts; `.dan` `bVisible` patch is untested; `glb_slim.py` all five lossless ops: -48.6% (A) / -42.6% (B).
- Code: avatar GLB created by `step_12_export_glb.py` (Step 1) in `clo_avatar_generation/avatar_runtime/`; Step 3 GLB at `step_12_texture_glb.py`.
- Action: now: `python -I scripts/glb_slim.py --drop-mesh Hair,shoes_r,shoes_l --weld --u16-indices --weights-u8 --joints-u8 in.glb -o out.glb --report`; then test the `.avt` `bVisible` patch via `avt_patch_tool.py patch --hide Hair`; recompress the four roughness PNGs offline (9.4 MB) with an external tool.
- Risk: low for offline slimming; medium for the `bVisible` patch (import may restore visibility). Note input B (real CLO export) fails the script's own 4-byte alignment check on image views, but the outputs are aligned; no external glTF validator or viewer test was done.
- Verify: `glb_probe.py summary` (expect hair gone, 58.7k vertices left); load in the web viewer.
- Tools: `glb_slim.py`, `avt_patch_tool.py`, e08 (visibility variant).

### P1-30 Save-project / diffs
- Evidence: findings/23: `.pac` saves contain uninitialised memory and random uuids, so byte diffs are never clean; the embedded avatar is not byte-identical to the pipeline's.
- Action: compare parsed values via `zprj_probe.py`, not bytes.

---

## 6. Grading

### P1-31 Treat the 29 dead APIs as removed
- Evidence: findings/12, 20, 30, 37 (lanes E, M, Y, AF): `AddGradingSizeGroup` (slot 202) returns -1, `SetGradingPairedAvatarSizing`/`FromFile` return false; Pattern 196-220 and Utility 388, 397-400 are thunks; `RemoveGraphicStyle(int)` delegates so 29 are effectively dead. findings/09 recommendations stay dead.
- Code: `RestPlugin_windows.cpp` grading experiment l.1253-1255 and l.1956-1965 (`/avatar/grading-size`).
- Action: remove or hide the route (never call it; e04 exits 3); do not use `AddGradingSize`, `ImportGradeRuleToSizeGroup`, `SetGradingPairedAvatar`, offset setters. Also avoid `SetAssetShareRoot`, `GetBasePath`.
- Risk: none. Verify: grep for callers; abi_check lists thunks as non-fatal.

### P2-32 Template-switch grading flow (needs plugin commands and a template)
- Evidence: findings/37 (lane AF; 16 implemented slots: 136-148, 179-181), 43 (M4: only group > count fails; still pass `group < count`).
- Code: none yet (no routes for `GetGradingSizeGroupCount`, `ChangeGradingSizeInformation`, `GetCurrentGradingSizeIndex`, `GetGradingPairedAvatar`).
- Action: template `.zprj` authored in the GUI with no Pair-3D-Form entries -> require `GetGradingSizeGroupCount() >= 1` -> map size label with `GetGradingSizeListFromRuleTable(0)` -> `ChangeGradingSizeInformation(0, idx)` (check true and `GetCurrentGradingSizeIndex() == idx`) -> check paired avatar is empty -> import Mirra avatar -> `Simulate()`. Fallback: one garment per size DXF.
- Risk: medium (avatar swap, undo-prompt reachability unknown).
- Verify: e04 once the commands exist (currently blocked, exit 3).
- Tools: e04, spec group `/grading/*`.

---

## 7. Logging and crash correlation

### P1-33 Make crashes attributable
- Evidence: findings/17 (lane J): `plugin_crash_trace.log` has 9 `BEGIN` without `END` (6 `import-avatar-avt`, 3 `clear-avatars`), new `tid` and fresh `g_cloMainWnd discovered` after; trace uses local time without dates; CLO analytics log holds only 3 events; `api_plugin_log.txt` at `C:\Users\Public\Documents\CLO\CLO Assets\`. findings/47: the 37 MB trace was not examined.
- Code: `RestPlugin_windows.cpp` `TraceLog` and `plugin_crash_trace.log` (l.23-51, `MIRRA_PLUGIN_LOG_DIR`); `/health` fields.
- Action: add date + request id to every `BEGIN`/`END`; log `host_matches_sdk` at load; Python clients should send the same request id and write it to the run JSON. Add a log-scanner that reports BEGIN lines without END and version-mismatch warnings per run.
- Risk: low. Verify: induce a failure with e07 off and a known-bad command, then correlate.
- Tools: spec "request ids", `scripts/log_catalog.py` (offline message catalog).

### P2-34 Check the 37 MB trace for pre-336 crash clusters
- Evidence: findings/47 (not examined). Action: scan for BEGIN-without-END after 2026-10-29 15:06 (deploy time of the 336 plugin) to see whether crashes persist.

---

## 8. Live-test plan

Prerequisites for all: one supervised CLO 336 instance, plugin REST at 127.0.0.1:50505, `/health` ok with `host_matches_sdk` true, queue idle, backups of the CLO project/settings, `e07` running in a second terminal. All scripts are dry-run by default; pass `--live` to act. Results go to `experiments/out/`; fill `experiments/RESULTS_TEMPLATE.md`. Never call `POST /avatar/grading-size`.

| # | Experiment | Question | Expected if hypothesis H holds | Expected if H fails |
|---|---|---|---|---|
| 1 | e07 `--list-once`, then leave running | Does the watchdog see CLO windows? | Window list includes CLO main window | Fix the title filter before continuing |
| 2 | e02 `--avt <stock.avt>` (offline prepare, then `--live`) | Does any `.avt` byte change re-deform the mesh? (H: no, findings/19) | Mesh position bytes identical after CLO re-save for patched floats | Positions differ: `.avt` route is viable; revisit P1-12 |
| 3 | e01 S1 (one avatar then `.avs`) | Does `.avs` resize the single current avatar and change measurements? | Height/bust read-back near target; mesh bounds change; name has no `_resaved` | No change: check `listMeasureMode` and qsAvatarID category (lane AL) |
| 4 | e01 S2 (two avatars, same category, `.avs`) | Is only the CURRENT avatar resized (lane AL) rather than every avatar? | Exactly one avatar changed (the current); no chooser | Both changed: lane AL wrong; or chooser appears (>=2 matching with no current) |
| 5 | e01 S3 (`--skip-load`: no avatar) | Does `.avs` with no avatar show "No matching Avatar."? | Modal box; watchdog logs it; queue timeout | No box: re-check the first test in `0x50fcfe0` |
| 6 | e01 with softbody on (set in GUI) | Does the softbody prompt appear and does pre-flight (P0-5) prevent it? | Prompt appears without pre-flight; none with it | No prompt: lane AB reachability wrong; pre-flight stays harmless |
| 7 | e05 (units x scale matrix) | Does `$INSUNITS` set scale and is `m_Scale` ignored with autoscale? | Piece bbox scales 25.4/10/1000/1 by `$INSUNITS`; `m_Scale` has no effect when autoscale is true; `UNITS:` text changes nothing | Bbox follows `UNITS:` or `m_Scale`: lanes AA/M3 need re-checking |
| 8 | e05 (annotation variants) | Does a DXF without `PIECE NAME:`/`UNITS:`/`SAMPLE SIZE:` import? Are notches imported with `m_bIncludeNotchs` true? | Imports with warning or baseline conversion; notches present only when the flag is true | Empty import: annotations are mandatory (promote P0-15) |
| 9 | e06 (colour read-back) | Float overload, Front vs Back, sRGB vs linear | GLB `baseColorFactor` equals r,g,b as given (no gamma); Back may alias Front | Gamma applied: adjust colour pipeline |
| 10 | e08 (export scope) | Does `bExportAvatar=false` + `bExportGarment=true` yield garment-only GLB; does an empty list give an empty vector? | Garment-only file with no skins; stale list returns empty | Avatar still present: lane AK/M4 gating wrong |
| 11 | e08 + `avt_patch_tool.py patch --hide Hair` | Does `bVisible=0` remove hair from the GLB with `bIncludeHiddenObject=false`? | Hair mesh absent; 58.7k vertices | Hair present: remove offline with `glb_slim.py --drop-mesh` |
| 12 | e03 (Simulate chunking) | Does a second Simulate call restart Folding/Draping? | Single 150-step call result differs from 15 x 10-step; 3 x 50 matches | Same output: chunking is safe; lane X caveat resolved |
| 13 | e03 (empty scene, then scene with button garment) | Is the negative-thread-length box reachable? | Box appears only with a button failing the check | Never: lane X reachability low risk |
| 14 | New (not written): AddFabric x3 / AssignFabricToPattern (spec group `/fabric/physical`) | Are three independent fabrics created and mapped? | Count n0+3; `iFabricIndex` 0-3 in saved zprj; 4 GLB materials | Count unchanged or shared: use graphic decals (C1) |
| 15 | New (e09 proposed): ChangeFabricWithJson then save zprj | Does a spec-only `.jfab` apply physical values? | `listFabric/0/mapPhysical` equals the jfab; `_v2` regenerated | Defaults kept or `_v2` missing: build presets from CLO exports |
| 16 | e04 after plugin commands exist | Does the template-switch flow work; is `Simulate` required; is the avatar swapped? | Group count >= 1; index set; no avatar swap with empty pairings | Swap occurs: remove pairings in the template; else fall back to per-size DXF |
| 17 | After any run: `abi_check.py`, `dxf_validate.py`, `glb_probe.py` | Static gates | PASS | Stop |

Order: 1 -> 2 -> 3-6 -> 7-8 -> 9-11 -> 12-13 -> 14-15 -> 16 -> 17. Stop on any crash and check `/health` and `plugin_crash_trace.log` before continuing.

---

## Top 10 actions (copy of SUMMARY.md)
1. P0-4 Call `clear-avatars` (never called today) before every avatar import.
2. P0-1 Gate on `host_matches_sdk`; run `abi_check.py` after each CLO update.
3. P0-15 Add `PIECE NAME:`/`SIZE:`/`QUANTITY:` and `STYLE NAME:`/`SAMPLE SIZE:`/`UNITS: METRIC` to the DXF writer.
4. P0-22 One fabric per panel (AddFabric x3 + AssignFabricToPattern).
5. P0-5/P0-6 Softbody/Divide pre-flight and the modal watchdog allow-list.
6. P0-7 Read back measurements after `.avs`.
7. P1-17/18 Fix autoscale/`m_Scale` and enable notches.
8. P1-29 Slim the avatar GLB offline (drop hair/shoes, weld, u16, u8 weights).
9. P1-9 Replace the wide `step_03` ranges with training-data tiers.
10. P1-25/31 Physical fabric presets via `ChangeFabricWithJson`; remove dead grading routes.
