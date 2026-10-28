# 19 — Temporary business Quick Access (2026-10-08)

User request: restore `/business/login` Quick Access for showing and testing the
dashboard now, and leave the real authentication work for finalisation.

## Confirmed cause

`pages/business/Login.tsx` calls `continueAsGuest()`, which creates a shopper
guest through `POST /auth/guest`. It then navigates to `/dashboard/start`.
`bootstrapLiveSession()` rejects `account.isGuest` and sends the visitor back to
business login. Guest creation also depends on the backend being reachable.
This temporary action never establishes the dashboard's separate persona session.

## Plan

- Replace this button's guest call with the existing demo session for `u_owner`
  (Atelier Noir, active brand owner) and enter `/dashboard/portal` directly.
- Preserve safe business `next` destinations and the dashboard's existing
  localStorage session persistence so a refresh remains usable.
- Enable Quick Access only in Vite development. Keep password/Google login and
  all backend authentication and merchant permission checks as they are.
- Load the dashboard session dynamically from the business page to retain its
  lazy loading. Do not introduce mock API or avatar/try-on engine modes.
- Verify development login, reload, safe redirects and production disablement,
  then run the frontend checks and record the result here.

Files: `src/pages/business/Login.tsx`, a business Quick Access helper and tests,
this note, and `02-remaining-work.md` (all source paths under `website/frontend`).

## AI handoff — before finalisation

- Replace/retire this temporary entry point after verifying real business
  password and Google authentication, workspace provisioning, membership and
  role adoption through `/dashboard/start`.
- Verify redirect, page reload/session restoration and sign-out end to end for
  real merchant accounts. Guests must remain unable to access merchant APIs.
- Review the older `/dashboard/login` demo persona picker before a public launch.
- Quick Access only opens the seeded frontend demo. It does not create a real
  merchant account/workspace or enable server-backed Shopify, uploads or jobs.
  Dashboard demo data resets on a full reload; the selected persona persists.

## Execution and verification

Implemented `pages/business/quick-access.ts`: development-only entry into the
existing `u_owner` persona, dynamically loading the dashboard session. The
business page uses its own pending state and no longer calls shopper guest
authentication or reports demo entry as a real authenticated login.

Safe `next` links retain their query and fragment; `/dashboard/start` resolves
directly to the demo portal. Production hides the button and rejects the helper
before establishing any session. No backend files changed.

Verified:

- Browser: `/business/login` → Quick Access → `/dashboard/portal`, visibly showing
  Atelier Noir and Elodie Marchand as Owner. A full browser reload stays in the
  same workspace without another login.
- `npm test`: 85 tests passed, including 9 new checks for the demo owner session,
  no backend calls, safe redirects, reload/sign-out and production disablement.
- `npm run typecheck`, `npx --no-install eslint src --max-warnings=0`,
  `npm run build`, and `git diff --check` passed.
- Production assets contain neither the Quick Access button label nor the helper's
  development-only error text. Vite's large-chunk advisory remains unrelated to
  this fix.

Final authentication work listed above is deliberately deferred, as requested.
