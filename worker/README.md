# CLO worker

Native Windows Python process that drives the real CLO3D avatar/VTO
pipelines for the website backend's `AVATAR_ENGINE_MODE=live` /
`TRYON_ENGINE_MODE=live` paths. Design doc:
[`.agent/website-launch/07-step0-worker-queue.md`](../.agent/website-launch/07-step0-worker-queue.md).

Runs **outside Docker** — it needs to reach the CLO3D REST plugin at
`localhost:50505` directly, and drive `clo_avatar_generation`/`clo_vto`
against the local filesystem the same way the existing dev CLI scripts
(`run_avatar.py`, `run_clo_vto.py`) already do.

## Setup

1. `cp worker/.env.example worker/.env` and fill in `MONGODB_URI` (same
   Atlas URI as `website/backend/.env.dev`) and `REDIS_URL` (defaults to
   `redis://localhost:6379/0`, matching the port `docker-compose.yml`
   publishes).
2. `docker compose up -d redis` (or `backend`, which brings up `redis` too
   via `depends_on`) — Redis must be reachable before starting the worker.
3. Make sure CLO3D is running locally with the REST plugin loaded
   (`http://localhost:50505/health` should respond).
4. From the repo root, inside the repo `.venv`:
   ```
   python worker/run_worker.py
   ```

Concurrency is intentionally 1 — CLO3D's plugin is itself single-threaded
(one command queue, drained by CLO's own UI thread), so running a second
worker against the same CLO instance would race and corrupt whichever job's
scene state loses. Don't start a second worker against the same CLO
instance.

## What it does

- Consumes the `clo` Redis queue, enqueued by
  `website/backend/src/avatars/engine.py::start_job` and
  `website/backend/src/tryon/engine.py::start_render` whenever
  `*_ENGINE_MODE=live`.
- **Avatar jobs**: runs `clo_avatar_generation`'s real 11-step pipeline
  against the user's stored measurements, then marks `avatar_jobs` /
  `avatar_profiles` ready or failed in Mongo — the same collections/document
  shapes the FastAPI app itself reads (`worker/tasks.py` imports
  `website/backend/src` directly so these never drift apart).
- **Try-on renders**: runs `clo_vto`'s real 12-step native pipeline against
  the requesting user's most recently generated avatar. **Uses the
  default-panels t-shirt only, untextured** — Step 7 (catalog → real
  garment pattern wiring) isn't built yet, so every live try-on renders the
  same placeholder garment regardless of what was actually requested. See
  `.agent/website-launch/06-avatar-vto-implementation-status.md` Steps 7
  and 9.
- A stuck/unresponsive CLO instance fails the job (RQ's own `job_timeout` —
  20 min for avatar generation, 25 min for try-on, set at the enqueue call
  sites) instead of leaving it stuck in `processing`/`rendering` forever.
  This does **not** restart CLO for you — if a job fails with a timeout
  reason in `failure_reason`, check the CLO3D window on this machine and
  restart it before retrying.

## Known scope limits (by design — this is Step 0 only)

- No GLB export (Step 4) and no `live_upload/` storage (Steps 5/10) yet — a
  `ready` job/render has no web-facing 3D asset. This step only proves the
  queue + real pipeline invocation + Mongo state machine work end to end
  against real CLO3D.
- Try-on output lands in the single shared `clo_vto/output/` folder (a
  pre-existing constraint of `clo_vto`'s pipeline, not something this pass
  changed), which the *next* try-on render overwrites — there's no
  per-render artifact storage until Step 10.
- The avatar pipeline currently only supports `gender: male` measurement
  docs (`clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`)
  — a pre-existing pipeline limitation, unrelated to this step.

## Windows/RQ note

The default `rq.Worker` forks a work-horse process per job — `os.fork()`
doesn't exist on Windows, so it can't be used here. This worker uses
`rq.worker.SimpleWorker` instead (runs jobs in-process, no fork). Its
timeout mechanism (`TimerDeathPenalty`) uses `threading.Timer` +
`PyThreadState_SetAsyncExc` rather than `SIGALRM`, which also doesn't exist
on Windows — verified working end to end on this machine (RQ 2.10.0) before
wiring it up for real, including confirming the worker keeps processing
later jobs cleanly after an earlier one times out. One real caveat: the
async exception can only interrupt at a Python bytecode boundary, so a
timeout is delivered *after* whatever single blocking call is currently in
flight returns (every CLO REST call already has its own `timeout=30`,
so in practice this adds at most ~30s of latency, not an indefinite hang).
