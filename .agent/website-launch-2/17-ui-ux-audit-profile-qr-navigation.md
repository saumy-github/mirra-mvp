# 17 - UI/UX audit: Profile layout, QR/phone capture, navigation

6 October 2026. Static audit (CSS + component code + backend pairing logic). **Not visually verified**: the Chrome extension was not connected, so nothing below was reproduced in a browser. Items marked *hypothesis* need a screenshot pass at 1280, 1100 and 390px. No application code was changed. Extends `16-signup-to-studio-flow-audit.md`.

## A. Profile section — right side clipped / cramped

**Cause (confirmed in CSS, effect not screenshotted):** two stylesheets are layered and fight each other.

- `profile.css` (legacy) gives pages fixed shells (`min(100% - 48px, 1118px)`, looks `1432px`) and fixed right-hand columns: avatar `minmax(0,714px) 381px`, measurements `1fr 340px`. Breakpoints 1279 / 1050 / 767.
- `profile-refresh.css` (new editorial shell) adds a 228px sidebar, re-sets page width to `min(100% - 64px, 1040px)`, and sets measurements to `1fr 300px`. Breakpoints 1120 / 900 / 700. It never overrides the avatar grid, so avatar keeps the legacy 714px + 381px (1095px total) inside a 1040px page.
- Net effect at a 1280px window: 1280 − 228 sidebar − 64 gutters ≈ 988px of content, but the layouts were designed for 1118–1432px. The fixed right columns (avatar 381, measurements 300–340, looks note `padding-left: 302px`) plus `minmax(0,…)` main columns squeeze the left card or push the right column to the edge. Between 1051 and 1120px the sidebar is already a 72px rail while the content is still two-column, so it is tightest exactly where laptops live. *Hypothesis for the exact "half cut" symptom: fixed-width right column + 3D stage / `object-fit` figure sized to 100% of a column that has shrunk.*
- Also: `.profile-route > :not(…)` forces any unlisted child to `768px` wide, so Privacy/settings and Profile use a different width than every other page.

**Fix:** pick one width system. One `--profile-content-max` (about 1040px), one breakpoint set, collapse right columns to a stacked layout below about 1180px *of content width* (use a container query on `.profile-route`, not viewport width), delete the superseded `profile.css` page-shell rules. Use `minmax(0, 1fr) minmax(280px, 340px)` rather than hard 381px.

## B. QR / phone capture — "broken screen after it's been scanned once"

Root causes found in code (likely, not reproduced):

1. **Every QR fetch rotates the token.** `refresh_link` (`photo_measurements/pairing.py`) overwrites `token_hash` each call. The desktop calls it whenever the QR query mounts or refetches (page reload, returning to the tab after a remount, "Refresh QR code", "New code"). A phone that already scanned the *previous* code now gets "This link isn't valid." The same happens if the user taps "New code" while the phone is mid-capture. Fix: reuse the current token until it expires (store the raw token server-side, or return the same link while `expires_at` is in the future); rotate only on explicit "new code" and warn it will disconnect the phone.
2. **Dead-end error on the phone.** `CaptureLink.tsx` shows "Try this link again" for every error. For 404 (invalid) and 410 (expired) retrying can never work, and there is no other action. Fix: distinguish expired / replaced / invalid; show "This code is out of date. Look at your computer, a new code is waiting there" with no retry button (or auto-poll nothing). Offer retry only for network errors.
3. **Wrong escape hatch on the phone.** The "done" screen's "Started on this device? Continue here" links to `/onboarding/qr`. A phone opened from a QR has no session, so `SetupFlow` redirects it to `/auth/sign-up` and the user can end up creating a second account. Remove it on the token page, or show it only when the browser is already signed in.
4. **Desktop stuck on "Your phone is connected".** Once the phone scans, state becomes `capturing`, the QR query is disabled, and the screen only says to follow the steps on the phone. If the phone tab is closed, camera permission is denied, or the phone loses signal, there is no timeout, no "phone stopped responding?" message and the recovery ("New code") is a small text link that also rotates the token (see 1). Fix: track `phone_stage` freshness (a heartbeat), after about 90s of silence show "Phone disconnected" with a primary "Show QR again" and "Use this device's camera" button.
5. **Manual path is hidden.** "Enter measurements instead" (the `manual` state) is not a first-class choice next to the QR; users with no phone nearby or a localhost link (the page itself says "A phone needs the site's public HTTPS address") are stuck. Put "Use this computer's camera" and "Enter measurements" as visible secondary buttons under the QR.

## C. Navigation from the QR screen — a trapped, standalone page

- The topbar has a logo and an X, and **both go to `/studio`**. For a user with no avatar yet, Studio's only content is "Create your avatar" → `/onboarding/qr`. So Close → Studio → Create → QR is a loop. There is no route to Profile, Home, help, or sign-out.
- No back step inside the flow (the stepper is display-only), and no "save and finish later".
- Browser Back from setup goes to `/auth/sign-up` (replace-navigations aside); neither Login nor SignUp redirects an already-signed-in user, so they can see "Create account" while signed in.
- The "Skip for now · preview" link exists only in dev builds; production users get nothing equivalent.

**Fix (as a founding designer):**
1. Treat setup as a *guided mode with a way out*, not a lock-in. Top-left: **Back** (previous step) and logo → `/`. Top-right: **Save & exit** (goes to Studio *browse mode*, below) plus a small account menu (Profile, Sign out).
2. Give Studio a real avatar-less browse mode: catalogue visible, try-on controls disabled with an inline "Add your avatar" banner showing live setup status. This removes the loop and de-risks the Redis/CLO-down case.
3. Add "Enter measurements instead" and "Use this device" as visible alternatives on the QR screen.
4. Redirect signed-in users away from `/auth/login` and `/auth/sign-up`.
5. Introduce one shared `RequireAuth`/layout so exit targets and sign-out are consistent (doc 02 B6).

## D. Cross-product inconsistencies (design-system level)

| Area | Observation | Suggestion |
|---|---|---|
| Shells | Four different chromes: marketing nav, auth card, setup topbar, Studio header, Profile sidebar. Logo/home behaviour differs (home vs Studio). | One header contract: logo → home, one account menu everywhere. |
| Naming | Studio nav says "Fit profile" / "Saved looks"; Profile sidebar says "Measurements" / "My Looks"; routes say `signature-looks`. | One vocabulary: "Measurements", "Looks". |
| Avatar creation | Three entry points (QR setup, `/profile/avatar`, `/profile/measurements?generate=1`) with different layouts and copy. | One "Avatar" hub with method choice: photos / measurements. |
| Visual language | Setup is cream/serif (`#FCFBF9`, Times display); Auth/Profile/Studio use other tokens. | Share tokens; decide whether the serif is brand or onboarding-only. |
| Empty/error states | Mixed tone ("Let's reconnect", "A small pause", "We couldn't open your Studio") and mostly a single retry button. | One pattern: what happened, what is safe, primary action, alternate route out. |
| Auth screens | Login has no "Forgot password?"; no consent checkbox; guest is a tiny grey link. (See doc 16.) | Make Google primary, guest explicit about consequences. |
| Responsive | Profile uses 1120/900/700 and 1279/1050/767 together; setup 30px/48px gutters differ from Profile's 56/64px. | Single breakpoint scale and gutter tokens. |
| Accessibility | Not audited: contrast of muted cream greys, focus order in setup stepper, QR alt text is good. | Run an axe + keyboard pass after the layout fix. |

## E. Suggested sequence

1. QR token reuse + phone error states + remove the phone "Continue here" link (B1–B3): small, high-impact, fixes the reported breakage.
2. Setup exit/back + Studio avatar-less browse mode (C1–C2).
3. Profile layout consolidation to one width/breakpoint system (A), verified with screenshots at 1280 / 1100 / 390.
4. Phone-disconnect detection and manual/own-camera alternatives (B4–B5).
5. Shared header/naming/tokens (D) as a design-system pass.

## Verification still owed
Screenshot the Profile pages at 1280/1100/390; reproduce the scan-then-reload case with two browser sessions; test the phone error screen with an expired and a rotated token; confirm Studio empty-state loop in a fresh account.

## Implementation status — 2026-10-06 (same day)

Done and verified (typecheck, lint, 65 unit tests, production build; headless Chromium at 1440 / 1280 / 1100 / 900 / 768 / 390 / 320, no page-level horizontal overflow):

- **A. Profile "half cut"**: the real cause was the 3:2 garment-rail plate forced into tall portrait panels with `object-fit: cover`, slicing garments at the edges. Panels now use the plate's own ratio (16:9 when stacked on tablets), stepper moved into normal flow (no more overlap with the subtitle at 768px), two-column layouts stack at ≤860px, "From photos / Enter manually" no longer wraps. CSS lives in a "Responsive consolidation" block at the end of `profile-refresh.css`; the legacy `profile.css` rules were left in place, not deleted.
- **B1 token rotation**: desktop keeps the issued link in `localStorage` per pairing and reuses it until 60s before expiry (`setup-utils.ts`, unit-tested). Verified: reload keeps the same token and a phone that already scanned keeps working.
- **B2 phone dead end**: 404/410 now shows "This code has expired" with no futile retry; network errors keep a retry.
- **B3**: "Continue setup on this device" appears only for a signed-in browser. Verified absent for a signed-out phone.
- **B4**: after 2.5 min with no phone progress the desktop shows "Still there?" with "Show the code again" (reuses the same valid code; never rotates it).
- **B5**: "Use this device's camera" and "Enter measurements instead" are visible under the QR.
- **C**: setup header has logo → home, "Save & exit" → Studio, and an account menu (Profile, Sign out). Studio no longer dead-ends without an avatar: it opens in browse mode with a setup-status banner and CTA ("Continue avatar setup", "See progress", "Review your avatar", "Fix avatar setup"). Signed-in visitors to `/auth/login` and `/auth/sign-up` are redirected.
- **Doc 16 #1, #3**: consent restored. Sign-up requires an explicit Terms/Privacy checkbox for both Google and email (`acceptedTerms` is no longer hardcoded); Login states the terms beside the Google button and both call `markPendingConsent()` before the redirect. The Sign-up page's fake GitHub button (it called Google) was removed.
- **D naming**: "Measurements" / "My Looks" used in Studio nav, Settings links, the hanger bar and the measurements page heading.

Not done / still open:
- Phone silence is a frontend timer, not a server heartbeat. Real disconnect detection needs a `phone_seen_at` on the pairing.
- Stored capture token in `localStorage` is a short-lived (20 min) pairing token; acceptable for the pilot, but a server-side "return current link without rotating" endpoint would be cleaner.
- Doc 16 #2 / #4 (email-auth policy and its verify/reset dead ends), #6 (saved-measurements shortcut), #7 (guest upgrade), #11 (`RequireAuth`) — unchanged.
- Legacy `profile.css` page-shell rules still exist under the override block; a cleanup pass should delete them once the new layout has been reviewed.
- Physical phone over HTTPS still unverified (needs public URLs).
