# Port Audit — `user-side` (Shopper Runtime) → Standalone Site

*Last updated: 2026-07-18*

## Context

`user-side` ("Mirra — Shopper Runtime") was built as a widget embedded in merchant Shopify stores: multi-tenant, tenant-scoped routing (`/t/[tenantSlug]/...`), cart handoff back to the merchant's Shopify cart, and a separate `merchant_dashboard` repo as the control plane for tenant/catalogue data. We've now confirmed the target for this build is a **standalone site** — no merchant tenants, no Shopify embed, our own catalogue and accounts.

Most of the actual product logic in `user-side` (auth, photo capture, avatar generation, the try-on "studio," profiles) is **not inherently SaaS-specific** — it's generic product experience that happens to be wrapped in tenant-routing and Shopify-integration code. This doc goes through the repo piece by piece and marks what survives the move to standalone, what needs rework, and what gets dropped entirely.

**Confidence note**: verdicts below are based on directory structure, filenames, `README.md`, `docs/backend-contract.md`, `docs/going-live.md`, and a handful of files read in full (`app/layout.tsx`, `integrations/mirra-api/index.ts`, `components/ui/button.tsx`, `package.json`). Component bodies were not all individually read — verify each ✅/🔧 item's actual content before wiring it into the new build, especially anything touching cart/checkout or tenant context that might be more deeply threaded through than the filename suggests. I also found no evidence of a distinct pre-built "standalone mode" already toggled on somewhere in this repo — this audit is a decomposition of the SaaS-oriented codebase into generic vs. SaaS-specific parts, not a discovery of an existing standalone path. Flag if there's another branch or the `merchant_dashboard` repo that changes this.

## Legend

- ✅ **TAKE** — reusable as-is or with minor adaptation, no tenant/merchant/Shopify coupling
- 🔧 **ADAPT** — the concept is right, implementation needs rework to remove tenant/merchant/Shopify assumptions
- ❌ **DROP** — inherently SaaS/Shopify-embed specific, not applicable to a standalone site

---

## Routes (`src/app/`)

| Route | Verdict | Notes |
|---|---|---|
| `/` (launch resolver) | ❌ DROP | Resolves incoming Shopify launch params (tenant/product/variant). Replace with a normal homepage. |
| `/auth/sign-up`, `/login`, `/verify-email`, `/forgot-password` | ✅ TAKE | Generic account flows, no tenant coupling. |
| `/t/[tenantSlug]/launch` | ❌ DROP | Shopify launch entry point. Not applicable. |
| `/t/[tenantSlug]/onboarding/avatar` | 🔧 ADAPT | Avatar generation onboarding — generic. Drop the tenant segment → becomes `/onboarding/avatar`. |
| `/t/[tenantSlug]/onboarding/measurements` | 🔧 ADAPT | Measurement intake — generic. Drop tenant segment → `/onboarding/measurements`. |
| `/t/[tenantSlug]/studio` | 🔧 ADAPT | The core try-on experience — generic. Drop tenant segment → `/studio`. This is steps 4–6 of our flow (load avatar, choose clothes, show result) in one page. |
| `/capture`, `/capture/[token]` | ✅ TAKE | QR-based desktop-to-mobile photo capture. Not SaaS-specific — a generic capture mechanism, directly useful for our measurement+photo step. |
| `/profile`, `/profile/avatar`, `/profile/measurements`, `/profile/signature-looks`, `/profile/privacy` | ✅ TAKE | Generic account management. Matches "load avatar" and future account needs directly. |
| `/error/tenant-not-found` | ❌ DROP | No tenants in standalone. |
| `/error/product-unavailable` | ✅ TAKE | Generic (garment removed/out of stock). |
| `/error/account-inactive` | ✅ TAKE | Generic (suspended/deleted account). |

## Components

| Folder / File | Verdict | Notes |
|---|---|---|
| `components/auth/*` (auth-shell, oauth-buttons, quick-access-control) | ✅ TAKE | Generic auth UI. |
| `components/capture/*` (camera-capture, silhouettes) | ✅ TAKE | Generic photo-capture UI (pose guides, camera access). |
| `components/onboarding/*` (generation-progress, measurement-row, qr-card, sync-status, synchronized) | ✅ TAKE | Generic — avatar generation progress and the QR desktop↔mobile pairing UX aren't SaaS-specific. Directly addresses the "time issues" wait-state problem we already flagged. |
| `components/studio/avatar-figure.tsx`, `avatar-stage.tsx`, `studio-header.tsx` | ✅ TAKE | Core avatar/garment rendering shell. |
| `components/studio/product-rail.tsx`, `product-panel.tsx`, `curated-look-rail.tsx` | ✅ TAKE | Catalog browsing — directly matches "choose clothes from preset" (step 5). |
| `components/studio/hanger-bar.tsx` | ✅ TAKE | Recently-tried/saved items — generic, nice UX carried over for free. |
| `components/studio/signature-look-dialog.tsx` | ✅ TAKE | Save a full outfit combo. Not in our original 7-step flow but generic and already built — free enhancement, not core-critical. |
| `components/studio/pinch-carousel.tsx` | ✅ TAKE | Generic carousel UI. |
| `components/studio/cart-drawer.tsx` | 🔧 ADAPT / possibly defer | Almost certainly wired to hand off to Shopify checkout. Our pilot flow (per `website_pilot_v1_scope.md`) ends at "show the result," not a real purchase — keep the UI shell if useful, but the checkout action needs to be replaced or removed. Lowest-priority item in this list. |
| `components/ui/*` (button, error-screen, fabric-panel, field, logo, misc) | ⚠️ Judgment call | This is exactly the "small button component" pattern you said not to build going forward — but it's already built, and (from reading `button.tsx`) it's a well-crafted shared primitive with variants/sizes/motion, not a trivial wrapper. Recommend keeping it as inherited rather than re-atomizing from scratch; flag if you'd rather consolidate it during the port. |
| `components/providers/app-providers.tsx` | ✅ TAKE | App-level providers (TanStack Query, etc.) — reimplement without Next-specific bits. |

## Integrations (`src/integrations/`)

| File | Verdict | Notes |
|---|---|---|
| `mirra-api/types.ts`, `errors.ts`, HTTP client | ✅ TAKE (as reference) | Generic contract shape — will need rewriting field-by-field against our own backend's actual schema, but the pattern is worth keeping. |
| `mirra-api/runtime-provider.ts` (the interface) | ✅ TAKE | This is the key architectural pattern: one typed seam (`MirraRuntimeProvider`) that the whole UI codes against, with the actual implementation swapped by environment. Directly reusable idea regardless of framework. |
| `mirra-api/mock-runtime-provider.ts` | ✅ TAKE | Valuable for frontend dev without the real backend running. |
| `mirra-api/dashboard-runtime-provider.ts`, `dashboard-adapter.ts` | ❌ DROP | Maps Shopify-merchant-dashboard concepts (tenant config, merchant theme, external catalogue) onto the runtime. Not needed — we own our catalogue directly. |
| `mirra-api/public-runtime-provider` | 🆕 Doesn't exist yet | Referenced in their docs as the future target for "when the shared backend exists." This is exactly what our new backend-integration work builds — not something to port, something to build fresh against the same `runtime-provider.ts` interface. |
| `engines/avatar/types.ts` (`AvatarEngineProvider`) | ✅ TAKE | Typed seam: `createCaptureSession · getCaptureSession · submitCaptureAssets · startAvatarGeneration · getAvatarGenerationStatus · getAvatarProfile · updateMeasurements · deleteAvatarProfile`. This is exactly the CLO3D integration boundary — matches "don't build the CLO3D microservice now, but leave the seam" perfectly. |
| `engines/try-on/types.ts` (`TryOnEngineProvider`) | ✅ TAKE | Same pattern for try-on/VTO rendering. Same reasoning. |

## Lib

| File | Verdict | Notes |
|---|---|---|
| `lib/launch-context.ts`, `return-url.ts`, `cart-handoff.ts` | ❌ DROP | All Shopify-launch/return/cart-handoff specific. |
| `lib/hanger.ts` (LRU) | ✅ TAKE | Generic recently-viewed cache. |
| `lib/analytics.ts` | 🔧 ADAPT | Keep the event vocabulary concept; drop the merchant-dashboard ingest mapping (`DASHBOARD_EVENT_MAP`) — point events at our own backend/analytics instead. This event vocabulary is worth keeping regardless, since this pilot's whole goal is learning user behavior. |
| `lib/units.ts` | ✅ TAKE | Generic measurement unit conversion. |
| `lib/state-machines/capture.ts`, `avatar-job.ts`, `try-on.ts` | ✅ TAKE | Formalized state machines for exactly the async, slow-job flows we already flagged as needing real UX design. Free win. |
| `lib/state-machines/tenant.ts` | ❌ DROP | Tenant gating/suspension/entitlement — not applicable. |

## Hooks, Stores, Config

| File | Verdict | Notes |
|---|---|---|
| `hooks/use-shopper`, `use-capture`, `use-try-on`, `use-signature-looks` | ✅ TAKE | Generic. |
| `hooks/use-tenant` | ❌ DROP | Tenant-specific. |
| `stores/studio-store.ts` (zustand) | ✅ TAKE | Generic studio UI state. |
| `config/env.ts` | 🔧 ADAPT | Keep the "all configuration in one place" pattern; drop tenant/Shopify/dashboard-specific variables. |
| `config/urls.ts` | ❌ DROP / rewrite | Currently "tenancy-aware URL builders" (path↔subdomain tenancy). Standalone needs plain route builders — much simpler, write fresh. |
| `src/proxy.ts` | ❌ DROP | Subdomain-per-tenant rewriting. Not applicable. |

## Server (mock backend)

`src/server/mock/*` + `app/api/v1` mock route handlers — 🔧 **ADAPT**. The *concept* (in-memory fixtures behind the same typed contract, for frontend dev without a live backend) is valuable and worth keeping. The *implementation* is Next.js API routes, which don't exist once we're off Next.js — needs to become either a browser-side mock (e.g., MSW) or just point local dev at our real FastAPI backend's own seed/mock data instead of maintaining a second mock layer.

## Top-level `integration/shopify/` package

❌ **DROP entirely.** Manual embed package (snippet, block, link, enhancer) for merchants to add a "Try It On" button to their Shopify product pages. Not applicable to a standalone site.

## `docs/` (openapi.yaml, backend-contract.md, going-live.md)

🔧 **ADAPT / reference only.** Not directly reusable as our API contract — it's scoped to tenant/dashboard concepts we're dropping. But genuinely useful as a reference for shaping our own FastAPI backend: the staged avatar-job status pattern, the capture-session token flow, and the measurement-patching semantics are all good ideas worth re-specifying against our own schema.

## Tests

Vitest (unit) + Playwright (e2e) as an **approach** is worth carrying forward — but the actual test content (tenant launch, Shopify cart handoff, dashboard sync) is tied to flows we're dropping and will need to be rewritten against the standalone flows.

---

## Net Result: Standalone Route List

Combining `Mirra-landing-page` (as-is, already on our stack) with the ported/adapted pieces of `user-side`:

| Route | Source |
|---|---|
| `/`, `/pricing`, `/team` | `Mirra-landing-page`, as-is |
| `/auth/sign-up`, `/login`, `/verify-email`, `/forgot-password` | `user-side`, taken as-is |
| `/capture`, `/capture/[token]` | `user-side`, taken as-is |
| `/onboarding/measurements` | `user-side`, de-tenanted |
| `/onboarding/avatar` | `user-side`, de-tenanted |
| `/studio` | `user-side`, de-tenanted — this single page covers "load avatar," "choose clothes," and "show result" (steps 4–6) |
| `/profile`, `/profile/avatar`, `/profile/measurements`, `/profile/signature-looks`, `/profile/privacy` | `user-side`, taken as-is |
| `/error/product-unavailable`, `/error/account-inactive` | `user-side`, taken as-is |
| Guest mode / guest avatar | **Net new** — no equivalent exists in `user-side`; it assumes an authenticated shopper throughout |
| Paste-a-link garment extraction (optional, step 7) | **Net new** — no equivalent in either repo |

**Bottom line**: the auth flow, photo-capture flow, avatar-generation flow, the entire "studio" (try-on) experience, profile management, the mock/live runtime-provider architecture, and the CLO3D-facing engine seams are all inherited with light rework. What's actually net-new work for this pilot is: removing tenant/Shopify plumbing, guest mode, the optional link-scraping feature, and the real backend behind the `public-runtime-provider` seam.
