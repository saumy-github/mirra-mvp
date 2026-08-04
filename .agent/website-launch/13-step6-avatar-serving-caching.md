# Step 6 - Show the avatar on the website, without reloading/re-running CLO

**Status:** planned, not yet executed
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [12-step5-avatar-storage.md](12-step5-avatar-storage.md)

## Goal

Let the frontend display a user's avatar on every visit without ever re-invoking CLO, and without the backend re-reading/re-serving the file more than browser caching already allows — this is the step that actually delivers "reduce server and CLO load."

## Current state

- `GET /api/v1/avatars/profile` already exists (`avatars/routes.py` → `controller.get_profile`) and returns the profile shape — once Step 5's fields exist, this endpoint just needs to include them, no new endpoint required for the metadata itself.
- The serving pattern to copy already exists elsewhere in this codebase: `capture/routes.py`'s `GET /{session_id}/photo` → `capture/controller.py::get_photo` → `FileResponse(path, media_type=session.photo.content_type)`, gated by `identity: CurrentIdentity` and an ownership check. This is the exact shape the new GLB route should follow — nothing new to invent here.
- `website/backend/src/config.py` already has the equivalent pattern for a different folder (`uploads_dir`/`uploads_path`) to model the new `live_upload_dir` setting on.

## Remaining work

1. **Bind-mount `live_upload/` read-only into the backend container.** In `docker-compose.yml`'s `backend` service: `./live_upload:/app/live_upload:ro`. This is the mechanism that lets the containerized backend read files written by the native Windows worker process, without a duplicate copy.
2. **Add `live_upload_dir` to `config.py`**, same shape as `uploads_dir`/`uploads_path`.
3. **New route: `GET /api/v1/avatars/profile/glb`** (`avatars/routes.py` + `controller.py`):
   - resolve the path from `avatar_profiles.avatar_glb_path` (the Mongo doc), never from a client-supplied path
   - verify the profile belongs to `identity.user_id` before serving (same ownership check as `capture`'s photo route)
   - `FileResponse(path, media_type="model/gltf-binary")` (or the correct media type once the `.glb`/`.gltf` naming decision from Step 4 is settled)
   - response header: `Cache-Control: private, max-age=<long>, immutable` — safe because the path is already version-qualified (a real regeneration produces a new path, so there's no staleness risk from long caching)
4. **Staleness check, not auto-regeneration.** Compare `avatar_profiles.source_measurements_version` to the live `measurements.measurements_version` (added in Step 2). If they differ, the frontend shows a "your measurements changed — regenerate your avatar?" prompt. It must **never** trigger a new CLO job automatically just because this mismatch is detected on a page view.
5. **Frontend: lazy-loaded 3D viewer component**, per `03-backend-behavior-plan.md` Section 7's SPA/3D guidance already established:
   - not part of the main app bundle (separate chunk/dynamic import)
   - not loaded during route transitions — page shell renders first, viewer loads after
   - dispose Three.js/`<model-viewer>` resources when navigating away
   - never render this avatar viewer and a try-on viewer simultaneously (memory spike risk, already flagged in doc 03)
6. **Frontend must never call avatar generation as a side effect of viewing a page.** Generation only happens from the explicit "Create avatar" / "Regenerate" button — viewing is always a pure `GET`.

## Files touched

- `docker-compose.yml` — bind mount
- `website/backend/src/config.py` — `live_upload_dir`
- `website/backend/src/avatars/routes.py`, `controller.py` — new GLB route
- frontend: new lazy-loaded avatar viewer component + integration into the profile/studio page

## Verification

- Load the avatar page twice in a row — confirm via backend logs (or a network tab check) that CLO is never invoked on either load, only on explicit generation.
- Edit measurements, reload the avatar page, confirm the staleness prompt appears instead of an automatic regeneration.
- Check response headers on the GLB route — confirm caching headers are present and the browser doesn't re-fetch on a second visit within the cache window.
- Attempt to fetch another user's `avatar_glb_path` while authenticated as a different user — confirm the ownership check rejects it (401/403, not the file).

## Execution Log

Not started.
