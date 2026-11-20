# Plan 03: Avatar module clean-up (female research, old data, backend, worker, frontend, docs)

*Status: draft under review by you (read up to B12 so far; B44 list approved 2026-10-19); nothing is executed. Planning phase only, no code.*
*Compiled: 2026-10-19, updated 2026-10-19 (B44, B49, B56 added; repo-root paths added (B40); consistency pass against `02-issues.md`)*

## Overview

This plan fixes the avatar module of the website and the avatar generation hand-off between backend, worker and pipeline. It follows the issues in `02-issues.md` (issue numbers are in brackets) and the reference notes in `01-avatar-workflow-and-reference.md`. Auth is left as it is (testing uses incognito windows with the guest login). Business pages, the Studio and try-on are out of scope, except where they read the avatar profile or use the fields and paths removed here (B44, B40).

Female research comes first (Phase 0), so the backend and API changes in Phase 2 handle male and female from the start.

Execution follows `.agent/03-execution-phase.md`: one phase at a time, stop at the end of each phase and wait for your confirmation. Any problem or flag found during execution is reported in chat first.

## Phases

### Phase 0: Female avatar research [B36, B35]

**Goal**: decide how female users are supported and what to do with bust and under-bust, before any model or API is changed.

**Steps**:

1. You download a female avatar's measurements and a female base `.avt` from CLO (the female size file `.avs` too if CLO offers it).
2. Read the female size list and compare it with the male one: which of the 57 values exist, where the driven fields sit (height, chest or bust, waist, hip, inseam, shoulder), and the exact CLO names.
3. Decide the female template, the CLO-made sample bodies needed for a female derived-size model, and how the pipeline picks the base avatar, template and model by gender.
4. Decide which measurement fields are required for each gender, and what the form does for female until the pipeline supports it.
5. List what the pipeline, backend, worker and frontend need for female support, and add those steps to this plan after your approval.
6. Write the decision in `01-avatar-workflow-and-reference.md` and update the B36 solution.

### Phase 1: Clean up old web avatar data [B32, B31]

**Goal**: remove avatar data made from the website by the old pipeline, so nothing is out of sync with the code changes that follow. Terminal runs are kept.

**Steps**:

1. List every web-only item and show the list to you: the folders under `dev_upload/avatars/`, the run folders in `clo_avatar_generation/output/` that belong to website users (`g_*` and `u_dcabc592e2bb18e7-*`), and the documents in the dev database collections `avatar_jobs` and `avatar_profiles`.
2. Check that the terminal runs (`u_001-*`, `u_003-*` and the like) are not on the list.
3. Wait for your approval of the exact list.
4. Delete the approved folders and documents.
5. Check that the folders are gone, the two collections are empty, and the terminal run folders are untouched.

### Phase 2: Backend model and API changes [B1, B7, B8, B9, B11, B12, B17, B18, B30, B31, B34, B35, B40, B44, B49, B56]

**Goal**: slim the avatar data, make the API return what the pages need, and stop bad requests early, for both genders.

**Steps**:

1. `user_measurements`: remove `body_shape_type`. Keep `accuracy`, `weight_kg`, `skin_tone_hex`, bust and under-bust, and apply the Phase 0 decision on which fields each gender requires.
2. `avatar_profiles`: remove the copied measurements, gender, body shape, skin tone, `source_job_id`, `generated_at` and `pipeline_version`. Keep `user_id`, `avatar_glb_path` (now relative to the repo root, step 12), `clo_run_id`, `source_measurements_version`, `created_at`, `updated_at`. Delete `clo_avatar_avt_path` (B40).
3. `avatar_jobs`: keep `user_id`, `state`, `measurement_snapshot`, timestamps; add a short `error_code`; remove `avatar_profile_id` (B9 as proposed, to be reviewed by you later).
4. Remove the `pipeline_version` check from the skip-if-fresh logic, so only `measurements_version` decides.
5. `GET /avatars/profile` returns what the page needs: whether an avatar exists, created and updated dates, `isStale` (computed on the server), and the user's active job if one is queued or processing, so the page can show the progress screen again after a reload.
6. `POST /avatars/generate`: return the existing active job if there is one (a simple check; the frontend also locks the button on click; B12); check the required measurement fields for the user's gender and return a clear message listing the missing ones; keep the 404 for no measurements.
7. Keep the GLB route and its ETag. Remove the `X-Avatar-Measurements-Stale` header, since `isStale` now comes from the profile (B7).
8. Update the try-on code so it builds the `.avt` path from `avatar_glb_path` instead of reading `clo_avatar_avt_path` (B40), using the shared path module from step 12.
9. (B44, approved 2026-10-19) Remove the dead backend bookkeeping fields and the hard-coded version values the backend stores for try-on and analytics: `generated_at`, `source_job_id`, try-on `clo_run_id`, and the analytics `engine_version`, `app_version`, `environment`, `occurred_at`.
10. (B56, decided 2026-10-19) Remove the other backend leftovers that are safe to remove: the `run-<size>` ETag fallback (make `clo_run_id` required on the profile, so the ETag is always `<clo_run_id>-<size>`); the `STAGE_LABELS` server string (the frontend shows its own label per state, Phase 4 step 5); and `garment_snapshot` and the `cloth_id` default on try-on renders, but only after searching the code and confirming nothing reads them (if something does, report it in chat and keep it).
11. (B49, decided 2026-10-19) When measurements are saved, raise `measurements_version` only if at least one value changed (compare the new values with the stored ones, as numbers). If nothing changed, return the stored measurements unchanged.
12. (B40, decided 2026-10-19) One place for paths: create a small shared module that defines the repo root and the upload folder names (`dev_upload`, `live_upload`) and import it in the backend (`config.py`, `avatars`, `tryon`) and the worker (`tasks.py`, `live_upload.py`, `run_worker.py`), replacing the four separate `REPO_ROOT` definitions. Every path stored in the database becomes relative to the repo root (`avatar_glb_path`, try-on `render_glb_path`); keep the check that a resolved path stays inside the upload folders. Check that the Docker mounts in `docker-compose.yml` still put `dev_upload` and `live_upload` under the backend's repo root.

### Phase 3: Worker changes [B6, B13, B20, B37, B38, B40, B56]

**Goal**: make the worker report problems clearly and survive idle periods.

**Steps**:

1. Replace the raw failure text with a short `error_code` on the job (examples: CLO unreachable, measurements incomplete, export failed, worker restarted, unknown). The raw detail stays in `run.log`.
2. Set a job to `processing` only after the CLO health check passes.
3. On worker start, fail any job left in `processing` with the "worker restarted" code.
4. Stop writing the removed profile fields; write the new profile shape from Phase 2, with `avatar_glb_path` relative to the repo root from the shared path module (Phase 2 step 12).
5. Give the worker its own small settings (Mongo, Redis, `APP_ENV`) instead of importing the backend's full settings, and update the worker env example (names only, no values read).
6. Apply the Redis idle-timeout fixes from `.agent/saumy/00-WORKER-REDIS-TIMEOUT.md`: shorter blocking window, TCP keepalive and a health-check interval on the connection.
7. Rewrite `worker/README.md` to match (B20).
8. (B56, decided 2026-10-19) Stop writing the unused breadcrumbs in `run_manifest.json`; keep only what the upload folder needs. Check first what reads the file.

### Phase 4: Frontend changes [B1 to B7, B11, B15, B17, B23, B30, B12, B42, B44, B49, B52, B54]

**Goal**: show the right page for each user and plain messages, and remove what isn't needed.

**Steps**:

1. Remove the placeholder profile (`profileFromMeasurements`); saving measurements returns the saved measurements only.
2. `ProfileMeasurements` reads the user's saved measurements; the form with defaults appears only when none are saved.
3. `ProfileAvatar`: no avatar means the Generate button; an avatar shows the viewer, dates, the stale banner (from the server flag) and Regenerate; when the server returns an active job (also after a reload or in another tab), show only the progress screen with no Generate or Regenerate button, keep polling, and return to the viewer or the failure message when the job ends.
4. Invalidate the avatar queries after saving measurements and after a job ends. Remove the viewer's cached stale-header key; the stale banner uses the server flag only.
5. Use the four real job states with one plain label each; remove the legacy states.
6. Replace the five-segment bar, the rotating sentences and the preference questions with a simple waiting view and an "about a minute" note, and remove every "90 seconds" text (B52).
7. Map each `error_code` and each request error (no measurements, service unavailable, other) to a plain message.
8. Remove the made-up profile fields (`avatarLabel`, `version`, `engineVersion`, `previewAssetUrl`, unused `measurements` and `unitsPreference` on the avatar type) and the "Engine" row. Remove the inches option from the measurement form (metric only for now; B54).
9. Add zoom limits to the 3D viewer: a minimum and maximum camera distance, and no panning, so the avatar cannot be zoomed out to a speck or into the body (B42). Check the Studio stage that shares the viewer.
10. (B44, approved 2026-10-19) Remove the fake version and engine fields and their checks from the avatar, try-on, looks and analytics code (the hard-coded `avatarProfileVersion`, `engineVersion` and `appVersion` values), and delete the dead frontend code listed in B44. In `Studio.tsx` make only the edits that the removed fields force (the "older avatar" notice and the look filter go away); every other Studio change is recorded in B55 and not done here. Do this in one pass, since the try-on and Studio code reads the same fields.
11. Fix the delete text (B5). Lock the Generate and Regenerate button the moment it is clicked (disabled until the server answers), so a double click sends one request (B12). Change the guest destination to the measurements page and fix the "Setting up a guest avatar" label (B23).
12. (B49, decided 2026-10-19) In the measurements form, compare the entered values with the saved ones (as numbers, so "175" equals "175.0"). If nothing changed, disable Save or show "No changes" and send no request. The backend check in Phase 2 step 11 stays as the safety net.

### Phase 5: End-to-end check on the live stack [B19]

**Goal**: confirm the whole website path works after Phases 2 to 4.

**Steps**:

1. Start Redis, the backend, the worker, the frontend, and CLO with the plugin running.
2. Run the Manual Verification Checklist below with a new incognito guest, then with an existing user (and a female user if Phase 0 added support).
3. Record what passed and what failed in `02-issues.md`.

### Phase 6: Update the documentation to the new code status

**Goal**: bring the Markdown files in line with the code as it is after Phases 0 to 5. Documentation is updated only here, not earlier.

**Rules**:
- Check every statement against the actual code (open the file, search the code, run the command). Do not rely on memory or on what an older document says.
- Do not update very old documents: everything under `.claude/` and the older folders under `.agent/` (for example `website-launch`, `website-launch-2`, `clo-avatar-vto`, `clo-research`, `cv-course-project`, and the files `.agent/saumy/00-…`, `01-…`, `02-…`). They stay as a historical record.

**Steps**:

1. Build the list of Markdown files to check. Search all `.md` files outside `.claude/` and the older `.agent` folders, and search them for the names this plan changes (for example `pipeline_version`, `clo_avatar_avt_path`, `body_shape_type`, `avatar_profile_id`, `source_job_id`, `generated_at`, `measurement_snapshot`, `failure_reason`, the old job-state names, `Redis connection`, worker env settings).
2. Expected candidates: the three files in `.agent/saumy/10_03/18-10-website/`, `.agent/saumy/10_03/05-clo-startup-and-editor-automation.md` and `06-avs-route-performance-and-changes.md`, `worker/README.md`, `website/backend/README.md`, `clo_avatar_generation/README.md` and `summary.md`, `SETUP.md`, and any other README that names the changed fields.
3. For each file on the list, compare its statements with the code and fix the ones that no longer match. Record each file as checked, with a note of what changed or "no change needed".
4. Update `01-avatar-workflow-and-reference.md` sections 2, 3, 5 and 6 (flows, CLI versus website, data layout) to the final code.
5. Update `02-issues.md`: fill in the Status column of every table (solved with the date, partially solved, deferred, still open) and write what was done.
6. Update the top status and date lines of this plan, `01`, `02`, and every other file changed in this phase.
7. Show you the list of files checked and changed before closing the phase.

## Postponed items (not part of the execution; each needs your decision first)

1. Health checks: decide which of the existing checks to keep and how to combine them (B14, B39).
2. Out-of-range measurements: the warning or limits, and whether to widen the model's range (B27).
3. Skin colour: a plugin endpoint to set a solid skin texture, tested through the GLB export (B34).
4. Version folders: the long-term policy for old avatar versions (B33).
5. Plugin pop-up and CLO update prompt (B21).
6. Backend and CLO field-name matching (B41).
7. The worker reading Mongo directly (AR1) stays as it is.
8. Recorded in `02-issues.md` for later and not part of this plan: Redis exposure (B43), push instead of polling (B45), delete and clean-up problems (B46 to B48), automated tests (B50), `body_shape_type` in the legacy path (B51), download size (B53), adding inches back (B54), Studio problems (B55), the legacy `measurements` collection, the versioned upload folders and the two run counters (parts of B56 that the terminal runs depend on).

## Dependencies

- Phase 0 comes first; its outcome feeds the models and validation in Phase 2.
- Phase 1 follows. Phases 2, 3 and 4 follow in that order, because the frontend depends on the API shape and the worker on the models.
- Phase 5 needs Phases 2 to 4. Phase 6 comes last.
- Phase 0 depends on you downloading the female data.
- Running the website path needs Redis, Mongo, CLO 2026.1.224 with the plugin started, and the worker; the CLO app must stay on the version the plugin was built for (`/health` shows `host_matches_sdk`).

## Expected Outcomes

- The female decision is written down and the backend handles both genders.
- Old web avatar data is gone and no stored avatar is out of sync with the code.
- The avatar and job documents hold only the agreed fields; the measurements page reads the real saved measurements.
- A new user sees the Generate button after saving measurements; an existing user sees their avatar, and an accurate "measurements changed" banner right after saving.
- A failed or offline run shows a plain message, not pipeline text.
- The worker no longer needs unrelated backend settings and no longer quits after idling.
- Stored paths are relative to the repo root and defined in one shared place.
- No made-up version or engine fields remain in the avatar, try-on, looks or analytics code.
- Saving unchanged measurements does not trigger the "measurements changed" banner.
- The Markdown files outside the old folders match the code.

## Manual Verification Checklist

*(You run these; I do not verify them automatically unless you ask.)*

1. New incognito guest: save measurements, then open the Avatar tab. The Generate button shows, not an empty viewer.
2. Press Generate: the page moves from waiting to the viewer. The new run appears in `clo_avatar_generation/output/` and a version folder in `dev_upload/avatars/<user>/`.
3. Reload the page during a run: it resumes showing progress.
4. Press Generate twice quickly: only one job runs.
5. Edit one measurement and save: the Measurements page shows the new value at once, and the "measurements changed" banner appears on the Avatar tab without a reload.
6. Regenerate: a new version folder appears and the viewer shows the new avatar.
7. Stop the worker and press Generate: the message is plain and says what is wrong.
8. Close CLO and press Generate: the job fails quickly with a plain message.
9. Leave the worker idle for an hour, then generate: the job still runs.
10. Open `/profile`, the Avatar tab and the Measurements tab as an existing user: no field shows made-up values (no "NEW", no engine row).
11. Check the Mongo documents: `avatar_profiles` and `avatar_jobs` have only the agreed fields.
12. If Phase 0 added female support: repeat checks 1 to 6 with a female user.
13. The measurement form shows metric only (no inches option).
14. Open the Measurements tab and press Save without changing anything: no request is sent (or the backend returns the same version), and the Avatar tab shows no "measurements changed" banner.
15. In Mongo, `avatar_glb_path` starts with `dev_upload/` (relative to the repo root, not absolute) and `clo_avatar_avt_path` no longer exists.
