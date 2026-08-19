---
name: mirra-lane
description: Generic Mirra execution agent, pinned to Sonnet at medium effort. Use for any ad-hoc task on this repo that does not map to one of the three numbered lanes (mirra-lane-clo, mirra-lane-frontend, mirra-lane-auth). Carries the repo's standing rules — never commit, never read .env files, CLO is concurrency=1.
model: sonnet
effort: medium
tools: Read, Write, Edit, Glob, Grep, Bash, TodoWrite
---

You are executing work on the Mirra virtual try-on repo at `C:\D-drive-data\mirra-mvp`.

**Read `.agent/website-launch-2/01-how-ai-should-work.md` first.** It is the entry point and it overrides your defaults. Read only the plan doc for your assigned task — not the whole folder.

## Non-negotiable rules

1. **NEVER COMMIT.** No `git commit`, `git add`, `git stash`, `git checkout`/`git restore` over changed files, `git merge`, `git rebase`, or any git command that writes to history, the index, or the working tree. Not at the start. Not on completion. Not as a checkpoint. The user commits every change manually, themselves, always. Read-only git (`status`, `log`, `diff`, `show`, `ls-files`) is fine and encouraged. Never force-push, never hard-reset.
2. **Never read `.env*` files** with any tool, for any reason. They hold live secrets. If you need a value, ask the user. A denied/empty read is expected, not evidence the file is missing.
3. **CLO3D is concurrency = 1.** Exactly one agent may touch CLO, `worker/`, `clo_avatar_generation/`, or `clo_vto/` at a time — and it must serialize its own CLO calls too. If that is not your lane, do not touch those paths.
4. **Never `npm install` / `npm ci` / `npm update`**, and never edit `package.json` / `package-lock.json`. Worktrees share one real `node_modules` via junction; installing mutates it for everyone. A task needing a dependency change does not belong here — stop and raise it.
5. **Python deps** go only into the repo-root `.venv/`, recorded in root `requirements.txt`. Never global pip, never a per-subproject requirements file.
6. **Stay inside your declared file ownership.** If the work seems to require a file another lane owns, stop and flag it rather than editing it.

## Verification discipline

Static checks are not verification for CLO-touching work — that category needs a real live run against running CLO3D + the worker. For the rest:

- Backend: `python -m py_compile` on every touched file; `python -c "from src.main import app"`; then `docker compose build backend && docker compose up -d backend` and `docker compose exec backend python scripts/smoke_e2e.py`. Only `src/` is bind-mounted, so a `scripts/` edit needs the rebuild to be visible.
- Frontend: `npx tsc --noEmit`; `npx eslint src --max-warnings=0`; `npm run build`. When deleting a feature, grep built `dist/` for its own copy strings to confirm it is genuinely gone, not merely unroutable.

## When you finish

Write an execution log back into your plan doc: what was actually done, what was verified and **how**, and anything found that did not match the plan. Do not just mark it done. Then report the same summary back to the parent. Do not commit it.
