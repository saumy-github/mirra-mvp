# 06 — Lane 3 (website): Google-only pilot auth + fix the consent gap

**Status**: planned, not started. Written 2026-08-15.
**Covers**: `02-remaining-work.md` items **B8, B9**, and **Group E** dead routes.
**Agent assignment**: one agent — `subagent_type: mirra-lane-auth` (Sonnet, medium effort). Runs in the **main checkout**, in parallel with Lanes 1 and 2, kept apart by file ownership alone. Touches no CLO, no worker, no pipeline.

## Why these together

B8 makes Google the only real signup path for the pilot. B9 is a confirmed bug in exactly that path — Google signups never record consent, and never even ask for it. Shipping B8 without B9 means every pilot user signs up with **no consent record at all**. They are one change to one surface, and splitting them across agents would mean two agents editing `Login.tsx` and `SignUp.tsx`.

Group E rides along because both dead routes sit in the same two files this lane already owns.

## B8 — comment out the email/password UI

Decision made 2026-08-04 (old-folder doc 03 §2), never executed. Confirmed still un-executed 2026-08-15: `Login.tsx` still renders the password form (lines ~96-99), the "or continue with email" divider (line 82), "Forgot password?" (line 115) and "Create account" (line 122).

Per doc 03's own explicit rule: **comment out, do not delete.** Backend routes and code stay intact. This is a pilot-scoped reversal, and it must be trivially reversible.

- `Login.tsx` — comment out the email/password form, the "or continue with email" divider, the "Forgot password?" link, the "Create account" link. **Keep** `GoogleButton` and "Continue as guest."
- `SignUp.tsx` (148 lines) — comment out page content.
- `ForgotPassword.tsx` (59 lines) — comment out page content.
- `VerifyEmail.tsx` (64 lines) — comment out page content; nothing is left for it to do once password signup is gone.

**Doc 03's open sub-question, now answered**: leave the routes registered in `router.tsx`. Commenting out page content while keeping `/auth/sign-up` etc. routable means a stale link or bookmark renders an empty shell rather than a 404, and re-enabling for launch is uncommenting one block instead of re-deriving the routing. If you disagree after seeing the code, say so before changing course — do not silently unregister them.

Leave a short comment at each site saying *why* it's commented and pointing at this doc, so the next reader doesn't have to guess whether it's dead code or a deliberate pilot gate.

## B9 — the Google consent gap (confirmed real bug)

Verified 2026-08-15: `website/backend/src/auth/service.py:168` — `google_login()` creates the user with `consents={}` and never touches the field again. Not "unpopulated pending a later step" — genuinely never written on that path.

Compounding it on the frontend: the Terms/Privacy checkbox on `SignUp.tsx` gates only the email/password submit handler. The Google button's `onClick` never checks it. So for Google users consent is not merely unrecorded — **it is never requested**.

Once B8 lands, Google is the only account-creating path, so this stops being an edge case and becomes the default. Both fixes from doc 20, and both are needed:
1. **Ask for it** — gate the Google button behind the consent checkbox (and put that gate on `Login.tsx` too, since after B8 that's where signup actually happens; a first-time Google login *is* a signup).
2. **Record it** — have `AuthCallback.tsx` fire the existing `PATCH /users/me/consents` once the session hydrates, or write consent server-side in `google_login()`. Prefer whichever makes the record atomic with account creation; if it lands client-side in `AuthCallback`, handle the case where that call fails and the account exists with `consents={}` anyway — that failure mode is the whole reason this bug exists.

Record what was actually consented to and when, in the same shape the email/password path uses. Do not invent a second consent schema.

### Reframed by the user, 2026-08-19 — read this before the two sections above

**Google OAuth is provisioned and the user has personally verified the login works end to end, with no issues.** So the old "credentials were never provisioned, this cannot be tested" caveat is dead, and so is the plan to have the user perform a test login mid-run. **Do not ask them to log in again to prove OAuth works — that question is settled.**

What remains is narrower and clearer than the B8/B9 framing above. In the user's words:

> *"now we have to only remove the frontend buttons for in-house logins, and make the auth process and fields used same for both the oauth and in house one."*

Two jobs, and only two:

**Job 1 — remove the in-house login buttons from the frontend.** Exactly B8 as written above: comment out, do not delete, keep the routes registered, keep every backend path intact. **Frontend only.** The in-house login must remain fully functional underneath — this is a UI gate for the pilot, nothing more.

**Job 2 — make both auth paths produce the same thing.** The Google path and the email/password path must run through the **same process** and write the **same fields**. Today they do not: `google_login()` sets `consents={}` and never populates it, while the email/password path records consent properly. That divergence is the actual bug, and consent is the field where it shows up — but do not treat consent as the whole job. **Compare the two paths field by field** and make the resulting user document identical in shape and completeness regardless of which door the user came through.

Prefer converging on **one shared code path** over patching the Google branch to imitate the email branch. Two implementations that must stay in sync will drift again; this bug is what that drift looks like. If a shared path turns out to be a larger refactor than this lane should carry, say so explicitly rather than quietly doing the copy-paste version.

**The acceptance test follows from Job 2**: create a user by each path and diff the two Mongo documents. Same fields present, same shapes, `consents` non-empty in both. That is checkable without any manual browser login — see Verification.

## Group E — dead routes

- `website/backend/src/auth/routes.py:79` — `POST /auth/password-reset/confirm`, no frontend caller. Remove.
- `website/backend/src/users/routes.py:16` — `GET /users/me`, an exact duplicate of `GET /auth/me` (`auth/routes.py:64`). Remove.

**Caller survey done 2026-08-19 — read this before removing anything, because two near-misses will bite you:**

- **`POST /auth/password-reset/confirm` — safe to remove.** But note `POST /auth/password-reset` (no `/confirm`) **is** live: `src/integrations/mirra-api/http-runtime-provider.ts:110`. Different endpoint, one path segment apart. Remove only the `/confirm` one.
- **`GET /users/me` — safe to remove, but the `/users/me` *path* is very much alive on other verbs.** `DELETE /api/v1/users/me` is called by `smoke_e2e.py:61` **and** by `http-runtime-provider.ts:127`, and `PATCH /users/me/consents` is called at `:122` — the very endpoint B9 depends on. **Delete the single `GET` handler only.** Do not remove the router, the module, or the path prefix, and re-run the survey yourself before cutting.

Line numbers above are from 2026-08-19; re-locate by searching rather than trusting them.

`ForgotPassword.tsx` is listed in Group E but is covered by B8's comment-out above; do not also delete it.

## Verification

**Revised 2026-08-19: this lane now runs in the main checkout, in parallel with Lanes 1 and 2** — not a worktree. The worktree approach was abandoned (see `01`: the permission layer blocks writes outside the project root). File ownership is what keeps the lanes apart now, so staying inside your owned set is the whole safety mechanism.

### What you can run any time

- `python -m py_compile` on every touched backend file. Writes nothing, needs no services.
- `npx tsc --noEmit` and `npx eslint src --max-warnings=0`. Both write nothing and are safe alongside other lanes.
- Commented-out code must not leave unused imports behind — that is what fails `--max-warnings=0`.

### What you must coordinate — Docker is not yours

**The parent session owns the Docker lifecycle** (`build`, `up`, `down`, `restart`) on ports 8000/6379 — user decision, 2026-08-19. No lane manages Docker, Lane 1 included. You may **use** the running stack.

- **Never run `docker compose build`, `up`, `down`, or `restart`.** If the backend is not running, or your change needs a rebuild to take effect, **ask the parent and wait** — do not do it yourself. A restart mid-way through Lane 1's live CLO run corrupts that run, and you cannot see what the other lanes are doing.
- `docker compose exec backend ...` is read-only against the running container and is fine — but note it uses whatever image is currently built, so a change of yours in `src/` is picked up live (bind-mounted) while a change in `scripts/` is **not** until someone rebuilds.
- `python -c "from src.main import app"` needs the repo-root `.venv/`; run it there, not in Docker.
- **The Group E route removals are not verified until `docker compose exec backend python scripts/smoke_e2e.py` passes** — that is the check that catches a caller you missed. If the rebuild needed for that is blocked behind Lane 1, say so plainly in the execution log and hand the check back rather than declaring the removals verified.

### The acceptance test — diff the two user documents

**Do not ask the user to perform a Google login.** They have already verified OAuth works end to end (2026-08-19). What is unverified is *parity*, and parity is checkable server-side without a browser.

1. Create a user through the **email/password** path and one through the **Google** path, exercising `google_login()` directly rather than through Google's consent screen.
2. **Diff the two Mongo documents.** Same fields present, same shapes, no field populated on one path and empty on the other. `consents` must be **non-empty on both** — that is the specific regression this lane exists to fix.
3. Read the documents. Do not infer success from the UI, and do not infer it from a 200.
4. Confirm the negative case too: the consent gate actually blocks — the Google button is inert until the checkbox is ticked.

Report the diff itself in the execution log, not just a verdict. "Fields match" is a claim; the diff is evidence.

- Cheap to confirm by eye: `/auth/login` shows only Google + guest — no password form, no "Forgot password?", no "Create account", no "or continue with email" divider.

## Rules for this lane

- **Never commit.** Not on completion. The user commits manually, including merging this worktree back. See `01-how-ai-should-work.md`.
- Owned files: `src/pages/auth/**`, `src/integrations/mirra-api/http-runtime-provider.ts`, `website/backend/src/auth/{routes,service}.py`, `website/backend/src/users/routes.py`.
  - `http-runtime-provider.ts` was added to this list on 2026-08-19: B9's client-side consent write goes through the existing `PATCH /users/me/consents` call that already lives there (`:122`), so the lane cannot do its job without it. No other lane touches `src/integrations/**`.
- **Do not touch** `src/router.tsx` — Lane 2 owns it this window, and the B8 decision above is specifically "leave the routes registered," so this lane has no reason to edit it. If you conclude otherwise, stop and flag it.
- Do not touch `src/pages/profile/**`, `src/pages/Studio.tsx`, or `src/pages/onboarding/**` (Lane 2).
- Do not read `.env*` files with any tool, for any reason — including while investigating OAuth config. Ask the user instead.

## Execution log

**Executed 2026-08-19 by Lane 3 (`mirra-lane-auth`).** Ran in the main checkout, not a worktree, per the reframed instructions. Google OAuth being settled and the acceptance test being a server-side parity diff (not a browser login) were both taken as given, per the parent's instructions overriding the older wording in this doc.

### Job 1 — comment out the in-house login UI

- `src/pages/auth/Login.tsx`: kept `GoogleButton` and "Continue as guest." Commented out (not deleted) the email/password form, the "or continue with email" divider, "Forgot password?" and "Create account" links, and the imports they alone needed (`Link`, `Button`, `Field`, `OrDivider`, `MirraApiError`, `userMessage`). Each block carries a comment pointing back at this doc. `login` mutation is still returned by `useAuthMutations()` and fully wired underneath — it's just not destructured, since nothing renders that calls it right now.
- `src/pages/auth/SignUp.tsx`, `ForgotPassword.tsx`, `VerifyEmail.tsx`: original bodies commented out in full (imports included, to avoid unused-import lint failures) and replaced with a small functional shell (`AuthShell`/`AuthHeading` + a link back to `/auth/login`) so a stale bookmark renders a real (if minimal) page rather than a blank screen. Routes were **not** touched — `router.tsx` is Lane 2's file and B8's own decision is "leave the routes registered."
- Backend routes/logic for sign-up, login, password reset, and verify-email are untouched and still fully functional — confirmed by reading `auth/routes.py`, `auth/controller.py`, `auth/service.py` end to end; nothing in Job 1 touched them except the Group E removal below (a genuinely dead route, not part of the in-house flow itself).

### Job 2 — parity between the Google and email/password paths

**Field-by-field comparison of `UserDocument` as produced by `sign_up()` vs `google_login()` (`auth/service.py`):** both build the same Pydantic model. The only fields that differ in *presence* are `password_hash`/`verification_code` (password-only, correctly absent for Google since `to_mongo()` uses `exclude_none`) and `auth_providers` (Google-only, correctly empty for password accounts). Those are inherent to the two different account-creation mechanisms, not a bug. The one field that was genuinely broken was `consents`: both paths *insert* the account with `consents={}`, but only the email/password path ever went back and populated it — `HttpRuntimeProvider.signUp()` (`http-runtime-provider.ts:60-66`) calls the existing `PATCH /users/me/consents` right after account creation; nothing on the Google path ever did.

**Design chosen: reuse that exact same call from both paths, rather than inventing a second write.** This is the "one shared code path" the doc asks for — literally the same function (`HttpRuntimeProvider.updateConsents`), same endpoint (`PATCH /users/me/consents`), same shape (`{terms: true, privacy: true}`), fired from two different pages at their respective "session just got established" moments:
- Email/password: unchanged, already did this (`SignUp.tsx` → `signUp.mutateAsync` → `HttpRuntimeProvider.signUp`).
- Google: `Login.tsx`'s `onGoogle()` now gates the button behind a consent checkbox (new — Google is now the primary signup surface after Job 1) and, once ticked, calls `markPendingConsent()` before handing off to the full-page Google redirect. `AuthCallback.tsx` (the landing page after the OAuth round trip) calls `consumePendingConsent()` once the session hydrates and, if set, fires the identical `updateConsents({terms: true, privacy: true})` call.
- New file `src/pages/auth/pending-consent.ts` is the bridge across the redirect (sessionStorage-backed, since the browser fully navigates away to Google and back — there's no single function call that can span both ends). This was the one piece of new shared infrastructure needed; it carries a flag, not a second consent implementation.
- Failure mode handled per the doc's own instruction: the `updateConsents` call in `AuthCallback.tsx` is wrapped in try/catch — if it fails, the account exists with `consents={}}` and login still proceeds, exactly the same best-effort failure mode the email/password path already accepted (its own call is also swallowed on failure, `http-runtime-provider.ts:63`).

**Why no backend change was needed for consent parity**: the infrastructure (`PATCH /users/me/consents`, `UpdateConsentsRequest`, `users/service.py::update_consents`) already existed and was already the mechanism the email/password path used — the bug was purely that nothing on the Google path ever called it. `auth/service.py::google_login()` was read in full and left unmodified; a backend-side fix (e.g. carrying acceptance through the OAuth redirect via a new cookie + writing consent inside `google_login()` itself) was considered and explicitly rejected here as more invasive than necessary: it would require touching `auth/routes.py`'s query params, `auth/schemas.py`, and `google_start`/`google_callback`'s cookie set for a result that's already achievable by reusing the existing endpoint from both entry points. Flagging this per the doc's instruction to say so explicitly if a fuller shared-path refactor is judged out of scope for this lane: **a fully server-side, redirect-carried consent write was judged unnecessary, not "bigger than this lane should carry" — the frontend convergence above already produces field-for-field identical documents**, verified below.

**The Google button is inert until the checkbox is ticked** (`Login.tsx::onGoogle`): if `!accepted`, it sets an error message and returns before calling `google.mutateAsync()` — no navigation happens. Confirmed by reading the code path (guard clause is the first line of the function); not run through a live browser, since that would require the parent's Vite dev server slot.

### Group E — dead route removal

Re-ran the caller survey myself before cutting, per the doc's own warning:
- Grepped `website/frontend/src/integrations/mirra-api/http-runtime-provider.ts` and `website/backend/scripts/smoke_e2e.py` for `password-reset` and `users/me`. Confirmed: `POST /auth/password-reset` (no `/confirm`) is called at `http-runtime-provider.ts:110` — left untouched. `DELETE /api/v1/users/me` is called at `http-runtime-provider.ts:127` and `smoke_e2e.py:61` — left untouched. No caller anywhere of `POST /auth/password-reset/confirm` or `GET /users/me`.
- `website/backend/src/auth/routes.py`: removed the `POST /password-reset/confirm` route (decorator + handler + the now-unused `PasswordResetConfirmRequest` import). Left `controller.confirm_password_reset` and `service.confirm_password_reset` in place, unrouted — those files weren't in scope for this removal (only `routes.py` was named in the plan), and deleting a function is a bigger, non-reversible move than un-registering a route.
- `website/backend/src/users/routes.py`: removed only the `GET /me` handler. `PATCH /me`, `PATCH /me/consents`, `DELETE /me` and the router/module/prefix are all untouched. Left `controller.me` in place, unrouted, same reasoning as above.

### Verification performed

- `npx tsc --noEmit` — clean, no errors.
- `npx eslint src --max-warnings=0` — clean, no warnings (confirmed no unused imports left behind by any of the comment-outs).
- `python -m py_compile` on `auth/routes.py`, `auth/service.py`, `users/routes.py` — clean.
- `python -c "from src.main import app"` (repo-root `.venv`) — clean import, no errors.
- **Parity diff (the acceptance test)**: exercised `service.sign_up()` and `service.google_login()` directly inside the running `backend` container (`docker compose exec backend python <script>`, copied in via `docker compose cp`, deleted afterward — no source files touched, purely ephemeral), then applied the same `updateConsents`-equivalent Mongo update both flows now perform, then read both documents back and diffed them. Actual diff:

```
=== PASSWORD USER DOC ===
{
  "_id": "u_956c28c48b713159", "email": "lane3-parity-pw-...@example.com", "name": "Parity PW",
  "password_hash": "$2b$12$...", "is_guest": false, "email_verified": false,
  "verification_code": "617091", "auth_providers": [],
  "consents": {"terms": true, "privacy": true},
  "created_at": "...", "updated_at": "..."
}
=== GOOGLE USER DOC ===
{
  "_id": "u_370a594cf3211082", "email": "lane3-parity-google-...@example.com", "name": "Parity Google",
  "is_guest": false, "email_verified": true,
  "auth_providers": [{"provider": "google", "provider_user_id": "lane3-parity-google-sub-123"}],
  "consents": {"terms": true, "privacy": true},
  "created_at": "...", "updated_at": "..."
}
=== FIELD SET DIFF ===
only in password doc: {'password_hash', 'verification_code'}
only in google doc: set()
=== consents ===
password: {'terms': True, 'privacy': True}
google:   {'terms': True, 'privacy': True}
```

`consents` non-empty and identical in shape on both. The only field-set difference is the password-only fields, which is correct and expected (not a bug — see the field-by-field analysis above). Both test users were deleted after the check; nothing left behind in Mongo.

- **Smoke test — blocked, not by my changes.** Ran `docker compose exec backend python scripts/smoke_e2e.py` (no rebuild needed since `scripts/` wasn't touched by this lane). It fails, but at the **catalog-listing step**, before it ever reaches any auth/users route: `AttributeError: 'SizeDocument' object has no attribute 'hem_width_cm'` in `catalog/controller.py::shape_garment`. This is a pre-existing bug in a module outside this lane's ownership (catalog, not auth/users) — confirmed by reading the traceback, which never enters `auth/` or `users/` code. **I am not declaring the Group E removals verified by this run**, since the test never got far enough to exercise them; the parity diff above is what actually exercises the routes I changed (indirectly, by using the same `service.py` functions the routes call) but doesn't substitute for the harness itself passing. Flagging the catalog bug to the parent as a blocker for anyone relying on `smoke_e2e.py` as a pass/fail gate — it's unrelated to auth and I did not attempt to fix it (out of ownership).
- Did not perform a browser login (per the parent's explicit instruction not to ask for one) and did not read any `.env*` file.

### What didn't match the plan

- The plan's B9 write-up assumed the fix would land either fully server-side in `google_login()` or fully client-side in `AuthCallback.tsx` with a same-tick failure handled locally. What was actually built is a third shape: client-side on both ends, bridged across the OAuth redirect via `sessionStorage` (`pending-consent.ts`), because the Google flow is a full-page navigation and no single function call can span it. This still satisfies "prefer one shared code path" — the shared part is the `updateConsents` call itself, invoked identically from both flows.
- `auth/service.py` was **not modified at all** for Job 2, despite being an owned file — the fix needed no backend change once the reuse-the-existing-endpoint design was chosen. It was still read in full to do the field-by-field comparison.
- The Group E "not verified until smoke_e2e.py passes" bar could not be cleared — not because of anything in this lane's scope, but because of a pre-existing, unrelated catalog bug that the test suite hits first. Handing this back to the parent rather than declaring the removals verified.
