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

From `website/backend/`:

```powershell
..\..\.venv\Scripts\fastapi dev src/main.py
```

- API: http://localhost:8000/api/v1 (matches the frontend's `VITE_API_BASE_URL`)
- Health: http://localhost:8000/api/v1/health
- Interactive docs: http://localhost:8000/docs

`fastapi dev` auto-reloads on code changes. Production later runs the same
app via uvicorn/gunicorn workers instead — no code changes.

## Seed dev data

```powershell
..\..\.venv\Scripts\python scripts\seed_measurements.py
..\..\.venv\Scripts\python scripts\seed_sizes.py
```

## Verify everything works

```powershell
..\..\.venv\Scripts\python scripts\smoke_e2e.py
```

Runs the full pilot flow (guest → measurements → capture → demo avatar →
catalog → demo try-on → signature look → analytics → account deletion)
in-process against the real database, cleaning up after itself.
Exit code 0 = healthy.

## Engine modes

`AVATAR_ENGINE_MODE` / `TRYON_ENGINE_MODE` are `demo` by default: staged
fake jobs so the frontend can integrate before the CLO3D worker exists.
`live` currently refuses with a 503 — it's the seam for the future worker
queue (deliberately undecided, see implementation plan Phase 0 item 3).
