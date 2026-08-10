# Step 5 - Save the avatar to `dev_upload/`/`live_upload/`

**Status:** implemented and live-verified against real CLO3D pipeline output (2026-08-08). **Note:** storage now splits by `APP_ENV` between `dev_upload/` (default, local/dev testing) and `live_upload/` (production only, reserved — no working path for a Render-hosted backend to receive files exists yet) — see [22-remove-demo-live-mode-and-upload-split.md](22-remove-demo-live-mode-and-upload-split.md). All the `live_upload/`-specific history below predates that split; the same logic now applies to whichever root `APP_ENV` selects.
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [11-step4-avatar-pipeline-invocation.md](11-step4-avatar-pipeline-invocation.md)

## Goal

Move a completed avatar run's final artifacts out of the pipeline's own dev/debug `output/` folder and into a stable, versioned, production-facing location the website can serve from directly — without losing the ability to trace back to the full debug run if something looks wrong later.

## Current state

Nothing here exists yet — today, avatar runs only ever write into `clo_avatar_generation/output/<user_id>-<run_number>/`, which is the pipeline's own dev/QA trail, not meant to hold real pilot users' production data (explicitly decided not to reuse it — see doc 05).

## Remaining work

1. **Create `live_upload/avatars/` at the repo root**, sibling to `clo_avatar_generation/`, `product_ingestion/`, `clo_vto/`, `website/`.
2. **Add a local `.gitignore`** inside `live_upload/` — same pattern as `clo_avatar_generation/.gitignore` (`avatars/*` ignored, tracked `.gitkeep`). Also extend the **repo-root** `.gitignore` to cover `*.avt` and `*.zprj` — currently only `*.dxf`/`*.glb`/`*.gltf`/`*.obj`/`*.svg`/`*.mtl` are covered there, `.avt`/`.zprj` are not.
3. **Worker-side copy logic** (part of the Step 0 worker's avatar task, not a separate service): after a successful pipeline run —
   - compute the next version number for this `user_id` (next integer under `live_upload/avatars/<user_id>/`, similar logic to `clo_avatar_generation/avatar_runtime/run_manifest.py::get_next_run_number`, but scoped to `live_upload/` instead of the pipeline's own output root)
   - create `live_upload/avatars/<user_id>/<version>/`
   - copy `avatar.zprj`, `avatar.avt`, the new `.glb`/`.gltf` (per Step 4's naming decision), and `run.log`
   - write `run_manifest.json` recording: source run id (`<user_id>-<run_number>` from `clo_avatar_generation/output/`), timestamp, pipeline step results summary — enough to trace back to the full debug log without duplicating it
4. **Add the new fields to `AvatarProfileDocument`** (`avatars/models.py`):
   ```python
   avatar_glb_path: str | None = None          # relative path under live_upload/avatars/...
   source_measurements_version: int | None = None
   generated_at: datetime | None = None
   clo_run_id: str | None = None                # e.g. "u_001-004", for tracing to clo_avatar_generation/output/
   ```
5. **Populate these fields when the worker marks the job `ready`** — this is the same write that updates `avatar_jobs.state` and `avatar_profiles`, just with the new fields included.
6. Since `avatar_profiles` is one-per-user (unique index on `user_id`), each regeneration **updates** that single doc's path/version fields to point at the newest version — older versions stay on disk (per this round's "keep versions" decision) but aren't referenced by the live profile doc unless you later add a "restore an old version" feature (not currently planned).

## Files touched

- new: `live_upload/avatars/.gitkeep` + `live_upload/.gitignore`
- root `.gitignore` — add `*.avt`, `*.zprj`
- worker task code (from Step 0) — the copy/version logic
- `website/backend/src/avatars/models.py` — new fields on `AvatarProfileDocument`

## Verification

- Two successive avatar generations for the same user produce `live_upload/avatars/<user_id>/001/` and `.../002/`, both fully intact, neither overwriting the other.
- `run_manifest.json` in each version folder correctly points to its source `clo_avatar_generation/output/...` run.
- `avatar_profiles` doc's path fields always point at the *latest* version after a regeneration.
- Confirm nothing under `live_upload/` gets committed to git (check `git status` after a test run).

## Execution Log

### 2026-08-08 - Implemented

- `live_upload/avatars/.gitkeep` + `live_upload/.gitignore` (`avatars/*` ignored, `.gitkeep` tracked — same pattern as `clo_avatar_generation/.gitignore`). `tryon/` and `catalog/` subtrees from doc 05's full layout intentionally **not** created yet — those belong to Steps 9/10, out of scope for this pass.
- Root `.gitignore` — added `**/*.avt`, `**/*.zprj` (previously only `.dxf`/`.obj`/`.mtl`/`.glb`/`.gltf`/`.svg` were covered).
- New `worker/live_upload.py` — `save_avatar_version(user_id, *, run_id, run_dir, zprj_path, avt_path, glb_path, step_results) -> SavedAvatarVersion`. Computes the next integer version under `live_upload/avatars/<user_id>/` (mirrors `run_manifest.py::get_next_run_number`'s logic, scoped to `live_upload/` instead of the pipeline's own `output/`), copies whichever of `avatar.zprj`/`avatar.avt`/`avatar.glb` are actually present (GLB may be `None` — step_12 is non-blocking), copies `run.log`, and writes `run_manifest.json` (`source_run_id`, `source_run_dir`, timestamp, full `step_results` list — the pointer back to the debug trail doc 05 asked for). Never overwrites a prior version.
- `avatars/models.py::AvatarProfileDocument` — added `avatar_glb_path` (relative to `live_upload/`, e.g. `"avatars/<user_id>/001/avatar.glb"`, for Step 6's serving route), `generated_at`, `clo_run_id`. Also added `source_measurements_version` but it's **always written as `None` for now** — `measurements_version` doesn't exist on `MeasurementDocument` yet (doc 09's own still-open "Remaining work" item), so there's nothing correct to populate it with. Left in place per doc 05's DB field list so Step 6's staleness check has the field to read once doc 09 lands, treating `None` as "unknown" per doc 09's own guidance.
- **Repointed `clo_avatar_avt_path`**: previously stored the raw `clo_avatar_generation/output/<user_id>-<run>/` path; now stores the versioned `live_upload/avatars/<user_id>/<version>/avatar.avt` copy instead. `run_tryon_render` (already reads this field to locate the avatar for VTO) needed no changes — it just resolves whatever path is stored.
- `worker/tasks.py::_run_avatar_job` — after `_materialize_profile`, calls `save_avatar_version(...)` and writes `clo_avatar_avt_path`, `avatar_glb_path`, `generated_at`, `clo_run_id` onto the profile doc in the same update. Module docstring updated to reflect the new scope (Step 0 + avatar-side 4/5; try-on still Step-0-only).
- **Verified**: a standalone unit test of `save_avatar_version()` against temp files (not a real CLO run) — confirms version numbering starts at 1 and increments without overwriting, files copy correctly, `run_manifest.json` is well-formed, and a `None` GLB path (simulating a failed export) doesn't crash and leaves `glb_relative_path` as `None`. Also confirmed `worker.tasks` and the full `clo_avatar_generation.avatar_runtime.pipeline` module import cleanly with all the new wiring, and the backend (`from src.main import app`) still imports cleanly with the new `AvatarProfileDocument` fields (all `None`-defaulted, no migration needed for existing docs).
### 2026-08-08 - Live-verified against real CLO3D pipeline output

Ran `save_avatar_version()` directly (not yet through the RQ worker — Redis/Mongo weren't spun up for this pass, see "Remaining work") against the two real runs from doc 11's live test:

- `save_avatar_version("u_001", run_id="u_001-062", ...)` → created `live_upload/avatars/u_001/001/`, copied `avatar.zprj`/`avatar.avt`/`avatar.glb` (real ~81KB GLB, not a stub) + `run.log`, wrote `run_manifest.json`. All copied files confirmed to exist on disk after the call.
- `save_avatar_version("u_001", run_id="u_001-063", ...)` → created `live_upload/avatars/u_001/002/` — confirmed via SHA-256 hash comparison that `001/avatar.avt` was byte-for-byte unchanged after the second call (no overwrite), and `live_upload/avatars/u_001/` now contains exactly `["001", "002"]`. This is doc 05's exact "two successive generations" verification criterion, satisfied with real pipeline artifacts rather than synthetic test files (the earlier synthetic-file unit test from this doc's first execution-log entry above already covered the same logic in isolation).

**Not yet verified**: the full worker path (`worker/tasks.py::run_avatar_job` → Redis/RQ → this same `save_avatar_version()` call → `avatar_profiles` Mongo doc updated with `avatar_glb_path`/`generated_at`/`clo_run_id`) — this pass called `save_avatar_version()` directly against real artifacts to isolate and verify the storage logic itself, without also standing up Redis + the Mongo Atlas connection in the same session. The wiring in `worker/tasks.py` was confirmed importable/syntactically correct (see 07-step0-worker-queue.md's existing worker verification and this doc's earlier import checks), but an actual `POST /avatars/generate` → job → `avatar_profiles.avatar_glb_path` round trip through the real queue hasn't been exercised since these Step 4/5 changes landed.

### 2026-08-08 - Re-verified after doc 11's GLB packing fix

The first live test (`u_001-062`/`u_001-063`) copied CLO's *raw*, not-actually-openable glTF-separate export into `live_upload/` — those two versions were broken (confirmed by the user's CLO3D re-import failing with "Invalid GLB header"). Deleted both (`rm -rf live_upload/avatars/u_001` — safe, they were this session's own test artifacts, not user data) after doc 11's fix landed, then re-ran `save_avatar_version()` against the corrected `result_avatar_packed.glb` from run `u_001-064`: produced a clean `live_upload/avatars/u_001/001/avatar.glb`, 30,521,080 bytes, confirmed to start with the real `glTF` binary magic header. No change was needed in `worker/live_upload.py` itself — it already just copies whatever `ctx.avatar_glb_path` resolves to, and that field now correctly points at the packed file instead of the raw one.

**2026-08-08, user-confirmed**: `live_upload/avatars/u_001/001/avatar.glb` opens correctly in both VS Code's 3D preview and CLO3D's own import — see doc 11's execution log for the same finding. The file this doc's storage logic produces is genuinely usable, not just structurally valid.

### 2026-08-08 - Full worker round trip live-verified

Ran the real path end to end against the actual running stack (Docker backend + Redis, native worker, real CLO3D): created a guest account via `POST /api/v1/auth/guest`, submitted measurements via `PUT /api/v1/measurements/me`, called `POST /api/v1/avatars/generate` with the backend temporarily in `AVATAR_ENGINE_MODE=live` (see caveat below). The job (`engineMode: "live"`) was picked up off the real `clo` Redis queue by the native worker (confirmed in its log: `worker.tasks.run_avatar_job(...)`), ran the full 12-step pipeline against real CLO3D, and reached `state: "ready"` in ~86 seconds. `GET /api/v1/avatars/profile` confirmed a real `avatar_profiles` doc with the submitted measurements and a valid `avatarProfileId` — the full chain (backend → Redis → worker → CLO3D → `live_upload/` → Mongo → backend read) works.

**Caveat worth recording**: `AVATAR_ENGINE_MODE` is a process-wide backend setting, not scoped per-request — flipping it to `live` (via a temporary `docker-compose.yml` environment override, reverted immediately after the test) affects every request the shared local backend handles, not just the test's own guest account. This briefly disrupted the user's own concurrent use of the app. Any future live-mode testing against the shared dev backend should flag this *before* flipping the switch, not after.

### 2026-08-09 - `dev_upload/`/`live_upload/` split via `APP_ENV`

Part of [22-remove-demo-live-mode-and-upload-split.md](22-remove-demo-live-mode-and-upload-split.md). Changes:

- `worker/live_upload.py` — `LIVE_UPLOAD_AVATARS_ROOT` hardcoded module constant replaced with `DEV_UPLOAD_AVATARS_ROOT`/`LIVE_UPLOAD_AVATARS_ROOT` plus a new `_avatars_root()` function reading `APP_ENV` from the worker process's environment (`os.environ.get("APP_ENV", "development")`) — `"production"` selects `live_upload/`, anything else (including unset) defaults to `dev_upload/`. `_next_version()` and `save_avatar_version()` both take the resolved root instead of the old hardcoded constant.
- New `dev_upload/avatars/.gitkeep` + `dev_upload/.gitignore`, identical pattern to `live_upload/`'s.
- Cleared `live_upload/avatars/u_001/` and `live_upload/avatars/g_4e1a14ccadb2fd2f/` — both were this session's own test data (from the live tests logged above), not real production data. `live_upload/` now starts clean, reserved for real production output once a Render-hosted backend has a way to receive it (still not built — see doc 22's "Out of scope").
- `website/backend/src/config.py` — added `app_env: Literal["development", "production"] = "development"` (mirrors the frontend's `VITE_APP_ENV`). Not yet consumed by the backend itself — read directly by the worker process today; Step 6's serving route will need it once built.
- `AvatarProfileDocument.clo_avatar_avt_path`/`avatar_glb_path` docstrings updated to say "relative to whichever upload root is configured" instead of hardcoding `live_upload/`.

**Verified**: a standalone test confirming `_avatars_root()` resolves to `dev_upload/` when `APP_ENV` is unset or `"development"`, and to `live_upload/` when `APP_ENV="production"`.

## Remaining work (post-implementation)

- `source_measurements_version` stays `None` until doc 09's `measurements_version` field is added — tracked there, not here.
- Step 6 (serving route) is the natural next step now that both the export and the storage logic are live-verified: `GET /api/v1/avatars/profile/glb` resolving `avatar_glb_path` against a new upload-root setting (mirroring `app_env`), per doc 05's "Serving strategy".
- The Render production path is still unbuilt (object storage bridge) — `live_upload/` stays empty in practice until that lands, per doc 22.
