# 01 - Docker for website services + CLO3D avatar/VTO render pipeline

**Status:** planned, not yet executed
**Created:** 2026-08-01

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

## Key discovery before planning (read from the actual code, not the docs)

The architecture docs say Step 3's render output format is "TBD" — that's stale. Reality, confirmed by reading the source:

- **Step 3 (VTO) already exports a textured GLB.** [`clo_vto/native_vto/step_11_export_note.py`](../../clo_vto/native_vto/step_11_export_note.py) calls the plugin's `POST /export` endpoint (`client.export_garment(path, format="glb")`), and [`step_12_texture_glb.py`](../../clo_vto/native_vto/step_12_texture_glb.py) injects per-panel textures/colors into it via `pygltflib`, producing `simulation_textured.glb`. This exists and is wired into the Step 3 pipeline already — it needs **verification that it actually runs end-to-end**, not new development.
- **The plugin itself already supports GLB/glTF export.** Both `RestPlugin_windows.cpp` and `RestPlugin_macOS.cpp` implement `cmd.type == "export"` → `EXPORT_API->ExportGLTF(path, options, asGLB)`, driven by `POST /export` with body `{"path": ..., "format": "glb"|"gltf"}`. This is the same CLO SDK feature visible in the File → Export → glTF 2.0 (GLTF/GLB) menu in the screenshot — it's scriptable, not just a manual menu action.
- **Step 1 (avatar generation) has no GLB export.** [`clo_avatar_generation/avatar_runtime/client.py`](../../clo_avatar_generation/avatar_runtime/client.py) only has `export_avatar_avt()` (the crash-prone `.avt` binary export). The 11-step Step 1 pipeline ([`pipeline.py`](../../clo_avatar_generation/avatar_runtime/pipeline.py)) ends at `step_11_save_outputs` with no GLB step. This is the actual gap for point 2 below — and it's a small addition, not a new capability, because the plugin-side `/export` endpoint Step 3 already uses will work for an avatar-only scene too.
- **Plugin build state is currently unstable.** Per `clo_workspace/versions/v_1.3.0.json`: Windows build is source-reviewed but **"NOT YET BUILT OR TESTED"**, Mac is **"pending"** (not rebuilt at all this cycle). Anything we add to the plugin should go on top of a build we've actually verified with `/health` and `/capabilities` first — otherwise we can't tell our new code from pre-existing breakage.

## Decision: where artifacts live (dev vs. website-triggered runs)

**Dev/CLI pipeline runs (unchanged):** `output/<user_id>-<run_number>/` and `output/<cloth_id>-<size_id>-<run_number>/` stay exactly as they are — full run trail (`.avt`, DXF/SVG, `run_summary.json`, `error_report.json`, `run.log`, and now the new `avatar.glb` / `simulation_textured.glb` from Phases 2–3). This is the pipeline's own debug/QA record regardless of how it was triggered, and it's what we already build tooling and troubleshooting docs around — no reason to change it.

**Website-triggered runs — what's actually web-facing vs. internal:**
- `.avt` files, `zprj` project files, and `run.log`/JSON step logs: **stay internal to `output/`, never copied anywhere else.** The browser can't render `.avt`, and raw logs aren't a user-facing artifact — job status/failure reasons are already surfaced through Mongo (`avatar_jobs`/`tryon_renders` documents already have `state` and `failure_reason` fields per `avatars/service.py` and `tryon/service.py`), not by exposing log files.
- Only the **GLB** (and later, maybe a thumbnail PNG rendered from it) needs to reach the web tier.
- Mirror the pattern the backend already uses for `capture` photos (`UPLOADS_DIR=uploads`, served through an authenticated route — see `backend-structure-plan.md`) instead of inventing a new storage convention: after a pipeline run completes, a "publish" step copies just the final GLB from `output/<run>/` into `website/backend/uploads/avatars/<user_id>/<job_id>/avatar.glb` (or `uploads/tryon/<user_id>/<render_id>/result.glb`), and the Mongo job/profile doc stores that relative path. The frontend fetches it through the existing authenticated-route pattern, not a raw filesystem path.
- Do this as an explicit **copy step**, not a shared-path assumption — even though the pipeline and the backend happen to be on the same machine today (see the open question below), a real "publish" step means this still works unchanged the day the backend moves to a different host and artifacts need an actual transfer instead of a local copy.

## Decision: how CLO jobs actually get processed (sync vs. queue)

Worth being precise here: **CLO3D itself is inherently single-threaded for API calls, independent of anything we build.** The plugin's whole design — read in `RestPlugin_windows.cpp` — is one `g_commandQueue`, drained by a single Win32 timer callback on CLO's main UI thread every 200ms. There is no way to get two avatar/VTO operations running concurrently against one CLO instance, no matter what queueing tech sits in front of it.

That changes the framing of "sync vs. queue" — it's not really a concurrency decision, it's just "how do we avoid holding an HTTP request open for however long CLO takes" (VTO simulation + export can run minutes; there's already a known issue of seams timing out past 60s). Recommendation:
- Still use a lightweight job queue (Redis + RQ, single worker process, concurrency = 1) rather than handling it synchronously inside the FastAPI request — not for parallelism (there isn't any to gain), but so the HTTP request returns immediately and the frontend polls, which is exactly the `queued → processing → ready` shape `avatars`/`tryon` already model in demo mode.
- Concurrency = 1 is the *correct* setting here, not a limitation being worked around — a second pilot user's job simply waits in FIFO order behind the first. Given "small pilot user base," this is fine; revisit only if queue depth becomes a real wait-time problem.

## Phase 1 — Dockerize `website/backend` and `website/frontend`

**Goal:** both services build and run in containers locally, talking to the existing Mongo Atlas `mirratest` database (no Mongo container — Atlas stays external). No behavior change to the app itself.

Plan:
1. Use [`Info.md`](Info.md) in this folder as the pattern reference (split containers, multi-stage frontend build, base compose + dev override, env-var-driven config).
2. `website/backend/Dockerfile` — Python image, install from repo-root `requirements.txt` (per [project_python_env](../../CLAUDE.md) convention — deps live in the root `requirements.txt`/`.venv`, not a per-service file), run via uvicorn (README already notes prod runs uvicorn/gunicorn workers, same app as `fastapi dev`).
3. `website/frontend/Dockerfile` — multi-stage: `npm ci && npm run build` in a builder stage, serve the static output from a small runtime image (nginx).
4. `docker-compose.yml` at repo root or under `website/` — wires backend + frontend, passes through the env vars already defined in both `.env.example` files (`MONGODB_URI` pointed at Atlas, `AVATAR_ENGINE_MODE`/`TRYON_ENGINE_MODE=demo` for now, `CORS_ORIGINS`, `VITE_API_BASE_URL`, etc.). No Redis/queue service yet — that's a later phase, not part of this one.
   - **Deploy target for the pilot (decided):** these containers run via **Docker Desktop on the same Windows 11 machine that runs CLO3D**, not a separate host. The future worker process talks to the plugin over `localhost:50505` directly — no tunnel/VPN/network bridge needed for this pilot. Revisit only when moving to public hosting or adding a second CLO worker.
   - **Ports (decided):** backend `8000`, frontend `3000` — same as the existing dev defaults already in both `.env.example` files, so nothing else in the codebase (CORS origins, `VITE_API_BASE_URL`) needs to change.
   - **Env file naming (decided):** any new env file created for this Docker work is named **`.env.dev`**, not `.env`/`.env.development` (those names stay reserved for the existing non-Docker local dev flow documented in the backend/frontend READMEs). Since `docker compose` only auto-loads a file literally named `.env`, the compose file/commands must reference `.env.dev` explicitly (`env_file:` per service, or `docker compose --env-file .env.dev ...`) — noting this now so it isn't a surprise later.
5. `docker-compose.override.yml` (or documented dev flags) for local bind-mounts/hot-reload, matching Info.md's base+override split.
6. Verify: `docker compose up`, hit `/api/v1/health` from the host, confirm the frontend build serves and can reach the backend through CORS.

**Explicitly not in this phase:** Redis/queue container, CLO3D worker, reverse proxy in front of both (can add later if needed), CI wiring.

**Forward-looking notes (not this phase's problem, but shapes how it's built so nothing needs reworking later):**
- The future CLO worker process will run as a **native Windows Python process** (using the existing repo-root `.venv`), not inside a container — it needs to drive `run_avatar.py`/`run_clo_vto.py` directly, write into the local `output/` folder, and reach the plugin at `localhost:50505`. Only backend, frontend, and (later) Redis get containerized.
- When Redis is added later, containers reach the CLO plugin on the Windows host via **`host.docker.internal:50505`**, not `localhost:50505` (which inside a container means the container itself). Irrelevant to Phase 1 itself since nothing in this phase calls the plugin, but worth designing the compose network config with this in mind from the start.
- Secrets (`MONGODB_URI`, `ACCESS_TOKEN_SECRET`, etc.) get passed to compose via a gitignored `.env` file at the compose root, never baked into the image layers.

## Phase 2 — Step 1: add avatar GLB export

**Goal:** after avatar generation + measurement application, produce a viewable `avatar.glb` for that user's digital twin — the concrete ask behind point 2 ("save the avatar_generated with proper measurement... in glb format").

Plan:
1. Rebuild and verify the current plugin (v1.3.0, Windows) first: `python clo_workspace/build_plugin.py`, confirm `/health` and `/capabilities` respond cleanly before adding anything on top. This directly follows from the "not yet built or tested" state found above — building blind on an unverified base makes any new bug ambiguous.
2. Add an `export_avatar_glb()` (naming TBD) method to `clo_avatar_generation/avatar_runtime/client.py`, mirroring `native_vto/client.py`'s existing `export_garment()` — same `/export` endpoint, `format="glb"`.
3. Add `step_12_export_glb.py` to the Step 1 pipeline (after `step_11_save_outputs`), following the same shape as Step 3's `step_11_export_note.py`: trigger export, `wait_for_queue`, verify file size, set `ctx.avatar_glb_path`, never block the pipeline on failure (same non-blocking pattern already used everywhere else in this codebase).
4. Register the new step in `pipeline.py`'s step list.
5. Test against a real measurement set, confirm the GLB opens in a standard viewer (e.g. `https://gltf-viewer.donmccurdy.com/` or `<model-viewer>` locally) before wiring anything on the backend/frontend side.

**Note:** since no garment is loaded at this point in the Step 1 flow, the plugin's hardcoded `bExportGarment = true` in the C++ export handler is harmless — there's nothing to export, it'll just produce an avatar-only GLB. Worth confirming this assumption once we test rather than trusting it blindly.

## Phase 3 — Step 3: verify the existing VTO GLB export actually works

**Goal:** confirm `simulation_textured.glb` is real and correct, not just present in the code.

Plan:
1. Run the full Step 3 pipeline (`python clo_avatar_generation/run_clo_vto.py`) against a real avatar + garment pair.
2. Confirm `step_11_export_note.py` produces `simulation.glb` and `step_12_texture_glb.py` produces `simulation_textured.glb` with textures actually applied (not grey/untextured).
3. Note any failures — this step already has defensive fallbacks (`pygltflib`/`Pillow` missing, GLB missing, etc.) that silently no-op, so a "success" pipeline run doesn't guarantee a usable GLB came out. Check the actual file, not just the log line.

## Phase 4 — Frontend: display the GLB

**Goal:** a working viewer component in `website/frontend`, first against a local test GLB, before any backend wiring.

Plan:
1. Add a GLB viewer to `website/frontend/src` — `<model-viewer>` web component is the fastest path (no React Three Fiber scene setup needed) and fits a 48-hour-shaped timeline better.
2. Point it at a GLB produced in Phase 2 or 3, served as a static file for now (no upload/storage pipeline yet — that's a later, separate concern once the demo→live engine mode work happens).
3. Confirm it renders correctly in a real browser, not just "the component mounts."

**Explicitly not in this phase:** wiring to the real `avatars`/`tryon` services, object storage, the queue/worker — those depend on decisions not made yet (see Open Questions).

## Phase 5 — CLO3D hosting research (no VM stood up yet — research + recommendation only)

**Goal:** answer "is there a free tier we can try CLO3D on," concretely, before spending money.

Findings:
- CLO3D's own system requirements (support.clo3d.com, April 2026): **16GB RAM minimum** (64GB+ recommended for heavy garments/animation), **GPU with 4GB VRAM minimum, 12GB+ recommended**. This rules out the smallest free-tier CPU-only instances outright (AWS `t2.micro`-class, Azure `B1s`-class, GCP `e2-micro` — none have a GPU).
- **No cloud provider offers a genuinely free GPU tier.** AWS, Azure, and GCP all gate GPU instances (AWS G4dn/G5 with NVIDIA T4/A10G; Azure NV-series with A10/T4; GCP N1+T4) behind paid billing. The closest thing to "free" is new-account trial credit (varies by provider/region/offer, time-limited, not guaranteed) — good enough for a short evaluation, not a real free tier to build on long-term.
- Un-researched and needed before committing money: whether the **Pro plan license activation** even permits running CLO3D on a cloud VM at all (node-locked vs. floating activation, whether the CLO3D installer/license server treats a cloud VM's hardware ID as a new machine each time it's re-provisioned). This is a real risk for a VM-based approach specifically, independent of the automated-use question already flagged in the earlier discussion.
- **Recommendation for the pilot given the small-user-base scope**: skip standing up a cloud GPU VM for now. Use the existing physical/dev machine that already runs CLO3D as the single worker for the pilot (matches the "small user base first" framing) — this sidesteps both the free-tier question and the license-activation-on-a-VM question entirely. Revisit cloud GPU VMs specifically when/if the pilot needs more than one always-on worker.

This phase produces no code changes — just this write-up, to close out the open question from the earlier discussion.

---

## Phase 2 findings (live plugin testing, before writing any Python)

Tested the plugin's `/export` endpoint directly (curl) against the running CLO3D instance before touching `avatar_runtime/client.py`, per the plan's "verify before building on top" step.

1. **Plugin v1.3.0 is actually already built, installed, and running** — the `versions/v_1.3.0.json` "NOT YET BUILT OR TESTED" note is stale. `/health` and `/capabilities` both respond cleanly (`plugin_built_at: 2026-07-23T09:56:16Z`).
2. **`POST /export {"format":"glb"} hangs indefinitely on a completely empty scene** (no avatar, no patterns loaded) — `queue_size` never drains, CLO's main thread visibly burns CPU (climbing, not idle) but never returns, `/health` stays responsive throughout (separate thread) so only that one command is wedged. Recovered by restarting CLO3D (confirmed nothing unsaved was open first). **Real bug, worth a known-issues note**, but not a blocker: the real Phase 2/3 use case always has an avatar loaded first.
3. **With a real avatar loaded** (ran Step 1's actual pipeline — `python clo_avatar_generation/run_avatar.py --user-id u_001 --non-interactive` — against golden user `u_001`), the export completed almost instantly and wrote a 52.8MB file. Steps 1-10 of that pipeline run all passed; step 11 (`save_outputs`) failed on a **pre-existing, already-documented** mesh-size quality check (`after-1-jun/plan-03.md Phase 6`, unrelated to GLB work) — the avatar was still fully present in the live CLO scene regardless.
4. **The exported file is not actually binary `.glb`.** Inspected the header — it's plain JSON starting with `{`, not the `glTF` binary magic. Parsed it directly as JSON: fully valid, well-formed glTF 2.0 (`asset.generator: "CLO Standalone OnlineAuth 2026.0.374"`, 9 meshes, 16 materials, 70 accessors, 1 buffer with a base64 `data:` URI holding 13.4MB of real geometry). This is the **JSON-embedded glTF variant**, not the binary container format — despite the plugin code passing `asGLB=true` as its own parameter into `EXPORT_API->ExportGLTF(path, options, asGLB)`. Root cause looks like CLO's SDK itself, not obviously fixable from our plugin code without more investigation.
   - **This affects Step 3's existing `step_12_texture_glb.py` too** — same endpoint, same `GLTF2().load(str(glb_path))` binary-load call on a `.glb`-named path. Very likely never actually worked end-to-end; its failure mode is silently non-blocking by design (`step_12` always returns `True`), so this would not have surfaced as a pipeline failure before now.
   - **Not a hard blocker.** Valid JSON-embedded glTF is fully spec-compliant and renders identically to binary `.glb` in `<model-viewer>`/three.js — just larger (base64 overhead ~33%). Practical fix on our side: either save/serve these as `.gltf` (correct extension for what they actually are) or keep `.glb` naming but load with `pygltflib`'s JSON path instead of `load_binary`. Doesn't require a plugin rebuild.
   - **Decision needed before writing the client method/pipeline step**: rename convention to `.gltf`, or keep `.glb` naming and just fix the loader call in both Step 1 (new) and Step 3 (`step_12_texture_glb.py`, existing)? Leaning toward `.gltf` since it's honest about the actual format, but this also touches Phase 4's frontend viewer expectations — worth deciding once, not per-step.

## Execution Log

### 2026-08-01 — Phase 1 first build attempt

- Created `website/backend/Dockerfile`, `website/frontend/Dockerfile`, `website/frontend/nginx.conf`, `website/frontend/.dockerignore`, root `.dockerignore`, root `docker-compose.yml`, root `.env.dev` (gitignored — added `.env.dev` to root `.gitignore`).
- Backend `Dockerfile` pinned to `python:3.12.10-slim` to exactly match the local `.venv` version.
- `docker compose --env-file .env.dev config` validated cleanly — no syntax errors, all `${VITE_*}` build-arg substitution resolved correctly.
- `docker compose --env-file .env.dev build` run in background:
  - **`mirra-mvp-frontend` built successfully — 117MB.**
  - **`mirra-mvp-backend` never finished.** `pip install -r requirements.txt` got stuck resolving `scipy`/`tensorflow`/`torch` version compatibility (pip's resolver backtracking across the loosely-pinned entries) and made zero progress across multiple checks over an extended period.
  - Docker Desktop's engine itself then went unresponsive — `docker images` and `docker stats` both returned `500 Internal Server Error` on the daemon's own `/_ping` endpoint. This is a daemon crash, not just a slow build.
  - Likely cause: WSL2 VM memory exhaustion — resolving/downloading `torch` + `tensorflow` + `transformers` + their CUDA/nvidia sub-packages simultaneously is heavy, and the pilot machine has 16GB RAM total (shared with whatever else is running, e.g. CLO3D).
  - Stopped the stuck build task. **Backend image build needs to be retried after Docker Desktop is restarted**, ideally with more WSL2 memory headroom (close other heavy apps during the build; consider raising the WSL2 memory limit via `.wslconfig` if this recurs).
- Outstanding: retry backend build, confirm both images build, then verify with `docker compose up` + health check (rest of Phase 1's plan, not yet reached).

### 2026-08-01/02 — tensorflow removal + Docker Desktop crash recovery

- Audited actual `tensorflow` usage repo-wide (case-insensitive search across all `.py` files): **zero real usage anywhere** — no `import tensorflow`, no `tf.` calls. The one apparent hit during an earlier import audit was a false positive (`gltf.` substring match in `step_12_texture_glb.py`). `torch`, by contrast, is genuinely used (`product_ingestion/segmentation.py` SAM2/U2Net inference, `utils/device.py` device selection).
- Removed `tensorflow>=2.3.0` from root `requirements.txt` — dead weight, and likely a contributor to the pip resolver backtracking (its own `numpy` constraints competing with the pinned `numpy==1.26.4`).
- Docker Desktop's engine crashed harder than initially thought: after the daemon started erroring with 500s, it went fully down (`npipe` connection failures — process wasn't running at all). Relaunched `C:\Program Files\Docker\Docker\Docker Desktop.exe` directly; engine came back (server 29.6.1 confirmed via `docker info`).
- **Verified the existing `mirra-mvp-backend:latest` image (3.97GB, created 2026-08-01T13:50) is stale** — inspected via `docker run --rm mirra-mvp-backend:latest pip show tensorflow`, confirmed it still has `tensorflow==2.21.0` installed, i.e. it predates the `requirements.txt` edit above. So the original build did eventually complete (not a hard hang, just very slow under memory pressure) — but it needs a rebuild now to actually drop tensorflow from the image.
- Next: rerun `docker compose --env-file .env.dev build backend` to get a lean image, compare size against the 3.97GB baseline.

### 2026-08-02 — Root cause found: C: drive nearly full, plus WSL2 vhdx bloat

- The real cause of everything above (build "hangs," Docker Desktop crashing to `500`s, and finally a hard pip `[Errno 5] Input/output error` writing `/usr/local/bin/convert-caffe2-to-onnx`) was the **Windows C: drive dropping to ~0.16GB free** (single 200GB drive — there is no separate D: drive; `D-drive-data` is just a folder name on C:). Repeated failed backend builds kept downloading/writing gigabytes (torch/tensorflow wheels) with nothing ever cleaning up after a crash.
- Saumy freed ~4.4GB via Windows Disk Cleanup (temp files, recycle bin) — enough to get Docker Desktop's processes running again, but the engine still returned `500`s: Docker Desktop was in a "zombie" state (outer app processes alive, inner Linux engine dead). Fixed by force-killing `Docker Desktop`/`com.docker.backend` processes, `wsl --shutdown`, then relaunching — this is the correct recovery path for that specific symptom (processes present, `/info`/`/_ping` still 500ing).
- Once the engine was back, `docker system df` showed **12.89GB reclaimable in images + 938MB in build cache** — almost entirely orphaned layers from the repeated `mirra-mvp-backend` rebuild attempts (that tag alone: 12.8GB on-disk vs 3.97GB actual content). Removed the stale image (`docker rmi mirra-mvp-backend:latest -f`) and ran `docker builder prune -af` — Docker-internal usage dropped from ~28GB to ~2.7GB.
- **That internal cleanup did not free any Windows-visible space** (`C:` stayed at 4.4GB free) — a known WSL2 behavior: deleting data inside the VM doesn't shrink the `.vhdx` file on the host automatically. Found the file at `%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`, sized **34.26GB** despite only ~2.7GB of real content.
- Fixed by stopping Docker Desktop + `wsl --shutdown`, then compacting the vhdx via `diskpart` (`select vdisk file=...` → `attach vdisk readonly` → `compact vdisk` → `detach vdisk`), then relaunching Docker Desktop. **vhdx dropped from 34.26GB to 5GB; Windows `C:` free space went from 4.4GB to 33.71GB.**
- **Takeaway for future Docker work on this machine:** if Docker Desktop starts acting up again (hangs, 500s, or slow builds) and there's been a lot of build churn, check `docker system df` and the `docker_data.vhdx` size before assuming it's a code/network problem — this exact vhdx-bloat-vs-host-free-space gap is likely to recur given this machine's small (200GB) single system drive, and the fix (prune + diskpart compact) is now a known playbook, not something to rediscover.
- Backend rebuild retried after full recovery (tensorflow removed + disk freed) — see next entry for result.

### 2026-08-02 — Backend build succeeded

- `docker compose --env-file .env.dev build backend` completed successfully. **`mirra-mvp-backend:latest` — 3.35GB content size** (down from the stale pre-fix image's 3.97GB).
- `pip` inside the image: **25.0.1**, pre-installed in `python:3.12.10-slim`, never upgraded (`requirements.txt` only requires `pip>=21.0`, already satisfied).
- Also cleaned up an unrelated project's leftover Docker resources found alongside ours in Docker Desktop (`nalum`/`alumni-*` containers, images `nalum-backend`/`mongo:7`/`postgres:16-alpine`/`redis:7-alpine`, 3 named volumes, and 4 confirmed-anonymous/unreferenced volumes) — Saumy had already deleted that project's source, these were just orphaned Docker state taking up space.
- **Both images now build successfully.** `mirra-mvp-frontend:latest` (117MB) and `mirra-mvp-backend:latest` (3.35GB) exist and are current.
- Outstanding for Phase 1: run `docker compose --env-file .env.dev up`, confirm `frontend` can reach `backend` through CORS, and hit `/api/v1/health` to confirm the container boots cleanly (DB will report unreachable until `MONGODB_URI` in `.env.dev` is pointed at the real Atlas URI — expected, matches existing non-Docker dev behavior).

### 2026-08-02 — Phase 1 verified: `docker compose up` works end to end

- `docker compose --env-file .env.dev up -d` — both containers created and started cleanly, no errors.
- `GET http://localhost:8000/api/v1/health` → `{"status":"ok","database":"unreachable"}`, HTTP 200. "unreachable" is expected — `.env.dev`'s `MONGODB_URI` is still the local placeholder, not the real Atlas URI.
- `GET http://localhost:3000/` → HTTP 200 (frontend serving).
- Backend logs show a clean uvicorn boot (`Application startup complete`, health check logged as `200 OK`) — the only log line is the expected Mongo connection failure, no crashes.
- **Phase 1 is done.** Remaining follow-up (not blocking): fill in the real `MONGODB_URI` in `.env.dev` (Atlas connection string) to get a fully connected backend — currently gitignored/placeholder by design.

### 2026-08-02 — Real Mongo URI wired in, Phase 1 fully closed out

- Saumy had the real Atlas URI already sitting in a pre-existing, separate `website/backend/.env.dev` (dated Jul 20, predates this session's Docker work — unrelated file, same name, worth not confusing the two going forward). Copied its `MONGODB_URI` into the root `.env.dev` (the one Compose actually reads).
- `docker compose --env-file .env.dev up -d` recreated just the `backend` container (env vars are baked in at container creation, not hot-reloaded) — `frontend` stayed untouched/running.
- `GET /api/v1/health` → `{"status":"ok","database":"connected"}`. Clean uvicorn boot, no errors in logs.
- **Phase 1 fully closed.** Both services build, run, and the backend reaches the real `mirratest` Atlas database from inside its container. Nothing outstanding for this phase.