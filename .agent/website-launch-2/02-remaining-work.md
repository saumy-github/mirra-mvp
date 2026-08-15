# 02 - What's left to be done

Status as of 2026-08-11, cross-checked against the actual code (not just doc status lines — see `01-how-ai-should-work.md` for why that distinction matters; several old docs, especially `06-avatar-vto-implementation-status.md`, are stale relative to what was actually built later). Grouped by who can safely work on it.

## Group A — CLO / worker territory (exactly one agent, ever, at a time)

**A1 + A2 + A3 are planned together in `04-clo-measurement-repoint-and-glb-serving.md`** (2026-08-15) — one agent, primary checkout, not a worktree (untracked `.env` files mean a worktree can't run the worker). All three re-verified against code that day and confirmed genuinely open.

### A1. Repoint the CLO pipeline's measurement read to `user_measurements`
`clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py` still reads the *old* `measurements` collection directly (via `mirra_measurements.db.get_measurements_collection()`), independent of anything the backend does. Real signed-in users now save to `user_measurements` instead (old-folder doc 23) — so today, a real user's `POST /avatars/generate` would run the pipeline, find nothing, and fail.

Proposed approach (old-folder doc 23, Part C — not yet implemented): try `user_measurements` first by `user_id`; fall back to `measurements` if nothing's found there. Keeps CLI/golden-user testing (`run_avatar.py --user-id u_001`) working unchanged.

Related: this same file (line ~150) and `product_ingestion/run_product_ingestion.py` (line ~42) both still import `mirra_measurements` directly — the old-folder doc 19 flagged deleting/migrating that whole package as bigger and riskier than first assumed, bundled with the (also deferred) local-Mongo-container work. Not blocking A1's fix, but touches the same file — worth doing in the same pass if convenient.

**Blocks**: A3's end-to-end verification, and all of Group B's "actually generate an avatar for a signed-in user" work.

### A2. Step 6 — serve the generated GLB to the browser
Old plan: old-folder doc 13, written before the `dev_upload/`/`live_upload/` split existed — needs updating for it (resolve whichever root `APP_ENV` selects, not one hardcoded `live_upload_dir`).

- Bind-mount the relevant upload root read-only into the backend container.
- New `GET /api/v1/avatars/profile/glb` route: resolve the path from `avatar_profiles.avatar_glb_path` (never client input), ownership-checked, long-cache headers.
- `source_measurements_version` staleness check (compare against `user_measurements.measurements_version`) — the field this depends on now exists on the live path, so this is actually unblocked, not still-theoretical.

**Blocks**: any real "show the avatar in the browser" work in Group B.

### A3. Live end-to-end verification once A1 + A2 land
Real signed-in user: save measurements → generate → worker picks it up → CLO3D runs → packed GLB lands in `dev_upload/` → `GET /avatars/profile/glb` actually serves it → confirm it opens in a real viewer, not just "the request didn't 404" (same standard as the earlier GLB verification).

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

### B1. Fix `ProfileAvatar.tsx`'s dead end
Planned in `05-delete-onboarding-consolidate-on-profile.md` (folded into the `/onboarding` deletion — `/profile/avatar` now *absorbs* the generation flow rather than linking out to it).

`/profile/avatar` with no avatar yet shows static leftover copy from the deleted photo-capture feature with no button at all — confirmed 2026-08-15 (`ProfileAvatar.tsx:24-34`, zero buttons).

**Correction 2026-08-15**: this item's rationale said "nothing in the signed-in flow links to `/studio` today." Not true — `onboarding/Avatar.tsx:160` ("Use my saved avatar") does. What's actually true is that nothing under `/profile/*` links to Studio. The fix stands; the reasoning didn't.

### B2. ~~Decide + wire the post-generation "continue" destination~~ → superseded, and the original was factually wrong
**Corrected 2026-08-15 after reading the code** — planned in `05-delete-onboarding-consolidate-on-profile.md`.

This item claimed Continue goes to `/profile/measurements` and framed the work as a preference call. Both wrong:

- `router.tsx` registers exactly one onboarding route, `/onboarding/avatar`. **`/onboarding/measurements` and `/measurements` no longer exist.**
- `onboarding/Avatar.tsx` navigates to those deleted routes from **three** live call sites — line 98/226 (`goToMeasurements`, the Continue handler), line 169 ("update measurements"), and line 207 (the "Add measurements" CTA on the `measurements-required` phase, which is the first screen a signed-in user without measurements ever sees). All three 404 into `NotFound`. `tsc`/eslint can't catch it — route targets are string literals.

So this is a live broken-navigation bug, not a decision. **User decision 2026-08-15**: `/studio` shows the VTO, `/profile/measurements` takes measurements, and **the `/onboarding` pages are to be deleted completely** — everything consolidates under `/profile`. That deletion fixes the dead links by construction.

### B3. Wire generation trigger from `/profile/measurements`'s first save — scoped carefully
Auto-trigger only on the true first-time save (no avatar yet). **Do not** auto-trigger on every subsequent edit — CLO is concurrency=1; repeated tweak-and-save would queue up multiple real ~90s CLO runs. Keep "save" and "regenerate" separate explicit actions post-first-generation, matching `onboarding/Avatar.tsx`'s existing pattern.

### B4. Track in-flight job state so it survives navigation/refresh
Job ids currently only live in local component state — lost on leaving the page. Needs a way to ask "is there a job in progress for me" without already holding a job id (new backend surface — a "latest job" lookup or similar), not purely a frontend fix.

### B5. Loading UI on `/profile/avatar`
Reuse the existing `GenerationProgress`-style component from `onboarding/Avatar.tsx` rather than rebuilding it.

### B6. `RequireAuth` central route guard (doc 03 Section 5)
Several pages currently do their own manual "check account, redirect to `/auth/login?next=...`" logic independently (Studio, onboarding, profile layout). A shared `RequireAuth` wrapper would consolidate this. Pure frontend refactor, no backend/CLO dependency. Backend remains the real security boundary either way — this is a UX/consistency improvement, not a security fix.

### B7. Homepage (`/`) performance — lazy loading (doc 18, audit done, fixes not implemented)
Confirmed via a real production build, not assumed. Ranked by impact/effort:
1. Lazy-load below-the-fold `Home.tsx` sections individually (`RoiCalculator`, `Closure` are the easiest/lowest-risk).
2. Add `loading="lazy"` + explicit `width`/`height` to the Unsplash images in `ProductReveal.tsx`/`Closure.tsx` — cheapest, near-zero risk.
3. Gate the `LiquidMetal` WebGL shader (in `Hero.tsx`'s "Early Access" pill) behind visibility, or drop it — a GPU shader for a badge-sized decoration, mounted unconditionally above the fold.
4. Scope Lenis smooth-scroll to pages that actually use scroll-driven GSAP effects instead of every marketing route.
5. Investigate the `rotate-ccw-*.js` shared icon chunk (45.84 kB gzip) — confirm it's expected Rollup chunking vs. an accidental over-broad `lucide-react` import.

### B8. Comment out email/password UI for pilot (product decision made 2026-08-04, still not executed)
Planned in `06-pilot-auth-google-only-and-consent.md` together with B9 and Group E — B8 makes Google the only signup path, and B9 is a confirmed bug in exactly that path, so shipping B8 alone would mean every pilot user signs up with no consent record. Doc 03's open sub-question is answered there: **keep the routes registered in `router.tsx`, comment out page content only.**

Old-folder doc 03, Section 2 — decided, never done. Exact file list already specified there: `Login.tsx` (comment out the email/password form, "or continue with email" divider, "Forgot password?" link, "Create account" link — keep `GoogleButton` + "Continue as guest"), `SignUp.tsx` (comment out page content), `ForgotPassword.tsx` (comment out page content), `VerifyEmail.tsx` (comment out — nothing left for it to do once password signup is gone). **Comment out, not delete** — backend routes and code stay intact per doc 03's own explicit rule. Open sub-question doc 03 never resolved: should the routes also be removed from `router.tsx` (fully unreachable) or just the page content (route stays registered, reachable by direct URL)?

### B9. Fix the Google OAuth consent gap (doc 20, confirmed real bug, not fixed)
Google signups never record `consents` — the field stays `{}` permanently, not just unpopulated but genuinely never touched by that code path (`auth/service.py::google_login()`). Compounding issue: the Terms/Privacy checkbox on `SignUp.tsx` only gates the email/password submit handler — the Google button's `onClick` doesn't check it at all, so consent isn't just unrecorded for Google users, it's never actually requested either. Two possible fixes outlined in doc 20 (gate the Google button behind the checkbox; and/or have `AuthCallback.tsx` fire the existing `PATCH /users/me/consents` once the session hydrates). Given B8 makes Google the *only* real signup path for pilot, this becomes more important, not less.

## Group C — Guest user flow (explicitly deferred, not active work)

Noted here only so it isn't forgotten. Guests currently *can* reach `/onboarding/avatar` (Login page's "Continue as Guest" → `/studio` → auto-redirect), unlike signed-in users pre-Group-B — so the guest path needs a different starting audit than Group B's, not the same one. When picked up, also folds in:
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

Low priority, no dependencies, safe filler for a parallel agent with nothing else queued:
- `POST /auth/password-reset/confirm` — dead backend route, no frontend caller.
- `GET /users/me` — exact duplicate of `GET /auth/me`, unused.
- `ForgotPassword.tsx` — folds into B8 now (comment-out decision already covers it).

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
