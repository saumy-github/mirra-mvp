# Website Pilot v1 — Scope

*Last updated: 2026-07-18*

## Goal

This is a **pilot**, not a polished product launch. The purpose is to learn:
- How much concurrent load the system (CLO-backed pipelines) can actually handle
- What users want / how they behave in the flow
- Where the system breaks

Not a goal yet: full production scale, full garment catalog, mobile support, facial realism.

## Core Flow

| # | Step | Maps to existing pipeline | Notes |
|---|------|---------------------------|-------|
| 1 | Sign in | — (new) | Auth + accounts, nothing exists yet |
| 2 | Submit measurements + face photo | Step 1 input fields (`.claude/context/MVP-step-1.md`) | Face photo is handed off to a separate, in-progress workstream — not built here |
| 3 | Generate personal avatar | Step 1 (`clo_avatar_generation/`) | Known slow step (~30-60s, worse on edge cases). Needs async job handling + a real "generating..." UX, not a blocking wait |
| 4 | Load avatar | Step 1 output (`.avt`) | `.avt` is not browser-renderable — needs export to glTF/GLB + a web 3D viewer |
| 5 | Choose clothes from preset catalog | Step 2 output (DXF + edge manifest) / "Inventory" concept (`.claude/project-context.md`) | Optional: preload/precompute Step 2 outputs ahead of time so browsing is instant instead of generated on demand |
| 6 | Show final try-on result | Step 3 (VTO) output | Same web-viewer problem as step 4. VTO is the slowest/least reliable step today (up to 5 min, known timeout issues on complex seams — see `.claude/current-roadmap.md`) |
| 7 | (Optional) Paste a link to any website → extract & generate the garment | Step 2 (`product_ingestion/`), triggered live instead of via admin upload | **Optional/stretch.** Needs a web scraper + on-demand ingestion trigger |

## Phase 1 — Frontend Tech Stack & Port

**Goal**: Decide the frontend tech stack, then port the existing landing page + other pages (currently built in Next.js by a teammate) onto it — preserving structure/content/design as-is — so that teammate can keep iterating on design and content without being blocked by the stack change.

**Explicitly out of scope for Phase 1**: avatar loading, cloth catalog/display, and any pipeline integration (steps 1-7 above). That work belongs to a separate team/phase and is not blocked by Phase 1.

**Division of labor**:
- This phase: decide the stack, then port/rebuild the existing pages 1:1 on it.
- Teammate (frontend/design): free to make any design and content changes on top of the ported frontend once Phase 1 lands.
- Other team: backend pipeline integration (avatar generation, cloth catalog, VTO display) — separate workstream.

**Structure plans** (both build on the tech stack decision and the port audit below):
- [Frontend Structure Plan](frontend-structure-plan.md) — directory layout, routing/code-splitting, toast notifications, component-granularity rule
- [Backend Structure Plan](backend-structure-plan.md) — service-based architecture (`src/services/<domain>/{routes,controller,service,models}.py`), service list, shared infra, CLO3D seam (not implemented)

**Tech stack decision**: see [Tech Stack Decision](#tech-stack-decision) below.

**Scope confirmed**: standalone site (not the Shopify-embedded/multi-tenant SaaS model). Your friend's `user-side` repo was built to serve both; `website/port-audit-user-side.md` breaks down exactly what's reusable as-is, what needs rework, and what's SaaS-specific and gets dropped.

## Tech Stack Decision

### Rendering Architecture: CSR (SPA)

**Why:**
- The app is mostly logged-in/personalized (measurements, avatar, catalog, try-on results) — SSR/SSG doesn't help pages like this.
- Avatar rendering — the core feature — is WebGL, which runs client-side regardless of architecture. SSR gains nothing on the single most important page in the app; it can render a `<canvas>` tag, not what's drawn inside it.
- No Node server to run/maintain — clean separation from the Python backend, and avoids reintroducing the frontend/backend coupling that ruled out Next.js in the first place.
- **Trade-off accepted**: marketing/landing pages lose SSR/SSG's SEO benefit for now. Acceptable for a pilot focused on load-testing and user feedback, not organic acquisition. Revisit later with a small dedicated static marketing microsite if SEO becomes a priority — not a rewrite of the app.

**What most companies actually do**: hybrid — SSR/SSG for public marketing pages, CSR for the logged-in product (Airbnb, Notion, Figma, and Vercel all split this way). Pure CSR everywhere, including marketing pages, is the standard pattern for internal tools, dashboards, and early-stage/pilot products where SEO isn't the priority yet — which is where this pilot sits. Pure CSR SPAs are also how Gmail, Google Docs/Sheets, Figma's editor, Linear, Notion's workspace, and Discord's web app all work once you're logged in.

**Alternatives considered and rejected:**
- **Next.js / Remix (SSR meta-frameworks)** — requires running/maintaining a Node server for a benefit (SSR) the core avatar page can't use anyway; also reintroduces the frontend/backend coupling being moved away from.
- **Astro (islands)** — good for content-heavy static pages, poor fit for a highly interactive/3D app. Could work later as a separate marketing microsite only.
- **Vue/Svelte instead of React** — no reason to switch. Porting from an existing React/Next.js frontend (less migration friction), and React has by far the best 3D ecosystem via React Three Fiber.

### Frontend Stack

| Layer | Choice | Why |
|---|---|---|
| Build tool | Vite | Fast dev server, static build output, no Node server needed — pairs naturally with CSR |
| Framework | React + TypeScript (TSX) | Matches the existing Next.js frontend structure (less migration friction); best 3D ecosystem via React Three Fiber |
| Styling | Tailwind CSS | Already used in both of the friend's repos (v4) — no conversion needed on port |
| Routing | React Router | Standard pairing with Vite + React CSR |
| 3D rendering | React Three Fiber + drei (built on Three.js) | React-idiomatic scene graph — avatar/garment state lives in React state, not manual imperative scene mutation. `drei` provides GLTF/GLB loaders, orbit controls (for the 360° rotation spec), and a `useProgress` hook for asset-load progress. Chosen over raw Three.js (more boilerplate for no real gain here) and Google's `<model-viewer>` (too limited once garments need to be layered on the avatar rather than displaying one static model) |
| Data fetching / async jobs | TanStack Query | Built-in polling/refetch/caching — needed for avatar-gen and VTO jobs, which take real time to complete ("time issues" from the core flow) |
| Asset format | glTF/GLB | Web-renderable 3D format. The current pipeline only produces `.avt`/CLO-native formats — an export step needs to be added for steps 4 and 6 |

### Backend Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **FastAPI** | Async-native — this backend's job is mostly I/O-bound orchestration (CLO worker services, MongoDB, waiting on long jobs), not CPU work. Pydantic-native, matching the existing repo convention (`repo-rules.md`). Auto-generates an OpenAPI schema, which can generate TS types for the frontend automatically, keeping the API contract in sync across languages |
| Rejected: Flask | Sync by default; no schema/validation story as clean as FastAPI's for this use case |
| Rejected: Django | Batteries (auth, admin, ORM) are tempting for "basic user management," but the ORM is relational-first — MongoDB support is a bolt-on (Djongo/MongoEngine, both awkward). Mongo is already the established store across the whole pipeline |
| Database | MongoDB, via **PyMongo's native async API** (`AsyncMongoClient`, 4.9+) — not Motor, not an ODM | Consistent with the rest of the pipeline, which already uses `pymongo` (per `architecture.md`, `repo-rules.md`) — same library, async variant, not a second driver. Motor is being phased out in favor of async support built directly into PyMongo, so adopting it now would mean migrating again soon. No ODM (e.g. Beanie) needed — FastAPI + Pydantic already handle validation, and Beanie is built on Motor anyway. Must be async: a sync driver call inside an async FastAPI handler blocks the event loop for every other in-flight request, which would corrupt the pilot's own load-test results |

### CLO 3D Integration: Worker Microservices

Extends the existing `clo_workspace/` REST plugin bridge pattern rather than replacing it. Each dedicated CLO worker machine runs: CLO 3D + the existing REST plugin (`localhost:50505`) + a thin service wrapping the existing `avatar_runtime`/`native_vto` pipelines, consuming jobs from a queue instead of being invoked as a CLI script.

The main FastAPI backend never talks to CLO directly — it enqueues avatar-gen/VTO jobs and polls/receives results, the same pattern TanStack Query needs on the frontend anyway.

**Still open**: which queue technology (Redis+RQ, Celery, or arq) — deferred until the FastAPI ↔ CLO-service boundary is scoped in detail.

### Performance & Loading Strategy

CSR has two real failure modes if left unhandled — both solvable:

**Problem 1 — loading everything at once**: without code splitting, Vite ships one bundle containing the entire app, including the heavy 3D stack (Three.js/R3F/drei), even for users who only ever hit the login page.

**Problem 2 — blank screen on lazy load**: naive `React.lazy()`/dynamic `import()` without a fallback UI causes a white flash while the browser fetches an uncached route's JS chunk.

**Mitigations:**
- **Route-based code splitting** with `Suspense`, using **skeleton screens** (shaped like the destination page) as fallbacks instead of blank/spinner — makes navigation feel instant even when a chunk is still loading.
- **Split the 3D engine into its own chunk**, loaded only on routes that need it (avatar viewer, try-on result) — auth, catalog browsing, and profile pages never pay that cost.
- **Prefetch on hover/intent** (React Router supports this) — e.g., start prefetching the avatar-viewer chunk the moment login succeeds, since it's the near-certain next screen, so the chunk is already cached by the time the user navigates.
- **Separate JS-chunk loading from 3D-asset loading**: use `drei`'s `useProgress` hook to show a real progress bar while the GLB model/textures stream in — a different bottleneck than the JS bundle, and one that overlaps with the already-known wait-time problem around avatar/VTO generation, so it should reuse the same progress-communicating UX pattern.
- **App-shell pattern**: keep nav/layout chrome permanently mounted; only the content area shows loading state, so a slow route never blanks the whole screen.
- **Vite's content-hashed build output** + CDN cache headers mean this cost is paid once per chunk per user — repeat visits load from cache.

## Guest Mode

Users who don't want to give personal details can skip steps 1-3 entirely and use a shared, pre-generated **guest avatar** instead. This reuses the existing "generate once, store, reuse" pattern already built into Step 1, just applied to a generic body instead of real measurements.

## Key Open Questions / Dependencies

1. **CLO 3D scaling** — Steps 3 and 7 both route through CLO 3D, which is a licensed desktop app requiring a locally-running instance + REST plugin (`localhost:50505`). Since the whole point of this pilot is measuring load capacity, this determines the actual concurrent-user ceiling. Needs a real answer (e.g., how many licensed worker machines are available) before frontend work goes far.
2. **Wait-time UX** — Steps 3 and 7 have real, sometimes multi-minute wait times. Needs explicit design (queue position, notify-when-ready, spinner + expectations), not an afterthought.
3. **Face photo hand-off** — format/storage location for the face photo, and what the (separate, in-progress) facial-avatar workstream expects to consume, is still unresolved.
4. **Web-viewable export format** — nothing in the current pipeline produces a browser-renderable format (glTF/GLB or similar); this needs to be added for steps 4 and 7.

## Out of Scope for This Website (for now)

- Facial/appearance realism — separate workstream, in progress
- Mobile optimization
- Full production-scale catalog
- Live/camera-based try-on
