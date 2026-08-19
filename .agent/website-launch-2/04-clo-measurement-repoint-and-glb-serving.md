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

*(To be written after the work, per `01`'s workflow step 3: what was actually done, what was verified and how, and anything found that didn't match this plan.)*
