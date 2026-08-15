# 05 — Lane 2 (website): delete `/onboarding` entirely, consolidate on `/profile`

**Status**: planned, not started. Written 2026-08-15.
**Covers**: `02-remaining-work.md` items **B1, B2 (revised — see below), B5**, plus a dead-route bug the doc did not capture.
**Agent assignment**: one agent, **isolated worktree**. Touches no CLO, no worker, no pipeline, no backend.

## The product decision driving this (user, 2026-08-15)

- `/studio` is for **showing the VTO**.
- `/profile/measurements` is for **taking measurements**.
- **The `/onboarding` pages are to be deleted completely.** Not redirected, not kept as aliases — deleted. Everything lives under `/profile`.

This supersedes `02-remaining-work.md`'s B2, which framed the task as "decide whether Continue should go to `/studio` instead." That framing was wrong on the facts anyway (see next section).

## The bug `02-remaining-work.md` got wrong

B2 claims Continue goes to `/profile/measurements`. It does not. Verified in code 2026-08-15:

- `router.tsx` registers exactly one onboarding route: `/onboarding/avatar` (line 54). **`/onboarding/measurements` and `/measurements` do not exist** — both pages were deleted in the current uncommitted `user_measurements` work.
- `pages/onboarding/Avatar.tsx` still navigates to both of them, from three live call sites:
  - **line 207** — the "Add measurements" button in the `measurements-required` phase. This is the *first screen* a signed-in user with no measurements sees. The primary entry point into the product is a 404.
  - **line 169** — the "update measurements" button on the saved-avatar panel.
  - **line 226** — `SynchronizedState`'s post-generation Continue (`goToMeasurements`, defined line 98).

All three fall through to `<Route path="*">` → `NotFound`. `tsc` and eslint cannot catch this: route targets are string literals. This is a live broken-navigation bug, not a preference question — and deleting `/onboarding` fixes it by construction.

## Scope — the complete `/onboarding` reference list (verified, exhaustive)

Delete:
- `src/pages/onboarding/Avatar.tsx` (241 lines) — the only remaining onboarding page.
- `src/router.tsx:19` (the lazy import) and `:54` (the route).

Repoint:
- `src/pages/Studio.tsx:65` — redirects avatar-less users to `/onboarding/avatar`; becomes `/profile/avatar`.
- The login `next=` param currently pointing at `/onboarding/avatar` (`Avatar.tsx:49`) — moves with the migrated code, targeting `/profile/avatar`.

Migrate into `/profile/avatar`, do not rewrite from scratch:
- `src/features/onboarding/components/generation-progress.tsx` (this is B5 — the doc asks for exactly this reuse)
- `src/features/onboarding/components/synchronized.tsx`

Leave alone (already correct, already used by `/profile/measurements`):
- `src/features/onboarding/components/measurement-row.tsx`, `measurement-form.tsx`

Cosmetic, do last if at all: `src/styles/globals.css:6` has a comment listing "auth/onboarding/studio/profile" routes. `src/pages/Pricing.tsx:71` says "White-glove onboarding" — that is marketing copy about customer onboarding, **not** a route. Do not touch it.

**Judgment call to make and record**: the folder `src/features/onboarding/` survives this, still holding four components, two of which `/profile/measurements` depends on. Leaving a folder named `onboarding` after deleting the onboarding concept is a half-deletion. Recommend renaming it to `src/features/profile/` and updating the four import sites. Do this as the **last** step, in its own pass, so a rename conflict never obscures the functional work.

## The real work: `ProfileAvatar.tsx` absorbs the generation flow

`pages/profile/ProfileAvatar.tsx` today (verified) has, when no avatar exists, static leftover copy from the **deleted photo-capture feature** — "One is created the next time you complete a photo session" — and **zero buttons**. That's B1's dead end, and it's also now the only place the generation flow can live.

`onboarding/Avatar.tsx` runs a phase machine: `checking` → `decision` / `measurements-required` / `generating` → `synchronized` / `failed`. That machine is the feature; it moves to `/profile/avatar` largely intact. New wiring:
- `measurements-required` → "Add measurements" navigates to **`/profile/measurements`** (a route that exists).
- `synchronized` Continue → **`/studio`**, per the user's decision that Studio is where the VTO is shown. This is the genuinely new destination, and the reason the old Continue target was never coherent.
- `decision` phase's "Use my saved avatar" → `/studio` (already correct at `Avatar.tsx:160`; note this contradicts B1's claim that nothing links to Studio — `/onboarding/avatar` does. What's actually true is that nothing under `/profile/*` does, which this fixes).
- Preserve the existing regenerate action and the explicit save/regenerate separation. **Do not** add an auto-trigger on measurement save — that's B3, deliberately deferred, because CLO is concurrency=1 and every trigger is a real ~90s run.

### Layout: decided 2026-08-15 — stay inside `ProfileLayout`

`/profile/avatar` renders inside `ProfileLayout` — a `max-w-3xl` shell with a tab bar and sign-out header (`ProfileLayout.tsx:31-66`). The generation flow is currently full-screen and centered with animated phase transitions. **Decision: adapt the phases to the panel. Do not build a layout escape hatch.**

Why: `/profile/avatar` is a profile sub-page, and breaking out of the shell mid-route strands the user with no nav and no consistent way back. It's also strictly less code — no escape mechanism to build, and none to maintain when the profile chrome changes. Let the panel run full-width inside the `max-w-3xl` shell during `generating`/`synchronized`, and convert the phase animations from full-screen centering to panel centering. Keep the animations; they're the flow's character, and they work fine at panel scale.

**One hazard this creates, and the cheap mitigation.** Keeping the tab bar visible during a ~90s run invites the user to navigate away — and job ids currently live only in local component state, so leaving the page loses track of the run entirely. That's B4, which is deliberately deferred and *not* in this lane's scope. Until B4 lands, the `generating` state must say so plainly in the UI — something to the effect of "this takes about 90 seconds; leaving this page will lose track of the run." That's honest, costs nothing, and stops this decision from quietly shipping a trap. Do not attempt to fix the underlying state persistence here; flag it and move on.

Also note `ProfileLayout.tsx:24-26` runs its own inline auth guard. That duplication is B6 (`RequireAuth`), sequenced **after** this lane precisely because it rewrites these same files. Do not do B6 here.

## Verification

- `npx tsc --noEmit`
- `npx eslint src --max-warnings=0`
- `npm run build`
- `grep -rn "onboarding" src/` — should return only `features/onboarding/` paths (or nothing, if the rename happened) and the Pricing marketing string. **No route, navigate, or import referencing `/onboarding` may survive.**
- Per `01`'s deletion rule: grep the built `dist/` output for the deleted page's own copy strings to confirm it's genuinely gone, not merely unroutable.
- Click through by hand: signed-in user with no measurements → `/profile/avatar` → "Add measurements" → lands on `/profile/measurements` (not a 404). Then measurements saved → generate → progress → Continue → `/studio`. And `/studio` with no avatar → redirects to `/profile/avatar`.

## Rules for this lane

- **Never commit.** Not on completion. The user commits manually, including merging this worktree back. See `01-how-ai-should-work.md`.
- Owned files: `src/pages/onboarding/**` (deleting), `src/pages/profile/ProfileAvatar.tsx`, `src/pages/Studio.tsx`, `src/router.tsx`, `src/features/onboarding/**`.
- **Do not touch** `src/pages/auth/**` or `src/pages/profile/ProfileMeasurements.tsx` — Lane 3 owns the auth pages, and ProfileMeasurements is mid-flight uncommitted work.
- No backend changes. If something here seems to need a new API surface, that's B4 — stop and flag it rather than adding a route.

## Execution log

*(To be written after the work, per `01`'s workflow step 3.)*
