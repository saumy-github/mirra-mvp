# 05 - Avatar generation + VTO live pipeline: high-level flow

**Status:** planned, not yet executed. **Note:** the `demo`/`live` engine-mode distinction this doc references throughout was later removed entirely (every request always runs the real pipeline), and `live_upload/` below now specifically means *production only* — local/dev testing uses a sibling `dev_upload/` instead, selected by `APP_ENV`. See [22-remove-demo-live-mode-and-upload-split.md](22-remove-demo-live-mode-and-upload-split.md). The folder structure and serving strategy below are otherwise still the target.
**Created:** 2026-08-04
**Continues:** [01-docker-and-clo-render-pipeline.md](01-docker-and-clo-render-pipeline.md) (GLB export findings), [03-backend-behavior-plan.md](03-backend-behavior-plan.md) Section 8 (guest tracking)

This file is the end-to-end flow for turning a logged-in user into a rendered 3D avatar, and that avatar into a try-on result, using the real `live` engine (not the current `demo`-mode staged timers). [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md) breaks this same flow into "done" vs. "remaining" per step, for building it one piece at a time.

## Decisions locked this round (2026-08-04)

- **`run.log` is part of every production run**, same as the existing `clo_avatar_generation`/`clo_vto` pipelines already do for their own dev runs. Every avatar/try-on version saved to disk includes its `run.log` so a broken run can be diagnosed after the fact.
- **No separate "publish" copy into `website/backend/uploads/`.** Earlier drafts of this plan (see doc 01) proposed copying just the GLB into the backend's own uploads folder to keep CLO's output and the web-served asset separate. That's now rejected to avoid duplicate storage — the backend serves the GLB **directly from `live_upload/`** instead. See "Serving strategy" below for how the backend container reaches that folder.
- **Versioned folders per user, kept** — not overwritten in place. Every regeneration gets a new version directory; nothing is deleted automatically.
- **Disk headroom is not a near-term concern** — 10+ GB was freed on the pilot machine since the Docker Desktop disk-exhaustion incident (doc 01's execution log). A retention/cleanup policy is still worth having eventually, just not urgent for launch.
- **The garment catalog is pre-generated before launch, not on demand.** `product_ingestion` (Step 2) runs ahead of time for each real garment style, and the resulting pattern files are copied into `live_upload/` too, under their own catalog-facing names — the live VTO pipeline never invokes Step 2 at request time.

## End-to-end flow

1. **User logs in via Google OAuth.** Email/name/`google_sub` saved on the `users` document (see `03-backend-behavior-plan.md` for the OAuth plan itself — this file assumes that login already happened and a `user_id` exists, guest or real).
2. **User fills in a measurements form.** Saved to the `measurements` collection, one document per `user_id`, upserted on every submit.
3. **User clicks "Create avatar."** Backend creates an `avatar_jobs` document (`queued` state) with a snapshot of their current measurements, then hands the job to a queue.
4. **A worker process picks up the job and drives the CLO avatar pipeline.** The worker is a native Windows Python process (not containerized — it needs to talk to the CLO plugin at `localhost:50505` and drive `clo_avatar_generation/run_avatar.py` directly), running with concurrency = 1 because CLO itself is single-threaded regardless of what queueing sits in front of it.
5. **On success, the pipeline's outputs are saved into `live_upload/avatars/<user_id>/<version>/`** — `.zprj`, `.avt`, `.glb` (or `.gltf`, pending the naming decision below), and `run.log`. `<version>` increments per regeneration (`001`, `002`, ...); nothing is overwritten.
6. **The `avatar_jobs` doc is marked `ready`, and `avatar_profiles` is updated** with the path to the new version's GLB and the measurement snapshot it was built from.
7. **The frontend fetches the avatar directly from `live_upload/`** through an authenticated backend route — no separate copy, no re-invoking CLO. See "Serving strategy" below for exactly how.
8. **User opens the catalog**, browsing pre-generated garment styles/sizes — no CLO involved in browsing, just DB metadata plus a thumbnail image.
9. **User selects a garment + size and requests a try-on.** Backend creates a `tryon_renders` document (`requested` state), captures a snapshot of the selected catalog item, and — if no matching cached result already exists for this `(avatar_profile, size)` pair — hands the job to the same worker/queue as step 4.
10. **The worker drives the CLO VTO pipeline**, loading the user's existing avatar (no avatar regeneration) and the garment's pre-generated pattern files from `live_upload/catalog/...`.
11. **Results save to `live_upload/tryon/<user_id>/<size_id>/<version>/`** — same shape as avatars: `.zprj`, `.avt`, `.glb`, `run.log`.
12. **`tryon_renders` is marked `ready`**, and the frontend fetches the result GLB the same way it fetched the avatar — directly from `live_upload/` via an authenticated route.

## `live_upload/` folder structure

Lives at the repo root, sibling to `clo_avatar_generation/`, `product_ingestion/`, `clo_vto/`, `website/` — not nested inside any of the existing pipeline folders, and not reusing any of their `output/` directories.

```text
live_upload/
  avatars/
    <user_id>/
      <version>/                 # 001, 002, ... — one per regeneration, never overwritten
        avatar.zprj
        avatar.avt
        avatar.glb                (or avatar.gltf — see naming decision below)
        run.log
        run_manifest.json         # links back to clo_avatar_generation/output/<user_id>-<run>/ for debugging

  tryon/
    <user_id>/
      <size_id>/
        <version>/
          result.zprj
          result.avt
          result.glb               (or result.gltf)
          run.log
          run_manifest.json        # links back to clo_vto/output/... for debugging

  catalog/
    <cloth_id>/
      <size_id>/
        pattern set (DXF files, named to match clo_vto's expected panel names)
        thumbnail.jpg              # product photo for catalog browsing, no CLO involved
        manifest.json               # links back to product_ingestion/output/<cloth_id>-<size_id>-<run>/
```

Gitignore this the same way the existing pipeline folders already do — a local `live_upload/.gitignore` with `avatars/*`, `tryon/*`, `catalog/*` ignored and a tracked `.gitkeep`, plus explicit `*.avt`/`*.zprj` patterns added (the repo-root `.gitignore` already covers `*.dxf`/`*.glb`/`*.gltf`/`*.obj`/`*.svg`, but not `.avt`/`.zprj` yet).

## `run_manifest.json` traceability

Both `clo_avatar_generation` and `clo_vto` already write their own dev-side run identity/logs under their respective `output/` folders — `live_upload/`'s `run_manifest.json` is not a replacement for that, it's a pointer back to it, so a broken production run can always be traced to its full dev-side debug trail (raw pipeline logs, step-by-step results, error reports) without duplicating all of that into `live_upload/` itself. Only the final artifacts + `run.log` (the summary, not the full step trace) live in `live_upload/`.

## Serving strategy — direct from `live_upload/`, no duplicate copy

The backend (`website/backend`) runs in a Docker container; `live_upload/` is written by a native Windows worker process outside that container. For the backend to serve files from it directly (per this round's decision to skip the publish-copy step), the container needs read access to that folder:

- add a **read-only bind mount** to `docker-compose.yml`'s `backend` service: `./live_upload:/app/live_upload:ro` (repo root → container path), same mechanism already used for the `website/backend/src` hot-reload mount in doc 04's compose plan.
- add a `live_upload_dir` setting to `website/backend/src/config.py` (same pattern as the existing `uploads_dir`/`uploads_path`), pointing at `/app/live_upload` inside the container (or the real repo-root path for non-Docker local dev).
- new authenticated routes, following the exact pattern `capture/routes.py` already uses for serving photos (`FileResponse`, ownership-checked via `identity.user_id`):
  - `GET /api/v1/avatars/profile/glb` — serves the current user's latest-ready avatar GLB
  - `GET /api/v1/tryon/sessions/{session_id}/renders/{render_id}/glb` — serves a specific try-on result GLB
- both routes resolve the path from the Mongo doc's stored path field (see DB fields below), not from a client-supplied path — never trust a path built from user input.
- response headers: `Cache-Control: private, max-age=<long>, immutable` — safe because the path already includes the version number, so a real regeneration naturally produces a new URL instead of needing cache invalidation.
- **In production (Render), this bind-mount approach doesn't apply** — Render doesn't share a filesystem with the pilot Windows machine. For the pilot, backend + CLO worker are explicitly on the same machine (doc 01's decision), so this works as-is; moving the backend off that machine later means revisiting this (object storage, most likely) — not a pilot blocker, just a known limit of "serve directly from disk."

## Open naming decision, carried over from doc 01

The CLO plugin's `/export` endpoint produces valid glTF 2.0 that's JSON-embedded (starts with `{`), not true binary GLB, despite the `.glb` extension and `asGLB=true` parameter. Two options, still undecided:
- name these files `.gltf` (honest about the actual format), or
- keep `.glb` naming and make sure every loader (`step_12_texture_glb.py`, the new frontend viewer) reads the JSON-embedded path instead of assuming binary.

This affects every path in the folder structure above and the frontend `<model-viewer>` component — needs to be settled before Step 4/6 implementation in doc 06 below.

## DB field additions (summary — see doc 06 for per-step detail)

```text
measurements:
  + measurements_version: int          # incrementing, bumped on every submit/patch

avatar_profiles:
  + avatar_glb_path: str | None        # relative path under live_upload/avatars/...
  + source_measurements_version: int   # which measurement snapshot this avatar was built from
  + generated_at: datetime | None
  + clo_run_id: str | None             # traceability to clo_avatar_generation/output/<user_id>-<run>/

tryon_renders:
  + result_glb_path: str | None        # relative path under live_upload/tryon/...
  + clo_run_id: str | None

sizes (catalog):
  + pattern_asset_path: str | None     # relative path under live_upload/catalog/<cloth_id>/<size_id>/
  + thumbnail_url: str | None
```

## Non-goals for this pass (explicitly deferred)

- Guest → Google account data merge (an avatar generated as a guest doesn't currently carry over to a Google login afterward) — flagged in doc 03 Section 8, real work, not scoped here.
- Retention/cleanup policy for old `live_upload/` versions — not urgent given freed disk space, but should exist before this runs unattended for a long stretch.
- Object storage / CDN migration for served assets — fine to serve directly from disk for the pilot; revisit if the backend ever moves off the same machine as the CLO worker.

## Execution Log

Not started.
