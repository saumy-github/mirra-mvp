# 19 - Docker local dev: completion status

**Status:** backend Docker + hot reload done; local Mongo + `mirra_measurements/` migration explicitly deferred
**Created:** 2026-08-08
**Closes out:** [02-phase-1-continuation-docker-env-and-local-db-plan.md](02-phase-1-continuation-docker-env-and-local-db-plan.md) and [04-docker-local-dev-setup-plan.md](04-docker-local-dev-setup-plan.md) (doc 04's frontend-in-Docker approach was superseded — see "What changed from the original plan" below)

## What's actually finalized

**Backend runs in Docker. Frontend runs natively (not in Docker).** This is a deliberate deviation from doc 02/04's original three-container (`mongo` + `backend` + `frontend`) vision — see below for why.

- `docker-compose.yml` — **one service, `backend`.** Builds from repo root, `env_file: website/backend/.env.docker.dev`, bind-mounts `./website/backend/src` for hot reload, runs `uvicorn ... --reload` via a `command:` override (the image's own `CMD` stays reload-free, correct for `docker build`/Render later).
- `website/backend/.env.docker.dev` (gitignored) — service-owned env, still points at the Atlas `mirratest` database (local Mongo is deferred, see below).
- `website/frontend/` — **no Dockerfile, no `nginx.conf`, no `.env.docker.dev`.** Runs via plain `npm run dev` on the host, using `website/frontend/.env.development` (gitignored, pre-filled to point at the Dockerized backend on `localhost:8000`, `VITE_AUTH_PROVIDER=live`/`VITE_INTEGRATION_MODE=live`).
- Root `.gitignore`/`.dockerignore` hardened: `.env`, `.env.*` ignored everywhere except `!**/.env.example`, so no env file (dev or prod) can leak into git or an image layer.
- `package.json` — `dev:up`/`dev:down`/`dev:restart`/`dev:ps`/`dev:logs`/`dev:logs:backend`/`dev:seed`/`dev:smoke`, all backend-only now (no `dev:logs:frontend`).
- `website/backend/README.md` and new `website/frontend/README.md` document the actual two-terminal daily workflow.

## What changed from the original plan, and why

Doc 04 originally planned to Dockerize the frontend too (Vite dev server in a container, bind-mounted source). Built and tested it — it worked for building/serving, but **hot reload never worked**: Docker Desktop's Windows filesystem-sharing layer doesn't reliably propagate file-change events *or even `stat`/mtime updates* into the bind-mounted container, so Vite's watcher never saw edits — confirmed with `usePolling: true` enabled too, which still didn't help, since the underlying `stat` data itself wasn't updating, not just the event notification.

Rather than keep fighting that, the frontend was pulled out of Docker entirely and runs natively instead — sidesteps the problem completely (normal OS-level file watching), and matches a pattern this repo's own reference doc (`Info.md`) already called out as standard: Docker for a deployable artifact, the package manager for fast local feedback. The backend doesn't have this problem since Python/uvicorn's reload mechanism polls by default regardless, so it stayed in Docker without issue.

## Explicitly still deferred (not part of this pass)

- **Local `mongo` Docker container.** Backend still connects to Atlas `mirratest` via `.env.docker.dev`, same as it did before this round of work. No `mongo` service exists in `docker-compose.yml`.
- **`mirra_measurements/` migration/deletion.** Still exists at the repo root, untouched. Found during exploration to still be imported at runtime by **live CLO pipeline code**, not just old website code — `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py:150` and `product_ingestion/run_product_ingestion.py:42` both import from it directly. This is bigger and riskier than doc 02 assumed and was explicitly deferred to its own focused pass, deliberately bundled together with the Mongo migration since they're linked (the pipelines' `mirra_measurements.db` connector would need to move somewhere both the pipelines and any future local-Mongo setup can share).
- Render/Vercel production deployment (doc 02's later sections) — untouched, not attempted.

## File-by-file: what's done

**Modified (tracked):**
- `.gitignore` — env-file wildcard + example exceptions
- `.dockerignore` — same, for image builds
- `docker-compose.yml` — rewritten to backend-only, bind mount, `--reload` override
- `package.json` — scripts simplified to backend-only, added `dev:seed`/`dev:smoke`
- `website/backend/README.md` — added the Docker-based run option alongside the existing native-venv instructions

**Deleted (tracked):**
- `website/frontend/Dockerfile`
- `website/frontend/nginx.conf`

**New (untracked, gitignored — created but never committed since they're env files):**
- `website/backend/.env.docker.dev`
- `website/frontend/.env.development`

**New (untracked, will need `git add` when committing):**
- `website/frontend/README.md` — new, didn't exist before; documents the native frontend dev flow and why it's not Dockerized

**Reverted to original (touched during verification, no net change):**
- `website/frontend/vite.config.ts` — briefly added a polling watcher workaround while diagnosing the Docker hot-reload issue, reverted once the frontend was pulled out of Docker entirely (the workaround no longer applies)

## Verified working (this session)

- `docker compose config` validates cleanly.
- `npm run dev:up` builds and starts `backend` with no errors.
- `GET http://localhost:8000/api/v1/health` → `{"status":"ok","database":"connected"}` (Atlas).
- Backend hot reload confirmed live: editing `website/backend/src/main.py` triggered `WatchFiles detected changes ... Reloading...` in the container logs with no rebuild.
- Frontend native flow (`npm run dev` in `website/frontend`) was not re-verified end-to-end after the Docker-removal change in this session — worth a quick check next time it's run.

## Execution Log

### 2026-08-08 - Backend Dockerized with hot reload; frontend pulled out of Docker after a real, unresolved bind-mount issue

Implemented and verified as described above. Docker/env portion of doc 02 is done to the extent planned (minus Mongo, deferred). `mirra_measurements/` migration untouched, tracked as a separate future pass alongside local Mongo.
