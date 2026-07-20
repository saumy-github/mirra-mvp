# Frontend Structure Plan

*Last updated: 2026-07-18*

Builds on [Tech Stack Decision](website_pilot_v1_scope.md#tech-stack-decision) and [Port Audit](port-audit-user-side.md). Vite + React + TypeScript, ported from `Mirra-landing-page` (as-is) and the taken/adapted pieces of `user-side`.

## Principles

- **Modular by domain, not by atom.** Group by feature (`auth`, `capture`, `studio`, ...), not by component size. No `atoms/molecules/organisms`-style structure — that's exactly what produces a folder full of single-purpose wrappers.
- **`pages/` stays thin.** A page file composes feature components and wires up routing/params — it doesn't contain business logic or large JSX trees itself.
- **No new small single-purpose components.** Per your instruction, don't add another `components/ui/xyz.tsx` for a one-off element. The inherited primitives from the port audit (`Button`, `Field`, `Logo`, `Spinner`/`misc`, `ErrorScreen`, `FabricPanel`) already cover the common cases — reuse them. Only promote something new into `components/ui/` if it's genuinely used across 3+ features, matching the no-premature-abstraction rule already in `repo-rules.md`.
- **Toast notifications for async feedback**, not blocking alerts/modals — this app has several slow, async operations (avatar generation, capture pairing, VTO rendering) where a toast is the right way to surface "done" / "failed" without interrupting the user.

## Directory Tree

```
frontend/
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
├── .env.example
└── src/
    ├── main.tsx                  # entry point, mounts <App />
    ├── App.tsx                   # root: providers + router outlet
    ├── router.tsx                # route table, React.lazy + Suspense per page
    │
    ├── pages/                    # one file per route — thin composition only
    │   ├── Home.tsx
    │   ├── Pricing.tsx
    │   ├── Team.tsx
    │   ├── auth/
    │   │   ├── SignUp.tsx
    │   │   ├── Login.tsx
    │   │   ├── VerifyEmail.tsx
    │   │   └── ForgotPassword.tsx
    │   ├── onboarding/
    │   │   ├── Measurements.tsx
    │   │   └── Avatar.tsx
    │   ├── Capture.tsx
    │   ├── CaptureToken.tsx
    │   ├── Studio.tsx            # heaviest page — own lazy chunk, R3F lives here
    │   ├── profile/
    │   │   ├── Profile.tsx
    │   │   ├── ProfileAvatar.tsx
    │   │   ├── ProfileMeasurements.tsx
    │   │   ├── SignatureLooks.tsx
    │   │   └── Privacy.tsx
    │   └── errors/
    │       ├── ProductUnavailable.tsx
    │       └── AccountInactive.tsx
    │
    ├── features/                 # domain logic + components, ported from user-side
    │   ├── auth/
    │   ├── capture/               # camera-capture, silhouettes, qr-card, sync-status
    │   ├── onboarding/            # generation-progress, measurement-row
    │   ├── studio/
    │   │   ├── components/        # avatar-figure, avatar-stage, product-rail, hanger-bar,
    │   │   │                      # curated-look-rail, signature-look-dialog, pinch-carousel
    │   │   └── studio-store.ts    # zustand, ported as-is
    │   └── profile/
    │
    ├── components/                # cross-feature shared UI ONLY — kept deliberately small
    │   ├── ui/                    # inherited: button, field, logo, misc, error-screen, fabric-panel
    │   ├── layout/                # app shell, nav, footer — persistent app-shell pattern
    │   └── toast/                 # toast provider/mount point
    │
    ├── integrations/
    │   ├── mirra-api/             # runtime-provider.ts (the seam), types, errors, client,
    │   │                          # mock-runtime-provider.ts (dev), public-runtime-provider.ts (new — built against our FastAPI backend)
    │   └── engines/                # avatar/ + try-on/ typed seams — the CLO3D integration boundary, not implemented yet
    │
    ├── lib/                       # state-machines/{capture,avatar-job,try-on}, hanger.ts, units.ts, analytics.ts
    ├── hooks/                     # use-capture, use-try-on, use-signature-looks, etc.
    ├── config/                    # urls.ts — reads import.meta.env.VITE_* directly, no wrapper module
    ├── assets/
    └── styles/                    # tailwind entry + globals
```

## Routing & Code-Splitting

Every entry in `pages/` is lazy-loaded via `React.lazy()` + `Suspense`, per the CSR loading strategy already agreed:

- **Skeleton fallbacks**, not blank/spinner, shaped like the destination page.
- **The `Studio` page is its own chunk** — this is where React Three Fiber, drei, and Three.js actually load. Auth, onboarding forms, and profile pages never pay that cost.
- **Prefetch on hover/intent** for the near-certain next screen (e.g., prefetch the `Studio` chunk once avatar generation status hits "ready," prefetch `onboarding/Avatar` the moment measurements are submitted).
- **App-shell pattern**: `components/layout/` (nav/header) stays mounted across navigations; only the route outlet shows loading state.

Final route table (from the port audit's net result, now as the actual router target):

| Route | Page file |
|---|---|
| `/`, `/pricing`, `/team` | `pages/Home.tsx`, `Pricing.tsx`, `Team.tsx` |
| `/auth/sign-up`, `/login`, `/verify-email`, `/forgot-password` | `pages/auth/*` |
| `/capture`, `/capture/:token` | `pages/Capture.tsx`, `CaptureToken.tsx` |
| `/onboarding/measurements`, `/onboarding/avatar` | `pages/onboarding/*` |
| `/studio` | `pages/Studio.tsx` |
| `/profile`, `/profile/avatar`, `/profile/measurements`, `/profile/signature-looks`, `/profile/privacy` | `pages/profile/*` |
| `/error/product-unavailable`, `/error/account-inactive` | `pages/errors/*` |

Not yet in the table: **guest mode entry point** and **paste-a-link garment extraction** — both net-new, no route shape to inherit. Worth a short design pass before implementation, not decided here.

## Toast Notifications

Recommend **Sonner** — small API (`toast.success(...)`, `toast.error(...)`), built-in stacking/auto-dismiss/swipe-to-dismiss, easy to theme with Tailwind, and is the current default choice in most modern Vite+React+Tailwind stacks (no heavier alternative buys you anything here). Mount a single `<Toaster />` once in `App.tsx` alongside the other providers.

**Where it's used**: avatar generation complete/failed, capture pairing succeeded/expired, measurement save confirmation, cart/wishlist actions, network errors — anything that's a background result the user should notice without a modal interrupting them. This directly serves the "time issues" wait-state problem: a toast is how the user finds out their avatar finished generating if they've navigated away from the progress screen.

## State & Data

- **TanStack Query** — server state: avatar-job polling, catalog fetching, capture-session status. Already the plan; `user-side` already uses it, so this is a straight port.
- **Zustand** — local/UI state, e.g. `studio-store.ts` (ported as-is).
- **Zod** — request/response schema validation, already used in `user-side`, kept for the same reason FastAPI uses Pydantic on the backend: one source of truth for shape, not hand-checked types.

## What's Inherited vs. Net New

See [Port Audit](port-audit-user-side.md#net-result-standalone-route-list) for the full breakdown. Summary: auth, capture, onboarding, the studio experience, and profile pages are ported with light rework. Guest mode, toast notifications, and the optional link-scraping feature are built fresh.
