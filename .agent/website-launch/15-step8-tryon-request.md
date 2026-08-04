# Step 8 - User selects avatar + garment + size, requests try-on

**Status:** mostly done — one real behavior change remaining (cache reuse)
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [07-step0-worker-queue.md](07-step0-worker-queue.md) for the enqueue wiring; benefits from [14-step7-garment-catalog.md](14-step7-garment-catalog.md) for real garment variety, but can be built against the current single default garment in the meantime.

## Goal

Let a user request a try-on of a specific catalog item on their existing avatar, without re-running CLO for a combination that's already been rendered.

## Current state (already built in demo mode)

- `POST /api/v1/tryon/sessions` and `POST /api/v1/tryon/sessions/{session_id}/renders` already exist (`tryon/routes.py` → `controller.py`).
- `TryonRenderDocument` already captures a `garment_snapshot` (the catalog doc at request time) and references `avatar_profile_id` — exactly the inputs a live render needs.
- The state machine (`requested → rendering → ready → failed`) already exists and drives demo-mode UI via `tryon/engine.py::derive_demo_state`.
- The doc comments in `tryon/models.py` already describe the intended cache-reuse behavior in plain language: *"`state` derives from elapsed time on read in demo mode until ready, then it's persisted and every later read is a cheap restore (the Hanger no-recompute path)."* The behavior is named and understood — it just isn't implemented for `live` mode yet.

## Remaining work

1. **Before enqueueing a live render, check for an existing reusable result.** Query `tryon_renders` for a `ready` doc matching `(avatar_profile_id, size_id)` where the avatar hasn't been regenerated since that render was created (compare timestamps, or a version marker if you want to be precise — `avatar_profiles.generated_at` vs. the existing render's `created_at`/`completed_at`). If found, return that doc instead of creating a new job — this is the actual mechanism that keeps CLO load down for try-on, described in the models file but not yet built.
2. **Wire `tryon/engine.py::start_render` to Step 0's worker/queue** instead of `raise ServiceUnavailable(...)`.
3. No changes needed to the request/response shape — the existing endpoints already return the right document shape for both the "reused" and "new job" cases, since both are just a `TryonRenderDocument`.

## Files touched

- `website/backend/src/tryon/service.py` (or `controller.py`, wherever the render-request logic lives) — add the cache-reuse lookup before creating a new render doc
- `website/backend/src/tryon/engine.py` — enqueue instead of refuse

## Verification

- Request the same garment+size twice in a row for the same avatar — confirm the second request returns the existing `ready` render immediately, with no new job enqueued (check worker logs / queue depth).
- Regenerate the avatar, then request the same garment+size again — confirm this time a *new* render is triggered (stale cache correctly invalidated).
- Request two different sizes — confirm both get independent renders, no incorrect cache hits across different `size_id`s.

## Execution Log

Not started.
