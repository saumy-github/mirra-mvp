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

### Product decision needed before pilot

Decide which login methods are allowed for the first public pilot:

1. Email/password only
2. Guest only
3. Email/password plus guest
4. Add Google OAuth before launch

Recommended pilot path:

```text
Email/password plus guest plus Google OAuth
```

Reason:

- email/password gives returning users a stable account
- guest mode keeps the funnel low-friction
- Google OAuth reduces signup friction for users who do not want to create another password
- Google OAuth is usually free when implemented directly through Google's OAuth/OpenID Connect flow

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

Backend work required:

- add Google OAuth config fields
- add Google start/callback routes
- add provider identity fields to the user model
- implement account linking rules for existing email/password users
- issue the same access-token/refresh-cookie session after OAuth login
- add tests for new-user Google signup, returning Google login, and duplicate-email handling

Account-linking rule to decide:

- If Google returns a verified email that already belongs to an email/password user, either:
  - automatically link Google to that existing user, or
  - require the user to log in with password first and then link Google from account settings

Recommended pilot behavior:

```text
Automatically link only when Google reports email_verified=true.
```

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

## Section 2 - Pilot auth direction: OAuth-only UI

For the pilot launch, the user-facing auth flow should become OAuth-first/OAuth-only.

Decision:

- keep existing backend email/password code for now
- do **not** delete backend auth code during this phase
- hide or remove the frontend email/password login form
- hide or remove the frontend email/password signup form
- hide or remove the forgot-password link/page from the normal user path
- hide or remove the email verification OTP page from the normal user path
- implement Google OAuth as the first real OAuth provider
- defer Apple OAuth unless there is a specific launch requirement

Reason:

- OAuth reduces signup friction
- OAuth avoids password-reset and email-verification work for the first pilot
- keeping the backend code avoids risky deletion while the OAuth flow is still being wired
- after pilot stability, unused in-house auth code can be removed deliberately

Important nuance:

If guest mode remains visible, the pilot is not strictly OAuth-only. That may still be a good product choice because guest mode lowers friction, but it should be named clearly:

```text
OAuth + guest
```

not:

```text
OAuth-only
```

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
