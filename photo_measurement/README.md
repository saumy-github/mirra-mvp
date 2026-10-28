# Photo measurement

Front + side photo + height → body measurements, for shoppers who don't have
a tape measure. The result is reviewed by the shopper and then saved into
`user_measurements` exactly like the manual form, so avatar generation (Step 1)
and try-on (Step 3) are unchanged.

```
website  /profile/measurements  "Measure from photos"
   │  POST /api/v1/photo-measurements (front, side, height_cm, gender, weight_kg?)
   ▼
backend  photo_measurements/   stores photos → photo_measurements doc → Redis queue `measure`
   ▼
worker   worker/run_worker.py --queues measure → worker/measure_tasks.py
         → photo_measurement.pipeline.measure_photos()  → result on the doc, photos deleted
   ▼
website  review + correct → POST /photo-measurements/{id}/apply → user_measurements (source="photo")
```

## Pipeline

1. **MediaPipe Pose Landmarker** — person mask + 33 landmarks per photo (`capture.py`).
2. **Geometry** — widths/depths at anatomical levels, ellipse girths, scaled by the
   given height (`measure.py`, `geometry.py`).
3. **BMnet** — a two-view silhouette network (ResNet-18 per view + height/weight/sex
   MLP) replaces the girths/lengths it was trained on; bust, under-bust, abdomen and
   overarm are rescaled by its correction of the neighbouring girth (`bmnet/`).
4. **Profile** — the `user_measurements` field names, plus `body_shape_type` and
   `skin_tone_hex` (cheek colour) (`report.py`).

Accuracy (mean absolute error, BodyM test sets): chest 1.8–2.3 cm, waist 1.7–2.6 cm,
hip 1.4–1.9 cm. Bad poses produce `warnings` (shown to the shopper), not failures.

## Model files (not in git)

```
photo_measurement/models/bmnet.pt                  ~92 MB, required
photo_measurement/models/pose_landmarker_full.task ~9 MB, downloaded on first use if missing
```
Copy them from the R&D repo (`for_measurements/models/`) or the team drive. A
missing `bmnet.pt` fails the job loudly (`ModelMissing`) rather than silently
falling back to the less accurate geometric numbers.

**Licence:** `bmnet.pt` is trained on Amazon BodyM (CC BY-NC 4.0 — non-commercial).
Retrain on licensed data before commercial launch. Training code lives in the R&D
repo (`for_measurements`, `mirra_avatar/bmnet/train.py`); this folder is inference only.

## Run by hand

```bash
python photo_measurement/run_photo_measurement.py --front f.jpg --side s.jpg --height 170 --gender female
python -m pytest photo_measurement/tests
```

## Capture protocol (shown to shoppers)

Fitted clothing, phone upright at chest height 2–3 m away, whole body in frame;
front: arms 20–40° out; side: a true 90° profile; JPEG/PNG/WebP (HEIC refused).
