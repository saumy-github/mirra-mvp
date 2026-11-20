# 06 — The `.avs` avatar route: performance, why it replaced the old methods, and every change so far

*Status: implemented and run end to end for one user; two derived-float variants compared on two profiles*
*Compiled: 2026-10-15*

## 1. Summary

Step 1 used to patch measurement numbers into a copy of `base-1.avt`, import that file into CLO through the plugin, and export a GLB. The numbers were saved correctly, but the exported body never changed: every GLB was the base body (top of the mesh at 1.9078 m, the 187.96 cm template), whatever height or girth was requested. The saved-float check passed regardless, because it only reads the same floats back.

The new route imports the **unpatched** `base-1.avt`, then applies a generated CLO avatar-size file (`.avs`) to it with the SDK's `ImportFile`. CLO then rebuilds the body from the size data, the same way its Avatar Editor does. The exported GLB, the saved project and CLO's own measurements all show the resized body.

---

## 2. Why the previous methods did not work

| Method | What it did | Result |
|---|---|---|
| `avt_patch` + `ImportAvatar` (the old default) | Wrote six floats into the `.avt` binary (about 18 bytes differ from the base) and imported it | Floats saved; mesh stayed the base body. The five batch runs (users u_011–u_015) and run u_001-081 all had identical vertex buffers, skeleton and inverse-bind matrices. The same patched file opened in CLO's GUI **does** morph the body, so the file was valid and the API import path was the gap. |
| Wait 30 s or run a simulation after import | Gave CLO time to rebuild | No change (body top stayed 1.9078 m). |
| `ImportAvatar` / `ImportFile` option sweep (`bAdd`, `bAutoTranslate`, `ImportObjectType`, `bMoveGarment`, `bSizeAndPoseFromAvatar`) | Eight variants | No change; the variant that passes an options object to `ImportFile` returned false. |
| CSV: `ImportAvatarMeasurement`, `ImportMeasurement` | Three guessed CSV layouts, then CLO's **own** exported Avatar Size CSV, unchanged and edited | Rejected every time, even the unchanged export. The SDK documents the function in two lines with no format. |
| `avatar_properties` (`SetAvatarProperties`) | Earlier research (see `clo_avatar_generation/schema/legacy_routes.md`) | Only physics and render properties exist in that namespace; body measurements never appear. |
| Grading route (`AddGradingSizeGroup` then `SetGradingPairedAvatarSizing`) | Experimental endpoint added to the plugin | `AddGradingSizeGroup` returned -1 in every variant, so nothing was applied. |
| Opening the Avatar Editor panel first | Only an observation | With the editor open, the API import did morph the body. That is not usable for automation, and it pointed at the editor's size-driven rebuild as the missing step. |

---

## 3. How the new route works

1. Step 7 starts a new project, waits for CLO to settle, and imports the unpatched `base-1.avt`.
2. Step 8 writes `clo_payload.avs`: the template `CLO_Male_Default.avs` with six floats overwritten (height, chest, waist, low hip, inseam, across-shoulder) and about 50 derived floats filled in from a fitted model.
3. The plugin applies it with `ImportFile` (`POST /import-avatar-avt` with `method: "import_file"`).
4. Step 11 saves the project (`result_project.zprj`; kept for now, may be dropped later) and reads the avatar back out of it.
5. Step 12 exports the GLB and **checks the body height**: the GLB's highest vertex must be within 1.5 cm of `1.9078 m x requested height / 187.96 cm`. If not, the step fails and a warning says the body was not resized.

Why the derived floats: an `.avs` carries the same 57-float `listFeatureValues` block as the `.avt`, but only six are measurement fields we drive. CLO uses the stored values rather than recomputing the rest, so leaving them at the template defaults (set A) leaves thigh, bicep, neck and arm length almost unchanged for a differently sized body. A ridge fit (set B) predicts them from the six inputs. It was trained on 25 CLO-made samples: the 11 male sizes CLO ships (`CLO_Male_Default` and the ASTM sizes R_34 to R_52), three files saved from the editor, and 11 distinct pipeline-run results. Leave-one-out error is about 0.7 cm typical and 4.2 cm worst.

---

## 4. How it performs

### 4.1 Body height from seven generated sizes (set A, GLB body height)

| Profile (height / chest / waist / hip / inseam / shoulder, cm) | Requested height | Body height in GLB |
|---|---|---|
| p1 short, slim: 160 / 88 / 72 / 92 / 73 / 40 | 160 | 161.1 |
| p2 small: 168 / 92 / 78 / 96 / 77 / 42 | 168 | 169.1 |
| p3 mid: 175 / 98 / 84 / 98 / 81 / 44 | 175 | 176.1 |
| p4 tall: 182 / 104 / 92 / 102 / 84 / 46 | 182 | 183.0 |
| p5 tall, big: 190 / 110 / 100 / 108 / 88 / 48 | 190 | 191.0 |
| p6 heavy: 172 / 120 / 110 / 112 / 79 / 50 | 172 | 173.1 |
| p7 slim, tall: 178 / 90 / 70 / 92 / 82 / 43 | 178 | 179.0 |

All seven GLBs are different. The mesh reads about 1 cm above its nominal height (the unmodified default measures 188.9 cm against a stored 187.96).

### 4.2 CLO's own measurements (Avatar Size CSV exported from the editor)

For each file the editor's CSV was exported and compared with the request (mm):

| File | Bust | Waist | Low Hip | Inseam | Shoulder | Total Height |
|---|---|---|---|---|---|---|
| A, p1 (requested 880 / 720 / 920 / 730 / 400 / 1600) | 880.0 | 720.0 | 920.0 | 730.0 | 400.0 | 1610 |
| A, p5 (1100 / 1000 / 1080 / 880 / 480 / 1900) | 1100.0 | 1000.0 | 1080.0 | 880.0 | 480.0 | 1910 |
| B, p6 (1200 / 1100 / 1120 / 790 / 500 / 1720) | 1200.0 | 1100.2 | 1119.8 | 790.3 | 500.0 | 1729.6 |
| A, p7 (900 / 700 / 920 / 820 / 430 / 1780) | 900.0 | 700.1 | 919.9 | 820.3 | 430.0 | 1789.7 |
| B, p7 | 900.0 | 700.1 | 919.8 | 820.3 | 430.0 | 1789.7 |

The five measurement fields land within 0.3 mm of the request in these files. Total Height reads about 1 cm high everywhere, the same offset as above.

### 4.3 Set A against set B

| Profile | Key measurements | What differs |
|---|---|---|
| p6 heavy (172 / 120 / 110 / 112 / 79 / 50) | B within 0.2 mm; A drifted up to 6.5 mm (waist 1093.5 against 1100) | Thigh: A 567.8, B 660.2, default 558.9. Bicep: A 327.4, B 387.1. Neck base: A 410.6, B 459.7. Arm length: A 650.5, B 627.7. |
| p7 slim, tall (178 / 90 / 70 / 92 / 82 / 43) | Both within 0.3 mm | Thigh: A 558.9, B 520.4. Bicep: A 323.4, B 295.7. Arm length: A 648.5, B 624.2. High hip: A 882.5, B 830.7. |

Only 2 (p6) and 8 (p7) of 53 measurements are identical between A and B, so the derived floats shape the whole body. B scales thigh, bicep, neck and arm with the body; A leaves them at the default avatar's values. That B looks more plausible is a reading of the proportions, not a check against real bodies.

### 4.4 Pipeline run `u_003-004` (the first run on the new route)

- All 12 steps passed; about 66 seconds in total, against 67.6 to 69.9 s for the previous route.
- One avatar in the saved project. Saved avatar floats match the request exactly (175 / 96 / 82 / 96 / 80 / 43).
- GLB height check: top 1.7786 m against 1.7763 m expected (+0.24 cm).
- The saved avatar's body mesh array tops out at 1792 mm, against 1921 mm for the unmodified base. (A second array in the file stays at the base height; CLO's own GUI-saved files show the same.)
- Outputs: `clo_payload.avs`, `result_avatar.glb`, `result_avatar_from_project.avt`, `result_project.zprj`, `run.log`.
- The database record for u_003 has no hip or leg-length value, so the run used a separate measurement file with two estimated fields (hip 96, leg length 80); the database was not changed.

---

## 5. Why it is better than the previous methods

- The body actually changes. Everything before produced the base body in the GLB regardless of the request.
- It uses CLO's own file format and CLO's own resize path, so the result is the same as typing the values into the Avatar Editor.
- It is checked at the end against something that cannot pass by accident: the GLB's body height. The old check only read back the floats it had just written.
- It needs no GUI at run time: after the plugin is up, the pipeline is plugin calls only.
- The saved `.zprj` embeds the resized avatar and its floats read back correctly, so the existing save-and-verify steps still work.
- Run time and file sizes are unchanged from the old route.

---

## 6. Known limits

- Total Height reads about 1 cm above the requested value; this is not compensated yet.
- The fitted derived floats have a typical error of about 0.7 cm and up to about 4 cm at extremes, and were trained mostly on heights of 165 to 190 cm and chest 86 to 132 cm.
- Set A against set B has been compared on two profiles only, and only through CLO's measurement export. Measurements outside the six driven fields have no ground truth.
- `ImportFile` returns success even when it did nothing, so the GLB height check is the real proof. Plugins built before 2026-10-15 ignore the `method` field and would try to import the `.avs` as an avatar.
- Male only (the template and fitted model are the male default). Face and skin are not part of this.
- CLO must stay on 2026.1.224 to match the plugin's SDK build.
- The two new runtime files, `clo_avatar_generation/input/CLO_Male_Default.avs` and `clo_avatar_generation/input/avs_derived_model.json`, sit in an `input/` folder that `.gitignore` excludes (as `base-1.avt` already is), so they will not be committed or cloned unless that is changed.
- The u_003 database record is incomplete, as noted above.

---

## 7. Everything changed so far

### Earlier in this work (CLO crash diagnosis, 2026-10-14)
- `clo_workspace/build_plugin.py`: records the SDK folder and SDK CLO version in the generated `PluginBuildInfo.h`, and logs the SDK folder.
- `clo_workspace/windows/RestPlugin_windows.cpp`: `GetHostAppVersion()`; `/health` now returns `sdk_folder`, `sdk_clo_version`, `host_app_version` and `host_matches_sdk`; a startup warning is written when they differ.
- `clo_vto/native_vto/context.py`: removed an unused `project_dir` field and the `projects/` folder it created; nine empty `projects/` folders under `clo_vto/output/` were deleted.
- Cause found: CLO had auto-updated to 2026.1.310 while the plugin was built against SDK 2026.1.224. Rolling CLO back fixed the crashes.

### Plugin source (`RestPlugin_windows.cpp`, additive; defaults unchanged)
- `POST /import-avatar-avt` accepts optional `method` (`import_avatar`, `import_file`, `import_file_opts`) and `options` (`scale`, `bAdd`, `bAutoTranslate`, `ImportObjectType`, `bMoveGarment`, and others).
- New experimental `POST /avatar/grading-size` (the grading route; it fails at `AddGradingSizeGroup`, kept for reference).
- The vault DLL `C:\D-drive-data\plugins\mirra-vault\RestPlugin_v1.3.2.dll` holds the current build; `RestPlugin_v1.3.2.import-options.bak.dll` is the build before the grading endpoint. The verified build from before 2026-10-15 was overwritten by the first rebuild.

### Pipeline (`clo_avatar_generation/`)
- New `avatar_runtime/avs_patch.py`: finds the float block in an `.avs`, builds an `.avs` from the template with the requested fields and the predicted derived floats.
- New `input/CLO_Male_Default.avs` (copy of CLO's shipped default male size file) and `input/avs_derived_model.json` (the fitted model, with its training summary).
- `avatar_runtime/client.py`: `import_avatar_avt(path, method=...)`.
- `avatar_runtime/apply_mode.py`: new `avs` mode, preferred in `auto`.
- `avatar_runtime/step_06_build_payloads.py`: `avs` reuses the avt-patch field and index payload.
- `avatar_runtime/step_07_import_base_avatar.py`: imports the unpatched base avatar when the mode is `avs`, then waits 2 s.
- `avatar_runtime/step_08_apply_measurements.py`: new `avs` apply branch.
- `avatar_runtime/step_12_export_glb.py`: GLB body-height check, failing the step when the body was not resized.
- `run_avatar.py`: default mode is `avs`; `avs` added to the choices.

### Documents and data in this folder
- `15-10-avatar measurement-glb-issue/`: the avatars, projects, GLBs and CSVs saved from CLO; two sets of seven generated `.avs` files (set A: template defaults for the derived floats, set B: fitted); and the measurement CSVs exported for p1, p5, p6 and p7.
- This file and `05-clo-startup-and-editor-automation.md`.
- An unrelated stray file, `Custom_Custom.avs`, was saved here from the editor's default file name.

### Not done
- Nothing is committed.
- The plugin's modal start-up message is still there.
- Hip and leg length for u_003 are still missing from the database.
- No decision yet between set A and set B beyond the evidence above (the pipeline currently uses B).

---

## 8. Update 2026-10-16: warm CLO session, simpler measurements, website wiring

*Status: implemented and run on the CLI; website changes tested with a fake database only, not through the running stack*
*Compiled: 2026-10-16*

### Warm session
- CLO stays open with the base avatar. Step 7 skips the new project and base import when the plugin reports an avatar loaded, no garment patterns, and the last import was the base file or an `.avs`; otherwise it resets as before. `--fresh-session` forces the reset.
- Safe because each `.avs` overrides every size value: applying p1, p6 and p3 in sequence gave bodies identical to fresh loads (0.000 mm).
- Two different users back to back (`u_001-092`, `u_003-005`): both reused the session, both passed the GLB height check, runs took about 52 to 53 s against about 66 s with the reset.

### Outputs per run
`clo_payload.avs` (input size file), `result_avatar.glb`, `result_avatar_from_project.avt` (extracted from the project), `result_project.zprj`, `run.log`. Three product formats (GLB, AVT, ZPRJ) plus the `.avs` input. No OBJ or FBX is exported.

### Measurements (step 3)
- Three sources only: the job snapshot (`measurement_doc_input`, passed by the worker), an explicit `--measurement-file`, or MongoDB (`user_measurements`, then the legacy `measurements` collection with a warning).
- Removed: the implicit per-user JSON in `input/` and the stale-snapshot fallback. A database error or a missing record now fails the run.

### Website
- `worker/tasks.py`: uses the shared `DEFAULT_APPLY_MODE` (`avs`; it was still `avt_patch`), passes the job's measurement snapshot, and stores `pipeline_version` on the profile.
- `avatars/service.py`: `start_generation` returns a ready job without queueing CLO when the stored avatar matches the current measurements version and pipeline version and its GLB exists; `force=true` always regenerates.
- `avatars/controller.py` and `routes.py`: the GLB route sends an `ETag` and `Cache-Control: private, no-cache`, and answers a matching `If-None-Match` with 304 plus the fresh staleness header. The old `immutable` header sat on a URL that does not change between regenerations, so a browser could keep showing an old avatar.
- `avatars/models.py`: `AVATAR_PIPELINE_VERSION = "avs-1"` and a `pipeline_version` profile field. Avatars stored before this change count as stale and regenerate the next time the user generates.

### Other changes
`context.py` (`DEFAULT_APPLY_MODE`, `measurement_doc_input`, `reuse_session`), `step_02_run_setup.py`, `run_avatar.py` (`--fresh-session`), `repeat_run_check.py` (shared default mode).

### Open
- The website changes have not been run against the real stack (Mongo, Redis, worker, browser).
- Whether generation should also start automatically when measurements are saved, or stay on the user's click, is undecided.
- The u_003 database record still lacks hip and leg length.
