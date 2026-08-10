# 21 - Website audit: frontend lazy loading + unreachable backend routes

**Status:** findings only — no code changed
**Created:** 2026-08-08
**Extends:** [18-homepage-lazy-loading-audit.md](18-homepage-lazy-loading-audit.md) (homepage-only; this covers the whole app + the backend surface)

## Goal

Two questions, answered from the actual code and a real `npm run build`, not assumptions:

1. Where does the frontend load more than it needs to, and what should be deferred?
2. Which backend routes exist but have no path to them from the frontend?

---

# Part A — Backend routes with no way to reach them

Method: enumerated every `@router.<verb>` across `website/backend/src/*/routes.py` (28 routes),
then traced each against `website/frontend/src/integrations/mirra-api/http-runtime-provider.ts`
(the only place the live frontend issues HTTP calls), then a second pass against actual
page/component callers via `hooks/`.

## A1. Genuinely dead — no frontend caller exists at all

### 1. `POST /api/v1/auth/password-reset/confirm` — dead, and it breaks a user-visible promise

Nothing in the frontend calls it. `http-runtime-provider.ts:110` only calls
`POST /auth/password-reset` (the *request* half); there is no `confirmPasswordReset` method
on `MirraRuntimeProvider`, no page at `/auth/reset-password`, and no route registered in
`router.tsx` that could consume a reset token.

This is worse than an unused route — `pages/auth/ForgotPassword.tsx:31-33` tells the user
*"a reset link is on its way. It expires in 30 minutes."* Even if an email provider were
wired up (it isn't — the token is only logged server-side, doc 03), the link would have
nowhere to land. **The password-reset flow is a dead end from the user's side, end to end.**

Relevant to the pilot decision: doc 03 Section 2 already plans to comment out
`ForgotPassword.tsx`. That resolves the user-facing half. The backend route stays per
Section 3's "don't delete backend auth code yet" rule.

### 2. `PATCH /api/v1/users/me` (update display name) — no caller, no UI

`users/controller.py:12` takes `body.name` and updates the profile. There is no
`updateProfile` method on the runtime provider and no UI anywhere to change a display name.
`pages/profile/Profile.tsx:15` only *reads* `account.displayName`.

Net effect today: **a user's name is whatever Google returned (or literally `"Guest"`) and
can never be changed.** This is the one route on this list that's a genuine missing feature
rather than dead weight — worth deciding whether it's a pilot gap or an accepted limitation.

### 3. `GET /api/v1/users/me` — exact duplicate of `GET /auth/me`

`users/controller.py:7-9` returns `{"account": shape_account(user)}` — byte-identical shape
to `auth/controller`'s `me`, via the same `shape_account` helper (it literally imports it
from `auth.controller`). The frontend uses `/auth/me` exclusively
(`http-runtime-provider.ts:99`). Two routes, one behavior, one used.

### 4. `GET /api/v1/measurements/me` — no caller

`MirraRuntimeProvider` has **no measurements read method at all** — only
`updateMeasurements`, which does `PATCH` (falling back to `PUT` on 404). Every page that
displays measurements reads them off the avatar profile instead
(`live.profileFromMeasurements`, `useAvatarProfile`).

This matters more than it looks: it means the frontend has no way to read measurements for a
user who has submitted them but has **no avatar profile yet**, and it's the read side Step 2's
planned `measurements_version` staleness check (doc 09 → doc 13 Step 6) will need. So this
one shouldn't be deleted — it should get wired up.

## A2. Dead query parameters on live routes

`GET /api/v1/catalog/garments` accepts `fit_type`, `category`, `q`, `limit`, `offset`.
`listProducts` (`http-runtime-provider.ts:31-40`) only ever sends `category`, `offset`, `limit`.
**`fit_type` and `q` are never sent by anything** — there is no search box or fit filter in the
UI. Harmless, but they're untested surface area.

## A3. Everything else is genuinely wired

For completeness — these all have a real path from a real page:
auth `sign-up`/`login`/`guest`/`google/start`/`google/callback`/`refresh`/`logout`/`me`/
`verify-email`/`password-reset`, `users/me/consents` (PATCH), `users/me` (DELETE),
`measurements/me` (PUT + PATCH), all 4 `avatars/*`, both `catalog/*`, all 4 `tryon/*`,
all 4 `signature-looks/*`, `analytics/events`.

## A4. Unreachable *frontend* routes (the mirror-image problem)

Counted inbound links to every route in `router.tsx`, excluding `router.tsx` itself:

| Route | Inbound links | Note |
|---|---|---|
| `/measurements` | **0 real** | ⚠️ see below |
| `/error/product-unavailable` | 0 | no code ever navigates here |
| `/error/account-inactive` | 0 | no code ever navigates here |
| `/auth/callback` | 0 | ✅ correct — the backend redirects here |

**`/measurements` is the notable one.** The standalone measurement intake form built in
doc 09 — specifically to fix the dead end where `/onboarding/measurements` refused to render
without a pre-existing avatar — is itself now only reachable by typing the URL. Its single
grep hit is its own self-redirect to login (`Measurements.tsx:74`, `next=/measurements`).
Nothing links to it. **Doc 09 fixed the form and inherited the exact dead end it was fixing.**

Meanwhile `pages/onboarding/Avatar.tsx:98` still routes users to the *old*
`/onboarding/measurements` page — the one that hard-requires an avatar to already exist.
So the live navigation path still leads to the broken page, not the fixed one.

---

# Part B — Frontend loading

Evidence: real `npm run build` output (vite 6.4.3, 2355 modules, clean).

## B1. What actually ships

```text
index-BKKV-RQ5.js       429.46 kB │ gzip: 136.78 kB   ← every route
rotate-ccw-C5f4lw8J.js  115.80 kB │ gzip:  45.84 kB   ← shared lucide icon chunk
use-shopper-C-49hWcn.js 102.34 kB │ gzip:  29.06 kB   ← see B2
index-BXIkLhus.css      100.89 kB │ gzip:  17.12 kB   ← global CSS, every route
Home-BtBRkaoT.js         99.40 kB │ gzip:  30.24 kB
Studio-CCjAJgpp.js       70.37 kB │ gzip:  20.02 kB
marketing-layout.js      45.28 kB │ gzip:  12.86 kB   ← GSAP + Lenis
Home-CWPkwabE.css        39.47 kB │ gzip:   8.44 kB
```

Route-level lazy loading is already correct — every page in `router.tsx` is `React.lazy`,
and it shows: each page gets its own small chunk. The waste is **inside** the shared chunks
and inside individual pages.

## B2. The mock layer ships to production — confirmed, not suspected

`integrations/mirra-api/index.ts:1-2` statically imports **both** providers:

```ts
import { createMockRuntimeProvider } from "./mock-runtime-provider";
import { createPublicRuntimeProvider } from "./public-runtime-provider";
```

The choice happens at *runtime* (`import.meta.env.VITE_INTEGRATION_MODE === "live" ? ... : ...`),
so Rollup cannot tree-shake the mock branch — it has to keep both. Verified against the built
output: the mock-only fixture string `"Google Demo"` (from `mocks/mock-provider.ts:123`) and
the fixture name `"Ava"` (`mocks/store.ts:67`) are **both present in the production bundle**.

That's `mock-provider.ts` (15.6 kB) + `store.ts` + `fixtures.ts` (~24 kB of source) plus its
zod schemas, riding inside the 29 kB-gzip `use-shopper` chunk that loads on every
authenticated page — as pure dead code in a `live` build.

Fix: make the mock branch a dynamic `import()` (or gate it behind a build-time constant Vite
can statically eliminate). This is the single highest value/effort ratio item in Part B — it's
a config-shaped change, not a refactor, and it removes code that can never execute in prod.

## B3. Zero lazy images across the entire app

`grep 'loading="lazy"'` returns **0 matches repo-wide.** There are ~20 `<img>` sites, and
they're not only on the marketing pages doc 18 covered:

- Marketing: `ProductReveal.tsx:488`, `Closure.tsx:80`, `LiveLedger.tsx:295`,
  `MirrorCTA.tsx` (**7 images in one component**, lines 122-172), `LaurelPortrait.tsx:74`,
  `Team.tsx:74`
- **Studio (missed by doc 18)**: `product-rail.tsx:162`, `hanger-bar.tsx:126` and `:203`,
  `curated-look-rail.tsx:39`, `cart-drawer.tsx:245`, `avatar-figure.tsx:78`,
  `studio-header.tsx:90`
- Profile: `SignatureLooks.tsx:30`

The Studio ones matter most for the pilot: product rails and the hanger bar render a
thumbnail per catalog item, all eager, all at once. That scales directly with catalog size —
so it gets worse the moment doc 14's real multi-garment catalog lands. Adding
`loading="lazy"` + explicit `width`/`height` is near-zero-risk and prevents layout shift too.

## B4. The `rotate-ccw` icon chunk (45.84 kB gzip) — biggest single suspicious item

Doc 18 flagged this and left it unresolved. It's 45.84 kB gzip — **larger than the entire
Home page chunk** — for what should be a handful of SVG paths. 8 distinct icons on Home alone
pull it onto `/`'s critical path. Worth confirming whether `lucide-react` is being
barrel-imported (importing the whole icon set and relying on tree-shaking that isn't
happening) versus genuinely being a shared chunk. If it's the former, switching to
per-icon deep imports collapses this almost entirely.

## B5. Studio (70.37 kB / 20.02 kB gzip) is one eager chunk

`pages/Studio.tsx` is ~550 lines and imports its whole feature set eagerly — `product-rail`,
`hanger-bar`, `cart-drawer`, `curated-look-rail`, `studio-header`, `avatar-figure`. The
cart drawer in particular is modal/on-demand UI that a user may never open, loaded up front.

This is also **the page that will host the GLB viewer** (doc 13 Step 6 / doc 17 Step 10).
Doc 03 Section 7's rule — "3D viewer is isolated, lazy-loaded, measured, and disposable" —
needs Studio to already be split before that lands, or the viewer gets absorbed into this
same eager chunk. Splitting Studio is therefore a prerequisite for Step 6, not a nice-to-have
afterwards.

## B6. Still open from doc 18 (unchanged, re-confirmed in this build)

Home's 7 sections are still one eager chunk (99.40 kB); GSAP + `ScrollTrigger` + `SplitText`,
Lenis, and the `@paper-design/shaders` WebGL liquid-metal badge all still mount
unconditionally. Numbers are identical to doc 18's — nothing regressed, nothing improved.

---

# Suggested order (highest value / lowest risk first)

1. **`loading="lazy"` + `width`/`height` on all ~20 `<img>`** — trivial, no behavior change,
   and it's the fix that stops scaling badly as the catalog grows (B3).
2. **Dynamic-import the mock provider** so `live` builds drop it — removes ~29 kB gzip of
   never-executable code from every authenticated page (B2).
3. **Link `/measurements` properly**, and repoint `Avatar.tsx:98` at it instead of the
   avatar-requiring `/onboarding/measurements` — this is a correctness bug, not perf (A4).
4. **Investigate the `rotate-ccw` icon chunk** (B4) — potentially the largest single win.
5. **Split Studio's below-the-fold/on-demand components** (B5) — do this *before* the GLB
   viewer work (Step 6), not after.
6. **Home section-level lazy loading** (B6 / doc 18's own list) — largest effort, and it's
   marketing-only, so it doesn't block the pilot funnel.
7. **Backend route decisions** (A1): wire up `GET /measurements/me`; decide whether
   `PATCH /users/me` becomes a real "edit your name" feature or is accepted as absent;
   leave `GET /users/me` and `password-reset/confirm` in place per doc 03 Section 3's
   "don't delete backend auth code yet" rule, but record them as knowingly dead.

## Execution Log

Not started — audit only, per this round's request.
