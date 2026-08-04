# 06 - Avatar generation + VTO live pipeline: implementation status

**Status:** planned, not yet executed
**Created:** 2026-08-04
**Companion to:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) — read that first for the overall shape; this file breaks the same flow into buildable, ordered steps.

Each section below is "done today" vs. "remaining" — grounded in what's actually in the repo right now, not assumed. Build in the order listed; later steps depend on earlier ones (mainly Step 0, the worker/queue, which everything else needs).

---

## Step 0 — Shared infra: the job worker/queue

Nothing in `live` mode works — avatar or try-on — until this exists. Both `avatars/engine.py` and `tryon/engine.py` currently just `raise ServiceUnavailable(...)` in live mode. This is the actual Phase 0.

**Done:**
- The reasoning for *why* a lightweight single-worker queue (Redis + RQ, concurrency = 1) is the right shape is already recorded in doc 01 — CLO itself is single-threaded regardless of what queueing sits in front of it, so this isn't a parallelism decision, just a "don't hold an HTTP request open for minutes" decision.
- The `queued → processing → ready → failed` state shape already exists end-to-end in demo mode (`avatar_jobs`, `tryon_renders`) — the live worker just needs to drive real transitions instead of time-based fake ones.

**Remaining:**
1. Add Redis to `docker-compose.yml` (was explicitly deferred in doc 01/02 — "not part of this phase" — now it's time).
2. Build the actual worker process: a native Windows Python script (uses the repo's `.venv` directly, not containerized) that:
   - polls/consumes the queue
   - for avatar jobs: loads the `measurement_snapshot`, calls into `clo_avatar_generation`'s pipeline (importing `run_avatar.py`'s pipeline function, non-interactive)
   - for try-on jobs: loads the avatar + catalog pattern paths, calls into `clo_vto`'s pipeline
   - writes results to `live_upload/...` (Step 5 / Step 9 below)
   - updates the Mongo job doc on completion/failure
3. Wire `avatars/engine.py::start_job` and `tryon/engine.py::start_render` to enqueue onto this instead of raising `ServiceUnavailable`.
4. Containers reach the CLO plugin/worker via `host.docker.internal:50505` if anything containerized ever needs to call it directly (per doc 01) — likely not needed if only the native worker talks to CLO and the backend only talks to Mongo + the queue.

---

## Step 1 — OAuth login, email saved

Covered in full in `03-backend-behavior-plan.md` (Google OAuth plan + Section 8). Referenced here only because every later step assumes a `user_id` already exists.

**Done:** backend `users` model, guest identity, session issuance all exist.
**Remaining:** Google OAuth routes/config themselves — see doc 03, not repeated here.

---

## Step 2 — Measurements form → MongoDB

**Done — fully built, no gaps found:**
- `POST`/`PATCH` on `measurements` collection, one doc per `user_id`, upserted (`website/backend/src/measurements/service.py`).
- Schema (`MeasurementDocument`) already documented as byte-compatible with what the CLO pipeline reads.
- Validation (positive numbers, gender/accuracy enums, hex color pattern) already in place.

**Remaining:**
1. Add `measurements_version: int` field, incremented on every `submit`/`patch` — needed by Step 6's staleness check, not by the form itself.

---

## Step 3 — "Create avatar" click → job creation

**Done — fully built in demo mode:**
- `POST /api/v1/avatars/generate` (`avatars/routes.py`) already creates an `avatar_jobs` doc with a `measurement_snapshot` taken at creation time (so a later measurement edit can't change what an in-flight job builds from).
- `GET /api/v1/avatars/jobs/{job_id}` already exists for polling.

**Remaining:**
1. Nothing structural — this step becomes "live" automatically once Step 0's worker is wired to `avatars/engine.py::start_job`.

---

## Step 4 — Avatar generation pipeline invocation (worker → CLO)

**Done:**
- The 11-step Step 1 pipeline (`clo_avatar_generation/avatar_runtime/pipeline.py`) already runs end-to-end against real measurements (verified in doc 01's Phase 2 testing against golden user `u_001`).
- Plugin `/export` endpoint confirmed working with a real avatar loaded (doc 01 Phase 2 testing).

**Remaining:**
1. **`step_12_export_glb.py` doesn't exist yet** — the pipeline currently stops at `step_11_save_outputs` with no GLB export step. This is the one concrete new pipeline file needed (mirrors `clo_vto/native_vto/step_11_export_note.py`'s existing export pattern).
2. Resolve the GLB/glTF naming decision (doc 05's "open naming decision") before writing this step, since it decides the output filename/loading convention.
3. Register the new step in `pipeline.py`'s step list.
4. Add `export_avatar_glb()` to `clo_avatar_generation/avatar_runtime/client.py` (mirrors `native_vto/client.py`'s existing `export_garment()`).

---

## Step 5 — Save the avatar to `live_upload/`

**Done:** none of this exists yet — no code writes anywhere outside `clo_avatar_generation/output/` today.

**Remaining:**
1. Create `live_upload/avatars/` folder + local `.gitignore` (matches the pattern `clo_avatar_generation/.gitignore` already uses for its own `output/`).
2. After a successful pipeline run, worker copies `.zprj`, `.avt`, the new `.glb`/`.gltf`, and `run.log` into `live_upload/avatars/<user_id>/<version>/` (version = next integer for that user, never overwritten).
3. Write `run_manifest.json` in that folder, pointing back to the source `clo_avatar_generation/output/<user_id>-<run_number>/` for full debug traceability.
4. Add the new fields to `AvatarProfileDocument` (`avatar_glb_path`, `source_measurements_version`, `generated_at`, `clo_run_id`) and populate them when the job completes.

---

## Step 6 — Show the avatar on the website, without reloading/re-running CLO

**Done:** `GET /api/v1/avatars/profile` already exists and returns the profile shape — just needs the new path field once Step 5 exists.

**Remaining:**
1. New route `GET /api/v1/avatars/profile/glb` (`avatars/routes.py` + `controller.py`), same `FileResponse` + ownership-check pattern `capture/controller.py::get_photo` already uses.
2. Bind-mount `live_upload/` read-only into the backend container (`docker-compose.yml`), add `live_upload_dir` to `config.py` (same shape as the existing `uploads_dir`).
3. `Cache-Control: private, max-age=<long>, immutable` response header, safe because the path is already version-qualified.
4. Frontend: lazy-loaded `<model-viewer>` (or equivalent) component, per doc 03 Section 7's SPA/3D guidance — not loaded as part of the main app bundle, not loaded during route transitions.
5. Staleness check: compare `avatar_profiles.source_measurements_version` to the live `measurements.measurements_version`; if they differ, show a "regenerate?" prompt instead of auto-regenerating.
6. Frontend never calls avatar generation on page load — only on the explicit "Create avatar" / "Regenerate" actions.

---

## Step 7 — Garment catalog (premade clothes)

**Done:**
- `sizes` collection + read-only `GET` catalog routes already exist (`catalog/service.py`, `catalog/routes.py`), with `cloth_id`/`cloth_label` grouping fields already in the schema.
- 10 seeded demo sizes exist (`website/backend/scripts/seed_sizes.py`) — pure measurement metadata, no garment styling behind them yet.

**Real gap found (not just missing fields):** every catalog entry today, regardless of `cloth_id`, renders using the same single hardcoded placeholder pattern set (`clo_vto/default_panels/dxf/`). `cloth_id` is stored but never used to pick a different pattern. "2-3 distinct t-shirt styles" doesn't work until this is wired.

**Remaining, per this round's decision to pre-generate before launch:**
1. Run `product_ingestion` (Step 2) once per real garment style/photo ahead of launch — produces `product_ingestion/output/<cloth_id>-<size_id>-<run_number>/` as usual.
2. Copy the chosen final pattern set + a product thumbnail into `live_upload/catalog/<cloth_id>/<size_id>/`, named properly (not raw run-numbered filenames) — per this round's decision, "with proper name and in the live upload folder also."
3. Add `pattern_asset_path` and `thumbnail_url` fields to `SizeDocument`, populated to point at the `live_upload/catalog/...` paths above.
4. Update the seed/catalog-population script so these pre-generated entries are what's actually seeded for launch, not the current placeholder measurement-only rows.
5. Change `clo_vto`'s pipeline to load patterns from the selected catalog item's `pattern_asset_path` instead of the `use_default_panels` flag/hardcoded folder.
6. Frontend: catalog browsing page needs no CLO involvement at all — pure Mongo read + thumbnail image.

---

## Step 8 — User selects avatar + garment + size, requests try-on

**Done — fully built in demo mode:**
- `POST /api/v1/tryon/sessions` and `POST /api/v1/tryon/sessions/{session_id}/renders` already exist, capturing a `garment_snapshot` of the catalog doc at request time and referencing `avatar_profile_id`.
- The "Hanger no-recompute" comment already in `tryon/models.py` describes exactly the cache-reuse behavior needed in live mode.

**Remaining:**
1. Before enqueueing a live render, check for an existing `ready` `tryon_renders` doc matching `(avatar_profile_id, size_id)` where the avatar hasn't been regenerated since — serve that instead of recomputing. This is the actual "reduce CLO load" mechanism for try-on.
2. Wire `tryon/engine.py::start_render` to Step 0's worker/queue instead of raising `ServiceUnavailable`.

---

## Step 9 — VTO pipeline invocation (worker → CLO)

**Done:**
- `clo_vto`'s 12-step native pipeline exists and is wired for the current single default-panel t-shirt.
- GLB export (`step_11_export_note.py`) and texturing (`step_12_texture_glb.py`) already exist in code.

**Blocking prerequisite found, not yet resolved:**
- `step_12_texture_glb.py` loads the exported file as binary `.glb` (`GLTF2().load(...)`, binary path) — but the plugin actually produces JSON-embedded glTF (same bug found in doc 01's avatar GLB testing). Because this step's failure mode is silently non-blocking by design, **a "successful" pipeline run today doesn't guarantee a usable textured GLB came out.** Must verify this against a real run and fix the loader (or switch to `.gltf` naming) before trusting any output from this step.

**Remaining:**
1. Resolve the blocking prerequisite above.
2. Once Step 7's catalog wiring exists, point pattern loading at `live_upload/catalog/<cloth_id>/<size_id>/` instead of `default_panels/dxf/`.
3. Confirm textures apply correctly (not grey/untextured) against a real garment + real avatar, per doc 01's Phase 3 verification plan.

---

## Step 10 — Save + serve the try-on result

Mirrors Steps 5 and 6 exactly, for try-on instead of avatar.

**Remaining:**
1. `live_upload/tryon/<user_id>/<size_id>/<version>/` — `.zprj`, `.avt`, `.glb`/`.gltf`, `run.log`, `run_manifest.json` pointing back to `clo_vto/output/...`.
2. Add `result_glb_path` and `clo_run_id` fields to `TryonRenderDocument`.
3. New route `GET /api/v1/tryon/sessions/{session_id}/renders/{render_id}/glb`, same `FileResponse`/ownership/cache-header pattern as Step 6.
4. Same frontend lazy-load/dispose discipline as the avatar viewer — never two full 3D viewers mounted at once (avatar + try-on side by side is a specific risk called out in doc 03 Section 7).

---

## Suggested build order

1. Step 0 (worker/queue) — nothing else works without it.
2. Step 4 (avatar GLB export) + the naming decision — needed before Step 5/6 can be tested against a real file.
3. Steps 5 + 6 (avatar storage + serving) — gives a complete, demoable avatar flow end to end.
4. Step 7 (catalog pre-generation) — can happen in parallel with 1-3 since it doesn't depend on the worker.
5. Step 9's blocking prerequisite (GLB texturing bug) — verify/fix before relying on any try-on output.
6. Steps 8 + 10 (try-on request + storage/serving) — completes the full pilot flow.

## Execution Log

Not started.
