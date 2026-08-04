# Step 3 - "Create avatar" click → job creation

**Status:** already done — becomes live automatically once Step 0 lands
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [07-step0-worker-queue.md](07-step0-worker-queue.md)

## Goal

When a user clicks "Create avatar," record a job with a frozen snapshot of their current measurements, so a later measurement edit can't retroactively change what an in-flight job builds from.

## Current state (already fully built)

- `POST /api/v1/avatars/generate` (`avatars/routes.py` → `controller.start_generation`) already creates an `avatar_jobs` document at request time.
- `AvatarJobDocument.measurement_snapshot` (`avatars/models.py`) is already populated as a copy of the measurements doc at job creation — this is exactly the "freeze the input" behavior needed, already correct.
- `GET /api/v1/avatars/jobs/{job_id}` already exists for the frontend to poll job status.
- The state machine (`queued → processing → ready → failed`) is already modeled and already drives real UI behavior in `demo` mode via `avatars/engine.py::derive_demo_state`.

## Remaining work

**None, structurally.** This step does not need new code. Once Step 0's worker/queue exists and `avatars/engine.py::start_job` enqueues instead of raising `ServiceUnavailable`, this endpoint starts producing real jobs with no further changes here.

The only thing worth double-checking once Step 0 lands: `derive_demo_state`'s time-based state derivation is demo-only logic — confirm the `live`-mode path reads `state` directly from the Mongo doc (set by the worker) rather than any time-elapsed heuristic. Worth a quick read of `avatars/service.py`/`controller.py` at that point to confirm the demo/live branch is clean, not a new build task.

## Files touched

None expected. This file exists mainly to make explicit that Step 3 is not blocking work — it's already correct and just needs Step 0 to exist.

## Verification

Once Step 0 is live: click "Create avatar," confirm an `avatar_jobs` doc appears with `state: "queued"`, a real `measurement_snapshot`, and that editing measurements afterward does not change the snapshot already stored on that job.

## Execution Log

Not started.
