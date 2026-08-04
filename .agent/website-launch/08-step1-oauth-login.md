# Step 1 - OAuth login, email saved

**Status:** Google OAuth code implemented and verified (2026-08-04) — not yet reachable end-to-end, see "What's still needed before this actually works" below
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)

## Goal

Every step downstream of this one assumes a `user_id` already exists (guest or real). This step is what produces that identity for a real (non-guest) user.

## Where the actual plan lives

The full Google OAuth plan — flow, routes, session issuance, required env vars, account-linking decision, and the frontend comment-out plan for email/password — is already written in detail in [`03-backend-behavior-plan.md`](03-backend-behavior-plan.md):

- "Section 1 - Users, registration, and authentication" → "Google OAuth plan"
- "Section 2 - Pilot auth direction: OAuth + guest only" (confirmed decision, includes the exact frontend file list to comment out)
- "Section 8 - Guest identity and analytics tracking" (the guest→Google merge gap, directly relevant here — a guest who already generated an avatar before logging in currently loses that avatar on login, since there's no merge path)

Do not fork a second copy of that plan into this file — edit doc 03 directly if the OAuth plan itself changes, and only update this pointer if the *dependency shape* on it changes (e.g. if avatar generation needs a new field from the OAuth flow that doc 03 doesn't currently produce).

## What this step needs from doc 03, specifically

For the avatar/VTO flow to work, OAuth login must produce:
- a stable `user_id` (`u_...`) — already the shape doc 03 designs for
- `email_verified: true` on arrival (Google-verified) — already assumed by doc 03's account model

Nothing else from OAuth is a dependency for avatar generation — measurements, avatar jobs, and try-on are all already built to work identically for guest and real users (see Step 2 onward).

## What was implemented (2026-08-04)

The Google OAuth code path described in doc 03's "Google OAuth plan" is now built, following that plan's exact flow (backend redirect → Google → backend callback → session cookie → frontend `/auth/callback`). Scope was deliberately kept to *just* the OAuth wiring — the Section 2 decision to comment out the email/password UI was **not** touched in this pass; that's a separate, still-open task.

**Backend:**
- `website/backend/src/config.py` — added `google_client_id`, `google_client_secret`, `google_redirect_uri`, `frontend_auth_success_url`, `frontend_auth_failure_url` (defaults match doc 03's local-dev values). Documented in `website/backend/.env.example`.
- `website/backend/src/auth/models.py` — added `AuthProvider` (`provider`, `provider_user_id`) and `UserDocument.auth_providers: list[AuthProvider]`.
- new `website/backend/src/auth/google_oauth.py` — pure HTTP helpers (`build_authorize_url`, `exchange_code`, `fetch_userinfo`), no FastAPI/DB imports, matching the existing service-layer layering rule. Identity is established via Google's userinfo endpoint using the OAuth access token, not by verifying the id_token's signature ourselves — deliberate simplification to avoid adding a JWKS/RS256 dependency for a pilot-scale login path.
- `website/backend/src/auth/service.py` — added `google_login()`: finds an existing user by `(provider, provider_user_id)`, falls back to linking a matching verified-email account (the "automatically link only when Google reports `email_verified=true`" rule from doc 03), otherwise creates a new user. Reuses the existing `_issue_tokens` session machinery unchanged.
- `website/backend/src/auth/controller.py` — added `google_start`/`google_callback`, handling CSRF `state` + the post-login `next` redirect target via two short-lived (5 min) httpOnly cookies scoped to `/api/v1/auth/google`. On success, sets the **same** `mirra_refresh` cookie every other login path already uses (`_set_refresh_cookie`, unmodified) and redirects to `FRONTEND_AUTH_SUCCESS_URL` — no access token is ever put in a URL.
- `website/backend/src/auth/routes.py` — added `GET /auth/google/start` and `GET /auth/google/callback`.
- `website/backend/src/db.py` — added a `(auth_providers.provider, auth_providers.provider_user_id)` index.

**Frontend:**
- `website/frontend/src/integrations/mirra-api/http-runtime-provider.ts` — `loginWithGoogle()` now does a real full-page redirect to `${apiBaseUrl}/auth/google/start` (reads `next` from the current URL's query string) instead of throwing `api_degraded`. The returned promise intentionally never resolves — the browser navigates away.
- new `website/frontend/src/pages/auth/AuthCallback.tsx` + registered at `/auth/callback` in `router.tsx` — lands after the Google round trip, hydrates the session from the refresh cookie the backend already set (via a new `completeOAuthCallback()` helper in `hooks/use-shopper.ts`), then routes to `postAuthDestination(next)`.
- `website/frontend/src/pages/auth/Login.tsx` — shows an error banner when the callback redirects back with `?error=...` (denied consent, state mismatch, or an exchange failure).
- `SignUp.tsx`'s existing `GoogleButton` needed no changes — it already calls the same `google.mutateAsync()` mutation, which now performs the redirect automatically.

**Verified (in this sandbox, not the pilot Windows machine):**
- Full backend app + OpenAPI schema import cleanly with the two new routes present alongside every pre-existing route (no regressions).
- `GET /auth/google/start` with no `GOOGLE_CLIENT_ID`/`SECRET` configured correctly returns a clean `503 google_not_configured` instead of crashing (matches the "refuse cleanly" pattern already used by `avatars/engine.py`/`tryon/engine.py`).
- With test credentials set: `/auth/google/start` redirects to the correct Google authorize URL with `state`/cookies set as designed; `/auth/google/callback` correctly rejects a state mismatch and a denied-consent (`error=access_denied`) callback, redirecting to the frontend failure URL with the right `?error=` code.
- Frontend: `npm run typecheck`, `npm run build`, and `eslint` on every touched file all pass clean.
- **Not verified**: the actual Google consent screen round trip end-to-end, since that requires a real `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` from Google Cloud Console, which nobody has provisioned yet — see below.

## What's still needed before this actually works

1. **A real Google OAuth client.** Create one in Google Cloud Console (OAuth consent screen + Web application client), add both redirect URIs (`http://localhost:8000/api/v1/auth/google/callback` for local dev, the Render domain's equivalent for production), then set `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` in `website/backend/.env` (local) and Render's env settings (production). Nothing in this codebase can create that client — it requires a human with access to the Google Cloud Console project.
2. **A real end-to-end test** against that client once it exists — click through the actual Google consent screen and confirm a session lands correctly, for both a brand-new Google account and a returning one.
3. **The Section 2 decision (comment out email/password UI) is still separate, unimplemented work** — intentionally out of scope for this pass. OAuth and email/password currently coexist on the login/signup pages.
4. **The guest→Google merge gap (doc 03 Section 8) is still unaddressed** — a guest who signs in with Google today gets a brand-new, unrelated account; their guest activity isn't carried over. Not touched in this pass.

## Execution Log

### 2026-08-04 - Google OAuth backend + frontend implemented

Implemented per doc 03's plan, verified as described above. See doc 03's own execution log for the OAuth-plan-level summary; this file holds the implementation-level detail since the work landed here.
