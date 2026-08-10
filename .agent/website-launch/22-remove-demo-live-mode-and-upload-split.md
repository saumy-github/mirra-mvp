# 22 - Remove demo/live engine mode; split upload storage into dev_upload/ and live_upload/

**Status:** implemented and verified (2026-08-09) — Section E (dead-route removal) dropped from scope during review, not executed
**Created:** 2026-08-09
**Part of:** [07-step0-worker-queue.md](07-step0-worker-queue.md), [11-step4-avatar-pipeline-invocation.md](11-step4-avatar-pipeline-invocation.md), [12-step5-avatar-storage.md](12-step5-avatar-storage.md)

## Goal

The backend currently supports two avatar/try-on execution modes: `demo` (fake, timer-based state progression, no CLO/Redis/worker needed) and `live` (real CLO3D pipeline via the Redis/worker path built in docs 07/11/12). `demo` was the right choice while the live pipeline didn't exist — it let the rest of the product (auth, catalog, try-on UX, onboarding) get built and demoed without depending on a fragile single-Windows-machine CLO3D dependency.

Now that Steps 0/4/5 are live-verified end to end (doc 12's 2026-08-08 execution log — full worker round trip confirmed against real CLO3D), the demo/live split is no longer needed. The website (both the deployed production site and local developer testing of the website) should only ever use the real pipeline path. Separate, CLI-driven testing (`run_avatar.py`, `run_clo_vto.py`, `run_product_ingestion.py` — already exists, unchanged by this work) remains the way to test individual pipeline steps in isolation without going through the website at all.

Alongside this, storage needs to split by where the request came from: `live_upload/` becomes strictly production data (once a real path exists for a Render-hosted backend to receive files — not built yet, explicitly deferred, see "Out of scope" below), and a new `dev_upload/` holds everything generated during local website testing, which is what will actually be used day to day until that production path exists.

## Decisions made with the user before this plan

- Frontend mock mode (`VITE_INTEGRATION_MODE=mock`, the in-browser fixture layer with zero backend) is being removed too — a separate axis from backend demo/live, but the user wants it gone as part of the same "no fake data path" cleanup. Confirmed acceptable: without it, `npm run dev` alone only renders the marketing pages (Home/Pricing/Team); every app page needs the real backend running.
- `scripts/smoke_e2e.py` is being rewritten, not just adjusted — it currently passes in ~8s only because demo mode fakes the avatar/try-on timers. New scope: the flows that don't need CLO3D (guest auth, measurements CRUD, catalog browse, analytics, account-deletion cascade). Avatar/try-on generation is no longer smoke-tested automatically — that's covered by CLI runs and manual live tests against the real worker instead (same manual test pattern used in doc 12's 2026-08-08 execution log).
- The dev/live upload split is driven by an explicit env var, not inferred from the Mongo connection.
- **Object storage for a Render-hosted backend to receive GLBs from the local worker is a real, separate piece of work the user will plan themselves later.** This change does not attempt it — Render's avatar/try-on path stays non-functional until that's built, which the user has explicitly accepted for now. Traced during discussion: doc 02 ("Scope confirmed by Saumy") already lists "changing from demo engine mode to live CLO jobs" and "object storage migration for uploads/GLB files" under "Explicitly not in this phase," and its own Render/Vercel verification checklist assumed demo mode would stay on for that deployment specifically because of this gap. This plan supersedes that specific assumption for local/dev use, but the underlying Render filesystem gap doc 02 and doc 05 both flag is still real and still unsolved.

## Plan

### A. Backend: remove demo/live engine mode entirely

Every avatar/try-on request always goes through the real Redis→worker→CLO3D path. No mode field, no branching, no fake timers.

- `website/backend/src/config.py` — remove `avatar_engine_mode`/`tryon_engine_mode` settings.
- `website/backend/src/avatars/engine.py` and `website/backend/src/tryon/engine.py` — remove `engine_mode()` and `derive_demo_state()`; `start_job()`/`start_render()` become unconditional `enqueue(...)` calls (the existing `ServiceUnavailable` wrapping in `core/queue.py` already handles "Redis unreachable" sensibly — no new error handling needed).
- `website/backend/src/avatars/models.py` / `tryon/models.py` — remove `DEMO_*_SECONDS` constants and the `engine_mode` field from `AvatarJobDocument`/`TryonRenderDocument`. Safe schema change: neither model sets `extra="forbid"`, so existing Mongo docs with a leftover `engine_mode` key are read back fine, just ignored — no migration needed.
- `website/backend/src/avatars/service.py` / `tryon/service.py` — remove the demo-branch in `get_job()`/the render equivalent (the `if job.engine_mode == "demo":` block); state always comes straight from Mongo, written only by the worker.
- `website/backend/src/avatars/controller.py` / `tryon/controller.py` — drop `engineMode`/`kind` from the shaped API response.
- `website/backend/README.md` — remove the now-stale demo/live documentation section.
- `.agent/website-launch/02-phase-1-continuation-docker-env-and-local-db-plan.md` and `07-step0-worker-queue.md` — update the env var example blocks and any remaining "demo engine mode" references to match.

### B. Frontend: remove mock mode + the now-dead engine-mode UI

- `website/frontend/src/integrations/mirra-api/index.ts` — drop the `VITE_INTEGRATION_MODE` branch; always construct the real HTTP-backed provider.
- Delete `website/frontend/src/mocks/` entirely (`mock-provider.ts`, `store.ts`, `fixtures.ts`, `mock-runtime-provider.ts`) — this also fixes a bug found this session where the mock bundle ships in the production build regardless of mode, since it removes the static import entirely.
- Delete `website/frontend/src/features/auth/components/quick-access-control.tsx` (mock-only demo-login shortcut) and its usage site.
- Delete the `DemoModeNotice` component (`components/ui/misc.tsx`) and its one usage in `pages/onboarding/Avatar.tsx`.
- `integrations/engines/try-on/provider.ts` — drop the `VITE_TRYON_ENGINE_MODE` flag (confirmed this session: it currently only switches a label string, both branches already call the same real API methods) — collapse to the one real behavior.
- Remove `engineMode`/`kind` from the job/render TypeScript types (`integrations/mirra-api/types.ts`), Zod schemas (`schemas.ts`/`live-schemas.ts`), and any remaining UI branching on it — grep `engineMode` repo-wide during execution to catch every reference, since the API stops returning the field.
- Remove `VITE_INTEGRATION_MODE`/`VITE_AVATAR_ENGINE_MODE`/`VITE_TRYON_ENGINE_MODE` from `.env.example`/doc 02's example env blocks.

### C. Rewrite `scripts/smoke_e2e.py`

Trim to exactly what doesn't need CLO3D: guest signup → measurements submit → catalog browse → analytics event → account deletion, then the existing cascade-leftover-count check (harmless to leave checking avatar/tryon collections too — they'll just always be 0 now, still a valid check that deletion doesn't leave stray docs). Remove the `POST /avatars/generate` → `wait_for(... state == "ready")` block and the try-on session/render block entirely. Update `website/backend/README.md`'s smoke-test description to match.

### D. `dev_upload/` vs `live_upload/` split

- Add `app_env: Literal["development", "production"] = "development"` to `website/backend/src/config.py`'s `Settings` (mirrors the frontend's existing `VITE_APP_ENV` naming convention already used in `lib/analytics.ts`).
- `worker/live_upload.py` — generalize the hardcoded `LIVE_UPLOAD_AVATARS_ROOT` module constant into a function that reads `APP_ENV` from the worker process's own environment (set via `worker/.env`, same mechanism as `MONGODB_URI`/`REDIS_URL` today) and resolves to `REPO_ROOT / "dev_upload" / "avatars"` or `REPO_ROOT / "live_upload" / "avatars"` accordingly. Defaults to `dev_upload/` (development) if unset.
- Create `dev_upload/avatars/.gitkeep` + `dev_upload/.gitignore` (identical pattern to the existing `live_upload/.gitignore`: `avatars/*` ignored, `.gitkeep` tracked).
- Clear out `live_upload/avatars/u_001/` — everything currently in there is this session's own test data from local runs, not real production data; the user explicitly asked for `live_upload/` to start clean and hold only real production output going forward.
- Update `avatar_glb_path`'s docstring on `AvatarProfileDocument` (`website/backend/src/avatars/models.py`) to reflect "relative to whichever upload root is configured" instead of hardcoding `live_upload/`.
- Update this doc set (`12-step5-avatar-storage.md`, and `05-...md`/`07-...md` if they hardcode `live_upload/` paths) to document the `APP_ENV`-driven split.


## Out of scope (explicitly deferred by the user)

- Object storage bridge for a Render-hosted backend to receive GLBs from the local worker. Render's avatar/try-on generation stays non-functional until this is built; the user is planning this separately. `dev_upload/`/`live_upload/` are both local-disk folders under this plan — no S3/R2/cloud storage code is added here.
- Any change to the local dev backend's own Docker/Compose deployment story (doc 02's plan already covers this and isn't being revisited).

## Verification

- Backend: `python -m py_compile` on every touched file; `from src.main import app` import check; run the rewritten `scripts/smoke_e2e.py` against the real Docker backend — all checks pass without needing CLO3D/worker running.
- Frontend: `npx tsc --noEmit`, `npx eslint src --max-warnings=0`, `npm run build` — confirm the mock fixture strings (e.g. `"Google Demo"`) are gone from the built output, confirming `mocks/` is no longer bundled.
- `worker/live_upload.py`: a standalone unit test (same pattern used earlier this session) confirming `APP_ENV=development` resolves to `dev_upload/` and `APP_ENV=production` resolves to `live_upload/`.
- Manual: with CLO3D + the native worker running, repeat the same real end-to-end check already done this session (guest → measurements → `POST /avatars/generate` → poll to `ready` → `GET /avatars/profile`) — confirm it still works with no `engineMode` field anywhere in the responses, and that the artifact lands under `dev_upload/avatars/<user_id>/` (not `live_upload/`) since local testing defaults to `APP_ENV=development`.

## Execution Log

### 2026-08-09 - Implemented

Executed Sections A-D exactly as planned; Section E (the two dead backend routes) was removed from the plan during review and not touched.

**A — Backend demo/live removal**: `config.py`'s `avatar_engine_mode`/`tryon_engine_mode` gone; `avatars/engine.py` and `tryon/engine.py` rewritten to unconditionally enqueue (no `engine_mode()`, no `derive_demo_state()`); `DEMO_*_SECONDS` constants and `engine_mode` fields removed from both Mongo document models; the demo-branch in `avatars/service.py::get_job()` and `tryon/service.py::get_render()` removed (state is now a straight Mongo read); `engineMode`/`kind`/`demoNotice` dropped from both controllers' shaped API responses. `website/backend/README.md` and docs 02/07 updated to match.

**B — Frontend mock mode removal**: `VITE_INTEGRATION_MODE` branch gone from `integrations/mirra-api/index.ts` (always the real HTTP provider now); `mocks/` (fixtures.ts, mock-provider.ts, store.ts, placeholder.ts) and `mock-runtime-provider.ts` deleted entirely; `QuickAccessControl` (mock-only demo-login shortcut) deleted along with its usage in `Login.tsx`/`SignUp.tsx` and the now-dead `demoAccessDestination` helper; `DemoModeNotice` deleted from `components/ui/misc.tsx` and its usage in `Avatar.tsx`; `integrations/engines/try-on/provider.ts` collapsed to one behavior (dropped `VITE_TRYON_ENGINE_MODE`, the `mode` field, and the demo/live `engineVersion` ternary in favor of a fixed `"clo-vto"` constant shared with `live-schemas.ts::mapRender`); `engineMode`/`kind`/`demoNotice` removed from `live-schemas.ts`'s Zod schemas and mappers, with `mapProfile`/`profileFromMeasurements`'s hardcoded `"demo"` `engineVersion` replaced by a fixed `"clo-avatar"` constant. Also found and fixed during a repo-wide grep sweep (not originally itemized in the plan, but the same "no fake data path" cleanup): a `VITE_AUTH_PROVIDER`-gated "Demo mode — no email is actually sent" hint in `VerifyEmail.tsx` (now dead, only consumer of that flag), and stale doc comments in `avatar-figure.tsx` and `public-runtime-provider.ts` referencing the deleted `DemoModeNotice`/`VITE_INTEGRATION_MODE`.

**C — `scripts/smoke_e2e.py` rewrite**: trimmed to guest signup → measurements → catalog browse → analytics event → account deletion (cascade check kept as-is). Avatar generation, try-on session/render, hanger restore, and signature-look creation all removed — they depended on the demo timers or on each other's output (signature-looks needs a `renderId` from a completed try-on render). `website/backend/README.md`'s description updated to match.

**D — `dev_upload/`/`live_upload/` split**: `worker/live_upload.py`'s hardcoded `LIVE_UPLOAD_AVATARS_ROOT` replaced with an `_avatars_root()` function reading `APP_ENV` from the worker's environment (`"production"` → `live_upload/`, anything else/unset → `dev_upload/`). New `dev_upload/avatars/.gitkeep` + `dev_upload/.gitignore`. `live_upload/avatars/` cleared of this session's own test data (two folders, confirmed as this session's test artifacts, not user data) — starts clean, reserved for real production output once the (still unbuilt) object-storage bridge exists. `app_env` setting added to `website/backend/src/config.py` (not yet consumed by the backend itself, only by the worker directly via `os.environ` — Step 6's serving route will need it later). Docs 05/12 updated with pointers to this split.

**Verified**:
- Backend: `py_compile` + `from src.main import app` import checks on every touched file; backend image rebuilt (picks up the new `scripts/smoke_e2e.py`, which isn't bind-mounted) and the trimmed smoke test passed **7/7** against the real Docker backend + Mongo.
- Frontend: `tsc --noEmit`, `eslint --max-warnings=0`, and `npm run build` all clean; grepped the built `dist/` output and confirmed zero mock fixture strings (`"Google Demo"`, `InProcessMockProvider`, `demo-tryon-0.1`, `demo-avatar-0.1`) remain — the mock bundle is genuinely gone, not just unreachable.
- `worker/live_upload.py`'s `_avatars_root()`: directly tested all three `APP_ENV` states (unset, `"development"`, `"production"`) resolve to the correct root.
- **Full real end-to-end run** with CLO3D + the native worker running: created a real guest account, submitted measurements, called `POST /avatars/generate` — confirmed the response has no `engineMode` field anywhere (job creation or polling), the job reached `state: "ready"` in ~76 seconds via the real pipeline, `GET /avatars/profile` returned a real profile, and the artifact landed in `dev_upload/avatars/<user_id>/001/` (not `live_upload/`) exactly as expected since `APP_ENV` wasn't set (defaults to development).

**Not touched**: Section E's two dead routes (`POST /auth/password-reset/confirm`, `GET /users/me`) — dropped from the plan before execution, per the reviewed version of this doc.
