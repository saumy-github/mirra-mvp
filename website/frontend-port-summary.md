# Frontend Port Summary

*Last updated: 2026-07-18 (see final entry below)*

Retrospective record of what actually got copied into `website/frontend/` from the two source repos, what was deliberately left out, and why. `port-audit-user-side.md` was the pre-implementation *plan* for the `user-side` side of this; this document reports what actually happened during implementation, across **both** sources.

## The two sources

- **`Mirra-landing-page`** — marketing site only. Already on the target stack (Vite + React + TS + Tailwind + react-router-dom + `motion`). Small, low-friction port.
- **`user-side`** — "Mirra Shopper Runtime," a full Next.js app built for a different product shape (multi-tenant, Shopify-embedded SaaS). Large and sophisticated; the bulk of the actual work was de-tenanting and porting this one.

---

## From `Mirra-landing-page`

### Copied

| What | New location |
|---|---|
| `Home`, `Pricing`, `MeetTheTeam` pages | `pages/Home.tsx`, `Pricing.tsx`, `Team.tsx` |
| `Hero`, `Header`, `MirrorCTA`, `ProductReveal`(+css), `ProblemTeardown`(+css), `LiveLedger`, `RoiCalculator`, `Closure`, `TextReveal`, `LiquidMetal`, `LaurelPortrait`, `CustomCursor`, `DemoPlaceholder` | `features/marketing/components/` |
| Waitlist form (was inline in `App.tsx`) | extracted to `features/marketing/components/WaitlistModal.tsx` |
| Smooth-scroll setup (Lenis + GSAP ScrollTrigger, was inline in `App.tsx`) | extracted to `features/marketing/marketing-layout.tsx`, scoped to marketing routes only |
| Public assets (audio track, `Footer-Mirra.jpeg`, `shirt_baked.glb`) | `public/` |

### Left out / changed, and why

- **Its own `<BrowserRouter>`** — not used. This app has exactly one router; the marketing pages are nested routes under it, not a separate mini-app.
- **`onBookDemo` prop drilling** from `App.tsx` down through `Home`/`Pricing`/`Team` — replaced with React Router's `<Outlet context>` from `MarketingLayout`, since these are now nested routes under a shared layout rather than receiving props from a single top-level component.
- **`lib/utils.ts`** (a `cn()`/clsx helper) — copied to `lib/marketing-utils.ts`, but grepping the original repo confirmed it's never actually imported anywhere, even in the source. Dead code carried over as-is, not wired to anything.
- **`index.html`'s `<model-viewer>` CDN script tag** — dropped. Also unused in the source (confirmed via grep), and superseded anyway by the React Three Fiber decision for real 3D once GLB avatar assets exist.
- **`main.tsx` / `index.css`** — not copied directly. Folded into this app's own `main.tsx`/`App.tsx`, and the theme tokens merged into one shared `globals.css` (see below).

---

## From `user-side`

The large port. Full file-by-file take/adapt/drop reasoning is in [`port-audit-user-side.md`](port-audit-user-side.md); this is the summary of what that plan turned into.

### Copied close to as-is

- **Shared architecture layer**: `integrations/mirra-api/*` (types, schemas, errors, client, runtime-provider, http-runtime-provider, public-runtime-provider), both CLO3D-facing engine seams (`integrations/engines/avatar`, `.../try-on`), all four state machines, `lib/units.ts` / `format.ts` / `analytics.ts` / `hanger.ts`, all five hooks, the zustand `studio-store`.
- **Components**: `ui/` (kept per your explicit instruction not to re-atomize what was already well-built), `auth/`, `capture/`, `onboarding/`, and the full `studio/` set (avatar figure/stage, studio header, product rail/panel, hanger bar, cart drawer, signature-look dialog, curated-look rail, pinch carousel).
- **Pages**: the 4 auth pages, both capture pages, both onboarding pages, the studio page, all 5 profile pages, both error pages.

### Left out entirely, and why

| Left out | Why |
|---|---|
| Tenant system — `useTenant`, `TenantConfiguration` type, `lib/state-machines/tenant.ts`, `/t/[tenantSlug]/...` routing | No merchant tenants in a standalone site |
| Shopify integration — `integration/shopify/` embed package, `lib/launch-context.ts`, `launch-state.ts`, `return-url.ts`, `cart-handoff.ts`, `createCartHandoff` API method, `externalShopifyVariantId` fields | No merchant to hand a cart off to |
| `dashboard-runtime-provider.ts` + `dashboard-adapter.ts` | Mapped merchant-dashboard concepts onto the runtime; we own our catalogue directly, no dashboard |
| Root `/` "launch resolver" `page.tsx` | Replaced with a real homepage (from `Mirra-landing-page`) |
| `docs/openapi.yaml`, `backend-contract.md`, `going-live.md` | Scoped to tenant/dashboard concepts, not reusable as our contract — used as inspiration for `backend-structure-plan.md` instead |
| Tests (55 unit + 10 e2e) | Tied to tenant/Shopify flows being dropped; would need rewriting from scratch, out of scope for "implement the frontend" |
| `src/server/mock/*` (~1,500 lines of Next API-route mock backend) | Not portable line-by-line — no Next server left to host API routes on. Replaced with a smaller, purpose-built in-process mock (`src/mocks/`) rather than porting tenant/entitlement-aware mock logic that no longer applies |
| `crossMerchantAvatarReuse` consent field | Meaningless with one "merchant" (us) |

### Adapted — concept kept, implementation reworked

- **`Studio.tsx`** — the heaviest rewrite. Stripped all tenant params/state; replaced merchant cart handoff with a local-only cart ("Checkout" surfaces an honest toast, since no real payment/checkout backend exists yet for this pilot).
- **`onboarding/Avatar.tsx`, `Measurements.tsx`** — de-tenanted (dropped `tenantSlug` routing and `tenantId` from analytics calls).
- **`studio-header.tsx`** — dropped merchant theme/branding props, uses static Mirra branding instead.
- **`product-panel.tsx`, `hanger-bar.tsx`, `cart-drawer.tsx`** — dropped `tenant`/`locale` props, price formatting now uses each item's own `currency` field.
- **`hanger.ts`, `studio-store.ts`** — dropped `tenantId`/`externalShopifyVariantId` fields from `OutfitLayer`/`HangerEntry`/`StudioCartItem`.
- **`ProfileLayout.tsx`** — Next's `{children}` prop pattern → React Router's `<Outlet />` nested-route pattern.

---

## Net-new — not from either repo

- **`src/mocks/`** — the in-process mock backend (fixtures, store, mock-provider). Purpose-built rather than ported; see above.
- **Guest mode** — `continueAsGuest`, wired into `Login.tsx`. No equivalent existed in either source.
- **`src/router.tsx`, `App.tsx`, `main.tsx`** — the whole app's routing/shell assembly. Neither source had one router serving both marketing and app pages.
- **Toast notifications (Sonner)** — new dependency, wired into `Studio.tsx` for cart and signature-look feedback.
- **`components/layout/PageFallback.tsx`, `pages/NotFound.tsx`** — Suspense fallback and 404 page.
- **Merged `globals.css`** — combines both repos' Tailwind `@theme` tokens under one stylesheet (documented inline in the file itself, since the two repos' palettes weren't designed to coexist).
- **`config/env.ts` was written, then deleted** at your request — env vars are now read directly via `import.meta.env.VITE_*` at each call site instead of through a central wrapper module (see the `.env.development`/`.env.example` setup).

---

## Post-port cleanup

A pass through the finished port to find unused files, single-use components, and repeated code, requested separately after the initial implementation. Full findings (including what was checked and *not* changed — most single-use components turned out to be legitimate page-section splits, not bloat) are in the conversation; this is the record of what actually got removed/changed.

### Deleted (dead code — zero usages anywhere)

- **`lib/marketing-utils.ts`** (the `cn()` helper from `Mirra-landing-page`) — confirmed unused even in the original source repo, never wired to anything after the port either.
- **`MonoTag` export in `components/ui/misc.tsx`** — defined, never imported.
- **`integrations/engines/avatar/provider.ts` + `types.ts`** (`getAvatarEngine`, `AvatarEngineProvider`) — built as the CLO3D integration seam per the architecture plan, but nothing ever called it: `Avatar.tsx`/`use-capture.ts` call `getRuntimeProvider()` directly instead. This was inconsistent with the try-on side, where `use-try-on.ts` genuinely does route through `getTryOnEngine()`. Deleted rather than wired in — if a future pass adds real avatar-engine-specific logic (vs. just proxying to the runtime provider, which is all it did), it can be rebuilt then, following the try-on file as a template.

### Deduplicated

- **`mocks/mock-provider.ts`'s local `STAGE_LABELS`** was a byte-for-byte copy of `lib/state-machines/avatar-job.ts`'s exported `avatarStageLabels`. Now imports and reuses it instead.
- **New file `lib/motion-presets.ts`**, extracting three `motion` spring configs that had been copy-pasted across components (a pattern inherited from `user-side`, not introduced during the port):
  - `MATERIAL_SPRING` (`stiffness:420, damping:41, mass:1`) — was defined identically, same name, in 5 files: `synchronized.tsx`, `qr-card.tsx`, `sync-status.tsx`, `generation-progress.tsx`, `pages/onboarding/Avatar.tsx`.
  - `CONTROL_SPRING` (`stiffness:520, damping:38, mass:0.7`) — was defined identically, same name, in `cart-drawer.tsx` and `studio-header.tsx`. (Note: `curated-look-rail.tsx` also has a local `CONTROL_SPRING`, but with different values — left untouched since it isn't actually a duplicate, just a name collision in separate module scopes.)
  - `PANEL_SPRING` — same values as `signature-look-dialog.tsx`'s old `SHEET_SPRING`, different name. `signature-look-dialog.tsx` now imports `PANEL_SPRING as SHEET_SPRING` to keep its internal usages unchanged.
  - The other locally-defined springs (`RAIL_SPRING`, `HANGER_SPRING`, `FIGURE_SPRING`, `STAGE_SPRING`, `DRAWER_SPRING`, `SNAP_SPRING`, `RETURN_SPRING`, etc.) have genuinely distinct values — each component's own tuned feel, not duplication — and were left as local constants.

Verified after each change: `tsc --noEmit` and `vite build` both clean.

---

## ESLint + Prettier

Added for cross-developer consistency, on top of the existing `tsc --noEmit` check. The `package.json` `"lint"` script existed from the initial scaffold but was never actually wired up (no `eslint` dependency, no config) — this closes that gap rather than adding it from scratch.

### What was added

- **ESLint** (flat config, `eslint.config.js`) — `typescript-eslint` + `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh`, the standard Vite+React+TS combination. `@typescript-eslint/no-unused-vars` is configured with `argsIgnorePattern`/`varsIgnorePattern`/`destructuredArrayIgnorePattern` all set to `^_`, matching the existing `_password`-style "intentionally discarded" convention already used in `mock-provider.ts`.
- **Prettier** (`.prettierrc.json`) — `printWidth: 100` to match the Python side's convention in `repo-rules.md`; otherwise Prettier's own defaults (double quotes, trailing commas, 2-space indent).
- **`eslint-config-prettier`** so the two tools never fight over formatting rules.
- New `package.json` scripts: `lint:fix`, `format`, `format:check` (alongside the now-functional `lint`).
- **`.vscode/settings.json` + `.vscode/extensions.json`** — format-on-save and recommended-extensions prompt (ESLint + Prettier), committed to the repo (adjusted `website/.gitignore`, which previously blanket-ignored `.vscode/`, to allow just these two files through — everything else in `.vscode/` stays personal/gitignored).
- Scope: this setup only covers `website/frontend/`'s JS/TS. It doesn't apply to other projects, and doesn't touch the Python pipeline elsewhere in `mirra-mvp` (different tooling entirely, e.g. `ruff`/`black`, not set up here).

### What the first lint run found — real, pre-existing issues, not noise

Running ESLint for the first time against the ported codebase surfaced 8 errors and 8 warnings, all fixed:

- **5 `any` types replaced with real ones**, all in files ported from `Mirra-landing-page`:
  - `LiquidMetal.tsx` — `config?: any` and a `new (ShaderMount as any)(...)` cast. The `@paper-design/shaders` package actually ships a proper `ShaderMount` class and `ShaderMountUniforms` type; neither `any` was necessary. Also simplified the cleanup function, which was defensively duck-typing for a `.destroy()` method that doesn't exist on the real type — only `.dispose()` does.
  - `ProblemTeardown.tsx` — `FlashText`/`PlaceholderTile` given real prop interfaces instead of `any`; the GSAP `gsap.utils.toArray(...)` call now uses its generic parameter (`toArray<Element>(...)`) instead of casting the `.forEach` callback args to `any`.
  - `WaitlistModal.tsx` — the parsed fetch-response `data` variable typed as `{ message?: string; error?: string }`, matching what it's actually destructured into.
- **Dead imports removed**: `HelpCircle` (unused lucide icon) in `LiveLedger.tsx`; `LaurelPortrait` and `KineticText` (never rendered) in `Team.tsx`.
- **Dead props removed**: `Team.tsx`'s `MeetTheTeam` and `Closure.tsx` both destructured/accepted an `onBookDemo` callback that was never actually called in either component's render — true in the original `Mirra-landing-page` source too, not something introduced during the port. Removed from both components and from `Home.tsx`'s `<Closure />` call site (Team/Home's other CTA-driven sections, `Hero`/`ProblemTeardown`/`RoiCalculator`, do use it and were left alone).
- **Removed a `key?: any` prop** from `ParallaxTeamCard`'s prop type in `Team.tsx` — `key` is a React-reserved prop that's never actually passed through to a component; declaring it in the prop type does nothing and doesn't belong there.
- **Minor unused-variable cleanups**: an unused loop index in `mocks/fixtures.ts`, an unused `containerRef` effect-cleanup warning in `LiquidMetal.tsx` (resolved as a side effect of the `any` fix above, since the simplified cleanup no longer touches the ref).

Also ran `prettier --write .` for the first time — reformatted 62 files to a single consistent style (the codebase had a real mix of single/double quotes and wrapping conventions, since it was assembled from two source repos with different conventions plus new files written during the port). Verified after: `tsc --noEmit`, `eslint .`, and `vite build` all clean.

---

## Tailwind v4 canonical-class migration

A separate, third diagnostic source — not ESLint, not Prettier — surfaced ~180 issues: the Tailwind CSS IntelliSense VS Code extension flagging old (but still valid) Tailwind syntax against v4's newer preferred forms. Expected, since the codebase was assembled from two repos that predated some of these v4 conventions: `!class` important-prefix → `class!` suffix, `bg-gradient-to-*` → `bg-linear-to-*`, `supports-[backdrop-filter]:*` → `supports-backdrop-filter:*`, arbitrary values that match a defined theme token (e.g. `rounded-[10px]`) → the semantic utility name (`rounded-field`, since `--radius-field: 10px` is already defined in `globals.css`), and several arbitrary pixel/opacity values → their canonical scale-based form (`max-w-[1040px]` → `max-w-260`, `to-ink/[0.06]` → `to-ink/6`).

Given the volume (180 instances across 15+ files), used Tailwind's own official codemod (`npx @tailwindcss/upgrade --force`) rather than hand-editing each one — purely a syntax rewrite to equivalent forms, not a visual change, and the tool is purpose-built for exactly this. `--force` was needed only because the wider `mirra-mvp` repo has unrelated pre-existing uncommitted Python changes from before this session; `website/frontend/` itself was untracked in git at the time (never yet committed), so there was no risk of losing prior work either way.

Migrated 25 files plus `globals.css`, and bumped `tailwindcss`/`@tailwindcss/vite` from `^4.1.14` to `^4.3.3` (still v4, no breaking changes). One file (`pages/onboarding/Avatar.tsx`) needed a Prettier re-format afterward to match line-wrapping to the new class strings. Verified after: `tsc --noEmit`, `eslint .`, `prettier --check .`, and `vite build` all clean, theme tokens in `globals.css` intact, and a full-codebase grep confirmed no leftover old-style patterns (`bg-gradient-to-*`, prefix-`!important`) remain.

A follow-up VS Code screenshot showed the same ~180 issues again after this was already done — that was a **stale Problems panel** (the Tailwind IntelliSense extension hadn't re-scanned), not a real regression. Confirmed by re-running the codemod: `0 files changed` the second time.

---

## Two more plugins: `prettier-plugin-tailwindcss` + `@tanstack/eslint-plugin-query`

- **`prettier-plugin-tailwindcss`** — sorts utility classes within `className` strings into Tailwind's canonical order (ordering only, not syntax — complements the v4 migration above rather than overlapping with it). Needed one explicit config line for Tailwind v4's CSS-based theme: `"tailwindStylesheet": "./src/styles/globals.css"` in `.prettierrc.json`, since there's no `tailwind.config.js` for it to auto-detect.
- **`@tanstack/eslint-plugin-query`** — the official TanStack Query lint rules (`flat/recommended`), added to `eslint.config.js` alongside the existing rule sets.

### What the first run of the query plugin found — also real, not noise

7 errors, all the same underlying pattern: `const api = getRuntimeProvider();` declared once per component/hook and then closed over inside a `queryFn`. `@tanstack/query/exhaustive-deps` correctly flags this — since `api` isn't part of `queryKey`, the linter can't prove the query result stays valid if `api` ever changed identity. In practice `getRuntimeProvider()` always returns the same module-level singleton, so this was never a real bug, but the fix is also simply *better* than the workaround of stuffing `api` into `queryKey` (which would put a non-serializable object into the cache key): call `getRuntimeProvider()` directly inside each flagged `queryFn`/`mutationFn` instead of closing over an outer variable. Applied in `CaptureToken.tsx` (1 query) and `Studio.tsx` (4 queries/fetches, including a module-level helper `outfitFromRender` that no longer needs `api` threaded through as a parameter at all). Cleaned up the now-unnecessary `api` entries in two `useCallback` dependency arrays as a result (flagged separately by `react-hooks/exhaustive-deps`).

One more genuine bug alongside these: `@tanstack/query/no-unstable-deps` in `CaptureToken.tsx` — a `useEffect` depended on the whole object returned by `useMutation()`, which isn't referentially stable across renders. Fixed by destructuring the specific stable pieces actually used (`mutate`, `isPending`, `isSuccess`) and depending on those instead.

Verified after: `eslint .`, `tsc --noEmit`, `prettier --check .`, and `vite build` all clean. Also ran `prettier --write .` once more for the new class-sorting plugin's first pass (36 files reformatted — sorting only, no content changes). Added `.env*` to `.prettierignore` after noticing Prettier had touched `.env.example` (harmless — collapsed one blank line — but env files shouldn't go through a code formatter at all).

---

## Tailwind canonical-class migration, round two — the real cause

A later screenshot showed the same class of issue again (`rounded-[16px]` can be written as `rounded-2xl`, etc.), and this time it was **not** a stale panel. The `@tailwindcss/upgrade` codemod from the first round only rewrites genuine v3→v4 *syntax* changes (`!class`→`class!`, `bg-gradient-to-*`→`bg-linear-to-*`, `[var(--x)]`→`(--x)`, fraction/aspect syntax). It never touches arbitrary-value classes like `rounded-[16px]` or `text-[14px]` that are valid syntax in both v3 and v4 but happen to exactly match a named utility on the default (or this project's custom) scale — that's a *different* check, the Tailwind IntelliSense extension's "suggest canonical classes" lint, and nothing in round one ran that class of fix as a bulk pass.

Pulled the IDE's live diagnostics via `mcp__ide__getDiagnostics` to get exact file/line/suggestion triples instead of reading them off a screenshot. That only covered currently-open editor tabs, though (22 files, missing `pinch-carousel.tsx` entirely and undercounting several others against the Problems-panel screenshot) — so after fixing those 64 confirmed real instances (15 more in the same diagnostics batch turned out to already be fixed — stale cache again, confirmed by grepping for the old bracket syntax and finding zero matches anywhere in `src`), did a second, complete pass: a script scanning every `.tsx`/`.ts` file in `src` for arbitrary-bracket classes and checking each against Tailwind v4's actual scales — spacing (`--spacing: 0.25rem`, so any whole-integer `px` value on a spacing-scale utility converts cleanly), font-size, border-radius (including this project's custom `--radius-field: 10px` / `--radius-card: 18px` theme tokens from `globals.css`), aspect-ratio fractions, opacity, and color-opacity modifiers (`bg-ink/[0.06]`→`bg-ink/6`).

That surfaced 53 more real instances, entirely in files round one never touched — most of the marketing/landing components (`Hero.tsx`, `MirrorCTA.tsx`, `LiveLedger.tsx`, `Closure.tsx`, `RoiCalculator.tsx`, `WaitlistModal.tsx`, `DemoPlaceholder.tsx`, `Header.tsx`) plus a few in `Measurements.tsx`, `button.tsx`, `field.tsx`, `fabric-panel.tsx`, and `quick-access-control.tsx`. One scripting bug caught before applying anything: an early version of the "important-prefix" rule (`!class`→`class!`) matched on `!` generically and was catching TypeScript's non-null-assertion operator and logical NOT (`!account`, `!avatar.trim`) in plain code, not Tailwind classes — restricted to tokens containing a hyphen/bracket with no dot and not followed by `(`, which eliminated every false positive. A second bug: the spacing-scale conversion briefly allowed fractional `px` inputs (`h-[1.5px]` → `h-0.5`, which is wrong — 1.5/4 = 0.375, not a clean quarter-step) — restricted to whole-integer `px` values only, since those always divide cleanly into the quarter-rem scale.

Deliberately left untouched: anything without an exact scale match (odd pixel values like `text-[13px]`, `text-[17px]`, `rounded-[28px]`, `rounded-[15px]`), percentages (`h-[90%]`, `rounded-[50%]`), custom one-off colors and gradients (`bg-[#ebe6dc]`), and complex CSS functions (`clamp()`, `calc()`, `env()`, `min()`) — none of these have a canonical named-class equivalent, so leaving them as arbitrary values is correct, not leftover work.

Verified after: `tsc --noEmit`, `eslint .` clean; `prettier --check .` flagged 2 files for class-order only (raw string replacement doesn't re-sort), fixed with `prettier --write` on those two; `vite build` succeeded. A final re-run of the full-codebase scanner confirmed zero remaining convertible classes.

---

## `cssConflict` warnings — a third, unrelated false-positive class

A follow-up screenshot showed a *different* Tailwind IntelliSense diagnostic code, `cssConflict`, in `measurement-row.tsx`, `pinch-carousel.tsx`, `signature-look-dialog.tsx`, and `RoiCalculator.tsx` (13, 6, 4, and 17 instances respectively — pulled exact messages via `mcp__ide__getDiagnostics` rather than reading them off the panel). Every single one is the same false-positive pattern: the checker flags any two classes that resolve to the same CSS property, without understanding that a variant prefix makes them mutually exclusive or scoped to a different box, so it can't tell "these silently override each other" apart from "these apply under different conditions by design":

- `[&::-moz-range-thumb]:*` vs `[&::-webkit-slider-thumb]:*` (`measurement-row.tsx`, `RoiCalculator.tsx`) — mutually exclusive per-browser-engine pseudo-elements, the standard way to style a native `<input type="range">` thumb across browsers.
- `cursor-grab` vs `active:cursor-grabbing` (`pinch-carousel.tsx`) — base state vs. the `:active` pseudo-class override, the idiomatic grab/grabbing drag-handle pattern.
- `opacity-0` vs `group-focus-visible/*:opacity-100` (`pinch-carousel.tsx`) — intentional show-on-focus/hover pattern for the prev/next arrow buttons.
- `bg-transparent` vs `backdrop:bg-ink/25` (`signature-look-dialog.tsx`) — `backdrop:` targets a native `<dialog>`'s `::backdrop` pseudo-element, a completely different rendered box from the dialog content itself.
- `border-line-strong` vs `focus:border-ink` (`signature-look-dialog.tsx`) — base vs. `:focus` override, standard focus-ring pattern.

None of this is a real bug — every instance is correct, intentional, idiomatic Tailwind. No code changes made. (If the warning noise itself is unwanted, it can be silenced per-project via `"tailwindCSS.lint.cssConflict": "ignore"` in `.vscode/settings.json` — not done here since it's a useful check in general, just noisy for these specific variant patterns.)

While pulling those diagnostics, the same full-workspace call also surfaced 2 genuinely real `suggestCanonicalClasses` leftovers — from the round-two fix above, not from the original port. `max-w-*` turns out to draw from its own dedicated named scale (`max-w-xs` … `max-w-7xl`, matching Tailwind's `--container-*` theme tokens) in addition to the generic numeric spacing scale, and the round-two scanner only checked the generic scale. Two of its own conversions had a more-canonical named equivalent one level up: `max-w-320` (1280px) → `max-w-7xl` in `Hero.tsx`, `LiveLedger.tsx`, and `RoiCalculator.tsx`; `max-w-80` (320px) → `max-w-xs` in `avatar-stage.tsx` (this one wasn't live-flagged yet since the file's diagnostics hadn't refreshed after the earlier edit, but the same exact-pixel-match reasoning applies). Verified after: `tsc --noEmit`, `eslint .`, `prettier --check .`, `vite build` all clean.

Two of the four `cssConflict` sources — the `<input type="range">` cross-browser thumb styling in `measurement-row.tsx` and `RoiCalculator.tsx` — turned out to be genuinely fixable, not just a linter false positive to suppress: extracted the `::-webkit-slider-thumb`/`::-moz-range-thumb` pseudo-element styling out of Tailwind arbitrary variants and into two plain CSS classes in `globals.css` (`.range-thumb`, `.range-thumb-sm`), since the IntelliSense conflict-checker only inspects `className` strings and never touches real CSS. This also shrank both `className`s from a 400+-character chain down to 4–5 utilities. The remaining two files (`pinch-carousel.tsx`'s `cursor-grab`/`active:cursor-grabbing` and `opacity-0`/`group-focus-visible:opacity-100`; `signature-look-dialog.tsx`'s `backdrop:bg-ink/25` and `focus:border-ink`) are single-property state overrides with no equivalent win from extracting to CSS — `"tailwindCSS.lint.cssConflict": "ignore"` in `.vscode/settings.json` stays the right call for those specifically.

Separately: the `editor.defaultFormatter": "esbenp.prettier-vscode"` warning in `.vscode/settings.json` ("Value is not accepted") isn't a config error — VS Code validates that field against currently-*installed* formatter extensions, and Prettier's extension isn't installed on this machine yet (it's listed as a recommendation in `.vscode/extensions.json`, not auto-installed). The setting value is correct and will resolve once the extension is installed.

### One more stale-panel repeat, for the same `max-w-320`/`max-w-7xl` fix

A later screenshot showed `Hero.tsx` and `LiveLedger.tsx` still flagging `max-w-320` → `max-w-7xl`, at the exact lines already fixed above. Re-grepped both files on disk (`max-w-320` returns zero matches anywhere in `src/`; both lines already read `max-w-7xl`) and re-pulled live `mcp__ide__getDiagnostics` for `Hero.tsx`, which still reported the old message — confirming this is the editor's diagnostic cache, not the file content. Root cause: these particular edits were made by an external script (not through the editor), and Tailwind IntelliSense doesn't always invalidate its own diagnostics when a file changes outside VS Code's edit pipeline. No code change was possible or needed — nothing to fix. Clears with **Ctrl+Shift+P → "Reload Window"** (or, more surgically, **"Developer: Restart Extension Host"**).
