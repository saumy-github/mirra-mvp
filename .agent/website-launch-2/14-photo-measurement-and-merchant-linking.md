# 14 — Photo measurement + merchant ↔ shopper linking (2026-10-04)

Integrates the photo-measurement system (R&D repo `for_measurements`) and closes
three gaps found in the pre-integration audit. Nothing committed; all changes are
working-tree changes on `Madhavan`, alongside the uncommitted frontend work that
was already there.

## Audit findings (before any change)

| # | Finding | Status |
|---|---|---|
| 1 | `mediapipe` would pull numpy 2.x and a second OpenCV (`opencv-contrib-python`) next to the pinned `opencv-python` | fixed: pin `opencv-contrib-python==4.10.0.84` (same version, superset) + `mediapipe>=0.10.14,<0.11`; resolves with `numpy==1.26.4` |
| 2 | Backend image has no torch/MediaPipe; CLO worker is single-job, 20-min runs | new `measure` RQ queue + `run_worker.py --queues measure` |
| 3 | `bmnet.pt` 92 MB; repo ignores model binaries | `photo_measurement/models/` gitignored; README says where to get it |
| 4 | BMnet trained on BodyM (CC BY-NC) | **decision: use it anyway for now**; documented as a pre-commercial blocker |
| 5 | R&D `.avt` builder / `clo_csv` / cloth module duplicate Step 1 / target a different CLO workflow | not migrated; only the measurement inference moved |
| 7 | CLO avatar `step_03` accepted `gender == "male"` only | fixed in pass 2 (below) — needs the female base avatar installed |
| 8 | No code created merchant tenants; business sign-up had no workspace; dashboard ran on the demo persona store | fixed (below) |
| 9 | Ingestion writes `cloths`/`sizes` at *submit*; shopper catalogue served every cloth → unapproved garments visible in the studio | fixed (below) |
| 10 | `mirra_measurements/db.py` hardcoded database `mirratest` | fixed: reads `DATABASE_NAME` |
| — | `docker-compose.yml` mounted upload roots `:ro` → every API upload (merchant captures too) failed in the container | fixed: read-write |
| — | `dev_upload`/`live_upload` `.gitignore` only covered `avatars/` | added `captures/`, `measurement_photos/` |

Dev database at audit time (read-only check): 0 merchant tenants, 0 merchant cloths,
11 `user_measurements` (male and female) — so #9 hides nothing that exists today.

## Photo measurement

```
/profile/measurements → "Measure from photos" (or "Enter manually", unchanged)
  POST /api/v1/photo-measurements            multipart front, side, height_cm, gender, weight_kg?, shoe_sole_cm?
  GET  /api/v1/photo-measurements/{id}       poll: queued → processing → ready | failed
  GET  /api/v1/photo-measurements/latest     resume after reload
  POST /api/v1/photo-measurements/{id}/apply {overrides: {field: value}} → user_measurements
```

- Backend `src/photo_measurements/` (models, storage, service, engine, routes);
  collection `photo_measurements`; photos at
  `<upload_root>/measurement_photos/<user_id>/<capture_id>/`, **deleted by the worker
  after measuring, success or failure**. Account deletion cascades docs + files.
- Worker `worker/measure_tasks.py` (entry `worker.tasks.run_photo_measurement`) runs
  `photo_measurement.pipeline.measure_photos`. Failure text shown to shoppers never
  contains server paths.
- `apply` merges: existing doc fields → photo profile → weight entered with the photos
  → shopper overrides; re-validated like a manual submit; written through
  `user_measurements.service.submit(..., source="photo", photo_capture_id=...)`,
  `accuracy="approx"`. Bust/under-bust dropped for men. `user_measurements` gained
  optional `source` and `photo_capture_id` (additive; old docs validate).
- Verified end to end in-process with the real model on real photos: upload → worker →
  apply → `user_measurements` → `POST /avatars/generate` snapshot → CLO `step_03`
  `_validate_required_fields` + `_validate_ranges` pass.

## Merchant ↔ shopper

- **Provisioning (#8).** `POST /merchant/workspaces` (signed-in non-guest, one per
  account, creator = owner, slug de-duplicated), `POST /merchant/{id}/members`
  (owner/admin seat an existing account by email). Workspace responses carry the
  caller's `role`.
- **Dashboard session.** `/business/login` now lands on `/dashboard/start`
  (`pages/Start.tsx`): signed out → business login; no workspace → create one;
  otherwise `data/live-session.ts` mirrors the real user/workspace/role into the demo
  store and signs in as it. Portal and onboarding guards send a missing session to
  Start instead of the persona picker (still at `/dashboard/login`). Sign-out of a live
  session also ends the backend session.
  - Settings: **Shopify store card** (store domain + Admin API token → connect +
    reconcile) for live workspaces.
  - Team: **Add a colleague** (backend seat) for live workspaces; the demo invite card
    is hidden there.
  - "+ Add garment" on a live workspace goes to the server-backed Digitise flow.
  - Other portal pages (analytics, billing, audit, admin console) still read demo
    data — for a live workspace they show its empty demo slice. No backend exists
    for them yet.
- **Shopper gate (#9).** `merchant.service.shopper_size_ids()` runs the same
  `publication.resolve_garment` the dashboard uses; `catalog.service` excludes merchant
  cloths (`brand_id` set) that aren't served, restricts sizes to served ones, and 404s
  them in `get_cloth` — so `tryon.request_render` (via `resolve_pair`) can't reach them
  either. Seeded cloths (`brand_id` None) unchanged.

## Running it

```bash
pip install -r requirements.txt            # opencv swap + mediapipe
python worker/run_worker.py                # CLO jobs
python worker/run_worker.py --queues measure   # photo jobs (Docker host, same APP_ENV)
# model: photo_measurement/models/bmnet.pt (see photo_measurement/README.md)
```

Tests: `cd website/backend && PYTHONPATH=../.. python -m pytest` (backend, 99),
`python -m pytest photo_measurement/tests` (22), `cd website/frontend && npm test` (45).

## Open items

1. Female CLO avatars: code done (pass 2); install the female base `.avt` and confirm the slot mapping on the first real run.
2. BodyM licence — retrain BMnet on owned/licensed data before commercial use.
3. Shopify: token-based connect only; the Mirra Shopify app (OAuth install, webhooks
   for inventory) does not exist yet.
4. `_hidden_merchant_cloth_ids` evaluates every merchant cloth per catalogue request —
   fine at pilot scale; denormalise a `served` flag onto `cloths` when it isn't.
5. The `measure` worker must share the upload folder with the API (same as merchant
   captures); a separate worker host needs object storage instead.
6. Dashboard admin mapping: backend `admin` → dashboard `brand_merchandiser`, which
   lacks `settings.manage`, so admins can't use the Shopify card in the UI although the
   API allows it.

## Pass 2 (same day): QR hand-off, female avatars, clean-ups

**QR → photos → avatar.** `/onboarding/qr` now creates a real pairing
(`POST /photo-measurements/pairings`, `photo_measurements/pairing.py`) and shows
`/capture/<token>` as the QR code. The phone opens `pages/onboarding/CaptureLink.tsx`
**without signing in**: the token (192-bit, stored hashed, 20-minute TTL, revoked when
a newer code is issued, max 5 uploads) scopes uploads to the desktop's account. The
phone sees progress only (`GET /photo-capture/{token}/capture` omits the numbers).
The desktop polls the pairing, and when the capture is ready opens
`/profile/measurements?photos=1` (the photo flow resumes at review); saving goes to
`/profile/avatar?generate=1`, which starts the CLO avatar job once. Signed-out desktops
get a sign-in button instead of a code. Collection `photo_pairings` (deleted with the
account).

**Female avatars.** `step1_field_contract.json` is now `v2-draft`, `male_and_female`:
height/weight/shoulder/waist/hip/inseam are shared; chest is male-only; bust is female
on `.avt` slot 2 (CLO's BustCircum — `fBaseFeatureBustCircum` sits beside the feature
block in `base-1.avt`); under-bust is female, optional, property/CSV routes only.
`base_avatars` picks the base per gender (step 04; the worker no longer forces the male
one). A female profile without bust (manual form asks for "chest") uses chest as bust,
with a warning. **To switch it on:** copy CLO's stock `Female_V2/FV2_Feifei.avt` to
`clo_avatar_generation/input/base-female.avt`; a missing file fails the job with that
instruction. Unverified until a real CLO run: that FV2 uses the same slots as MV2 —
check the run's `requested` vs `.avt` readback (step 09). Tests:
`python -m pytest clo_avatar_generation/tests` (5, offline, uses `base-1.avt`).

**Clean-ups.** Photo captures no worker picked up within an hour are failed and their
photos deleted (swept on every upload). The Shopify card uses the backend role, so
workspace admins can connect a store.

Verified in-process end to end with the real model: desktop pairing → signed-out phone
upload → worker → desktop review/apply → avatar job → CLO steps 03–06 on a female base
(Bust patched into slot 2 of a real `.avt`). Not verified in a browser (extension not
connected) — `vite build` succeeds and the running dev servers serve the new routes.

Open: no rate limiting on the public `/photo-capture/{token}` routes (token is the only
gate); pairing links work only while the measure worker shares the API's upload folder.

## Pass 3: face layer

`face_reconstruction/` (top-level pipeline, Apache-2.0 only — MediaPipe Face
Landmarker + canonical face model; FLAME was the plan but its files sit behind a
registration and are research-only): 1–3 face photos → metric, textured face
mesh `face.glb`. See its README for the method and limits (a personalised face on
CLO's stock head; expression baked in; no body skin tint yet).

- Backend `src/faces/`: `POST /faces` (front, left?, right?), `GET /faces/latest`,
  `GET /faces/{id}`, `GET /faces/current/glb`, `DELETE /faces`; collection
  `face_captures`; photos under `face_photos/` deleted by the worker, mesh under
  `faces/<user>/<id>/face.glb`; one face per user (older ones removed);
  account deletion cascades. Phone: `POST|GET /photo-capture/{token}/face` on the
  QR link. Worker: `worker/face_tasks.py` (`worker.tasks.run_face_reconstruction`,
  `measure` queue).
- Frontend: `GlbViewer withFace` attaches the face on `/profile/avatar` and in the
  studio (avatar and try-on renders) via `face-attachment.ts`; "Your face" panel
  on `/profile/avatar` (add/replace/remove); the phone page offers face photos
  after the body photos.
- Tested: `face_reconstruction/tests` (6, synthetic faces), backend `test_faces.py`
  (6), frontend `face-attachment.test.ts` (4); the real pipeline was run on a
  portrait photo end to end through the worker.
- **Not yet checked on a real CLO avatar GLB** (none on this machine): the head
  finder is verified on synthetic bodies. First thing to look at on a real avatar:
  that the face sits on the face (orientation from the toes, nose at ~6.5% of
  height below the top).
