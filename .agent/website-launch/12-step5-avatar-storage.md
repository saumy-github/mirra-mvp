# Step 5 - Save the avatar to `live_upload/`

**Status:** planned, not yet executed
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)
**Depends on:** [11-step4-avatar-pipeline-invocation.md](11-step4-avatar-pipeline-invocation.md)

## Goal

Move a completed avatar run's final artifacts out of the pipeline's own dev/debug `output/` folder and into a stable, versioned, production-facing location the website can serve from directly — without losing the ability to trace back to the full debug run if something looks wrong later.

## Current state

Nothing here exists yet — today, avatar runs only ever write into `clo_avatar_generation/output/<user_id>-<run_number>/`, which is the pipeline's own dev/QA trail, not meant to hold real pilot users' production data (explicitly decided not to reuse it — see doc 05).

## Remaining work

1. **Create `live_upload/avatars/` at the repo root**, sibling to `clo_avatar_generation/`, `product_ingestion/`, `clo_vto/`, `website/`.
2. **Add a local `.gitignore`** inside `live_upload/` — same pattern as `clo_avatar_generation/.gitignore` (`avatars/*` ignored, tracked `.gitkeep`). Also extend the **repo-root** `.gitignore` to cover `*.avt` and `*.zprj` — currently only `*.dxf`/`*.glb`/`*.gltf`/`*.obj`/`*.svg`/`*.mtl` are covered there, `.avt`/`.zprj` are not.
3. **Worker-side copy logic** (part of the Step 0 worker's avatar task, not a separate service): after a successful pipeline run —
   - compute the next version number for this `user_id` (next integer under `live_upload/avatars/<user_id>/`, similar logic to `clo_avatar_generation/avatar_runtime/run_manifest.py::get_next_run_number`, but scoped to `live_upload/` instead of the pipeline's own output root)
   - create `live_upload/avatars/<user_id>/<version>/`
   - copy `avatar.zprj`, `avatar.avt`, the new `.glb`/`.gltf` (per Step 4's naming decision), and `run.log`
   - write `run_manifest.json` recording: source run id (`<user_id>-<run_number>` from `clo_avatar_generation/output/`), timestamp, pipeline step results summary — enough to trace back to the full debug log without duplicating it
4. **Add the new fields to `AvatarProfileDocument`** (`avatars/models.py`):
   ```python
   avatar_glb_path: str | None = None          # relative path under live_upload/avatars/...
   source_measurements_version: int | None = None
   generated_at: datetime | None = None
   clo_run_id: str | None = None                # e.g. "u_001-004", for tracing to clo_avatar_generation/output/
   ```
5. **Populate these fields when the worker marks the job `ready`** — this is the same write that updates `avatar_jobs.state` and `avatar_profiles`, just with the new fields included.
6. Since `avatar_profiles` is one-per-user (unique index on `user_id`), each regeneration **updates** that single doc's path/version fields to point at the newest version — older versions stay on disk (per this round's "keep versions" decision) but aren't referenced by the live profile doc unless you later add a "restore an old version" feature (not currently planned).

## Files touched

- new: `live_upload/avatars/.gitkeep` + `live_upload/.gitignore`
- root `.gitignore` — add `*.avt`, `*.zprj`
- worker task code (from Step 0) — the copy/version logic
- `website/backend/src/avatars/models.py` — new fields on `AvatarProfileDocument`

## Verification

- Two successive avatar generations for the same user produce `live_upload/avatars/<user_id>/001/` and `.../002/`, both fully intact, neither overwriting the other.
- `run_manifest.json` in each version folder correctly points to its source `clo_avatar_generation/output/...` run.
- `avatar_profiles` doc's path fields always point at the *latest* version after a regeneration.
- Confirm nothing under `live_upload/` gets committed to git (check `git status` after a test run).

## Execution Log

Not started.
