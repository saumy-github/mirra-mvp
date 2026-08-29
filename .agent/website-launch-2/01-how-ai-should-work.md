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

### Launching subagents: Sonnet at medium effort, and where they can actually write

**Every subagent on this repo runs Sonnet at medium reasoning effort.** User instruction, 2026-08-15. The user reserves Opus for their own chats and pays for subagent tokens separately, so an Opus subagent is a real and unwanted cost.

**This is now mechanically enforced. Use the agent definitions in `.claude/agents/` — do not launch lanes as `general-purpose`.** Created 2026-08-19:

| `subagent_type` | Lane | Plan doc | Territory |
|---|---|---|---|
| `mirra-lane-clo` | 1 | `04` | CLO, `worker/`, `clo_avatar_generation/`, `clo_vto/`, backend avatars + Docker. **Holds the CLO lock — never run two.** |
| `mirra-lane-frontend` | 2 | `05` | `/onboarding` deletion, `ProfileAvatar.tsx`, `Studio.tsx`, `router.tsx`, `features/onboarding/`. Owns `npm run build`/`dist/`. |
| `mirra-lane-auth` | 3 | `06` | `pages/auth/**`, backend `auth/` + `users/routes.py`. |
| `mirra-lane` | — | (assigned) | Generic fallback for ad-hoc work that maps to none of the above. |

Each file pins `model: sonnet` and `effort: medium` in its frontmatter, and restates the non-negotiables inline (never commit, never read `.env*`, CLO concurrency=1, never `npm install`, file ownership) so a lane agent carries them even if it skims this doc.

- **Model**: also pass `model: "sonnet"` explicitly on the `Agent` call as a belt-and-braces measure. Omitting it on a `general-purpose` launch makes the subagent **inherit the parent's model** — on an Opus session that silently launches Opus agents. Omission is not a neutral default here, it is the wrong default.
- **Effort**: `effort` is a real frontmatter key — confirmed 2026-08-19 against shipped agent definitions in the official plugin marketplace (e.g. `claude-security/agents/explore.md` uses `model: sonnet` + `effort: xhigh`). The `Agent` **tool** still has no effort parameter, so the definition file is the only way to set it. That is why lanes must be launched by `subagent_type`, not as `general-purpose` with a model override — the latter sets the model and silently inherits effort.

Because the plan docs (`04`, `05`, `06`) carry the detailed, pre-verified context, Sonnet at medium is a reasonable fit: the hard thinking is already written down, and the lanes are execution against a specific plan rather than open-ended design.

**Keep the agent files in sync.** If a rule in this doc changes — a new standing constraint, a change to file ownership, a lane's scope shifting — update the corresponding `.claude/agents/*.md` too. A lane agent reads its own definition first and reads `01` second; a rule that lives only here can be missed under a tight context budget.

**Hand-rolled git worktrees outside the project root do not work.** Confirmed the hard way 2026-08-15: worktrees were created at `C:\D-drive-data\mirra-worktrees\...`, agents were pointed at them, and the agent died immediately — *"writes outside the main project root are blocked by default."* The permission layer sandboxes agents to the main project root. Creating the worktree succeeds; the agent simply cannot write in it. Two options that do work:

1. **Run every lane in the main checkout** (`C:\D-drive-data\mirra-mvp`) with **strictly disjoint file ownership assigned up front**. This is the simpler path, and it has a real bonus: all work lands directly in the user's own `git status` as one reviewable diff, with no copy-back step. Given the user commits everything manually, this matches how they actually work.
2. Use the `Agent` tool's own `isolation: "worktree"` option, which creates a worktree the harness knows about and permits. Note the agent will then need to create the `node_modules` junction itself as its first step (see below), since a fresh worktree has none.

**When several lanes share the main checkout, assign the shared, stateful things to exactly one owner each** — otherwise concurrent agents clobber each other even with disjoint source files:
**User decision, 2026-08-19: every shared resource is operated by the orchestrating (parent) session, not by any lane.** A lane that needs one *asks and waits*. This is the safe version, chosen deliberately over letting lanes self-serve.

- **Docker lifecycle** (`build`/`up`/`down`/`restart`, ports 8000/6379) → **parent only**. **No lane runs `docker compose build/up/down/restart`, including Lane 1.** A restart mid-way through Lane 1's live CLO run corrupts that run, and a lane cannot know what the other two are doing. `docker compose exec` against an already-running stack is read-only and permitted.
- **The CLO plugin rebuild** → **parent only.** No lane rebuilds the plugin.
- **`npm run build` / `dist/`** → one frontend lane only (Lane 2), and **only the repo's own `website/frontend/dist/`** — see the dist rule below.
- The Vite dev server (port 3000) → one at a time, arranged through the parent. Beyond the port, concurrent servers corrupt each other's `node_modules/.vite` dep-optimization cache.
- **`website/backend/scripts/smoke_e2e.py`** → Lane 1 owns the *file*; other lanes may *run* it but never edit it.
- `npx tsc --noEmit` and `npx eslint` write nothing, so they are safe from any lane at any time.

### The dist rule: this repo's `dist/` and no other

`npm run build` and every `dist/` check mean **`C:\D-drive-data\mirra-mvp\website\frontend\dist\`** — the build output of *this* repo, and nothing else. Never build, read, or grep a `dist/` belonging to another checkout, another clone, the standalone landing redesign, or any path outside this repo. When a plan says "grep the built `dist/` output", it means this one. If the path you are about to touch is not under the project root, stop.

### Comments: one line, only where the code is not self-explanatory

**User instruction, 2026-08-19.** Agents on this repo have been writing long explanatory comment blocks that nobody asked for and nobody needs.

The rule:

- **One line.** Not a paragraph, not a multi-line block, not a rationale essay above a function.
- **Only where the code is genuinely not self-explanatory.** If a reader can see what the line does by reading it, it gets no comment. Most code needs none.
- Comment the **non-obvious why**, never the **what**. `// increment counter` above `count++` is noise. `// CLO returns half-girth, not circumference` earns its place.
- Do not narrate your own work in code comments — no "changed 2026-08-19", no "per doc 05", no explaining what you were asked to do. That belongs in the execution log, which is what the plan docs exist for.
- Do not leave commented-out code with an explanation of why it is commented, beyond one short line.

This applies to the code you write. Do not go reformatting unrelated existing comments.

### Verification runs once, at the end — not after every edit

**User instruction, 2026-08-19.** `npx tsc --noEmit`, `npx eslint src --max-warnings=0`, `npm run build`, `py_compile`, and the smoke test are **end-of-work checks**, run once after all the changes for that lane are complete. Do not run them after each small edit.

Why it matters here beyond wasted time: three lanes share one checkout and one `node_modules`. A lane that rebuilds after every edit multiplies contention on `dist/` and the Vite cache, and floods its own context with output it will only act on at the end anyway. Make the whole change, then verify it.

The exception is a genuine debugging loop — if a check fails and you are iterating on that specific failure, re-run it as needed until it passes. That is diagnosis, not routine checking.

**Unowned this window — nobody touches these:** `src/features/marketing/**`, `src/pages/{Home,Pricing,FAQ}.tsx`, `index.html`, `public/**`. The landing redesign merged 2026-08-19 and has open follow-ups (unwired favicon/OG tags, ~10 MB of dead assets, placeholder client logos) that are deliberately **not** assigned to a lane.

### Worktree setup on Windows — junction `node_modules`, and the things a worktree silently lacks

**Only relevant if using harness-managed worktrees (`isolation: "worktree"`) — see the note above about hand-rolled ones being unwritable.**

A git worktree checks out **tracked files from a commit only**. Everything untracked is missing, and on this repo the untracked things are load-bearing. Set every worktree up like this, and **tell every subagent working in one to use it** — this is not optional, it's how we avoid burning ~330 MB per agent.

**1. Junction `node_modules` instead of running `npm install`.** `website/frontend/node_modules` is ~327 MB and untracked; the tracked working tree is only ~15 MB. A Windows directory junction makes the worktree share the main checkout's copy at near-zero disk cost:

```powershell
New-Item -ItemType Junction `
  -Path   "<worktree>\website\frontend\node_modules" `
  -Target "C:\D-drive-data\mirra-mvp\website\frontend\node_modules"
```

Run it right after creating the worktree, before any `npx`/`npm` command. Then `npx tsc --noEmit`, `npx eslint`, and `npm run build` all work immediately.

- **Hard rule that makes the junction safe: a junctioned worktree must never run `npm install`, `npm ci`, `npm update`, or edit `package.json`/`package-lock.json`.** All worktrees share one real `node_modules`; installing in any of them mutates it for everyone, including the main checkout. If a task genuinely needs a dependency change, that task does not belong in a junctioned worktree — stop and raise it.
- Only the **frontend** needs this. The backend is Python/FastAPI with no `node_modules` and no `package.json`.
- Junctions are removed with `Remove-Item <path>` (or `cmd /c rmdir`), which deletes the link, not the target. Do not `Remove-Item -Recurse` a junction — depending on the tool that can walk into the target and delete the real `node_modules`.

**2. The repo-root `.venv/` is also untracked** and will not exist in a worktree. Python work in a worktree can therefore only do static checks against the main checkout's interpreter, or defer verification to after merge-back.

**3. `.env*` files are untracked and will not exist in a worktree.** As of 2026-08-15 the repo has these (names only — never read their contents): root `.env.dev`; `clo_workspace/.env`; `mirra_measurements/.env`; `website/backend/.env.dev`, `.env.docker.dev`; `website/frontend/.env.dev`, `.env.development`; `worker/.env`. A worktree gets none of them. **Ask the user to copy whichever a lane actually needs — never read one to find out what's in it, and never reconstruct one from guesses.**

**4. Port conflicts are real — assume collision, not luck.** Ports in use: **backend 8000** and **Redis 6379** (`docker-compose.yml`), **Vite dev server 3000** (`website/frontend/vite.config.ts:14`).
- `docker compose` derives its project name from the directory, so a worktree spawns a *second* stack that immediately fights the main one for 8000/6379. **Only one checkout runs Docker — the main one.** A worktree lane needing backend verification either uses the main checkout's already-running backend, or defers Docker verification to after merge-back. It must not `docker compose up` from inside a worktree.
- **Only one Vite dev server at a time.** Beyond the port, concurrent dev servers sharing a junctioned `node_modules/.vite` cache can corrupt each other's dep-optimization cache. `tsc`, `eslint`, and `build` are safe to run concurrently; `npm run dev` is not.

**5. Merging work back without committing.** Agents never commit (see the standing rules). To get parallel work into the main checkout as one reviewable diff: confirm each worktree's changed-file list stays inside that lane's declared ownership, then **copy those files into the main checkout**. This is safe only because lanes are assigned strictly disjoint file sets up front — that assignment is what makes a plain copy equivalent to a merge, with no conflict resolution and no commits anywhere. If an agent touched a file outside its ownership, stop and show the user rather than copying.

## Standing rules carried over from the previous session (still in force)

- **Never read `.env*` files with any tool, for any reason.** Ask the user to paste/handle values themselves. This is enforced at the harness level too — Read/Grep/Glob against `.env*` files will be silently denied or return empty; that's expected, not evidence the file is missing.
- **Python dependencies**: only ever installed into the repo-root `.venv/`, recorded in root `requirements.txt` (or `website/backend/requirements-docker.txt` for the slimmed Docker-only subset — keep both in sync manually, the Docker one is a curated subset of the root one).
- **Docker's backend container only bind-mounts `website/backend/src/`, not `scripts/`.** Editing a script (e.g. `smoke_e2e.py`) requires `docker compose build backend && docker compose up -d backend` before `docker compose exec backend python scripts/...` picks up the change — the running container otherwise silently uses the stale copy.
- **Plan before multi-file or architecturally significant changes.** Write a plan doc in this folder (numbered, next available number), get it reviewed, then execute. This isn't bureaucracy for its own sake — every time this was skipped this past session, real gaps got found only after the fact (the pipeline still reading the old measurements collection, the GLB export bug, etc.).
- **Verification discipline**:
  - Backend: `python -m py_compile` on every touched file, `python -c "from src.main import app"` import check, rebuild+restart the Docker backend, run the smoke test (`docker compose exec backend python scripts/smoke_e2e.py`).
  - Frontend: `npx tsc --noEmit`, `npx eslint src --max-warnings=0`, `npm run build`. When deleting a feature, grep the built `dist/` output for the feature's own strings/copy to confirm it's genuinely gone, not just unreachable via routing.
  - CLO-touching: an actual live run against running CLO3D + the worker. Nothing else counts as verification for this category.
- **NEVER COMMIT. This rule is absolute and has no exceptions.** No agent or subagent may run `git commit`, `git add`, `git stash`, `git checkout`/`git restore` over changed files, `git merge`, `git rebase`, or any other git command that writes to history, the index, or the working tree. Not at the start of work. Not on completion. Not "just a checkpoint before something risky." Not even when a subagent finishes its task and the work looks obviously done. **The user commits every single change manually, themselves, always.**
  - If some piece of work appears to *require* a commit before it can proceed — the common case being "a git worktree can only branch from a commit, and the work it needs is uncommitted" — **stop and ask the user to commit it**. Do not commit on their behalf to unblock yourself.
  - Read-only git is fine and encouraged: `git status`, `git log`, `git diff`, `git show`, `git ls-files`.
  - Never force-push and never hard-reset, under any circumstances, asked or not.
- The `saumy` branch is at any moment a mix of committed history and uncommitted working-tree changes (including untracked new modules). Run `git status` before assuming which — and remember that untracked files do **not** appear in a new worktree.

## Known, load-bearing technical facts (don't rediscover these the hard way)

- **Windows can't fork** — the worker uses `rq.worker.SimpleWorker`, never the default `rq.Worker`. Already implemented; don't "simplify" it back.
- **CLO's `/export` endpoint cannot produce true binary `.glb` with the SDK we currently build against.** `ExportGLB` is a bare stub (returns an empty vector) in that SDK's header; `ExportGLTF` always writes JSON glTF-separate (external `.bin` + texture files) regardless of any binary flag — confirmed by reading the plugin's own C++ source, not assumed. The fix is entirely Python-side: `clo_avatar_generation/avatar_runtime/step_12_export_glb.py` packs the raw export into a real self-contained binary `.glb` via `pygltflib` (`_pack_self_contained_glb`, using `convert_images(DATAURI)` + `convert_buffers(BINARYBLOB)`).
  - **Corrected 2026-08-15. The old claim "ExportGLB is an unimplemented stub, so this is impossible at the CLO level" rests on a misreading of the SDK header, and should not be repeated.** What is actually true, verified by reading `C:\Users\Saumy\Downloads\CLO_SDK_v2025.2.368_Win\CLOAPIInterface\include\ExportAPIInterface.h` directly:
    - **Every** export method in that header has an empty default body — `ExportOBJW` (L108), `ExportGLTF` (L118), `ExportGLTFW` (L128), `ExportGLB` (L608), `ExportGLBW` (L618), `ExportGLTFWithDialog` (L675), `ExportGLBWithDialog` (L685); `ExportBOMW` (L669) just returns `false`. This is an **abstract interface**: the SDK ships no-op defaults and the real implementations live in `CLOAPIInterface.dll`, overriding the virtuals at runtime.
    - The proof that an empty body means nothing: **`ExportGLTF` is a bare stub in this same header and our pipeline calls it successfully on every run.** So "stub body in the header" is not evidence of non-implementation, and never was.
    - The empirical fact still stands and is not in dispute: `ExportGLB` returned an empty result in real manual testing (`RestPlugin_windows.cpp:1774-1780`). Only the *explanation* was wrong.
    - **Leading hypothesis, untested**: vtable/ABI skew. We build against a 2025.2-line SDK header while running a 2026.0 app. With a pure-virtual interface, if CLO inserted or reordered virtuals between those versions, a call dispatches to the wrong slot — or falls through to the header's own empty default. Consistent with the observed split: `ExportGLTF` sits early in the class (L118) and works; `ExportGLB` sits far later (L608) and returns empty, which is exactly where accumulated vtable divergence would bite. If this is right, **rebuilding the plugin against a matching-line SDK may fix `ExportGLB` outright** — not because it was newly implemented, but because the vtable would line up. Testable, and cheaper than an app upgrade.
    - Practical consequence: keep the Python packing workaround (it works), but **do not record it as permanent or the CLO path as impossible.** See `03-clo-2026.1-upgrade-assessment.md`, whose Q1 conclusion is built on the same header misreading and should be read with this correction in hand.
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
