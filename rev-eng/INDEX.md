# rev-eng index

*Status: lane AY rewrite; listing taken from the directories on 2026-10-30.*
*Target: CLO Standalone OnlineAuth 2026.1.336 (build 58954), SDK 2026.1.336 (224 for comparison).*

Reading order: `SUMMARY.md` (one page) -> `RECOMMENDATIONS.md` (prioritised actions) -> `FINDINGS.md` (lane-by-lane record; later lanes and the M/M2/M3/M4 verification reports win over earlier ones) -> the detail file named in the lane heading.

## Top level

| File | Purpose |
|---|---|
| SUMMARY.md | One-page executive summary: confidence levels, live tests needed, top 10 actions |
| RECOMMENDATIONS.md | P0/P1/P2 action list with evidence, code location, risk, verification, tooling, live-test plan |
| FINDINGS.md | Full record of Rounds 1-3, lanes A-AX, with corrections |
| PLAN.md | Original scope and steps (status done) |
| PLUGIN_COMMAND_SPEC.md | Design for new plugin commands (request ids, grading, measurements, fabric, export, DXF, preflight, avs sequence); design only, nothing applied |
| INDEX.md | This file |

## findings/ (detail files, numbered)

| File | Purpose |
|---|---|
| 01_call_sites.md | Every CLO API call site in `RestPlugin_windows.cpp` |
| 02_header_signatures.md | SDK header signatures of called functions |
| 03b_export_diff.md | DLL export diff, SDK 224 vs 336 (+76/-1) |
| 04_target_vtable_slots.md | Vtable slot for each plugin-called function |
| 05_dll_to_app_bridge.md | How the SDK DLL stubs relate to the exe implementations |
| 06_exe_real_vtables.md | Real `Marvelous::*API` classes and vtable RVAs (lane A; Fabric texture slots corrected by 14) |
| 07_function_reference.md | Semantic reference of API functions, plugin issues from docs |
| 08_struct_reference.md | `ImportExportOption`, `ImportDxfOption` and related structs |
| 09_unused_useful_apis.md | Unused APIs worth adopting (several grading entries are dead; see 30, 37) |
| 10_file_formats.md | `.avt` / `.zprj` / GLB container formats (lane C; 606,659 count corrected by 25) |
| 11_impl_util_import_export.md | Disassembly notes: Utility, Import, Export wrappers; ImportAvatar crash mechanism |
| 12_impl_pattern_fabric.md | Disassembly notes: Pattern and Fabric wrappers, indices, arrangement units, grading thunks |
| 13_avs_dan_grammar.md | Byte-exact property-stream grammar for `.avs`, `.dan`, `.osw` |
| 14_abi_check_report.md | `abi_check.py` result, SDK 336 (PASS) |
| 14_abi_check_report_224.md | `abi_check.py` result, SDK 224 (FAIL, 19 items) |
| 15_measurement_import_internals.md | CSV parser, key table, units, application path |
| 16_impl_new_and_unused_apis.md | Implementations of new-in-336 and unused APIs (seam Partial, measurements, JSON APIs) |
| 17_log_message_catalog.md | Log and error string catalog, Logger behaviour, log locations, crash correlation |
| 18_cli_options.md | CLO command-line options (`headless`) |
| 19_avatar_resize_mechanism.md | Why patched `.avt` floats do not re-deform; `.avs` route and resize driver |
| 20_verification_report.md | Lane M: independent verification of thunks, struct size, CSV parser, constants |
| 21_fabric_appearance_internals.md | Colour/texture setter internals (no gamma, Front/Back, fall-backs) |
| 22_importdxf_internals.md | ImportDXF chain, return value, `m_Scale` (units claim superseded by 32/35) |
| 23_zprj_garment_structure.md | Garment `.zprj` / `.pac` structure, seams, fabric, texture clobbering |
| 24_simulate_newproject_deleteavatar.md | Simulate, NewProject, DeleteAvatar semantics |
| 25_glb_exporter_rule.md | GLB vertex rule; 606,659 is a counting artefact, real 200,134 |
| 26_verification_report_2.md | Lane M2 verification (driver call sites, `m_Scale`, Simulate, GLB) |
| 27_measurement_mapping.md | Mirra fields -> CLO feature indices, csv route break, ridge model |
| 28_avatar_deformation_model.md | CLO resizing preset (PCA) model; anchor interpolation idea |
| 29_modal_dialog_and_blocking_risks.md | Modal dialogs and blocking paths (Simulate, NewProject, ImportFile, resize) |
| 30_unimplemented_apis.md | The 30 thunk APIs (29 effectively dead), workarounds |
| 31_container_header_and_digest.md | `.avt`/`.zprj` header fields and SHA-256 digest formula |
| 32_dxf_reader_dispatch.md | DXF reader: `$INSUNITS` units, layers, annotations, checklist |
| 33_resize_dialog_reachability.md | Softbody/Divide prompt reachability from `ImportFile(.avs)` and mitigations |
| 34_measurement_ranges.md | Male/female training ranges, correlations, proposed hard/warn tiers |
| 35_verification_report_3.md | Lane M3: DXF unit source, CRT helpers, preset file headers, `.avt` loader calls |
| 36_importfile_dispatch.md | ImportFile type map, headless vs GUI, return values |
| 37_implemented_grading_apis.md | The 16 implemented grading slots and the template-switch flow |
| 38_fabric_physical_properties.md | No physics API; JFAB route; Default fabric values |
| 39_garment_glb_export_flow.md | Garment-only GLB export, selection, frame, materials, recipe |
| 40_avs_avatar_targeting.md | `.avs` resizes the current avatar only (corrects K/AG/AB) |
| 41_per_panel_texture_solutions.md | One fabric per panel plan, SetPatternPieceFabricIndex behaviour |
| 42_avatar_mesh_visibility_and_glb_size.md | No API to hide hair; `bVisible` patch idea; GLB size plan |
| 43_verification_report_4.md | Lane M4: `.avs` dword, target vector, grading `jb`, AddFabric, export gating |
| 44_dxf_validation_results.md | `dxf_validate.py` results on 44 DXFs, writer recommendations |
| 45_glb_slim_results.md | `glb_slim.py` measurements (-42.6% to -48.6%) |
| 46_avt_patch_tool_results.md | `avt_patch_tool.py` results (float and `bVisible` edits) |
| 47_plugin_compile_check.md | Plugin build log, `/Zs` syntax checks, API drift 224 -> 336 |
| 52_rea_binding_and_live_preflight.md | REA target identity, provider limitation, and live 336 plugin preflight |
| 53_live_avt_patch_redeform_336.md | Live SDK 336 test: five AVT field variants produce identical mesh buffers |
| 54_live_avs_import_modal_blocker_336.md | AVS targeting test stopped by reproducible AVT unzip/free-space modal blocker |
| 55_multi_instance_clo.md | Plugin completion events (long-poll, WebSocket) and parallel CLO sessions on separate ports |

## scripts/ (all Python 3, stdlib; run with `python -I`)

User-facing tools:

| Script | Purpose |
|---|---|
| abi_check.py | Slot/version/struct ABI check of SDK vs installed exe (PASS/FAIL) |
| dxf_validate.py | Validate DXFs against the CLO reader's rules (PASS/WARN/FAIL) |
| avt_patch_tool.py | Safe `.avt` patcher (feature floats, hide/show meshes, digest recompute) |
| glb_slim.py | Offline GLB slimming (drop meshes, weld, u16 indices, u8 weights/joints) |
| glb_probe.py, glb_dups.py | GLB structure summary; duplicate-vertex analysis |
| avs_grammar.py | Parse/round-trip/diff `.avs`/`.dan`/`.osw`/`.pac` property streams |
| avt_probe.py, zprj_probe.py | Inspect `.avt` and garment `.zprj` containers |

Disassembly and lookup helpers (lane working tools):

| Group | Scripts | Purpose |
|---|---|---|
| Disassembly drivers | disasm_fn.py, disasm_fn2..6.py, disasm_fn8..20.py, disasm_view.py, body_view.py, calls_view.py, wrap_view.py, slice.py, rd.py, rdata_dump.py, pdata_fn.py | Disassemble and view functions of the CLO exe (disasm_fn9.py was overwritten by a copy of disasm_fn6.py) |
| Cross-reference | xref_rip.py, xref_dialog9.py, xref_dialog12.py, callers5.py, revgraph5.py, reach9.py, reach12.py, k_callers.py, k_xref2.py, m3_ctx.py | Callers, reachability (reach scripts scan 0x200 bytes past targets without .pdata: false positives) |
| Vtable and slots | vtable_slots.py, target_slots.py, slots_lookup.py, hdr_align.py, exe_rtti.py, proxy_map.py, iat_name.py, af_enum.py, ag_typemap.py | Slot model, RTTI, proxies, grading enum, extension type map |
| Strings and catalogs | exe_strings.py, log_catalog.py, msg_catalog_gen.py, write_17.py, k_strscan.py, y_strscan.py, dxf_strscan.py, fab_scan.py | String scans and message catalogs |
| Binary/PE info | exe_report.py, pe_info.py, exports_analysis.py | PE headers, exports |
| Verification | verify_thunks.py, verify_dll_exports.py, verify_layout.py, verify_str.py, verify_dandiff_agg.py, verify_dandiff_scan.py, m2_k_scan.py, m2_n_consts.py, m2_r_scan.py, m2_t_posacc.py, m3_dispscan.py | Lane M/M2/M3 re-checks |
| Deformation model | w_allnames.py, w_bigleaves.py, w_extract.py, w_feats.py, w_fit.py, w_hdr.py, w_leafagg.py, w_pca_layout.py, w_pca_reg.py | Lane W `.dan` leaf analysis and PCA regression |
| Measurement ranges | ae_ranges.py, ae_analyze.py, ae_maletable.py, measure_map_extract.py | Lane AE preset statistics and key table |
| Digest/header | z_verify_digest.py, z_digest_test.py, z_digest_test2.py, z_digest_test3.py, z_constscan.py | Lane Z SHA-256 digest derivation |
| Other lane scripts | aa_brief.py, aa_region.py, ab_dan_flags.py, ab_reach_flags.py, ae_*.py, ak_garment_probe.py, fn3_brief.py, k_ann.py, k_dis.ps1, y_gen30.py | Per-lane helpers |

## experiments/ (live harness, written and syntax-checked, never run)

| File | Purpose |
|---|---|
| README.md | Safety rules, run order, blocked-experiment table |
| RESULTS_TEMPLATE.md | Per-experiment results form |
| _common.py | REST client, recorder, preflight (health, version match, idle queue) |
| e01_avs_single_avatar.py | `.avs` resizes only the current avatar (scenarios S1-S3) |
| e02_avt_patch_redeform.py | Does a patched `.avt` re-deform? (offline prepare + live compare) |
| e03_simulate_chunking.py | Simulate chunking and Folding/Draping restart |
| e04_grading_flow.py | Template-switch grading flow (blocked, exit 3) |
| e05_importdxf_units.py | `$INSUNITS` x `m_Scale` x annotation variants |
| e06_fabric_colour_readback.py | Colour read-back, Front/Back, gamma |
| e07_modal_watchdog.py | Windows modal-dialog watchdog (dry-run dismissal by default) |
| e08_export_gltf_scope.py | Export scope, component lists, hidden objects |
| e09_per_panel_fabrics.py | One fabric per panel via `ExportFabric` + `AddFabric` x3 + `AssignFabricToPattern` (fully blocked, exit 3: plugin routes missing) |
| e10_fabric_physical_preset.py | `ChangeFabricWithJson` stiff/soft presets (`--prepare` works offline; live part blocked) |
| e11_avatar_part_visibility.py | Hair/shoe `bVisible` patch and GLB mesh list (`--prepare` offline; AVT re-export check blocked) |

No `experiments/out/` exists yet (created on first run). `findings/48_recommendations_code_check.md` (lane M5) re-checks the repo-code claims in `RECOMMENDATIONS.md`.

## out/ (generated test outputs)

| Path | Purpose |
|---|---|
| out/avt_patch/base1_h_chest.avt | Patched copy: height 180.5, chest 100.0 (digest valid) |
| out/avt_patch/base1_nohair.avt | Patched copy: Hair `bVisible`=0 (untested in CLO) |
| out/avt_patch/base1_noshoes.avt | Patched copy: both shoes hidden (untested in CLO) |
| out/glb_slim/{A,B}_{base,weld,u16,w8,j8,drop,all,nodrop_all}.glb | 16 slimming variants of two sample GLBs (A text glTF, B real CLO GLB) |
| out/compile_check/14_abi_check_report_cc47.md | abi_check report (tag cc47, PASS) |
| out/compile_check/run_224.bat, run_336.bat | MSVC `/Zs` syntax-check launchers |

## raw/ (key files; about 230 raw tool outputs, mostly per-function disassembly)

| Path | Purpose |
|---|---|
| abi_check_336.json, abi_check_224.json, abi_check_cc47.json | Machine-readable ABI check results |
| exe_vtables.json, abi_exe_vtables_cache.json, exe_rtti_cache.json | Exe vtable and RTTI caches |
| exports_336_undecorated.txt, dll_exports_224.txt, dll_exports_336.txt, dll_imports_336.txt, dll_headers_336.txt, dll_deps_336.txt, app_exe_*.txt, app_dll_*.txt | PE exports, imports, headers, dependencies |
| hdrdiff_*.diff | SDK 224 vs 336 header diffs per API interface |
| exe_strings.txt, glb_summary.tsv, avs_tree.json | Exe string dump, GLB summary table, `.avs` parse tree |
| cloapi_iat.json | IAT map of the interface DLL |
| compile_check_224.txt, compile_check_336.txt | MSVC `/Zs` outputs |
| verify_thunks.json, y_unimpl_table.md | Thunk verification and the 30-API table |
| ae_out.txt | Derived preset statistics only (no Preset content) |
| af_*, ag_*, ak_*, ap_*, aq_*, aa_* | Per-lane function disassemblies and tables (lane prefix = lane letter) |
| disasm*, disasm2..20/ | Per-lane disassembly dumps |
| k_*, w_*, z_*, m_*, m2_*, m3_*, m4_* | Lane K/W/Z/M verification outputs and extracts (w_positions.pkl is a data pickle) |
| dxflib_rdata.txt, aama_rdata.txt | Vendored DXF library and AAMA strings in `.rdata` |
