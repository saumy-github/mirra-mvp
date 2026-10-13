# 04 — Plan: env file consolidation and field cleanup

*Status: in progress — .example files and deletions done; 4 real-file edits pending (listed below, require your action)*
*Compiled: 2026-10-11*
*Executed: 2026-10-13*

## Context

The repo has accumulated duplicate `.env` files per component (e.g. backend has three real env files, frontend has two) plus fields inside them that no longer correspond to anything the code reads — confirmed to be leftovers from the demo/live "engine mode" system that was removed earlier (`.agent/website-launch/22-remove-demo-live-mode-and-upload-split.md`). Goal, per direction already given: each component ends up with **exactly one** real env file, its `.env.example` names that file in a top comment, and every field in both files is something the code actually reads — with the `.env.example` itself being the accurate, trustworthy reference going forward (not a prose doc).

Methodology: cross-referenced the actual field *names* in every real `.env` file (read once, with explicit permission, names only — no values were viewed or recorded, none appear below) against a full repo-wide sweep of every `os.environ`/`os.getenv`/`import.meta.env.VITE_*` call and every pydantic `Settings` field. Two independent passes (a manual grep + a dedicated Explore agent) agree on the frontend findings.

No secret **value** will be touched — only file structure and field *names*. Changes to any field's value stay entirely a manual, separate step.

---

## Per-component changes

### 1. Backend (`website/backend/`) — canonical file: `.env.docker.dev`

- **Delete** `website/backend/.env.dev` (single-field stub, superseded — native `fastapi dev` mode is already retired from `SETUP.md`).
- **Remove from `.env.docker.dev` and `.env.example`** — confirmed absent from `config.py`'s `Settings` class entirely, leftover from the removed demo/live engine-mode system:
  - `AVATAR_ENGINE_MODE`
  - `TRYON_ENGINE_MODE`
  - `UPLOADS_DIR`
- **Add to `.env.docker.dev`** (currently absent; has a safe default of `"development"` so not breaking today, but should be explicit rather than implicit): `APP_ENV`
- **Add top comment to `.env.example`**: `# Copy this file to .env.docker.dev `
- `.env.example` additionally has `JOIN_NOTIFICATION_EMAIL`, `SMTP_*` fields not present in `.env.docker.dev` — these are all genuinely optional (default to `""`/unconfigured in `config.py`), so no change needed there, just noting it's expected.

### 2. Frontend (`website/frontend/`) — canonical file: `.env.development` (already decided)

- **Delete** `website/frontend/.env.dev`.
- **Remove from `.env.development` and `.env.example`** — confirmed not read anywhere under `website/frontend/src/` (checked twice, independently):
  - `VITE_AUTH_PROVIDER`
  - `VITE_AVATAR_ENGINE_MODE`
  - `VITE_INTEGRATION_MODE`
  - `VITE_RUNTIME_ORIGIN`
  - `VITE_TRYON_ENGINE_MODE`
- **Keep**: `VITE_API_BASE_URL`, `VITE_ANALYTICS_ENABLED`, `VITE_APP_ENV` — confirmed actually read.
- **Remove** (explicit request, 2026-10-13): `VITE_APP_VERSION` — has a safe fallback in code (`?? "0.1.0"`), so removing it from the env file is non-breaking.
- **Add top comment to `.env.example`**: `# Copy this file to .env.development — the only env file this frontend uses (Vite's dev-mode filename).`

### 3. Worker (`worker/`) — canonical file: `worker/.env` (already just one; no rename needed)

- **Confirmed real gap, not stale cruft** (verified 2026-10-13). `worker/.env` currently only has `MONGODB_URI` and `REDIS_URL`, but `worker/tasks.py` needs the full backend `Settings` object, which also requires `DATABASE_NAME`, `ACCESS_TOKEN_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `COOKIE_SECURE`, and `CORS_ORIGINS` — none with defaults.
- **Add to `worker/.env` and `worker/.env.example`**: `DATABASE_NAME`, `ACCESS_TOKEN_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `COOKIE_SECURE`, `CORS_ORIGINS` — same values as the backend's, so the worker is self-sufficient and doesn't silently depend on whatever else happens to be set in the shell it's launched from.
- **Add top comment to `worker/.env.example`**: `# Copy this file to .env — the only env file the worker uses.`

### 4. `mirra_measurements/` — canonical file: `mirra_measurements/.env` (already just one)

- **Fix `.env.example`** — it's currently completely empty (zero fields), while the real `.env` correctly has `MONGODB_URI`. Add `MONGODB_URI` to the example so it's actually usable as a template.
- **Add top comment to `.env.example`**: `# Copy this file to .env — the only env file this module uses.`

### 5. `clo_workspace/` — canonical file: `clo_workspace/.env` (already just one)

- **Remove from `.env`** (the real file only — `.env.example` correctly never included it): `PLUGIN_PORT` — confirmed zero references anywhere in the repo (Python, C++, headers, JSON). The plugin's port (50505) is hardcoded everywhere it's actually used instead. This is a leftover in the real file that was never pruned, not a documentation gap.
- **No change needed to `.env.example`** — it's already accurate and complete, Windows and macOS blocks both correctly reflect every field the real `.env` (minus `PLUGIN_PORT`) and `build_plugin.py` actually use. No top-comment addition needed either, it's already there.

### 6. Repo root

- **Delete** `.env.dev` — confirmed zero references anywhere (not in `docker-compose.yml`, `package.json`, or any `load_dotenv`/`os.getenv` call). It's also structurally wrong for the current layout — it mixes backend-style fields and `VITE_*` frontend fields in one file, a leftover from before backend/frontend had their own separate env files.

---

## What this plan does NOT include

- Won't touch or view any actual secret **value** — only file existence and field names.
- Won't change `SETUP.md` as part of this plan — once the files are consolidated, a small follow-up pass on `SETUP.md`'s env tables to match should happen as a separate step, after this lands.
- Nothing gets deleted or edited until this plan is reviewed and execution is explicitly requested.

## Verification after implementing

1. `git status` — confirm only the intended `.env*` files changed/deleted. Note: real `.env` files aren't git-tracked per `.gitignore`, so `git status` will only show changes to the `.example` files — most deletions here are of gitignored files, so verify those by directly listing the directories, not just `git status`.
2. Re-run the field-name-only grep from this audit on each surviving file, confirm it now matches exactly what each component's code reads.
3. Actually start each component once (`npm run dev:up`, `cd website/frontend && npm run dev`, `python worker/run_worker.py`, a `clo_workspace/build_plugin.py` run) to confirm nothing broke from a field being removed that was secretly still needed.

---

## Execution status (2026-10-13)

**Done directly:**
- All `.env.example` files updated (backend, frontend, worker, mirra_measurements) — dead fields removed, `APP_ENV`/worker fields added, top comments added, `VITE_APP_VERSION` removed per request, worker's example stripped of all comments per request.
- Backend `.env.example`, follow-up pass (2026-10-13): added `REDIS_URL` — a genuine pre-existing gap, not caused by this cleanup (`config.py` requires it with no default; the example never had it even before today). Removed the whole SMTP/`JOIN_NOTIFICATION_EMAIL` block per request (notifications not implemented yet) — safe, all those fields default to unconfigured in `config.py`. No real-file (`.env.docker.dev`) change needed for either — it never had the SMTP fields to begin with, and already has `REDIS_URL`.
- `clo_workspace/.env.example` — confirmed already correct, no change needed.
- Deleted: repo-root `.env.dev`, `website/backend/.env.dev`, `website/frontend/.env.dev`.
- `worker/README.md` — fixed the dangling `.env.dev` reference, the stale `AVATAR_ENGINE_MODE=live`/`TRYON_ENGINE_MODE=live` mention, and expanded the setup step to list all the worker's new fields with a pointer to AR1.

**Pending — these 4 need to be applied by hand** (real `.env` files are permission-blocked for me by design; exact content already handed over in chat):
- [ ] `clo_workspace/.env` — delete the `PLUGIN_PORT=50505` line.
- [ ] `worker/.env` — add `DATABASE_NAME`, `ACCESS_TOKEN_SECRET` (placeholder value, doesn't need to match backend's real secret), `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `COOKIE_SECURE`, `CORS_ORIGINS`.
- [ ] `website/backend/.env.docker.dev` — delete `AVATAR_ENGINE_MODE`, `TRYON_ENGINE_MODE`, `UPLOADS_DIR`; add `APP_ENV=development`.
- [ ] `website/frontend/.env.development` — delete `VITE_RUNTIME_ORIGIN` (confirmed 2026-10-13: the other 5 flagged fields were already absent from the real file).

**Deliberately deferred, not part of this plan:**
- AR1 (worker importing the backend's full `Settings` object instead of a narrow Mongo-only subset) — flagged for a separate effort, not scoped into this cleanup. See `.agent/saumy/02-remaining-build-list.md`.
- `SETUP.md`'s env tables — still need a follow-up pass to match the new reality, once the 4 pending edits above are confirmed applied.
