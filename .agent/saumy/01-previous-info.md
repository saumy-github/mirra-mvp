## Scope & constraints (confirmed by Saumy)

- CLO3D license: **Pro plan**, currently on a single machine. We are launching to a **small pilot user base** first. If it needs to scale, we upgrade to the Business plan and talk to CLO3D support then — not blocking this phase.
- CLO3D pilot machine: Saumy's own **Windows 11** desktop, **16GB RAM, RTX 4050 (6GB VRAM)**. Against CLO3D's published minimums (16GB RAM / 4GB VRAM) this clears the floor but sits below the *recommended* 12GB+ VRAM — watch for slowdowns or crashes on complex/heavy garments specifically; not expected to be an issue for simple T-shirt VTO at pilot scale.
- **Windows-only for now.** No Mac plugin work, no Mac build/verify — deferred until there's an actual second machine to run it on.
- **Plugin versioning:** any plugin change made as part of this initiative (starting with the Phase 2 GLB export work) ships as a new version file following the existing convention in `clo_workspace/versions/` — next one is **`v_1.3.1.json`**, not an in-place edit of `v_1.3.0.json`. Same shape as the existing version files: `plugin_version`, `status`, `platforms.windows`/`platforms.mac`, `changes.added/changed/fixed/known_issues`, `notes`.
- **Docker environment confirmed ready:** Docker Desktop 29.6.1 + Compose v5.3.0 already installed on the pilot Windows machine, WSL2 backend with Ubuntu as the default distro. No environment setup blocker for Phase 1.
- Stay away from Blender for now. CLO3D stays the only render/simulation engine unless something in this plan turns out to be a hard blocker.
- The 3 deleted `.agent/clo-avatar-vto/*.md` files (plan-movement.md, plugin-mac.md, plugin-windows.md) were an intentional deletion by Saumy. Not part of this plan, not to be touched.
- General repo cleanup is explicitly **not** a priority right now. Goal is to get things working end to end; polish comes after.
- Process for this folder going forward: each numbered plan file states what we're *about to do* before any code changes happen. Once executed, results/issues get appended to the same file under "Execution Log" rather than opening a new file.

---

## Phase 5 — CLO3D hosting research (no VM stood up yet — research + recommendation only)

**Goal:** answer "is there a free tier we can try CLO3D on," concretely, before spending money.

Findings:
- CLO3D's own system requirements (support.clo3d.com, April 2026): **16GB RAM minimum** (64GB+ recommended for heavy garments/animation), **GPU with 4GB VRAM minimum, 12GB+ recommended**. This rules out the smallest free-tier CPU-only instances outright (AWS `t2.micro`-class, Azure `B1s`-class, GCP `e2-micro` — none have a GPU).
- **No cloud provider offers a genuinely free GPU tier.** AWS, Azure, and GCP all gate GPU instances (AWS G4dn/G5 with NVIDIA T4/A10G; Azure NV-series with A10/T4; GCP N1+T4) behind paid billing. The closest thing to "free" is new-account trial credit (varies by provider/region/offer, time-limited, not guaranteed) — good enough for a short evaluation, not a real free tier to build on long-term.
- Un-researched and needed before committing money: whether the **Pro plan license activation** even permits running CLO3D on a cloud VM at all (node-locked vs. floating activation, whether the CLO3D installer/license server treats a cloud VM's hardware ID as a new machine each time it's re-provisioned). This is a real risk for a VM-based approach specifically, independent of the automated-use question already flagged in the earlier discussion.
- **Recommendation for the pilot given the small-user-base scope**: skip standing up a cloud GPU VM for now. Use the existing physical/dev machine that already runs CLO3D as the single worker for the pilot (matches the "small user base first" framing) — this sidesteps both the free-tier question and the license-activation-on-a-VM question entirely. Revisit cloud GPU VMs specifically when/if the pilot needs more than one always-on worker.

This phase produces no code changes — just this write-up, to close out the open question from the earlier discussion.

---


## Target file layout

Keep:

```text
docker-compose.yml
package.json
website/backend/Dockerfile
website/frontend/Dockerfile
```

Add/standardize:

```text
website/backend/.env.docker.dev
website/backend/.env.example
website/frontend/.env.docker.dev
website/frontend/.env.example
```

Do not keep long-term:

```text
.env.dev
```

Reason: root `.env.dev` was convenient for Compose interpolation, but it mixes backend secrets and frontend public config at repo root. Service-owned env files are easier for a beginner to reason about:

- backend env lives with backend
- frontend env lives with frontend
- deployment env lives in Render/Vercel dashboards


---


## Step 5 — Save the avatar to `live_upload/`

**Done:** none of this exists yet — no code writes anywhere outside `clo_avatar_generation/output/` today.

**Remaining:**
1. Create `live_upload/avatars/` folder + local `.gitignore` (matches the pattern `clo_avatar_generation/.gitignore` already uses for its own `output/`).
2. After a successful pipeline run, worker copies `.zprj`, `.avt`, the new `.glb`/`.gltf`, and `run.log` into `live_upload/avatars/<user_id>/<version>/` (version = next integer for that user, never overwritten).
3. Write `run_manifest.json` in that folder, pointing back to the source `clo_avatar_generation/output/<user_id>-<run_number>/` for full debug traceability.
4. Add the new fields to `AvatarProfileDocument` (`avatar_glb_path`, `source_measurements_version`, `generated_at`, `clo_run_id`) and populate them when the job completes.

---

## Step 6 — Show the avatar on the website, without reloading/re-running CLO

**Done:** `GET /api/v1/avatars/profile` already exists and returns the profile shape — just needs the new path field once Step 5 exists.

**Remaining:**
1. New route `GET /api/v1/avatars/profile/glb` (`avatars/routes.py` + `controller.py`), same `FileResponse` + ownership-check pattern `capture/controller.py::get_photo` already uses.
2. Bind-mount `live_upload/` read-only into the backend container (`docker-compose.yml`), add `live_upload_dir` to `config.py` (same shape as the existing `uploads_dir`).
3. `Cache-Control: private, max-age=<long>, immutable` response header, safe because the path is already version-qualified.
4. Frontend: lazy-loaded `<model-viewer>` (or equivalent) component, per doc 03 Section 7's SPA/3D guidance — not loaded as part of the main app bundle, not loaded during route transitions.
5. Staleness check: compare `avatar_profiles.source_measurements_version` to the live `measurements.measurements_version`; if they differ, show a "regenerate?" prompt instead of auto-regenerating.
6. Frontend never calls avatar generation on page load — only on the explicit "Create avatar" / "Regenerate" actions.

---

## Step 7 — Garment catalog (premade clothes)

**Done:**
- `sizes` collection + read-only `GET` catalog routes already exist (`catalog/service.py`, `catalog/routes.py`), with `cloth_id`/`cloth_label` grouping fields already in the schema.
- 10 seeded demo sizes exist (`website/backend/scripts/seed_sizes.py`) — pure measurement metadata, no garment styling behind them yet.

**Real gap found (not just missing fields):** every catalog entry today, regardless of `cloth_id`, renders using the same single hardcoded placeholder pattern set (`clo_vto/default_panels/dxf/`). `cloth_id` is stored but never used to pick a different pattern. "2-3 distinct t-shirt styles" doesn't work until this is wired.

**Remaining, per this round's decision to pre-generate before launch:**
1. Run `product_ingestion` (Step 2) once per real garment style/photo ahead of launch — produces `product_ingestion/output/<cloth_id>-<size_id>-<run_number>/` as usual.
2. Copy the chosen final pattern set + a product thumbnail into `live_upload/catalog/<cloth_id>/<size_id>/`, named properly (not raw run-numbered filenames) — per this round's decision, "with proper name and in the live upload folder also."
3. Add `pattern_asset_path` and `thumbnail_url` fields to `SizeDocument`, populated to point at the `live_upload/catalog/...` paths above.
4. Update the seed/catalog-population script so these pre-generated entries are what's actually seeded for launch, not the current placeholder measurement-only rows.
5. Change `clo_vto`'s pipeline to load patterns from the selected catalog item's `pattern_asset_path` instead of the `use_default_panels` flag/hardcoded folder.
6. Frontend: catalog browsing page needs no CLO involvement at all — pure Mongo read + thumbnail image.

---


## Step 8 — User selects avatar + garment + size, requests try-on

**Done — fully built in demo mode:**
- `POST /api/v1/tryon/sessions` and `POST /api/v1/tryon/sessions/{session_id}/renders` already exist, capturing a `garment_snapshot` of the catalog doc at request time and referencing `avatar_profile_id`.
- The "Hanger no-recompute" comment already in `tryon/models.py` describes exactly the cache-reuse behavior needed in live mode.

**Remaining:**
1. Before enqueueing a live render, check for an existing `ready` `tryon_renders` doc matching `(avatar_profile_id, size_id)` where the avatar hasn't been regenerated since — serve that instead of recomputing. This is the actual "reduce CLO load" mechanism for try-on.
2. Wire `tryon/engine.py::start_render` to Step 0's worker/queue instead of raising `ServiceUnavailable`.

---

## Step 9 — VTO pipeline invocation (worker → CLO)

**Done:**
- `clo_vto`'s 12-step native pipeline exists and is wired for the current single default-panel t-shirt.
- GLB export (`step_11_export_note.py`) and texturing (`step_12_texture_glb.py`) already exist in code.

**Blocking prerequisite found, not yet resolved:**
- `step_12_texture_glb.py` loads the exported file as binary `.glb` (`GLTF2().load(...)`, binary path) — but the plugin actually produces JSON-embedded glTF (same bug found in doc 01's avatar GLB testing). Because this step's failure mode is silently non-blocking by design, **a "successful" pipeline run today doesn't guarantee a usable textured GLB came out.** Must verify this against a real run and fix the loader (or switch to `.gltf` naming) before trusting any output from this step.

**Remaining:**
1. Resolve the blocking prerequisite above.
2. Once Step 7's catalog wiring exists, point pattern loading at `live_upload/catalog/<cloth_id>/<size_id>/` instead of `default_panels/dxf/`.
3. Confirm textures apply correctly (not grey/untextured) against a real garment + real avatar, per doc 01's Phase 3 verification plan.

---

## Step 10 — Save + serve the try-on result

Mirrors Steps 5 and 6 exactly, for try-on instead of avatar.

**Remaining:**
1. `live_upload/tryon/<user_id>/<size_id>/<version>/` — `.zprj`, `.avt`, `.glb`/`.gltf`, `run.log`, `run_manifest.json` pointing back to `clo_vto/output/...`.
2. Add `result_glb_path` and `clo_run_id` fields to `TryonRenderDocument`.
3. New route `GET /api/v1/tryon/sessions/{session_id}/renders/{render_id}/glb`, same `FileResponse`/ownership/cache-header pattern as Step 6.
4. Same frontend lazy-load/dispose discipline as the avatar viewer — never two full 3D viewers mounted at once (avatar + try-on side by side is a specific risk called out in doc 03 Section 7).

---

## Remaining work (post-implementation)

- `source_measurements_version` stays `None` until doc 09's `measurements_version` field is added — tracked there, not here.
- Step 6 (serving route) is the natural next step now that both the export and the storage logic are live-verified: `GET /api/v1/avatars/profile/glb` resolving `avatar_glb_path` against a new upload-root setting (mirroring `app_env`), per doc 05's "Serving strategy".
- The Render production path is still unbuilt (object storage bridge) — `live_upload/` stays empty in practice until that lands, per doc 22.

---

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

---

## Remaining work

1. **Before enqueueing a live render, check for an existing reusable result.** Query `tryon_renders` for a `ready` doc matching `(avatar_profile_id, size_id)` where the avatar hasn't been regenerated since that render was created (compare timestamps, or a version marker if you want to be precise — `avatar_profiles.generated_at` vs. the existing render's `created_at`/`completed_at`). If found, return that doc instead of creating a new job — this is the actual mechanism that keeps CLO load down for try-on, described in the models file but not yet built.
2. **Wire `tryon/engine.py::start_render` to Step 0's worker/queue** instead of `raise ServiceUnavailable(...)`.
3. No changes needed to the request/response shape — the existing endpoints already return the right document shape for both the "reused" and "new job" cases, since both are just a `TryonRenderDocument`.

---

