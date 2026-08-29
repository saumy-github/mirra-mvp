# 08 — API surface, docs exposure, and measurement-field consistency

**Status**: recorded, nothing executed. Written 2026-08-19.
**Raised by**: the user, while rebuilding a picture of what is actually live.
**Renamed** from `08-api-surface-audit-and-docs-exposure.md` when the measurement concerns were added.

Five concerns, each with its own status line. All findings below were verified against the running app and the code on 2026-08-19 — not inferred from older docs.

**This file is a problem list, not a work order.** User instruction, 2026-08-19: *"first we are only listing the problems, for coding we will check later."* Nothing here is scheduled, and no agent should start on any of it because it looks straightforward. Wait to be told.

## How this file is maintained

**Every concern carries a `**Status:**` line.** One of:

- `NOT SOLVED` — recorded, no work done
- `SOLVED` — work done, user has manually verified it, outcome written up below the concern
- `DEFERRED → <file>` — moved elsewhere, with the pointer

**The write-up rule, set by the user 2026-08-19 and binding on every agent:**

> When work is done on a concern, the "What we did" section under it is written **only after the user has manually checked the result and explicitly given permission to write it.**

Do **not** write an outcome because the code compiles, the tests pass, or the work looks obviously finished. Do not pre-fill it optimistically and correct it later. Until that permission arrives the status stays as it was and the section stays empty. This is the same principle as the never-commit rule: the user verifies, then records.

---

# Concern 1 — API route sprawl (`/users/me` and friends)

**Status: NOT SOLVED**

The user's framing: too many paths have accumulated, which will make future debugging harder.

## Measured surface

**33 operations across 27 paths**, taken from the live app's own `/openapi.json`.

| Service | Ops | Paths |
|---|---|---|
| auth | 10 | 10 |
| avatars | 5 | 4 |
| tryon | 4 | 4 |
| signature-looks | 4 | 2 |
| users | 3 | 2 |
| user-measurements | 3 | 1 |
| catalog | 2 | 2 |
| analytics | 1 | 1 |
| health | 1 | 1 |

## The `/users/me` family

Three operations on two paths, in `website/backend/src/users/routes.py`:

| Method | Path | Frontend caller |
|---|---|---|
| `PATCH` | `/users/me` | **none** |
| `PATCH` | `/users/me/consents` | `http-runtime-provider.ts:122` |
| `DELETE` | `/users/me` | `http-runtime-provider.ts:127`, `smoke_e2e.py:61` |

`GET /users/me` was removed 2026-08-19 as a duplicate of `GET /auth/me` (doc 06, Group E).

**The problem is not the count — 33 is unremarkable for this feature set. It is that five different things are called some variant of "me", across three routers:**

```
GET           /auth/me                  read account
PATCH         /users/me                 update profile
PATCH         /users/me/consents        update consents
DELETE        /users/me                 delete account
GET|PUT|PATCH /user-measurements/me     a separate service entirely
```

`users` and `user-measurements` differ by one character in a URL and live on different routers. That is the debugging hazard.

## Endpoints with no caller anywhere

Verified by grepping the whole `website/` tree — frontend `src/` and `backend/scripts/`.

| Endpoint | Assessment |
|---|---|
| `PATCH /users/me` (`update_profile`) | **Dead.** No `updateProfile` exists anywhere in `website/`. Dead by exactly the test that condemned `GET /users/me`, but it was not on Group E's list so no lane touched it. |
| `GET /user-measurements/me` | **Dead as far as the app is concerned.** The client only ever `PUT`s and `PATCH`es that path. Plausibly intended for a "load my saved measurements" read that was never wired. |
| `GET /avatars/profile/glb` | **Not dead — new.** Landed 2026-08-19 (doc 04, A2). Its consumer is not built yet. Leave it. |
| `GET /health` | **Not dead.** Infrastructure; used by `smoke_e2e.py`. Leave it. |

**Trap for whoever acts on this.** Three endpoints look uncalled if you grep only for `http.get/post/...`, and are not:

- `GET /auth/google/start` — a full-page `window.location.assign` (`http-runtime-provider.ts:79`), not a fetch.
- `GET /auth/google/callback` — Google redirects the browser to it.
- `POST /auth/refresh` — fired by the client's 401 interceptor (`client.ts:85`, `auth-token.ts:35`), never by feature code.

Deleting any of those breaks login or session refresh. **Do not judge a route dead by fetch-grep alone.**

## What would actually help

1. Delete the two genuinely dead ops, or wire `GET /user-measurements/me` if a read is wanted. Each needs the full caller survey, including redirect and interceptor call sites.
2. Write down the `/me` map once so nobody re-derives it — one table on the users router.
3. Consider whether `user-measurements` should be `/users/me/measurements` rather than a sibling one character away. Breaking change, touches the client — a real decision, not a cleanup.

`http-runtime-provider.ts` is already the single place the frontend names endpoints, which is why this survey was cheap. Keep it that way; do not let feature code call `http.*` directly.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 2 — `/docs` must be unavailable in production

**Status: NOT SOLVED**

## Current state

`website/backend/src/main.py:39`:

```python
app = FastAPI(title="Mirra Website Backend", version="0.1.0", lifespan=lifespan)
```

No `docs_url`, no `redoc_url`, no `openapi_url`, no environment check, no auth dependency. FastAPI's defaults leave three endpoints open to anyone who can reach the backend. All three return 200 right now:

- `/docs` — Swagger UI, interactive
- `/redoc` — ReDoc
- `/openapi.json` — the raw schema

**Two things that do not protect them:**

- **CORS does not apply.** It is a browser-enforced restriction on cross-origin *scripted* requests. Typing the URL, or `curl`, ignores it.
- **`get_identity` does not apply.** Auth is a per-route dependency on the `/api/v1` routers. These three sit outside that router.

## What is exposed

The complete API surface: every path, method, field name, type, and validation rule — including auth and account-deletion endpoints. No secrets, no user data, no credentials. But it is a precise map for anyone probing the service, and it advertises `DELETE /users/me` directly.

The page also pulls Swagger UI's JS/CSS from a public CDN (`cdn.jsdelivr.net/npm/swagger-ui-dist@5`) rather than bundling it, so it is a third-party asset load on your production domain too.

## The fix

Gate on the `app_env` setting that already exists (`config.py`, `Literal["development", "production"]`, already consumed by `avatars_upload_root`):

```python
is_prod = settings.app_env == "production"
app = FastAPI(
    title="Mirra Website Backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)
```

**All three must be disabled together.** Turning off `/docs` while `/openapi.json` stays reachable accomplishes nothing — the schema is the payload, the UI is just a renderer.

## Verification

Static checks cannot confirm this. It needs the app running under each setting:

- `APP_ENV=development` → `/docs`, `/redoc`, `/openapi.json` all 200.
- `APP_ENV=production` → all three 404, **and** `/api/v1/health` still 200, proving the app is up and only the docs are gone.

`curl -o /dev/null -w "%{http_code}"` against all four URLs in both modes.

## One thing to decide deliberately

`APP_ENV` defaults to `development`, so docs are exposed unless production is *explicitly* configured — open-by-default. If that is not acceptable, invert it to an explicit opt-in (`ENABLE_DOCS=true`). A judgement call, not a technical constraint.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 3 — measurement fields must be consistent with the pipeline

**Status: NOT SOLVED**

User instruction, 2026-08-19: *"today we will make all the measurements consistent as per pipeline measurements, make it consistent in backend, frontend."*

## The pipeline's own truth is split across two files

This must be fixed first, or everything else syncs to a source that is itself inconsistent:

- `clo_avatar_generation/schema/step1_field_contract.json` — **9 field entries** with `mongo_field`, `genders`, `included_in_v1`, `property_key`, `avt_feature_index`, plus top-level `unit` and `round_decimals`. **Contains no min/max.**
- `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py` — `MEASUREMENT_RANGES`, a hardcoded dict holding min/max for all 9.

**Step one is to move the ranges into the contract JSON**, making it the complete definition.

## Where the ranges disagree today

| Field | Frontend (`FIELD_META`) | Pipeline (`MEASUREMENT_RANGES`) | Backend model |
|---|---|---|---|
| height_cm | 120–220 | 120–230 | `gt=0` only |
| weight_kg | 35–180 | 30–250 | `gt=0` only |
| chest_circumference_cm | 70–140 | 50–180 | `gt=0` only |
| waist_circumference_cm | 50–140 | 40–220 | `gt=0` only |
| hip_circumference_cm | 70–150 | 50–220 | `gt=0` only |
| shoulder_width_cm | 30–60 | 20–80 | `gt=0` only |
| leg_length_cm | 55–110 | 40–140 | `gt=0` only |

**Naming is already consistent** — `KEY_TO_FIELD` (`live-schemas.ts:134`) maps all 7 UI keys onto exactly the names `UserMeasurementFields` declares, and the contract asks for those same names. That was the most likely thing to be broken and it is not.

**The backend enforces nothing.** `UserMeasurementFields` validates only `gt=0`. Anything calling `PUT /user-measurements/me` directly — not through the form — can store a 400cm height, and it fails ~90 seconds later inside CLO. Closing this is the single biggest gain in this concern.

## Decision made 2026-08-19 — one range set, the pipeline's

> *"have only one validation range as per the pipeline, we will make changes in the frontend."*

**There is exactly one range set, and it is the pipeline's.** No separate UI range, no second set of numbers anywhere. The frontend changes to match the pipeline — not the other way round.

The consequence, accepted knowingly: **the form gets more permissive than it is today**, because the frontend is currently stricter on every single field. Weight goes 35–180 → 30–250, waist 50–140 → 40–220, and so on down the table above. If a value now feels too permissive in the UI, **the fix is to change the range in the contract** — which tightens the pipeline too — not to reintroduce a frontend-only limit. Reintroducing one recreates exactly the drift this concern exists to remove.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 4 — male-only frontend, both genders retained in pipeline and backend

**Status: NOT SOLVED — back in scope (user, 2026-08-19)**

Briefly deferred earlier the same day (*"for today leave the female as it is"*), then brought back in when the coding scope was set.

**Decision: female is shown but disabled.** Visible in the UI as unselectable — "coming soon" or equivalent — rather than hidden entirely. This closes the trap *and* signals the roadmap, which hiding it would not.

Gender is therefore effectively locked to male for anyone who can actually proceed. The backend and contract keep both genders exactly as they are — nothing is removed.

Concern 5's work makes the frontend derive its field list from the contract, and the contract filters by gender natively, so the male-only field *list* falls out of that for free. **Disabling the female option is the separate, deliberate part.**

User instruction, 2026-08-19: *"we will work only on males so keep all the fields as per both male and female in the pipeline and backend but for frontend only show the males one for now."*

## Current state — mostly already correct

- **Contract** — already holds both. `bust_circumference_cm` and `under_bust_circumference_cm` exist with `genders: [female]`, but `included_in_v1: false`.
- **Backend** — already holds both. `UserMeasurementFields` declares all 9 plus `body_shape_type` and `skin_tone_hex`. **Nothing to remove.**
- **Frontend** — the actual work. It renders 7 fields regardless of gender (`Object.keys(FIELD_META)`) and offers a male/female toggle at `measurement-form.tsx:35`.

## The live bug this closes

A female user can complete the form and save successfully, then fail avatar generation ~90 seconds in:

- `step_03_fetch_measurements.py:93` hard-rejects any gender but male: `"Step-1 CLO avatar generation currently supports male only"`.
- `get_v1_fields_for_gender("female")` returns **0 fields** — verified by running it.

So the toggle is a trap: it is a first-class choice in the UI, a validated `Literal["male","female"]` in the model, and an unsupported path in the pipeline.

## Two changes, and they must land together

1. The frontend derives its field list from the contract **filtered by gender**, instead of `Object.keys(FIELD_META)`.
2. **The gender toggle is locked to male.** Shipping male-only fields while leaving the toggle live preserves the trap rather than closing it.

**Open product question**: is female visible-but-disabled ("coming soon"), or hidden entirely? Not decided.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 5 — keeping measurement fields consistent permanently

**Status: NOT SOLVED**

User question, 2026-08-19: *"how can we ensure that the measurements field remain consistent throughout the project — everywhere frontend, backend, pipeline, measurements, user_measurements."*

## Why it drifts: six independent definitions, two languages

| # | Location | What it holds |
|---|---|---|
| 1 | `clo_avatar_generation/schema/step1_field_contract.json` | 9 entries, genders, CLO property keys |
| 2 | `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py` | `MEASUREMENT_RANGES` |
| 3 | `website/backend/src/user_measurements/models.py` | `UserMeasurementFields` (11 fields) |
| 4 | `website/backend/src/measurements/models.py` | the old collection's model |
| 5 | `mirra_measurements/avatar_model.py` | CLI-side model |
| 6 | `website/frontend/src/integrations/mirra-api/live-schemas.ts` | `KEY_TO_FIELD` + `FIELD_META` |

Six hand-maintained copies across Python and TypeScript. No amount of discipline fixes that; only structure does.

## Agreed approach — one source, one generated file, one test

Chosen by the user 2026-08-19.

1. **`step1_field_contract.json` becomes the single source of truth.** It is already the most complete definition and already lives in the pipeline — the component with the least flexibility, so everything else should bend toward it. Extend it with `min`, `max`, `label`, and the UI key.
2. **Backend reads it at import** rather than restating it, so #3 stops being an independent copy. #4 and #5 stay as they are — they are the CLI/legacy path the user has explicitly decided to keep (see doc 04's additive ruling) — but a test asserts their field names match.
3. **Frontend gets a generated file.** A script emits `measurement-fields.generated.ts` from the JSON. `scripts/port-landing.mjs` and `scripts/scope-marketing-css.mjs` already establish generated-file-with-a-regenerate-script as a repo pattern.
4. **One test that fails on drift.** It loads the contract and asserts every consumer matches: backend model field names, the generated TS file being current, and the two legacy models. **This is the part that actually enforces it** — without it the generator is just another thing people forget to run.

**Why a test rather than generating all five**: there are Python and TypeScript consumers plus two legacy models that are staying. Generating everything is a lot of machinery; generating the TS and *asserting* the rest gets most of the benefit for a fraction of the work, and fails loudly at the moment someone adds a field in one place.

## Ordering note

Concern 5 subsumes 3 and 4 — once the contract is the single source with ranges in it, "make everything consistent" (3) and "filter the frontend by gender" (4) both become consequences of reading from it rather than separate edits. Sequencing 3 and 4 as one-off fixes *before* 5 would mean doing the same work twice.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 6 — the wasted round trip on first measurement save

**Status: NOT SOLVED**

## What happens now

`http-runtime-provider.ts:161-176` tries `PATCH /user-measurements/me`, catches a 404, then falls back to `PUT`. On a user's **first ever** save the PATCH always 404s, so the first save is always two requests.

## Do we need PATCH at all? Yes

Both callers are genuinely different — verified 2026-08-19:

| Caller | Sends | Correct verb |
|---|---|---|
| `measurement-form.tsx:42` (empty state, first save) | all 7 fields, always | `PUT` |
| `ProfileMeasurements.tsx:24` (editing existing) | `draft` starts `{}` — **only changed fields** | `PATCH` |

Deleting PATCH would force the edit path to send a full merged document, reintroducing last-write-wins races on a form that currently only sends what was touched. **Keep PATCH.**

## Should first save be POST instead of PUT? No

`/user-measurements/me` is a **singleton** — one document per user, at an address fixed by the authenticated identity, with no server-chosen id to return.

- `PUT` is idempotent: saving twice leaves the same state, and a retry after a flaky connection is safe.
- `POST` is not, and means "create a new one in this collection" — implying many-per-user and an unknown id. Neither is true here.

`submit()` already does `replace_one(..., upsert=True)`, so `PUT` handles create *and* replace — which is precisely why the existing fallback works. Adding `POST` would be a third write endpoint doing what `PUT` already does, and pushes the wrong way on Concern 1.

## Approaches

| # | Approach | Cost | Verdict |
|---|---|---|---|
| **A** | **Caller passes intent.** `MeasurementForm` is rendered *inside* `if (!avatar)` (`ProfileMeasurements.tsx:32`), so the caller already knows it is a first save. Add a `mode` argument, or a separate `submitMeasurements()`, that goes straight to `PUT`. | ~10 lines, client only | **Recommended — today and later.** One round trip, no API change, no semantics change. |
| B | Make `PATCH` upsert when absent, so it never 404s. | backend change | **Reject.** `PATCH` carries no `gender`/`accuracy`, so upserting means defaulting them — silently storing `male`/`approx` for someone who never said so. |
| C | Always `PUT`, drop `PATCH`, merge client-side. | removes an endpoint | Helps Concern 1, but reintroduces last-write-wins races on partial edits. Not worth it. |
| D | Add `POST` for creation. | new endpoint | **Reject.** See above. |

There is no simple-now/efficient-later split here: **A is both.**

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 7 — the avatar tab shows far too much

**Status: NOT SOLVED**

User instruction, 2026-08-19: *"this much information is too much, just show the white doll in center and a loading bar which goes from 0 to 100% in 90s. no other unnecessary text."*

Today the tab shows a headline, two paragraphs, a five-segment stage strip, a reassurance line, a status pill, and a preferences footnote.

## Target

White doll centred, one progress bar, nothing else.

## Three things behind that screen that are not cosmetic

**1. The progress bar is necessarily fake.** The backend has four stages only (`STAGE_LABELS` in `avatars/models.py:14` — queued / processing / ready / failed). **No percentage exists.** A 0→100%-over-90s bar is a synthetic timer, not real progress. That is a normal and acceptable UI choice, but it must not reach 100% and sit there while the run is still going. Agreed behaviour: **animate toward ~95% over 90s, hold, then snap to 100% the moment the GLB is actually ready.**

**2. Deleting the "leaving this page will lose track of the run" line removes a true warning.** The job id lives only in component state — that is **B4**, deferred. Removing the sentence without fixing B4 keeps the trap and hides it. Either B4 comes along, or this is a knowingly accepted regression.

**3. Failure needs somewhere to go.** Stripping to a doll and a bar leaves no surface for "generation failed". A minimal error state is still required, even if unstyled.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 8 — generation should start when measurements are saved

**Status: NOT SOLVED**

User instruction, 2026-08-19: as the backend receives new measurements, write to Mongo **and** enqueue the CLO worker job at the same time, then move the frontend to the avatar tab.

This is **B3** in `02-remaining-work.md`, previously deferred on purpose.

## Today's behaviour

`ProfileMeasurements.tsx:44` renders `<MeasurementForm />` with **no `onSaved` handler and no navigation**. After a successful save the user stays put: no generation, no redirect, no prompt. They must find `/profile/avatar` themselves and press generate.

## Why it was deferred, and what still applies

CLO is **concurrency = 1**. Every trigger is a real ~90-second run. Auto-triggering means:

- Two users saving at once queue behind each other. The second one's bar sits at ~95% for up to ~3 minutes.
- Every measurement edit becomes a new run unless something suppresses re-triggering on trivial changes.

Neither blocks the work — but the progress UI in Concern 7 has to be honest about queueing, and "save" becomes an expensive action rather than a cheap one.

## Approaches

| # | Approach | Verdict |
|---|---|---|
| **A** | **Backend enqueues inside `submit()`/`patch()`**, same request, before returning. | **Simplest, recommended for today.** One round trip, no client coordination, impossible for the client to forget. |
| B | Client calls `POST /avatars/generate` after a successful save. | Works, but a client that crashes between the two calls leaves measurements with no run. |
| C | A Mongo change stream or watcher that reacts to writes. | Most decoupled, most machinery. Not for now. |

## Trigger policy — decided 2026-08-19

**Every save re-triggers generation, for now.** Simplest rule, and correct while usage is a handful of people.

> *"every save for now, in future we will add a check on the frontend which only send request when there is a change in the field, and people can send request after a particular time only."*

**Known cost, accepted deliberately:** a user nudging one field three times queues three full ~90-second CLO runs, and with concurrency = 1 they serialise behind each other and behind everyone else. This is survivable at pilot scale and will not be at any real scale.

**Future work, not now** — two guards, both frontend-side:
1. **Change detection** — only send when a measurement value actually differs from what is stored. Suppresses the no-op save entirely.
2. **Rate limit** — a minimum interval between generation requests per user.

Do not implement either now, and do not treat their absence as an oversight when reading this later.

## Background: the one avatar currently on disk

`dev_upload/avatars/g_241f677bd4b8f8a4/001/` — looked up across all collections 2026-08-19:

```
users              FOUND   is_guest=True   created 2026-08-08
measurements       FOUND   gender=male     ← the OLD collection
user_measurements  not found
avatar_profiles    FOUND
avatar_jobs        FOUND
```

A **guest account** from 8 August. `run.log` shows `00:30:18` → `00:31:32` — **~74 seconds** — with `Measurement source: mongodb` (the bare label, from before A1 started naming the collection).

**This is the A1 bug preserved in amber.** That avatar exists because its measurements were in `measurements`, which is what the pipeline read at the time. It has no `user_measurements` document at all. Every real user since writes to `user_measurements`, which the pipeline could not see — which is exactly why A1 was needed. It is the last avatar generated before the two halves drifted apart, and it is a useful fixture precisely because of that.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 9 — displaying the generated GLB in the frontend

**Status: NOT SOLVED**

User instruction, 2026-08-19: *"today our target is to show the avatar only. we will first build it and then make it pretty."* File size, failure states, and timing are explicitly **out of scope for today**.

## Starting position

- `GET /api/v1/avatars/profile/glb` is live (doc 04, A2) with `model/gltf-binary` and immutable caching.
- `GET /api/v1/avatars/jobs/{job_id}` is live for polling.
- `three`, `@react-three/fiber`, `@react-three/drei` are **already in `package.json`** — no dependency change needed.
- **There is no 3D rendering anywhere in the frontend today.** Grepping for `Canvas`, `useGLTF`, `GLTFLoader` returns zero matches. Those three packages are installed and entirely unused. This is new code, not a reuse job.

## The constraint that rules out the obvious approach

Requests authenticate with `Authorization: Bearer <jwt>` from in-memory storage (`client.ts:117`), and `auth_dependency.py:26` rejects anything without that header.

**A 3D loader given a URL fetches with a plain request carrying no Authorization header.** Point `useGLTF` straight at `/avatars/profile/glb` and it 401s. The simplest-looking approach is the one that does not work.

## All approaches

| # | Approach | How | Trade-offs |
|---|---|---|---|
| **A** | **Authed fetch → blob URL → `useGLTF`** | Fetch the GLB through the existing authed client as a blob, `URL.createObjectURL(blob)`, hand that to `useGLTF`. `revokeObjectURL` on unmount. | **Today's choice.** No backend change, no new dependency, ~30 lines. **Defeats the immutable caching** the route already sends — every mount re-downloads 30 MB. `useGLTF` caches by URL and blob URLs are new each time, so it will not dedupe across mounts. |
| **B** | **Cookie-auth the GLB route** | Switch that one endpoint to the refresh-cookie auth, so a plain URL works and `useGLTF` can be pointed at it directly. | **The efficient answer later.** Restores real HTTP caching — the browser caches a 30 MB immutable asset properly, which is the whole point of the headers Lane 1 wrote. Cost: this endpoint authenticates differently from every other route, which is a deliberate design decision, not a shortcut. |
| C | Short-lived signed URL | Backend issues a time-limited signed link; loader fetches it unauthenticated. | Standard for media at scale. Real caching, no auth inconsistency. Most machinery — needs signing, expiry, and a way to refresh a stale link mid-session. |
| D | Serve avatars from static/CDN with unguessable paths | Move GLBs out of the API entirely. | Best performance eventually. Security by obscure path unless combined with C. Premature now. |
| E | `<model-viewer>` web component | Google's drop-in viewer. | Fewer lines than A, but it is a **new dependency** and still hits the same auth problem — a blob URL would be needed anyway. No advantage over A here. |
| F | Raw `three` + `GLTFLoader` by hand | Manual scene, camera, lights, loop. | More code than A for no benefit; `@react-three/fiber` is already installed. |

## Today (A), later (B or C)

**Today:** approach **A** — authed blob fetch, `<Canvas>` + `<Suspense>` + `<primitive object={scene} />` + `<OrbitControls>` and a light.

**Later:** **B** is the smallest step to real caching; **C** is the right destination if avatars are ever served at volume or from a CDN. Deferring is a conscious choice, not an oversight: A's re-download cost is invisible on localhost and very visible on real network.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 10 — the CLO3D queue must handle many users, one at a time

**Status: NOT SOLVED**

User instruction, 2026-08-19: *"make that queue also work, even if many people come they should be able to generate their avatar one by one, no time constraint. there should just be progress."*

## The queue already exists and already does this

Verified 2026-08-19 — this is not new infrastructure to build:

- `website/backend/src/avatars/engine.py:18` enqueues `worker.tasks.run_avatar_job` via Redis/RQ.
- `worker/run_worker.py:57` runs an **`rq.worker.SimpleWorker`** over that queue — one job at a time, in-process, no `os.fork()` (Windows cannot fork).
- `AVATAR_JOB_TIMEOUT_SECONDS = 20 * 60` (`engine.py:12`) — a generous ceiling well above a ~90s run.
- Job state is persisted in Mongo as stages: `JOB_STATES = ("queued", "processing", "ready", "failed")`, written **only by the worker** (`avatars/models.py:31`).

So ten users saving at once already results in ten queued jobs processed strictly one after another. **Serialisation is not the gap.** The `SimpleWorker` choice is what enforces concurrency = 1, and must never be "simplified" to the default `rq.Worker`.

## What is actually missing

**1. The user cannot see their place in the queue.** `queued` and `processing` are distinguishable, but nothing exposes *how many are ahead*. The tenth user sees the same screen as the first for ~15 minutes with no explanation.

**2. The synthetic 90s progress bar (Concern 7) is wrong while queued.** It assumes the run started. Someone waiting behind five others would watch it crawl to 95% and stall, which reads as "broken" rather than "waiting". The bar must not start until the job reaches `processing`; while `queued` the UI needs a different, non-time-based signal.

**3. Job ids live only in component state (B4).** With a real queue this stops being a minor annoyance: a user who navigates away during a genuinely long wait loses the run entirely, even though the worker will still complete it.

**4. Nothing enforces one worker.** The rule "never start two workers against the same CLO instance" is documented in `01` but not mechanically prevented. Two workers would each pull jobs and corrupt each other's CLO scene state.

## Approaches for surfacing position

| # | Approach | Trade-offs |
|---|---|---|
| **A** | **Return `queued`/`processing` only, no position.** UI shows an indeterminate state while queued, the timed bar once processing. | **Simplest, honest.** No new backend work beyond what the job doc already carries. No "3rd in line" reassurance. |
| **B** | **Count ahead in Mongo** — `count_documents({state: "queued", created_at: {$lt: mine}})` on the job status endpoint. | Cheap, no new infrastructure, accurate enough. Reads a collection that is already indexed by state. **Recommended once A is working.** |
| C | Ask RQ for queue position (`Queue.get_job_position`). | Authoritative about the actual queue, but couples the API to RQ internals and is O(n) on the queue. |
| D | Push updates over WebSocket/SSE instead of polling. | Best UX, most machinery. Not now — polling `GET /avatars/jobs/{job_id}` already exists and works. |

**No time constraint is the right call** — the 20-minute job timeout is per-job execution, not per-wait, so a long queue does not cause failures. Worth confirming that RQ's queue has no TTL that would silently drop a job waiting behind many others.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 11 — the worker should not talk to MongoDB Atlas at all

**Status: NOT SOLVED**

User decision, 2026-08-19: *"i would go with the design change of using backend to read and write everything. the backend will always be up so that is not an issue."*

The backend owns all database access. The worker runs CLO and reports results back through the backend. It holds no Atlas credentials and opens no database connection.

**This decision was not forced by the DNS failure.** The DNS problem (below) is a broken resolver on one machine and is fixed by one command; redesigning around it would be treating a symptom. This is a separate, deliberate architectural choice: the worker is a native Windows process living outside the container network, and giving it fewer external dependencies and no database credentials is sound on its own merits.

## Every place the worker process currently touches Atlas

**Three touchpoints, not one.** Removing only the obvious one leaves the dependency fully intact.

**1. `worker/tasks.py` — 11 direct operations** via `src.db` collections (imported at `tasks.py:43`):

| Line | Operation | Purpose |
|---|---|---|
| 87 | `find_one(avatar_jobs)` | read job → `measurement_snapshot`, `user_id` |
| 93 | `update_one` → `processing` | claim the job |
| 131 | `update_one(avatar_profiles)` | write `avatar_glb_path`, `clo_avatar_avt_path`, `clo_run_id` |
| 143 | `update_one` → `ready` | + `avatar_profile_id`, `completed_at` |
| 168 | `update_one` → `failed` | + `failure_reason` |
| 182 | `find_one(tryon_renders)` | read render |
| 188 | `update_one` → `rendering` | |
| 190 | `find_one(avatar_profiles)` | resolve `clo_avatar_avt_path` for VTO |
| 224 | `update_one` → `ready` | |
| 231 | `update_one` → `failed` | |

**2. `avatars_service._materialize_profile()` — the hidden one.** `tasks.py:118` calls a *backend service function directly* (imported at `tasks.py:41`), which performs its own `find_one` + `replace_one` internally (`avatars/service.py:50-68`). Nothing at that line looks like a database call. **Do not miss this one.**

**3. `clo_avatar_generation/avatar_runtime/step_03_fetch_measurements.py`** — reads the measurement collections *inside the pipeline*, through `mirra_measurements/db.py`. A completely separate connection from `src.db`.

## Two of the three are nearly free

**The pipeline already has a Mongo-free route.** `step_03:134` — when `ctx.measurement_file_input` is set, measurements are loaded from JSON and **Mongo is never opened**. Today `tasks.py:102` passes `measurement_file_input=None`, which is the only reason it hits the database.

The job document **already carries `measurement_snapshot`** — exactly the data needed. So: write the snapshot to a temp JSON file, pass the path, and **touchpoint 3 disappears with no pipeline changes whatsoever.**

**Everything else in the worker is already Mongo-free.** Verified 2026-08-19: `get_next_run_number()` (`run_manifest.py:63`) is filesystem-only, and `worker/live_upload.py` contains zero Mongo calls.

## What has to be built

An internal API for the worker to report through — roughly five endpoints:

```
GET  /internal/avatar-jobs/{job_id}          → job + measurement_snapshot
POST /internal/avatar-jobs/{job_id}/state    → processing | ready | failed
POST /internal/avatar-jobs/{job_id}/result   → glb path, avt path, clo_run_id
GET  /internal/tryon-renders/{render_id}     → render + resolved avt path
POST /internal/tryon-renders/{render_id}/state
```

The result endpoint takes ownership of `_materialize_profile`, which moves fully backend-side — where it arguably belonged already.

**Auth is the genuinely new work.** Verified 2026-08-19: **no internal or service-to-service auth exists anywhere in the backend** — no API key, no shared secret, no service token. Every route uses a user Bearer JWT (`core/auth_dependency.py:26`), and the worker has no user.

So this needs a service-auth mechanism built from scratch, plus a decision on whether `/internal/*` is network-exposed at all or bound to loopback. **The honest cost of this concern is not "swap 11 calls for 11 HTTP requests" — it is that, plus an auth scheme the codebase does not currently have.**

## What gets deleted

- `tasks.py:43` — the `src.db` import and all 11 collection calls.
- `tasks.py:41` — the `src.avatars.service` import; `_materialize_profile` moves backend-side.
- `MONGODB_URI` from `worker/.env` — **the worker stops needing Atlas credentials entirely.** A real security win for a native process outside the container network. *(User edits `.env` — no agent reads or writes it.)*
- Possibly the `sys.path` hook into `website/backend` (`tasks.py:31-34`), if shared document shapes move to a small shared package.

**What must NOT be deleted:** `step_03`'s Mongo path stays. `run_avatar.py --user-id u_001` (CLI, golden users) depends on it, and doc 04's A1 ruling is explicit that nothing is removed. Website runs take the JSON path; CLI runs keep reading Mongo directly. **Both routes stay alive in the same file.**

## Approaches

| # | Approach | Trade-offs |
|---|---|---|
| **A** | **Internal HTTP API + service token**, worker writes snapshot to temp JSON for the pipeline. | **The chosen design.** Clean boundary, no DB credentials on the worker, `_materialize_profile` lands where it belongs. Cost: five endpoints plus a new auth scheme. |
| B | Report results back over Redis (worker publishes, backend consumes). | No new auth — Redis is already a trusted shared channel. But results become fire-and-forget, and Redis is not a durable store for something that took 90 seconds to produce. |
| C | Keep Mongo writes, only remove the pipeline's read. | Smallest change, and would have sidestepped DNS — but leaves credentials on the worker and does not deliver the decision above. |
| D | Backend polls RQ job status instead of the worker reporting. | RQ knows a job finished, not what it produced. Would still need a results channel. |

## Two properties being traded away — worth naming, not blockers

**Shared-model coupling becomes a wire contract.** `tasks.py:9-11` states the current rationale outright: the worker reuses backend Mongo models *"so job, profile, and render document shapes never drift from what the FastAPI app itself reads/writes."* Over HTTP that guarantee is gone. Normal for a service boundary — but prefer a shared schema package over duplicated dataclasses, or the drift this comment warns about arrives by a different door.

**Failure handling changes shape.** Today a Mongo write succeeds or throws locally. Over HTTP, a 90-second CLO run can complete and *then* fail to report — the avatar exists on disk while nothing in the database knows. The user's position is that the backend is always up, which is reasonable; note that "always up" still includes restarts and deploys. A small retry on the result call covers it cheaply and should be in scope from the start, not added after the first lost run.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Concern 12 — avatar viewer loading cost: bundle size, re-download, no code-splitting

**Status: DEFERRED — knowingly accepted today (user, 2026-08-19)**

> *"understood there is loading issue... the size, re-downloading every mount issue and lazy loading, we will solve it later not today."*

Concern 9 shipped the viewer with three known performance costs. All three were visible at the time of the decision — none is a surprise to be rediscovered later.

## 1. The `ProfileAvatar` chunk grew from 2.62 kB to 997 kB

Measured from `npm run build`, 2026-08-19:

```
before:  dist/assets/ProfileAvatar-CIhJS5nt.js    2.62 kB │ gzip:   1.07 kB
after:   dist/assets/ProfileAvatar-9Qxu7DfK.js  997.20 kB │ gzip: 271.35 kB
```

That is `three` + `@react-three/fiber` + `@react-three/drei` landing in the profile-avatar chunk. Vite emits its >500 kB chunk warning on this build.

**Mitigating factor**: the route is already lazy-loaded in `router.tsx`, so this never touches the marketing pages or first paint. The cost is paid only by someone opening `/profile/avatar`.

**Fix later**: dynamic-import the viewer component itself, so the rest of the avatar page (measurements state, progress, buttons) paints while the 3D runtime streams in behind it.

## 2. The GLB re-downloads on every mount

`GET /avatars/profile/glb` sends `Cache-Control: public, max-age=31536000, immutable` — but the viewer cannot benefit from it. The route requires an `Authorization` header, so the file is fetched through the authed client and passed to the loader as an object URL (Concern 9, approach A). Object URLs are new on every mount, so:

- The browser's HTTP cache is bypassed for this asset.
- `useGLTF` caches by URL, so it cannot dedupe across mounts either.

That is **~29 MB per mount**. Invisible on localhost, very visible on a real connection.

**Fix later**: Concern 9's approach **B** (cookie-auth the GLB route so a plain URL works and real HTTP caching applies) or **C** (short-lived signed URL). A React Query `staleTime: Infinity` already avoids re-fetching within a single session, so the acute case is reload and navigation.

## 3. No progressive loading

The model appears only once all ~29 MB have arrived. There is no streaming, no low-poly placeholder, no percentage. The skeleton simply sits there.

**Fix later**: a Draco/meshopt-compressed GLB would cut the payload substantially, and a progress indicator driven by `Content-Length` would at least make the wait legible.

## Why all three are deferred

The user's framing for today: *"we will first build it and then make it pretty."* Getting the avatar on screen was the goal; these are optimisation, and each has a clear, known fix. **Do not treat any of them as a defect discovered later** — they were measured and accepted on the day.

## What we did

*(Empty until the user has verified the work and given permission to write here.)*

---

# Appendix — the DNS failure that surfaced Concern 11

**Not a code defect. Recorded so it is not re-diagnosed from scratch.**

The worker could not reach Atlas from this machine. Root cause, established 2026-08-19: **the router at `192.168.0.1` silently drops every DNS response larger than ~512 bytes.**

`mongodb+srv://` requires an SRV lookup plus a TXT lookup before any connection is attempted. Atlas answers with three long hostnames plus options — over the 512-byte UDP limit, needing EDNS0 or TCP fallback, which that router handles for neither. The reply simply never arrives; the driver times out after 21s having never obtained an address.

Evidence — every large response fails through the router and succeeds instantly through Google DNS:

```
google.com      192.168.0.1  FAIL LifetimeTimeout 6.4s
google.com      8.8.8.8      OK  15 recs ~854B   0.0s
microsoft.com   192.168.0.1  FAIL LifetimeTimeout 6.4s
microsoft.com   8.8.8.8      OK  61 recs ~4177B  0.1s
cloudflare.com  192.168.0.1  FAIL LifetimeTimeout 6.4s
cloudflare.com  8.8.8.8      OK  28 recs ~2130B  0.0s
```

**A misleading earlier data point**: a *small* SRV record resolved fine through the router, which made SRV look healthy and sent the diagnosis elsewhere. Response **size** is what matters, not record type.

Docker is unaffected because Docker Desktop resolves through its own resolver inside its Linux VM, not the router — which is why the identical URI works in the backend container and fails natively.

**Fix (needs elevation, user runs it):**

```powershell
Set-DnsClientServerAddress -InterfaceIndex 7 -ServerAddresses 8.8.8.8,1.1.1.1
# revert: Set-DnsClientServerAddress -InterfaceIndex 7 -ResetServerAddresses
```

Interface 7 is the Wi-Fi adapter. This affects every native process on the machine — anything else needing a large DNS record is currently broken too.

**Still worth fixing even after Concern 11 lands.** Concern 11 removes the worker's *Mongo* dependency, not the machine's broken resolver. Any other native process needing a large DNS record will hit the same wall.

---

## Not tracked elsewhere

None of Concerns 1-5 appear in `02-remaining-work.md`, including Group F (security / launch-readiness). Concern 2 belongs in Group F when scheduled, since it is launch-readiness rather than a feature.

Concerns 7, 8, 9 and 10 overlap existing items: **8 is B3**, and **7 and 10 both depend on B4**. When any of them is scheduled, update `02-remaining-work.md` rather than letting the same work be tracked in two places with different status.

## Reading order if these are worked together

Concerns 6-10 are one feature — *save measurements → generate → watch progress → see the avatar* — and they interlock:

- **8** starts the run, so it comes first.
- **10** determines what progress can honestly be shown, so it constrains **7**.
- **7** must not begin its timed bar until **10** reports `processing`.
- **9** is what happens at the end and is independent of the other three.
- **B4** (job id survives navigation) is **in scope** as of 2026-08-19 — the user included it once it became clear that 7 and 10 both assume it. It needs a "latest job for this user" lookup so progress survives a refresh. Without it, both would ship with a known hole.

**Correction, 2026-08-19 — an earlier version of this note overstated a dependency.** It claimed Concern 11 must land before 8 and 10 or after all of them, on the grounds that it "rewrites the mechanism 8 triggers and 10 reads". That is wrong. **8** enqueues (backend → Redis) and **10** counts queued job documents (backend → Mongo); Concern 11 changes only *who writes* job state — the worker. The enqueue and read paths are untouched, so **8 and 10 can be built now without 11 forcing rework.**

## Scope and decisions for the current coding round (2026-08-19)

In scope: **3, 4, 5, 6, 7, 8, 9, 10, plus B4.** Not in scope: 1, 2, 11.

Order:
1. **Concern 9** first — independent, verifiable against the existing guest avatar with no CLO/worker/DNS, and it independently proves A2.
2. **Concern 5**, with **3** and **4** falling out of it. Doing 3 or 4 first means doing the same work twice.
3. **Concern 6**, then **8** — same save path, 6 first.
4. **B4**, then **10**, then **7** — each determines what the next can honestly show. 7 must not start its timed bar until 10 reports `processing`.

Execution: **the orchestrating session does this work directly. No subagents** (user decision) — these concerns share files (`step1_field_contract.json`, `live-schemas.ts`, `http-runtime-provider.ts`, `ProfileAvatar.tsx`) and the ordering is strict, so coordination overhead would exceed the benefit.

**Concern 9 is the one piece that can start immediately.** Verified 2026-08-19: the existing guest avatar is already servable through the A2 route — `avatar_profiles` holds `avatars/g_241f677bd4b8f8a4/001/avatar.glb`, the container resolves it via the compose mount, and the 29.1 MB file is present. So the viewer can be built and tested with no worker, no CLO, and no DNS fix — and doing so **independently verifies A2**, which currently has no live proof. (`source_measurements_version` is `None` on that row, so the staleness header reports `unknown` — documented behaviour for avatars predating the field, not a bug.)
