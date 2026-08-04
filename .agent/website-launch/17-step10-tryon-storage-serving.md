# Step 10 - Save and serve the try-on result

**Status:** planned, not yet executed — mirrors Steps 5 + 6 for try-on
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [16-step9-vto-pipeline.md](16-step9-vto-pipeline.md); reuses the storage/serving pattern from [12-step5-avatar-storage.md](12-step5-avatar-storage.md) and [13-step6-avatar-serving-caching.md](13-step6-avatar-serving-caching.md)

## Goal

Same as Steps 5+6, applied to try-on results: save the VTO run's artifacts to `live_upload/`, and serve the result GLB to the frontend without re-invoking CLO or duplicating storage.

## Current state

Nothing exists yet — no code writes try-on results anywhere outside `clo_vto/output/` today, and there's no serving route for a try-on result GLB.

## Remaining work

1. **Worker-side copy logic** (part of the Step 0 worker's try-on task): after a successful VTO run —
   - compute the next version number under `live_upload/tryon/<user_id>/<size_id>/`
   - create `live_upload/tryon/<user_id>/<size_id>/<version>/`
   - copy `result.zprj`, `result.avt`, the textured `.glb`/`.gltf` (per Step 9's naming decision), and `run.log`
   - write `run_manifest.json` pointing back to the source `clo_vto/output/...` run
2. **Add fields to `TryonRenderDocument`** (`tryon/models.py`):
   ```python
   result_glb_path: str | None = None
   clo_run_id: str | None = None
   ```
3. **New route: `GET /api/v1/tryon/sessions/{session_id}/renders/{render_id}/glb`** (`tryon/routes.py` + `controller.py`) — same shape as Step 6's avatar GLB route: resolve path from the Mongo doc, ownership check against `identity.user_id`, `FileResponse`, same `Cache-Control: private, max-age=<long>, immutable` header (safe for the same reason — version-qualified path).
4. **No new bind mount needed** — reuses the same `live_upload/` read-only mount already added for Step 6, since `tryon/` is just another subtree of the same folder.
5. **Frontend:** same lazy-load/dispose discipline as the avatar viewer (Step 6) — and explicitly, per doc 03 Section 7's flagged risk, **never mount the avatar viewer and the try-on result viewer at the same time.** If the try-on page shows both "your avatar" and "the try-on result" side by side, that's the specific multi-viewer memory-spike scenario already called out as a risk — worth a deliberate UX decision (e.g., toggle between the two rather than both live simultaneously) rather than defaulting into it.

## Files touched

- worker task code (from Step 0) — the copy/version logic for try-on
- `website/backend/src/tryon/models.py` — new fields
- `website/backend/src/tryon/routes.py`, `controller.py` — new GLB route
- frontend: try-on result viewer, reusing Step 6's viewer component if built generically enough

## Verification

- A completed try-on produces a versioned folder under `live_upload/tryon/<user_id>/<size_id>/`, with `run.log` and `run_manifest.json` present.
- The result GLB route serves correctly and rejects cross-user access, same checks as Step 6.
- Requesting the same garment+size again (Step 8's cache-reuse logic) correctly returns the *existing* render's `result_glb_path` without creating a new version folder.
- Try-on page doesn't spike memory/crash on a mid-range mobile browser when both an avatar and a try-on result exist for the same user — the actual risk this step's frontend guidance is meant to prevent.

## Execution Log

Not started.
