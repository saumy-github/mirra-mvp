# 07 — Landing redesign: open follow-ups (for discussion with Madhavan)

**Status**: parked, deliberately unassigned. Written 2026-08-19.
**Owner**: the user, to discuss with Madhavan and decide. **No agent or lane touches any of this.**

## Why this file exists

The landing redesign merged on 2026-08-19 (squash of `origin/Madhavan`, already on `origin/main` @ `4f1d7b1`). Reviewing it turned up a handful of loose ends. **None of them are being fixed now.** The user's call, 2026-08-19: *"today we are focused on the working of website and not on the cosmetics of the landing page."*

They are recorded here so they are not silently lost, and so that no future agent "helpfully" fixes them mid-lane and muddies someone else's diff.

**Nobody touches these files this window**: `src/features/marketing/**`, `src/pages/{Home,Pricing,FAQ}.tsx`, `index.html`, `public/**`. This is recorded as an unowned zone in `01-how-ai-should-work.md`.

## The migration itself is sound — this is a punch list, not a complaint

Worth stating plainly, since the list below reads as negatives. Verified 2026-08-19:

- `npx tsc --noEmit`, `npx eslint src --max-warnings=0`, and `npm run build` all pass clean.
- Every dependency the new code imports (`motion`, `gsap`, `gsap/Draggable`, `lenis`) was already in `package.json`. No dependency change was needed.
- **The CSS scoping is real, not merely claimed.** All 8,622 lines of `marketing.css` are nested under `.mirra-landing`, and the redesign's `:root` variables were rewritten as `.mirra-landing` custom properties. The only global escape is a documented `html.lenis` height rule. The app routes cannot be reached by this stylesheet — this was the highest-risk part of the port and it was done properly.
- Only one Lenis instance exists, deliberately, with a comment explaining that two would fight and that Studio's own scroll containers must never be touched.
- The `.gitignore` negations are correct: the repo ignores `**/*.svg` globally for pipeline output, and without the targeted `website/frontend/**` exceptions the brand-logo strip and favicon would have built locally and 404'd in production. Good catch on his part.
- No dead links to the retired `/meet-the-team` survive.

## The open items

### 1. The client-logo strip implies customers Mirra does not have — **decide this one first**

`src/features/marketing/content.ts` (`MIRRA_TRUST`, ~L97-103) renders **14 template client logos** under `brandsLabel: "Trusted by fashion brands"` and `brandLogosAriaLabel: "Fashion brands using Mirra"`. The logos are real company wordmarks carried over from the MWG template — they are not Mirra customers.

This is the only item on the list with exposure beyond taste: presenting third-party marks as customers is a false-endorsement and trademark problem, and it is on the homepage.

Options: swap in real customers, drop the strip until there are some, or relabel it honestly as something other than a customer list.

**Same block**: `peopleLabel: "Used by X+ people"` — the literal placeholder `X+` is shipping live.

### 2. Commercial fonts served as public `.woff`

`public/mwg/` serves `PPNeueMontrealMono-Medium.woff` (Pangram Pangram) and three `LayGrotesk` weights, unauthenticated. Both are paid licenses, and webfont serving is typically a separate tier from a desktop license.

Question for Madhavan: what license was the standalone redesign built under, and does it cover webfont delivery on a production domain? If not, these need swapping or licensing.

### 3. `favicon.svg` and `og-mirra.png` were added but never wired up

`index.html` has no `<link rel="icon">` and no OG/Twitter meta tags. So the favicon never applies and 1.27 MB of social-preview image ships as dead weight while link previews stay blank.

Cheap and mechanical — a few lines in `index.html`. It was missed because `index.html` sits outside the migration's own declared blast radius (`website/MIGRATION.md` lists the in-scope paths and `index.html` is not among them), which is a reasonable way to miss it.

### 4. ~10.4 MB of now-dead tracked assets

- `public/leberch-ethereal-cinematic-512569.mp3` — **10.2 MB**. Background audio for the old marketing layout's sound toggle. That player was deleted with `Header`/`CustomCursor`; nothing references the file.
- `public/Footer-Mirra.jpeg` — 165 KB, likewise orphaned.

Both are tracked, so deleting them shrinks the working tree but not history.

Worth a sanity check before deleting: confirm Madhavan has no plan to reintroduce the audio.

### 5. Asset weight generally

76 binary assets, **17.5 MB** total, including 18 `.mp4` files served from `public/`. Fine for a pilot; worth revisiting before real traffic (a CDN, or at least checking what the homepage actually pulls on first paint). Not urgent, listed for completeness.

## What to do with this file

When the decisions are made, either fold them into a numbered plan doc and assign a lane, or delete this file. Do not let it drift into a stale to-do list — `01`'s standing warning about append-only docs applies here too.
