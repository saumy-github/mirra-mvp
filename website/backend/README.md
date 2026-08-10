# Mirra Website Backend

FastAPI + MongoDB backend for the website pilot. Architecture:
[backend-structure-plan.md](../backend-structure-plan.md) · build order:
[backend-implementation-plan.md](../backend-implementation-plan.md).

## First-time setup

From the **repo root**:

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Then create your local env file (never commit it):

```powershell
copy website\backend\.env.example website\backend\.env
```

and set `MONGODB_URI` in it to the shared Atlas URI (ask Saumy privately —
it is never sent through git). Without it the app still boots against
`mongodb://localhost:27017` and `/api/v1/health` reports the database as
unreachable.

Note: Python is run in UTF-8 mode (`PYTHONUTF8=1`). If `fastapi dev`
crashes with a `UnicodeEncodeError` on your machine, run
`setx PYTHONUTF8 1` once and open a new terminal.

## Run (development)

**Option A — Docker (recommended, matches CI/prod more closely):** from the
**repo root**:

```powershell
npm run dev:up
```

Builds and starts the backend with hot reload (`uvicorn --reload`, source
bind-mounted — edits apply with no rebuild). Env comes from
`website/backend/.env.docker.dev` (gitignored, copy `.env.example` to create
it), not the `.env` from the venv flow below. Stop with `npm run dev:down`,
tail logs with `npm run dev:logs:backend`.

**Option B — native venv**, from `website/backend/`:

```powershell
..\..\.venv\Scripts\fastapi dev src/main.py
```

Either way:
- API: http://localhost:8000/api/v1 (matches the frontend's `VITE_API_BASE_URL`)
- Health: http://localhost:8000/api/v1/health
- Interactive docs: http://localhost:8000/docs

The frontend (`website/frontend`) always runs natively either way — see
its own README. Only the backend has a Docker option today.

## Seed dev data

Docker: `npm run dev:seed` (from repo root). Native venv:

```powershell
..\..\.venv\Scripts\python scripts\seed_measurements.py
..\..\.venv\Scripts\python scripts\seed_sizes.py
```

## Verify everything works

Docker: `npm run dev:smoke` (from repo root). Native venv:

```powershell
..\..\.venv\Scripts\python scripts\smoke_e2e.py
```

Runs the flows that don't need CLO3D (guest → measurements → catalog →
analytics → account deletion) in-process against the real database,
cleaning up after itself. Exit code 0 = healthy.

Avatar generation and try-on rendering always run the real CLO3D pipeline
now (no demo/live mode) — they're covered by CLI runs
(`clo_avatar_generation/run_avatar.py`, `clo_vto/run_clo_vto.py`) and manual
live tests against the native worker instead, not this smoke test. See
`.agent/website-launch/22-remove-demo-live-mode-and-upload-split.md`.
