# Photo measurement, QR hand-off, female avatars, face layer — what was added

Written 2026-10-05. Everything below is **uncommitted working-tree change on
`Madhavan`**. Nothing here has been run against a real CLO install yet; Part 3
is the runbook for doing that. The session-by-session log (with the audit that
led to these changes) is `.agent/website-launch-2/14-photo-measurement-and-merchant-linking.md`.

## 0. What this is, in one picture

```
shopper (browser)                     phone (no sign-in)
  /profile/measurements                 /capture/<token>   ← QR from /onboarding/qr
  /onboarding/qr  ──────────────────────┘
  /profile/avatar  (+ "Your face")
        │  REST (/api/v1)                       │ token-scoped REST
        ▼                                       ▼
  FastAPI backend ── Mongo (user_measurements, photo_measurements,
        │              photo_pairings, face_captures, avatar_jobs, …)
        │  Redis / RQ
        ├── queue "measure" ──► worker (no CLO): photo_measurement/ , face_reconstruction/
        └── queue "clo"     ──► worker (needs CLO): clo_avatar_generation/ , clo_vto/
```

| Layer | Folder | What it does | Needs CLO |
|---|---|---|---|
| Photo measurement | `photo_measurement/` | front + side photo + height → body measurements | no |
| QR hand-off | backend `photo_measurements/pairing.py`, frontend `QrPairing.tsx`, `CaptureLink.tsx` | desktop shows a QR; signed-out phone uploads into that account | no |
| Face reconstruction | `face_reconstruction/` | 1–3 face photos → textured face mesh `face.glb` | no |
| Female avatars | `clo_avatar_generation/` (contract + steps 03–05) | women's profiles build a female CLO avatar | **yes** |
| Merchant ↔ shopper | backend `merchant/`, `catalog/`; frontend dashboard | workspace creation, seats, Shopify card, shopper catalogue gate | no |

## 1. Change inventory

"New" = new file/folder. "Edit" = existing file modified.

### 1.1 Photo measurement
- New `photo_measurement/` — inference-only copy of the R&D pipeline
  (`capture.py` MediaPipe pose, `measure.py`/`geometry.py` geometry, `bmnet/`
  network, `report.py`, `pipeline.py` entry point, `run_photo_measurement.py` CLI,
  22 tests). Model weights are **not in git** (see 2.3).
- New backend `website/backend/src/photo_measurements/` (`models, storage,
  service, engine, pairing, controller, routes, schemas`), collection
  `photo_measurements`.
- New `worker/measure_tasks.py`; edit `worker/tasks.py`
  (`run_photo_measurement`, `run_face_reconstruction`), `worker/run_worker.py`
  (`--queues clo|measure`), `website/backend/src/core/queue.py` (named queues).
- Edit `user_measurements/{models,service}.py` — optional `source`
  (`manual|photo`) and `photo_capture_id`; `submit()` takes them.
- Edit `users/service.py` — account deletion also removes photo captures,
  pairings and faces.
- Edit `db.py`, `main.py` — collection accessors/indexes, router mounting.
- Frontend: new `features/profile/components/{photo-measurement,measurement-entry}.tsx`;
  edit `pages/profile/ProfileMeasurements.tsx` (photos tab + "Re-measure from photos"),
  `integrations/mirra-api/{types,live-schemas,runtime-provider,http-runtime-provider}.ts`
  (+ test file).
- Data rules: photos are deleted by the worker after measuring (success or
  failure); captures stuck >1 h are failed and their photos deleted; the shopper
  reviews/corrects numbers before `apply` writes them as `accuracy: "approx"`.

### 1.2 QR hand-off (phone, no sign-in)
- Backend `pairing.py`: 192-bit token, stored hashed, 20-min TTL, new code
  revokes the old one, max 5 uploads; the phone sees progress only, never numbers.
- Routes: `POST /photo-measurements/pairings`, `GET …/pairings/{id}` (desktop);
  `GET|POST /photo-capture/{token}`, `GET …/capture`, `POST|GET …/face` (phone).
- Frontend: new `pages/onboarding/CaptureLink.tsx`; edit `pages/onboarding/QrPairing.tsx`
  (real code, live status), `router.tsx` (`/capture/:token`), `ProfileAvatar.tsx`
  (`?generate=1` auto-starts avatar generation once).

### 1.3 Female avatars (CLO pipeline)
- Edit `clo_avatar_generation/schema/step1_field_contract.json` → `v2-draft`,
  `male_and_female`: shared fields for both; chest male-only; **bust = `.avt`
  slot 2** (female); under-bust optional, property/CSV route only;
  `base_avatars` per gender.
- Edit `avatar_runtime/{field_contract,step_03_fetch_measurements,step_04_resolve_base_avatar,step_05_normalize_targets}.py`
  — gender-aware validation, per-gender base avatar, "chest used as bust" fallback
  for manual female profiles, optional fields.
- Edit `worker/tasks.py` — no longer forces the male base avatar.
- New `clo_avatar_generation/tests/test_gender_contract.py` (5 offline tests).

### 1.4 Face layer
- New `face_reconstruction/` — MediaPipe Face Landmarker (Apache-2.0) →
  iris-scaled metric mesh → fused views → UV texture → `face.glb`
  (`landmarks, canonical, reconstruct, glb, pipeline`, CLI, 6 tests, README).
  FLAME was the original plan but is registration-gated and research-only.
- New backend `website/backend/src/faces/`, collection `face_captures`;
  `POST /faces`, `GET /faces/latest|{id}|current/glb`, `DELETE /faces`.
- New `worker/face_tasks.py` (one face per user; older ones removed).
- Frontend: new `face-attachment.ts` (+test), `face-capture.tsx`; edit
  `avatar-glb-viewer.tsx` (`withFace`), `glb-query-keys.ts`,
  `studio/components/avatar-stage.tsx`, `ProfileAvatar.tsx` ("Your face" panel).

### 1.5 Merchant ↔ shopper fixes
- Backend `merchant/`: `POST /merchant/workspaces` (business account creates a
  workspace and owns it), `POST /merchant/{id}/members` (seat an existing account),
  workspace responses carry the caller's `role`; `shopper_size_ids()` gate.
- Backend `catalog/service.py`: merchant cloths (`brand_id` set) are listed,
  fetched and therefore try-on-able **only when QA-approved + live + rendered**
  (seeded cloths unaffected).
- Frontend dashboard: new `data/live-session.ts`, `pages/Start.tsx`,
  `components/{shopify-connect,live-seat-card}.tsx`; edit `dashboard-layout.tsx`,
  `dashboard-routes.tsx`, `routes.ts`, `data/{actions,merchant-api}.ts`,
  `pages/portal/{Settings,Team,GarmentFlow}.tsx`, `pages/business/destination.ts`.
  `/business/login` → `/dashboard/start`; demo persona picker stays at `/dashboard/login`.

### 1.6 Infrastructure / config
- `requirements.txt`: `opencv-python` → `opencv-contrib-python==4.10.0.84`
  (same version, superset; avoids two `cv2` copies) and `mediapipe>=0.10.14,<0.11`.
  **Everyone must re-run `pip install -r requirements.txt`.**
- `docker-compose.yml`: upload folders mounted read-write (were `:ro`, which broke
  every API upload inside the container).
- `dev_upload/.gitignore`, `live_upload/.gitignore`: ignore `captures/`,
  `measurement_photos/`, `face_photos/`, `faces/` (photos of people's bodies/faces).
- `mirra_measurements/db.py`: database name read from `DATABASE_NAME`.
- `worker/.env.example`, `worker/README.md`: new vars, how to run the `measure` worker.
- Tests: `website/backend/tests/{test_photo_measurements,test_faces}.py`,
  additions to `test_merchant_api.py`, `fake_mongo.py` helpers.

### 1.7 Not mine — other work in the tree
These were present or changed by others while this was being built, and are **not
covered or verified here**: backend `src/capture/` (new), edits to
`avatars/service.py` (reserved job id / failure on queue error), the new request
types in `photo_measurements/schemas.py` (`buildAvatar`, `skipFace`, capture
stages), and `website/frontend/public/profile/capture-*.webp`. They look like a
combined "setup" flow (measure → face → build avatar, resumable). Re-run the
test suites (Part 4) after that lands, since it touches the same routes and
`avatars/service.py`.

## 2. Setup (any machine)

### 2.1 Python
```bash
cd integration-mvp
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
Python 3.12. Torch is pinned to 2.4.1; the BMnet checkpoint was trained on a
newer torch and loads fine on 2.4.1 (verified).

### 2.2 Environment files (never commit)
- `website/backend/.env` (or `.env.docker.dev` for Docker): `MONGODB_URI`,
  `DATABASE_NAME`, `REDIS_URL`, `ACCESS_TOKEN_SECRET`, Google OAuth vars, `APP_ENV`.
- `worker/.env` (copy `worker/.env.example`): `MONGODB_URI`, `DATABASE_NAME`
  (**same value as the backend**), `REDIS_URL=redis://localhost:6379/0`,
  `APP_ENV` (**same as the backend** — it picks `dev_upload/` vs `live_upload/`).
- `mirra_measurements/.env`: `MONGODB_URI` (the CLO pipeline reads measurements).

### 2.3 Files not in git
| File | Size | Where | Source |
|---|---|---|---|
| `bmnet.pt` | ~92 MB | `photo_measurement/models/` | copy from the R&D repo `for_measurements/models/bmnet.pt` |
| `pose_landmarker_full.task` | ~9 MB | `photo_measurement/models/` | auto-downloaded on first use |
| `face_landmarker.task` | ~3.7 MB | `face_reconstruction/models/` | auto-downloaded on first use |
| `base-female.avt` | ~34 MB | `clo_avatar_generation/input/` | CLO's stock `Female_V2/FV2_Feifei.avt` |
| `base-1.avt` (male) | ~34 MB | `clo_avatar_generation/input/` | already in the repo |

### 2.4 Run everything
```bash
docker compose up -d redis backend                      # API on :8000 (needs website/backend/.env.docker.dev)
cd website/frontend && npm install && npm run dev       # UI on :3000
python worker/run_worker.py --queues measure            # photo + face jobs (no CLO)
python worker/run_worker.py                             # CLO jobs — only on the CLO machine
```
The API and **both** workers must see the same `dev_upload/` (or `live_upload/`)
folder, because photos and GLBs travel through it. Run the workers from the same
checkout the Docker volume mounts. Start the two workers as separate processes:
a photo job takes seconds, a CLO job 20+ minutes.

### 2.5 Tests
```bash
cd website/backend && PYTHONPATH=../.. python -m pytest      # 99
python -m pytest photo_measurement/tests face_reconstruction/tests clo_avatar_generation/tests product_ingestion/tests   # 68
cd website/frontend && npx tsc --noEmit && npx vitest run     # 49
```

## 3. Runbook for the machine that has CLO

Prerequisite: CLO3D open with the REST plugin loaded
(`http://localhost:50505/health` answers). See `clo_workspace/README.md`.
Do the steps in order; stop at the first failure and write down what happened.

1. **Baseline (male).** `python clo_avatar_generation/run_avatar.py` for the
   existing golden male user. Expect an `.avt`, a GLB and a step-09 readback equal
   to what was requested. If this fails, nothing below is meaningful.
2. **Female base avatar.** Copy CLO's `Female_V2/FV2_Feifei.avt` to
   `clo_avatar_generation/input/base-female.avt`. Create a `user_measurements`
   document with `gender: "female"` including `bust_circumference_cm`, run the
   pipeline, and compare the readback to what was sent. **Confirm the slot
   assumption:** Bust in `.avt` slot 2; Total Height/Waist/Low Hip/Inseam/Shoulder in
   slots 0/6/8/26/36. If any differ from the male avatar, fix
   `schema/step1_field_contract.json` (and its `female_note`) and add a test. Check
   whether Under Bust and Weight can be applied on the property or CSV route.
3. **Whole flow in the app.** Start Redis, backend, frontend and both workers.
   Sign in → `/onboarding/qr` → scan on a phone → body photos → review on the
   desktop → save → avatar builds → add a face on `/profile/avatar`. Note every
   break, with a screenshot (Chrome extension if available).
4. **Face placement.** Open the built avatar and the face together. The face must
   sit on the face: right way round, nose-to-nose, not floating or sunk. If not,
   tune the constants in
   `website/frontend/src/features/profile/components/face-attachment.ts`
   (nose band, cheek band, skin offset) and extend its test. The head-finding is
   only verified on synthetic bodies.
5. **Try-on.** Run one garment through `product_ingestion` and `clo_vto`
   (`python clo_vto/run_clo_vto.py`), then open it in `/studio`. The try-on GLB
   must show with the face still attached.
6. **Write up** results in `.agent/website-launch-2/14-…md` (what passed, what
   failed, what was changed).

## 4. Known gaps and risks

1. **Female CLO avatars are untested** against a real CLO install (step 2 above).
2. **Face on a real avatar is untested** (step 4). Hair, ears, skull and back of
   the head remain CLO's stock head; the photo's expression is baked in; body skin
   is not tinted to match the face (`skinToneHex` is stored for that).
3. **Licence:** `bmnet.pt` was trained on Amazon BodyM (CC BY-NC 4.0,
   non-commercial). Retrain on licensed/owned data before any commercial launch.
   Face reconstruction is Apache-2.0 only.
4. **Shopify** connects with a pasted Admin API token only; there is no Mirra
   Shopify app (OAuth install, inventory webhooks) yet.
5. **No rate limiting** on the public `/photo-capture/{token}` routes; the token is
   the only gate.
6. Dashboard pages for analytics, billing and audit still show demo data for a
   live workspace (no backend for them yet). Backend `admin` maps to dashboard
   `brand_merchandiser`, which lacks `settings.manage`.
7. Merchant garments are filtered per catalogue request (every merchant cloth is
   evaluated); add a stored "served" flag when the catalogue grows.
8. Nothing here has been clicked through in a browser; verification so far is
   automated tests, a production build, and in-process end-to-end runs with the
   real models on real photos.

## 5. Where to look

| Topic | File |
|---|---|
| Session log and audit | `.agent/website-launch-2/14-photo-measurement-and-merchant-linking.md` |
| Photo measurement | `photo_measurement/README.md` |
| Face reconstruction | `face_reconstruction/README.md` |
| Workers and queues | `worker/README.md` |
| CLO avatar contract | `clo_avatar_generation/schema/step1_field_contract.json` |
