# Step 2 - Measurements form to MongoDB

**Status:** frontend intake form implemented and verified (2026-08-04) — `measurements_version` field still remaining
**Created:** 2026-08-04
**Part of:** [05-avatar-vto-live-pipeline-flow.md](05-avatar-vto-live-pipeline-flow.md) / [06-avatar-vto-implementation-status.md](06-avatar-vto-implementation-status.md)

## Goal

Capture a user's body measurements through a form and store them in a shape the CLO avatar pipeline can read directly, with enough versioning information that Step 6 can later tell whether a generated avatar is stale relative to the user's current measurements.

## Current state (already built, verified by reading the code)

- `website/backend/src/measurements/service.py` already implements `submit()` and `patch()` against the `measurements` collection, one document per `user_id`, upserted via `replace_one(..., upsert=True)`.
- `MeasurementDocument` (`measurements/models.py`) is documented as byte-compatible with what `clo_avatar_generation` Step 1 already reads — `user_id`, `gender`, `accuracy`, `created_at`, `updated_at`, plus optional numeric/string fields (`NUMERIC_FIELDS`/`STRING_FIELDS`), absent-when-not-provided rather than stored as null.
- Validation is already in place: `gender ∈ {male, female}`, `accuracy ∈ {accurate, approx}`, every numeric field `> 0`, `skin_tone_hex` matches `#RRGGBB`.
- `to_mongo()` already drops unset optional fields instead of writing `null` — required for CLO pipeline compatibility, already correct.
- HTTP contract (`schemas.py`) reuses `MeasurementFields` directly — no schema drift risk between the DB doc and the request body.

**A real frontend gap was found on closer inspection (2026-08-04), and has now been fixed:** the only two measurement-editing pages that existed — `pages/onboarding/Measurements.tsx` and `pages/profile/ProfileMeasurements.tsx` — both **hard-required an avatar profile to already exist** before rendering any input at all (`if (!avatar) return <...no avatar yet.../>`). Since nothing in the app ever creates that first avatar profile except a measurements submission itself, and neither page would render a form without one, `/onboarding/measurements` was a dead end for every first-time user — reachable only by typing the URL directly, and even then a blocking wall, not a form. Confirmed via `grep`: nothing in the app ever links to that route either. Both pages remain exactly as they were — they're correct for their actual purpose (reviewing/adjusting a photo-derived avatar's estimated measurements) — this just documents why a separate, new entry point was needed rather than reusing them.

## What was implemented (2026-08-04)

A standalone, first-time manual measurement intake form, decoupled from any avatar/photo requirement, reusing the already-working backend end to end.

**Frontend:**
- new `website/frontend/src/pages/Measurements.tsx`, registered at `/measurements` in `router.tsx` — gender + accuracy + units selection, all 7 v1-supported fields (height, weight, chest, waist, hips, shoulder width, inseam — matches the existing `MeasurementKey` contract, deliberately not adding bust/under-bust since the v1 field contract is documented male-first elsewhere in this repo), pre-filled with sensible fallback defaults and editable via the existing `MeasurementRow` component. On save, redirects to `?next=` if present, otherwise `/onboarding/avatar` — the natural next step.
- `website/frontend/src/integrations/mirra-api/runtime-provider.ts` — widened `updateMeasurements`'s `opts` with optional `gender`/`accuracy`, so a first-time submission can actually choose gender instead of the previous hardcoded `"male"` default. Existing callers that don't pass these are unaffected — same defaults as before (`gender: "male"`, `accuracy: "approx"`) are preserved when omitted.
- `website/frontend/src/integrations/mirra-api/http-runtime-provider.ts` — `updateMeasurements()` now passes `opts.gender`/`opts.accuracy` through to the `PUT /measurements/me` fallback call (used on first submission, when the `PATCH` 404s because no doc exists yet).
- `website/frontend/src/integrations/mirra-api/live-schemas.ts` — exported `FIELD_META` (was module-private) so the new page reuses the exact same label/unit/min/max/fallback table the existing review pages use, instead of duplicating it.
- `website/frontend/src/mocks/mock-provider.ts` — **real bug fixed, not just worked around**: the mock's `updateMeasurements` threw a 404 ("No avatar profile yet") when no profile existed yet, meaning the new form couldn't work in the app's default local dev mode (`VITE_INTEGRATION_MODE=mock`) either — same dead-end as the live backend's pre-existing-avatar assumption, just in the mock layer. Fixed by bootstrapping a fresh pending profile on first submission, mirroring the live backend's own `profileFromMeasurements` fallback shape exactly (mock/live parity is a stated architectural rule in this codebase, not just a nicety).

**Backend:** no changes — already fully correct and unmodified, per the "Current state" section above. The new form calls the existing `PUT`/`PATCH /measurements/me` routes exactly as documented.

**Verified:**
- `npm run typecheck`, `npm run build`, and `eslint` all pass clean across every touched frontend file, including the two files this change widened the shared interface of (`runtime-provider.ts`, `mock-provider.ts`) — confirms no other caller of `updateMeasurements` broke.
- Confirmed via `git status` that only the intended files changed — the two existing avatar-review pages were not touched.
- **Not verified**: an actual browser click-through of the new form (no running Mongo/browser available in this environment) — typecheck/build/lint is the verification ceiling reached here, same as the OAuth work in doc 08.

## Remaining work

1. **Add `measurements_version: int` to `MeasurementDocument`.** Increment it on every successful `submit()` and `patch()` call. This is the only planned change — everything else about this step is already correct.
   - Default `1` on first `submit()`.
   - `patch()` increments regardless of which fields changed (even a single-field edit invalidates "is my avatar still accurate to my current measurements").
2. No migration concern — this is an additive field on an already-live collection; existing docs simply don't have it until their next `submit`/`patch`, and Step 6's staleness check should treat a missing `measurements_version` as "unknown, don't claim freshness" rather than crashing.

## Files touched

- `website/backend/src/measurements/models.py` — add the field
- `website/backend/src/measurements/service.py` — increment it in `submit()` and `patch()`

## Why this matters downstream

`avatar_profiles.source_measurements_version` (added in Step 5) is compared against this field to decide whether to show a "regenerate?" prompt (Step 6) instead of silently serving a stale avatar or silently re-running CLO on every page load.

## Verification

- Submit measurements, confirm `measurements_version == 1`.
- Patch a single field, confirm `measurements_version == 2`.
- Confirm `to_mongo()` still drops unset optional fields (unaffected by this change, but worth a quick regression check since it's touching the same model).

## Execution Log

### 2026-08-04 - Manual measurement intake form built; dead-end bug found and fixed along the way

Implemented and verified as described in "What was implemented" above. `measurements_version` (the one item under "Remaining work") is still outstanding — intentionally out of scope for this pass, tracked separately for Step 6's staleness check.
