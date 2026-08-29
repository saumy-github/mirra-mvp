# 04 — Lane 1 (CLO): repoint measurement fetch, serve the GLB, verify live

**Status**: planned, not started. Written 2026-08-15.
**Covers**: `02-remaining-work.md` items **A1, A2, A3**.
**Agent assignment**: exactly ONE agent — `subagent_type: mirra-lane-clo` (Sonnet, medium effort) — working in the **primary checkout** (`C:\D-drive-data\mirra-mvp`), never a worktree; see "Why not a worktree" below. No other agent may touch CLO, `worker/`, `clo_avatar_generation/`, or `clo_vto/` while this runs.

> **You are running alongside Lanes 2 and 3 (2026-08-19).** Both are website lanes in this same checkout, kept apart from you by file ownership only. Two consequences:
> - **Shared resources belong to the parent session, not to you** (user decision, 2026-08-19 — the deliberately safe option). **You do not run `docker compose build/up/down/restart`, and you do not rebuild the CLO plugin.** When your work needs a rebuild or restart — and A2's compose mount change does — **stop and ask the parent, then wait.** `docker compose exec` against an already-running stack is read-only and fine.
> - This directly affects your sequencing: you cannot rebuild-then-run at will. Land the code changes, ask the parent for the rebuild/restart, wait for confirmation, **then** do the A3 live run.
> - **Run verification once, at the end** — not after each edit. `py_compile`, the import check and the smoke test are end-of-work checks. Re-running a specific check while debugging a specific failure is fine; routine after-every-change checking is not.

## Why these three together

They are one causal chain, and splitting them across agents would violate concurrency=1 anyway:

- Today a real signed-in user who saves measurements and hits "generate" **fails**. The website writes to `user_measurements`; the pipeline reads `measurements`. A1 is the difference between "avatar generation works for real users" and "avatar generation works only for CLI golden users."
- Even once generation succeeds, the resulting GLB is unreachable from the browser — there is no route. A2 is the difference between "a file exists on disk" and "a user sees their avatar."
- A3 is the only thing that proves either actually worked. Per `01`, static checks are not verification in this territory.

## Confirmed starting state (verified in code 2026-08-15, not assumed)

- `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py:150` imports `mirra_measurements.db.get_measurements_collection` and reads the **old** `measurements` collection. No `user_measurements` path exists anywhere in the pipeline.
- `website/backend/src/avatars/models.py:64` already has `avatar_glb_path: str | None`, documented as "relative to whichever upload root is configured (e.g. `avatars/<user_id>/001/avatar.glb`) — Step 6's serving route resolves this against that root." **The field exists; the route does not.**
- `website/backend/src/avatars/routes.py` has exactly four routes: `POST /generate`, `GET /jobs/{job_id}`, `GET /profile`, `DELETE /profile`.
- `worker/live_upload.py:35-38` resolves the root: `APP_ENV == "production"` → `live_upload/avatars`, anything else (including unset) → `dev_upload/avatars`.
- `website/backend/src/config.py:31-35` explicitly notes `APP_ENV` is **"not yet consumed by the backend"** — A2 has to add that consumption.
- `docker-compose.yml` (repo root) mounts only `./website/backend/src:/app/website/backend/src` into the backend container. The upload root is **not** mounted — A2 must add it.
- **Field names already line up.** `user_measurements`' `UserMeasurementFields` uses exactly the names the pipeline's contract expects (`height_cm`, `weight_kg`, `shoulder_width_cm`, `chest_circumference_cm`, `waist_circumference_cm`, `hip_circumference_cm`, `leg_length_cm`, `bust_circumference_cm`, `under_bust_circumference_cm`) plus `gender`. This was a live risk; it checked out. The extra fields (`accuracy`, `units_preference`, `measurements_version`, `body_shape_type`, `skin_tone_hex`) are additive and harmless to the validator.

## A1 — measurement fetch: try `user_measurements`, fall back to `measurements`

### The user's ruling, 2026-08-19 — this is additive, and nothing is removed

Both collections are **permanent and intentional**, not a migration in progress:

- **`measurements`** — for CLI-mode testing of CLO3D work (golden users, `seed_measurements.py`). Kept.
- **`user_measurements`** — for the website, in **both dev and production**. Kept.

> *"we have to keep both of them, so wherever our pipeline is reading from the measurements model we have to add the user_measurements model also, and not remove anything."*

So this is strictly **additive**. **Do not delete, rename, deprecate, or stop writing to anything.** Do not "clean up" the old accessor, do not migrate documents between collections, and do not touch `seed_measurements.py` (it is a *writer* for golden users, not a read site). The title's word "fall back" describes lookup order only — it does not imply the old collection is on its way out. It is not.

**Every read site — enumerated 2026-08-19, so you do not have to go looking:**

| Site | What it reads | Action |
|---|---|---|
| `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py:150,159` | `get_measurements_collection()` — body measurements, the live pipeline fetch | **This is the one to change.** |
| `product_ingestion/legacy/generate_patterns_clo3d.py:31`, `legacy/generate_for_avatar.py:55` | `get_avatar_collection` (an alias of the same accessor) | **Out of scope** — `legacy/`. Leave alone. |
| `mirra_measurements/seed_measurements.py:200` | writes golden users into `measurements` | Not a read site. Leave alone. |
| `product_ingestion/run_product_ingestion.py:42` | `get_sizes_collection` | Garment sizes, unrelated collection. Leave alone. |

That leaves exactly one file to modify for A1. If you find yourself editing a second, stop and re-read this table.

Approach (from old-folder doc 23 Part C):

1. In `step_03_fetch_measurements.py`, replace the single `get_measurements_collection()` read with: look up `user_measurements` by `user_id` first; if nothing found, fall back to the old `measurements` collection.
2. Record which collection actually answered in `ctx.measurement_source` (e.g. `mongodb:user_measurements` vs `mongodb:measurements`) so `mongo_snapshot.json` and the run log say where the data came from. Do not collapse both into a bare `"mongodb"` — when a run produces a surprising avatar, the first question will be "which collection fed it."
3. Keep the JSON-file path, the local-snapshot fallback, and every existing error message intact. `run_avatar.py --user-id u_001` (golden users, which live in the old collection) must keep working **unchanged** — that's the regression to watch.
4. `measurements_version` should be carried into the snapshot when present — A2's staleness check depends on it being visible downstream.

Collection accessor: `mirra_measurements/db.py` hardcodes `AVATAR_COLLECTION_NAME = "measurements"` on database `mirratest`. Add a sibling accessor for `user_measurements` on the same client/database rather than opening a second connection.

**Database name: confirmed the same, 2026-08-15 — this was flagged as A1's highest risk and it checked out.** `website/backend/src/config.py:20` declares `database_name: str = "mirratest"`, `mirra_measurements/db.py` declares `DATABASE_NAME = "mirratest"`, and `website/backend/src/db.py:1-3` states it outright: "Async MongoDB client for the shared **mirratest** database. Ported from `mirra_measurements/db.py` (sync) — same database, same [convention]." The website and the pipeline read and write the same database. The only residual is that `database_name` is a Settings field with a default, so a deployment env var *could* override it — worth one glance at the effective setting, not worth treating as an open risk.

**Superseded 2026-08-19**: the old "optional, only if it stays trivial" note about `product_ingestion/run_product_ingestion.py:~42` is dropped — that line reads `get_sizes_collection` (garment sizes), an unrelated collection. Leave it alone. There is no `mirra_measurements` migration to expand into; per the ruling above, both collections stay.

## A2 — `GET /api/v1/avatars/profile/glb`

1. **Backend reads `APP_ENV`.** Add the same resolution `worker/live_upload.py` uses, in backend config: `production` → `live_upload/avatars`, else `dev_upload/avatars`. Do not hardcode one root. Do not duplicate the string literals in three places.
2. **Mount the upload root read-only** in `docker-compose.yml`'s backend service (`:ro`). The container currently cannot see the file at all.
3. **Route**: resolve the path from `avatar_profiles.avatar_glb_path` joined against the resolved root — **never from client input**. Ownership-check against the calling identity. Return 404 (not 500) when the profile has no GLB, since `avatar_glb_path` is legitimately `None` when export failed or hasn't run. Long-cache headers, and the path is version-scoped (`/001/`) so caching is safe.
4. **Staleness**: compare `avatar_profiles.source_measurements_version` against the user's current `user_measurements.measurements_version`. Decide and document what the response does when stale — surface it in the payload rather than silently serving an outdated avatar.
5. Guard against path traversal on the stored value even though it's server-written — resolve and assert the final path stays under the upload root.

**Do not** add a "latest job" lookup route here. That's B4, it lands in these same files, and it's sequenced after this lane merges specifically to avoid the collision.

## A3 — live end-to-end verification

CLO3D is running and the user has confirmed it is available for development use. Still concurrency=1: serialize every CLO call, and do not start a second worker.

The run, as a real signed-in user (not a CLI golden user):
1. Save measurements through the website → confirm the doc lands in `user_measurements`.
2. `POST /avatars/generate` → job enqueued to Redis.
3. Worker picks it up → CLO3D runs → packed GLB lands under `dev_upload/avatars/<user_id>/<version>/`.
4. `GET /api/v1/avatars/profile/glb` serves it.
5. **Open the served bytes in a real GLB viewer.** "The request returned 200" is not verification — this is exactly the standard the original GLB packing bug (doc 11) failed while looking fine by every other measure.
6. Re-run `run_avatar.py --user-id u_001` to confirm the old-collection CLI path still works.

If you start a worker for testing, stop it when done (`Stop-Process` on the PID) or say clearly in the execution log that it was left running and why.

## Verification checklist

- `python -m py_compile` on every touched Python file.
- `python -c "from src.main import app"` import check.
- `docker compose build backend && docker compose up -d backend` — required for the compose mount change to take effect; also required before any `scripts/` change is visible (only `src/` is bind-mounted).
- `docker compose exec backend python scripts/smoke_e2e.py`.
- The A3 live run above. **Nothing short of it counts** for the pipeline changes.

## Why not a worktree

`.env` files are untracked, so a fresh worktree has no `worker/.env` — no `MONGODB_URI`, no `APP_ENV`, no Redis config. The worker cannot start and the live run cannot happen. Pipeline output paths are also repo-root-relative, so a worktree would write to its own `dev_upload/`, not the real one. This lane works in the primary checkout; the parallel website lanes get the worktrees.

## Rules for this lane

- **Never commit.** Not on completion, not as a checkpoint. The user commits manually. See `01-how-ai-should-work.md`.
- Owned files (no other agent may touch these while this lane runs): `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`, `mirra_measurements/db.py`, `website/backend/src/avatars/{routes,controller,service,models}.py`, `website/backend/src/config.py`, `docker-compose.yml`, `website/backend/scripts/smoke_e2e.py`.
- Do not read `.env*` files with any tool. If you need to know whether `APP_ENV` is set in `website/backend/.env.docker.dev`, **ask the user** — do not open it.

## Execution log

**2026-08-19 — A1 and A2 landed, code-complete. A3 blocked on the parent's Docker rebuild/restart, not yet run.**

### A1 — done

- `mirra_measurements/db.py`: added `USER_MEASUREMENTS_COLLECTION_NAME = "user_measurements"` and a sibling accessor `get_user_measurements_collection()` (same client/`mirratest` database as `get_measurements_collection()`, unique index on `user_id`, no second connection). `get_measurements_collection()`, `get_avatar_collection` alias, and everything else in the file is untouched.
- `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`: the live MongoDB branch now tries `get_user_measurements_collection().find_one({"user_id": ...})` first; if that returns nothing, falls back to `get_measurements_collection().find_one(...)`. `ctx.measurement_source` (and `_source` in the logged `mongo_snapshot`) is now `"mongodb:user_measurements"` or `"mongodb:measurements"` depending on which collection actually answered, instead of a bare `"mongodb"`. The JSON-file path, the local-snapshot fallback (both the "Mongo raised" and the "Mongo returned None from both collections" cases), and every existing warning/error message are unchanged in structure — only the fallback warning text was updated to say "in either user_measurements or measurements". `measurements_version` is carried into `ctx.mongo_snapshot` automatically — `_sanitize_doc` copies every key off the raw doc (minus `_id`), and `user_measurements` documents already have `measurements_version` on them, so no separate code change was needed for plan point 4.
- No other file was touched for A1. Cross-checked doc 04's read-site table again before finishing: `product_ingestion/legacy/*` and `run_product_ingestion.py:42` (`get_sizes_collection`, unrelated collection) are both untouched, `seed_measurements.py` (a writer) is untouched.
- **Regression check (`run_avatar.py --user-id u_001`) was not re-run live in this pass** — golden user `u_001` lives only in the old `measurements` collection, so the new code path tries `user_measurements` first (finds nothing for `u_001`), falls through to `measurements` (finds it), and sets `source = "mongodb:measurements"`. This is a straightforward read of the new code, not a live-verified claim; folded into the A3 live-run checklist below (plan step 6) since that's the first point this lane touches CLO/Mongo live in this session.

### A2 — done

- `website/backend/src/config.py`: added `REPO_ROOT` (three parents up from `config.py`, i.e. `website/backend/../..` — resolves to the real repo root natively and to `/app` inside the container, since the Dockerfile's `COPY website/backend ./website/backend` under `WORKDIR /app` preserves the same relative structure) and a `Settings.avatars_upload_root` property mirroring `worker/live_upload.py`'s `_avatars_root()`: `app_env == "production"` → `REPO_ROOT / "live_upload"`, else → `REPO_ROOT / "dev_upload"`. Deliberately **excludes** the trailing `avatars` segment — `avatar_glb_path` is stored as `"avatars/<user_id>/<version>/avatar.glb"`, i.e. already relative to the upload root itself, not to an `.../avatars` subfolder (confirmed by reading `worker/live_upload.py`'s `glb_relative_path` construction, not assumed — this was a real near-miss, my first draft of the property included the `/avatars` suffix and would have produced a double `avatars/avatars/...` join). Updated the stale `app_env` docstring that said "not yet consumed by the backend."
- `docker-compose.yml`: backend service now also bind-mounts `./dev_upload:/app/dev_upload:ro` and `./live_upload:/app/live_upload:ro` (both roots, not just dev, so the container's `APP_ENV` resolves consistently with the worker's regardless of which value it's set to). **This is the change that needs the parent's rebuild+restart — not yet applied to the running container.**
- `website/backend/src/avatars/service.py`: added `get_profile_glb(user_id)` returning a small `ResolvedAvatarGlb(path, is_stale)`. Looks up the caller's own `avatar_profiles` doc by `user_id` (never client input) — 404 (`NotFound`) if no profile, if `avatar_glb_path` is unset (export failed or hasn't run), or if the resolved file isn't actually on disk. Resolves `avatars_upload_root / avatar_glb_path` and asserts the result stays under the upload root (path-traversal guard, even though the stored value is server-written). Staleness: reads `avatar_profiles.source_measurements_version` and, if set, compares it against the *current* `user_measurements.measurements_version` (via the existing `get_for_user`); `is_stale` is `None` (not `False`) when there's nothing to compare against, so "unknown" and "confirmed fresh" aren't conflated.
  - Also populated `source_measurements_version` in `_materialize_profile` (previously always `None` — the `models.py` docstring literally said "not yet populated"). `job.measurement_snapshot` is a dump of the `UserMeasurementsDocument` read at job-creation time and already carries `measurements_version` (default `1`, never `None`), so this was a one-line addition inside an already-owned file, not a second file touched for A1's read-site rule — this is A2's staleness plumbing, a distinct concern from A1's fetch-source change.
  - Considered whether this write belongs in `worker/tasks.py` instead (where `avatar_glb_path` itself gets set) — `worker/` is lane territory but not on doc 04's explicit "owned files" list, and the value is already fully available inside `_materialize_profile` in an owned file, so it landed there instead of touching a second file unnecessarily.
- `website/backend/src/avatars/controller.py`: added `get_profile_glb(user_id) -> FileResponse`. Sets `Cache-Control: public, max-age=31536000, immutable` (safe because the served path is version-scoped and never overwritten in place) and a custom `X-Avatar-Measurements-Stale` header (`"true"` / `"false"` / `"unknown"`) — chosen over a JSON wrapper because the response body has to be the raw GLB bytes for a `<model-viewer>`/three.js consumer to load it directly; staleness is surfaced out-of-band instead of silently dropped. Media type `model/gltf-binary`.
- `website/backend/src/avatars/routes.py`: added `GET /profile/glb` (literal path segment, no route-ordering conflict with the existing literal `GET /profile`).
- `website/backend/src/avatars/models.py`: updated `source_measurements_version`'s docstring, which previously claimed the field "doesn't exist ... yet" — untrue as of this pass.
- Did **not** add a "latest job" lookup route (B4, explicitly out of scope per doc 04).

### Verification performed (once, at the end, per `01`)

- `python -m py_compile` on every touched Python file (`step_03_fetch_measurements.py`, `mirra_measurements/db.py`, `avatars/routes.py`, `avatars/controller.py`, `avatars/service.py`, `avatars/models.py`, `config.py`) — all clean.
- `docker-compose.yml` is YAML, not Python; validated with `yaml.safe_load()` instead — parses cleanly.
- `python -c "from src.main import app"` run from `website/backend/` against the repo's `.venv` — imports cleanly (exercises `config.py`'s new `REPO_ROOT`/`avatars_upload_root`, `avatars/service.py`'s new imports, and the new route wiring all at once).
- **Not yet run**: `docker compose build backend && docker compose up -d backend` (parent-owned — see below), `docker compose exec backend python scripts/smoke_e2e.py`, and the full A3 live run. None of static-check verification substitutes for these per `01`'s standing rule — recorded here as still-open, not implied-done.

### What didn't match the plan

- Plan step "A2 point 4" undersold how much was already available: it framed the staleness check as blocked on `measurements_version` "being visible downstream" (true) but the actual blocker turned out to be that `source_measurements_version` had never been *written* anywhere — `_materialize_profile` simply omitted it. Fixing that turned out to be a one-line addition once traced, not a design question.
- The `avatars_upload_root` trailing-slash/segment mistake described above (would have produced `dev_upload/avatars/avatars/...`) is worth flagging explicitly for whoever reads this next — the plan doc's own phrasing ("bind-mount the relevant upload root") doesn't spell out where the `avatars/` segment lives, and it's easy to double it if you don't go read `worker/live_upload.py`'s actual string construction first.

### Handoff — waiting on the parent for the Docker rebuild before A3

Per `01` and this doc's own rules, this lane does not run `docker compose build/up/down/restart`. The `docker-compose.yml` volume-mount change above requires a rebuild + restart to take effect before `GET /profile/glb` can see any files at all inside the container. **Stopping here and asking the parent to run the rebuild** (`docker compose build backend && docker compose up -d backend` from the repo root) — will resume with the smoke test and the full A3 live run once that's confirmed done. No worker was started in this pass, so there is nothing to stop/clean up on that front.
