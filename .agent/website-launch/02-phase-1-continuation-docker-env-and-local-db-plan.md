# 02 - Phase 1 continuation: service-owned envs, local Mongo, hot reload, Render/Vercel deployment path

**Status:** planned, not yet executed
**Created:** 2026-08-02
**Continues:** [01-docker-and-clo-render-pipeline.md](01-docker-and-clo-render-pipeline.md), Phase 1

## Scope confirmed by Saumy

- Pilot production deployment target:
  - **Backend:** Render
  - **Frontend:** Vercel
  - **Production database:** MongoDB Atlas
- Local development target:
  - Docker should make the website easy for another developer to start without understanding the whole repo.
  - Local development should use a **Docker MongoDB container**, not Atlas.
  - Production envs are managed by Render/Vercel, not committed env files.
- Env ownership should live with the service:
  - backend env files under `website/backend/`
  - frontend env files under `website/frontend/`
  - no root `.env.dev` as the long-term source of website env
- Keep Docker simple:
  - one `docker-compose.yml`
  - no `docker-compose.override.yml` for now
  - no extra "weird override file" caused by another project's past issues
- Make services more independent:
  - frontend should be able to start even if backend is not healthy yet
  - backend should start against local Mongo in dev
  - Mongo should be a local dev dependency, not a production service
- Add hot reload for local dev:
  - frontend uses Vite dev server hot reload
  - backend uses FastAPI/uvicorn reload, **not nodemon** (nodemon is for Node apps; this backend is Python)
- Migrate `mirra_measurements/` into `website/backend/`:
  - development should no longer require the old root-level measurement package
  - the backend becomes the owner of measurement/catalog seed logic and Mongo models
  - after migration and verification, delete the old `mirra_measurements/` folder

## Key decision: Docker is for local dev/pilot parity, not final production orchestration

We still keep Dockerfiles now, because they are useful for:

- repeatable local setup
- backend deployment on Render if we choose Render's Docker path
- validating that the app can boot from a clean image
- onboarding future developers

But for the pilot production setup:

- **Vercel will build and host the frontend.** It will read frontend env vars from Vercel project settings.
- **Render will run the backend.** It will read backend env vars from Render environment settings.
- **MongoDB Atlas stays production database.**
- Docker Compose is not the production control plane for Render/Vercel.

This means local env files and production env configuration are deliberately separate.

## Target file layout

Keep:

```text
docker-compose.yml
package.json
website/backend/Dockerfile
website/frontend/Dockerfile
```

Add/standardize:

```text
website/backend/.env.docker.dev
website/backend/.env.example
website/frontend/.env.docker.dev
website/frontend/.env.example
```

Do not keep long-term:

```text
.env.dev
```

Reason: root `.env.dev` was convenient for Compose interpolation, but it mixes backend secrets and frontend public config at repo root. Service-owned env files are easier for a beginner to reason about:

- backend env lives with backend
- frontend env lives with frontend
- deployment env lives in Render/Vercel dashboards

## Env rules

### Backend env

Backend env may contain secrets and private infrastructure URLs.

Local Docker dev:

```text
website/backend/.env.docker.dev
```

Example values:

```env
MONGODB_URI=mongodb://mongo:27017
DATABASE_NAME=mirratest
ACCESS_TOKEN_SECRET=dev-only-secret-change-me-before-prod-0000
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
COOKIE_SECURE=false
CORS_ORIGINS=http://localhost:3000
AVATAR_ENGINE_MODE=demo
TRYON_ENGINE_MODE=demo
UPLOADS_DIR=uploads
```

Production on Render:

Render environment variables, not a committed file:

```env
MONGODB_URI=<Atlas connection string>
DATABASE_NAME=mirratest
ACCESS_TOKEN_SECRET=<strong production secret>
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
COOKIE_SECURE=true
CORS_ORIGINS=https://<vercel-domain>
AVATAR_ENGINE_MODE=demo
TRYON_ENGINE_MODE=demo
UPLOADS_DIR=uploads
```

Note: Render filesystem persistence depends on service configuration. For production capture/photo/GLB storage, local disk should eventually move to object storage. For pilot, if uploads are needed on Render, explicitly decide whether to use Render Disk or S3-style storage before relying on it.

### Frontend env

Frontend `VITE_*` env is public. It is baked into the browser bundle and must never contain secrets.

Local Docker dev:

```text
website/frontend/.env.docker.dev
```

Example values:

```env
VITE_RUNTIME_ORIGIN=http://localhost:3000
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_AUTH_PROVIDER=live
VITE_AVATAR_ENGINE_MODE=demo
VITE_TRYON_ENGINE_MODE=demo
VITE_INTEGRATION_MODE=live
VITE_ANALYTICS_ENABLED=true
VITE_APP_VERSION=0.1.0
VITE_APP_ENV=development
```

Production on Vercel:

Vercel project environment variables:

```env
VITE_RUNTIME_ORIGIN=https://<vercel-domain>
VITE_API_BASE_URL=https://<render-backend-domain>/api/v1
VITE_AUTH_PROVIDER=live
VITE_AVATAR_ENGINE_MODE=demo
VITE_TRYON_ENGINE_MODE=demo
VITE_INTEGRATION_MODE=live
VITE_ANALYTICS_ENABLED=true
VITE_APP_VERSION=0.1.0
VITE_APP_ENV=production
```

## Compose direction

Use one `docker-compose.yml` for local development.

Services:

- `frontend`
- `backend`
- `mongo`

No Redis in this phase. Redis/queue comes later with the CLO worker work.

### Compose behavior

Backend:

- build from repo root if it still depends on root `requirements.txt`
- env from `./website/backend/.env.docker.dev`
- port `8000:8000`
- command uses reload in local dev:

```text
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

- bind mount backend source for hot reload
- depends on local `mongo` health
- use `extra_hosts: host.docker.internal:host-gateway` only if needed later for CLO host access

Frontend:

- build context `./website/frontend`
- local dev command should run Vite:

```text
npm run dev -- --host 0.0.0.0 --port 3000
```

- port `3000:3000`
- bind mount frontend source for hot reload
- do **not** require backend health to start
- read local frontend env in a way Vite understands

Mongo:

- image `mongo:7`
- local-only database
- named volume, not a host path
- healthcheck with `mongosh` if available in the image; otherwise a simple connection command
- no host port required unless we want Compass/manual debugging. If exposed for debugging, bind only to localhost:

```text
127.0.0.1:27017:27017
```

### Why no root `--env-file` in scripts

The previous root `.env.dev` was needed because Compose used `${VITE_*}` interpolation for frontend build args.

The new local-dev plan should avoid that by letting each app read its own env file:

- backend gets `env_file: ./website/backend/.env.docker.dev`
- frontend runs Vite dev inside the container, so Vite can load env from the frontend project

For static production image builds, build args still matter. But production frontend will be Vercel-built, not served from our Compose nginx image for the pilot.

## Package scripts target

Root `package.json` should become a simple launcher:

```json
{
  "private": true,
  "scripts": {
    "dev:up": "docker compose up -d --build",
    "dev:down": "docker compose down",
    "dev:restart": "docker compose restart",
    "dev:ps": "docker compose ps",
    "dev:logs": "docker compose logs -f",
    "dev:logs:backend": "docker compose logs -f backend",
    "dev:logs:frontend": "docker compose logs -f frontend",
    "dev:logs:mongo": "docker compose logs -f mongo",
    "dev:seed": "docker compose exec backend python scripts/seed_dev.py",
    "dev:smoke": "docker compose exec backend python scripts/smoke_e2e.py"
  }
}
```

`dev:seed` may need to change depending on how seed scripts are reorganized during the `mirra_measurements/` migration.

## Dockerfile direction

### Backend Dockerfile

Current backend Dockerfile installs from root `requirements.txt`, which matches the repo's current Python dependency convention.

For this phase, keep it unless dependency bloat becomes painful again.

Later, consider a backend-specific requirements file:

```text
website/backend/requirements.txt
```

Reason: the backend image currently inherits heavyweight pipeline dependencies that the website API may not need at runtime. This is not blocking the pilot, but it matters for Render build time and image size.

### Frontend Dockerfile / nginx

For the pilot, remove nginx from the active frontend path.

Reason: the frontend production target is **Vercel only** for now. Vercel will run `npm ci` + `npm run build` inside its own build environment and serve the generated `dist/` files from Vercel's own CDN/static hosting layer. In that deployment path, nginx is not used.

Local development also does not need nginx. The frontend container should run the Vite dev server for hot reload:

```text
npm run dev -- --host 0.0.0.0 --port 3000
```

Implementation direction:

- remove nginx from `website/frontend/Dockerfile`
- remove `website/frontend/nginx.conf`
- make the frontend container a dev-only Vite container
- let Vercel own production frontend build/hosting

If we later stop using Vercel and deploy the frontend to a Docker host, VPS, ECS, Render container, or another non-Vercel environment, we can reintroduce a static-serving Dockerfile/nginx path then. Do not carry that complexity during the pilot.

## `mirra_measurements/` migration plan

Goal: backend owns all website measurement/catalog database logic.

Current state:

- `website/backend/src/measurements/` and `website/backend/src/catalog/` already exist.
- `mirra_measurements/` still exists as an older root-level reference/source package.
- Existing backend plan says `mirra_measurements/` should eventually be deleted manually after backend parity is verified.

Execution plan:

1. Inventory `mirra_measurements/`:
   - models
   - DB helpers
   - seed scripts
   - golden fixtures
   - any import paths still used outside that folder
2. Confirm backend parity:
   - `website/backend/src/measurements/models.py`
   - `website/backend/src/catalog/models.py`
   - `website/backend/scripts/seed_measurements.py`
   - `website/backend/scripts/seed_sizes.py`
   - `website/backend/scripts/golden_users.py`
3. Move any missing useful fixtures/scripts into `website/backend/scripts/` or a backend-local fixture folder.
4. Update imports so website dev, smoke tests, and seed scripts do not import from `mirra_measurements`.
5. Run backend smoke test against local Docker Mongo.
6. Run a repo-wide import search:

```text
rg "mirra_measurements"
```

7. Only after zero required imports remain, delete `mirra_measurements/`.

Important: deleting `mirra_measurements/` must happen after verification, not as the first step. It still may be a useful source of truth while checking parity.

## Local dev flow after this phase

Fresh developer setup:

1. Clone repo.
2. Install Docker Desktop.
3. Copy env examples:

```powershell
copy website\backend\.env.example website\backend\.env.docker.dev
copy website\frontend\.env.example website\frontend\.env.docker.dev
```

4. Start everything:

```powershell
npm run dev:up
```

5. Seed local Mongo:

```powershell
npm run dev:seed
```

6. Open:

```text
Frontend: http://localhost:3000
Backend health: http://localhost:8000/api/v1/health
Backend docs: http://localhost:8000/docs
```

7. Verify:

```powershell
npm run dev:smoke
```

Expected health response:

```json
{"status":"ok","database":"connected"}
```

## Production deployment flow after this phase

### Render backend

Render config:

- root directory: repo root, or `website/backend` depending on selected Render mode
- service type: Web Service
- runtime path:
  - option A: Docker using `website/backend/Dockerfile`
  - option B: native Python build/start commands
- start command if native:

```text
uvicorn src.main:app --host 0.0.0.0 --port $PORT
```

Required Render env:

- `MONGODB_URI` = Atlas URI
- `DATABASE_NAME`
- `ACCESS_TOKEN_SECRET`
- `COOKIE_SECURE=true`
- `CORS_ORIGINS=https://<vercel-domain>`
- engine mode vars

Backend health check:

```text
/api/v1/health
```

### Vercel frontend

Vercel config:

- root directory: `website/frontend`
- build command: `npm run build`
- output directory: `dist`
- install command: `npm ci`

Required Vercel env:

- `VITE_API_BASE_URL=https://<render-backend-domain>/api/v1`
- `VITE_RUNTIME_ORIGIN=https://<vercel-domain>`
- `VITE_INTEGRATION_MODE=live`
- `VITE_AUTH_PROVIDER=live`
- other public `VITE_*` values

After Vercel URL is known, update Render `CORS_ORIGINS`.

## Verification checklist

Local Docker dev:

- `npm run dev:up` starts `mongo`, `backend`, `frontend`
- frontend hot reload works after editing a `.tsx` file
- backend hot reload works after editing a `.py` file
- `GET http://localhost:8000/api/v1/health` reports database connected
- `npm run dev:seed` inserts local dev data idempotently
- `npm run dev:smoke` passes against local Mongo
- frontend live mode can sign up/log in/continue as guest against local backend

Render/Vercel pilot:

- Render backend deploys successfully
- Render health check returns database connected against Atlas
- Vercel frontend deploys successfully
- browser can call Render API without CORS errors
- refresh-token cookie settings work in production
- demo avatar/try-on states still work

Migration:

- no required imports from `mirra_measurements`
- backend seed scripts own local data bootstrap
- old `mirra_measurements/` deleted only after smoke tests pass

## Explicitly not in this phase

- Redis/RQ/Celery queue for CLO worker
- CLO worker containerization
- object storage migration for uploads/GLB files
- Kubernetes/ECS-scale deployment
- real production autoscaling plan
- changing from demo engine mode to live CLO jobs

Those belong after the local dev/prod boundary is clean and the website is deployable on Render/Vercel.

## Execution Log

Not started.
