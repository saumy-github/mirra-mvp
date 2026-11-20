# Plugin command specification (lane AR)

*Status: design only, nothing applied to `RestPlugin_windows.cpp`. Date: 2026-10-29. Static findings only; no CLO or plugin contact.*

Target file: `clo_workspace/windows/RestPlugin_windows.cpp` (read-only for this lane). Finding references are `F<nn>` = `rev-eng/findings/<nn>_*.md`. Tags: **[V]** verified by disassembly, **[I]** inferred, **[L]** needs a live test (experiment `eNN` in `rev-eng/experiments/`). Nothing here has been run live.

## 0. Existing plugin pattern (what to follow)

Read from the plugin source:

- **Async command**: the HTTP handler fills an `APICommand` (`type`, `param1..6`, `floatParam1..6`, `boolParam1/2`, `stringMapParam1`), pushes it onto `g_commandQueue` under `g_queueMutex`, and replies at once with `{"success":true,"message":"... queued","queue_size":N}`. The client then calls `POST /execute` (posts `WM_MIRRA_DRAIN_QUEUE` to `g_cloMainWnd`, so `ProcessCommandQueue()` runs on CLO's main thread) and polls `GET /status` until `queue_size==0 && !queue_processing`, reading `last_results[]` (`{type,success,message}`). `ProcessCommandQueue` has a re-entrancy guard (`g_queueProcessing`), swaps the queue into a local batch, and appends one `CommandResult` per async command. Python side: `avatar_runtime/client.py` (`_post`, `_get`, `wait_for_queue`, default `timeout=30`).
- **Sync read**: `dispatchSyncRead(type, param3, param4)` pushes a command with `isSync=true` and a `std::promise<json>`, waits **3 s** on the future, and returns `{"success":false,"error":"timeout"}` otherwise. Branch in `ProcessCommandQueue` sets `syncResult`. `GET /avatars/state` -> `"read-avatar-state"` is the model. Note a sync read still needs a drain: the timer/`/execute` path services it.
- Branch skeleton inside `ProcessCommandQueue` (one `else if (cmd.type == "...")` per command, wrapped in try/catch that sets `asyncResult.success=false` / `syncResult={"success":false,"error":...}`), plus `TraceLog("BEGIN ...")/("END ...")`. Guards: `CLOGuard::fabricReady`, `patternIndexValid`, `fileExists`.
- Existing weaknesses to fix in passing (all new commands should avoid them): (a) `g_lastResults` carries no command id, so a client cannot tell which result is its own; (b) `/clear-avatars` deletes only indices `0..g_avatarsLoaded-1` from a plugin-side tally instead of asking CLO; (c) async results contain only `message` strings, not structured data.

### 0.1 Required plumbing change: request ids and structured results

Add to `APICommand`: `std::string requestId;` and `json extra;` (typed payload from the HTTP body). Add to `CommandResult`: `std::string requestId; json data;`. Every new async route returns `request_id` (server-generated, monotonic) in its queued reply; `/status` `last_results[]` entries gain `request_id` and `data`. New helper `GET /result/<request_id>` returns that entry (keep the last 64). This is the only structural change; each command below then reports its structured output in `data`.

A second helper `dispatchSyncRead` variant `dispatchSyncReadJson(type, json args, seconds)` is needed because several reads take arguments beyond two ints and some (e.g. grading switch) need more than 3 s (see section on timeouts). Default 3 s stays for pure reads; mutating sync-style commands should be async (queued) and return via `/result`.

### 0.2 Common rules for every new command

1. **Main thread only.** All CLO API calls (Utility, Pattern, Fabric, Import, Export) run inside `ProcessCommandQueue` on CLO's UI thread. F21: fabric setters call UI-object virtuals directly and refresh synchronously, so they must be on the GUI thread; no sleeps needed between a set and a following read/export on the same thread.
2. **Preflight gate** (section 6): mutating commands `import-avatar*`, `clear-avatars`, `simulate`, and everything below that mutates return `409 {"success":false,"error":"abi_mismatch"}` when `host_matches_sdk` is false. Pure reads return `"abi_unverified":true` instead of refusing.
3. **Modal-dialog hazard.** CLO's `DisplayMessageBox` blocks in a modal loop with no timeout and no headless guard (F29). While one is up the main thread is stuck inside the command, `g_queueProcessing` stays true, and the HTTP threads still answer. Every route below lists the boxes it can raise. Client rule: if `/status` shows `queue_processing:true` for longer than the route's timeout, treat it as "modal dialog", run the watchdog (e07, F29 dismiss list), do not queue anything else.
4. **Return-value distrust table** (the real failure conventions, used in the error mapping below):

| API | Real behaviour | Source |
|---|---|---|
| `ImportFile(path)` slot 2 | returns true with no document; otherwise true except GUI-mode `App+0x50` method 74 false. Not a success signal. Slot 1 (options overload) only accepts obj/fbx/gltf/glb, returns false and does nothing for avs/avt. | F36 [V] |
| `ImportDXF` | returns true even for empty/invalid file; only false if global `0x14A2ABF10` is null | F22, F26 [V] |
| `AddFabric` | returns (fabric count - 1) read after load; failed load returns previous last index or 0xFFFFFFFF on empty list | F38 [V] |
| `Simulate` | always true, blocks until N frames done, no cancel | F24, F29 [V] |
| `DeleteAvatar` | true only if at least one index valid | F24 |
| `ChangeGradingSizeInformation(group,idx)` | `group == count` passes bounds check and reads one past the end | F37 [V] |
| `GetFabricPBRMaterialBaseColor` | `(1,0,0,0)` on any failure | F16 sec. 12, F21 [V] |
| `GetAvatarMeasurements` | empty vector (plus `[Python] ...` log line) when no avatar or bad index | F16 sec. 8 [V] |
| `SetFabricPBRMaterialBaseColor` | false on bad fabric/colorway/face; no bounds check on face; Back may alias Front | F21 [V] |
| `ExportGLB/GLTF` | empty vector, no error, when nothing selected or only stale uids | F39 [V] |
| `GetFabricIndexForPattern` slot 51 | returns 0 on failure (ambiguous) | F21 |

   **Rule**: for every mutating call, the command reads state back (counts, indices, measurements, colour) and reports `verified:true|false` separately from the raw API bool.

---

## 1. `/grading/info` and `/grading/change-size`

Basis: F37 (lane AF). All grading virtuals live on `PATTERN_API`. Implemented slots: group/size getters, `ChangeGradingSizeInformation` (146 by index, 147 by name), `GetGradingSizeListFromRuleTable` (142 index, 143 name), `GetGradingPairedAvatar`, quantity mix get/set. Creating/editing groups (`AddGradingSize*`, `ImportGradeRuleToSizeGroup`, pairing setters) are thunks: never call them. **Do not repair or extend `/avatar/grading-size`** (it calls `AddGradingSizeGroup`, an unimplemented thunk); mark it deprecated and make it return `501`.

### 1.1 `GET /grading/info` (sync read, type `read-grading-info`)

- Request: no body. Optional query `?group=0`.
- SDK calls in order (all inside the main-thread branch, each in try/catch):
  1. `n = PATTERN_API->GetGradingSizeGroupCount()` (null manager -> 0).
  2. for `g` in `0..n-1`: `sizes = PATTERN_API->GetGradingSizeListFromRuleTable(g)` (empty vector if bad group); `cur = PATTERN_API->GetCurrentGradingSizeIndex(g)` (verify exact signature in `PatternAPIInterface.h` of the SDK folder named by `MIRRA_PLUGIN_SDK_FOLDER`; F37 lists the getter without arguments needing a decode: if it takes no group argument, call once and report as `current_size_index`); `paired[i] = PATTERN_API->GetGradingPairedAvatar(i)` for each size index `i`.
- Response:
```json
{"success":true,"group_count":1,
 "groups":[{"group":0,"sizes":["XS","S","M","L"],"current_size_index":2,
            "paired_avatars":["","","",""],"has_pairing":false}],
 "notes":[]}
```
- Errors: `group_count==0` -> `success:true`, `groups:[]`, note `"no grading group (template needs authoring or graded DXF import)"` (F37: no group exists unless authored in the GUI or imported via DXF). Timeout from `dispatchSyncRead` -> `{"success":false,"error":"timeout"}` (3 s is ample; these are getters).
- Main thread: required (manager access).
- Verified/inferred: getters implemented and null-safe [V, F37]; exact `GetCurrentGradingSizeIndex` argument list and `GetGradingPairedAvatar` return type [I, check header]; decode of paired-avatar emptiness semantic [I]. **Live test: e04** (currently blocked at exit 3 solely because these routes do not exist; implementing this route unblocks e04 steps 1-3).

### 1.2 `POST /grading/change-size` (async, type `grading-change-size`)

- Request:
```json
{"group":0,"size_index":2,"size_name":"M","require_no_pairing":true,"simulate_after":0}
```
  Exactly one of `size_index` / `size_name` required. `size_name` is resolved to an index plugin-side from `GetGradingSizeListFromRuleTable(group)` (do not use the name overload slot 147 for matching: it compares wide strings exactly and a miss returns false, F37). `simulate_after` = frames, 0 = none.
- SDK calls in order:
  1. Guard: `n = GetGradingSizeGroupCount()`; require `0 <= group < n` **strictly** (F37 [V]: `group == n` passes CLO's own check and reads one past the end). Else error `group_out_of_range`, no CLO call.
  2. `sizes = GetGradingSizeListFromRuleTable(group)`; resolve `size_index`; require `0 <= size_index < sizes.size()`.
  3. `paired = GetGradingPairedAvatar(size_index)`; if non-empty and `require_no_pairing` -> error `size_has_paired_avatar` (F37 [I]: a switch will probably swap the scene avatar and overwrite Mirra's measured avatar). Also report for every size in `data.pairing_report`.
  4. `ok = ChangeGradingSizeInformation(group, size_index)` (index overload, slot 146). Worker pushes an undo step "Change Grading Size".
  5. Read back: `now = GetCurrentGradingSizeIndex(...)`; `verified = ok && now == size_index`.
  6. If `simulate_after>0`: `Simulate(simulate_after)` (F37 [I]: no `Simulate` in the wrapper chain, patterns and mesh rebuilt at the new size, so a Simulate may be needed; this is exactly the e04 open question). Do not default it on.
- Response `data`: `{"group":0,"requested_index":2,"api_returned":true,"current_index":2,"verified":true,"sizes":[...],"paired_avatar_after":""}`.
- Error mapping: `group_out_of_range`, `size_name_not_found`, `size_index_out_of_range`, `size_has_paired_avatar`, `api_false` (the bool was false: bad group/index, null manager), `readback_mismatch` (bool true but index differs).
- Timeout: queue-level 30 s (client) when `simulate_after==0`; if simulate is requested use the simulate formula in section 7.4. The inner workers `0x145609EA0`/`0x14578A150` were not decoded, so assume a pattern rebuild of a few seconds [I].
- Modal hazards: the undo-push routine contains the "If you directly edit a parametric pattern..." box (reachability from a switch unestablished, low risk for DXF-derived non-parametric patterns, F37); possible "Added avatars for graded size will be replaced..." box if graded-size avatars exist (F29). Watchdog must stay on.
- Verified/inferred: all SDK semantics [V, F37] except post-switch re-simulation, avatar-swap, and group count after graded DXF import [L]. **Live test: e04** (all of its steps).

---

## 2. `/avatar/measurements` and `/avatar/properties`

### 2.1 `GET /avatar/measurements?index=0` (sync read, type `read-avatar-measurements`, param3 = index)

- SDK: `m = UTILITY_API->GetAvatarMeasurements(index)` (Utility slot 401, impl `0x5fd4180`, F16 sec. 8). Return shape per header: per-measure records `{measurementName, type, value, basicLength, surfaceLength}` plus a `unit` string; confirm exact C++ return type (map/vector/struct) from `UtilityAPIInterface.h` before writing the marshalling, since this lane could not open the SDK headers. Marshal every record into JSON without reinterpretation.
- Response:
```json
{"success":true,"index":0,"unit":"mm","unit_known":true,"count":57,
 "measurements":[{"name":"Bust Circumference","type":"Circumference","value":912.0,"basic":912.0,"surface":915.2,
                  "value_mm":912.0}]}
```
  Display-unit awareness: `unit` is the **current CLO display unit** (global): internal code 4 -> "mm", 3 -> "cm", 2 -> "in", anything else -> "" (F16 [V]). Convert to mm in the plugin: `mm`x1, `cm`x10, `in`x25.4; if `unit==""` set `unit_known:false`, do not add `value_mm`, and tell the client to refuse comparisons. Add `value_mm`, `basic_mm`, `surface_mm` for every record. Values are full circumference, not half-girth (F16, F15). Type mapping: 1,5 Tape; 2,4 Circumference; 3 Height; 9 Linear; 7,8 Default (F16 [V]). Kind 6 measures are skipped by CLO.
- Errors: empty vector -> `{"success":false,"error":"no_avatar_or_index_out_of_range"}` (CLO also writes `[Python] Please Load Avatar` or `[Python] GetAvatarMeasurements: avatar index <n> is out of range` to its log); validate `0 <= index < GetAvatarCount()` plugin-side first (SEH-protect: the existing source notes `GetAvatarProperties(0)` on an empty scene crashed CLO, so check count first, and note that the existing comment says count queries are crash-prone: wrap in `__try` helper per the plugin's SEH pattern). Timeout 3 s sync; if the list is large raise `dispatchSyncRead`'s wait to 5 s via the new JSON variant.
- Main thread: required.
- Use: after step 8 of avatar generation, verify against requested measurements (F16 recommendation; F27 mapping decides which CLO measure names correspond to Mirra's keys: client side, not plugin). The client should compare **after** converting both to mm and apply tolerance; mismatch or "unchanged across users" = failure (F42 notes the exported GLBs are identical across users, so this read-back is the only reliable proof).
- Verified: implementation semantics [V, F16]. Inferred: return type and field names [I]. **Live test: e01** (`--need-measurements` flag fails fast today for lack of this route), also e02 (read-back of patched `.avt`).

### 2.2 `GET /avatar/properties?index=0` and `POST /avatar/properties` (replaces `/avatar/set-properties`)

- `GET`: sync read of `UTILITY_API->GetAvatarProperties(index)` (map<string,string>) with the same index guard; response `{"index":0,"properties":{...}}`. Include `bSoftBodySimulation`, `bOnSubDivision`, `iDivisionLevel`, `fSoftBodyStiffness` booleans parsed into `flags: {"softbody":bool,"divide":bool}` (the `.dan` keys, F33). Property-key naming through `GetAvatarProperties` [I]: accept any of the key spellings; report raw map too.
- `POST` body: `{"index":0,"properties":{...},"preflight_clear":true}`. SDK order: `SetAvatarProperties(index, map)` only for keys other than the two option flags (F33 [V]: `SetAvatarProperties` cannot set them). Read-back via `GetAvatarProperties` and compare the keys that were set; report `verified_keys`/`mismatched_keys`. Per F-AP, mesh visibility is a property; consult F42 for any key.
- **Option-clearing pre-flight** (also available alone as `POST /avatar/clear-options`, type `avatar-clear-options`, body `{"index":0}` or `{"all":true}`), to prevent the "The Softbody Option will be turned off to adjust the avatar size. Do you want to proceed?" and matching "Divide Option" boxes (F29, F33):
  1. `props = GetAvatarProperties(i)`; `divide`, `softbody` flags from the `.dan` keys (or by byte offsets are not accessible: use the property map only).
  2. If `divide`: `SetAvatarSmooth(i, 0)` (slot impl `0x60420c0`, clears Divide).
  3. If `softbody`: `SetAvatarSoftBodyStiffness(i, 0.0f)` (impl `0x6042680`; **refuses while Divide is on, so step 2 first**, F33 [V]).
  4. Re-read `GetAvatarProperties(i)`; `verified = !divide && !softbody`.
  5. **Never** call `SetAvatarSmooth(i, 1..3)` or `SetAvatarSoftBodyStiffness(i, nonzero)` anywhere in the plugin (they turn the options ON, F33). Whitelist: the route must reject nonzero values of these two with `400 option_enable_forbidden`.
  6. Loop over **every** avatar loaded (F33: the check covers every avatar in the manager; each box asked at most once per call). With the section 7 single-avatar discipline this is one index.
- Errors: `no_avatar`, `index_out_of_range`, `divide_clear_failed`, `softbody_clear_failed` (Softbody refusal while Divide still on), `verify_failed`.
- Modal hazards: none intended; undo records "Soft Body Simulation"/"Divide Mesh" may be pushed by proceed branch only (not by these setters, F33 [I]).
- Verified: setter ordering and refusal rule [V, F33]; that `GetAvatarProperties` exposes those two keys with CLO-stock values (all 5 repo `.avt` have both 0, F33 [V]). Inferred: key names visible via the property map; whether the clears also trigger a mesh rebuild/redeform side effect [I]. **Live test: e01** (S1-S3 runs with Softbody/Divide deliberately on), e07 (watchdog catches the box if the pre-flight is skipped).

---

## 3. `/fabric/physical` and `/fabric/color`

### 3.1 `POST /fabric/physical` (async, type `fabric-physical`)

Basis: F38 (lane AJ). There is no API to set or get physics; the only route is loading a `.jfab`/`.zfab`. The existing `/set-fabric` ignores `preset` and always uses fabric index 0 with the built-in Default (very soft: stretch 100000, bending 100/600/150, shear 5000, density 0.0003), so every VTO drapes with Default.

- Request:
```json
{"jfab_path":"C:/.../presets/cotton_light.jfab","mode":"change","fabric_index":0,
 "pattern_indices":[0,1,2,3],"assign_option":1,"reapply_color":{"r":0.8,"g":0.1,"b":0.1},
 "reapply_texture":"C:/.../tex.png","simulate_after":0}
```
  `mode`: `"change"` (default) = `ChangeFabricWithJson`, `"add"` = `AddFabric` + assign. `pattern_indices` empty = all patterns.
- SDK order, mode `change`:
  1. Guards: `CLOGuard::fabricReady`; `fileExists(jfab_path)`; `n = FABRIC_API->GetFabricCount()` and require `0 <= fabric_index < n`.
  2. `before_name = FABRIC_API->GetFabricName(fabric_index)`.
  3. `ok = FABRIC_API->ChangeFabricWithJson(fabric_index, jfab_path)` (0-based; false for bad index or unreadable file; **overwrites the whole fabric, physics and appearance**, F38 [V]).
  4. Read back `after_name = GetFabricName(fabric_index)`; compare with the `qsFabricName` inside the jfab (parse the jfab with nlohmann json first; its `mapPhysical` keys: `fSuK fSvK fHK fBuK fBvK fBhK fBuLR fBvLR fBhLR fBucklingStiffness* fDensity fThickness fFriction fIDS enFabricType`). There is no physics getter: `verified_name` is the only API-side proof; full proof is project save + `zprj_probe.py` reading `listFabric/<i>/mapPhysical` (offline, see Live tests).
  5. Re-apply colour/texture (they were wiped): section 3.2 then `SetBaseTextureMapImageGivenFilePath`.
  6. Assign (see below), then optional `Simulate`.
- SDK order, mode `add`:
  1. `before = GetFabricCount()`; `idx = AddFabric(jfab_path)`.
  2. `after = GetFabricCount()`. **Success iff `after == before+1` and `idx == after-1`** (F38 [V]: `AddFabric` returns count-1 after load; failure returns the previous last index or 0xFFFFFFFF). Also check `GetFabricName(idx)` equals the jfab `qsFabricName`.
  3. Assign to patterns.
- Assignment (both modes): for each `p` in `pattern_indices`: `CLOGuard::patternIndexValid(p)`; `AssignFabricToPattern(fabric_idx, p, assign_option)` (impl `0x5f9bd50`; false for null fabric, out-of-range pattern, or bad option; option probably 1..3 [I]; default 1). Read-back: `GetFabricIndexForPattern(p, colorway=0)` (slot 50 form: returns -1 for invalid scene/colorway/pattern, 0 when fabric lookup fails; do not use slot 51 for verification because it returns 0 on failure, F21 [V]). `verified_assign = (readback == fabric_idx)`; when `fabric_idx == 0` the readback cannot distinguish failure, so additionally require the API bool true and report `ambiguous_zero:true`.
- Response `data`: `{"mode":"change","fabric_index":0,"api_returned":true,"name_before":"Default","name_after":"Cotton_light","verified_name":true,"assigned":[{"pattern":0,"api":true,"readback":0,"ok":true}],"colour_reapplied":true,"texture_reapplied":true}`.
- Error mapping: `file_not_found`, `jfab_parse_error`, `fabric_index_out_of_range`, `api_false`, `add_failed_count_unchanged`, `assign_failed`, `readback_mismatch`.
- Main thread: required (fabric setters use UI virtuals, F21). Note: do not dispatch via the timer-callback path; the plugin already moved fabric colour/texture to `PostMessage` for the reason that these calls pump the Win32 loop (see header comment, line ~196). Execute this inside the `WM_MIRRA_DRAIN_QUEUE` handler (the same path as every other queued command), not inside `QueueDrainTimer`.
- Timeout: 30 s without simulate. Modal hazard: loader not fully read (F38); a malformed jfab may raise a parse error box [I]. Pre-validate the jfab as JSON and require version/`mapPhysical`, `qsFabricName` before calling.
- Mark: SDK semantics [V, F38]; whether a spec-only jfab regenerates `_v2`/`LeftShear`, `ReplaceFabric` with a jfab, and units of density/stiffness [L, no experiment currently: add an `e09` (not written) that loads two jfabs, saves the project and diffs `mapPhysical`; closest existing is e03, which only proves Simulate determinism]. Recommendation: copy presets from CLO-exported fabrics, not from the JFAB spec example (F38).

### 3.2 `POST /fabric/color` (replaces `/set-fabric-color`) and `GET /fabric/color`

- `POST` body: `{"fabric_index":0,"colorway":0,"r":0.5,"g":0.2,"b":0.1,"faces":["front","back"],"bytes":false}`. If `bytes:true`, divide by 255 on the plugin side (no gamma; F21 [V]: input is 0..1 floats, 0..255 would be stored unscaled; there is **no sRGB conversion** in the setter path).
- SDK order (per face in `faces`, Front=0 then Back=1; Side=2 only if requested):
  1. `fabricReady`; `0 <= fabric_index < GetFabricCount()`.
  2. Use the **float overload** `SetFabricPBRMaterialBaseColor(colorway, fabric, face, r, g, b)` (slot 115; 116 uses the current colorway; string overloads 113/114 take colour-library names, not hex). Check the bool.
  3. Read back with `GetFabricPBRMaterialBaseColor(colorway, fabric, face)` (slot 117, 3-arg; 118 is the 2-arg form (fabric, face) using the current colorway). Returns `tuple<float,float,float,float>` in R,G,B,A order [I for order]. **Treat exactly `(1,0,0,0)` as failure** (alpha 0 never occurs for a real colour, F16 [V]). Then channel-wise compare with tolerance 1e-3 (the setter fixes alpha at 1.0).
  4. Order caveat: because face lookup has no bounds check and a missing Back material falls back to Front (F21 [V]), set Front, read Front, set Back, **re-read Front**; if Front changed, report `back_aliases_front:true` and treat Back as unsupported for that fabric.
- `GET /fabric/color?fabric=0&colorway=0&face=0` (sync read, `read-fabric-color`): returns the tuple, `valid:false` for `(1,0,0,0)`, and also `linear_vs_srgb_note` (the stored value is whatever was set; no gamma, F21).
- Response `data`: `{"fabric_index":0,"faces":[{"face":0,"api":true,"readback":[0.5,0.2,0.1,1.0],"ok":true},{"face":1,"api":true,"readback":[...],"ok":true}],"back_aliases_front":false}`.
- Error mapping: `fabric_index_out_of_range`, `api_false`, `readback_invalid` (sentinel), `readback_mismatch`, `back_aliases_front`.
- Texture companion: same route may accept `"texture":"path"` and uses overload 211 (face + failure string) rather than 212-214, which are void and silently no-op on a missing file, and where 213 with a bad fabric index silently textures the *currently selected* fabric (F21 [V]); `fileExists` and the index guard first. After texturing, reset base colour to white if true texture colours are wanted [I].
- Main thread: required. Modal hazards: none found.
- Mark: setter semantics [V, F21]; getter failure value [V, F16]; the RGBA order and 0..1 range of the getter [I]; Back-falls-back-to-Front [V] but its practical effect [L]. **Live test: e06** (currently uses GLB `baseColorFactor` as a proxy; this route replaces it and tests Front/Back).

---

## 4. `POST /export` (extended; replaces current behaviour, keeps backward compatibility)

Basis: F39 (lane AK), F25, F42. Current handler hard-codes `options.scale=0.001`, `bExportGarment=(g_patternsLoaded>0)`, `bExportAvatar=true`, no lists. The `g_patternsLoaded` tally is a plugin-side count; replace with a real `PATTERN_API->GetPatternCount()`.

- Request (all fields optional except `path`):
```json
{"path":"C:/.../garment.glb","format":"glb",
 "scale":0.001,"bExportGarment":true,"bExportAvatar":false,"bThin":true,
 "bIncludeHiddenObject":false,"bIncludeSceneProp":false,
 "patternList":[],"buttonList":[],"zipperList":[],"graphicList":[],
 "bSaveColorWays":false,"bSaveInZip":false,"bExportFabric":false,
 "min_bytes":1024}
```
- SDK order (async, type `export`):
  1. Preflight: `path` extension must match `format` (`.glb` for glb; gltf: a `.gltf` path, additional `.bin`/images alongside [I]); parent directory exists; delete a pre-existing target (so a stale file cannot be mistaken for success).
  2. Build `Marvelous::ImportExportOption options;` set `scale`, `bExportGarment`, `bExportAvatar`, `bThin` (+0x10, default true), `bIncludeHiddenObject` (+0x2B), `bIncludeSceneProp` (+0x58), `bSaveColorWays` (+0x43), `bSaveInZip` (+0x44), `bExportFabric` (+0x4C), `bSaveColorWaysSingleFile` (+0x4D), and the four lists (field names to be confirmed against the SDK's `ImportExportOption` struct; F39 confirms offsets, F14 confirms struct hash equality with the 336 header).
  3. **Stale-list guard**: if `patternList` non-empty, require each `0 <= i < GetPatternCount()` (list entries are checked against the internal pattern list but out-of-range/expired are silently skipped, and when *nothing* valid is selected the call returns an empty vector with no error, F39 [V]). `buttonList`/`graphicList` uids are inserted unchecked; `zipperList` unknown uids skipped. Reject (400) any list entry that fails the check so an empty export can never be mistaken for success.
  4. Content-sanity: if both `bExportGarment` and `bExportAvatar` are false -> 400 `nothing_selected`. If `bExportGarment` and `GetPatternCount()==0` -> 400 `no_patterns` (old behaviour silently dropped the garment).
  5. Call `EXPORT_API->ExportGLB(path, options)` or `ExportGLTF(path, options, false)`.
  6. Verify: returned vector non-empty; `GetFileAttributes(path)` exists and size >= `min_bytes`; record `files` list. `bSaveInZip` replaces the vector with one zip name (exact name [I]); multiple colorways without single-file produce one file per colorway (names [I]).
- Response `data`: `{"files":["..."],"bytes":12345678,"scale":0.001,"export_garment":true,"export_avatar":false,"thin":true,"pattern_count":4}`.
- Recipe (F39, F42): Simulate -> avatar once (`bExportAvatar=true,bExportGarment=false`) -> garment per try-on (`bExportGarment=true,bExportAvatar=false,bThin=true`, all lists empty, or `patternList` only to drop pieces) -> `glb_probe.py` check (no skins, ~1-2k vertices per piece, embedded images); garment world space equals avatar world space (Y-up, metres with scale 0.001; no recentring found) [I], so separate exports should align if the avatar is not moved in between. **Never recentre or translate between exports.**
- Frame/material notes for the consumer (not plugin work): `alphaMode` BLEND with alpha 1, `KHR_texture_transform` listed in `extensionsRequired` (viewer must support it or force the cloth opaque, F39 [V]).
- Error mapping: `bad_extension`, `nothing_selected`, `no_patterns`, `list_index_out_of_range`, `empty_vector` (CLO returned no files: nothing selected, or stale uids, or error), `file_missing_or_small`, `exception`.
- Timeout: 120 s (a combined 40 MB GLB is plausible, F25; export of a garment-only file is smaller). Main thread required. Modal hazards: the "less than 10GB" disk-space prompt (F29, appears on file-open worker; export path not shown to raise it [I]); mode 1 of slot 19 would open the GUI export dialog but the API path uses mode 0 [V, F39].
- Mark: selection flags/offsets [V, F39]; thick (`bThin=false`) output, `weldType`, colorway file naming, whether `bExportGarment`/`bExportAvatar` still gate list-selected objects (0x5cabcf0 unresolved) [L]. **Live test: e08** (currently only whole-scene variants testable; this route unblocks the component-list variants and the avatar-excluded export). Avatar-mesh-visibility effect on size: F42.

---

## 5. `POST /pattern/import-dxf` (hardened; replaces `/import-pattern`)

Basis: F22 (lane P), F32 (lane AA, corrects units), F26, F15.

- Request:
```json
{"path":"C:/.../block.dxf","append":true,"include_notches":true,"auto_scale":true,
 "scale":1.0,"expect_pieces":4,"validate":"strict","min_pieces":1}
```
- Pre-validation of the DXF text (plugin side, before any CLO call; read the file as text, ASCII/ANSI, reject > 50 MB). Reasons: `ImportDXF` returns true even for empty/invalid files and bad content can raise modal "This file is not a DXF format." / "Failed to load the DXF file." boxes (F22 [I]); non-AAMA DXFs trigger a convert-to-baselines message (F32 [V]).
  1. Group-code/value pair parse: alternate lines; every code line must be an integer; EOF section `0\nEOF`. Reject with `dxf_not_pairs`.
  2. File extension `.dxf` or `.aama` only (`.aam` is **not** accepted although the GUI lists it, F22 [V]); reject `.aam`.
  3. Required sections: HEADER, ENTITIES (TABLES, BLOCKS optional). Reject if ENTITIES missing.
  4. Header: if `$INSUNITS` present, report the implied factor (1 inch x25.4, 5 cm x10, 6 m x1000, else mm x1, F32 [V]); recommend omitting it (CLO's own reference DXFs have none and use a `UNITS: METRIC` text entity, F32). Warn if `UNITS:` text entity absent (default behaviour unconfirmed, F32/F22 conflict: lane AA says units come from `$INSUNITS`, lane P said from `UNITS:` text; resolve live, see e05).
  5. AAMA hints: look for text entities `PIECE NAME:`, `UNITS: METRIC`, `SAMPLE SIZE:`, `SIZE:`, `QUANTITY:` (warn when missing; no hard check exists, F32). Count closed outlines on layers {1, 8, 11, 14, 84, 85, 86, 87} (outline layer predicate 0x4096580); polylines with >= 3 vertices auto-close when first and last within tolerance. If zero outline candidates -> reject `no_outline` (a piece without outline is dropped silently).
  6. Entities: only tags 1,2,3,7,8,11,14,19,23 have handlers; SPLINE/ELLIPSE/DIMENSION skipped (F32); warn if outline geometry is SPLINE-only. ARC tessellated to 10 segments.
  7. Layer meaning table for warnings only: POINT layer 3 curve point, 4 or 80-83 notch, 13 drill, 2 turn point; LINE layer 7 grainline (F32 [V]).
  8. Graded DXF: if `GRADE RULE TABLE`, `NUMBER OF SIZES`, `SIZE LIST`, `RULE:` present, note `has_grading:true`, and expect `GetGradingSizeGroupCount()` to increase (unproven [I], F37).
  Modes: `validate:"strict"` rejects on 1-3,5; `"warn"` proceeds and returns the warnings.
- SDK order (async, type `import-dxf`):
  1. `count_before = PATTERN_API->GetPatternCount()`.
  2. `Marvelous::ImportDxfOption o;` `o.m_bAppend = append`; `o.m_bIncludeNotchs = include_notches` (**plugin currently leaves it false so layer-4 notches are dropped**, F22); **autoscale/m_Scale rule**: `m_Scale` is honoured only when `m_bAutoScale==false` (F26 [V], address `0x14476C31D`, `0x476bfd0`); so if `scale == 1.0` or `auto_scale == true`: set `m_bAutoScale=true` and leave `m_Scale` untouched; if the caller supplies `scale != 1.0` they must also pass `"auto_scale":false`, otherwise reject `scale_ignored_with_autoscale` (never set `m_Scale` while autoscale is true: it is silently ignored). The builder always converts file units to mm via the unit code regardless (F32). Leave `m_bConvertToSeamAllowance` unset: never read (F22 [V]). `m_eNotchImportPlacement` clamped <= 2 (F22).
  3. `ret = IMPORT_API->ImportDXF(path, o)` (impl `0x6021f40`; **ignore `ret`**: true for empty/invalid files, F22/F26 [V]).
  4. `count_after = PATTERN_API->GetPatternCount()`; `added = count_after - count_before`. `ok = added >= min_pieces && (expect_pieces<0 || added == expect_pieces)`. Replace `g_patternsLoaded++` with `g_patternsLoaded = count_after`.
  5. Optional geometry sanity: for each new piece `PATTERN_API` bbox getter (the plugin already exposes `/patterns/(\d+)/bbox`, route `read-pattern-bbox`): report bbox in mm and flag implausible sizes (a body piece under 50 mm or over 3000 mm indicates a unit error, F32 unit table).
- Response `data`: `{"api_returned":true,"patterns_before":0,"patterns_after":4,"added":4,"verified":true,"warnings":[...],"bboxes_mm":[...],"has_grading":false,"grading_groups":0}`.
- Error mapping: `file_not_found`, `bad_extension`, `dxf_prevalidation_failed`, `scale_ignored_with_autoscale`, `zero_pieces_added` (API true but count unchanged: unreadable/non-AAMA/no outline), `piece_count_mismatch`, `implausible_bbox`.
- Timeout 60 s; main thread required. Modal hazards: "This file is not a DXF format.", "Failed to load the DXF file.", non-AAMA conversion message (0x8892080) (F22/F32 [I]); the pre-validation exists to avoid them. Watchdog must dismiss; note that after dismissal the count check still decides success.
- Mark: all above [V] except messages being modal (F22 [I]) and the unit selection rule ($INSUNITS vs `UNITS:` text; F32 says `$INSUNITS`; F22 said `UNITS:`; unresolved whether missing `UNITS:` defaults to metric) [L]. **Live test: e05** (units variants, hand-made `UNITS:`/`PIECE NAME:`/`SAMPLE SIZE:` entities; scripts already blocked only by DXF content, not by the plugin; the new route adds the pattern-count verification and bbox read-back they need).

---

## 6. `GET /preflight` and the mismatch gate

Basis: existing `/health` (reports `sdk_clo_version`, `host_app_version`, `host_matches_sdk`), F14 (ABI check PASS for 336, FAIL for 224), F29/F11 (mismatch crashes import/delete/simulate). A host/SDK mismatch is silent at the vtable level: calls mis-dispatch (F14: DeleteAvatar 262 vs 264, Simulate 83 vs 85, NewProject 53 vs 55, Get/SetAvatarProperties 343/342 vs 350/349, five Export functions one slot early, grading six slots early).

- `GET /preflight` (sync, no queue needed; may run on the HTTP thread because it touches only version strings and the capability flags; no CLO API call):
```json
{"success":true,"ok":true,"host_app_version":"2026.1.336","sdk_clo_version":"2026.1.336",
 "host_matches_sdk":true,"abi_verified_slots":37,"plugin_built_at":"...","blocked_commands":[],
 "checks":[{"name":"host_matches_sdk","ok":true},{"name":"api_pointers","ok":true,"detail":"FABRIC_API,PATTERN_API,UTILITY_API,IMPORT_API,EXPORT_API non-null"},
           {"name":"document_present","ok":true},{"name":"queue_idle","ok":true},{"name":"disk_free_gb","ok":true,"value":42}]}
```
- Checks, in order: (1) `GetHostAppVersion() == MIRRA_PLUGIN_SDK_CLO_VERSION` (compare the full `major.minor.build` string, not prefix; `MIRRA_PLUGIN_SDK_FOLDER` also reported). (2) All five API globals non-null (`CLOGuard`). (3) Queue idle: `g_commandQueue.empty() && !g_queueProcessing`. (4) Disk free on the export/output drive >= 12 GB (CLO's "less than 10GB" modal, F29). (5) Optional GPU mode unknown: `UtilityAPI` has no getter documented; report `gpu_sim_mode:"unknown"`. A static ABI proof of slots is offline-only (`scripts/abi_check.py`, exit 0 PASS); the build script should run it at build time and embed the result as `MIRRA_PLUGIN_ABI_CHECK_PASS` into `PluginBuildInfo.h` (not the plugin's job at runtime). `abi_check.py` evidence is for the 336 SDK only; it cannot see a different installed app at runtime, hence the runtime version compare.
- **Gate**: a global `std::atomic<bool> g_abiOk` set at startup from check 1. The route handlers for `/import-avatar`, `/import-avatar-avt`, `/import-avatar-measurements`, `/clear-avatars`, `/new-project`, `/simulate`, `/export`, `/pattern/import-dxf`, `/grading/change-size`, `/avatar/properties` (POST) and `/fabric/*` (POST) must check `g_abiOk` **before enqueueing** and reply `{"success":false,"error":"abi_mismatch","host":"...","sdk":"..."}` with HTTP 409. Read-only routes work but include `"abi_unverified":true`. Override only with an env var `MIRRA_FORCE_ABI=1` (for debugging), logged at WARN level in `TraceLog`. Python client must call `/preflight` once per run and abort on `ok:false` (e07-style preflight in `experiments/_common.py` already does the equivalent).
- Mark: version compare logic [V, existing `/health`]; ABI table [V, F14]; the "mismatch crashes" explanation is [I] but consistent with F14 [V] slot shifts. **Live test: none required to implement; verify by launching with an old SDK build** (do not run in this lane; supervised only).

---

## 7. Avatar import ordering endpoint: `POST /avatar/import-sequence` (async, type `avatar-import-sequence`)

Basis: F40 (lane AL, corrects F36/F33/K), F36, F33, F29, F24. Purpose: one atomic server-side macro so the client cannot reorder the steps. Replaces the client-side sequence `clear-avatars` / `import-avatar-avt` / `import-avatar-measurements` / `.avs` with a single verified flow.

### 7.1 Request
```json
{"avt_path":"C:/.../template.avt","avs_path":"C:/.../user.avs",
 "avt_method":"import_avatar","require_category":"male",
 "expect_measurements":{"Bust Circumference":912.0},"tolerance_mm":5.0,
 "export_glb":"","abort_on_dialog":true}
```

### 7.2 SDK calls in order (all in one `ProcessCommandQueue` branch, one request id)

1. **Gate**: preflight (section 6); queue idle; `fileExists(avt_path)`, `fileExists(avs_path)`; `.avs` first dword check: read 4 bytes, little-endian; value 1 or 2 -> reject `avs_lower_version`; value 3 -> legacy single path (accepted but warn); anything else (e.g. Mirra's `03 0a 0e 0d`... note F40: Mirra files start `03 0a 0e 0d` and take the current-format loop; interpret the dword as the `fread` result CLO uses, do not guess endianness: compare as raw bytes `{1,0,0,0}` and `{2,0,0,0}` for rejection, and flag `{3,0,0,0}` as legacy) [I on endianness].
2. **Clear**: delete all avatars, but not by tally. `count = EXPORT_API->GetAvatarCount()` inside an SEH-protected helper (existing comment: count queries crashed/hung in an empty scene on older builds; the current `read-avatar-state` calls it anyway, so it is considered usable on 336); `indices = [0..count-1]`; `UTILITY_API->DeleteAvatar(indices)` (true only if at least one index was valid; skip if `count==0`). Re-read `GetAvatarCount()`; require 0, else `clear_failed`. Reset `g_avatarsLoaded=0` from the real count. F40: clearing is *still needed* (otherwise an older current avatar would be resized instead, or the call aborts on a category mismatch, or the chooser/softbody dialogs appear on the wrong avatar). After a delete `mgr+0x98` (current) moves to the first remaining avatar (F24).
3. **Single import**: `IMPORT_API->ImportAvatar(avt_path, options)` (existing behaviour of method `import_avatar`) or `ImportFile(avt_path)` one-argument (method `import_file`, F36: use the one-argument slot-2 form, never the `ImportExportOption` overload for avt/avs; note slot 1 does nothing for avt). `ImportFile` on `.avt` appends (no clear call on traced path, F36 [I]), writes the `CurrentAvatarFilePath` setting, and if graded-size avatars exist shows a modal prompt (string 0x2d903af). Verify: `GetAvatarCount() == 1` and `GetAvatarNameList()[0]` non-empty; the returned bool is not used as proof (slot 2 returns true even with no document; F36 [V]). `g_avatarsLoaded = 1`.
4. **Category check** (F40 [V]): `GetAvatarGenderList()[0]` against `require_category` (Male/Female/Boy/Girl/PreSchool/Baby). The `.avs`'s `qsAvatarID` must be in the same template category as the `.avt` (match predicate 0x50f2660: id equal, or both ids map to the same category through 0x50d3680 by case-sensitive substring tests such as `MaleTemplate`, `New_002`/`New_004`, `MaleVariant`). Because `qsAvatarID` is inside the binary `.avs`, the plugin cannot parse it cheaply [I]: do it offline in Python (pre-check) and in the plugin only run the gate on `gender`. If mismatch is detected here, abort before step 6, `category_mismatch`.
5. **Option pre-flight** (section 2.2): `SetAvatarSmooth(0,0)` if Divide on, then `SetAvatarSoftBodyStiffness(0,0.0f)` if Softbody on; verify via `GetAvatarProperties(0)` that both are off. All five repo `.avt` samples already have both off (F33), so this is normally a no-op but is cheap. Skip on any failure -> `option_clear_failed` and abort (the confirmation box would block the UI thread).
6. **Apply sizing**: `IMPORT_API->ImportFile(avs_path)` (one-arg slot 2). **Only the current avatar** is resized (F40 [V]; with one avatar loaded it is the one). Expected dialogs on this call (F40/F33/F36): "No matching Avatar." (no avatar, validation failure, zero matches, legacy mismatch), chooser dialog (>= 2 candidates; `App+0x50` vtbl slot 71), the Softbody confirmation (if `avatar+0x10B0` set; cancel returns false), "Invalid file path", "created in a lower version", "This avatar pose file is not compatible with the current avatar.", and the non-fatal "sizing data was created in a lower version" box from the apply step (old-format `.avs`, e.g. a missing `MVresizingMap` key; keep every key the stock `.avs` has). Return value is not a success signal: true unless GUI-mode `App+0x50` method 74 returned false (F36 [V]).
7. **Verify**: (a) `GetAvatarCount() == 1` (no avatar duplication). (b) `m = GetAvatarMeasurements(0)`; convert to mm by `unit`; compare against `expect_measurements` (names must match CLO's measure names, mapping in F27) within `tolerance_mm` (default 5 mm). Silent no-op case F40: if the measure-mode validity test fails, CLO appends `_resaved` to the avatar id and clears `+0x990` so the driver skips the work, and the handler **still returns true**; so also read `GetAvatarProperties(0)["qsAvatarID"]` (or the name list) and fail if it contains `_resaved` `[I on property exposure]`. (c) Optional `export_glb`: after verification, `ExportGLB` avatar only (section 4) to prove a mesh. Each of (a)-(c) sets a `verified_*` flag. Overall `success = clear_ok && import_ok && no_dialog && measurements_within_tol`.
8. On any failure: do **not** continue to garment steps. Leave state as is; return `data.failed_at` with the step name; the client decides whether to retry from step 2.

### 7.3 Modal dialog strategy (the "No matching Avatar." / chooser / softbody dismissal strategy)

- **Prevent first**: single avatar loaded (step 2-3), same category (step 4), softbody and divide off (step 5), valid `.avs` (step 1). With these, none of the F40 boxes should appear; each prevention maps to one box: `No matching Avatar.` <- steps 3+4; chooser (>= 2 candidates) <- step 2; softbody confirmation <- step 5; "lower version" <- step 1.
- **Detect**: the macro runs on the UI thread, so it cannot observe its own modal box. A **watchdog thread** inside the plugin (new, started with the REST server) observes `g_queueProcessing && macro_step_started_at + step_timeout < now`; at that point it enumerates top-level windows of CLO's process (`EnumWindows` filtering `GetWindowThreadProcessId` == CLO's pid, class `#32770` or Qt message-box window), reads the title/static text (`GetWindowText`, child `Static` texts), and **only records** the text into `g_lastModal` (reported by `/status` as `modal:{"title","text","since"}`). It does not click anything unless `abort_on_dialog:true` AND the text matches the allow-list below. This is the same logic as `experiments/e07_modal_watchdog.py` (which reads window lists only and dry-runs dismissal by default); port the proven e07 approach after e07 results exist.
- **Dismiss allow-list** (button mapping: Cancel/No semantics assumed, dialog-service button ids not decoded, F33 [I]): 
  - "No matching Avatar." (info box, OK) -> dismiss with OK/Enter, then mark the step failed `no_matching_avatar`.
  - Avatar chooser (modal list) -> dismiss with Cancel; mark `avatar_chooser`; the step is failed (never pick).
  - "The Softbody Option will be turned off ..." / "Divide Option" -> **dismiss with No/Cancel** (button id 2, assumed; Cancel returns false and leaves the avatar unchanged, F33 [I]); mark `softbody_prompt`; fail the step. Never click Yes: clicking Yes turns the option off and resizes, but would also change the user's avatar's state silently; if a policy decision says Yes is acceptable, make it an explicit request field, not default.
  - "Failed to load the Avatar Size file. Invalid file path." / "created in a lower version" / "avatar pose file is not compatible" -> OK, fail.
  - Not auto-dismissed (leave for a human, report `needs_human`): "Loading a motion will delete all existing avatar animation layers...", "Added avatars for graded size will be replaced...", "This file format is not supported in this version.", the "negative thread lengths" Yes/No box, GPU-memory boxes, disk-space prompt, and anything unmatched.
- After a dismissal the macro resumes (the blocked API call returns). Because the return value is untrustworthy, the verify step (7) is always what decides success.

### 7.4 Timeouts

- Per-step budgets (plugin watchdog; client budget = sum + 15 s): clear 15 s; avt import 60 s (large template, large textures); option clear 5 s; avs apply 90 s (the resize driver `0x511a1b0` rebuilds the mesh; time not measured [L]); verify 15 s; optional GLB export 120 s. Overall client `wait_for_queue(timeout=240)`; the existing client default is 30 s, which is too short for the full macro (`client.py` `timeout` param).
- If a step exceeds its budget the watchdog logs the modal text (if any) and sets `data.timed_out_step`; the plugin cannot cancel the blocked call (no cancel path, F29). The client must then run the dismissal procedure by hand (e07) and call `/preflight` again before proceeding.
- Simulate budget formula for any command that includes a `simulate_after` (grading, fabric): `120 s + steps * per_frame_s` where `per_frame_s` is unknown; e03 measures it. Note F29 [V]: each Simulate call may restart the Folding/Draping phase from frame 0 (frames 0-9 Folding if a foldable item exists; Draping until 50 total frames, 40 without folding) so chunking into small requests may not behave as expected [L, e03].

### 7.5 Response
```json
{"success":true,"request_id":"r-17","data":{"cleared":1,"imported":true,"avatar_count":1,"gender":"Male",
 "options_cleared":{"divide":false,"softbody":false},"avs_applied":true,"avs_api_returned":true,
 "measurements_within_tolerance":true,"max_abs_diff_mm":1.2,"resaved_suffix":false,
 "modal_seen":null,"failed_at":null}}
```
- Mark: ordering rule and target-set semantics [V, F40, static]; clear-before-import requirement [V]; `.avs`'s first-dword classification [V]; chooser return value, whether import sets `mgr+0x98`, `GetAvatarProperties` exposing `qsAvatarID` [I]; whether the `.avs` route actually changes the exported GLB mesh (F42: exported GLBs were identical across users; only `.avt` floats differed) [L]. **Live tests: e01 (S1: single avatar + avs; S2: two avatars to see chooser/category behaviour; S3: softbody-on avatar to see the box), e02 (patched `.avt` redeform comparison), e07 (watchdog dismissal), e08 (export check after resize).** Per the experiments README the preflight in `_common.py` already aborts if the host mismatches or the queue is busy, matching section 6.

---

## 8. Summary matrix

| # | Route | New/changed | Verified (findings) | Inferred | Live test |
|---|---|---|---|---|---|
| 1a | GET `/grading/info` | new | F37 getters implemented | arg lists, pairing semantic | e04 |
| 1b | POST `/grading/change-size` | new | F37 `group<count` guard, bool returns | post-switch Simulate need, avatar swap | e04 |
| 2a | GET `/avatar/measurements` | new | F16 unit/list semantics | return type, field names | e01, e02 |
| 2b | GET/POST `/avatar/properties`, POST `/avatar/clear-options` | new/replace | F33 smooth-before-softbody, never enable | key names exposed | e01, e07 |
| 3a | POST `/fabric/physical` | new (replaces preset no-op) | F38 AddFabric/Change/Assign semantics | assign_option range, `_v2` regeneration | none yet (propose e09), zprj diff |
| 3b | POST/GET `/fabric/color` | replaces | F21, F16 float overload, failure sentinel | RGBA order, Back alias effect | e06 |
| 4 | POST `/export` | extended | F39 flags, offsets, lists, stale-list trap | zip/colorway names, thick mode | e08 |
| 5 | POST `/pattern/import-dxf` | replaces | F22, F26, F32 (return true, m_Scale rule, layers) | unit selector, modal messages | e05 |
| 6 | GET `/preflight` + gate | new | F14, existing `/health` | crash cause | none (old-SDK launch test, supervised) |
| 7 | POST `/avatar/import-sequence` | new | F40 ordering, F36 return values, F33 | chooser result, dialogs' button ids, GLB mesh change | e01, e02, e07, e08 |

## 9. Implementation checklist for the developer

1. Add `requestId`/`extra` to `APICommand`, `requestId`/`data` to `CommandResult`; extend `/status` and add `GET /result/<id>`; add `dispatchSyncReadJson` with a wait parameter.
2. Add `g_abiOk` and the 409 gate to all mutating routes (do not touch read routes).
3. Implement section order 6, 2, 1, 5, 4, 3, 7. Each route gets a thin HTTP handler (parse, validate, enqueue) and one `else if (cmd.type == ...)` branch; share helpers: `readbackColor`, `patternCountSafe` (SEH), `avatarCountSafe` (SEH), `mmFromUnit(unit)`.
4. Wrap each branch in the existing try/catch; any new SDK call that can fault goes through the plugin's `__try` helper pattern (no C++ objects with destructors in the `__try` function).
5. Keep the SDK/app match: rebuild with `clo_workspace/build_plugin.py` against the SDK folder equal to the host version, as already required by the repo memory note (mismatch crashes CLO).
6. After building, run `scripts/abi_check.py` (PASS) and the e04/e01/e05/e06/e08 experiments in the README order, supervised, with e07 running in a second terminal.
7. Remove no existing route; mark `/avatar/grading-size`, `/set-fabric` (preset ignored), `/import-pattern`, `/set-fabric-color` as deprecated aliases that forward to the new handlers.

*Not covered / out of scope*: `ReplaceFabric`, `CombineZfab`, `SetSimulationAirDamping` (raw float store, no clamp, no re-simulation, F38), and the vertex read-back needed by e03 (no API identified).
