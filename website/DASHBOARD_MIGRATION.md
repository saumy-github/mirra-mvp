# Merchant dashboard migration

Port of the standalone merchant dashboard prototype (`~/merchant_dashboard`)
into this repo's frontend.

- **Architectural source of truth:** this repo — Vite SPA on `react-router-dom`
  v7 + FastAPI/Mongo.
- **Design/behaviour source of truth:** the prototype. Treated as **read-only**;
  nothing is written back to it. It stays on disk as reference and can be
  deleted once this port is signed off.
- **Landed at:** `website/frontend/src/features/dashboard/`, mounted at
  `/dashboard/*`.

## Why a port, not a second app

Same reasoning as `MIGRATION.md`. The two codebases don't share a framework —
the prototype is Next 16 App Router with React Server Components, server
actions, and a Node-side JSON file store; this repo is a client-rendered SPA.
There is no merge base.

The prototype's data layer was being thrown away regardless: `lib/store.ts` read
and wrote `.data/db.json` through `node:fs`, and `lib/auth.ts` was a cookie
holding a raw user id. Both are labelled "prototype" in their own headers. Once
that layer goes, what's left is JSX and pure domain logic — which is portable.
Carrying Next along would have bought a second framework, a second design
system, a second auth implementation, and a cross-origin session problem, in
exchange for keeping RSC on 19 pages of tables and forms that need no SSR.

## What came across

| Prototype | Here |
|---|---|
| `app/portal/**` (13 pages) | `features/dashboard/pages/portal/**` → `/dashboard/portal/*` |
| `app/admin/**` (6 pages) | `features/dashboard/pages/admin/**` → `/dashboard/admin/*` |
| `app/onboarding/page.tsx` | `pages/Onboarding.tsx` → `/dashboard/onboarding` |
| `app/login/page.tsx` | `pages/Login.tsx` → `/dashboard/login` |
| `lib/{types,seed,lifecycle,rbac,entitlements}.ts` | `data/*` — **unchanged** |
| `lib/{queries,util}.ts` | `data/*` — import paths only |
| `lib/store.ts` | `data/store.ts` — **rewritten**, see below |
| `lib/auth.ts` | `data/session.ts` — **rewritten**, see below |
| `lib/actions.ts` | `data/actions.ts` — server actions → sync functions |
| `components/{ui,shell,charts}.tsx` | `components/*` — `next/link` → `react-router-dom` |
| `components/catalogue-client.tsx` | `components/catalogue-table.tsx` |
| `components/admin-client.tsx` | `components/admin-controls.tsx` |

## What was dropped, and why

| Dropped | Reason |
|---|---|
| `app/(marketing)/**` (5 pages) | This repo's landing overhaul supersedes it — see `MIGRATION.md`. |
| `app/t/[slug]`, `app/preview/[slug]` | Shopper try-on already exists here as `/studio`. The prototype's tenant-scoped preview (per-tenant theme + preview token) is a backend feature, not a second frontend. |
| `app/api/public/v1/**`, `lib/public-api.ts` | Belongs in FastAPI next to the other routers, not in the browser. Redis is already in `docker-compose.yml` for the rate limiter. |
| `components/{tryon-client,tryon-page}.tsx` | Served only the dropped `/t/[slug]` surface. |
| `components/lead-form.tsx`, `captureLeadAction` | Served only the dropped marketing pages. Seeded leads still drive `/dashboard/admin/leads`. |

Two "Preview page" buttons (garment detail, publication) pointed at
`/preview/<slug>?preview_token=…`. They now read "Open try-on studio" and link
to `/studio` — `dashPath.tryOnStudio`, one place to change when tenant-scoped
preview lands.

## Mechanical translations

**Server actions → plain functions.** `"use server"`, `redirect()` and
`revalidatePath()` are gone. The store notifies its subscribers, so nothing
needs revalidating; the four actions that redirected now *return* the path and
the caller passes it to `useNavigate`.

**`<form action={fn}>` survived untouched.** React 19 supports function form
actions on the client, so every form that submitted `FormData` to a server
action still submits `FormData` to the same-signature local function.

**Async page components → hooks.** `await requireSession()` became
`useSession()`, and `await params` became `useParams()`. Pages call
`useDbVersion()` to subscribe to store mutations; they still read through
`getDb()` and the query helpers, so page bodies are otherwise unchanged.

**Route guards.** The redirect ladders in `app/portal/layout.tsx` and
`app/admin/layout.tsx` moved verbatim into `PortalLayout` / `AdminLayout` in
`dashboard-layout.tsx`, as `<Navigate replace>`. Pages under a guard bail with
`if (!session?.tenant) return null` rather than throwing.

**`notFound()`** → an `EmptyState` with a link back, on garment detail and
tenant detail.

## Styling

The prototype's neutrals (`ink`, `muted`, `line`, `surface`) differed from this
app's by a few points, so they fold into the app's tokens — the same rule
`MIGRATION.md` applied to the landing merge. Two genuinely new tokens were added
to `src/styles/globals.css`:

```css
--color-accent: #4f46e5;      /* the console's indigo */
--color-accent-soft: #eef2ff;
```

Both were unused elsewhere in the app, so the addition is non-colliding. They
live in `globals.css` rather than the feature's own stylesheet because Tailwind
v4 resolves `@theme inline` values at build time, which rules out overriding
them per-subtree. `dashboard.css` holds only what can be scoped: the warmer page
ground and the 14px base size the prototype set on `<body>`.

## Data: what's real and what isn't

**Nothing here talks to the backend yet.** `data/store.ts` seeds ~5k rows in
module memory on first read; a reload reseeds. It is deliberately not persisted
— the seed is large enough to be awkward in `localStorage`, and a clean known
dataset is what you want from a demo. Only the demo session (two ids) persists,
so a refresh doesn't sign you out.

`grep -ril "tenant\|merchant\|brand_owner" website/backend/src` currently returns
nothing: the backend has no tenant, membership, plan, lead, entitlement, or audit
concept at all. That is the next piece of work, and `data/types.ts` is the
specification for it — it is the prototype's domain model, unmodified.

The seams, in the order they'd be replaced:

1. `data/store.ts` — four functions (`getDb`, `updateDb`, `resetDb`, `newId`).
   Swap for `@/integrations/mirra-api` calls behind TanStack Query, which the
   rest of the app already uses.
2. `data/session.ts` — replace the persona switcher with real organisation-aware
   sessions. Note this is entirely separate from the shopper session in
   `@/stores`; `/dashboard/login` and `/auth/login` are different doors.
3. `data/actions.ts` — each function becomes a mutation. Signatures already
   match what an API layer would want.
4. `data/entitlements.ts`, `data/lifecycle.ts`, `data/rbac.ts` — pure logic that
   should be **enforced server-side** and mirrored here for UI affordances only.

## Charts: Bklit UI

The analytics surfaces render [Bklit UI](https://bklit.com/docs) chart
primitives, vendored from the `@bklit` shadcn registry into
`features/dashboard/charts/` (81 files, 12 registry items).

**Installed without `shadcn init`.** Bklit's charts turned out to need no
shadcn runtime — they depend on `@visx/*`, `d3-array`/`d3-shape`,
`@number-flow/react`, `motion` (already present), and a `cn` helper. No Radix,
no Recharts, no `class-variance-authority`. The only shadcn convention is the
`@/lib/utils` import, so `src/lib/utils.ts` was added with `cn` and nothing
else. `src/styles/globals.css` is byte-identical to before the install —
verified by diff — so none of shadcn's base tokens leaked into the marketing
surface.

The `shadcn` CLI itself fails in this environment (`unable to get local issuer
certificate` — Node doesn't read the macOS keychain roots that curl uses), so
the registry closure was resolved and written directly. `components.json` is
checked in with the `@bklit` registry configured, for whenever the CLI works.

The vendored directory is **eslint-ignored** (`eslint.config.js`): it is
upstream source kept byte-for-byte so it can be re-pulled, and it carries 5
`no-explicit-any` errors and 23 warnings under this repo's rules. Everything
outside `charts/` lints clean.

Bklit lands in its own lazy chunk (177 kB / 60 kB gzipped) pulled in only when
an analytics page opens; the main bundle grew 0.4 kB.

### Chart colour

The `--chart-*` custom properties Bklit reads are defined in `dashboard.css`,
scoped to `.dashboard-root`. Unlike Tailwind theme tokens these are ordinary
runtime `var()` lookups, so scoping works and nothing reaches the marketing
routes.

The two series hues are categorical slots 1 and 2 of the validated data-viz
palette **in fixed order** — blue `#2a78d6`, orange `#eb6834` — checked against
this surface with `validate_palette.js --mode light --surface "#fbfbfd"`:
lightness band, chroma floor, CVD separation (ΔE 24.7 protan), normal-vision
floor (ΔE 33.6) and 3:1 contrast all PASS.

This corrected the prototype's pairing, which used slots 1 and **3** (blue +
aqua `#1baf7a`). That pair passes CVD but fails contrast on a light surface
(2.72:1), which obligates direct labels or a table view. Slots 1+2 need no such
relief. Re-run the validator before changing these.

Chart chrome — grid, axes, crosshair, every label — wears neutral ink tokens,
never a series colour. Both series carry a legend with a text label and its
running total, so identity is never colour-alone.

## Post-login UI pass

`website/ZANDER_WHITEHURST_UI_UX_RESEARCH.md` scoped itself to the shopper
surfaces (`/measurements`, `/studio`, `/profile/*`) because the merchant
dashboard did not exist when it was written. Its consolidated guidance applies
here as the dashboard is also a post-login product surface. Applied so far:

- **Three-layer hierarchy on Analytics.** Four equal-weight stat tiles became
  one hero (session completion rate, with a worded status badge and a sentence
  saying what the number means and what usually causes a low one) over a
  supporting row. Per the brief's own caveat the hero was chosen on task
  evidence — completion rate is the one number that says whether try-on works —
  not for visual balance.
- **Fewer containers and borders.** `StatTile` grids became `StatRow`: one
  surface with hairline separators instead of N bordered boxes ("stop adding
  containers", "stop adding borders"). Used on Overview, Analytics, and Admin
  Tenants.
- **Status is never colour alone.** Every tone in `StatRow`/`HeroMetric` ships
  with its word.
- **One shared reduced-motion contract** for the whole surface in
  `dashboard.css`, covering Bklit's reveal animations — reduced-motion users
  get the final state immediately rather than a missing chart.
- **Table view as the chart's accessible equivalent**, with a `<caption>` and
  `scope="col"` headers.

Applied across the remaining pages:

- **Count-led page summaries.** Every list screen's subtitle now answers "how
  much of this needs me?" — `3 of 14 garments are missing data…`, `2 escalated
  and 1 open`, `Last 4 runs all clean`. Previously they restated the page title
  in prose.
- **Honest unavailable features.** Three forms looked functional and silently
  discarded input: Team's invite form (no action), Settings' appearance form
  (claimed "changes publish within a minute" while dropping every edit), and
  onboarding's team step (inputs with no `name`). They now say what isn't
  available and where to get it done. This is the brief's own acceptance
  criterion — *unsupported features do not claim success*.
- **No mock payment fields.** Onboarding's billing step rendered card-number
  and CVC inputs that went nowhere. A form that looks like it takes payment
  details but doesn't is worth refusing to build, so the step explains that
  card entry happens on the provider's hosted page and takes no details here.
- **Accessible tables.** `Table` now requires a `caption` (visually hidden) and
  emits `scope="col"`; the nine list pages pass one. Search and filter controls
  have real labels.
- **Honest empty states** on Products, Fabric and Size & fit, which previously
  rendered an empty table shell.

Not yet done: the deeper form-quality pass (`inputMode`, live formatting,
inline validation and first-error focus) on the garment-edit and ticket forms.

## The merchant flow

The canonical flow (from the client workflow diagram) is **sales-led and
invite-only**:

```
landing marketing site
  → verification form ("founding team gets to know about brand")
  → sales team talks ──→ training / workflow for the Shopify brand
  → pricing + setup: company-specific URL, unique URL per garment
  → dashboard and management site UNLOCKS ──→ 2D-to-3D, tech team integration
  → manage dashboard → intuitive UI → support tickets → retention
        └─ subscription branch: track status → end service → how to stop
```

What that settled, and what changed as a result:

**There is no self-serve merchant signup.** A brand gets a workspace only when
sales invites a qualified lead (`inviteLeadAction`), which is exactly the
existing Leads → Invite → onboarding path. `/dashboard/login` now says so and
points at `/join` instead of implying a sign-up exists.

**The dashboard "unlocks" after activation.** `PortalLayout` already enforced
this — an unactivated tenant is redirected to onboarding — so the guard matches
the flow as written.

**Lead capture already exists and is real.** `/join` posts to `/api/v1/join`,
which writes the `join_applications` collection — that *is* the flow's
verification-form step, built before this port. The prototype invented a
parallel lead pipeline with `estSkuCount` and `market`, fields no form on the
site ever captured. `Lead` now mirrors `JoinApplicationRequest` exactly
(name/email/company/website/role/monthlyOrders/goals), and the Leads screen
states plainly that it is showing demo data because the backend has no
`GET /api/v1/join/applications` yet. **That endpoint is the single missing link
between the public form and sales** — everything else on that path exists.

**Two URL levels, both missing.** The flow calls for a company-specific URL and
a unique URL per garment. `publicUrl` in `routes.ts` defines both; Publication
shows the company URL and preview link, and each garment's page shows its own
try-on URL once it is live. These are copy-and-share values — no route serves
them yet.

## Garment ingestion

Ingestion has one front door: **`+ Add garment`** on the Garments page, which
opens `/dashboard/portal/garments/new`. That screen's only job is picking the
colourway you have a physical sample of — one garment is one colourway of a
synced Shopify product — and it hands straight off to the garment workbench.

### Two surfaces, deliberately

There are two pages per garment and they do different jobs:

- **`/garments/:id`** — the summary. What state is this garment in? Capture
  set, garment data, size chart, and a rail of progress / Shopify mapping /
  live stock / shopper link / details.
- **`/garments/:id/setup?step=`** — the flow. **Sample → Capture → Material →
  Size & fit → Review**, with a vertical stepper and a persistent "what you're
  digitising" card.

An intermediate version merged the two — ingestion as tabs on the summary page.
It was worse than either: a summary interrupted by forms, and a form that had
lost its sense of progress. The merchant is stood next to a physical garment
doing one thing at a time; that is a flow, not a tab.

What the flow borrows from the summary page is its *layout language* — compact
cards, real density, a persistent context rail — because the earlier wizard's
problem was never that it was a wizard. It was tall, near-empty cards with one
oversized question each, which made five minutes of work feel like twenty.

Both are reachable from everywhere: `dashPath.garment(id)` for the summary,
`dashPath.garmentFlow(id, step?)` for the flow. Omitting `step` resumes at the
first outstanding one rather than restarting, so "Continue setup" always picks
up where the merchant left off. Every answer is written as it is given, so
**Save and exit** never loses anything.

Everything the ingestion model supports — reference size, the four-view capture
set, fabric, sizing, variant mapping, sold-out policy — is reached through that
one workflow rather than assembled by visiting three separate pages.

The existing Assets, Size & fit and Fabric pages stay exactly what they were:
the bulk-management screens. The wizard is the layer that stops them being
three unrelated chores.

**Cards open the summary, never the wizard.** Clicking a garment anywhere —
an Assets card, a Products colourway row, a Garments table row — opens its full
detail page. Continuing setup is always an explicit, separately labelled action
("Continue capture →", "Continue setup →"). A card that silently drops you into
a multi-step flow is not a card.

### Why a capture flow exists at all

Adding a garment is **not** publishing. Publication makes an already-built
garment visible or hidden; this is how a garment comes to exist.

When a brand releases a drop, the products land in Shopify with their
marketing photography — models, props, crops, colour grading — and none of it
can be reconstructed into a wearable garment. Shopify keeps supplying product,
variants, price and stock. What it cannot supply is imagery Mirra can rebuild
geometry and texture from, so every new colourway needs its physical sample
re-shot to specification.

That specification is `CAPTURE_SPEC` in `data/ingestion.ts`, shown at the top
of the Capture step: garment not model, whole garment in frame, flat/unstyled,
plain contrasting background, even light, camera square — each with the reason
it matters. Merchants aren't asked to understand reconstruction, only to follow
six rules.

### Reference size is the load-bearing idea

The prototype had nowhere to record *which physical garment* was photographed.
Every capture, every auto-measurement and every derived size describes one
sample, and without `referenceSize` none of it is auditable six months later.
It now appears on the garment row, the Assets card, the Size & fit table and
the size chart itself.

The corollary is that merchants **do not photograph every size**. One reference
sample plus graded measurements produces every digital size — 6 sizes × 5
colourways would otherwise mean 30 photo sessions per product. The exception is
explicit: answering "some sizes use a different pattern" creates a second
construction block with its own reference sample, and Mirra interpolates within
each block separately.

### One stage, not two statuses

`qaStatus` and `publication.status` were separate fields that could disagree —
a garment could read "QA passed" and "Draft" at once — and QA was a dropdown
the merchant set themselves. Both collapse into one `GarmentStage`:

```
draft → processing → needs_data → merchant_review → in_qa → ready → live
                                                                  ⇅
                                                               paused
        sync_error interrupts from anywhere
```

`MERCHANT_TRANSITIONS` grants merchants everything up to `merchant_review` and
`ready → live`. The `in_qa → ready` edge belongs to `qaDecisionAction`, which
requires an internal role — so a brand can no longer pass its own QA.

### Honesty about what photos can tell you

Four photographs infer shape and relative proportion. They do **not** yield
reliable centimetres without a physical scale, so auto-measure is a separate,
optional step that asks for a calibration card, a depth capture, or one anchor
dimension. Measurements come back with per-value confidence (`high` / `review`).

Likewise `gradingSource`: a full graded chart is `chart`, brand increments are
`rules`, and sizes inferred from a single sample are `estimated` — which sets
`gradingUnverified` and shows a **Draft sizes — verification required** banner.
Mirra does not quietly present derived numbers as measured.

The other distinction merchants rarely realise they are making is
`sizeChartKind`: body measurements and finished-garment measurements are
different numbers for the same garment. The flow asks outright, and "I'm not
sure" is a recorded answer that flags the garment rather than a silent guess.

### Provenance everywhere

`sizeSource`, `sizeChartKind`, `gradingSource` and `fabricSource` are surfaced
on the bulk pages — Size & fit gained **Reference** and **Source** columns,
Fabric shows "Shopify · confirmed" / "Merchant entered" / "Tech pack" / "Mirra
estimate" under each composition. This is what makes a wrong output diagnosable.

### Category-aware questions

`MEASUREMENT_FIELDS` gives each category only its own measurements — a trouser
is asked for rise, inseam and leg opening, never bust — each with a "how to
measure" note.

### Fabric suggests, merchant confirms

`suggestAttributes` derives stretch/drape/opacity/thickness from the
composition and labels them **Mirra suggestion** until confirmed
(`attributesSuggested`). Merchants correct rather than behave like textile
engineers. Advanced properties (GSM, warp/weft stretch, recovery) stay behind
disclosure.

### Colourway reuse

Once one colourway is done, siblings offer "same cut and fabric" (reuse
geometry, grading, fit *and* material — only new colour imagery needed) or
"same cut, different fabric" (reuse geometry and grading, fresh material
profile). Seeded: Ivory reuses Noir.

### Inventory is Shopify's

Mirra reads `ProductVariant.inventory` and never writes it. The one merchant
decision is the sold-out policy — *keep available for try-on, disable purchase*
(default) or *hide that size* — set store-wide in Settings, overridable per
garment. A generated size does not stop existing because stock hit zero.

### Completion, not a missing-count

`requirements()` returns five checks — Shopify mapping, Images, Size & fit,
Material, Fit — with `blocking` separating what stops a publish from what
merely improves it. Garments shows "3 / 5 complete" plus the per-requirement
breakdown; Review splits **Blocking** from **Suggestions**.

### What is simulated

The UI states are real and driven by the model; these capabilities are backend
work and are visibly stubbed rather than faked:

| Stubbed | What exists today |
|---|---|
| Phone capture over QR | The QR panel and live per-view arrival; capture is triggered in-page |
| CV validation | Accept/reject states with specific messages ("The lower hem is outside the frame"), triggered manually |
| 2D→3D generation | The `processing` stage, a non-blocking banner, and a "simulate completion" control |
| Auto-measure | Calibration input is real; returned measurements are derived from the anchor |
| Size-chart OCR/upload | Source buttons record provenance and populate a chart |
| Try-on preview render | Placeholder with a size switcher, labelled as not yet wired |

## Duplicates

Removed:

| Duplicate | Resolution |
|---|---|
| Two line-chart implementations (hand-rolled SVG + the new one) | Deleted `components/charts.tsx`; both surfaces now render `components/analytics-charts.tsx`. |
| Overview's second stat row repeated Analytics' headline totals verbatim | Dropped from Overview, which now links to Analytics from the chart card. |
| Publication showed the subdomain three times, and its "Domain & redirects" card duplicated Settings' "Domains" card | Domain configuration belongs to Settings. Publication keeps one line of live state plus a link. |

Resolved against the flow:

| Duplicate | Resolution |
|---|---|
| `GarmentTable` rendered identically on Garments and Publication — two screens competing to be where you publish | The flow separates setup/enrichment from management, so the table takes a `mode`. `catalogue` (Garments) leads with data readiness and its row action is "Complete data →"; `publication` (Publication) keeps selection, bulk actions and status transitions. Each screen now has one primary task. |
| Two sign-ins, `/dashboard/login` and `/auth/login` | Not a duplicate — two personas, and the flow makes the merchant door invite-only. The merchant page now states there is no sign-up, links to `/join` for access, and cross-links the shopper sign-in. |
| Three wordmarks | The dashboard was hand-setting `mirra.` in text because the prototype had no brand files. It now uses `@/components/ui/logo`, the same component `ProfileLayout` uses. Marketing's `MirraBrand` is left alone — the UI brief forbids touching that surface. |
| A second lead pipeline (`db.leads` with invented fields) alongside the real `/join` → `join_applications` | One lead shape, mirroring the backend schema. See the flow section above. |

## Blast radius

Everything new is under `features/dashboard/**`. Outside it:

- `src/router.tsx` — three added lines (lazy import + `/dashboard/*` route).
- `src/styles/globals.css` — the two accent tokens above, and nothing else;
  unchanged by the Bklit install.
- `src/lib/utils.ts` — new, `cn` only (the import Bklit's files expect).
- `eslint.config.js` — ignores the vendored chart directory.
- `components.json` — new, for the `@bklit` registry.
- `package.json` — 11 runtime deps (`@visx/*`, `d3-array`, `d3-shape`,
  `@number-flow/react`) and 2 type packages.

The dashboard is one lazy chunk (45 kB / 14 kB gzipped) behind `/dashboard/*`,
so shoppers who never visit it never download it.

## Verified

`npm run typecheck`, `npm run lint` (0 errors, 0 warnings), and `npm run build`
all pass. The chart palette was validated with the data-viz validator as
recorded above.

**Browser walkthrough is still outstanding** — the Chrome automation used here
is blocked from `localhost:3000` by extension site permissions, so no route has
been rendered and looked at. The charts in particular are unverified visually:
they typecheck and build, but Bklit's composition API was read from vendored
source rather than from a working example, so axis/tooltip wiring needs eyes on
it. Grant the extension permission for `localhost:3000`, or run
`npm run dev` and check `/dashboard/portal/analytics` manually.
