# 20 - Google OAuth signups never record Terms/Privacy consent

**Status:** findings only — no code changed
**Created:** 2026-08-08

## Goal

User tried Google OAuth login (working) and password login (working, to be removed before pilot launch per prior decision) and noticed the two signup paths produce different `consents` shapes in Mongo. Investigated why, and whether it needs cleanup.

## Evidence

Two real user documents from the `users` collection:

```js
// Google OAuth signup
{
  _id: 'u_ebf25207ffbd70c8',
  email: 'saumy2502@gmail.com',
  auth_providers: [{ provider: 'google', provider_user_id: '...' }],
  consents: {},                       // <- empty, permanently
  created_at: ISODate('2026-08-08T08:52:36.219Z'),
  updated_at: ISODate('2026-08-08T08:52:36.219Z'),  // same instant as created_at
}

// Password signup
{
  _id: 'u_174f866ec86f5e86',
  email: 'saumybha@gmail.com',
  password_hash: '$2b$12$...',
  consents: { privacy: true, terms: true },   // <- populated
  created_at: ISODate('2026-08-08T08:53:55.480Z'),
  updated_at: ISODate('2026-08-08T08:53:55.772Z'),  // ~0.3s after created_at
}
```

## Root cause

Password signup is two network calls, not one:

1. `POST /auth/sign-up` — creates the user with `consents={}` (`website/backend/src/auth/service.py:97`)
2. A follow-up `PATCH /users/me/consents {terms: true, privacy: true}`, fired client-side right after, only if the signup form's checkbox was checked (`website/frontend/src/integrations/mirra-api/http-runtime-provider.ts:60-66`, driven by `SignUp.tsx:34-39`)

That second call is why the password account's `updated_at` trails `created_at` by ~0.3s and why its `consents` is populated.

Google OAuth signup is a full-page redirect round trip: `GET /auth/google/start` → Google → `GET /auth/google/callback` → frontend `AuthCallback.tsx` lands, hydrates the session, and navigates on (`website/backend/src/auth/controller.py:121-171`, `service.google_login()` in `auth/service.py:134-177`). **Nothing in that path ever calls the consents patch.** `google_login()` creates the user with `consents={}` and it is never touched again — there's no code path that could populate it later.

Compounding this: on the signup page, the "I accept the Terms of Service... Privacy Notice" checkbox (`SignUp.tsx:112-125`) only gates the **email/password** submit handler (`onSubmit` checks `accepted` at line 29). The `GoogleButton`'s `onClick={onGoogle}` (line 78) does **not** check `accepted` at all — a user can click "Continue with Google" and complete signup without ever interacting with the checkbox.

## Why this matters

- **Data inconsistency**: two signup paths produce structurally different `consents` records for what should be the same acceptance event.
- **No consent is ever recorded for Google users** — not "recorded as false", genuinely absent, indistinguishable from a user who was never asked.
- **The checkbox doesn't gate the Google path at all**, so today it's not just an unrecorded consent, it's a genuinely-never-requested one for that flow.

## Possible fixes (not implemented)

1. **Gate the Google button behind the checkbox**, same as the email form — disable it (or block `onGoogle`) until `accepted` is true.
2. **Thread the acceptance through the OAuth redirect round trip** so it can be recorded once the session is hydrated. Options:
   - Have `AuthCallback.tsx` call the existing `PATCH /users/me/consents` once `completeOAuthCallback()` resolves, mirroring what `signUp()` does — simplest, no backend changes, but fires unconditionally for every Google login (including returning users who already consented, which is harmless/idempotent but worth noting).
   - Or pass the acceptance forward explicitly (e.g. alongside the existing `mirra_oauth_state`/`mirra_oauth_next` short-lived cookies) so only genuine new-signup consent gets written, not every login.

## Execution Log

Not started — findings only, per this round's request.
