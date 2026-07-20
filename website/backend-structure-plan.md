# Backend Structure Plan

*Last updated: 2026-07-20*

Builds on [Tech Stack Decision](website_pilot_v1_scope.md#tech-stack-decision): FastAPI (async), MongoDB via PyMongo's native async API. **Scope: frontend-facing backend only — the CLO3D worker microservice is explicitly out of scope for this plan** (tracked separately). The `avatars` and `tryon` services below expose the seam that will eventually call it, but that queue/worker design isn't decided here.

## Principles

- **Service-based architecture**: one folder per domain directly under `src/`, not one folder per technical layer. Everything about "users" lives in `src/users/`, not scattered across a global `routes/`, `controllers/`, `models/`. No `services/` wrapper folder — flat domain packages under `src/` is the dominant convention for domain-structured FastAPI monoliths (Netflix Dispatch, the fastapi-best-practices reference layout, Django's apps-at-root); the infra/domain split stays visible because all cross-cutting infra is contained in `core/` plus the three root files.
- **Three files per service**, matching what you asked for:
  - `routes.py` — FastAPI `APIRouter`: path/method definitions, request dependency wiring (auth, validation), delegates immediately to `controller.py`. No business logic.
  - `controller.py` — translates between HTTP and the domain: unpacks the request, calls `service.py`, shapes the HTTP response, maps domain errors to HTTP status codes.
  - `service.py` — the actual business logic. No FastAPI/HTTP imports, so it's directly unit-testable and directly reusable if something needs to call it outside an HTTP request later.
  - `models.py` — Pydantic schemas (request/response) and the Mongo document shape for this domain.
- **No repository layer imposed up front.** DB access lives inside `service.py` for now — introducing a separate `repository.py` per service is a fine future split if a service's data-access logic grows complex, but not worth adding for every service on day one at pilot scale.

## Directory Tree

```
backend/
├── .env.example               # deps are NOT here — they live in the repo-root requirements.txt, installed into the repo-root .venv/
├── README.md                  # setup + run (`fastapi dev src/main.py`) + smoke-test instructions
├── scripts/                   # dev-only: seed_measurements.py, seed_sizes.py, golden_users.py, smoke_e2e.py
└── src/
    ├── main.py                    # FastAPI app instance, mounts all service routers
    ├── config.py                  # pydantic-settings — all env config in one place
    ├── db.py                      # AsyncMongoClient setup, shared across services
    │
    ├── core/                      # cross-cutting infra, not a domain
    │   ├── security.py            # password hashing, access/refresh JWT issuing, rotation & verification
    │   ├── auth_dependency.py     # FastAPI dependency for "current user" / guest session
    │   └── errors.py              # shared exception types + handlers
    │
    ├── auth/
    │   ├── routes.py              # /auth/sign-up, /login, /logout, /auth/refresh, /auth/me, /verify-email, /password-reset, guest session
    │   ├── controller.py
    │   ├── service.py
    │   └── models.py
    ├── users/
    │   ├── routes.py              # /users/me, account deletion, privacy settings
    │   ├── controller.py
    │   ├── service.py
    │   └── models.py
    ├── measurements/
    │   ├── routes.py              # submit/update measurements
    │   ├── controller.py
    │   ├── service.py
    │   └── models.py
    ├── capture/
    │   ├── routes.py              # QR capture session create/status, token-scoped photo upload
    │   ├── controller.py
    │   ├── service.py
    │   └── models.py
    ├── avatars/
    │   ├── routes.py              # start generation, get status, get profile, delete
    │   ├── controller.py
    │   ├── service.py             # enqueues to CLO3D worker (interface only, not implemented here)
    │   └── models.py
    ├── catalog/
    │   ├── routes.py              # browse/search preset garments (Step 2 output, surfaced)
    │   ├── controller.py
    │   ├── service.py
    │   └── models.py
    ├── tryon/
    │   ├── routes.py              # request try-on, get status/result, restore cached result
    │   ├── controller.py
    │   ├── service.py             # enqueues to CLO3D worker (interface only, not implemented here)
    │   └── models.py
    ├── signature_looks/
    │   ├── routes.py              # CRUD for saved outfit combos
    │   ├── controller.py
    │   ├── service.py
    │   └── models.py
    └── analytics/
        ├── routes.py              # event ingest — matches the event vocabulary kept in the frontend audit
        ├── controller.py
        ├── service.py
        └── models.py
```

## Service Responsibilities

| Service | Responsibility | Notes |
|---|---|---|
| `auth` | Sign-up, login, email verification, password reset, session issuing. Also owns **guest session creation** — a guest is an auth concern (an unauthenticated-but-tracked session), not a separate domain. | Session mechanism = short-lived access JWT + 30-day rotating refresh token, not a plain session cookie — see `backend-implementation-plan.md` Phase 0 item 1. |
| `users` | Profile CRUD, privacy settings, account deletion (must cascade — see invariant below). | |
| `measurements` | Store/update body measurements, field validation ranges. | Ports the existing `mirra_measurements/avatar_model.py` validation logic (already in production use by the CLO pipeline), reconciled against the Step 1 field contract (`schema/step1_field_contract.json`) — see `backend-implementation-plan.md` Phase 0 item 4. |
| `capture` | QR-based photo capture session lifecycle: create session, pair, upload, complete, expire. | Photos are retained after avatar generation — see invariant below. |
| `avatars` | Avatar generation job lifecycle (queued → ready), avatar profile storage. | **This is the CLO3D seam.** `service.py` here is where a job gets hand off to the (not-yet-designed) CLO worker queue. Build the interface, not the implementation. |
| `catalog` | Garment browsing — the "choose clothes from preset" step. Surfaces Step 2 (`product_ingestion/`) output to the frontend. | Reads the existing `sizes` collection already populated by `mirra_measurements`/Step 2, rather than a fresh schema — see `backend-implementation-plan.md` Phase 5. |
| `tryon` | VTO request lifecycle, cached result restore ("Hanger" no-recompute path). | Same CLO3D-seam caveat as `avatars`. |
| `signature_looks` | Save/list/delete a full outfit combination. | Directly ported concept from `user-side`. |
| `analytics` | Ingest frontend events. | Given this pilot's actual goal is learning user behavior and load, this service matters more than it would in a normal MVP — don't treat it as an afterthought. |

Deliberately **not** a service yet: garment-from-URL extraction (optional step 7, per the port audit) — would live in `catalog` or its own `ingestion` service later, not designed now.

## Shared Infra

- **`db.py`**: single `AsyncMongoClient` instance, imported by any service's `service.py` that needs it. Async end-to-end — a sync driver call here would block the event loop for every other in-flight request, which matters given this pilot's whole point is measuring real concurrency.
- **`config.py`**: pydantic-settings, one place for every env var (Mongo URI, access-token signing secret + expiry, refresh-token expiry, CORS origins, etc.) — mirrors the `config/env.ts` pattern kept on the frontend side for symmetry.
- **`core/auth_dependency.py`**: a FastAPI dependency injected into any route needing "current user" — including resolving a guest session, so `capture`, `avatars`, `tryon`, etc. don't each reimplement session handling.
- **`main.py`**: assembles the app — creates the FastAPI instance, mounts each service's router, registers `core/errors.py` exception handlers, sets up CORS.

## Invariants to Carry Forward

These came out of reading `user-side`'s `docs/backend-contract.md` and are worth upholding regardless of the SaaS/standalone split, since they're really privacy/correctness guarantees, not tenant-specific:

- Source photographs (capture step) are **retained** after avatar generation completes — this intentionally diverges from `user-side`'s reference invariant (which deletes them and disallows training use). Ours are kept specifically to keep improving avatar-generation accuracy over time. See `backend-implementation-plan.md`, Phase 0 item 2.
- Account deletion cascades: profile, avatars, try-on results, signature looks, capture sessions, and any stored refresh tokens all go with it.

## Explicit Non-Goals for This Plan

- **CLO3D worker service and job-queue technology** (Redis+RQ / Celery / arq) — tracked as a separate open decision. `avatars/service.py` and `tryon/service.py` are written to the point of "hands off a job," not further.
- **Garment web-scraping / on-demand ingestion** (optional flow step 7) — deferred.
