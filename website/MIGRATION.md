# Landing redesign migration

Controlled frontend migration of the standalone landing redesign onto this
repo's production architecture.

- **Architectural source of truth:** this repo (`origin/main` @ `4f1d7b1`).
- **Design source of truth:** the standalone redesign
  (`~/Documents/ChatGPT/New project`, tag `redesign-final-v1`). Treated as
  **read-only** — nothing is ever written back into it.
- **Working branch:** `feat/landing-redesign`, in a git worktree so the
  primary clone stays on a buildable `main` at all times.
- **Rollback:** `git reset --hard pre-migration` (tag on the pre-migration tip).

## Why this is a port, not a merge

The two codebases do not share a framework. The redesign is `vinext`
(Next-style App Router, React Server Components) on Cloudflare Workers; this
repo is a Vite SPA on `react-router-dom` v7 talking to a Python/FastAPI
backend. There is no merge base and `git merge` is not applicable.

The direction follows from scope: the redesign covers **3 routes**, this repo
serves **19** plus the whole product. So the design moves into this stack,
page by page — not the reverse.

## Blast radius

The marketing surface is already an isolated leaf module. Verified on `4f1d7b1`:

- `src/features/marketing/**` imports nothing from `@/components`, `@/stores`,
  `@/integrations`, `@/lib` or `@/hooks` — only npm packages and its own files.
- Only two things outside it reference it: `router.tsx:6` (lazy layout import)
  and `pages/Team.tsx:4` (imports `TextReveal`).
- `marketing-layout.tsx` already scopes Lenis to this subtree by design.

So changes are confined to:

```
src/features/marketing/**
src/pages/{Home,Pricing,Team}.tsx
src/router.tsx          (only if route names change)
public/**               (additive)
```

**Anything proposed outside this list is a bug in the plan.** Auth, onboarding,
studio, profile and capture are out of scope and must not be touched.

## Route mapping

| Route | This repo | Redesign | Action |
|---|---|---|---|
| `/` | `pages/Home.tsx` | `app/page.tsx` | REPLACE |
| `/pricing` | `pages/Pricing.tsx` | `app/pricing/PricingClient.tsx` | REPLACE |
| `/meet-the-team` | `pages/Team.tsx` | *(none)* | **DECISION NEEDED** |
| `/faq` | *(none)* | `app/faq/FAQClient.tsx` | **DECISION NEEDED** |

Two open questions, flagged rather than guessed:

1. `/meet-the-team` has no redesigned counterpart. Restyle it to match the new
   design, or leave it on the old look?
2. `/faq` exists only in the redesign. Add it as a new route, or drop it?

Neither blocks phases 1–2.

## Migration map

### KEEP — unchanged, production-critical
- `src/styles/globals.css` — **app-owned**, see HIGH RISK below.
- `src/router.tsx` — structure stays; at most the marketing route list changes.
- Everything under `src/features/{auth,studio,onboarding,capture}`,
  `src/pages/{auth,profile,onboarding,errors}`, `src/integrations`,
  `src/stores`, `src/lib`, `src/components`.
- `vite.config.ts`, `.env.example`, `eslint.config.js`, backend, deployment.

### REPLACE — old landing superseded by the redesign
- `pages/Home.tsx` ← `app/page.tsx`
- `pages/Pricing.tsx` ← `app/pricing/PricingClient.tsx`
- `features/marketing/components/Header.tsx` ← `SiteNavbar.tsx` + `SiteChrome.tsx`
- `features/marketing/components/MirrorCTA.tsx` ← `SiteFooter.tsx`

### ADAPT — redesign code needing framework rewiring
Zero new npm dependencies are required. The redesign's `matter-js` is a stale
entry it never imports, and its `framer-motion` is the same library as this
repo's `motion` — only the import path differs.

| Redesign import | Becomes |
|---|---|
| `from "framer-motion"` | `from "motion/react"` |
| `next/link` → `<Link href>` | `react-router-dom` → `<Link to>` |
| `next/navigation` `usePathname` | `useLocation().pathname` |
| `next/navigation` `useRouter().push` | `useNavigate()` |
| `next/headers`, `next` metadata | server-only — remove |
| RSC (`async` components, `"use server"`) | client components |

- `SmoothNavigation.tsx` — overlaps `marketing-layout.tsx`'s existing Lenis
  instance. Reconcile to **one** instance; do not mount two.

### MERGE — both sides hold logic worth keeping
- `features/marketing/components/TextReveal.tsx` — **still imported by
  `pages/Team.tsx`**. Must survive the migration even if the new Home stops
  using it.
- `features/marketing/components/RoiCalculator.tsx` — the only marketing file
  using the shared `.range-thumb` utility. Keep unless deliberately dropped.

### CREATE
- `src/features/marketing/marketing.css` — generated, see below.
- `scripts/scope-marketing-css.mjs` — the scoping transform.
- `pages/FAQ.tsx` + router entry, if `/faq` is adopted.

### DELETE — only after the replacement is verified live
- Superseded marketing components once nothing imports them:
  `Hero`, `LiquidMetal`, `LiveLedger`, `ProblemTeardown{.tsx,.css}`,
  `ProductReveal{.tsx,.css}`, `LaurelPortrait`, `DemoPlaceholder`, `Closure`,
  `CustomCursor`.
- From the redesign, **do not port at all** — starter-template scaffolding,
  not your work, and superseded by the real FastAPI backend:
  `app/api/auth/me/route.ts`, `app/chatgpt-auth.ts`, `db/`, `drizzle/`,
  `worker/`, `cloudflare-env.d.ts`, `wrangler` config.

### HIGH RISK

**1. `src/styles/globals.css` — app infrastructure, not landing styling.**
Imported once in `main.tsx`, so it applies to all 19 routes. Measured usage:

| | marketing | app |
|---|---|---|
| `.glass` / `.glass-heavy` | 0 | 4 |
| `.pressable` | 0 | 3 |
| `.rail-scroll` | 0 | 6 |
| `.mono-tag` | 0 | 7 |
| `.range-thumb` | 1 | 2 |

The redesign is **dark-themed** (`html { background: #161419; color-scheme: dark }`,
22px `LayGrotesk`); the app is light-themed. Letting the redesign's sheet land
globally would restyle studio, profile, onboarding and auth — pages nobody
would think to re-check after a "styles" commit. Hence the scoping transform.

**2. Shared design tokens — never change their values.**
`--color-ink` (marketing 12 / app 27), `--color-line` (6 / 23),
`--color-surface` (7 / 12). If the new design needs a different ink or border,
add a new landing-scoped token instead. (`--color-bg` 10/0 and `--color-wine`
4/0 are landing-only and safe to change.)

**3. `.gitignore` line 42 `**/*.svg`** ignored every SVG repo-wide — intended
for generated garment patterns, but it silently swallowed the landing's 14
brand logos and favicon. Negation rules added; re-check after adding any SVG.

**4. Lenis.** The redesign applies `html.lenis` globally; this repo scopes Lenis
to `MarketingLayout` precisely because the studio has its own scroll
containers. Keep it scoped.

## Style scoping

`marketing.css` is **generated** — re-run rather than hand-edit:

```bash
node scripts/scope-marketing-css.mjs \
  "$REDESIGN/app/globals.css" \
  website/frontend/src/features/marketing/marketing.css
```

It nests all 731 rules under `.mirra-landing`, folds `html`/`body`/`:root` onto
that wrapper, and hoists only inert at-rules (`@font-face`, `@keyframes`) plus
the Lenis rules to top level. It fails loudly on any selector it cannot scope.

Verified in the build output: the landing CSS lands entirely in the
`marketing-layout` chunk; the global `index` chunk contains zero
`.mirra-landing` rules and no document-level dark-theme rules.

## Phases

Each phase is one commit that builds. `npm run build` before every commit.

1. **Design system + assets** — scoped stylesheet, fonts, images. Inert. ✅
2. Shared layout / navigation — apply `.mirra-landing`, swap header + footer.
3. `/` (Home)
4. `/pricing`
5. `/meet-the-team` and `/faq` — pending the decisions above.
6. **App regression pass** — `/studio`, `/profile`, `/onboarding/measurements`,
   `/auth/login` must be pixel-identical to `pre-migration`.
7. Animations, responsive, `build` + `typecheck` + `lint`.

## Known follow-ups

- `public/` is 28MB, ~18MB of it landing video (`video-effect-*.mp4`). Heavy for
  git; consider Git LFS or a CDN before this merges.
- The redesign repo has **no remote**. It exists on one disk, tagged
  `redesign-final-v1`. Push it somewhere.
