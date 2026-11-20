# Avatar generation runs: summary

*Status: written before deleting the heavy files from `clo_avatar_generation/output/`; the deletion was done on 2026-11-20 (1,673 files, 14.64 GiB; 149 folders and the 6 root files kept)*
*Date: 2026-11-20*

Every folder in `output/` is kept, so run numbering continues as before (the next number is worked out from the folder names in `avatar_runtime/run_manifest.py`). The heavy files (`.avt`, `.zprj`, `.glb`, `.bin`, `.zip`, `.dan`) and the texture images (`.png`, `.jpg`) inside the run folders are deleted to free disk space (decided 2026-11-20). The small files stay: `run.log`, the JSON and CSV files, `.avs` inputs and `.txt` notes. The five loose probe files directly in `output/` (`probe_*.avt`) were kept.

The facts below come from each folder's `run.log`, its JSON files, and a read of every heavy file just before deletion (measurement floats inside each `.avt`, and the vertex count and height of each GLB). The appendix lists each deleted file with its size and the first 16 characters of its SHA-256.

- Run folders: 149
- Deleted: 451 heavy files (14.08 GiB) and 1222 texture images (0.56 GiB)

## 1. The story in phases

| Dates | Runs | What was tried | Outcome | What we learned |
|---|---|---|---|---|
| 2026-03-31 to 04-07 | u_001-001 to 006, 011 | CSV measurement import (`ImportAvatarMeasurement` with a bridge CSV) | Failed every time | The CSV route does not work in the GUI CLO (later traced to headless-only behaviour, `rev-eng/findings/11`) |
| 2026-04-07 | u_001-007, 009, 010 | `SetAvatarProperties` route | "Completed", but the saved body was the unchanged base (187.96 cm) | Avatar properties are physics settings, not body measurements |
| 2026-04-07 | field_probes_20260407 | Patch one measurement float at a time inside base-1.avt | Verification passed for all six fields after a CLO round trip | Fixed the field-to-float index map |
| 2026-04-07 to 07-06 | u_001-012 to 039 | `avt_patch`: patch the floats inside the `.avt`, import it, save | Mostly success; failures were CLO going down or the plugin not running; 022 showed the direct `.avt` export is invalid | `avt_patch` became the main route; save the avatar from the project file; health check first |
| 2026-07-06 | u_002, u_003, u_004, u_005 | Other test users | u_002 fine; u_003 to u_005 stopped for missing measurements | Input validation works |
| 2026-07-06 to 08-02 | u_001-040 to 061 | Repeat-run stability series | 6 of 15 runs (040 to 054) and 3 later runs saved a mesh 7 to 10% smaller than base | Saving was unreliable until the plugin built 2026-08-01 |
| 2026-08-08 to 08-09 | u_001-062 to 064, g_241f…, g_4e1a… | Avatar GLB export added (text glTF, then packed binary GLB) | Success | Every GLB: 606,659 vertices, 1.9213 m tall, whatever the requested height |
| 2026-08-20 | u_001-065 to 074, website users u_5c93…, u_dcabc…-001 to 007 | More repeats; first runs from the website | 5 runs saved the base body instead of the patched one; website runs hit import timeouts or had no measurements (MongoDB down) | Patched import can silently fail; verification is needed |
| 2026-08-22 to 08-23 | u_001-075 to 080, u_011 to u_015, u_dcabc…-008 | Several targets in a row; five users started at once | Only 1 of 5 targets applied in 076 to 080; parallel starts timed out; later runs had 2 to 4 avatars in one scene | CLO takes one job at a time; avatars pile up without a clear step; GLBs byte-identical across users (u_011-001 168 cm = u_001-065 178.5 cm) |
| 2026-08-29 | u_001-081 | Plugin build with binary-only GLB | Success | No more loose texture files |
| 2026-09-12 | u_001-082, 083 | - | Plugin not running | - |
| 2026-10-14 | u_001-084 to 091, u_011 to u_015 (-006/-007) | CLO updated to 2026.1.310; plugin rebuilt | Crashes and timeouts while `host_matches_sdk=false`; all fine again on CLO 2026.1.224 | The plugin must be built for the installed CLO version; GLBs still identical (1.9213 m) |
| 2026-10-15 to 10-18 | u_003-003 to 005, u_001-092, u_dcabc…-009, g_e5c3… | `.avs` route (import a measurement `.avs`) | Success | The mesh finally scales: 137 cm gives 1.4132 m, 175 cm 1.7921 m, 178.5 cm 1.8271 m, 179.5 cm 1.8371 m |

## 2. Every run

Columns: **Route** is how measurements were applied. **Body** shows the requested height (`asked`, from the patched `.avt`) and the height stored in the saved avatar (`saved`), in cm. **GLB** is the exported avatar mesh (vertex count, height in metres). **Deleted** is MB removed from that folder.

| Run | Started | Route | Result | Body (cm) | GLB | Problem or success | What we learned / why it was useful | Deleted (MB) |
|---|---|---|---|---|---|---|---|---|
| u_001-001 | 2026-03-31 16:02 | csv import | failed |  |  | CSV measurement import failed, then CLO stopped answering | First run. The CSV route (`ImportAvatarMeasurement`) did not apply measurements in the GUI CLO. MongoDB was unreachable, so the input snapshot was used. | 0 |
| u_001-002 | 2026-03-31 16:08 | csv import | failed |  |  | Same as 001 | Repeat; same CSV failure and lost CLO connection. | 0 |
| u_001-003 | 2026-04-01 09:13 | csv import | failed |  |  | CSV import failed | The CSV route fails even with CLO healthy. Later traced to `ImportMeasurement` working only when CLO runs headless (`rev-eng/findings/11`). | 0 |
| u_001-004 | 2026-04-01 09:44 | csv import | failed |  |  | CSV import failed | Same CSV failure. | 0 |
| u_001-005 | 2026-04-07 11:09 | csv import | failed |  |  | CSV import failed | Same CSV failure, new day. | 0 |
| u_001-006 | 2026-04-07 11:14 | csv import | failed |  |  | CSV import failed | Same CSV failure; led to trying a different route. | 0 |
| u_001-007 | 2026-04-07 12:02 | avatar_properties | success | saved 187.96 |  | Pipeline 'completed' but the avatar is the unchanged base body | Route `avatar_properties` (`SetAvatarProperties`). Saved avatar still has the base height 187.96 cm. Showed that avatar properties are physics settings, not body measurements. Files in `_inspect/` were unpacked to study the `.avt` format. | 290 |
| u_001-008 | 2026-04-07 12:21 | - | failed |  |  | Base avatar path was 'y' (typing slip) | Input validation of the base avatar path works. | 0 |
| u_001-009 | 2026-04-07 12:21 | avatar_properties | success | saved 187.96 |  | 'Completed', body unchanged (187.96 cm) | Confirms 007: the properties route does not resize the body. | 99 |
| u_001-010 | 2026-04-07 12:23 | avatar_properties | success | saved 187.96 |  | 'Completed', body unchanged (187.96 cm) | Third confirmation; the properties route was dropped. | 99 |
| u_001-011 | 2026-04-07 12:28 | csv import | failed |  |  | CSV import failed | Last try of the CSV route. | 0 |
| u_001-012 | 2026-04-07 12:39 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success: patched floats verified | First `avt_patch` run: the measurement floats inside the `.avt` were patched and read back (178.5 / 100 / 85). Became the main route for months. | 131 |
| u_001-013 | 2026-04-07 12:44 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success with a height-only filter | Field filter test: only Total Height changed (178.5); the other fields stayed at base values. | 131 |
| u_001-014 | 2026-04-07 12:48 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat of 012; result stable. | 131 |
| field_probes_20260407 | 2026-04-07 18:11 | avt_patch probes | success | one field per probe (height 178.5, chest 100, waist 85, ...) |  | Per-field patch probes | Each of six fields (height, chest, waist, low hip, inseam, across shoulder) was patched alone in base-1.avt, imported and exported by CLO; `summary.json` shows verification passed for all six, and in the exported height, chest and waist probes only the patched field differed from base. Proved the field-to-float index map used by `avt_patch`. | 388 |
| u_001-015 | 2026-04-12 10:57 | - | failed |  |  | Base avatar path was 'y' again | Same input slip as 008. | 0 |
| u_001-016 | 2026-04-12 14:13 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | avt_patch repeat; stable. | 131 |
| u_001-017 | 2026-05-17 07:21 | avt_patch | failed | asked 178.5 |  | CLO stopped answering during save | CLO was lost during the save step; showed the save step needs a live-connection check. | 32 |
| u_001-018 | 2026-05-17 07:23 | avt_patch | failed | asked 178.5 |  | CLO stopped answering during save | Same as 017. | 32 |
| u_001-019 | 2026-05-17 07:32 | avt_patch | failed | asked 178.5 |  | CLO stopped answering during save | Same as 017. | 32 |
| u_001-020 | 2026-05-17 07:46 | avt_patch | failed | asked 178.5 |  | CLO stopped answering during save | Same as 017. | 32 |
| u_001-021 | 2026-05-17 07:51 | - | failed |  |  | Plugin not running | Health check stopped the run before any work (good fail-fast). | 0 |
| u_001-022 | 2026-05-17 07:55 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Directly exported `.avt` had no ZIP inside | The direct avatar export was not a valid `.avt`, so the pipeline switched to extracting the avatar from the saved project (`result_avatar_from_project.avt`). | 102 |
| u_001-023 | 2026-05-17 08:02 | avt_patch | failed | asked 178.5 / saved 178.5 |  | CLO stopped answering during save | Same as 017. | 99 |
| u_001-024 | 2026-05-17 08:09 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | First good run with the 'avatar from project' save; verification passed. | 93 |
| u_001-025 | 2026-05-17 08:10 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-026 | 2026-05-17 08:11 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 93 |
| u_001-027 | 2026-05-17 08:13 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-028 | 2026-06-30 14:56 | avt_patch | success | saved 178.5 |  | Success | Re-check after a break; route stable. | 126 |
| u_001-029 | 2026-06-30 19:33 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-030 | 2026-07-02 18:02 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 93 |
| u_001-031 | 2026-07-02 18:25 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-032 | 2026-07-02 19:53 | - | failed |  |  | Plugin not running | Health check stopped the run. | 0 |
| u_001-033 | 2026-07-02 19:57 | - | failed |  |  | Plugin not running | Health check stopped the run. | 0 |
| u_001-034 | 2026-07-02 20:11 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-035 | 2026-07-06 08:17 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success, `avt_patch` requested explicitly | Apply mode can now be forced instead of 'auto'. | 94 |
| u_001-036 | 2026-07-06 08:18 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-037 | 2026-07-06 14:10 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | First run with the full `run.log` written into the run folder. | 100 |
| u_001-038 | 2026-07-06 16:09 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-039 | 2026-07-06 16:13 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-040 | 2026-07-06 17:26 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Start of a repeat-run stability series (040 to 054) on the plugin built 2026-07-02. | 100 |
| u_002-001 | 2026-07-06 18:08 | avt_patch | success | asked 182.0 / saved 182.0 |  | Success (182 cm) | Second test user; route works for other measurements. | 100 |
| u_003-001 | 2026-07-06 18:22 | avt_patch | failed |  |  | Missing hip and leg measurements | Validation stops incomplete user records before CLO is touched. | 0 |
| u_004-001 | 2026-07-06 18:23 | avt_patch | failed |  |  | Missing chest and shoulder measurements | Validation stops incomplete records. | 0 |
| u_005-001 | 2026-07-06 18:23 | avt_patch | failed |  |  | Missing five measurements | Validation stops incomplete records. | 0 |
| u_003-002 | 2026-07-06 18:25 | avt_patch | failed |  |  | Missing hip and leg measurements | Same as 001. | 0 |
| u_002-002 | 2026-07-06 18:26 | avt_patch | success | asked 182.0 / saved 182.0 |  | Success | Repeat. | 100 |
| u_004-002 | 2026-07-06 18:26 | avt_patch | failed |  |  | Missing chest and shoulder measurements | Same. | 0 |
| u_005-002 | 2026-07-06 18:26 | avt_patch | failed |  |  | Missing five measurements | Same. | 0 |
| u_001-041 | 2026-07-06 18:32 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-042 | 2026-07-06 18:34 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-043 | 2026-07-06 18:35 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Saved avatar mesh 7.15% smaller than base | New size guard caught a structurally incomplete avatar mesh after 3 save attempts. 6 of 15 runs in the 040 to 054 series failed this way: saving was not reliable. | 94 |
| u_001-044 | 2026-07-06 18:36 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-045 | 2026-07-06 18:41 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Saved avatar mesh smaller than base | Same intermittent save problem as u_001-043. | 94 |
| u_001-046 | 2026-07-06 18:42 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-047 | 2026-07-06 18:43 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-048 | 2026-07-06 18:44 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Saved avatar mesh smaller than base | Same intermittent save problem as u_001-043. | 94 |
| u_001-049 | 2026-07-06 18:46 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Saved avatar mesh smaller than base | Same intermittent save problem as u_001-043. | 94 |
| u_001-050 | 2026-07-06 18:47 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-051 | 2026-07-06 18:48 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-052 | 2026-07-06 18:49 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Saved avatar mesh smaller than base | Same intermittent save problem as u_001-043. | 94 |
| u_001-053 | 2026-07-06 18:51 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Saved avatar mesh smaller than base | Same intermittent save problem as u_001-043. | 94 |
| u_001-054 | 2026-07-06 18:52 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-055 | 2026-07-23 15:29 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Mesh 9.18% smaller than base | Guard still triggering with the plugin built 2026-07-23. | 93 |
| u_001-056 | 2026-07-23 15:32 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Mesh 7.83% smaller than base | Same as 055. | 94 |
| u_001-057 | 2026-07-23 15:36 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_002-003 | 2026-07-23 15:37 | avt_patch | success | asked 182.0 / saved 182.0 |  | Success | Repeat on plugin 2026-07-23. | 100 |
| u_001-058 | 2026-08-02 01:13 | avt_patch | failed | asked 178.5 / saved 178.5 |  | Mesh 9.67% smaller than base | Same as 055; fixed by the plugin built 2026-08-01 (059 onwards pass). | 93 |
| u_001-059 | 2026-08-02 01:31 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Plugin build 2026-08-01: saving reliable again. | 100 |
| u_001-060 | 2026-08-02 01:36 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-061 | 2026-08-03 00:27 | avt_patch | success | asked 178.5 / saved 178.5 |  | Success | Repeat run; confirms the route is stable at that time. | 100 |
| u_001-062 | 2026-08-08 19:18 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success, first GLB export | First avatar GLB: text glTF saved as `.glb` with external `.bin` and texture images. 606,659 vertices, height 1.9213 m. | 125 |
| u_001-063 | 2026-08-08 19:59 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success, GLB | Same as 062. | 125 |
| u_001-064 | 2026-08-08 21:01 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success, packed binary GLB added | `result_avatar_packed.glb` (real binary GLB) written next to the text one. | 154 |
| g_4e1a14ccadb2fd2f-001 | 2026-08-08 22:19 | avt_patch | success | asked 175.0 / saved 175.0 | 606,659 verts, 1.9213 m | Success (175 cm) | Guest user; same as above. | 154 |
| g_241f677bd4b8f8a4-001 | 2026-08-09 00:30 | avt_patch | success | asked 175.0 / saved 175.0 | 606,659 verts, 1.9213 m | Success (175 cm) | Guest user from the website; GLB 1.9213 m tall like every avt_patch GLB. | 154 |
| u_5c939be0e3cff36f-001 | 2026-08-20 10:40 | avt_patch | failed |  |  | Import never finished | Website user; first runs from the website flow hit the import timeout. | 0 |
| u_dcabc592e2bb18e7-001 | 2026-08-20 11:10 | avt_patch | failed |  |  | Import never finished | Website user; import timeout. | 0 |
| u_dcabc592e2bb18e7-002 | 2026-08-20 11:28 | avt_patch | failed |  |  | Import never finished | Same. | 0 |
| u_dcabc592e2bb18e7-003 | 2026-08-20 20:38 | avt_patch | failed |  |  | No measurements: MongoDB down and no local snapshot | Website user had no local fallback; showed the need for the database to be up (or a snapshot). | 0 |
| u_dcabc592e2bb18e7-004 | 2026-08-20 20:38 | avt_patch | failed |  |  | No measurements (MongoDB down) | Same as 003. | 0 |
| u_dcabc592e2bb18e7-005 | 2026-08-20 20:39 | avt_patch | failed |  |  | No measurements (MongoDB down) | Same as 003. | 0 |
| u_dcabc592e2bb18e7-006 | 2026-08-20 20:39 | avt_patch | failed |  |  | No measurements (MongoDB down) | Same as 003. | 0 |
| u_dcabc592e2bb18e7-007 | 2026-08-20 20:40 | avt_patch | failed |  |  | No measurements (MongoDB down) | Same as 003. | 0 |
| u_001-065 | 2026-08-20 20:43 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success | Its GLB files are byte-identical to the ones from u_011-001/002 (168 cm user) and u_001-075: the GLB did not depend on the measurements. | 154 |
| u_001-066 | 2026-08-20 20:44 | avt_patch | failed | asked 178.5 / saved 187.96 |  | Saved avatar = base body (187.96 cm) | Patched avatar was not applied; verification caught it. 066 to 069 and 074 all reverted to base: silent failure of the patched import. | 132 |
| u_001-067 | 2026-08-20 20:45 | avt_patch | failed | asked 178.5 / saved 187.96 |  | Saved avatar = base body | Same silent patched-import failure as u_001-066. | 132 |
| u_001-068 | 2026-08-20 20:46 | avt_patch | failed | asked 178.5 / saved 187.96 |  | Saved avatar = base body | Same silent patched-import failure as u_001-066. | 132 |
| u_001-069 | 2026-08-20 20:47 | avt_patch | failed | asked 178.5 / saved 187.96 |  | Saved avatar = base body | Same silent patched-import failure as u_001-066. | 132 |
| u_001-070 | 2026-08-20 23:26 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_001-071 | 2026-08-20 23:28 | avt_patch | success | asked 178.5 / saved 178.5 | 1,819,977 verts, 1.9213 m | Success, but 3 avatars in the scene | GLB had 1,819,977 vertices (3 x 606,659): avatars pile up in the CLO scene unless cleared. | 327 |
| u_001-072 | 2026-08-20 23:30 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_001-073 | 2026-08-20 23:31 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_001-074 | 2026-08-20 23:32 | avt_patch | failed | asked 178.5 / saved 187.96 |  | Saved avatar = base body | Same silent patched-import failure as u_001-066. | 132 |
| u_001-075 | 2026-08-22 19:10 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success | GLB byte-identical to 065. | 154 |
| u_001-076 | 2026-08-22 19:11 | avt_patch | failed | asked 165.0 / saved 178.5 |  | Asked 165 cm, got 178.5 cm (previous avatar) | Multi-target test (076 to 080): CLO kept the previous avatar. Only 078 (172 cm) applied correctly. | 165 |
| u_001-077 | 2026-08-22 19:12 | avt_patch | failed | asked 185.0 / saved 187.96 |  | Asked 185 cm, got base 187.96 cm | Multi-target test: reverted to base. | 132 |
| u_001-078 | 2026-08-22 19:13 | avt_patch | success | asked 172.0 / saved 172.0 | 606,659 verts, 1.9213 m | Success, 172 cm applied | Only success in the multi-target test; GLB still 1.9213 m tall, same as every other avt_patch GLB. | 154 |
| u_001-079 | 2026-08-22 19:14 | avt_patch | failed | asked 190.0 / saved 187.96 |  | Asked 190 cm, got base 187.96 cm | Multi-target test: reverted to base. | 132 |
| u_001-080 | 2026-08-22 19:31 | avt_patch | failed | asked 178.5 / saved 187.96 |  | Asked 178.5 cm, got base 187.96 cm | Multi-target test: reverted to base. | 132 |
| u_011-001 | 2026-08-22 21:34 | avt_patch | success | asked 168.0 / saved 168.0 | 606,659 verts, 1.9213 m | Success (168 cm) | Seeded batch user. GLB byte-identical to the 178.5 cm user's GLB (u_001-065): proof that avt_patch GLBs ignore measurements. | 154 |
| u_012-001 | 2026-08-22 21:35 | avt_patch | failed |  |  | Import never finished | Five users (u_011 to u_015) were started at the same moment; queue sizes 0 to 3 show they shared one CLO. CLO handles one job at a time. | 0 |
| u_013-001 | 2026-08-22 21:36 | avt_patch | failed |  |  | Import never finished (parallel start) | Same cause as u_012-001. | 0 |
| u_014-001 | 2026-08-22 21:36 | avt_patch | failed |  |  | Import never finished (parallel start) | Same cause as u_012-001. | 0 |
| u_015-001 | 2026-08-22 21:37 | avt_patch | failed |  |  | Import never finished (parallel start) | Same cause as u_012-001. | 0 |
| u_011-002 | 2026-08-22 23:38 | avt_patch | success | asked 168.0 / saved 168.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_012-002 | 2026-08-22 23:39 | avt_patch | success | asked 175.0 / saved 175.0 | 1,213,318 verts, 1.9213 m | Success, 2 avatars in the scene | 1,213,318-vertex GLB (2 avatars). | 240 |
| u_013-002 | 2026-08-22 23:41 | avt_patch | success | asked 181.0 / saved 181.0 | 1,213,318 verts, 1.9213 m | Success, 2 avatars in the scene | Same pile-up as u_012-002. | 240 |
| u_014-002 | 2026-08-22 23:42 | avt_patch | success | asked 186.0 / saved 186.0 | 1,213,318 verts, 1.9213 m | Success, 2 avatars in the scene | Same pile-up. | 240 |
| u_015-002 | 2026-08-22 23:44 | avt_patch | success | asked 186.0 / saved 186.0 | 1,213,318 verts, 1.9213 m | Success, 2 avatars in the scene | Same pile-up. | 240 |
| u_011-003 | 2026-08-22 23:59 | avt_patch | success | asked 168.0 / saved 168.0 | 1,819,977 verts, 1.9215 m | Success, 3 avatars in the scene | 1,819,977-vertex GLB: avatars accumulate without a clear step. | 327 |
| u_012-003 | 2026-08-23 00:01 | avt_patch | success | asked 175.0 / saved 175.0 | 2,426,636 verts, 1.9215 m | Success, 4 avatars in the scene | 2,426,636-vertex GLB (4 avatars): worst pile-up seen. | 414 |
| u_013-003 | 2026-08-23 00:03 | avt_patch | success | asked 181.0 / saved 181.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_014-003 | 2026-08-23 00:04 | avt_patch | success | asked 186.0 / saved 186.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_015-003 | 2026-08-23 00:05 | avt_patch | success | asked 186.0 / saved 186.0 | 1,213,318 verts, 1.9213 m | Success, 2 avatars in the scene | Same pile-up. | 240 |
| u_011-004 | 2026-08-23 00:16 | avt_patch | success | asked 168.0 / saved 168.0 | 1,819,977 verts, 1.9213 m | Success, 3 avatars in the scene | Same as 003. | 327 |
| u_012-004 | 2026-08-23 00:18 | avt_patch | success | asked 175.0 / saved 175.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_013-004 | 2026-08-23 00:20 | avt_patch | success | asked 181.0 / saved 181.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_014-004 | 2026-08-23 00:21 | avt_patch | success | asked 186.0 / saved 186.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_015-004 | 2026-08-23 00:23 | avt_patch | success | asked 186.0 / saved 186.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_011-005 | 2026-08-23 00:25 | avt_patch | success | asked 168.0 / saved 168.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_012-005 | 2026-08-23 00:26 | avt_patch | success | asked 175.0 / saved 175.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_013-005 | 2026-08-23 00:28 | avt_patch | success | asked 181.0 / saved 181.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_014-005 | 2026-08-23 00:29 | avt_patch | success | asked 186.0 / saved 186.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_015-005 | 2026-08-23 00:30 | avt_patch | success | asked 186.0 / saved 186.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 154 |
| u_013-006 | 2026-08-23 00:51 | avt_patch | success | asked 181.0 / saved 181.0 | 606,659 verts, 1.9213 m | Success | Repeat run; confirms the route is stable at that time. | 137 |
| u_dcabc592e2bb18e7-008 | 2026-08-23 00:59 | avt_patch | success | asked 179.5 / saved 179.5 | 1,213,318 verts, 1.9213 m | Success (179.5 cm), 2 avatars in the scene | Website user finally generated; GLB still 1.9213 m tall. | 195 |
| u_001-081 | 2026-08-29 13:30 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success, binary GLB only | From the plugin built 2026-08-29: one binary GLB, no loose texture files. | 137 |
| u_001-082 | 2026-09-12 19:44 | avt_patch | failed |  |  | Plugin not running | Health check stopped the run. | 0 |
| u_001-083 | 2026-09-12 19:50 | avt_patch | failed |  |  | Plugin not running | Health check stopped the run. | 0 |
| u_001-084 | 2026-10-14 15:43 | avt_patch | failed | asked 178.5 |  | CLO stopped answering during apply | Old plugin (built 2026-09-12) on an updated CLO; CLO went down during the apply step. | 32 |
| u_001-085 | 2026-10-14 15:48 | avt_patch | failed | asked 178.5 |  | CLO stopped answering during apply | Same as 084. | 32 |
| u_001-086 | 2026-10-14 16:00 | avt_patch | failed | asked 178.5 |  | CLO stopped answering during apply | Same as 084. | 32 |
| u_001-087 | 2026-10-14 16:17 | avt_patch | failed | asked 178.5 |  | CLO 2026.1.310 vs plugin SDK: mismatch | New `/health` field `host_matches_sdk=false`. A plugin built for a different CLO version crashes CLO on import or apply. | 32 |
| u_001-088 | 2026-10-14 16:27 | avt_patch | failed |  |  | Import never finished (version mismatch) | Same cause as 087. | 0 |
| u_001-089 | 2026-10-14 16:29 | avt_patch | failed |  |  | Import never finished (version mismatch) | Same cause as 087. | 0 |
| u_001-090 | 2026-10-14 16:31 | avt_patch | failed | asked 178.5 |  | CLO went down during apply (version mismatch) | Same cause as 087; led to the rule: run only when `host_matches_sdk` is true. | 32 |
| u_001-091 | 2026-10-14 16:48 | avt_patch | success | asked 178.5 / saved 178.5 | 606,659 verts, 1.9213 m | Success on matching CLO 2026.1.224 | Version match fixed the crashes. GLB still 606,659 vertices and 1.9213 m tall. | 137 |
| u_011-006 | 2026-10-14 16:59 | avt_patch | success | asked 168.0 / saved 168.0 | 606,659 verts, 1.9213 m | Success on matching CLO 224 | Re-run after the version fix. | 137 |
| u_012-006 | 2026-10-14 17:00 | avt_patch | success | asked 175.0 / saved 175.0 | 606,659 verts, 1.9213 m | Success on matching CLO 224 | Re-run after the version fix. | 137 |
| u_013-007 | 2026-10-14 17:02 | avt_patch | success | asked 181.0 / saved 181.0 | 606,659 verts, 1.9213 m | Success on matching CLO 224 | Re-run after the version fix. | 137 |
| u_014-006 | 2026-10-14 17:03 | avt_patch | success | asked 186.0 / saved 186.0 | 606,659 verts, 1.9213 m | Success on matching CLO 224 | Re-run after the version fix. | 137 |
| u_015-006 | 2026-10-14 17:04 | avt_patch | success | asked 186.0 / saved 186.0 | 606,659 verts, 1.9213 m | Success on matching CLO 224 | Re-run after the version fix. | 137 |
| u_003-003 | 2026-10-15 13:37 | avs | failed |  |  | Missing hip and leg measurements | Same record problem on the `.avs` route. | 0 |
| u_003-004 | 2026-10-15 13:37 | avs | success | saved 175.0 | 606,659 verts, 1.7921 m | Success, `.avs` route (175 cm) | GLB height 1.7921 m: mesh scales with height on the `.avs` route. | 105 |
| u_001-092 | 2026-10-16 09:37 | avs | success | saved 178.5 | 606,659 verts, 1.8271 m | Success, `.avs` route | First u_001 run on the `.avs` route: GLB height 1.8271 m for 178.5 cm requested. The body mesh finally changes with the measurements. | 105 |
| u_003-005 | 2026-10-16 09:38 | avs | success | saved 175.0 | 606,659 verts, 1.7921 m | Success, `.avs` route | Repeat from an explicit measurement file; same GLB height 1.7921 m (repeatable). | 105 |
| u_dcabc592e2bb18e7-009 | 2026-10-18 20:53 | avs | success | saved 179.5 | 606,659 verts, 1.8371 m | Success, `.avs` route | Same user on the `.avs` route: GLB 1.8371 m for 179.5 cm. | 105 |
| g_e5c37ff7a450d060-001 | 2026-10-18 22:13 | avs | success | saved 137.0 | 606,659 verts, 1.4132 m | Success, `.avs` route (137 cm) | Shortest body tested: GLB 1.4132 m tall. Confirms the `.avs` route scales the mesh. | 105 |

## 3. Appendix: deleted files

| Run | File | MB | SHA-256 (first 16) | Contents read before deletion |
|---|---|---|---|---|
| field_probes_20260407 | across_shoulder_curvilinear.exported.avt | 32.4 | 4a6582de4a13801b | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| field_probes_20260407 | across_shoulder_curvilinear.patched.avt | 32.4 | eea5eaeaad8e083c | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| field_probes_20260407 | chest.exported.avt | 32.4 | 6e206a4df4d16381 | H 187.96, chest 100.0, waist 82.55, low hip 95.25 |
| field_probes_20260407 | chest.patched.avt | 32.4 | 30660bd76ff70d88 | H 187.96, chest 100.0, waist 82.55, low hip 95.25 |
| field_probes_20260407 | inseam.exported.avt | 32.4 | 0d2bb827279005bd | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| field_probes_20260407 | inseam.patched.avt | 32.4 | aa550b24d797252a | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| field_probes_20260407 | low_hip.exported.avt | 32.4 | 49f91861a0b5dae6 | H 187.96, chest 96.52, waist 82.55, low hip 98.0 |
| field_probes_20260407 | low_hip.patched.avt | 32.4 | 721a60af367868ef | H 187.96, chest 96.52, waist 82.55, low hip 98.0 |
| field_probes_20260407 | total_height.exported.avt | 32.4 | 2ebbc7f2c1bd1cde | H 178.5, chest 96.52, waist 82.55, low hip 95.25 |
| field_probes_20260407 | total_height.patched.avt | 32.4 | a357e62e75ee5d97 | H 178.5, chest 96.52, waist 82.55, low hip 95.25 |
| field_probes_20260407 | waist.exported.avt | 32.4 | 9be65ec0d2e451ba | H 187.96, chest 96.52, waist 85.0, low hip 95.25 |
| field_probes_20260407 | waist.patched.avt | 32.4 | 44027ecaadcb4383 | H 187.96, chest 96.52, waist 85.0, low hip 95.25 |
| g_241f677bd4b8f8a4-001 | clo_payload.patched.avt | 32.4 | 914ef07079165110 | H 175.0, chest 100.0, waist 85.0, low hip 98.0 |
| g_241f677bd4b8f8a4-001 | result_avatar.bin | 12.8 | 3dd45a78cb9d6629 |  |
| g_241f677bd4b8f8a4-001 | result_avatar.glb | 0.1 | 4796317eb406df52 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| g_241f677bd4b8f8a4-001 | result_avatar_from_project.avt | 32.7 | ec28f6bbde4ce457 | H 175.0, chest 100.0, waist 85.0, low hip 98.0 |
| g_241f677bd4b8f8a4-001 | result_avatar_packed.glb | 29.1 | d8092f8b7c2cac11 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| g_241f677bd4b8f8a4-001 | result_project.zprj | 34.5 | e997a031d42cf1a1 |  |
| g_241f677bd4b8f8a4-001 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| g_4e1a14ccadb2fd2f-001 | clo_payload.patched.avt | 32.4 | 914ef07079165110 | H 175.0, chest 100.0, waist 85.0, low hip 98.0 |
| g_4e1a14ccadb2fd2f-001 | result_avatar.bin | 12.8 | 3dd45a78cb9d6629 |  |
| g_4e1a14ccadb2fd2f-001 | result_avatar.glb | 0.1 | c767b1a95622e4d2 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| g_4e1a14ccadb2fd2f-001 | result_avatar_from_project.avt | 32.7 | 468df45bb14063f9 | H 175.0, chest 100.0, waist 85.0, low hip 98.0 |
| g_4e1a14ccadb2fd2f-001 | result_avatar_packed.glb | 29.1 | 6813153abb911159 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| g_4e1a14ccadb2fd2f-001 | result_project.zprj | 34.5 | c0da17b9fcc570ce |  |
| g_4e1a14ccadb2fd2f-001 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| g_e5c37ff7a450d060-001 | result_avatar.glb | 37.8 | 95ed2766b614c004 | binary, 9 meshes, 606,659 verts, 1.4132 m |
| g_e5c37ff7a450d060-001 | result_avatar_from_project.avt | 32.8 | a9e128287cfc0859 | H 137.0, chest 81.5, waist 62.0, low hip 83.5 |
| g_e5c37ff7a450d060-001 | result_project.zprj | 34.6 | c9b57672a0fd3fc2 |  |
| u_001-007 | _inspect\base-1.zip | 32.1 | 7eed0b58e32d56d6 |  |
| u_001-007 | _inspect\first.dan | 31.5 | ecafd548ef2ad6f2 |  |
| u_001-007 | _inspect\result_avatar.dan | 31.5 | ae3f7ff1cc780657 |  |
| u_001-007 | _inspect\result_avatar.zip | 32.1 | a5642634bceaa607 |  |
| u_001-007 | _inspect\result_avatar_from_project.zip | 32.1 | 34bc0ffbf196d16f |  |
| u_001-007 | _inspect\result_project_0.dan | 31.5 | ae3f7ff1cc780657 |  |
| u_001-007 | result_avatar.avt | 32.4 | 6e2928019f1dc0df | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-007 | result_avatar_from_project.avt | 32.4 | 43986ce7eaab9d05 | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-007 | result_project.zprj | 33.9 | ae4343443e02513e |  |
| u_001-009 | result_avatar.avt | 32.4 | 47d5d155ae4d7713 | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-009 | result_avatar_from_project.avt | 32.4 | 14c7b9660ba1ae8d | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-009 | result_project.zprj | 33.9 | c2945196fc9be579 |  |
| u_001-010 | result_avatar.avt | 32.4 | d59c4457098ddeb2 | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-010 | result_avatar_from_project.avt | 32.4 | 4bad999e2a6d4e69 | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-010 | result_project.zprj | 33.9 | 6490cc81f0f87d16 |  |
| u_001-012 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-012 | result_avatar.avt | 32.4 | d98eeeeb2187fbcb | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-012 | result_avatar_from_project.avt | 32.4 | f07433c5fd562a78 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-012 | result_project.zprj | 33.9 | f6f4f4398ce74894 |  |
| u_001-013 | clo_payload.patched.avt | 32.4 | a357e62e75ee5d97 | H 178.5, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-013 | result_avatar.avt | 32.4 | 9de08abcf9627aca | H 178.5, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-013 | result_avatar_from_project.avt | 32.4 | 6109ca2e7e755363 | H 178.5, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-013 | result_project.zprj | 33.9 | f675e509a38ee9b3 |  |
| u_001-014 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-014 | result_avatar.avt | 32.4 | 56619acbf7864d34 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-014 | result_avatar_from_project.avt | 32.4 | 11b423e4f44ae1e6 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-014 | result_project.zprj | 33.9 | b17185b6d3311993 |  |
| u_001-016 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-016 | result_avatar.avt | 32.4 | fd60d6295ec5c34b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-016 | result_avatar_from_project.avt | 32.4 | 5f32cc872ad0ae04 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-016 | result_project.zprj | 33.9 | 0fe1d49dd1bac1eb |  |
| u_001-017 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-018 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-019 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-020 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-022 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-022 | result_avatar.avt | 2.8 | b1c0e84db8b57c6e |  |
| u_001-022 | result_avatar_from_project.avt | 32.7 | 13c9793ac60ec21f | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-022 | result_project.zprj | 34.5 | a643881a2c559cc1 |  |
| u_001-023 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-023 | result_avatar.avt | 2.8 | 293196c9c46cfab8 |  |
| u_001-023 | result_avatar_from_project.avt | 31.1 | 91488dfbceb34408 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-023 | result_project.zprj | 32.9 | 0402d77c136ee9a4 |  |
| u_001-024 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-024 | result_avatar_from_project.avt | 29.2 | 8406961d694c9304 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-024 | result_project.zprj | 31.0 | a250abb53e953aa8 |  |
| u_001-025 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-025 | result_avatar_from_project.avt | 32.7 | b373104c823a5495 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-025 | result_project.zprj | 34.5 | e34afefd772ba406 |  |
| u_001-026 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-026 | result_avatar_from_project.avt | 29.2 | 69e1201fd32db005 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-026 | result_project.zprj | 31.0 | c42c32f24db0ee3c |  |
| u_001-027 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-027 | result_avatar_from_project.avt | 32.7 | b475d29310819cac | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-027 | result_project.zprj | 34.5 | 255c0095c46d8b98 |  |
| u_001-028 | clo_payload.patched.avt | 59.2 | d719c7fd38d0193a | error BadZipFile: Bad magic number for central directory |
| u_001-028 | result_avatar_from_project.avt | 32.7 | df52fafd34a3abfe | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-028 | result_project.zprj | 34.5 | 4fc272ab8672de52 |  |
| u_001-029 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-029 | result_avatar_from_project.avt | 32.7 | 2075c3f818789843 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-029 | result_project.zprj | 34.5 | 863368ffc7013639 |  |
| u_001-030 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-030 | result_avatar_from_project.avt | 29.2 | c42bb061a2e74a46 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-030 | result_project.zprj | 31.0 | e03338f148fe98b9 |  |
| u_001-031 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-031 | result_avatar_from_project.avt | 32.7 | 305cb6045b8a1023 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-031 | result_project.zprj | 34.5 | 05a8f4231d9ffa94 |  |
| u_001-034 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-034 | result_avatar_from_project.avt | 32.7 | 83b3a34436399aeb | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-034 | result_project.zprj | 34.5 | bc76a6a219b2a5f2 |  |
| u_001-035 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-035 | result_avatar_from_project.avt | 30.0 | 58a1cd182a756336 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-035 | result_project.zprj | 31.9 | 0eb6323d0a19dc68 |  |
| u_001-036 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-036 | result_avatar_from_project.avt | 32.7 | 392ac6f015a24680 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-036 | result_project.zprj | 34.5 | 9526f5b39f642e65 |  |
| u_001-037 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-037 | result_avatar_from_project.avt | 32.7 | f53eccbcb71f8067 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-037 | result_project.zprj | 34.5 | f6ed021d8b5649f1 |  |
| u_001-038 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-038 | result_avatar_from_project.avt | 32.7 | 49d45ed77a97f451 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-038 | result_project.zprj | 34.5 | 48ce71b3e63f7533 |  |
| u_001-039 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-039 | result_avatar_from_project.avt | 32.7 | bb63f9a27405c84c | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-039 | result_project.zprj | 34.5 | bfc37ce77c600ff4 |  |
| u_001-040 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-040 | result_avatar_from_project.avt | 32.7 | dd016eb74aef3ce7 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-040 | result_project.zprj | 34.5 | 24fad9ed4232302c |  |
| u_001-041 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-041 | result_avatar_from_project.avt | 32.7 | 3fb5ed6bd82a4a1f | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-041 | result_project.zprj | 34.5 | 0172a2494f63a08a |  |
| u_001-042 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-042 | result_avatar_from_project.avt | 32.7 | a8556b5465844e65 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-042 | result_project.zprj | 34.5 | 74de683c6685b775 |  |
| u_001-043 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-043 | result_avatar_from_project.avt | 30.0 | c22c5aa722d71f08 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-043 | result_project.zprj | 31.9 | e2e1af152c0ecec9 |  |
| u_001-044 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-044 | result_avatar_from_project.avt | 32.7 | 913ea1463a381533 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-044 | result_project.zprj | 34.5 | ef69e0d37735d562 |  |
| u_001-045 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-045 | result_avatar_from_project.avt | 30.0 | 78c7f3048195d98d | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-045 | result_project.zprj | 31.9 | cee8d390a5c6303d |  |
| u_001-046 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-046 | result_avatar_from_project.avt | 32.7 | a8f87b96b287dd65 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-046 | result_project.zprj | 34.5 | f247a5fecf768da4 |  |
| u_001-047 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-047 | result_avatar_from_project.avt | 32.7 | e0a00df8f2cef6a4 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-047 | result_project.zprj | 34.5 | ab559b61cc79bf9a |  |
| u_001-048 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-048 | result_avatar_from_project.avt | 29.8 | 349eb39db5e6d827 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-048 | result_project.zprj | 31.5 | 78f2ccfe388c93f4 |  |
| u_001-049 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-049 | result_avatar_from_project.avt | 30.0 | efde80837a1e358c | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-049 | result_project.zprj | 31.9 | a7e5de48224088a0 |  |
| u_001-050 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-050 | result_avatar_from_project.avt | 32.7 | 735c0ea1ecd73ddf | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-050 | result_project.zprj | 34.5 | 2b668d518892bdcc |  |
| u_001-051 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-051 | result_avatar_from_project.avt | 32.7 | c71fbd33473e7250 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-051 | result_project.zprj | 34.5 | 8a52c95d48cd80db |  |
| u_001-052 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-052 | result_avatar_from_project.avt | 30.0 | 2bc12f742357d666 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-052 | result_project.zprj | 31.9 | 401a36373860394b |  |
| u_001-053 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-053 | result_avatar_from_project.avt | 29.8 | aaffd72d2de39a6b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-053 | result_project.zprj | 31.5 | 89a4c245eb4a096d |  |
| u_001-054 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-054 | result_avatar_from_project.avt | 32.7 | 38624db849e38c05 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-054 | result_project.zprj | 34.5 | 649294004ec2a0bb |  |
| u_001-055 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-055 | result_avatar_from_project.avt | 29.4 | 3ab134c9f5401cec | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-055 | result_project.zprj | 31.1 | a3be71266ca633a6 |  |
| u_001-056 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-056 | result_avatar_from_project.avt | 29.8 | 630a7abd6d0d3c02 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-056 | result_project.zprj | 31.6 | 6a8d30f6afaafb03 |  |
| u_001-057 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-057 | result_avatar_from_project.avt | 32.7 | 178c0f5910cbc4cf | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-057 | result_project.zprj | 34.5 | 2aa954654cf6d5c4 |  |
| u_001-058 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-058 | result_avatar_from_project.avt | 29.2 | f0aa2c2067ab3f8e | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-058 | result_project.zprj | 31.0 | 04473727a2d18a65 |  |
| u_001-059 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-059 | result_avatar_from_project.avt | 32.7 | f623d38dd69b63c1 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-059 | result_project.zprj | 34.5 | 952358b9f42898ae |  |
| u_001-060 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-060 | result_avatar_from_project.avt | 32.7 | fa23ee6e92a08ff7 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-060 | result_project.zprj | 34.5 | 08472a507d31fc99 |  |
| u_001-061 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-061 | result_avatar_from_project.avt | 32.7 | e4ffc060b1dd038b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-061 | result_project.zprj | 34.5 | 627df18219f0fdec |  |
| u_001-062 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-062 | result_avatar.bin | 12.8 | 3dd45a78cb9d6629 |  |
| u_001-062 | result_avatar.glb | 0.1 | f0922f13549582c0 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-062 | result_avatar_from_project.avt | 32.7 | 40187f29ef93ba96 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-062 | result_project.zprj | 34.5 | 1ee67ba276b7fca2 |  |
| u_001-062 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-063 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-063 | result_avatar.bin | 12.8 | 3dd45a78cb9d6629 |  |
| u_001-063 | result_avatar.glb | 0.1 | 90c8ff8ed220ba5f | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-063 | result_avatar_from_project.avt | 32.7 | dcd6ef371701c02f | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-063 | result_project.zprj | 34.5 | 1df16e5bcc6a6b8c |  |
| u_001-063 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-064 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-064 | result_avatar.bin | 12.8 | 3dd45a78cb9d6629 |  |
| u_001-064 | result_avatar.glb | 0.1 | af5aec89ba25964b | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-064 | result_avatar_from_project.avt | 32.7 | ce337ab98096de47 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-064 | result_avatar_packed.glb | 29.1 | 5ddb4a9b0d810da9 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-064 | result_project.zprj | 34.5 | bd8addba995502c5 |  |
| u_001-064 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-065 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-065 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_001-065 | result_avatar.glb | 0.1 | 6e23f7c400fe8d57 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-065 | result_avatar_from_project.avt | 32.7 | 6301f7f89dd96184 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-065 | result_avatar_packed.glb | 29.1 | 7ecf7eda1d451a7f | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-065 | result_project.zprj | 34.5 | fcfd064c197c885d |  |
| u_001-065 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-066 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-066 | result_avatar_from_project.avt | 32.7 | 9e6dc19f828c7cde | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-066 | result_project.zprj | 67.0 | c9fef6f543b6d294 |  |
| u_001-067 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-067 | result_avatar_from_project.avt | 32.7 | 75b78cdd50c7768c | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-067 | result_project.zprj | 67.0 | ec694cb71fb1dbe2 |  |
| u_001-068 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-068 | result_avatar_from_project.avt | 32.7 | b2fe29f3baf2fd0b | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-068 | result_project.zprj | 67.0 | e9ffb3bea50ed729 |  |
| u_001-069 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-069 | result_avatar_from_project.avt | 32.7 | a89d705f42e665b3 | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-069 | result_project.zprj | 67.0 | a5fa404e43982dfb |  |
| u_001-070 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-070 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_001-070 | result_avatar.glb | 0.1 | e0c45aabf5e3274b | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-070 | result_avatar_from_project.avt | 32.7 | 5a6baa484fd09c3d | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-070 | result_avatar_packed.glb | 29.1 | 34a9150c9dfcb7db | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-070 | result_project.zprj | 34.5 | f3a7afd4effccaf6 |  |
| u_001-070 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-071 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-071 | result_avatar.bin | 38.4 | efae437d04937240 |  |
| u_001-071 | result_avatar.glb | 0.2 | 397cf3c5ad80cd5f | text-gltf, 27 meshes, 1,819,977 verts, 1.9213 m |
| u_001-071 | result_avatar_from_project.avt | 32.7 | 0c57932410e4c94d | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-071 | result_avatar_packed.glb | 87.3 | 07f246a6d79ac571 | binary, 27 meshes, 1,819,977 verts, 1.9213 m |
| u_001-071 | result_project.zprj | 99.5 | 8effec3a7cee2b27 |  |
| u_001-071 | 78 texture images (.png/.jpg) | 36.6 | - | avatar textures exported with the GLB |
| u_001-072 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-072 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_001-072 | result_avatar.glb | 0.1 | 12806922468071b3 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-072 | result_avatar_from_project.avt | 32.7 | 6832c82fbf59e852 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-072 | result_avatar_packed.glb | 29.1 | 9110a59e118d99cc | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-072 | result_project.zprj | 34.5 | de2c365ce28510b3 |  |
| u_001-072 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-073 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-073 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_001-073 | result_avatar.glb | 0.1 | 85614a671af4f069 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-073 | result_avatar_from_project.avt | 32.7 | bb52ac2295cda056 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-073 | result_avatar_packed.glb | 29.1 | 8689401c37d2a562 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-073 | result_project.zprj | 34.5 | a5a7190ceacebdef |  |
| u_001-073 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-074 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-074 | result_avatar_from_project.avt | 32.7 | b24a814bebeda7cf | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-074 | result_project.zprj | 67.0 | c43f779aee49808c |  |
| u_001-075 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-075 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_001-075 | result_avatar.glb | 0.1 | 6e23f7c400fe8d57 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-075 | result_avatar_from_project.avt | 32.7 | 312ae2130e2f8571 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-075 | result_avatar_packed.glb | 29.1 | 7ecf7eda1d451a7f | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-075 | result_project.zprj | 34.5 | 44901dd598e3f926 |  |
| u_001-075 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-076 | clo_payload.patched.avt | 32.4 | 4616686f2ae60257 | H 165.0, chest 92.0, waist 76.0, low hip 98.0 |
| u_001-076 | result_avatar_from_project.avt | 32.7 | d6e034b3b4daa7b8 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-076 | result_project.zprj | 99.5 | 66838493ae428c56 |  |
| u_001-077 | clo_payload.patched.avt | 32.4 | 1145ef1a63471e61 | H 185.0, chest 108.0, waist 95.0, low hip 98.0 |
| u_001-077 | result_avatar_from_project.avt | 32.7 | 9e5a450fa66c157c | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-077 | result_project.zprj | 67.0 | 3cfa0c7661b228de |  |
| u_001-078 | clo_payload.patched.avt | 32.4 | 9fff9260a2c9d300 | H 172.0, chest 96.0, waist 80.0, low hip 98.0 |
| u_001-078 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_001-078 | result_avatar.glb | 0.1 | 361c54f2a8311ccd | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-078 | result_avatar_from_project.avt | 32.7 | bb7f1b69119183e6 | H 172.0, chest 96.0, waist 80.0, low hip 98.0 |
| u_001-078 | result_avatar_packed.glb | 29.1 | 383b3903fd5cd79b | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-078 | result_project.zprj | 34.5 | e56a018ad4c4a696 |  |
| u_001-078 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_001-079 | clo_payload.patched.avt | 32.4 | 557b56506be7b874 | H 190.0, chest 112.0, waist 99.0, low hip 98.0 |
| u_001-079 | result_avatar_from_project.avt | 32.7 | f1eafb52ffa7b548 | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-079 | result_project.zprj | 67.0 | acab180ee6fc4c96 |  |
| u_001-080 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-080 | result_avatar_from_project.avt | 32.7 | 7d4c8ed34e663137 | H 187.96, chest 96.52, waist 82.55, low hip 95.25 |
| u_001-080 | result_project.zprj | 67.0 | ca8efabc2b26fef3 |  |
| u_001-081 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-081 | result_avatar.glb | 37.8 | 2abe8cb91c9b2a4b | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-081 | result_avatar_from_project.avt | 32.7 | a15db93ecea0060f | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-081 | result_project.zprj | 34.5 | 303812e3e3603836 |  |
| u_001-084 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-085 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-086 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-087 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-090 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-091 | clo_payload.patched.avt | 32.4 | e7179827e3b6be3b | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-091 | result_avatar.glb | 37.8 | f476e06fa7ac2ccb | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_001-091 | result_avatar_from_project.avt | 32.7 | f9d5c1f4652a0ab8 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-091 | result_project.zprj | 34.5 | 794e28a4cf9e505e |  |
| u_001-092 | result_avatar.glb | 37.8 | 111f62e61cd0cc45 | binary, 9 meshes, 606,659 verts, 1.8271 m |
| u_001-092 | result_avatar_from_project.avt | 32.7 | d543edbd5b71f385 | H 178.5, chest 100.0, waist 85.0, low hip 98.0 |
| u_001-092 | result_project.zprj | 34.5 | 67c07aaf56a773a1 |  |
| u_002-001 | clo_payload.patched.avt | 32.4 | 91969482af06a51e | H 182.0, chest 105.0, waist 90.0, low hip 102.0 |
| u_002-001 | result_avatar_from_project.avt | 32.7 | e9c05cbf718274ce | H 182.0, chest 105.0, waist 90.0, low hip 102.0 |
| u_002-001 | result_project.zprj | 34.5 | d915db365dc37e45 |  |
| u_002-002 | clo_payload.patched.avt | 32.4 | 91969482af06a51e | H 182.0, chest 105.0, waist 90.0, low hip 102.0 |
| u_002-002 | result_avatar_from_project.avt | 32.7 | 11f4d10f17ead583 | H 182.0, chest 105.0, waist 90.0, low hip 102.0 |
| u_002-002 | result_project.zprj | 34.5 | b9f095a950fbb690 |  |
| u_002-003 | clo_payload.patched.avt | 32.4 | 91969482af06a51e | H 182.0, chest 105.0, waist 90.0, low hip 102.0 |
| u_002-003 | result_avatar_from_project.avt | 32.7 | f323a411e06cde2c | H 182.0, chest 105.0, waist 90.0, low hip 102.0 |
| u_002-003 | result_project.zprj | 34.5 | d5cb790d6809e6a5 |  |
| u_003-004 | result_avatar.glb | 37.8 | 24bf7aea735fdf26 | binary, 9 meshes, 606,659 verts, 1.7921 m |
| u_003-004 | result_avatar_from_project.avt | 32.7 | b84ce5fd52593cdb | H 175.0, chest 96.0, waist 82.0, low hip 96.0 |
| u_003-004 | result_project.zprj | 34.5 | ec2fa4681bfed4e5 |  |
| u_003-005 | result_avatar.glb | 37.8 | 3cac45ba39480a26 | binary, 9 meshes, 606,659 verts, 1.7921 m |
| u_003-005 | result_avatar_from_project.avt | 32.7 | 64d5a3c80eb2e0c1 | H 175.0, chest 96.0, waist 82.0, low hip 96.0 |
| u_003-005 | result_project.zprj | 34.6 | 46b9ed72ba3cc816 |  |
| u_011-001 | clo_payload.patched.avt | 32.4 | a618065f35dcbc66 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-001 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_011-001 | result_avatar.glb | 0.1 | 6e23f7c400fe8d57 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_011-001 | result_avatar_from_project.avt | 32.7 | 0fab85e93751121b | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-001 | result_avatar_packed.glb | 29.1 | 7ecf7eda1d451a7f | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_011-001 | result_project.zprj | 34.5 | 168a1e48bf6f6a18 |  |
| u_011-001 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_011-002 | clo_payload.patched.avt | 32.4 | a618065f35dcbc66 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-002 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_011-002 | result_avatar.glb | 0.1 | 6e23f7c400fe8d57 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_011-002 | result_avatar_from_project.avt | 32.7 | 0aab2f8cf0b3da7c | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-002 | result_avatar_packed.glb | 29.1 | 7ecf7eda1d451a7f | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_011-002 | result_project.zprj | 34.5 | 0818fc2bbc3d519c |  |
| u_011-002 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_011-003 | clo_payload.patched.avt | 32.4 | a618065f35dcbc66 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-003 | result_avatar.bin | 38.4 | 705f43f6e00e1784 |  |
| u_011-003 | result_avatar.glb | 0.2 | cc59129a8fa4ea71 | text-gltf, 27 meshes, 1,819,977 verts, 1.9215 m |
| u_011-003 | result_avatar_from_project.avt | 32.7 | 27ceb30c8388de5b | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-003 | result_avatar_packed.glb | 87.3 | 05d69814e43fce1c | binary, 27 meshes, 1,819,977 verts, 1.9215 m |
| u_011-003 | result_project.zprj | 99.6 | 0d84c3136b93e7e6 |  |
| u_011-003 | 78 texture images (.png/.jpg) | 36.6 | - | avatar textures exported with the GLB |
| u_011-004 | clo_payload.patched.avt | 32.4 | a618065f35dcbc66 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-004 | result_avatar.bin | 38.4 | efae437d04937240 |  |
| u_011-004 | result_avatar.glb | 0.2 | dc1250e110cdbaf8 | text-gltf, 27 meshes, 1,819,977 verts, 1.9213 m |
| u_011-004 | result_avatar_from_project.avt | 32.7 | ff10cdecbb1fb369 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-004 | result_avatar_packed.glb | 87.3 | ab54a722a9cf6c3a | binary, 27 meshes, 1,819,977 verts, 1.9213 m |
| u_011-004 | result_project.zprj | 99.5 | 803ea240805d364e |  |
| u_011-004 | 78 texture images (.png/.jpg) | 36.6 | - | avatar textures exported with the GLB |
| u_011-005 | clo_payload.patched.avt | 32.4 | a618065f35dcbc66 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-005 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_011-005 | result_avatar.glb | 0.1 | f57412cd3065969c | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_011-005 | result_avatar_from_project.avt | 32.7 | dda9620f6ef81299 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-005 | result_avatar_packed.glb | 29.1 | f75af087963b5ef7 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_011-005 | result_project.zprj | 34.5 | 76e746a2cffd9e7a |  |
| u_011-005 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_011-006 | clo_payload.patched.avt | 32.4 | a618065f35dcbc66 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-006 | result_avatar.glb | 37.8 | 0be7e32a0e6eaa1d | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_011-006 | result_avatar_from_project.avt | 32.7 | 848dd172416a2574 | H 168.0, chest 92.0, waist 76.0, low hip 92.0 |
| u_011-006 | result_project.zprj | 34.5 | 75191cdf22d24909 |  |
| u_012-002 | clo_payload.patched.avt | 32.4 | 2064e24611e71c7f | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-002 | result_avatar.bin | 25.6 | 04813176d993a2b2 |  |
| u_012-002 | result_avatar.glb | 0.2 | 51fb7211f58d9a86 | text-gltf, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_012-002 | result_avatar_from_project.avt | 32.7 | 068e0e6e32bbcd2d | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-002 | result_avatar_packed.glb | 58.2 | f3b5e1f2113bb4e4 | binary, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_012-002 | result_project.zprj | 67.0 | b413c366435a19f3 |  |
| u_012-002 | 52 texture images (.png/.jpg) | 24.4 | - | avatar textures exported with the GLB |
| u_012-003 | clo_payload.patched.avt | 32.4 | 2064e24611e71c7f | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-003 | result_avatar.bin | 51.2 | c3644cba96efb879 |  |
| u_012-003 | result_avatar.glb | 0.3 | 950f74afcd8cd946 | text-gltf, 36 meshes, 2,426,636 verts, 1.9215 m |
| u_012-003 | result_avatar_from_project.avt | 32.7 | f9d5f2929a5390ea | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-003 | result_avatar_packed.glb | 116.4 | 38b59e09f58043a5 | binary, 36 meshes, 2,426,636 verts, 1.9215 m |
| u_012-003 | result_project.zprj | 132.1 | 2c9217d27dddb7bc |  |
| u_012-003 | 104 texture images (.png/.jpg) | 48.8 | - | avatar textures exported with the GLB |
| u_012-004 | clo_payload.patched.avt | 32.4 | 2064e24611e71c7f | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-004 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_012-004 | result_avatar.glb | 0.1 | e47c742233374b58 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_012-004 | result_avatar_from_project.avt | 32.7 | fa1bc2aa669cff2e | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-004 | result_avatar_packed.glb | 29.1 | 818111a89e5a715d | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_012-004 | result_project.zprj | 34.5 | 66fda3d70c02dcdf |  |
| u_012-004 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_012-005 | clo_payload.patched.avt | 32.4 | 2064e24611e71c7f | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-005 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_012-005 | result_avatar.glb | 0.1 | 60c6c9fd2fbbc54e | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_012-005 | result_avatar_from_project.avt | 32.7 | 496f083fee3939c3 | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-005 | result_avatar_packed.glb | 29.1 | 0eb4fdf7c6358bb7 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_012-005 | result_project.zprj | 34.5 | 2b9533b46db1ecba |  |
| u_012-005 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_012-006 | clo_payload.patched.avt | 32.4 | 2064e24611e71c7f | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-006 | result_avatar.glb | 37.8 | 854c7f09db5b3edb | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_012-006 | result_avatar_from_project.avt | 32.7 | ae67405ec9aa2e65 | H 175.0, chest 98.0, waist 82.0, low hip 96.0 |
| u_012-006 | result_project.zprj | 34.5 | bc2a8f1d1485f0e9 |  |
| u_013-002 | clo_payload.patched.avt | 32.4 | b62eb5c828feeca7 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-002 | result_avatar.bin | 25.6 | 04813176d993a2b2 |  |
| u_013-002 | result_avatar.glb | 0.2 | 36f5050dd8415823 | text-gltf, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_013-002 | result_avatar_from_project.avt | 32.7 | 35cca7846e6df8da | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-002 | result_avatar_packed.glb | 58.2 | 437c9e4bf1bf6550 | binary, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_013-002 | result_project.zprj | 67.0 | 675f1aeb1d2aab47 |  |
| u_013-002 | 52 texture images (.png/.jpg) | 24.4 | - | avatar textures exported with the GLB |
| u_013-003 | clo_payload.patched.avt | 32.4 | b62eb5c828feeca7 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-003 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_013-003 | result_avatar.glb | 0.1 | c967e9dbb085b59a | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-003 | result_avatar_from_project.avt | 32.7 | 0844b059d6be1da6 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-003 | result_avatar_packed.glb | 29.1 | 07883060a378c252 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-003 | result_project.zprj | 34.5 | 0682f21962134284 |  |
| u_013-003 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_013-004 | clo_payload.patched.avt | 32.4 | b62eb5c828feeca7 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-004 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_013-004 | result_avatar.glb | 0.1 | a2bff6d1d8aab57c | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-004 | result_avatar_from_project.avt | 32.7 | f91ba969cb018ae9 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-004 | result_avatar_packed.glb | 29.1 | 3cfb257c8000d23a | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-004 | result_project.zprj | 34.5 | 1a338d497b80b70d |  |
| u_013-004 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_013-005 | clo_payload.patched.avt | 32.4 | b62eb5c828feeca7 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-005 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_013-005 | result_avatar.glb | 0.1 | 6d7dd7fae3ffb30f | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-005 | result_avatar_from_project.avt | 32.7 | 06468719169d4c6e | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-005 | result_avatar_packed.glb | 29.1 | 2f4ef27ec4df295f | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-005 | result_project.zprj | 34.5 | e4a13dd1b85ffe04 |  |
| u_013-005 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_013-006 | clo_payload.patched.avt | 32.4 | b62eb5c828feeca7 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-006 | result_avatar.glb | 37.8 | befb4f12cd08cbf4 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-006 | result_avatar_from_project.avt | 32.7 | 3a3aceb769ef1a47 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-006 | result_project.zprj | 34.5 | 43dcfea38d2a266a |  |
| u_013-007 | clo_payload.patched.avt | 32.4 | b62eb5c828feeca7 | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-007 | result_avatar.glb | 37.8 | c9f2cc6389fb3380 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_013-007 | result_avatar_from_project.avt | 32.7 | c9c59cf1384c720c | H 181.0, chest 106.0, waist 92.0, low hip 104.0 |
| u_013-007 | result_project.zprj | 34.5 | 2ecd26260fd12432 |  |
| u_014-002 | clo_payload.patched.avt | 32.4 | ee325d08734b04c5 | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-002 | result_avatar.bin | 25.6 | 04813176d993a2b2 |  |
| u_014-002 | result_avatar.glb | 0.2 | 9c871c267e94e3ec | text-gltf, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_014-002 | result_avatar_from_project.avt | 32.7 | beeef78a50bf090b | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-002 | result_avatar_packed.glb | 58.2 | 6bc60eeab7291c36 | binary, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_014-002 | result_project.zprj | 67.0 | da48e14c7cc77cf2 |  |
| u_014-002 | 52 texture images (.png/.jpg) | 24.4 | - | avatar textures exported with the GLB |
| u_014-003 | clo_payload.patched.avt | 32.4 | ee325d08734b04c5 | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-003 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_014-003 | result_avatar.glb | 0.1 | 2abbf142f7e3cd5b | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_014-003 | result_avatar_from_project.avt | 32.7 | c80b3bbd3c81d9dc | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-003 | result_avatar_packed.glb | 29.1 | 67e1bf8922da39f3 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_014-003 | result_project.zprj | 34.5 | 90efdb8b01d5f6ae |  |
| u_014-003 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_014-004 | clo_payload.patched.avt | 32.4 | ee325d08734b04c5 | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-004 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_014-004 | result_avatar.glb | 0.1 | ab2ed5a22747b1aa | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_014-004 | result_avatar_from_project.avt | 32.7 | d83feac3c7968473 | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-004 | result_avatar_packed.glb | 29.1 | c42ef7d9d1ddc552 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_014-004 | result_project.zprj | 34.5 | 2c17a2102cfd110c |  |
| u_014-004 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_014-005 | clo_payload.patched.avt | 32.4 | ee325d08734b04c5 | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-005 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_014-005 | result_avatar.glb | 0.1 | 8c74b59bb9bfb59a | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_014-005 | result_avatar_from_project.avt | 32.7 | 7eaea748da8d03fd | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-005 | result_avatar_packed.glb | 29.1 | 4177d721225f61db | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_014-005 | result_project.zprj | 34.5 | 126d050141925e26 |  |
| u_014-005 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_014-006 | clo_payload.patched.avt | 32.4 | ee325d08734b04c5 | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-006 | result_avatar.glb | 37.8 | 3570d05c2b42f027 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_014-006 | result_avatar_from_project.avt | 32.7 | 02d1a0f206bf397b | H 186.0, chest 100.0, waist 84.0, low hip 98.0 |
| u_014-006 | result_project.zprj | 34.5 | 215efadb20c72814 |  |
| u_015-002 | clo_payload.patched.avt | 32.4 | b6f0dc19837455c3 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-002 | result_avatar.bin | 25.6 | 04813176d993a2b2 |  |
| u_015-002 | result_avatar.glb | 0.2 | 686decbf0b2f505f | text-gltf, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_015-002 | result_avatar_from_project.avt | 32.7 | b684d459916272ac | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-002 | result_avatar_packed.glb | 58.2 | 867fb6e63a01da09 | binary, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_015-002 | result_project.zprj | 67.0 | a9975ba3d9db7135 |  |
| u_015-002 | 52 texture images (.png/.jpg) | 24.4 | - | avatar textures exported with the GLB |
| u_015-003 | clo_payload.patched.avt | 32.4 | b6f0dc19837455c3 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-003 | result_avatar.bin | 25.6 | 04813176d993a2b2 |  |
| u_015-003 | result_avatar.glb | 0.2 | c71a9a9f2c63fb91 | text-gltf, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_015-003 | result_avatar_from_project.avt | 32.7 | a7fb03aaa840ad70 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-003 | result_avatar_packed.glb | 58.2 | de5acdb8134e52a1 | binary, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_015-003 | result_project.zprj | 67.0 | b10584a2bfe8d472 |  |
| u_015-003 | 52 texture images (.png/.jpg) | 24.4 | - | avatar textures exported with the GLB |
| u_015-004 | clo_payload.patched.avt | 32.4 | b6f0dc19837455c3 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-004 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_015-004 | result_avatar.glb | 0.1 | 3a15ba049db8e391 | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_015-004 | result_avatar_from_project.avt | 32.7 | 07694fac19a0eaa8 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-004 | result_avatar_packed.glb | 29.1 | bbe84aa745b84ac9 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_015-004 | result_project.zprj | 34.5 | 27504dd4983d618f |  |
| u_015-004 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_015-005 | clo_payload.patched.avt | 32.4 | b6f0dc19837455c3 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-005 | result_avatar.bin | 12.8 | 6a8aabbfee6c2c25 |  |
| u_015-005 | result_avatar.glb | 0.1 | 8c3f4f778258410d | text-gltf, 9 meshes, 606,659 verts, 1.9213 m |
| u_015-005 | result_avatar_from_project.avt | 32.7 | 1b825c86c0037dfc | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-005 | result_avatar_packed.glb | 29.1 | 90b798f6f8bd2e52 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_015-005 | result_project.zprj | 34.5 | ba8eb198124ddf1c |  |
| u_015-005 | 26 texture images (.png/.jpg) | 12.2 | - | avatar textures exported with the GLB |
| u_015-006 | clo_payload.patched.avt | 32.4 | b6f0dc19837455c3 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-006 | result_avatar.glb | 37.8 | 9d91d7985f0b57c0 | binary, 9 meshes, 606,659 verts, 1.9213 m |
| u_015-006 | result_avatar_from_project.avt | 32.7 | a8b20d49f3bd57c3 | H 186.0, chest 112.0, waist 98.0, low hip 108.0 |
| u_015-006 | result_project.zprj | 34.5 | 2cc362942125d0fa |  |
| u_dcabc592e2bb18e7-008 | clo_payload.patched.avt | 32.4 | ff439154b2c328b8 | H 179.5, chest 96.0, waist 82.0, low hip 107.5 |
| u_dcabc592e2bb18e7-008 | result_avatar.glb | 62.8 | 943c27ecd907d66b | binary, 18 meshes, 1,213,318 verts, 1.9213 m |
| u_dcabc592e2bb18e7-008 | result_avatar_from_project.avt | 32.7 | 552a5834e126484d | H 179.5, chest 96.0, waist 82.0, low hip 107.5 |
| u_dcabc592e2bb18e7-008 | result_project.zprj | 67.0 | 3a573ac015b6353e |  |
| u_dcabc592e2bb18e7-009 | result_avatar.glb | 37.8 | dc9557788a655b5e | binary, 9 meshes, 606,659 verts, 1.8371 m |
| u_dcabc592e2bb18e7-009 | result_avatar_from_project.avt | 32.7 | 09325c40283b9a96 | H 179.5, chest 96.0, waist 82.0, low hip 107.5 |
| u_dcabc592e2bb18e7-009 | result_project.zprj | 34.6 | 77e736752323d2d0 |  |
