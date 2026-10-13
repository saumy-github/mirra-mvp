# Developer Setup Guide

*Status: current*
*Last updated: 2026-10-11*

This repo has two layers: **the website** (what a shopper actually opens in a browser — FastAPI backend + React frontend) and **the pipeline** (CLO3D-driven avatar/garment/try-on generation). Most new contributors only need Part I, Sections 1-5 (the website); Section 6 (CLO3D + plugin + worker) is only needed if you're touching avatar generation, product ingestion, or virtual try-on.

The guide is split into **Part I — one-time setup** (do this once, when you first join) and **Part II — daily practice** (what you actually run each time you sit down to work).

---

# Part I — One-time setup

## 1. Prerequisites — install these first

### Everyone needs

- **Git**
- **Python 3.12+**
- **Node.js** (LTS, v20 or newer)
- **Docker Desktop** — runs the backend + Redis. Make sure it's actually running before any `docker compose`/`npm run dev:up` command.
- Access to the shared **MongoDB Atlas** connection string — ask a teammate privately; it's never committed to the repo.

### Only if you're working on the pipeline (Section 6)

- **CLO3D** installed, with a license.
- The **CLO SDK** matching your installed CLO3D version, downloaded from the CLO developer portal (`developer.clo3d.com`) — get the exact version your CLO3D app reports (bottom-left corner of the CLO3D window), not just "the latest."
- **Windows:** Visual Studio with the C++ toolchain (2019 or 2022 recommended) + CMake.
- **macOS:** Xcode Command Line Tools (`xcode-select --install`) + CMake (`brew install cmake`) + Qt 5 (`brew install qt@5`).

### Verify everything installed correctly

```bash
git --version
python --version
node --version
npm --version
docker --version
docker compose version
```

Each should print a version number. You want Python 3.12+ and Node 20.x+.

---

## 2. Clone the repo

```bash
git clone <repo-url>
cd mirra-mvp
```

---

## 3. Python environment & dependencies (repo root — needed for everything)

The whole repo shares **one** virtual environment at the repo root — never create a separate venv inside a subfolder, and never `pip install` globally.

```bash
python -m venv .venv
```

Activate it:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

Install everything:

```bash
pip install -r requirements.txt
```

This one file covers both the website backend's dependencies (FastAPI, pymongo, rq) and the pipeline's heavier ML stack (torch, transformers, opencv, SAM2, etc.). If you add a new Python dependency anywhere in the repo, it goes in this one file (and, if the backend's Docker image needs it too, also in `website/backend/requirements-docker.txt` — see that file's own comment for why both exist).

---

## 4. Setting up the website (backend + frontend)

### Backend — Option A: Docker (recommended)

From the **repo root**:

```bash
cp website/backend/.env.example website/backend/.env.docker.dev
```
Fill it in as follows — ask a teammate privately for the shared dev `MONGODB_URI` (never commit it anywhere); leave the Google fields blank to run with sign-in disabled (`auth/google/start` responds 503), or get your own from `console.cloud.google.com`:

```env
MONGODB_URI=<ask a teammate — shared Atlas dev URI>
DATABASE_NAME=mirratest

ACCESS_TOKEN_SECRET=dev-only-secret-change-me-before-going-live-0000
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
COOKIE_SECURE=false

CORS_ORIGINS=http://localhost:3000
APP_ENV=development

# Docker service name, not localhost — the backend reaches Redis over the
# Docker network
REDIS_URL=redis://redis:6379/0

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
FRONTEND_AUTH_SUCCESS_URL=http://localhost:3000/auth/callback
FRONTEND_AUTH_FAILURE_URL=http://localhost:3000/auth/login
```

### Frontend — always native, no Docker option

```bash
cd website/frontend
cp .env.example .env.development
npm install
```

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1

VITE_ANALYTICS_ENABLED=true

VITE_APP_ENV=development
```

`.env.development` is the filename Vite actually loads in dev mode.

---

## 5. Starting artifacts you'll need from a teammate (not in git)

`clo_avatar_generation/input/` only has a `.gitkeep` in git — every real input file is gitignored and has to be shared out-of-band. Ask a teammate for:

- **A base avatar template** (`base-1.avt`) — the starting mesh Step 1 morphs into a personalized avatar. Goes in `clo_avatar_generation/input/`.
- **Sample measurement files** (e.g. `u_001.measurements.json`) — only needed if you want to run the CLI pipeline (`run_avatar.py`) without a live MongoDB measurement doc. Same folder.

You only need these if you're running the pipeline directly (Section 6) — the website's own flow (a shopper typing in their own measurements) doesn't need them.

---

## 6. Running CLO3D, building the plugin, and the worker

Skip this section unless you're working on Step 1 (avatar generation), Step 2 (product ingestion), or Step 3 (virtual try-on).

### 6.1 — MongoDB for the pipeline side

The pipeline (not the website) depends directly on `mirra_measurements/` for the `cloths`/`sizes` collections and as a measurement fallback — `mirra_measurements/db.py` hardcodes `DATABASE_NAME = "mirratest"`, the same database `website/backend` uses, and `mirra_measurements/.env` points at the same shared Atlas dev connection string as everyone else's.

**You don't need to seed anything.** There's one shared dev database for the whole team — if `cloths`/`sizes` are already populated (they are), every new contributor already has that data the moment they point at the shared `MONGODB_URI`. The seed commands (`python -m mirra_measurements.seed_cloths`, `seed_sizes`) only matter if the shared database itself is ever genuinely empty — not a per-developer setup step.

### 6.2 — Build and install the CLO3D plugin

1. Copy `clo_workspace/.env.example` to `clo_workspace/.env` and fill in with your own machine's paths. Example (Windows):
   ```bash
   cp clo_workspace/.env.example clo_workspace/.env
   ```
   ```env
   PLUGIN_PLATFORM=windows
   BUILD_CONFIG=Release

   CMAKE_EXE=C:/Program Files/Microsoft Visual Studio/18/Community/Common7/IDE/CommonExtensions/Microsoft/CMake/CMake/bin/cmake.exe
   CMAKE_GENERATOR=Visual Studio 18 2026
   CMAKE_ARCH=x64

   CLO_SDK_PATH=C:/Users/<you>/Downloads/CLO_SDK_v2026.1.224_Win
   CLO_PLUGINS_DIR=C:/Program Files/CLO Standalone OnlineAuth/plugins
   CLO_PLUGIN_VAULT_DIR=C:/D-drive-data/plugins/mirra-vault
   ```
   `CLO_SDK_PATH` must match your installed CLO3D version. `CLO_PLUGIN_VAULT_DIR` (built plugins saved here for rollback) must be **outside** the repo. macOS: `PLUGIN_PLATFORM=mac`, plus `CMAKE_PREFIX_PATH`/`Qt5_DIR` if CMake can't find Qt 5 automatically and `CMAKE_OSX_ARCHITECTURES` (`arm64` or `x86_64`) in place of the Windows-only `CMAKE_GENERATOR`/`CMAKE_ARCH`.
2. Build:
   ```bash
   python clo_workspace/build_plugin.py
   ```
   This builds the DLL (Windows) or dylib (macOS) and saves a versioned copy to `CLO_PLUGIN_VAULT_DIR`, printing the exact copy command you need next.
3. Manual install step (requires Administrator on Windows):
   - Close CLO3D.
   - Copy the versioned build artifact from the vault into your CLO plugins folder (the build output gives you the exact path).
   - Delete any old unversioned `RestPlugin.dll`/`libRestPlugin.dylib` if present.
   - Restart CLO3D.
4. Verify the plugin is actually running:
   ```bash
   # Windows (PowerShell)
   Invoke-RestMethod http://127.0.0.1:50505/health
   # macOS
   curl http://127.0.0.1:50505/health
   ```

**Always check which SDK version the plugin was actually built against** (the build log in `clo_workspace/logs/`, not a version file's notes field — those can go stale) before assuming it matches your running CLO3D app. A mismatch here has caused real, hard-to-diagnose hangs before.

To switch between previously-built versions saved in the vault without rebuilding, use `python clo_workspace/scripts/switch_plugin.py`.

### 6.3 — The native CLO worker

The worker drives the real pipeline on behalf of the website — it needs CLO3D open with the plugin loaded (6.2) and Redis reachable (Section 4's Docker backend already starts Redis; `docker compose up -d redis` on its own also works).

1. Create the worker's env file:
   ```bash
   cp worker/.env.example worker/.env
   ```
   ```env
   MONGODB_URI=<same shared Atlas dev URI as the backend's — ask a teammate>
   DATABASE_NAME=mirratest
   REDIS_URL=redis://localhost:6379/0

   ACCESS_TOKEN_SECRET=dev-only-secret-change-me-before-going-live-0000
   ACCESS_TOKEN_EXPIRE_MINUTES=15
   REFRESH_TOKEN_EXPIRE_DAYS=30
   COOKIE_SECURE=false
   CORS_ORIGINS=http://localhost:3000
   ```
   `REDIS_URL` uses `localhost`, not the Docker service name, since the worker runs natively outside Docker. The last five fields exist only because `worker/tasks.py` imports the backend's full `Settings` object — the worker never actually uses them, so any value satisfying the validators works (using the same `ACCESS_TOKEN_SECRET` as the backend's is fine, but not required). See `.agent/saumy/02-remaining-build-list.md`, item AR1, for the real fix.
2. Run it, from the repo root, inside the repo `.venv`:
   ```bash
   python worker/run_worker.py
   ```

**Concurrency is intentionally 1** — CLO3D's plugin is itself single-threaded, so never run a second worker against the same CLO3D instance; it will race and corrupt whichever job loses.

---

# Part II — Daily practice

What you actually run each time you sit down to work, now that Part I is done once.

## 7. Starting everything up

**Website only:**
```bash
npm run dev:up               # terminal 1 — backend + Redis
cd website/frontend && npm run dev   # terminal 2 — frontend, http://localhost:3000
```

**Website + pipeline:**
```bash
# Open CLO3D manually first, confirm the plugin loaded (Section 6.2 step 4)
npm run dev:up                       # terminal 1 — backend + Redis
python worker/run_worker.py          # terminal 2 — worker (repo-root .venv)
cd website/frontend && npm run dev   # terminal 3 — frontend
```

You don't need `npm run dev:seed` either, for the same reason as Section 6.1 — one shared dev database for the whole team, already seeded.

Backend and frontend both hot-reload on edits — no restart needed. The worker does **not** hot-reload; restart it manually after changing anything under `clo_avatar_generation/`, `clo_vto/`, `product_ingestion/`, or `worker/`.

Stop everything with `npm run dev:down` (and just Ctrl+C the worker/frontend terminals).

## 8. Useful commands

- Backend logs: `docker compose logs -f backend`
- Open a MongoDB shell against the dev database: use MongoDB Compass with the shared `MONGODB_URI`
- Run the pipeline steps directly (see `CLAUDE.md` for the full command reference):
  ```bash
  python clo_avatar_generation/run_avatar.py        # Step 1
  python product_ingestion/run_product_ingestion.py # Step 2
  python clo_avatar_generation/run_clo_vto.py        # Step 3
  ```
- Check which SDK version the currently-installed plugin was built against:
  ```bash
  python clo_workspace/scripts/get_installed_plugin_info.py
  ```

---

## Troubleshooting

1. **`npm run dev:up` fails or the backend can't find a package after pulling new changes.** Someone added a new backend dependency. Run `npm run dev:up` again — it rebuilds automatically.

2. **Frontend can't reach the backend / network errors in the browser console.** Confirm `npm run dev:up` is actually running and healthy (`docker compose logs -f backend`), and that `VITE_API_BASE_URL` in the frontend's `.env.development` points at the right port.

3. **Backend won't boot, complains about `ACCESS_TOKEN_SECRET`.** It must be at least 32 characters — enforced on purpose so a missing secret fails loudly instead of booting with a known/public default.

4. **Worker can't reach CLO3D.** Open CLO3D, confirm the plugin is actually loaded (`Invoke-RestMethod http://127.0.0.1:50505/health` should respond), and make sure you haven't got a second worker already running against the same CLO3D instance.

5. **Plugin build succeeds but CLO3D behaves strangely / hangs on `New Project`.** Check that the plugin was actually built against the SDK version matching your installed CLO3D app — see Section 6.2. Check `clo_workspace/logs/` for the actual build log, not a version file's notes.

6. **`fastapi dev` crashes with `UnicodeEncodeError` (native backend path).** Run `setx PYTHONUTF8 1` once, then open a new terminal.

7. **Pipeline scripts fail looking for `cloths`/`sizes` documents.** This shouldn't happen on the shared dev database — if it does, the shared database may actually be missing data; check with a teammate before re-seeding, rather than assuming you need to run the seed commands yourself.

---

## Reference: pipeline/technology-specific setup guides

| Pipeline / Technology | Setup Guide |
|---|---|
| CLO worker | [worker/README.md](worker/README.md) |
| Website backend | [website/backend/README.md](website/backend/README.md) |
| Website frontend | [website/frontend/README.md](website/frontend/README.md) |
