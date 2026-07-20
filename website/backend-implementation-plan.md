# Backend Implementation Plan

*Last updated: 2026-07-20*

Sequential build order for [Backend Structure Plan](backend-structure-plan.md). That doc defines the architecture (folder layout, service responsibilities); this doc sequences the actual work — what gets built first, what depends on what, and what "done" means at each step.

**Status (2026-07-20): all phases (1–9) are implemented.** The backend lives in `website/backend/`, verified end-to-end against the real `mirratest` database (per-phase check scripts + `scripts/smoke_e2e.py`). Phase 9's live provider (`client.ts` + `http-runtime-provider.ts` + `live-schemas.ts` + `auth-token.ts` in `website/frontend/src/integrations/mirra-api/`) was verified by running the actual provider code through the full pilot flow against the running backend (25/25 checks). **Local dev still defaults to mock** (`VITE_INTEGRATION_MODE=mock` in `.env.development`) — flip to `live` (plus `VITE_AUTH_PROVIDER=live`) with the backend running to use the real stack. Engine modes are demo-only until the CLO3D worker/queue decision lands (Phase 0, item 3). Known live-mode placeholders: no product imagery/pricing (Step 2 output carries none yet), no rendered try-on imagery (demo engine), and capture uploads a placeholder pixel until the camera UI forwards real photo bytes (`CapturedImage.blob`).

References used while sequencing this:
- The cloned `user-side` repo (`C:\D-drive-data\user-side`) — its `docs/openapi.yaml`, `docs/backend-contract.md`, and `docs/going-live.md` describe a tenant/Shopify-shaped backend contract that doesn't apply directly, but the endpoint shapes and the demo/live engine-mode pattern (see Phase 4) are worth carrying over. Its `src/server/mock/` is a fully in-memory, dev-only fake (not a real backend) — useful purely as a behavioral spec of the same contract.
- The existing `mirra_measurements/` module (repo root) — the CLO pipeline's own measurement/size data layer, already live and already read/written by `clo_avatar_generation` (Step 1) and `product_ingestion` (Step 2). Phase 3 and Phase 5 build on its model structure directly instead of designing those services from zero — see Phase 0, item 4 for how the old folder itself eventually gets retired.

---

## Phase 0 — Decisions to lock before scaffolding

1. **Session mechanism** (`core/security.py`): **short-lived access JWT + long-lived refresh token**, the access/refresh pattern already used in your other project's auth flow, and the pattern most production SaaS backends actually run in practice.
   - **Access token**: JWT, ~15 minute expiry, verified by signature only — no DB hit on the hot path. Kept in frontend memory only (never `localStorage`, never a cookie), attached via `Authorization: Bearer` on API requests. Short lifetime bounds the exposure window if it ever leaks.
   - **Refresh token**: opaque random token, 30-day expiry, set as an httpOnly + Secure + SameSite cookie, sent only to `/auth/refresh`. Stored server-side, hashed, in a Mongo `refresh_tokens` collection — this is what actually delivers "don't make me log in again," not the access token. Storing it server-side means logout / account deletion / "log out everywhere" revoke it instantly (delete or flag the row), which a pure stateless JWT can't do.
   - **Rotation**: each `/auth/refresh` call issues a new refresh token and invalidates the one it replaces (rotation family). A replayed, already-rotated refresh token is a theft signal — revoke the whole family when that happens. Small addition on top of the collection above, worth building from day one rather than retrofitting.
   - **On page load**: frontend calls `/auth/refresh` (httpOnly cookie sent automatically) to mint a fresh access token into memory — mirrors the restore-on-load flow in your other project's `AuthContext`.
   - **Guest sessions**: same shape — short-lived guest access token + refresh cookie — one code path for both authenticated and guest.
   - See chat reply for the alternative methods considered (plain long-lived JWT, server-side session only, managed auth provider) and why this one won.

2. **Capture-photo storage**: local disk under a gitignored `uploads/` dir for the pilot, served through an authenticated route. **Photos are retained, not deleted after avatar generation** — this reverses the cloned repo's "delete after generation" invariant; we need the data to keep improving avatar-generation accuracy. This is a deliberate divergence from `user-side`'s `backend-contract.md` invariant (which also says captured photos are "never used for training"); `backend-structure-plan.md`'s own invariants section has been updated to match (see that file).

3. **CLO3D queue tech** (Redis+RQ / Celery / arq): explicitly deferred, not decided now. Current build priority is the standard parts almost every website needs — auth, users, sessions, measurements, catalog browsing — not the CLO-specific compute path yet. `avatars`/`tryon` stay on their demo-mode stub until this gets picked.

4. **`mirra_measurements/` is a model to copy from, not a dependency to keep.** New files/folders get created under the backend (`src/measurements/`, `src/catalog/` — domain folders sit directly under `src/`, no `services/` wrapper) mirroring `mirra_measurements`'s structure — ported and rewritten, not imported from the old package at runtime. Concretely:
   - **Same database, still true**: backend `config.py`/`db.py` point at the same `mirratest` Mongo database `mirra_measurements/db.py` already uses. The data itself (the `measurements`/`sizes` collections) lives in MongoDB, independent of whatever Python folder reads/writes it.
   - **Sync → async port**: `mirra_measurements/db.py` uses `pymongo.MongoClient`; backend `db.py` uses `AsyncMongoClient`. Collection accessors and index creation get re-written async.
   - **Validation logic ports, doesn't get re-invented**: `avatar_model.py`'s `create_measurement_doc`/`validate_measurement_doc` and `size_model.py`'s equivalent become `src/measurements/models.py` and `src/catalog/models.py`, reconciled against `schema/step1_field_contract.json` where they overlap.
   - **`user_id` becomes a real account id** once `auth`/`users` exist (Phase 2); `golden_users.py` + seed scripts get copied into the backend as dev/test fixtures.
   - **The old `mirra_measurements/` folder itself is not deleted by any phase in this plan.** It stays on disk, unused by the backend once the port lands, until the backend is fully built and tested — at which point you delete it yourself, manually. Nothing here is blocked on that deletion happening.

---

## Phase 1 — Shared infra skeleton

Everything else depends on this existing first.

- `src/main.py` — FastAPI app instance, CORS (frontend dev origin), router mounting (empty at first), exception handlers wired to `core/errors.py`
- `src/config.py` — pydantic-settings: Mongo URI, access-token signing secret + ~15 min expiry, refresh-token expiry (30 days), CORS origins
- `src/db.py` — single `AsyncMongoClient`, pointed at the existing `mirratest` database (Phase 0, item 4) — not a fresh database
- `core/errors.py` — shared exception types + handlers, matching the typed error shape from the cloned repo's `openapi.yaml` (`{error: {code, message}}`)
- `core/security.py` — password hashing; access-token issuing/verification; refresh-token issuing, rotation, and revocation against the `refresh_tokens` collection (per Phase 0, item 1)
- `core/auth_dependency.py` — stub only at this point (real body comes in Phase 2)

**Done when**: app boots, connects to the `mirratest` Mongo database, a health endpoint responds, CORS allows the Vite dev server.

---

## Phase 2 — `auth` service

Unblocks every other service, since all of them need "current user" resolution.

- Endpoints: sign-up, login, logout, `/auth/refresh`, `/auth/me`, verify-email, password-reset, **guest session creation** (guest is an auth concern per the structure plan, not a separate domain)
- Finish `core/auth_dependency.py` for real — resolves the current user (or guest) from the short-lived access token's `Bearer` header, signature-only, no DB hit. Refresh-token rotation/revocation lives in the auth service itself, not this dependency.
- Google OAuth: skip for pilot v1 (cloned repo notes this is blocked on credentials anyway) — email/password + guest only

**Done when**: sign-up → login → `/auth/me` → logout works end-to-end via a manual client; a simulated browser restart calls `/auth/refresh` (cookie only, no stored access token) and gets a fresh access token without re-entering credentials, up to the refresh token's 30-day life; logout and account deletion revoke the stored refresh token immediately; guest sessions resolve through the same dependency.

---

## Phase 3 — `users` + `measurements` services

- `users`: profile CRUD, consent/privacy patch, account deletion — stub the cascade calls now (profile/avatars/tryon/looks/capture-sessions), even though most of those collections don't exist until later phases, so the cascade contract exists from day one instead of being bolted on. Deletion must also revoke that user's `refresh_tokens` rows (their in-memory access token simply expires within its short window regardless).
- `measurements`: port `mirra_measurements/avatar_model.py` + the measurements half of `db.py` into `src/measurements/`, async. Validation = the existing `REQUIRED_FIELDS`/`NUMERIC_FIELDS`/`STRING_FIELDS` sets, reconciled against `schema/step1_field_contract.json` where they overlap. New docs key on the real account id (Phase 0, item 4) instead of `golden_users.py` fixture ids; the golden fixtures + seed scripts get relocated in as dev-only seed data.

**Done when**: a logged-in user can submit measurements and read them back; deleting the account removes the user + measurement docs and revokes their refresh tokens immediately; the relocated `seed_measurements.py` still seeds the golden users for local dev without breaking `clo_avatar_generation`'s existing read path against the same collection.

---

## Phase 4 — `avatars` service

Moved up — no longer waits on `capture` (see Phase 8).

- Endpoints: start generation, get status (staged states, not %), get profile, delete
- "Start generation" takes a stored measurement doc (Phase 3) directly — it has no dependency on a capture/photo session existing. This is exactly why `capture` can move to the end: `avatars` is fully testable against Phase 3's measurement data, including the `golden_users` fixtures, with zero photo-capture flow in the loop.
- Build to the CLO3D hand-off **interface only** — adopt the cloned repo's demo/live engine-mode pattern (`AVATAR_ENGINE_MODE=demo|live`): a demo mode fakes a staged job (queued → processing → ready) with no real CLO3D call, so the frontend can integrate against real endpoints before the worker/queue exists. In live mode, the hand-off is to the same `clo_avatar_generation/avatar_runtime` pipeline that already reads this measurements collection — this phase stubs the call, not a new integration.

**Done when**: given a stored measurement doc (including a `golden_users` fixture), a demo-mode job runs queued → processing → ready and the profile is retrievable — with no capture session ever having existed.

---

## Phase 5 — `catalog` service

Moved up. Reuses existing data instead of a fresh design.

- Browse/search preset garments, surfacing Step 2 (`product_ingestion/`) output
- Reads the existing `sizes` collection in `mirratest` — already populated by `mirra_measurements/seed_sizes.py` and written by the Step 2 pipeline. `catalog/models.py` ports `size_model.py`'s flat schema (`fit_type` + the 10 measurement fields + `cloth_id`/`cloth_label`/`category`) rather than inventing a new one.

**Done when**: garments produced by the existing Step 2 pipeline are listable/searchable through this service, reading the same `sizes` collection `mirra_measurements` already defines.

---

## Phase 6 — `tryon` service

- Open session, request render, poll/restore render (the Hanger no-recompute path)
- Same demo/live engine-mode pattern as `avatars`
- **Drop** the cart-handoff endpoint entirely — pilot cart is local-only per the frontend port (no real checkout backend)

**Done when**: given an avatar + a catalog item, a demo-mode render request returns a staged result; restoring a cached render doesn't recompute.

---

## Phase 7 — `signature_looks` + `analytics`

- `signature_looks`: CRUD, lowest-priority/nice-to-have, straightforward port of the concept
- `analytics`: event ingest matching the vocabulary already kept in `lib/analytics.ts` on the frontend — do this properly, not as an afterthought, since the pilot's real goal is learning user behavior

**Done when**: every event type the frontend already emits has somewhere real to land.

---

## Phase 8 — `capture` service

Moved to last, per explicit reorder — everything upstream of it (`avatars`, `catalog`, `tryon`) is buildable and testable against stored/seeded measurements alone, so the QR photo-pairing UX is the one piece that can wait.

- QR session create/poll/cancel/resolve-code, token-scoped pair/consent/upload/complete
- Wires to the Phase 0 storage decision for the photo itself — **photos are retained after avatar generation, not deleted** (Phase 0, item 2), so they can feed future avatar-accuracy improvements
- No forward-dependency stub needed: by this phase `avatars`' job-creation call already exists for real (Phase 4) — `complete` calls it directly, nothing to go back and wire up afterward.

**Done when**: a capture session can be created, paired, photo uploaded, and marked complete; completion enqueues a real (already-built) avatar job; the photo remains retrievable through the authenticated `uploads/` route after generation completes, not just during the capture flow.

---

## Phase 9 — Frontend swap-over

- Build `integrations/mirra-api/public-runtime-provider.ts` in `website/frontend` against these real endpoints (the seam already exists — `mock-runtime-provider.ts` is what it replaces, per `frontend-structure-plan.md`). It needs to hold the access token in memory (not `localStorage`), attach it via an `Authorization` header on every call, and call `/auth/refresh` once on app load — mirroring the pattern in Phase 0/2 and your other project's `AuthContext`.
- Flip local dev from mock provider to the real backend service-by-service (auth first, then measurements, then avatars/catalog/tryon, then capture last — mirroring build order) rather than all-at-once, so breakage is attributable
- **Do not delete `mock-runtime-provider.ts`, mock fixtures, or any other now-unnecessary mock data during this service-by-service flip.** That cleanup is explicitly deferred — see "Deferred Manual Cleanup" below.

**Done when**: the full pilot flow (sign-up/guest → measurements → capture → demo-mode avatar → catalog → demo-mode try-on) runs against the real FastAPI backend with zero mock fallback.

---

## Deferred Manual Cleanup

Two removals that are intentionally *not* part of any phase above — both happen only after the backend is fully built and tested, and both are done by you, manually, not as an automated step of this plan:

1. **Delete the `mirra_measurements/` folder** — only after the backend (through Phase 8) is built and tested. Until then it stays as the reference the new async services were ported from (Phase 0, item 4).
2. **Remove unnecessary files and mock data from `website/frontend`** (e.g. `mock-runtime-provider.ts`, mock fixtures) — only after the backend is fully built and tested, not incrementally as each service gets swapped over in Phase 9.

---

## Explicitly Not Covered by This Plan

- CLO3D worker microservice + queue technology (Phase 0, item 3) — separate, tracked decision
- Garment web-scraping / on-demand ingestion (optional pilot step 7) — deferred, per `backend-structure-plan.md`
