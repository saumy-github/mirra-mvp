# 03 - Backend behavior plan

**Status:** planned, being defined
**Created:** 2026-08-02

This file describes how the website backend should work from a product and launch-readiness point of view. It starts from what already exists in `website/backend/`, then records the decisions still needed before pilot launch.

## Section 1 - Users, registration, and authentication

### Current state: yes, auth already exists

The backend already has a real authentication system under:

```text
website/backend/src/auth/
website/backend/src/core/security.py
website/backend/src/core/auth_dependency.py
```

Implemented routes:

```text
POST /api/v1/auth/sign-up
POST /api/v1/auth/login
POST /api/v1/auth/guest
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
GET  /api/v1/auth/me
POST /api/v1/auth/verify-email
POST /api/v1/auth/password-reset
POST /api/v1/auth/password-reset/confirm
```

Implemented account types:

- normal email/password users
- guest users

Implemented session model:

- short-lived access JWT returned in the response body
- long-lived refresh token stored as an httpOnly cookie named `mirra_refresh`
- refresh token is stored hashed in MongoDB
- refresh tokens rotate on `/auth/refresh`
- logout revokes the refresh-token family
- password reset revokes existing sessions

Implemented security basics:

- password hashing with bcrypt
- JWT signing through `ACCESS_TOKEN_SECRET`
- refresh-token hashing with SHA-256 before storing in Mongo
- access token carried by frontend as `Authorization: Bearer <token>`
- refresh cookie scoped to `/api/v1/auth`

### Current pilot limitations

Email verification exists technically, but no email provider is wired yet.

Current behavior:

- signup creates a verification code
- verification code is logged server-side
- user submits code to `/api/v1/auth/verify-email`

This is acceptable for local/dev testing, but not good enough for public pilot onboarding unless we are okay manually reading codes from logs.

Password reset also exists technically, but no email provider is wired yet.

Current behavior:

- reset token is generated
- token is logged server-side
- user submits token to `/api/v1/auth/password-reset/confirm`

Again, this is a backend foundation, not a polished user-facing flow.

Google login is visible in the frontend, but not implemented end-to-end yet. The frontend has a Google button on the login page, but the live runtime provider currently returns a "not available" style error instead of completing OAuth.

Frontend login page exists:

```text
website/frontend/src/pages/auth/Login.tsx
Route: /auth/login
```

Current login page supports:

- Google button in the UI
- email/password form
- forgot-password link
- create-account link
- continue-as-guest action

Current frontend OAuth component:

```text
website/frontend/src/features/auth/components/oauth-buttons.tsx
```

The component currently includes a `GoogleButton`. The file is already Apple-ready in layout comments, but no Apple button/provider is wired.

### Product decision: locked for pilot launch (2026-08-04)

Login methods for the first public pilot:

```text
Google OAuth plus guest only
```

Email/password is explicitly excluded from the pilot UI (decided by Saumy, 2026-08-04). The backend implementation stays intact (Section 3) — only the frontend entry points go away, and by comment-out rather than deletion.

Reason:

- guest mode keeps the funnel low-friction
- Google OAuth reduces signup friction and gives returning users a stable, pre-verified account without us owning password storage/reset/email delivery
- removes the email-provider dependency (Resend/Postmark/etc., see "Email decision needed before pilot" below) as a pilot launch blocker entirely — nothing in the pilot path sends email
- removes the Google/password account-linking question from the OAuth plan below, since OAuth becomes the only way to create a non-guest account for pilot (see the updated "Account-linking" note under Google OAuth plan)

### Google OAuth plan

Google OAuth should become another way to create or log into the same internal Mirra user account.

Flow:

1. User clicks `Continue with Google` on `/auth/login` or `/auth/sign-up`.
2. Frontend redirects the browser to a backend route such as:

```text
GET /api/v1/auth/google/start
```

3. Backend redirects the user to Google's OAuth consent screen.
4. Google redirects back to the backend callback route with a temporary code:

```text
GET /api/v1/auth/google/callback
```

5. Backend exchanges the code with Google for tokens.
6. Backend verifies Google's identity token.
7. Backend finds or creates a Mirra user by Google's stable user id and/or verified email.
8. Backend issues the same Mirra session shape used by email/password login:

- access JWT in response/redirect handoff
- httpOnly refresh cookie
- internal `users` document in MongoDB

Recommended backend fields:

```json
{
  "_id": "u_...",
  "email": "user@gmail.com",
  "name": "User Name",
  "is_guest": false,
  "email_verified": true,
  "auth_providers": [
    {
      "provider": "google",
      "provider_user_id": "google-sub-id"
    }
  ]
}
```

Required backend env on Render:

```env
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
GOOGLE_REDIRECT_URI=https://<render-backend-domain>/api/v1/auth/google/callback
FRONTEND_AUTH_SUCCESS_URL=https://<vercel-domain>/auth/callback
FRONTEND_AUTH_FAILURE_URL=https://<vercel-domain>/auth/login
```

Required local dev env:

```env
GOOGLE_CLIENT_ID=<dev Google OAuth client id>
GOOGLE_CLIENT_SECRET=<dev Google OAuth client secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_AUTH_SUCCESS_URL=http://localhost:3000/auth/callback
FRONTEND_AUTH_FAILURE_URL=http://localhost:3000/auth/login
```

Frontend work required:

- make `GoogleButton` start the real backend OAuth redirect in live mode
- add an `/auth/callback` route if needed to finish post-login routing
- preserve `next` redirect behavior after successful login
- show a clear error if OAuth fails or is cancelled
- comment out the email/password login form, sign-up page, forgot-password link/page, and email-verification OTP page (file list under Section 2)

Backend work required:

- add Google OAuth config fields
- add Google start/callback routes
- add provider identity fields to the user model
- issue the same access-token/refresh-cookie session after OAuth login
- add tests for new-user Google signup and returning Google login

Account-linking: simplified for pilot (decided 2026-08-04)

Because email/password is commented out on the frontend, Google OAuth becomes the **only** way to create a non-guest account for pilot. There's no live population of email/password accounts a new pilot signup could collide with, so the original "does this Google email match an existing password account" question doesn't need matching/linking logic for launch:

- no automatic-linking-by-email logic needed
- no "log in with password first, then link Google" flow needed
- any stray email/password account from earlier dev/testing simply becomes unreachable via the UI — acceptable for pilot, since the backend route still exists (Section 3)

This removes matching against *other password accounts*, but not all matching concerns. A separate, still-open question is matching a **guest session** to a **new Google identity** when a guest later signs in — see Section 8, "Guest → Google upgrade path."

Apple Auth:

- Do not implement Apple in the first pilot unless there is a strong iOS-specific need.
- Apple usually requires Apple Developer Program setup, currently $99/year.
- Keep the UI/code structure Apple-ready, but focus engineering time on Google first.

### Email decision needed before pilot

If public users can sign up with email/password, we should add a real email provider before production launch.

Options:

- Resend
- Postmark
- SendGrid
- AWS SES

Recommended pilot path:

```text
Use Resend or Postmark for verification and password-reset emails.
```

Backend changes required:

- add email provider configuration
- send verification email on signup
- send password-reset email on reset request
- stop relying on logs for user-facing codes/tokens
- keep logging only safe operational events, not raw secrets

### Cookie/CORS production check

For local development:

```env
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000
```

For Render + Vercel production:

```env
COOKIE_SECURE=true
CORS_ORIGINS=https://<vercel-domain>
```

Important check: because frontend and backend will be on different domains, we must verify refresh-cookie behavior in the deployed browser flow. The cookie is currently `SameSite=lax`, scoped to `/api/v1/auth`, and httpOnly. If refresh does not work across the Vercel/Render domain boundary, we may need to revisit cookie domain/SameSite settings or use a custom shared domain setup.

### Launch readiness checklist for auth

- signup works from Vercel frontend to Render backend
- login works from Vercel frontend to Render backend
- guest session works
- `/auth/me` restores the current user after page reload
- `/auth/refresh` works through the httpOnly cookie
- logout clears the session
- account deletion revokes refresh tokens
- password reset sends real email, or is intentionally disabled for pilot
- email verification sends real email, or verification is intentionally skipped for pilot
- `ACCESS_TOKEN_SECRET` is strong and only stored in Render env
- frontend stores access token only in memory, not localStorage

## Open sections to define next

## Section 2 - Pilot auth direction: OAuth + guest only (confirmed decision, 2026-08-04)

For the pilot launch, the user-facing auth flow is **Google OAuth plus guest**. Email/password is excluded from the UI entirely, but not deleted from the codebase.

Decision:

- keep existing backend email/password code for now (routes, service functions, Mongo fields all stay — Section 3 still applies)
- do **not** delete backend auth code during this phase
- **comment out** (not delete) the frontend email/password login form
- **comment out** the frontend email/password signup page
- **comment out** the forgot-password link/page from the normal user path
- **comment out** the email verification OTP page from the normal user path
- keep Google OAuth and guest as the only visible entry points
- defer Apple OAuth unless there is a specific launch requirement

Naming: this is **OAuth + guest**, not "OAuth-only" — guest mode stays visible and is a first-class pilot entry point, not a fallback.

### Frontend changes for pilot — exact file list

Read directly from the current code (`website/frontend/src/pages/auth/`):

- `Login.tsx` — comment out the `<form onSubmit={onSubmit}>` email/password block, the "or continue with email" `OrDivider`, the "Forgot password?" link, and the "Create account" link. Keep `GoogleButton` and the "Continue as a guest" button untouched.
- `SignUp.tsx` — comment out the page content. Becomes unreachable via UI once `Login.tsx`'s "Create account" link is gone; whether its route registration in `router.tsx` should also be commented out (vs. leaving the page reachable by direct URL) is an open call — see questions below.
- `ForgotPassword.tsx` — comment out the page content, same reachability question as `SignUp.tsx`.
- `VerifyEmail.tsx` — comment out. This page has nothing to do once password signup is gone: Google accounts arrive pre-verified (`email_verified: true` from Google) and guests have no email to verify.

Backend routes (`/auth/sign-up`, `/auth/login`, `/auth/verify-email`, `/auth/password-reset`, `/auth/password-reset/confirm`) are untouched — Section 3's "do not delete backend auth code yet" still governs.

Reason:

- OAuth reduces signup friction
- OAuth avoids password-reset and email-verification work for the first pilot
- keeping the backend code avoids risky deletion while the OAuth flow is still being wired
- after pilot stability, unused in-house auth code can be removed deliberately

## Section 3 - Do not delete in-house auth code yet

Even if the frontend hides email/password login, do not remove the backend implementation immediately.

Current backend email/password capabilities:

- bcrypt password hashing
- signup
- login
- password reset token generation
- email verification code generation
- refresh-token sessions

Safe migration order:

1. Hide email/password UI on the frontend.
2. Implement Google OAuth.
3. Verify Google OAuth issues the same Mirra access/refresh session.
4. Verify existing protected APIs still work after OAuth login.
5. Decide whether guest access remains available.
6. Remove unused frontend routes only after the OAuth path is stable.
7. Delete unused backend email/password code only in a later cleanup phase, if still desired.

Do not comment out backend routes casually. If routes must be disabled for production, prefer an explicit feature flag/env setting so local testing remains possible:

```env
ENABLE_PASSWORD_AUTH=false
ENABLE_GOOGLE_AUTH=true
ENABLE_GUEST_AUTH=true
```

## Section 4 - SPA routing, lazy loading, and smooth transitions

The website frontend is a React SPA.

Current state:

- route-level lazy loading already exists in `website/frontend/src/router.tsx`
- route transitions already exist in `website/frontend/src/components/providers/app-providers.tsx`
- pages are wrapped in `Suspense` with `PageFallback`

This is a good starting point. We do not need server-side rendering just to get smooth page transitions.

Frontend behavior target:

- keep route-level lazy loading
- keep route transition animation light
- avoid layout jumps between pages
- prefetch likely next routes where it materially improves UX
- keep shared layout/navigation stable
- do not load heavy 3D assets as part of every route

For a smooth app feeling, expensive work should happen after the route is visible:

```text
route transition first
then fetch data
then load heavy avatar/3D viewer only if needed
```

## Section 5 - Protected routes and access control

Backend protected APIs already exist.

Current backend pattern:

```text
Depends(get_identity)
```

The following domains use authenticated identity for private endpoints:

- users
- measurements
- avatars
- try-on
- signature looks
- capture sessions
- auth `/me`
- auth `/verify-email`

Analytics intentionally allows optional identity for some events.

Frontend state:

- there is no single central `ProtectedRoute`/`RequireAuth` wrapper yet
- several pages manually check account state and redirect to `/auth/login?next=...`
- profile layout has page-level auth redirect behavior
- Studio/onboarding pages also perform auth checks locally

Target frontend improvement:

Add a central route guard component:

```text
RequireAuth
```

Expected behavior:

- while account is loading, show page fallback/skeleton
- if not authenticated, redirect to `/auth/login?next=<current-path>`
- if authenticated, render the protected route

Routes that should be guarded:

- `/studio`
- `/onboarding/measurements`
- `/onboarding/avatar`
- `/profile/*`
- any future private avatar/try-on/history pages

Backend remains the source of truth. Frontend route guards improve UX but are not security boundaries.

## Section 6 - Security vulnerabilities and launch risks

Current good foundations:

- passwords are hashed with bcrypt
- access tokens are short-lived JWTs
- refresh tokens are httpOnly cookies
- refresh tokens are stored hashed in MongoDB
- access token is stored in frontend memory, not `localStorage`
- protected backend endpoints use bearer-token auth
- frontend validates live backend response shapes with Zod

Main pilot risks to fix or explicitly accept:

- Google OAuth is not implemented yet even though a Google button exists
- email verification codes are logged server-side instead of emailed
- password-reset tokens are logged server-side instead of emailed
- no visible rate limiting for auth endpoints
- no brute-force protection for login/signup/password reset
- no bot/abuse controls around future expensive avatar/VTO actions
- production `ACCESS_TOKEN_SECRET` must be strong and stored only in Render env
- production `COOKIE_SECURE` must be `true`
- production `CORS_ORIGINS` must be locked to the Vercel domain
- refresh-cookie behavior must be tested across the Vercel/Render domain boundary
- capture uploads need stricter validation before public launch
- upload/file storage on Render may not be durable unless Render Disk or object storage is configured
- no clear frontend security-header/CSP plan yet

Recommended pilot security checklist:

- implement Google OAuth before showing Google login
- hide password auth UI if OAuth-only is the product decision
- add auth rate limiting before public launch
- add upload size/type limits before public launch
- confirm production cookies work in browser after Vercel/Render deploy
- configure Render env secrets manually, not through committed files
- configure Vercel env with only public `VITE_*` values
- add a basic security headers plan for frontend/backend responses
- add monitoring/logging for auth failures and API errors

## Section 7 - SPA plus heavy 3D avatar risk

The SPA architecture itself is not the problem. The risk is loading and rendering heavy 3D assets in the browser.

Potential issues:

- large GLB/GLTF downloads
- slow first render
- mobile GPU memory pressure
- browser tab crashes on low-end devices
- long main-thread work during parsing/loading
- poor route transitions if 3D loads during navigation
- battery drain and device heat
- multiple avatars/viewers on one page causing memory spikes

Mitigation plan:

- lazy-load the 3D viewer only on pages that need it
- do not include the 3D viewer in the main app bundle
- show a thumbnail or lightweight placeholder before loading the model
- load the model after the page shell is visible
- use progress/loading states for large assets
- compress geometry with Draco or Meshopt if compatible with the chosen viewer
- compress textures with KTX2/Basis where possible
- generate lower-poly web preview assets instead of using the heaviest simulation output directly
- serve avatar/try-on assets through CDN/object storage eventually
- dispose Three.js/model-viewer resources when leaving the page
- avoid rendering multiple full 3D avatars at once
- test on mobile devices, not only desktop Chrome

Frontend target:

```text
SPA shell stays fast.
3D viewer is isolated, lazy-loaded, measured, and disposable.
```

Backend/storage target:

```text
Store final web-facing avatar/try-on assets separately from internal CLO pipeline artifacts.
Serve optimized web-preview assets to the browser, not raw debug artifacts.
```

## Section 8 - Guest identity and analytics tracking (added 2026-08-04)

Question raised: with pilot login reduced to Google OAuth + guest, how do we track guests and use their data for analysis?

### Current state (already built — confirmed by reading the code, not assumed)

Guests are not anonymous/sessionless — they already get a full persistent identity, same as a real user:

- `POST /api/v1/auth/guest` (`website/backend/src/auth/service.py::create_guest`) creates a real `users` collection document: `_id` prefixed `g_...`, `is_guest: true`, no email/password.
- That guest gets the exact same session mechanism as a real user: a short-lived access JWT plus an httpOnly `mirra_refresh` cookie, `kind: "guest"`, rotated/revoked the same way as a real user's session (`auth/service.py::_issue_tokens`).
- `Depends(get_identity)` (`website/backend/src/core/auth_dependency.py`) resolves guests exactly like real users on every protected route — measurements, avatars, try-on, signature looks, and capture sessions all already work identically for a guest `g_...` id as for a real `u_...` id.
- Analytics already carries identity: `POST /api/v1/analytics/events` uses `get_optional_identity`, and `AnalyticsEventDocument` (`website/backend/src/analytics/service.py`) stores `user_id`, `authenticated`, `session_id`, `properties`, `occurred_at`. The frontend already fires a `guest_started` event (`Login.tsx`) the moment someone continues as a guest.
- Net result: guest analysis is already possible today as a straight query — join `analytics_events` against `users` where `is_guest: true`. The full funnel (`guest_started` → `avatar_generation_started/completed` → `try_on_started/completed` → `add_to_cart_clicked`, etc.) is already attributable per guest id. No new instrumentation is required to start analyzing pilot guest behavior.

### Gaps found (not yet built, confirmed by searching the code)

1. **No guest → Google upgrade path exists.** There is no route or service function anywhere in `auth/routes.py` / `auth/controller.py` / `auth/service.py` that converts a `g_...` guest doc into a `u_...` Google-linked account while carrying forward its data (measurements, avatar, try-on history, analytics trail). Today, if a guest later signs in with Google, they get a brand-new, unrelated `u_...` identity — their guest activity becomes orphaned and unattributable to their real account.
2. **No retention/cleanup policy for guest docs.** Unlike capture sessions (`SESSION_TTL_MINUTES = 10` in `capture/models.py`), there is no TTL or cleanup job for `users` docs where `is_guest: true`, or for their linked `analytics_events`. Every "Continue as a guest" click creates a permanent Mongo document that never expires.
3. **No cross-device/cross-session continuity.** A guest's identity lives entirely in the `mirra_refresh` cookie. Clearing cookies, a different browser, or a different device creates a brand-new `g_...` guest with no link to the previous one — guest counts in any analysis will overcount unique people and undercount returning visits.
4. **No reporting/dashboard surface yet.** Analysis today means querying MongoDB directly (Atlas UI, `mongosh`, or a notebook/script) — there's no admin view or scheduled report. Not necessarily a pilot blocker at small scale, but worth naming rather than assuming it exists.

### Open questions — need a decision, not covered by this plan yet

- Should a guest be able to upgrade to a Google account and keep their existing avatar/measurements/analytics history? If yes, this needs new backend work — e.g. the Google callback checks for an existing guest session and re-parents its data into the new/matched `u_...` account instead of creating an unrelated one. This is real, unscoped work, not something the current Google OAuth plan (above) covers as written.
- Do we want a guest data retention window (delete/anonymize guest docs and their analytics after N days of inactivity), or keep everything indefinitely for the pilot given the small user base?
- Is direct Mongo/Atlas querying acceptable for pilot-scale guest analysis, or do you want a lightweight internal reporting view/script before launch?
- For the frontend file list in Section 2: should `SignUp.tsx` / `ForgotPassword.tsx` also have their **routes** commented out in `router.tsx` (fully unreachable, even by direct URL), or just have their content commented out while the route stays registered?

## Open sections to define next

- User profile behavior
- Measurements behavior
- Avatar generation behavior
- Capture/photo behavior
- Catalog/product behavior
- Try-on behavior
- Signature looks behavior
- Analytics behavior
- Admin/dev seed behavior
- Failure states and user-facing error behavior

## Execution Log

### 2026-08-02 - Started backend behavior plan

- Added initial auth/user-registration section based on the actual backend code.
- Confirmed the backend already supports signup, login, guest sessions, refresh, logout, `/me`, email verification, and password reset.
- Flagged email delivery and production cookie behavior as the main auth launch-readiness gaps.

### 2026-08-03 - Added pilot auth/security/frontend behavior decisions

- Added OAuth-only frontend direction for pilot launch while keeping backend email/password code intact for now.
- Added SPA lazy-loading/page-transition notes.
- Added protected-route current state and target `RequireAuth` direction.
- Added security launch-risk checklist.
- Added SPA plus heavy 3D avatar risk and mitigation plan.

### 2026-08-04 - Locked OAuth + guest as the only pilot login methods; added guest tracking research

- Confirmed decision: pilot frontend ships with Google OAuth and guest mode only; email/password UI is commented out (not deleted), matching Section 3's existing "do not delete backend code" rule.
- Identified the exact frontend files to comment out: `Login.tsx` (email/password form, forgot-password link, create-account link), `SignUp.tsx`, `ForgotPassword.tsx`, `VerifyEmail.tsx`.
- Simplified the Google OAuth account-linking question: since OAuth is now the only way to create a non-guest account for pilot, matching a Google login against existing password accounts is no longer needed at launch.
- Added Section 8 documenting guest identity/analytics: confirmed guests already get a full persistent identity and analytics attribution today (no new instrumentation needed to start analyzing guest behavior), but flagged three real gaps as unscoped open work — no guest→Google upgrade/data-merge path, no guest retention/cleanup policy, no cross-device guest continuity.

### 2026-08-04 - Google OAuth implemented (code complete, credentials still outstanding)

- Implemented the full "Google OAuth plan" from this doc: backend `auth/google/start` + `auth/google/callback` routes, `google_login()` find-or-create/link service logic, `AuthProvider`/`auth_providers` on the user model, and the frontend redirect + `/auth/callback` page.
- Reused the existing session/cookie machinery unchanged (`_issue_tokens`, `_set_refresh_cookie`) — no access token is ever passed through a URL; the callback sets the same `mirra_refresh` cookie every other login path uses and the frontend hydrates the session from it, same as the existing page-load bootstrap.
- Identity is established via Google's userinfo endpoint (using the access token from code exchange), not by verifying the id_token ourselves — avoids a JWKS/RS256 dependency for a pilot-scale login path.
- Verified: full backend app + OpenAPI schema still import cleanly with no regressions to existing routes; unconfigured-credentials path returns a clean 503 instead of crashing; state-mismatch and denied-consent callback paths correctly redirect to the frontend failure URL; frontend typecheck/build/lint all pass clean on every touched file.
- **Not verified**: the real Google consent screen round trip — no `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` exist yet (needs to be created in Google Cloud Console by someone with access, then set in `website/backend/.env` and Render's env settings).
- Explicitly **not** done in this pass: Section 2's email/password UI comment-out (OAuth and password auth currently coexist on the frontend), and the guest→Google merge gap from Section 8 (a guest's activity still doesn't carry over on Google login). Both remain open, separate work.
- Full implementation-level detail lives in [`08-step1-oauth-login.md`](08-step1-oauth-login.md)'s "What was implemented" section.
