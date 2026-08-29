# 02 - What's left to be done

Status as of 2026-08-11, cross-checked against the actual code (not just doc status lines — see `01-how-ai-should-work.md` for why that distinction matters; several old docs, especially `06-avatar-vto-implementation-status.md`, are stale relative to what was actually built later). Grouped by who can safely work on it.

## Group A — CLO / worker territory (exactly one agent, ever, at a time)

**A1 + A2 + A3 are planned together in `04-clo-measurement-repoint-and-glb-serving.md`** (2026-08-15) — one agent, primary checkout, not a worktree (untracked `.env` files mean a worktree can't run the worker). All three re-verified against code that day and confirmed genuinely open.

### A1. Repoint the CLO pipeline's measurement read to `user_measurements` — **done 2026-08-19**, see `04-clo-measurement-repoint-and-glb-serving.md` execution log
`step_03_fetch_measurements.py` now tries `user_measurements` by `user_id` first, falls back to the old `measurements` collection if nothing's found there (additive lookup order only — nothing removed, per the 2026-08-19 ruling both collections stay permanently). `mirra_measurements/db.py` gained a sibling `get_user_measurements_collection()` accessor on the same client/database. `ctx.measurement_source` now records which collection actually answered (`mongodb:user_measurements` vs `mongodb:measurements`) instead of a bare `"mongodb"`. Verified via `py_compile` + import check; the `run_avatar.py --user-id u_001` regression path was reasoned through but not yet re-run live — folded into A3's live-run checklist.

**Blocks**: A3's end-to-end verification, and all of Group B's "actually generate an avatar for a signed-in user" work.

### A2. Step 6 — serve the generated GLB to the browser — **done 2026-08-19**, see `04-clo-measurement-repoint-and-glb-serving.md` execution log
- `website/backend/src/config.py` now resolves `avatars_upload_root` from `APP_ENV` (mirrors `worker/live_upload.py`'s `_avatars_root()` — `production` → `live_upload/`, else `dev_upload/`).
- `docker-compose.yml` bind-mounts both `./dev_upload:/app/dev_upload:ro` and `./live_upload:/app/live_upload:ro` into the backend container — **requires a rebuild+restart to take effect, not yet applied to the running container** (parent-owned per `01`, lane asked and is waiting).
- New `GET /api/v1/avatars/profile/glb` route (`routes.py`/`controller.py`/`service.py`): resolves `avatar_profiles.avatar_glb_path` against the resolved root (never client input, path-traversal-guarded), 404s (not 500) when there's no GLB yet, long-cache headers (`immutable`, since the path is version-scoped).
- Staleness: `avatar_profiles.source_measurements_version` is now actually populated (was always `None` before — `_materialize_profile` in `avatars/service.py` populates it from the job's measurement snapshot) and compared against the user's current `user_measurements.measurements_version`; surfaced via an `X-Avatar-Measurements-Stale` response header (`true`/`false`/`unknown`) rather than silently served.

**Blocks**: any real "show the avatar in the browser" work in Group B. **Still blocks A3** until the parent runs the Docker rebuild.

### A3. Live end-to-end verification once A1 + A2 land — **code landed 2026-08-19, live run not yet performed**
Blocked on the parent's `docker compose build backend && docker compose up -d backend` (A2's compose-mount change requires it). Once that's confirmed, the plan in `04` still applies: real signed-in user saves measurements → generate → worker picks it up → CLO3D runs → packed GLB lands in `dev_upload/` → `GET /avatars/profile/glb` actually serves it → confirm it opens in a real viewer, not just "the request didn't 404" (same standard as the earlier GLB verification) → re-run `run_avatar.py --user-id u_001` to confirm the old-collection CLI path still works unchanged.

### A4. Fix the same GLB-loading bug in the try-on/VTO pipeline (confirmed still unfixed)
`clo_vto/native_vto/step_12_texture_glb.py` loads the exported garment file as **binary** GLB (`GLTF2().load(...)`), but the plugin actually writes JSON-embedded glTF-separate — the identical root cause already found and fixed for avatars (`step_12_export_glb.py`'s pygltflib-based packing). This step's failure mode is silently non-blocking by design, so **a "successful" try-on pipeline run today doesn't guarantee a usable textured GLB came out** — confirmed still blocked per old-folder doc 16, never fixed. Needs the same class of fix: pack into a real self-contained binary `.glb` (or at minimum load via `GLTF2().load_json()` instead of assuming binary) before trusting any texture output.

### A5. Try-on render caching (avoid recomputing when a valid one already exists)
`tryon/service.py::request_render()` should check for an existing `ready` `tryon_renders` doc matching `(avatar_profile_id, size_id)` where the avatar hasn't regenerated since, and serve that instead of enqueueing a new CLO run. Not yet implemented — old-folder doc 15 confirms this is the one real gap in an otherwise-built Step 8. This is the actual "reduce CLO load" mechanism for try-on, and matters more once CLO is also serving real generation traffic (A1-A3).

### A6. Garment catalog pre-generation (Step 7) — substantial, not started
Every catalog entry today renders with the same single hardcoded placeholder pattern (`clo_vto/default_panels/dxf/`) regardless of `cloth_id` — the field is stored but never used to pick a different pattern. Old-folder doc 14's plan:
1. Run `product_ingestion` once per real garment style ahead of launch.
2. Copy the chosen pattern set + thumbnail into `live_upload/catalog/<cloth_id>/<size_id>/` (properly named, not raw run-numbered files).
3. Add `pattern_asset_path`/`thumbnail_url` to `SizeDocument`, populated from the above.
4. Update the seed/catalog script to seed these pre-generated entries instead of the current placeholder rows.
5. Point `clo_vto`'s pipeline at the selected item's `pattern_asset_path` instead of the `use_default_panels` flag.

Catalog *browsing* itself needs no CLO involvement (pure Mongo + thumbnail) — only the pre-generation step is CLO territory.

### A7. Try-on result storage + serving (Step 10) — mirrors A2, not started
`live_upload/tryon/<user_id>/<size_id>/<version>/` (`.zprj`, `.avt`, `.glb`, `run.log`, `run_manifest.json`), `result_glb_path`/`clo_run_id` fields on `TryonRenderDocument`, new `GET /api/v1/tryon/sessions/{id}/renders/{id}/glb` route (same ownership/cache-header pattern as A2). Depends on A4 (no point serving an untextured/broken GLB) and A6 (real garments to try on).

## Group B — Website/frontend work (safe to parallelize, no CLO involvement)

Items B1-B5 are scoped to **signed-in users only** — guest users are explicitly deferred (Group C).

### B1. Fix `ProfileAvatar.tsx`'s dead end — **done 2026-08-19**, see `05-delete-onboarding-consolidate-on-profile.md` execution log
Planned in `05-delete-onboarding-consolidate-on-profile.md` (folded into the `/onboarding` deletion — `/profile/avatar` now *absorbs* the generation flow rather than linking out to it).

`/profile/avatar` with no avatar yet shows static leftover copy from the deleted photo-capture feature with no button at all — confirmed 2026-08-15 (`ProfileAvatar.tsx:24-34`, zero buttons).

**Correction 2026-08-15**: this item's rationale said "nothing in the signed-in flow links to `/studio` today." Not true — `onboarding/Avatar.tsx:160` ("Use my saved avatar") does. What's actually true is that nothing under `/profile/*` links to Studio. The fix stands; the reasoning didn't.

**Done**: `ProfileAvatar.tsx` now runs the full generation phase machine in-panel and has real buttons ("Use my saved avatar", "Regenerate avatar", plus the existing delete action) for the saved-avatar case.

### B2. ~~Decide + wire the post-generation "continue" destination~~ → superseded, and the original was factually wrong — **done 2026-08-19**
**Corrected 2026-08-15 after reading the code** — planned in `05-delete-onboarding-consolidate-on-profile.md`.

This item claimed Continue goes to `/profile/measurements` and framed the work as a preference call. Both wrong:

- `router.tsx` registers exactly one onboarding route, `/onboarding/avatar`. **`/onboarding/measurements` and `/measurements` no longer exist.**
- `onboarding/Avatar.tsx` navigates to those deleted routes from **three** live call sites — line 98/226 (`goToMeasurements`, the Continue handler), line 169 ("update measurements"), and line 207 (the "Add measurements" CTA on the `measurements-required` phase, which is the first screen a signed-in user without measurements ever sees). All three 404 into `NotFound`. `tsc`/eslint can't catch it — route targets are string literals.

So this is a live broken-navigation bug, not a decision. **User decision 2026-08-15**: `/studio` shows the VTO, `/profile/measurements` takes measurements, and **the `/onboarding` pages are to be deleted completely** — everything consolidates under `/profile`. That deletion fixes the dead links by construction.

**Done**: `/onboarding` deleted entirely (`src/pages/onboarding/`, its router entry, its lazy import). `measurements-required` → `/profile/measurements`; post-generation Continue and "Use my saved avatar" → `/studio`. `Studio.tsx`'s avatar-less redirect repointed from the dead `/onboarding/avatar` to `/profile/avatar`. Verified no `/onboarding` route/navigate/import string survives in `src/` or the built `dist/`.

### B3. Wire generation trigger from `/profile/measurements`'s first save — scoped carefully
Auto-trigger only on the true first-time save (no avatar yet). **Do not** auto-trigger on every subsequent edit — CLO is concurrency=1; repeated tweak-and-save would queue up multiple real ~90s CLO runs. Keep "save" and "regenerate" separate explicit actions post-first-generation, matching `onboarding/Avatar.tsx`'s existing pattern.

### B4. Track in-flight job state so it survives navigation/refresh
Job ids currently only live in local component state — lost on leaving the page. Needs a way to ask "is there a job in progress for me" without already holding a job id (new backend surface — a "latest job" lookup or similar), not purely a frontend fix.

### B5. Loading UI on `/profile/avatar` — **done 2026-08-19**, see `05-delete-onboarding-consolidate-on-profile.md`
Reuse the existing `GenerationProgress`-style component from `onboarding/Avatar.tsx` rather than rebuilding it.

**Done**: `GenerationProgress` and `SynchronizedState` moved (not rewritten) from `features/onboarding/components/` to `features/profile/components/` and wired into `ProfileAvatar.tsx`'s panel-scale generation flow. Also added the B4-adjacent honesty note ("this takes about 90 seconds; leaving this page will lose track of the run") next to `GenerationProgress`, per doc 05's mitigation — B4 itself (persisting job state) remains open.

### B6. `RequireAuth` central route guard (doc 03 Section 5)
Several pages currently do their own manual "check account, redirect to `/auth/login?next=...`" logic independently (Studio, onboarding, profile layout). A shared `RequireAuth` wrapper would consolidate this. Pure frontend refactor, no backend/CLO dependency. Backend remains the real security boundary either way — this is a UX/consistency improvement, not a security fix.

### B7. Homepage (`/`) performance — lazy loading (doc 18, audit done, fixes not implemented)
Confirmed via a real production build, not assumed. Ranked by impact/effort:
1. Lazy-load below-the-fold `Home.tsx` sections individually (`RoiCalculator`, `Closure` are the easiest/lowest-risk).
2. Add `loading="lazy"` + explicit `width`/`height` to the Unsplash images in `ProductReveal.tsx`/`Closure.tsx` — cheapest, near-zero risk.
3. Gate the `LiquidMetal` WebGL shader (in `Hero.tsx`'s "Early Access" pill) behind visibility, or drop it — a GPU shader for a badge-sized decoration, mounted unconditionally above the fold.
4. Scope Lenis smooth-scroll to pages that actually use scroll-driven GSAP effects instead of every marketing route.
5. Investigate the `rotate-ccw-*.js` shared icon chunk (45.84 kB gzip) — confirm it's expected Rollup chunking vs. an accidental over-broad `lucide-react` import.

### B8. Comment out email/password UI for pilot — **done 2026-08-19**, see `06-pilot-auth-google-only-and-consent.md` execution log
`Login.tsx` keeps `GoogleButton` + "Continue as guest"; email/password form, "or continue with email" divider, "Forgot password?" and "Create account" links commented out (not deleted), each with a comment pointing at doc 06. `SignUp.tsx`, `ForgotPassword.tsx`, `VerifyEmail.tsx` bodies fully commented out and replaced with a minimal shell (`AuthShell`/`AuthHeading` + a link back to `/auth/login`). Routes stay registered in `router.tsx` (untouched — resolves doc 03's open sub-question the way doc 06 decided). Backend routes/logic for the in-house flow are fully intact and unmodified.

### B9. Fix the Google OAuth consent gap — **done 2026-08-19**, see `06-pilot-auth-google-only-and-consent.md` execution log
Fixed by reusing the *same* `PATCH /users/me/consents` call the email/password path already made, from the Google path too: `Login.tsx` now gates the Google button behind a consent checkbox and marks acceptance (`src/pages/auth/pending-consent.ts`, sessionStorage-backed since the OAuth flow is a full-page redirect) before handing off to Google; `AuthCallback.tsx` reads that flag back once the session hydrates and fires the identical `updateConsents({terms: true, privacy: true})` call, with the same best-effort failure handling the email/password path already had. No backend change was needed — `auth/service.py::google_login()` was read in full and left unmodified; the existing consent-write endpoint just wasn't being called from the Google path before. Verified via a server-side parity diff (both `sign_up()` and `google_login()` exercised directly, resulting Mongo docs diffed) — `consents` non-empty and identical in shape on both; the only field-set difference is the inherent password-only fields (`password_hash`, `verification_code`), not a bug.

## Group C — Guest user flow (explicitly deferred, not active work)

Noted here only so it isn't forgotten. Guests currently *can* reach `/profile/avatar` (Login page's "Continue as Guest" → `/studio` → auto-redirect; that redirect target was repointed from the deleted `/onboarding/avatar` to `/profile/avatar` on 2026-08-19, see `05`), unlike signed-in users pre-Group-B — so the guest path needs a different starting audit than Group B's, not the same one. When picked up, also folds in:
- **Guest → Google account merge/upgrade path doesn't exist** (doc 03 Section 8). A guest who later signs in with Google gets a brand-new, unrelated account — their guest activity (measurements, avatar, analytics trail) is orphaned, not carried over.
- **No guest retention/TTL policy** — every "Continue as guest" click creates a permanent Mongo doc that never expires (unlike capture sessions, which had a TTL before that feature was deleted).
- **No cross-device/cross-session guest continuity** — identity lives entirely in a cookie; a new browser/device/cleared-cookies is an entirely new, unlinked guest. Inherent to the current design, not a quick fix.

## Group D — Known, deliberately-accepted gaps (documented so they're not "discovered" as bugs later)

- **No migration for pre-existing real-user data** in the old `measurements` collection from before the `user_measurements` split.
- **No object storage bridge** for a Render-hosted backend — `live_upload/`/`dev_upload/` stay local-disk-only, user's own choice to defer.
- **Real Google OAuth credentials never provisioned.** Code is implemented and verified up to the point of needing a real `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` — requires a human with Google Cloud Console access; the actual consent-screen round trip has never been tested end-to-end.
- **`mirra_measurements/` package still exists at the repo root**, still directly imported by live pipeline code (not just old/dead website code) — deferred as its own focused pass, bundled with the also-deferred local-Mongo-container work since they're linked.
- **Local Mongo Docker container** — deferred; local dev backend still points at Atlas.
- **Frontend native dev flow (`npm run dev`) not re-verified** since the Docker-removal change (doc 19's own last line) — probably fine, worth a quick sanity check next time it's actually run, not urgent.

## Group E — Old dead-code items, never executed (old-folder doc 21)

**Removed 2026-08-19**, see `06-pilot-auth-google-only-and-consent.md` execution log:
- `POST /auth/password-reset/confirm` — dead backend route, no frontend caller. Removed from `auth/routes.py` (handler + now-unused schema import); `POST /auth/password-reset` (no `/confirm`, live) was re-confirmed untouched.
- `GET /users/me` — exact duplicate of `GET /auth/me`, unused. Removed the single `GET` handler from `users/routes.py` only; `PATCH /me`, `PATCH /me/consents`, `DELETE /me`, and the router/prefix are untouched and re-confirmed live.
- `ForgotPassword.tsx` — folded into B8 (comment-out), done alongside it.

**Verified 2026-08-19 — `smoke_e2e.py` now passes 7/7**, including `catalog browsable`, `account deleted`, and `cascade left nothing behind`. Group E is fully verified.

The blocker the lane reported (`AttributeError: 'SizeDocument' object has no attribute 'hem_width_cm'`) was real, pre-existing, and unrelated to the route removals — fixed by the parent session, see below.

### Pre-existing catalog bug, found and fixed 2026-08-19 (parent session, no lane)

`website/backend/src/catalog/models.py` declared `SIZE_MEASUREMENT_FIELDS` with **12** entries while `SizeDocument` declared only **10** — `hem_width_cm` and `wrist_width_cm` were added to the tuple and never to the model. `shape_garment()` iterates the tuple and `getattr`s each field, so **`GET /catalog/garments` returned 500 on every request**: garment browsing was entirely broken, independent of any of today's work.

The comment above those two entries ("Optional in the schema, so documents seeded before these existed report them as null") shows the intent was always two nullable model fields; only the tuple half of the change landed.

Fix: added `hem_width_cm: float | None = None` and `wrist_width_cm: float | None = None` to `SizeDocument`. Two lines, no behaviour change beyond ending the crash. Confirmed by the smoke test's `catalog browsable` check now passing.

## Group F — Security / launch-readiness checklist (doc 03 Section 6, not started)

Not urgent for local dev, genuinely blocking for a real pilot launch:
- No rate limiting on auth endpoints (login/signup/password-reset).
- No brute-force protection.
- No bot/abuse controls around expensive avatar/VTO actions (relevant now that generation actually costs real CLO time).
- Production `ACCESS_TOKEN_SECRET` — must be strong, Render-env-only, never committed.
- Production `COOKIE_SECURE=true` + `CORS_ORIGINS` locked to the Vercel domain — must be verified, not just configured.
- **Refresh-cookie behavior across the Vercel/Render domain boundary is untested** — frontend and backend will be on different domains in production; if refresh doesn't work cross-domain, cookie `SameSite`/domain settings need revisiting. Real risk, not theoretical.
- No frontend security-header/CSP plan yet.
- No monitoring/logging for auth failures or API errors.

## Updating this doc

Mark items done with a date and a pointer to the plan file that did the work (new numbered doc in this folder). Don't delete completed items — leave them as a record, same convention as the old folder.
