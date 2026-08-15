# 01 - How AI should work on this repo

This is the fresh entry point for continuing Mirra's website work. The old `.agent/website-launch/` folder (docs 01-23) is not deleted and is still valid as a detailed historical record/execution log if you need to know exactly why something was built a certain way — but it's long and partially superseded. Start here; go there only when you need the deeper trail.

## The one hard constraint: CLO3D is single-instance, concurrency = 1

CLO3D + its REST plugin (`localhost:50505`) is one process, single-threaded, one command queue. This is not a soft guideline — running two things against it at once (two workers, a live test while the worker is also processing a job, a CLI run overlapping a worker-driven run) **corrupts whichever job's scene state loses**, silently or with confusing errors.

Rules that follow from this:
- **Exactly one agent/subagent may touch CLO, the worker (`worker/`), or the CLO pipeline (`clo_avatar_generation/`, `clo_vto/`) at any given time.** If you're running multiple subagents in parallel, only one of them should ever be assigned this territory, and it must serialize its own CLO-touching work internally too — never fire off two CLO operations from within the same agent either.
- Before starting any CLO/worker work, check whether the user is also actively using CLO3D right now — an agent's test run competing with the user's own manual use causes the same corruption.
- The native worker (`worker/run_worker.py`) must never be started twice against the same CLO instance. If you start one for testing, stop it when you're done (`Stop-Process` on the PID, or note it clearly if leaving it running intentionally).
- **Real verification of CLO-touching changes requires an actual live run** — `python -m py_compile` and import checks catch syntax errors, not whether CLO3D actually produces a usable result. The GLB-packing bug (doc 11) was only caught by actually opening the exported file, not by any static check.

## Parallel work across multiple agents/subagents

Safe to parallelize: pure frontend/website work that never touches CLO, the worker, or the pipeline (design, auth flows, profile pages, most UI work).

To do this safely:
1. **Assign file ownership per task before starting**, not after. A few files sit on the boundary between "website work" and "CLO work" (e.g. `avatars/service.py` is backend code but feeds the pipeline) — decide up front which agent owns which file so two agents never edit the same file in the same window.
2. **Use isolated git worktrees for parallel agents** (the `Agent` tool's `isolation: "worktree"` option). Each agent gets its own checkout/branch; merge back once done. This makes file-ownership mistakes non-destructive instead of silently clobbering another agent's work.
3. Respect sequencing even across "parallel" work — some website work depends on CLO-agent output landing first (e.g. anything that loads/displays a GLB depends on Step 6 existing). See `02-remaining-work.md` for what depends on what.

## Standing rules carried over from the previous session (still in force)

- **Never read `.env*` files with any tool, for any reason.** Ask the user to paste/handle values themselves. This is enforced at the harness level too — Read/Grep/Glob against `.env*` files will be silently denied or return empty; that's expected, not evidence the file is missing.
- **Python dependencies**: only ever installed into the repo-root `.venv/`, recorded in root `requirements.txt` (or `website/backend/requirements-docker.txt` for the slimmed Docker-only subset — keep both in sync manually, the Docker one is a curated subset of the root one).
- **Docker's backend container only bind-mounts `website/backend/src/`, not `scripts/`.** Editing a script (e.g. `smoke_e2e.py`) requires `docker compose build backend && docker compose up -d backend` before `docker compose exec backend python scripts/...` picks up the change — the running container otherwise silently uses the stale copy.
- **Plan before multi-file or architecturally significant changes.** Write a plan doc in this folder (numbered, next available number), get it reviewed, then execute. This isn't bureaucracy for its own sake — every time this was skipped this past session, real gaps got found only after the fact (the pipeline still reading the old measurements collection, the GLB export bug, etc.).
- **Verification discipline**:
  - Backend: `python -m py_compile` on every touched file, `python -c "from src.main import app"` import check, rebuild+restart the Docker backend, run the smoke test (`docker compose exec backend python scripts/smoke_e2e.py`).
  - Frontend: `npx tsc --noEmit`, `npx eslint src --max-warnings=0`, `npm run build`. When deleting a feature, grep the built `dist/` output for the feature's own strings/copy to confirm it's genuinely gone, not just unreachable via routing.
  - CLO-touching: an actual live run against running CLO3D + the worker. Nothing else counts as verification for this category.
- **Nothing in this repo has been committed yet this session** — everything is uncommitted work on the `saumy` branch. Check `git status` before any destructive git operation; never force-push or hard-reset without being asked.

## Known, load-bearing technical facts (don't rediscover these the hard way)

- **Windows can't fork** — the worker uses `rq.worker.SimpleWorker`, never the default `rq.Worker`. Already implemented; don't "simplify" it back.
- **CLO's `/export` endpoint cannot produce true binary `.glb` on this installed CLO version.** `ExportGLB` is an unimplemented stub in this SDK version; `ExportGLTF` always writes JSON glTF-separate (external `.bin` + texture files) regardless of any binary flag — confirmed by reading the plugin's own C++ source, not assumed. The fix is entirely Python-side: `clo_avatar_generation/avatar_runtime/step_12_export_glb.py` packs the raw export into a real self-contained binary `.glb` via `pygltflib` afterward. Don't try to fix this at the plugin/CLO level — already investigated, not possible on this CLO version.
- **`dev_upload/` vs `live_upload/`** is controlled by `APP_ENV`, read directly from the worker process's own environment (`worker/.env`). `development` (default, unset included) → `dev_upload/`; `production` → `live_upload/`. `live_upload/` is reserved for real production data only — never write test/dev output there.
- **`measurements` vs `user_measurements`**: `measurements` (old collection) is now CLI/dev-fixture-only — `golden_users`/`seed_measurements.py`, and the CLO pipeline's own CLI-invoked reads. `user_measurements` (new collection) is the only thing the website itself writes to, dev and production alike. **Known, deliberate, still-open gap**: the CLO pipeline's own live fetch (`clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`) still reads the *old* collection — this is item 1 in `02-remaining-work.md`, not yet fixed.
- **No demo/live engine mode exists anymore.** Removed entirely. Every avatar/try-on request always goes through the real Redis → worker → CLO3D path. Don't reintroduce a mode flag or fake timers.
- **No frontend mock mode exists anymore.** `VITE_INTEGRATION_MODE`/`mocks/` deleted. The frontend always talks to a real backend; `npm run dev` alone (no backend running) only renders the marketing pages correctly.

## Workflow for every new piece of work

Same pattern this whole project has used, not a new process:

1. **Before touching code**, write a new numbered plan file in this folder (next available number) describing what's about to change, why, and which files it'll touch. For anything CLO/worker-adjacent or multi-file, this is not optional — every time it was skipped, a real gap got found only after the fact instead of before.
2. **Do the work.**
3. **After finishing, write back into that same plan file** what was actually done, what was verified and how, and anything found along the way that didn't match the plan. Don't just mark it "done" — the execution-log detail is what makes this folder trustworthy for the next person/agent instead of just aspirational.
4. **Update `02-remaining-work.md`** — move the item from open to done (with a date and a pointer to the plan file), and add anything newly discovered while doing the work.

## The old folder is not reliable as a status source by itself — verify against the actual code

`.agent/website-launch/` (23 docs) accumulated across many sessions, and **several docs are now stale relative to what actually happened later.** Concrete example found while setting this folder up: `06-avatar-vto-implementation-status.md` still describes Steps 4, 5, and 6 as "remaining" — but Steps 4 and 5 were actually built, live-tested against real CLO3D, and verified in later docs (11, 12) that doc 06 was never updated to reflect. Doc 06's own "Suggested build order" and step-by-step status is therefore **wrong today**, even though nothing about the doc itself looks obviously outdated.

The rule this implies: **a doc saying something is "planned" or "remaining" is a starting hypothesis, not proof.** Before treating any item in `02-remaining-work.md` (or any old doc) as actually not-done, grep/read the real code first — check whether the file it describes already exists, already does the thing, or was already fixed in a later doc that doesn't cross-reference back to update the earlier one. This project's docs are append-only execution logs, not a live-updated single source of truth — the truth is the code; the docs are a trail explaining *why* the code is the way it is.

## Where things live

- `.agent/website-launch/` — old planning docs, 01-23, historical record. Treat status claims here as needing a code cross-check, not as current fact.
- `.agent/website-launch-2/` (this folder) — current, trustworthy entry point. Add new numbered docs here as work continues; keep `02-remaining-work.md` up to date as items complete or new ones are found.
