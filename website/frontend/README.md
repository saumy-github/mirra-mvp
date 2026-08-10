# Mirra Website Frontend

Vite + React frontend for the website pilot. Runs natively (not in Docker) —
the backend runs in Docker, this talks to it over `localhost:8000`.

## First-time setup

```powershell
cd website\frontend
npm ci
copy .env.example .env.development
```

The copied defaults already point at the Dockerized backend
(`VITE_API_BASE_URL=http://localhost:8000/api/v1`) — no edits needed for
local dev. There's no mock/demo mode — every environment (local dev,
production) always talks to the real backend.

## Run (development)

Start the backend first (from the **repo root**, separate terminal):

```powershell
npm run dev:up
```

Then, from `website/frontend/`:

```powershell
npm run dev
```

Open http://localhost:3000. Vite's dev server hot-reloads on every save —
no restart needed.

## Daily workflow

```powershell
npm run dev:up               # terminal 1, repo root — backend
cd website\frontend
npm run dev                  # terminal 2 — frontend
```

Stop the backend with `npm run dev:down` from the repo root. Stop the
frontend with Ctrl+C.

## Why not Docker for the frontend too?

Tried it — Docker Desktop's bind-mount filesystem layer on Windows doesn't
reliably propagate file-change events (or even file `stat`/mtime updates)
into the container, so Vite's watcher never sees edits, polling or not.
Running natively sidesteps the problem entirely and matches this repo's own
documented pattern (`.agent/website-launch/Info.md`): Docker for a
deployable artifact, the package manager for fast local feedback.

## Build

```powershell
npm run build
```

Production build/hosting is Vercel's job, not this repo's Docker setup —
see `.agent/website-launch/02-phase-1-continuation-docker-env-and-local-db-plan.md`.
