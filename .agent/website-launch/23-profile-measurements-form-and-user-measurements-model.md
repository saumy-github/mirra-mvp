# 23 - `/profile/measurements` gets a real form; new `user_measurements` model for real users

**Status:** implemented and verified (2026-08-11)
**Created:** 2026-08-10

## Context

`ProfileMeasurements.tsx` (`/profile/measurements`) currently hard-gates on an avatar already existing — if there's no `avatar_profiles` doc yet, it renders one static line ("Measurements appear here once an avatar exists.") and nothing else, no inputs at all. The actual working first-time entry form lives at a completely different, unlinked route (`/measurements`, `pages/Measurements.tsx`), built earlier this session specifically because `ProfileMeasurements.tsx` and `onboarding/Measurements.tsx` both had this same dead-end problem. A first-time user landing on the profile tab today has no way to enter their body dimensions at all unless they already know the separate `/measurements` URL.

Separately: right now every measurement — real user or dev/test fixture — lands in the same `measurements` collection, the same one the CLO pipeline reads directly and that `golden_users` fixtures already populate. The user wants a second, new collection specifically for real users' saved body dimensions, kept structurally separate from that dev/pipeline-facing collection — the same "don't mix real and dev data" principle already applied to `dev_upload/`/`live_upload/` for avatar storage. The existing `measurements` collection and its model are explicitly **not** to be touched — they're depended on by the CLO pipeline and dev fixtures today and changing them isn't a same-day change.

## Part A — `/profile/measurements`: replace the dead end with the real form

**What changes:** only the empty-state branch. `ProfileMeasurements.tsx` currently has:

```tsx
if (!avatar) {
  return <p className="text-sm text-muted">Measurements appear here once an avatar exists.</p>;
}
```

That one line gets replaced with the actual measurement-entry form — the gender / accuracy / units toggle groups and the field rows currently in `pages/Measurements.tsx` (lines 90-168 of that file: the three pill toggle groups, then the bordered card of `MeasurementRow`s). The **existing** branch below it (the "Review your measurements" editor, shown once an avatar/profile already exists) is untouched — this is purely about giving the *empty* state a real form instead of a dead end.

**What does not change:**
- The `ProfileLayout` header ("PROFILE" title, Overview / Avatar / Measurements / Signature Looks / Privacy tabs) — untouched, exactly as it is today.
- `pages/Measurements.tsx` itself stays as-is (still reachable at `/measurements` for the onboarding flow, which redirects there with a `?next=` param) — this isn't a move, it's reusing the same form markup/logic in a second place.
- The existing "has avatar" review branch in `ProfileMeasurements.tsx`.

**Implementation shape:** extract the shared bits (the three toggle groups + field-row list + save button, roughly lines 90-184 of `Measurements.tsx`) into a small reusable component (e.g. `features/onboarding/components/measurement-form.tsx`) so `pages/Measurements.tsx` and `ProfileMeasurements.tsx`'s empty-state branch both render the same thing instead of duplicating ~90 lines of JSX. `pages/Measurements.tsx` keeps its own page chrome (the "Tell us your body measurements" heading, full-page `<main>` layout, and post-save `navigate(next ?? "/onboarding/avatar")`); `ProfileMeasurements.tsx`'s empty-state branch renders the same extracted form inside its existing tab content area, with its own on-success behavior (likely just refreshing the query cache and switching to the "review" view — no redirect needed since the user's already on the profile page they want to be on).

**Files touched:**
- `website/frontend/src/pages/profile/ProfileMeasurements.tsx` — empty-state branch replaced
- `website/frontend/src/pages/Measurements.tsx` — refactored to use the extracted shared form
- new: `website/frontend/src/features/onboarding/components/measurement-form.tsx` (or similar) — the extracted shared piece

**Also part of this pass (decided 2026-08-10): delete `website/frontend/src/pages/onboarding/Measurements.tsx` (`/onboarding/measurements`) entirely** — no longer needed once `ProfileMeasurements.tsx` actually works. It's currently reachable only from `Avatar.tsx`'s "Review measurements" button on the decision screen; that button gets repointed to `/profile/measurements` instead. Concretely:
- delete `website/frontend/src/pages/onboarding/Measurements.tsx`
- `website/frontend/src/router.tsx` — remove its lazy import and `<Route path="/onboarding/measurements" .../>`
- `website/frontend/src/pages/onboarding/Avatar.tsx` — `goToMeasurements` (currently `navigate("/onboarding/measurements")`) → `navigate("/profile/measurements")`

## Part B — new `user_measurements` model, and it becomes the only website write path

**Decision (2026-08-10): every measurement save from the website — dev or production, no distinction — writes to `user_measurements` from now on. Nothing on the website writes to `measurements` anymore, starting with this change.** `measurements` becomes CLI/pipeline-testing-only: `golden_users`/`seed_measurements.py` fixtures and direct `run_avatar.py`/`run_clo_vto.py` runs keep using it exactly as today, unchanged. You've said you'll deprecate `measurements` later — this plan doesn't delete or migrate it, just stops the website from writing to it.

**Still explicitly not in this pass:** migrating existing `measurements` data into the new collection, or changing `measurements/models.py`'s field definitions. The old model/collection keep existing, keep working for CLI use, just stop receiving website writes.

**A real consequence of this decision, not just a save-path change** — see Part C below. If the website stops writing to `measurements` entirely, the two places that currently *read* from it to actually generate an avatar break for every real user unless they're repointed too.

### Proposed fields

Based on `website/backend/src/measurements/models.py`'s existing `MeasurementFields`/`MeasurementDocument` (reusing the same field set and validation rules — gender/accuracy enums, `gt=0` on every numeric field, `#RRGGBB` pattern on `skin_tone_hex` — so the two models stay easy to compare and a future migration/merge isn't fighting a totally different shape), plus two additions:

```python
class UserMeasurementsDocument(BaseModel):
    id: str = Field(alias="_id")          # new own id, e.g. "um_..." — this collection's own doc id
    user_id: str                          # see "Linking to users" below

    gender: Literal["male", "female"]
    accuracy: Literal["accurate", "approx"]

    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    shoulder_width_cm: float | None = Field(default=None, gt=0)
    waist_circumference_cm: float | None = Field(default=None, gt=0)
    hip_circumference_cm: float | None = Field(default=None, gt=0)
    leg_length_cm: float | None = Field(default=None, gt=0)
    chest_circumference_cm: float | None = Field(default=None, gt=0)
    bust_circumference_cm: float | None = Field(default=None, gt=0)
    under_bust_circumference_cm: float | None = Field(default=None, gt=0)
    body_shape_type: str | None = Field(default=None, max_length=40)
    skin_tone_hex: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)

    # New, not present on the old model:
    units_preference: Literal["metric", "imperial"] = "metric"  # the old model never persisted this — the frontend re-derives/loses it each visit today
    measurements_version: int = 1         # increments on every submit/patch — this is exactly the field doc 09 flagged as still-missing on the old model; a new model gets to start with it from day one, which is what unlocks Step 6's "your measurements changed, regenerate?" staleness check

    created_at: datetime
    updated_at: datetime
```

### Linking to the `users` model

No true foreign key (Mongo doesn't have one) — `user_id: str` stores the same string id as `UserDocument.id` (aliased `_id` in `website/backend/src/auth/models.py`, e.g. `"u_..."`/`"g_..."` for guests). This is the exact same convention every other collection in this codebase already uses (`avatar_jobs.user_id`, `avatar_profiles.user_id`, `tryon_sessions.user_id`, `signature_looks.user_id`, and the existing `measurements.user_id` itself) — no new pattern being introduced, just applying the established one to the new collection.

Matching the old collection's own index (`db.py::ensure_indexes()` already does `measurements_col().create_index([("user_id", ASCENDING)], unique=True)`), the new collection gets the same: **one document per user**, unique index on `user_id`.

### Files this touches (new module, mirroring `measurements/`'s shape)

- new: `website/backend/src/user_measurements/models.py` — `UserMeasurementsDocument` above
- new: `website/backend/src/user_measurements/schemas.py` — HTTP request contract (mirrors `measurements/schemas.py`)
- new: `website/backend/src/user_measurements/service.py` — `submit()`/`patch()`/`get_for_user()` (mirrors `measurements/service.py`'s shape exactly, per your "take help from the measurements folder" note)
- new: `website/backend/src/user_measurements/controller.py`, `routes.py` — new endpoints, e.g. `PUT`/`PATCH`/`GET /user-measurements/me` (mirrors the existing `/measurements/me` shape so the frontend swap is a base-URL change, not a payload-shape change)
- `website/backend/src/db.py` — add `user_measurements_col()` + the unique index on `user_id`
- `website/backend/src/main.py` — mount the new router

**Frontend repointing** (the save path itself — Part A's new form is one of several callers):
- `website/frontend/src/integrations/mirra-api/http-runtime-provider.ts::updateMeasurements()` — repointed from `/measurements/me` to `/user-measurements/me`. This one change covers every caller at once: `pages/Measurements.tsx`, `pages/profile/ProfileMeasurements.tsx` (both branches), and `pages/onboarding/Measurements.tsx` all go through this same method — none of them need to change themselves, only what the method underneath them talks to.
- `website/backend/scripts/smoke_e2e.py` — currently does `PUT /api/v1/measurements/me` to simulate a real user saving measurements; since real users no longer write there, this needs to call `/user-measurements/me` instead so the smoke test actually exercises the real website path.

## Part C — every website read of the old model repoints too (except worker/CLO3D — deliberately deferred)

Decision (2026-08-10): every website HTTP path that touches the `measurements` model — for avatar generation or anything else — now points at `user_measurements`. This is broader than just the save path (Part B); two more places read or write the old collection today and need to move:

**1. `website/backend/src/avatars/service.py::start_generation()`** — currently:
```python
from ..measurements.service import get_for_user as get_measurements
...
measurements = await get_measurements(user_id)  # 404s if none stored
```
Repointed to `user_measurements`'s service. In scope now — this is website backend code, not the worker or the CLO3D queue.

**2. `website/backend/src/users/service.py::delete_account()`** — the account-deletion cascade currently does `await measurements_col().delete_many({"user_id": user_id})`. Repointed to `user_measurements_col()` instead, so deleting an account actually cleans up where that user's real data now lives. Also in scope now — not worker code.

### Explicitly deferred — no change to `worker/` or the CLO3D pipeline in this pass

Per your instruction: nothing in `worker/` and nothing in the CLO3D queue/pipeline invocation changes right now. This leaves a real, known gap, stated plainly rather than hidden: **`clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py` will still read the old `measurements` collection when the worker actually drives a real user's avatar generation.** That function does its own independent live fetch at run time — `mirra_measurements.db.get_measurements_collection().find_one({"user_id": ctx.user_id})` — separate from anything `avatars/service.py` does; it never reads the job's `measurement_snapshot`. So after this plan ships, a real website user can save measurements successfully (now in `user_measurements`), but the actual CLO pipeline run triggered by the worker will look in `measurements`, find nothing for that user, and fail. This is a deliberate, accepted gap for this pass, not an oversight — listed here so it isn't rediscovered as a surprise production bug.

**Places that will need a change later, once you're ready to touch the worker/pipeline side (list only, nothing here is executed by this plan):**
- `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py` — the actual fetch. Needs to read `user_measurements` for worker-driven (real user) runs while still reading `measurements` unchanged for CLI-driven (`run_avatar.py --user-id ...`, golden-user) runs. A "try `user_measurements` first, fall back to `measurements`" approach would do this without a mode flag and without changing how CLI testing is invoked — but that's a design choice for when this is actually picked up, not decided here.
- `worker/tasks.py::run_avatar_job` — likely doesn't need a change itself (it just triggers the pipeline by `user_id`; step_03 does its own fetch), but worth a fresh look at that point in case anything else assumes `measurements`.
- Possibly `clo_vto`'s equivalent, if it independently reads measurements anywhere for try-on — not confirmed, worth checking when this is picked up.

## Dead code: deleted outright as part of this plan (not just left unreachable)

Decision (2026-08-10): the HTTP-facing layer of the old `measurements` module has zero remaining callers once Part B/C land, and gets deleted, not just orphaned:

- `website/backend/src/measurements/routes.py` — deleted (`GET`/`PUT`/`PATCH /measurements/me`)
- `website/backend/src/measurements/controller.py` — deleted (only existed to back those routes)
- `website/backend/src/measurements/schemas.py` — deleted (only existed to validate those routes' bodies)
- `website/backend/src/main.py` — remove the `measurements_router` import and `api.include_router(measurements_router)` line
- `website/frontend/src/pages/onboarding/Measurements.tsx` — deleted (see Part A)
- `website/frontend/src/router.tsx` — remove its lazy import + `<Route path="/onboarding/measurements" .../>`

**Stays — still alive, just no longer reached over HTTP:**
- `website/backend/src/measurements/service.py` — `submit()`/`patch()`/`get_for_user()` called directly (in-process, not via HTTP) by `scripts/seed_measurements.py`/`scripts/golden_users.py` for CLI/dev fixture seeding.
- `website/backend/src/measurements/models.py` — still the doc shape those scripts and the CLO pipeline's CLI path (`step_03_fetch_measurements.py`) read/write.
- The `measurements` folder as a whole becomes CLI/dev-only, per your stated intent to deprecate it later — this plan doesn't delete the folder, only its now-truly-unused HTTP layer.

## Open doubts about `user_measurements` (not blocking execution, flagging for awareness)

1. **Existing real-user data left behind.** Any account that already saved measurements before this change has that data sitting in `measurements`, not `user_measurements`. After this plan ships, the website looks only at the new collection — those users would appear to have no measurements saved and need to re-enter them. No migration is included in this plan (wasn't asked for). Given this product is still pre-launch/pilot, likely low-stakes, but worth knowing it's not handled.
2. **Route naming**: proposing `/api/v1/user-measurements/me` (kebab-case, matches the existing `/signature-looks` precedent) for the new endpoints, `website/backend/src/user_measurements/` (snake_case) for the Python package, `user_measurements` for the Mongo collection name. Flagging the exact names in case you want something else before they're baked into the frontend too.
3. **`GET /user-measurements/me` is being built for symmetry** (mirrors the old module's shape) but nothing currently calls it from the frontend — same as the old `GET /measurements/me`, which doc 21 already flagged as unused. Building it anyway since it's near-zero extra cost and `get_for_user()` needs to exist for the other operations regardless; just noting it isn't wired to a consumer yet.
4. **One doc per user, no history** — matches the old model exactly (`measurements_version` increments in place, nothing is kept from prior versions). If you ever want to see a user's measurement history rather than just the latest, that's a different shape (a doc per submission, not per user) — not what's being built here.

## Verification (once implemented)

- `/profile/measurements` with no avatar/profile yet shows the real form, not the dead-end line; submitting it works and the page reflects the saved state afterward.
- `/measurements` (onboarding entry point) still works identically to today — the extraction didn't change its behavior, only where the JSX lives.
- New `user_measurements` collection: submit creates a doc with `measurements_version: 1`; a second submit for the same user updates the same doc (unique index holds) and increments the version; `user_id` matches a real `users` collection doc.
- `scripts/seed_measurements.py`/`golden_users.py` and `run_avatar.py --user-id u_001`-style CLI runs still work completely unchanged — confirms `measurements/*`'s models/service weren't touched.
- Account deletion cascade cleans up `user_measurements`, not `measurements`, for a real user.
- `/onboarding/measurements` is gone (404/no route); `Avatar.tsx`'s "Review measurements" goes to `/profile/measurements` instead.
- Backend imports cleanly with `measurements_router` removed from `main.py` and the module's routes/controller/schemas deleted.
- **Not verified in this pass** (deliberately deferred, see Part C): an actual `POST /avatars/generate` for a real website user still won't find measurements at the pipeline level, since `step_03_fetch_measurements.py` isn't touched. That's expected, not a bug to chase down now.

## Execution Log

### 2026-08-10/11 - Implemented

Built exactly as planned (Parts A, B, C's backend-side pieces only — worker/CLO3D deliberately untouched, per instruction), plus the dead-code deletions:

- **New `website/backend/src/user_measurements/`** — `models.py` (`UserMeasurementsDocument`), `schemas.py`, `service.py` (`submit`/`patch`/`get_for_user`/`delete_for_user`, version-incrementing), `controller.py`, `routes.py` (`GET`/`PUT`/`PATCH /api/v1/user-measurements/me`). `db.py` got `user_measurements_col()` + its unique `user_id` index. `main.py` mounts the new router.
- **Repointed reads/writes**: `avatars/service.py::start_generation()` now reads from `user_measurements`; `users/service.py::delete_account()`'s cascade now deletes from `user_measurements_col()` instead of `measurements_col()`.
- **Deleted**: `measurements/routes.py`, `controller.py`, `schemas.py`, and the router mount in `main.py`. `measurements/models.py` and `service.py` untouched — still used by `seed_measurements.py`/`golden_users.py`.
- **Deleted**: `website/frontend/src/pages/onboarding/Measurements.tsx`, its `router.tsx` route/import, and repointed `Avatar.tsx`'s `goToMeasurements` from `/onboarding/measurements` to `/profile/measurements`.
- **Part A**: extracted the shared gender/accuracy/units toggle groups + field rows + save button into `features/onboarding/components/measurement-form.tsx` (self-contained — owns its own state, calls `updateMeasurements()`, takes an `onSaved` callback). `pages/Measurements.tsx` now just supplies its page chrome and renders it. `ProfileMeasurements.tsx`'s empty-state branch (previously the dead "Measurements appear here once an avatar exists." line) now renders the same form. The existing "has avatar" review branch in that file is untouched.
- **Frontend repoint**: `http-runtime-provider.ts::updateMeasurements()` now calls `/user-measurements/me` instead of `/measurements/me` — this one change covers every remaining caller (`Measurements.tsx` via the new form, `ProfileMeasurements.tsx`'s review branch, `onboarding/Measurements.tsx` no longer exists).
- **`scripts/smoke_e2e.py`** — repointed to `/user-measurements/me`, and the cascade-leftover check now looks at `user_measurements` instead of `measurements`.

**Verified**:
- Backend: `py_compile` + `from src.main import app` on every touched/new file; backend image rebuilt (picks up `scripts/` + `src/user_measurements/`, neither bind-mounted) and confirmed healthy.
- `GET /api/v1/measurements/me` → **404**, confirmed genuinely unmounted, not just unauthorized.
- Direct end-to-end test against the real backend + Mongo: guest signup → `PUT /user-measurements/me` (creates `measurements_version: 1`) → `PATCH` (increments to `2`) → `GET` (reflects the patch) → raw Mongo confirms the doc in `user_measurements` and confirms **no doc was written to the old `measurements` collection** → account deletion → confirmed the `user_measurements` doc is gone (cascade works).
- `scripts/smoke_e2e.py`'s own run hit an **unrelated, pre-existing bug** in `catalog/controller.py` (`SizeDocument` missing a `hem_width_cm` attribute the shaper expects) — confirmed via `git diff` that `catalog/` has zero changes from this or any prior session's work here, so this isn't something this plan caused. Not fixed (out of scope). The smoke test got as far as "measurements submitted: PASS" before hitting the unrelated catalog failure, which independently confirms the new endpoint works via the exact same code path the standalone verification above already covered directly.
- Frontend: `tsc --noEmit`, `eslint --max-warnings=0`, `npm run build` all clean. Confirmed `measurement-form` is its own lazy-loaded chunk (extraction worked) and grepped the built `dist/` for the old page's copy ("quick photo session," "Retake photographs") and the old endpoint path (`/measurements/me`) — both absent.

**Not done (by instruction)**: nothing in `worker/` or `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py` was touched. See Part C's "Explicitly deferred" section for the exact, known gap this leaves (a real website user's avatar generation will still fail at the CLO-pipeline level until that's picked up later) and the list of places that will need a change then.

### 2026-08-11 - `/measurements` deleted too; only `/profile/measurements` remains

Follow-up decision: the standalone `/measurements` page is gone as well — `MeasurementForm` now has exactly one consumer (`ProfileMeasurements.tsx`'s empty state), no duplication anywhere.

- Deleted `website/frontend/src/pages/Measurements.tsx`.
- `router.tsx` — removed its lazy import and `<Route path="/measurements" .../>`.
- `pages/onboarding/Avatar.tsx`'s "measurements-required" phase button — was `navigate("/measurements?next=/onboarding/avatar")`, now `navigate("/profile/measurements")`. Note: this drops the old auto-return-to-avatar-generation behavior after saving (that page supported a `?next=` redirect; `/profile/measurements` doesn't take one) — not re-implemented since it wasn't asked for; flagging in case that UX gap matters later.
- Fixed a stale doc-comment in `measurement-form.tsx` that still referenced the deleted page.
- **Verified**: grepped for every remaining reference to `/measurements` or `pages/Measurements` — none left outside this doc's own history. `tsc`, `eslint`, and `npm run build` all clean; confirmed no separate orphaned chunk for the deleted page in the build output.
