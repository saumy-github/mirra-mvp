# 18 - Homepage (`/`) lazy loading audit

**Status:** findings only — no code changed
**Created:** 2026-08-08

## Goal

Answer: is the marketing homepage (`/`, `pages/Home.tsx`) slow on first load because of too much content and no lazy loading? Confirmed **yes**, with evidence from the actual production build (`npm run build`), not assumptions.

## Summary

The page is lazy at the **route** level (`Home` is already `React.lazy`-loaded in `router.tsx`, same as every other route) — that part is already correct. The problem is entirely **inside** the page: every section, every image, and every heavy animation/shader library loads immediately on mount, with nothing deferred by scroll position or viewport visibility.

## Findings

### 1. All 7 sections are one eager bundle, not split

`pages/Home.tsx` directly imports and renders all of:
`Hero`, `ProblemTeardown`, `ProductReveal`, `LiveLedger`, `DemoPlaceholder`, `RoiCalculator`, `Closure` — no per-section `React.lazy`/dynamic import anywhere. Rollup therefore bundles all 7 into a single chunk:

```text
Home-*.js    99.40 kB  (30.24 kB gzip)
Home-*.css   39.47 kB  ( 8.44 kB gzip)
```

This includes sections far below the fold (`RoiCalculator`, `Closure`) that a visitor may never scroll to, loaded with the same priority as the Hero.

### 2. Remote images load eagerly, no `loading="lazy"`

- `features/marketing/components/ProductReveal.tsx` (`gapFrames` array, top of file) — 5 full-size Unsplash photos (`images.unsplash.com/...?w=900&q=85`) rendered as plain `<img src>` inside a scroll-driven GSAP section well below the Hero. No `loading="lazy"`, no explicit `width`/`height` (layout-shift risk).
- `features/marketing/components/Closure.tsx` (`teamTeaserImages` array) — more Unsplash images, same pattern, same lack of lazy attribute.

Each is a separate network round-trip to a third-party CDN, fired immediately regardless of scroll position.

### 3. Heavy libraries run unconditionally on page load

- **GSAP** core + `ScrollTrigger` + `SplitText` + `CustomEase` — used in both `ProblemTeardown.tsx` and `ProductReveal.tsx`, doing character-level DOM-splitting animation setup on mount, not gated by visibility.
- **Lenis** (smooth-scroll) — instantiated once per marketing page load in `features/marketing/marketing-layout.tsx`'s `useSmoothScroll()`, unconditionally, for every marketing route (`/`, `/pricing`, `/meet-the-team`), not just ones that need scroll-driven effects.
- **A WebGL shader** — `features/marketing/components/LiquidMetal.tsx` uses `@paper-design/shaders`' `ShaderMount` + a custom liquid-metal fragment shader, mounted inside the small "Early Access" pill in `Hero.tsx` — the very first thing rendered, above the fold. A GPU shader compiling/rendering for a badge-sized decoration.

### 4. A large shared icon chunk rides along too

```text
rotate-ccw-*.js   115.80 kB  (45.84 kB gzip)
```

This is a Rollup-merged chunk of `lucide-react` icons shared across multiple routes (named after whichever icon happened to anchor it). Home's own components alone import 8 distinct icons (`Zap`, `ArrowRight` in `Hero.tsx`; `RotateCcw`, `Box`, `CheckCircle2`, `AlertOctagon`, `ArrowRight` in `LiveLedger.tsx`; `Play` in `DemoPlaceholder.tsx`; `ChevronDown` in `RoiCalculator.tsx`), which is enough to pull this entire shared chunk into `/`'s critical path.

## Rough cost of a cold first visit to `/`

| Chunk | gzip |
|---|---|
| Shared vendor (`index-*.js`, every page) | 137.10 kB |
| Global CSS (`index-*.css`) | 18.14 kB |
| `marketing-layout-*.js` (incl. GSAP + Lenis) | 12.86 kB |
| `Home-*.js` | 30.24 kB |
| `Home-*.css` | 8.44 kB |
| Shared icon chunk (`rotate-ccw-*.js`) | 45.84 kB |
| **Total** | **~252 kB gzip** |

...plus 5+ uncontrolled external image fetches (Unsplash), not counted above since they're not part of the JS/CSS bundle.

Not catastrophic by modern web standards, but every piece of it is currently avoidable-on-first-paint content — none of it is deferred.

## Possible fixes (not implemented, for a future pass)

Roughly in order of impact vs. effort:

1. **Lazy-load below-the-fold sections** of `Home.tsx` individually (`React.lazy` + `Suspense` per section, or an intersection-observer-gated mount) — `RoiCalculator` and `Closure` are the easiest, lowest-risk candidates since they're purely bottom-of-page.
2. **Add `loading="lazy"` to every `<img>`** in `ProductReveal.tsx` and `Closure.tsx`, plus explicit `width`/`height` to avoid layout shift. Cheapest fix here, near-zero risk.
3. **Gate the `LiquidMetal` shader mount behind visibility** (or drop it — it's a small decorative badge, arguably not worth a WebGL context on every page load) rather than mounting unconditionally in `Hero.tsx`.
4. **Scope Lenis to pages that actually use scroll-driven GSAP effects**, instead of every marketing route via the shared `MarketingLayout`, if `/pricing`/`/meet-the-team` don't need it.
5. **Investigate the `rotate-ccw` shared chunk** — confirm whether it's genuinely a cross-route shared-icon chunk (expected Rollup behavior, lower priority) or an accidental barrel-import pulling in more of `lucide-react` than needed (worth a `manualChunks`/import-cost check either way).

## Execution Log

Not started — audit only, per this round's request ("check and tell, no code change").
