# 06 — Lane 3 (website): Google-only pilot auth + fix the consent gap

**Status**: planned, not started. Written 2026-08-15.
**Covers**: `02-remaining-work.md` items **B8, B9**, and **Group E** dead routes.
**Agent assignment**: one agent, **isolated worktree**. Touches no CLO, no worker, no pipeline.

## Why these together

B8 makes Google the only real signup path for the pilot. B9 is a confirmed bug in exactly that path — Google signups never record consent, and never even ask for it. Shipping B8 without B9 means every pilot user signs up with **no consent record at all**. They are one change to one surface, and splitting them across agents would mean two agents editing `Login.tsx` and `SignUp.tsx`.

Group E rides along because both dead routes sit in the same two files this lane already owns.

## B8 — comment out the email/password UI

Decision made 2026-08-04 (old-folder doc 03 §2), never executed. Confirmed still un-executed 2026-08-15: `Login.tsx` still renders the password form (lines ~96-99), the "or continue with email" divider (line 82), "Forgot password?" (line 115) and "Create account" (line 122).

Per doc 03's own explicit rule: **comment out, do not delete.** Backend routes and code stay intact. This is a pilot-scoped reversal, and it must be trivially reversible.

- `Login.tsx` — comment out the email/password form, the "or continue with email" divider, the "Forgot password?" link, the "Create account" link. **Keep** `GoogleButton` and "Continue as guest."
- `SignUp.tsx` (148 lines) — comment out page content.
- `ForgotPassword.tsx` (59 lines) — comment out page content.
- `VerifyEmail.tsx` (64 lines) — comment out page content; nothing is left for it to do once password signup is gone.

**Doc 03's open sub-question, now answered**: leave the routes registered in `router.tsx`. Commenting out page content while keeping `/auth/sign-up` etc. routable means a stale link or bookmark renders an empty shell rather than a 404, and re-enabling for launch is uncommenting one block instead of re-deriving the routing. If you disagree after seeing the code, say so before changing course — do not silently unregister them.

Leave a short comment at each site saying *why* it's commented and pointing at this doc, so the next reader doesn't have to guess whether it's dead code or a deliberate pilot gate.

## B9 — the Google consent gap (confirmed real bug)

Verified 2026-08-15: `website/backend/src/auth/service.py:168` — `google_login()` creates the user with `consents={}` and never touches the field again. Not "unpopulated pending a later step" — genuinely never written on that path.

Compounding it on the frontend: the Terms/Privacy checkbox on `SignUp.tsx` gates only the email/password submit handler. The Google button's `onClick` never checks it. So for Google users consent is not merely unrecorded — **it is never requested**.

Once B8 lands, Google is the only account-creating path, so this stops being an edge case and becomes the default. Both fixes from doc 20, and both are needed:
1. **Ask for it** — gate the Google button behind the consent checkbox (and put that gate on `Login.tsx` too, since after B8 that's where signup actually happens; a first-time Google login *is* a signup).
2. **Record it** — have `AuthCallback.tsx` fire the existing `PATCH /users/me/consents` once the session hydrates, or write consent server-side in `google_login()`. Prefer whichever makes the record atomic with account creation; if it lands client-side in `AuthCallback`, handle the case where that call fails and the account exists with `consents={}` anyway — that failure mode is the whole reason this bug exists.

Record what was actually consented to and when, in the same shape the email/password path uses. Do not invent a second consent schema.

**Known limitation, not this lane's job to fix**: real Google OAuth credentials have never been provisioned (Group D), so the full consent-screen round trip cannot be tested end-to-end here. Verify everything up to that boundary and state plainly in the execution log what could not be exercised. Do not claim the flow is verified end-to-end when the OAuth round trip was not.

## Group E — dead routes

- `website/backend/src/auth/routes.py:79` — `POST /auth/password-reset/confirm`, no frontend caller. Remove.
- `website/backend/src/users/routes.py:16` — `GET /users/me`, an exact duplicate of `GET /auth/me` (`auth/routes.py:64`). Remove.

Before removing either, grep the frontend **and** `website/backend/scripts/` for callers — `smoke_e2e.py` is a plausible consumer of `/users/me` and is not part of the app's own routing. If anything calls them, repoint it first.

`ForgotPassword.tsx` is listed in Group E but is covered by B8's comment-out above; do not also delete it.

## Verification

**This lane runs in a worktree, which constrains how backend verification can happen** (see `01`'s worktree section). A worktree has no `.venv/`, no `.env*` files, and must never run `docker compose` — the main checkout's stack owns ports 8000/6379, and a second stack from a worktree directory just fights it.

- **In the worktree**: `python -m py_compile` on every touched backend file (syntax only — the import check needs the venv). Frontend: `npx tsc --noEmit`; `npx eslint src --max-warnings=0`; `npm run build` — all fine against the junctioned `node_modules`. **Do not run `npm install`.** Do not start a Vite dev server without checking that no other lane already has one on port 3000.
- **After copy-back into the main checkout** (user-supervised, serialized against Lane 1's Docker use): `python -c "from src.main import app"`; `docker compose build backend && docker compose up -d backend`; `docker compose exec backend python scripts/smoke_e2e.py`. The Group E route removals in particular are not verified until the smoke test passes — that's the check that catches a caller we missed.
- By hand: `/auth/login` shows only Google + guest; the Google button is inert until consent is checked; a fresh Google login produces a user doc whose `consents` is **non-empty**. That last one is the actual acceptance test for B9 — check the Mongo doc, don't infer it from the UI.
- Commented-out code must not leave unused imports behind — that's what will fail `eslint --max-warnings=0`.

## Rules for this lane

- **Never commit.** Not on completion. The user commits manually, including merging this worktree back. See `01-how-ai-should-work.md`.
- Owned files: `src/pages/auth/**`, `website/backend/src/auth/{routes,service}.py`, `website/backend/src/users/routes.py`.
- **Do not touch** `src/router.tsx` — Lane 2 owns it this window, and the B8 decision above is specifically "leave the routes registered," so this lane has no reason to edit it. If you conclude otherwise, stop and flag it.
- Do not touch `src/pages/profile/**`, `src/pages/Studio.tsx`, or `src/pages/onboarding/**` (Lane 2).
- Do not read `.env*` files with any tool, for any reason — including while investigating OAuth config. Ask the user instead.

## Execution log

*(To be written after the work, per `01`'s workflow step 3.)*
