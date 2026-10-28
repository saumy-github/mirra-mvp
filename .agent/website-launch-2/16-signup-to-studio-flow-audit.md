# 16 - Signup / sign-in → onboarding → Studio flow audit

6 October 2026. Research only: no application code was changed. Read against the working tree (dirty, uncommitted onboarding work included), not just doc status lines.

## The flow as it actually runs today

- **New email signup** (`/auth/sign-up`) → `signupDestination` → `/onboarding/qr` → QR, phone capture, sync, intro, review → `/studio`.
- **New Google account** → backend callback adds `newAccount=1` only on creation → `/onboarding/qr` → same path.
- **Returning sign-in** (password or Google) → `/studio`, with no avatar-completeness check.
- **Guest** (`Continue as guest` on Login) → `/studio` → "Create your avatar to begin" → `/onboarding/qr`.
- **Studio without an avatar** shows a single empty state with one button. `/profile/*` is reachable from the header but is not part of the setup path.

## Findings

### P1 — broken or regressed

1. **Google consent gap is back (regression of doc 06 / B9, marked "done").** `AuthCallback.tsx` still calls `consumePendingConsent()`, but nothing calls `markPendingConsent()`: `Login.tsx` and `SignUp.tsx` no longer import it. Google accounts therefore get no consent record. `Login.tsx` also has no consent checkbox or terms/privacy links.
2. **Email/password is live again, contradicting doc 06 / B8 ("Google only for the pilot").** Shopper `Login.tsx` and `SignUp.tsx` render the full email+password form. Either the pilot decision changed and the docs are stale, or the comment-out was reverted by mistake. Needs a decision.
3. **Email signup consent is hardcoded.** `SignUp.tsx:35` sends `acceptedTerms: true` with no checkbox and no links to `/terms` or `/privacy`. Consent is recorded without being shown.
4. **Email accounts dead-end on verification and password reset.** `VerifyEmail.tsx` and `ForgotPassword.tsx` are stubs that say "Google accounts are already verified — nothing to do here". The backend still creates password users with `email_verified=False`, and `Profile.tsx:88` links unverified accounts to that stub page. Login has no "Forgot password?" link, so a password user who forgets it is locked out.

### P2 — flow design gaps

5. **No resume path from Studio for a half-finished setup.** Studio's empty state always links to `/onboarding/qr`, which resumes server state, which is fine. But the copy ("Add an avatar to preview pieces on you") doesn't say whether the user has a setup in progress, and a failed or blocked setup (Redis/CLO down) just looks like "no avatar". Surface the latest setup state in Studio ("Your avatar is building / needs review / failed — retry").
6. **Setup is not short-circuited by manual measurements.** `setup-flow.tsx` auto-starts a *photos* pairing whenever there is no setup and no avatar. A user who already saved measurements in Profile still gets a QR, and "manual" is a secondary link. Check `user_measurements` first and offer "Use my saved measurements".
7. **Guests run the full QR onboarding, then are orphaned.** No guest→account upgrade, no TTL (doc 02 Group C). Suggestion: prompt guests to sign in with Google *before* the QR step (so the photos and avatar attach to a real account), or at minimum before leaving setup.
8. **Studio header offers no way to (re)start avatar setup** once an avatar exists. Regenerate lives only in `/profile/avatar`; the doc says "a returning user can explicitly open avatar setup from Studio or Profile", but Studio only links to it from the empty state and the avatar stage fallback.
9. **Two avatar creation surfaces with overlapping logic.** `/onboarding/qr` (photos, QR, review) and `/profile/avatar` + `/profile/measurements` (manual measurements, `?generate=1`). Doc 05 says `/onboarding` was deleted; it was rebuilt as standalone setup on 5 Oct, so doc 05's "everything consolidates under /profile" is no longer true. Decide the canonical home and have the other redirect to it.
10. **`next` handling is inconsistent.** `postAuthDestination` allowlists paths, but `/onboarding/qr` is both an allowed `next` and the signup destination, and `shopperDestination` has special-case code to unwrap it. Fragile; simplify to one rule: signup/new-Google → setup, everything else → `next` or Studio.

### P3 — polish and ops

11. `RequireAuth` still does not exist (doc 02 B6). Studio, ProfileLayout and SetupFlow each redirect on their own, to *different* targets: Studio → `/auth/login`, SetupFlow → `/auth/sign-up`, Profile → `/auth/login`.
12. Sign-out from Profile goes to `/auth/login`; from Studio there is no sign-out in the header.
13. In-flight avatar job state is still lost on navigation (B4) — partly mitigated now by `getLatestAvatarSetup` for onboarding, but not for `/profile/avatar`.
14. Operational blockers from `design-qa-2026-10-05.md`, all still open: Redis/measurement workers not running, no `base-female.avt`, no physical-phone HTTPS test, no end-to-end CLO run, intro video placeholder (`VITE_ONBOARDING_VIDEO_URL` blank), and `VITE_ENABLE_ONBOARDING_PREVIEW` must be off for production.

## Suggested order

1. Decide pilot auth policy (finding 2). Then restore one consent mechanism for every path (1, 3): a checkbox with links on Login/SignUp, `markPendingConsent()` before the Google redirect.
2. Fix the email dead ends (4) or hide email auth again, whichever finding 2 decides.
3. Add the saved-measurements shortcut and Studio setup-status banner (5, 6, 8).
4. Guest-to-account prompt before capture (7).
5. Introduce `RequireAuth` with a single login target (11) and collapse the `next` rules (10).
