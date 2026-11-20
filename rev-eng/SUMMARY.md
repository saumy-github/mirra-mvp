# CLO3D reverse-engineering: executive summary

*Status: lane AY synthesis. Static analysis only; no live CLO test has been run.*
*Date: 2026-10-30*
*Target: CLO Standalone OnlineAuth 2026.1.336 (build 58954), SDK 2026.1.336*

*Update 2026-11-10: a read-only live preflight passed with the 336 plugin
(`host_matches_sdk=true`, queue idle, zero avatars, no modal dialogs). No
mutating command has yet been run. See `findings/52_rea_binding_and_live_preflight.md`.*

*Update 2026-11-10: the first controlled mutating test also passed. Five
same-size AVT field variants imported and exported successfully on SDK 336,
with identical GLB buffer hashes. See
`findings/53_live_avt_patch_redeform_336.md`.*

*Update 2026-11-10: AVT import later reproduced a modal unzip failure even
with a re-packed copy; CLO reported approximately 11 GB free space. Further
mutations are stopped until disk space or the extraction environment is
addressed. See `findings/54_live_avs_import_modal_blocker_336.md`.*

See `FINDINGS.md` for the per-lane record, `RECOMMENDATIONS.md` for the action list and `INDEX.md` for the file map.

## High confidence (verified from bytes, headers or disassembly, mostly by lanes M/M2/M3/M4)
- The SDK DLL is only an ABI definition; the real implementations are in the exe. Vtable slot equals the header declaration index, with overloads grouped and reversed within a group. `abi_check.py` passes for SDK 336 against the installed app and fails for SDK 224 (13 called functions shift). The plugin build against 336 succeeded and is installed.
- `ImportExportOption` grew from 200 to 296 bytes between SDKs. A mismatched build mis-dispatches and likely corrupts the heap; that crash cause is inference.
- 30 Pattern/Utility APIs are import thunks to base-class stubs (25 Pattern slots 196-220 plus 5 Utility). 29 are effectively dead. Every grading create/edit API is among them; 16 grading read/switch slots are implemented.
- The `.avs`/`.dan`/`.pac` grammar is byte-exact. The `.avt`/`.zprj` header digest is SHA-256 over the header plus a fixed salt. Patching floats in an `.avt` never re-deforms the mesh, while `.avs` import does.
- `.avs` import resizes only the CURRENT avatar. It can raise modal boxes: "No matching Avatar.", an avatar chooser, softbody/divide prompts, and "lower version".
- `ImportDXF` returns true even for empty files. DXF units come from `$INSUNITS`. `m_Scale` is ignored while `m_bAutoScale` is true. Notches need `m_bIncludeNotchs`.
- `SetFabricPBRMaterialBaseColor` takes 0..1 floats with no gamma. The plugin always drapes with CLO's "Default" fabric. Per-panel textures overwrite each other because there is one shared fabric.
- The avatar GLB has 200,134 vertices (606,659 was a counting artefact), and hair is 71% of them. `Simulate` always returns true.

## Inferred (reasoned from code or data, not run)
- The mesh re-deformation path inside `0x50a0f70` and the PCA-based preset model. Anchor interpolation is feasible but unbuilt.
- Whether CLO honours the `.dan` `bVisible` patch for hair and shoes.
- The template-switch grading flow, including the avatar-swap risk.
- The fabric-copy sequence (`ExportFabric` plus `AddFabric` x3).
- Thin versus thick export.
- That each `Simulate` call restarts Folding/Draping.
- Whether modal boxes are reachable on the Simulate path (negative thread lengths, GPU).
- That version mismatch causes the import crashes. The crash trace (lane BA, `findings/49`) shows it is not the only cause: 3 of the 9 unmatched commands predate the version warning and one crashed with host and SDK both 224. The 336 plugin has run zero commands so far, so its stability is untested.
- (Resolved by lane BC, `findings/51`: CLO does not verify the container digest on load, and it uses the ZIP-length field 0x24 only as a read length: a value larger than the real ZIP loads fine, a smaller one breaks the load.)

## Needs live tests (`RECOMMENDATIONS.md` live-test table; harness in `experiments/`)
- `.avs` single-avatar targeting (e01).
- Whether `.avt` edits re-deform the mesh (e02).
- `Simulate` chunking (e03).
- The grading flow (e04, which first needs new plugin commands).
- DXF units and annotations (e05).
- Colour read-back (e06).
- The modal-dialog watchdog (e07).
- Export scope and hair hiding (e08).
- Per-panel fabrics and physical presets (new experiments, not yet written).

## Top 10 actions
1. Call `clear-avatars` before every avatar import (the client defines it but nothing calls it), and require exactly one avatar before `.avs`.
2. Gate every run on `host_matches_sdk`, and re-run `abi_check.py` after each CLO update.
3. Add AAMA annotation text to the DXF writer and validate with `dxf_validate.py`.
4. Create one fabric per panel (`AddFabric` x3 plus `AssignFabricToPattern`).
5. Add the softbody/Divide pre-flight and a modal-dialog watchdog with an allow-list.
6. Read measurements back after `.avs` with `GetAvatarMeasurements`, and do not trust import return values.
7. Stop sending a meaningless `m_Scale` (or set autoscale off with it), and enable `m_bIncludeNotchs`.
8. Slim the avatar GLB offline now (drop hair and shoes, weld, u16 indices, u8 weights): about -43% to -49%.
9. Replace the wide `step_03` sanity ranges with the training-data tiers and relational rules.
10. Add physical `.jfab` presets via `ChangeFabricWithJson`, and remove the dead grading route.
