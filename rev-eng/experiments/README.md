# CLO live-experiment harness (lane AN)

*Status: written, never run. Date: 2026-10-29. Stdlib-only Python 3.12.*

One script per experiment; each docstring states hypothesis, preconditions, exact steps, expected outcome per finding, and what to record (`python e01_avs_single_avatar.py --help` prints it). Results go to `experiments/out/<exp>_<timestamp>.json`; fill `RESULTS_TEMPLATE.md` per experiment.

## Safety (read first)
- Supervised only, a human at the keyboard and screen. Every script is a **dry run by default** (prints the plan, contacts nothing); pass `--live` to act. `e07` contacts only Windows APIs, never the plugin, and is dry-run for dismissal by default.
- Back up the CLO project/settings and the avatar/pattern inputs first. Scripts write only under `experiments/out/`; inputs are read-only. The plugin itself writes exports to the paths you give.
- **One CLO instance** (queue concurrency is 1). Do not run the pipeline or another experiment at the same time. Run `e07` in a second terminal while any live experiment runs (it only reads window lists).
- Preflight aborts unless `/health` is ok, `host_matches_sdk` is true (an SDK/app mismatch is known to crash import/delete/simulate), and the queue is idle. A queued command that does not finish within `--queue-timeout` aborts with "modal dialog?"; dismiss the box by hand, then check `/health`.
- Plugin REST is unauthenticated on 127.0.0.1:50505 (no token env var exists). `MIRRA_CLO_URL` overrides the base URL.
- Headless caveats: findings say behaviour differs headless vs GUI (`ImportMeasurement` 1-arg only works headless; `ImportFile` slot 2 takes another path in GUI for avs/avt/obj/zprj...). Run in the same mode as the pipeline uses and record which. Modal boxes have no headless guard.
- Never call `POST /avatar/grading-size` (it invokes an unimplemented thunk). No script does.
- `/new-project` is used between files in e03/e05/e06/e08; if CLO hangs there, stop and restart CLO.
- Opening a `.zprj` goes through the generic ImportFile hidden behind `/import-avatar-avt` with `method=import_file`; unverified for zprj.

## Run order
1. `e07_modal_watchdog.py --list-once` (check it sees CLO windows), then leave it running in a second terminal.
2. `e02_avt_patch_redeform.py --avt <stock.avt>` (offline prepare, then `--live` to compare).
3. `e01_avs_single_avatar.py` (scenarios S1, S2, S3 in its docstring; lane AL: only the CURRENT avatar is resized).
4. `e05_importdxf_units.py`, `e08_export_gltf_scope.py`, `e06_fabric_colour_readback.py`.
5. `e03_simulate_chunking.py` (slowest, riskiest: Simulate).
6. `e04_grading_flow.py` is blocked (fails fast, exit 3).

## Blocked / partly blocked by missing plugin commands
| Exp | Missing command | Effect |
|---|---|---|
| e01 | GetAvatarMeasurements; get/set current avatar | uses GetAvatarProperties via `/avatars/state`; current avatar inferred from what changed |
| e03 | vertex hash/read-back after Simulate | fallback GLB bin sha256 |
| e04 | GetGradingSizeGroupCount, ChangeGradingSizeInformation, GetCurrentGradingSizeIndex, GetGradingPairedAvatar | fully blocked |
| e05 | UNITS/PIECE NAME/SAMPLE SIZE entity layout (not a plugin gap) | those variants must be hand-made |
| e06 | GetFabricPBRMaterialBaseColor, Front/Back face parameter | GLB baseColorFactor proxy; Front/Back untestable |
| e08 | pattern/avatar component lists on `/export` | only whole-scene content variants |
| e02, e07 | none | e02 prepare is offline |

Exit codes: 0 ok/dry-run, 3 blocked by missing plugin command, other nonzero = abort.

## Lane AZ additions (e09-e11)

*Status: written, never run. Date: 2026-10-30.*

| Exp | Hypothesis | Missing plugin command / proposed route | Effect |
|---|---|---|---|
| e09 | ExportFabric + AddFabric x3 + AssignFabricToPattern gives each T-shirt panel its own fabric (4 GLB materials) | GetFabricCount, ExportFabric, AddFabric, AssignFabricToPattern, GetPatternPieceFabricIndex: `GET /fabric/count`, `POST /fabric/export`, `POST /fabric/add`, `POST /fabric/assign`, `GET /patterns/<i>/fabric` (findings/41 sec 8) | fully blocked, exit 3 (also in dry run) |
| e10 | ChangeFabricWithJson(0, preset.jfab) changes drape (default vs stiff vs soft) | `POST /fabric/physical` mode change (PLUGIN_COMMAND_SPEC sec 3.1), `GET /fabric/count` | live part blocked, exit 3; `--prepare` builds the .jfab presets offline into out/e10/ |
| e11 | Patched .dan bVisible=0 (Hair/shoes) makes ExportGLB skip them | runnable with existing routes; AVT re-export (does ImportAvatar keep the flag?) has no route: proposed `POST /export-avatar-avt` or zprj save + zprj_probe | partly blocked; `--prepare` writes patched copies offline into out/e11/; `--need-avt-reexport` exits 3 |

Run e11 `--prepare` first, then `--live` (supervised, one CLO). e09/e10 only after the routes above are added and the plugin rebuilt (SDK must match the CLO app).
