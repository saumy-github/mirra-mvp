# Step 0 - Shared infra: the job worker/queue

**Status:** implemented and live-verified (see Execution Log). `demo`/`live` engine mode itself was later removed entirely — see [22-remove-demo-live-mode-and-upload-split.md](22-remove-demo-live-mode-and-upload-split.md); every avatar/try-on request now always goes through this worker path, no mode flag.
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Blocks:** every other step in this sequence — nothing runs in `live` mode without this.

## Goal

Give the backend a way to hand an avatar/try-on job to CLO without holding an HTTP request open for minutes, and without pretending there's parallelism that CLO can't actually provide.

## Why this shape (recap, not a re-decision)

CLO3D's plugin is inherently single-threaded — one command queue, drained by a single Win32 timer on CLO's main UI thread (`RestPlugin_windows.cpp`). No queueing technology in front of it changes that. So this isn't a concurrency decision, it's purely "don't block the request thread" — a lightweight single-worker queue (Redis + RQ, concurrency = 1) is the right tool, not overkill.

## Current state

**Superseded by this doc's own Execution Log below, then by doc 22** — this section is kept for historical context only. `avatars/engine.py::start_job` and `tryon/engine.py::start_render` originally did exactly one thing in `live` mode: `raise ServiceUnavailable("... CLO3D worker queue pending")`. No queue, no worker, nothing downstream of this existed yet at the time this doc was written.
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

### 2026-08-08 - Implemented

Built as scoped — queue + worker + Mongo state machine wiring only, no GLB
export or `live_upload/` storage (Steps 4/5/9/10, still separate/later).

**Open decision resolved:** worker lives at top-level `worker/` (repo root),
per the doc's own leaning — conceptually closer to `clo_avatar_generation`/
`clo_vto` than to the website.

**What changed:**
- `docker-compose.yml` — added a `redis` service (`redis:7-alpine`, port
  `6379` published to the host so the *native* worker can reach it via
  `localhost:6379`; the Dockerized backend reaches it via the `redis`
  service name instead), `backend` now `depends_on: redis`.
- `requirements.txt` — added `rq>=1.16.0`, `redis>=5.0.0`.
- `website/backend/src/config.py` — added `redis_url` setting (native
  default `redis://localhost:6379/0`; the Dockerized backend needs
  `REDIS_URL=redis://redis:6379/0` added to `website/backend/.env.docker.dev`
  — not done here, that file's gitignored and gets hand-edited, see the
  "what I need from you" note this was implemented alongside).
- `website/backend/src/core/queue.py` (new) — `enqueue()`/`get_queue()`.
  Enqueues by **string** job path (`"worker.tasks.run_avatar_job"`), never
  imports `worker.tasks` directly — the backend's Docker image doesn't have
  `clo_avatar_generation`/`clo_vto` copied in (only `website/backend`),
  so a direct import would break the image. `job_timeout` is a required
  kwarg, not defaulted, so every call site makes a deliberate choice
  instead of silently inheriting RQ's 180s default.
- `avatars/engine.py::start_job` / `tryon/engine.py::start_render` —
  replaced the `raise ServiceUnavailable` with real enqueue calls
  (20 min / 25 min job timeouts respectively).
- `avatars/models.py::AvatarProfileDocument` — added
  `clo_avatar_avt_path: str | None`, set by the worker after a live run.
  This is a **Step 0-only internal bridge field** (how the try-on task
  locates the user's `.avt` to hand to `clo_vto`, since Step 5's real
  `live_upload/` storage doesn't exist yet) — not the web-facing
  `avatar_glb_path` doc 05/06 already plans for Step 5.
- `worker/` (new top-level package): `tasks.py` (`run_avatar_job`,
  `run_tryon_render`), `run_worker.py` (entrypoint — `SimpleWorker`, not
  the default `rq.Worker`, see below), `.env.example`, `README.md`.
  `worker/tasks.py` imports `website/backend/src` directly (via a
  `sys.path` insert, same pattern every pipeline entrypoint in this repo
  already uses for `REPO_ROOT`) so job/profile/render document shapes can
  never drift from what the FastAPI app itself reads — no duplicate schema.

**Real, non-obvious finding: `rq.Worker`'s default fork-based execution
model doesn't work on Windows at all** (`os.fork()` doesn't exist there).
Doc 07 didn't originally flag this — worth recording since it changes the
literal implementation, not just an implementation detail: used
`rq.worker.SimpleWorker` instead (runs jobs in-process, no fork — this is
also independently correct for us regardless of platform, since CLO3D's
plugin is itself single-threaded and there's no parallelism to gain from a
forking worker). Its timeout mechanism (`TimerDeathPenalty`) doesn't depend
on `SIGALRM` (also Windows-incompatible) — it uses `threading.Timer` +
`PyThreadState_SetAsyncExc` instead, which does work on Windows.

**Verified on this machine before wiring it up for real** (doc 01's own
"verify before building on top" precedent):
- `SimpleWorker` starts and processes jobs cleanly on Windows (RQ 2.10.0).
- Its timeout mechanism actually fires: a job exceeding `job_timeout` is
  marked `FAILED` with `JobTimeoutException`, and — critically — **the
  worker keeps processing later jobs cleanly afterward**, it doesn't wedge.
  One real caveat recorded in `worker/README.md`: the async exception can
  only land at a Python bytecode boundary, so it's delivered *after*
  whatever single blocking call is currently in flight returns, not
  instantly. Every CLO REST call already has its own `timeout=30`, so
  worst case this adds ~30s of latency, not an indefinite hang.
- `docker compose up -d redis` works; the backend app (`src.main:app`)
  still imports cleanly with the new `core/queue.py` wiring.
- `worker.tasks` imports cleanly end to end — pulls in the full
  `clo_avatar_generation`/`clo_vto` import chain plus `website/backend/src`
  with no errors.
- Full plumbing test: enqueued a real (fake-id) job onto the real `clo`
  Redis queue from the backend's `enqueue()` helper, then ran `SimpleWorker`
  against it — it picked up the job, resolved
  `"worker.tasks.run_avatar_job"`, executed, and reached the real (async)
  pymongo driver's connection attempt, which failed cleanly after the
  existing 3s `serverSelectionTimeoutMS` (no local Mongo was configured for
  this throwaway test — expected) without crashing the worker process.

**Not verified — needs the pilot machine + real credentials, which this
session doesn't have/read (`.env*` files are never read — see repo
convention):** a real end-to-end run against the actual Atlas DB and a
running CLO3D instance. See the chat turn that implemented this for the
exact "what I need from you" list (`worker/.env`, the `.env.docker.dev`
`REDIS_URL` line, `pip install -r requirements.txt`, a rebuilt backend
image, a male test user with measurements already stored).

**Known, deliberate scope limits carried into `worker/README.md`:**
- Try-on jobs use `clo_vto`'s default-panels t-shirt only, untextured —
  Step 7 (catalog → real garment pattern wiring) isn't built.
- Try-on output lands in the single shared `clo_vto/output/` folder (a
  pre-existing constraint of that pipeline), overwritten by the next
  render — no per-render storage until Step 10.
- No GLB export (Step 4), no `live_upload/` (Step 5/10) — a `ready`
  job/render has no web-facing 3D asset yet. This step only proves the
  queue + real pipeline invocation + Mongo state machine end to end.
