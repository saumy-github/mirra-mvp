# 04 - Docker local dev setup: concrete change plan

**Status:** planned, pending review — do not execute until Saumy confirms
**Created:** 2026-08-03
**Continues:** [02-phase-1-continuation-docker-env-and-local-db-plan.md](02-phase-1-continuation-docker-env-and-local-db-plan.md)

This file lists every file that will change, and the exact new content/diff, before any code is touched.

## Decisions locked in this round

1. Drop nginx from the local dev path entirely. Frontend container runs the Vite dev server. Vercel owns the real production build/hosting.
2. No committed prod env file. Render/Vercel dashboards own prod secrets. Only local dev gets env files, split per service.
3. Add a local `mongo` container with a named volume, replacing the current setup where local Docker dev points at the live Atlas `mirra-development` cluster.
4. Mongo host port: `127.0.0.1:27018:27017` (host 27018 → container's default 27017), not `27017:27017`, so it never collides with another local Mongo/Compass instance already using the default port. **Corrected from Saumy's stated `27017:27018` — that mapping had host/container backwards and wouldn't have worked; confirm this correction is what was meant.**
5. Backend requirements stay as the single root `requirements.txt` for now (not split). Accepted tradeoff: slower image rebuild only when `requirements.txt` changes, not per code edit, thanks to existing Docker layer ordering.
6. Hot reload included in this same pass (bind mounts + `--reload`/Vite dev server), since it's already in-scope for this phase per doc 02. Flag if you'd rather defer this specifically.

---

## File-by-file changes

### 1. `docker-compose.yml` (rewrite)

```yaml
services:
  mongo:
    image: mongo:7
    ports:
      - "127.0.0.1:27018:27017"
    volumes:
      - mongo_data:/data/db
    healthcheck:
      test: ["CMD", "mongosh", "--quiet", "--eval", "db.adminCommand('ping')"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: website/backend/Dockerfile
    env_file:
      - website/backend/.env.docker.dev
    ports:
      - "8000:8000"
    volumes:
      - ./website/backend/src:/app/website/backend/src
    depends_on:
      mongo:
        condition: service_healthy
    command: ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
    restart: unless-stopped

  frontend:
    build:
      context: ./website/frontend
      dockerfile: Dockerfile
    env_file:
      - website/frontend/.env.docker.dev
    ports:
      - "3000:3000"
    volumes:
      - ./website/frontend/src:/app/src
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  mongo_data:
```

Notes:
- `frontend.depends_on: [backend]` has no `condition`, which defaults to just "container started," not "healthy" — satisfies the plan-doc requirement that frontend isn't blocked by backend health.
- `backend`'s `command:` override switches on `--reload`; the Dockerfile's own `CMD` (no reload) stays as the default for a plain `docker build`/Render.
- Only `src/` is bind-mounted, not the whole project, so `node_modules`/installed deps inside the image aren't shadowed by the host filesystem.

### 2. `website/frontend/Dockerfile` (rewrite — drop the nginx/build stage entirely)

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "3000"]
```

### 3. `website/frontend/nginx.conf` — **delete**

No longer referenced anywhere once the Dockerfile above lands.

### 4. `website/backend/.env.docker.dev` (new, gitignored)

```env
MONGODB_URI=mongodb://mongo:27017
DATABASE_NAME=mirra_dev

ACCESS_TOKEN_SECRET=dev-only-secret-change-me-before-going-live-0000
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
COOKIE_SECURE=false

CORS_ORIGINS=http://localhost:3000

AVATAR_ENGINE_MODE=demo
TRYON_ENGINE_MODE=demo

UPLOADS_DIR=uploads
```

### 5. `website/backend/.env.example` (new, committed to git)

Same keys as above, secrets replaced with placeholders (e.g. `ACCESS_TOKEN_SECRET=changeme`), so a new dev can `copy` it and fill in nothing extra for local Docker use (Mongo/CORS defaults already work out of the box).

### 6. `website/frontend/.env.docker.dev` (new, gitignored)

```env
VITE_RUNTIME_ORIGIN=http://localhost:3000
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_AUTH_PROVIDER=mock
VITE_AVATAR_ENGINE_MODE=demo
VITE_TRYON_ENGINE_MODE=demo
VITE_INTEGRATION_MODE=mock
VITE_ANALYTICS_ENABLED=true
VITE_APP_VERSION=0.1.0
VITE_APP_ENV=development
```

### 7. `website/frontend/.env.example` (new, committed to git)

Same keys, same values (none of these are secret — all `VITE_*` is public by definition).

### 8. Root `.env.dev` — **delete**, after the two service-owned files above are verified working

Currently holds real Atlas credentials mixed with frontend public vars. Superseded entirely by files 4 and 6.

### 9. `website/backend/Dockerfile` — small edit only

No structural change. The dev-mode `--reload` flag comes from the compose `command:` override (see file 1), not a Dockerfile edit — keeps the image's default `CMD` (used by Render/plain `docker build`) reload-free, which is correct for production.

### 10. Root `package.json` (edit scripts)

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
    "dev:logs:mongo": "docker compose logs -f mongo"
  }
}
```

Drops `--env-file .env.dev` everywhere since each service now reads its own `env_file:` declared in `docker-compose.yml` — no root-level interpolation needed. Also collapses `dev:up` / `dev:up:all` into one target since `mongo` is now a real dependency every service needs, not an opt-in extra.

### 11. `.dockerignore` (add)

```text
.env
.env.*
!**/.env.example
```

Defensive: no env file — dev or prod — should ever be copyable into an image layer, even if a future Dockerfile's `COPY` scope widens.

### 12. `.gitignore` (edit)

Current:
```text
.env
.env.dev
```

New:
```text
.env
.env.*
!.env.example
!**/.env.example
```

So `website/backend/.env.docker.dev` and `website/frontend/.env.docker.dev` are gitignored automatically (matches the existing pattern of "no committed secrets"), while both `.env.example` files stay tracked.

---

## Verification after execution (not yet run)

- `docker compose up -d --build` brings up `mongo`, `backend`, `frontend` with no errors
- `docker compose ps` shows `mongo` healthy before `backend` reports ready
- `GET http://localhost:8000/api/v1/health` → `{"status":"ok","database":"connected"}` (connected, not unreachable — this is the real local Mongo now)
- Editing a file under `website/backend/src` reloads the backend without a rebuild
- Editing a file under `website/frontend/src` hot-reloads in the browser at `http://localhost:3000`
- `docker compose exec mongo mongosh --eval "db.adminCommand('ping')"` succeeds
- Confirm `localhost:27018` (not `27017`) is the only host-exposed Mongo port from this project

## Execution Log

Not started.
