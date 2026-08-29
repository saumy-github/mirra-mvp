# 05 — Lane 2 (website): delete `/onboarding` entirely, consolidate on `/profile`

**Status**: planned, not started. Written 2026-08-15.
**Covers**: `02-remaining-work.md` items **B1, B2 (revised — see below), B5**, plus a dead-route bug the doc did not capture.
**Agent assignment**: one agent — `subagent_type: mirra-lane-frontend` (Sonnet, medium effort). Runs in the **main checkout**, in parallel with Lanes 1 and 3, kept apart by file ownership alone. Touches no CLO, no worker, no pipeline, no backend.

> **Line numbers in this doc predate the landing-redesign merge (2026-08-19).** That merge rewrote `pages/Home.tsx`, `pages/Pricing.tsx`, `router.tsx`, and all of `features/marketing/`, and retired `/meet-the-team` in favour of `/faq`. **Re-locate every reference below by searching for the code, not by trusting the line number.** The `router.tsx` references (`:19`, `:54`) and `Pricing.tsx:71` are the ones most likely to have moved. The *substance* of this plan is unaffected — the merge touched only the marketing surface, which this lane does not own.

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

> **Contradiction resolved 2026-08-19 — read this before doing the rename.** The rule below says do not touch `ProfileMeasurements.tsx`, but that file imports `measurement-row.tsx`/`measurement-form.tsx` from `features/onboarding/`, so the rename *cannot* happen without editing its import line. Both cannot be true. The resolution: **the rename is permitted to change import statements in `ProfileMeasurements.tsx`, and nothing else in it.** No logic, no JSX, no formatting — one import path, mechanically. If the rename turns out to need more than that, **skip the rename entirely** and record why; it is cosmetic and not worth risking mid-flight work over. The original reason for the restriction was that `ProfileMeasurements.tsx` held uncommitted work; that work is committed as of 2026-08-19, which lowers the stakes but does not make the file yours to redesign.

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
- **Do not touch** `src/pages/auth/**` — Lane 3 owns the auth pages this window. `src/pages/profile/ProfileMeasurements.tsx` is likewise not yours, with the single narrow exception carved out above: the folder rename may update its **import path only**.
- **Do not touch `src/features/marketing/**`, `src/pages/{Home,Pricing,FAQ}.tsx`, or `index.html`** — the landing redesign landed 2026-08-19 and has open follow-ups of its own. `router.tsx` is yours, but only the auth/app/profile route block; leave the marketing routes (`/`, `/pricing`, `/faq`) and the `MarketingLayout` wrapper exactly as they are.
- **Shared resources**: you own `npm run build` and `dist/`. You do **not** own Docker (Lane 1 does) — never run `docker compose build/up/down/restart`. The Vite dev server on port 3000 is one-at-a-time; Lane 3 may also want it, so check before starting one and stop it when done.
- No backend changes. If something here seems to need a new API surface, that's B4 — stop and flag it rather than adding a route.

## Execution log

**Done 2026-08-19, Lane 2 (`mirra-lane-frontend`).** All of B1, B2-revised, B5 completed as planned. No backend/CLO/worker files touched, no `docker` commands run, no git writes.

### What was done

1. **Deleted `/onboarding` entirely.**
   - Removed `src/pages/onboarding/Avatar.tsx` and its folder.
   - Removed the lazy import and the `<Route path="/onboarding/avatar">` from `src/router.tsx`. Left the marketing routes (`/`, `/pricing`, `/faq`), `MarketingLayout`, and every other route in the auth/app/profile block untouched — only the onboarding import/route lines were removed.

2. **Repointed the two dead-link call sites** (the actual bug doc 05 flagged, not a preference call):
   - `src/pages/Studio.tsx` — avatar-less redirect now goes to `/profile/avatar` instead of the 404ing `/onboarding/avatar`.
   - The generation flow's "measurements-required" CTA and the post-generation Continue now target `/profile/measurements` and `/studio` respectively (see next point) — both real routes, replacing the old `/onboarding/measurements`/`/measurements` targets that never existed.

3. **Migrated the generation phase machine into `src/pages/profile/ProfileAvatar.tsx`**, replacing its old dead-end ("no avatar" copy with zero buttons). Reused `GenerationProgress` and `SynchronizedState` from the components folder rather than rewriting them (this is B5). Behavioral changes from the old `onboarding/Avatar.tsx`:
   - `measurements-required` phase's "Add measurements" → `/profile/measurements` (was the 404ing `/onboarding/measurements`).
   - `synchronized` phase's Continue → `/studio` (was the 404ing `/measurements`, and per the user's product decision that Studio is where the VTO lives).
   - "Use my saved avatar" already went to `/studio` in the old code and still does.
   - Added the mitigation doc 05 calls for explicitly (since B4 — persisting job state across navigation — is out of scope for this lane): the `generating` phase now shows "This takes about 90 seconds. Leaving this page will lose track of the run." directly above `GenerationProgress`.
   - Kept the explicit save/regenerate separation; did not add any auto-trigger on measurement save (that's B3, deliberately deferred).
   - Adapted the phase transitions from full-screen `min-h-dvh` centering to panel-scale centering (`flex w-full justify-center` inside `ProfileLayout`'s existing `max-w-3xl` shell) per the "stay inside ProfileLayout" decision — no layout escape hatch was built. Kept the `AnimatePresence`/`motion` transitions, just re-scaled.
   - The existing saved-avatar view (figure, metadata, delete-with-confirm) was preserved essentially as-is; added "Use my saved avatar" and "Regenerate avatar" buttons to it since B1 was exactly this file having "zero buttons."

4. **Folder rename: `src/features/onboarding/` → `src/features/profile/`.** Did this — it did not need more than the exception doc 05 carved out. Moved the `components/` subfolder (all four files: `generation-progress.tsx`, `synchronized.tsx`, `measurement-row.tsx`, `measurement-form.tsx`) with `Move-Item`, no content changes to any of the four. Updated exactly two import sites, exactly one line change per file:
   - `src/pages/profile/ProfileAvatar.tsx` — both `@/features/onboarding/components/...` imports repointed to `@/features/profile/components/...`.
   - `src/pages/profile/ProfileMeasurements.tsx` — same, for its two imports (`MeasurementRow`, `MeasurementForm`). **This is the only change made to that file** — no logic, no JSX, no reformatting, confirmed by diff-equivalence of everything else in the file.
   - Did this rename before the final verification pass, per the sequencing instruction.

### What was verified, and how

- `npx tsc --noEmit` — clean, no output, exit 0.
- `npx eslint src --max-warnings=0` — clean, no output, exit 0.
- `npm run build` — succeeded (5.48s, 660 modules). Confirmed in the chunk list that no `Avatar-*.js` chunk exists anymore (the old onboarding page's chunk is gone) and `ProfileAvatar-*.js` now carries the generation-flow weight (15.19 kB, up from a trivial size before, consistent with it having absorbed the phase machine).
- `grep -rn "onboarding" src/` — six hits, all permitted: a CSS comment (`globals.css:6`), two `Pricing.tsx` marketing-copy strings ("Self-serve onboarding"/"White-glove onboarding" — customer-onboarding copy, not a route, untouched), and three prose comments in the new `ProfileAvatar.tsx` referencing the old route/feature name for context. **No route, `navigate(...)`, or import referencing `/onboarding` remains anywhere in `src/`.**
- Grepped the built `dist/` for `/onboarding` (any case) — zero matches, confirming the string is genuinely gone from shipped output, not merely unroutable. Also grepped for the old dead-end copy strings ("Preparing your fitting room", "One is created the next time you complete a photo session") — zero matches in `dist/`.
- Did not click through in a live browser (no dev server was started — Lane 3 might have needed port 3000, and this wasn't a blocking risk given the route/logic tracing below). Instead traced the three scenarios by reading the final code:
  1. Signed-in, no measurements → `/profile/avatar`: `avatar` resolves `null`/undefined → effect sets `phase="generating"` → `generate.mutate()` 404s → `phase="measurements-required"` → "Add measurements" button navigates to `/profile/measurements` (a real route, not a 404). Matches the exact bug doc 05 called out as broken.
  2. Measurements saved, then generation runs to completion → `job.state === "ready"` → `phase="synchronized"` → `SynchronizedState`'s auto-continue and its "Continue now" button both call `goToStudio` → `/studio`.
  3. `/studio` with no avatar → its existing guard effect now calls `navigate("/profile/avatar", { replace: true })` instead of the dead `/onboarding/avatar`.
  - **Flagging this as the one verification gap**: doc 05 asked for a hand click-through; this was done by static trace against the actual hook/mutation contracts (`useAvatarProfile`, `useGenerateAvatar`, `useAvatarJob`) rather than a running browser, because no backend/CLO run was available or in this lane's scope to trigger. If a live click-through is wanted, someone with access to a running backend + worker should do one pass through the three scenarios above.

### Judgment call: the `features/onboarding/` → `features/profile/` rename

Done, per doc 05's own recommendation, since the narrow-exception path held: `ProfileMeasurements.tsx` only needed its two import lines changed, nothing else. No skip was necessary.

### Where this diverged from the plan

Nothing substantive diverged. Two small implementation notes not spelled out in the plan:
- The old `onboarding/Avatar.tsx` had a `phase="checking"` state gating on `accountLoading` before deciding "decision" vs. "generating". `ProfileAvatar.tsx` didn't need an equivalent `checking` phase — `ProfileLayout` already blocks rendering its `<Outlet>` until `account` resolves (see `ProfileLayout.tsx`'s own `if (!account) return null`), so `ProfileAvatar` only ever mounts once auth is already settled. This also means `ProfileAvatar` no longer needs its own auth-guard redirect — `ProfileLayout`'s existing inline guard already covers it. (That guard's duplication is B6's territory, explicitly not touched here.)
- The old code's "decision" phase (separate full-screen "Welcome back" card offering "Use my saved avatar" / "Review measurements" / "Regenerate avatar" for users who already have an avatar) is superseded by the pre-existing saved-avatar panel view in `ProfileAvatar.tsx` — that view already showed the avatar's metadata and a delete action; B1 was exactly that it had no other buttons. Rather than layering the old decision card on top, "Use my saved avatar" and "Regenerate avatar" were added directly to the existing panel view, since a `/profile/avatar` visit for a user who already has an avatar is naturally "here's your avatar" rather than a fresh decision prompt. Net effect is the same set of actions, presented in the panel's existing style instead of a re-introduced full-screen card (which the "stay inside ProfileLayout" decision ruled out anyway).
