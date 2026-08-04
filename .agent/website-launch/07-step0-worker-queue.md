# Step 0 - Shared infra: the job worker/queue

**Status:** planned, not yet executed
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Blocks:** every other step in this sequence — nothing runs in `live` mode without this.

## Goal

Give the backend a way to hand an avatar/try-on job to CLO without holding an HTTP request open for minutes, and without pretending there's parallelism that CLO can't actually provide.

## Why this shape (recap, not a re-decision)

CLO3D's plugin is inherently single-threaded — one command queue, drained by a single Win32 timer on CLO's main UI thread (`RestPlugin_windows.cpp`). No queueing technology in front of it changes that. So this isn't a concurrency decision, it's purely "don't block the request thread" — a lightweight single-worker queue (Redis + RQ, concurrency = 1) is the right tool, not overkill.

## Current state

- `avatars/engine.py::start_job` and `tryon/engine.py::start_render` both currently do exactly one thing in `live` mode: `raise ServiceUnavailable("... CLO3D worker queue pending")`. No queue, no worker, nothing downstream of this exists yet.
- The state machine both jobs need to drive already exists and is proven out in demo mode: `avatar_jobs` (`queued → processing → ready → failed`) and `tryon_renders` (`requested → rendering → ready → failed`).
- The worker's execution target already exists and works: `clo_avatar_generation/run_avatar.py` (proven against golden user `u_001`, doc 01 Phase 2) and `clo_vto/run_clo_vto.py`.
- Deploy topology is already decided (doc 01/02): backend + frontend run in Docker on the pilot Windows machine; the worker is a **native Windows Python process** using the repo's existing `.venv`, not containerized, because it needs to drive the pipeline scripts directly and reach the CLO plugin at `localhost:50505`.

## Remaining work

1. **Add Redis to `docker-compose.yml`.** Was explicitly deferred in docs 01/02 ("no Redis/queue container ... that's a later phase") — this is that phase. Standard `redis:7-alpine` image, named volume optional (job queue doesn't need durability across restarts for a pilot).
2. **Pick and add RQ (or equivalent) to `requirements.txt`.** Lightweight, Python-native, fits "single worker, FIFO" exactly — no need for Celery's heavier feature set here.
3. **Write the worker entrypoint** (new file, e.g. `worker/run_worker.py` at repo root, or under `website/backend/worker/` — decide placement so it's clear this is not part of the FastAPI app itself). Responsibilities:
   - connect to Redis, block on the queue, concurrency = 1 (single process, no multiprocessing)
   - for an avatar job: read the job id, look up `avatar_jobs` doc, extract `measurement_snapshot`, invoke the Step 1 pipeline non-interactively for that user
   - for a try-on job: look up `tryon_renders` doc, resolve `avatar_profile_id` → avatar file path and `size_id` → catalog pattern path, invoke the Step 3 (VTO) pipeline
   - on success: hand off to Step 5/Step 10's storage logic (writes into `live_upload/...`), then update the Mongo doc to `ready` with the new path fields
   - on failure: update the Mongo doc to `failed` with a `failure_reason`, never leave a job stuck in `processing`
4. **Wire the two engine seams to enqueue instead of refuse:**
   - `avatars/engine.py::start_job` — replace the `raise ServiceUnavailable(...)` with an enqueue call (e.g. `queue.enqueue("worker.tasks.run_avatar_job", job.id)`)
   - `tryon/engine.py::start_render` — same shape, enqueue the render id
5. **Add a Redis connection setting** to `website/backend/src/config.py` (`redis_url: str`, same pattern as `mongodb_uri`) — the FastAPI process needs this to enqueue, even though it never processes jobs itself.
6. **Failure/timeout handling:** doc 01 already found a real bug — `POST /export` on a completely empty CLO scene hangs indefinitely. The worker should not blindly trust CLO to return; add a timeout around each pipeline stage so a wedged CLO instance fails the job (and gets flagged for a human to check/restart CLO) instead of leaving a `processing` job stuck forever with no visibility.

## Files touched

- `docker-compose.yml` — add `redis` service
- `requirements.txt` — add RQ (or chosen equivalent) and `redis` client
- new: worker entrypoint + task functions (placement TBD — flag as an open decision below)
- `website/backend/src/config.py` — add `redis_url`
- `website/backend/src/avatars/engine.py` — enqueue instead of refuse
- `website/backend/src/tryon/engine.py` — enqueue instead of refuse

## Open decision

Where does the worker code live? Options:
- `website/backend/worker/` — close to the FastAPI app it shares Mongo models with, but it's not a containerized/deployed-the-same-way component, which could be confusing
- a new top-level `worker/` folder at repo root, alongside `clo_avatar_generation/`, `clo_vto/`, `website/` — keeps it visually separate from "the website" since it's really CLO-machine-specific infra

Leaning toward the top-level option since it's conceptually closer to the pipelines it drives than to the website, but this is your call.

## Verification

- `docker compose up` brings up `redis` alongside `mongo`/`backend`/`frontend` with no errors
- manually enqueue a fake job, confirm the worker process picks it up and logs receiving it (before wiring real pipeline calls)
- kill the worker mid-job, confirm the job doc doesn't silently stay `processing` forever (ties to the timeout handling above)

## Execution Log

Not started.
