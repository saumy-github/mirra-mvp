"""Photo measurement: upload -> worker -> review -> apply into user_measurements.

The worker test stubs the model (photo_measurement.pipeline.measure_photos) —
the pipeline has its own tests in photo_measurement/tests; what matters here is
the hand-off: files deleted, states written, and the applied result landing in
user_measurements exactly where the avatar pipeline reads it.
"""

import asyncio
import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent.parent
for _p in (BACKEND_ROOT, REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from tests.fake_mongo import FakeCollection  # noqa: E402

USER = "u_shopper"
OTHER = "u_someone_else"


def _png(w: int = 600, h: int = 900) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 200, 200)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def env(monkeypatch, tmp_path):
    import src.db as db_module
    import src.photo_measurements.engine as engine
    import src.photo_measurements.service as service
    import src.photo_measurements.storage as storage
    import src.user_measurements.service as um_service
    from src.config import Settings
    from src.core.auth_dependency import Identity, get_identity
    from src.main import create_app

    import src.photo_measurements.pairing as pairing

    photos, measurements, pairings = FakeCollection(), FakeCollection(), FakeCollection()
    for module in (db_module, service):
        monkeypatch.setattr(module, "photo_measurements_col", lambda: photos, raising=False)
    for module in (db_module, pairing):
        monkeypatch.setattr(module, "photo_pairings_col", lambda: pairings, raising=False)
    for module in (db_module, um_service):
        monkeypatch.setattr(module, "user_measurements_col", lambda: measurements, raising=False)

    settings = Settings(app_env="development")
    monkeypatch.setattr(type(settings), "avatars_upload_root", property(lambda _s: tmp_path / "upload"))
    monkeypatch.setattr(storage, "get_settings", lambda: settings)

    queued: list[str] = []
    monkeypatch.setattr(engine, "start_capture", queued.append)

    app = create_app()
    identity = {"user": USER}
    app.dependency_overrides[get_identity] = lambda: Identity(user_id=identity["user"], kind="user")
    client = TestClient(app)
    client.photos, client.measurements, client.queued = photos, measurements, queued
    client.pairings = pairings
    client.upload_root = tmp_path / "upload"
    client.identity = identity
    return client


def _upload(env, **form):
    data = {"height_cm": "170", "gender": "female", **form}
    files = {
        "front": ("front.png", _png(), "image/png"),
        "side": ("side.png", _png(), "image/png"),
    }
    return env.post("/api/v1/photo-measurements", data=data, files=files)


def _run_worker(env, monkeypatch, result=None, error=None):
    """Run the real worker task body against the fake collections."""
    import photo_measurement.pipeline as pipeline
    import worker.measure_tasks as tasks

    monkeypatch.setattr(tasks, "photo_measurements_col", lambda: env.photos)

    def fake_measure(front, side, height, weight, gender, shoe):
        assert Path(front).is_file() and Path(side).is_file()
        if error:
            raise error
        return result

    monkeypatch.setattr(pipeline, "measure_photos", fake_measure)
    asyncio.run(tasks._run_photo_measurement(env.queued[-1]))


RESULT = {
    "profile": {
        "height_cm": 170.0, "shoulder_width_cm": 38.2, "waist_circumference_cm": 71.5,
        "hip_circumference_cm": 97.0, "leg_length_cm": 77.1, "chest_circumference_cm": 90.4,
        "bust_circumference_cm": 91.0, "under_bust_circumference_cm": 76.3, "weight_kg": None,
        "body_shape_type": "hourglass", "skin_tone_hex": "#C8A08A",
    },
    "measurements": {"chest": 90.4, "waist": 71.5, "hip": 97.0, "neck": 33.0},
    "warnings": ["side: arm appears to touch the torso"],
    "model": ["bmnet.pt"],
}


# ------------------------------------------------------------------ upload


def test_upload_stores_photos_and_queues_a_measure_job(env):
    r = _upload(env, weight_kg="62")
    assert r.status_code == 201, r.text
    cap = r.json()["capture"]
    assert cap["state"] == "queued" and cap["gender"] == "female" and cap["weightKg"] == 62
    assert env.queued == [cap["captureId"]]
    stored = sorted(p.name for p in (env.upload_root / "measurement_photos" / USER / cap["captureId"]).iterdir())
    assert stored == ["front.png", "side.png"]


@pytest.mark.parametrize(
    "form, files, message",
    [
        ({"height_cm": "90"}, None, "Height"),
        ({"weight_kg": "500"}, None, "Weight"),
        ({}, {"front": ("f.heic", b"x", "image/heic")}, "HEIC"),
        ({}, {"side": ("s.png", None, "image/png")}, "480px"),
    ],
)
def test_bad_input_is_refused_and_nothing_is_kept(env, form, files, message):
    all_files = {
        "front": ("front.png", _png(), "image/png"),
        "side": ("side.png", _png(), "image/png"),
    }
    for view, (name, data, ctype) in (files or {}).items():
        all_files[view] = (name, data if data is not None else _png(300, 400), ctype)
    r = env.post("/api/v1/photo-measurements", data={"height_cm": "170", "gender": "male", **form}, files=all_files)
    assert r.status_code == 422 and message in r.text
    assert env.photos.docs == [] and env.queued == []
    assert not any((env.upload_root / "measurement_photos").glob("*/*/*"))


def test_queue_down_leaves_no_document_or_photos(env, monkeypatch):
    import src.photo_measurements.engine as engine
    from src.core.errors import ServiceUnavailable

    def down(_):
        raise ServiceUnavailable("Live engine queue is unreachable", code="engine_unavailable")

    monkeypatch.setattr(engine, "start_capture", down)
    r = _upload(env)
    assert r.status_code == 503
    assert env.photos.docs == []
    assert not any((env.upload_root / "measurement_photos").glob("*/*/*"))


def test_another_users_capture_is_not_found(env):
    capture_id = _upload(env).json()["capture"]["captureId"]
    env.identity["user"] = OTHER
    assert env.get(f"/api/v1/photo-measurements/{capture_id}").status_code == 404
    assert env.post(f"/api/v1/photo-measurements/{capture_id}/apply", json={}).status_code == 404


# ------------------------------------------------------------------ worker


def test_worker_writes_the_result_and_deletes_the_photos(env, monkeypatch):
    capture_id = _upload(env).json()["capture"]["captureId"]
    _run_worker(env, monkeypatch, result=RESULT)

    cap = env.get(f"/api/v1/photo-measurements/{capture_id}").json()["capture"]
    assert cap["state"] == "ready"
    assert cap["profile"]["waist_circumference_cm"] == 71.5
    assert cap["warnings"] == RESULT["warnings"]
    assert not (env.upload_root / "measurement_photos" / USER / capture_id).exists()
    assert env.photos.docs[0]["front_path"] is None


def test_worker_failure_is_shopper_readable_and_still_deletes(env, monkeypatch):
    capture_id = _upload(env).json()["capture"]["captureId"]
    _run_worker(env, monkeypatch, error=RuntimeError("no person detected in /srv/upload/x/front.png"))

    cap = env.get(f"/api/v1/photo-measurements/{capture_id}").json()["capture"]
    assert cap["state"] == "failed"
    assert "full body" in cap["failureReason"] and "/srv" not in cap["failureReason"]
    assert not (env.upload_root / "measurement_photos" / USER / capture_id).exists()


# ------------------------------------------------------------------- apply


def test_apply_before_ready_is_refused(env):
    capture_id = _upload(env).json()["capture"]["captureId"]
    r = env.post(f"/api/v1/photo-measurements/{capture_id}/apply", json={})
    assert r.status_code == 409


def test_apply_writes_user_measurements_with_corrections(env, monkeypatch):
    capture_id = _upload(env, weight_kg="62").json()["capture"]["captureId"]
    _run_worker(env, monkeypatch, result=RESULT)

    r = env.post(
        f"/api/v1/photo-measurements/{capture_id}/apply",
        json={"overrides": {"waist_circumference_cm": 73.0}},
    )
    assert r.status_code == 200, r.text
    saved = env.measurements.docs[0]
    assert saved["user_id"] == USER and saved["gender"] == "female"
    assert saved["source"] == "photo" and saved["photo_capture_id"] == capture_id
    assert saved["accuracy"] == "approx"
    assert saved["waist_circumference_cm"] == 73.0          # the shopper's correction wins
    assert saved["bust_circumference_cm"] == 91.0
    assert saved["weight_kg"] == 62                          # entered with the photos
    assert saved["skin_tone_hex"] == "#C8A08A"
    assert r.json()["capture"]["state"] == "applied"
    # The avatar pipeline's required v1 fields are all present (step_03).
    for field in ("height_cm", "weight_kg", "shoulder_width_cm", "chest_circumference_cm",
                  "waist_circumference_cm", "hip_circumference_cm", "leg_length_cm"):
        assert saved.get(field) is not None, field


def test_apply_keeps_existing_fields_and_drops_bust_for_men(env, monkeypatch):
    env.put("/api/v1/user-measurements/me", json={"gender": "male", "weight_kg": 80, "height_cm": 181,
                                                  "units_preference": "imperial"})
    capture_id = _upload(env, gender="male").json()["capture"]["captureId"]
    _run_worker(env, monkeypatch, result=RESULT)

    env.post(f"/api/v1/photo-measurements/{capture_id}/apply", json={})
    saved = env.measurements.docs[0]
    assert saved["weight_kg"] == 80                  # not measurable from photos: kept
    assert saved["height_cm"] == 170.0               # the capture's height is the new truth
    assert saved["units_preference"] == "imperial"
    assert saved["measurements_version"] == 2
    assert "bust_circumference_cm" not in saved and "under_bust_circumference_cm" not in saved


@pytest.mark.parametrize("overrides", [{"neck_cm": 30.0}, {"waist_circumference_cm": -1.0}])
def test_apply_refuses_bad_overrides(env, monkeypatch, overrides):
    capture_id = _upload(env).json()["capture"]["captureId"]
    _run_worker(env, monkeypatch, result=RESULT)
    r = env.post(f"/api/v1/photo-measurements/{capture_id}/apply", json={"overrides": overrides})
    assert r.status_code == 422
    assert env.measurements.docs == []


def test_latest_restores_the_most_recent_capture(env):
    assert env.get("/api/v1/photo-measurements/latest").json() == {"capture": None}
    _upload(env)
    second = _upload(env).json()["capture"]["captureId"]
    assert env.get("/api/v1/photo-measurements/latest").json()["capture"]["captureId"] == second


def test_account_deletion_cascade_removes_documents_and_files(env):
    from src.photo_measurements.service import delete_for_user

    _upload(env)
    asyncio.run(delete_for_user(USER))
    assert env.photos.docs == []
    assert not (env.upload_root / "measurement_photos" / USER).exists()


# ------------------------------------------------------------ QR hand-off


def _phone_upload(env, token, **form):
    data = {"height_cm": "165", "gender": "female", **form}
    files = {"front": ("f.png", _png(), "image/png"), "side": ("s.png", _png(), "image/png")}
    return env.post(f"/api/v1/photo-capture/{token}", data=data, files=files)


def test_qr_hand_off_desktop_to_phone_and_back(env, monkeypatch):
    env.put("/api/v1/user-measurements/me", json={"gender": "female", "height_cm": 165, "weight_kg": 58})
    created = env.post("/api/v1/photo-measurements/pairings").json()["pairing"]
    token, pairing_id = created["token"], created["pairingId"]
    assert created["active"] and created["captureId"] is None
    assert token not in str(env.pairings.docs)  # only the hash is stored

    # The phone is not signed in: no identity is involved in these calls.
    link = env.get(f"/api/v1/photo-capture/{token}").json()["link"]
    assert link["gender"] == "female" and link["heightCm"] == 165 and link["weightKg"] == 58
    assert env.get(f"/api/v1/photo-capture/{token}/capture").json() == {"capture": None}

    r = _phone_upload(env, token)
    assert r.status_code == 201, r.text
    capture_id = r.json()["capture"]["captureId"]
    assert env.photos.docs[0]["user_id"] == USER  # landed in the desktop user's account

    _run_worker(env, monkeypatch, result=RESULT)
    phone_view = env.get(f"/api/v1/photo-capture/{token}/capture").json()["capture"]
    assert phone_view["state"] == "ready" and "profile" not in phone_view  # numbers stay on the desktop

    desk = env.get(f"/api/v1/photo-measurements/pairings/{pairing_id}").json()
    assert desk["pairing"]["captureId"] == capture_id
    assert desk["capture"]["profile"]["waist_circumference_cm"] == 71.5
    assert env.post(f"/api/v1/photo-measurements/{capture_id}/apply", json={}).status_code == 200


def test_a_new_qr_code_revokes_the_old_link(env):
    old = env.post("/api/v1/photo-measurements/pairings").json()["pairing"]["token"]
    env.post("/api/v1/photo-measurements/pairings")
    r = env.get(f"/api/v1/photo-capture/{old}")
    assert r.status_code == 410 and "expired" in r.text
    assert _phone_upload(env, old).status_code == 410


def test_expired_and_unknown_links_are_refused(env):
    from datetime import datetime, timedelta, timezone

    token = env.post("/api/v1/photo-measurements/pairings").json()["pairing"]["token"]
    env.pairings.docs[0]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert env.get(f"/api/v1/photo-capture/{token}").status_code == 410
    assert env.get("/api/v1/photo-capture/not-a-real-token").status_code == 404
    assert env.photos.docs == []


def test_a_link_accepts_only_a_few_uploads(env):
    token = env.post("/api/v1/photo-measurements/pairings").json()["pairing"]["token"]
    for _ in range(5):
        assert _phone_upload(env, token).status_code == 201
    r = _phone_upload(env, token)
    assert r.status_code == 422 and "Too many uploads" in r.text


def test_another_users_pairing_is_not_found(env):
    pairing_id = env.post("/api/v1/photo-measurements/pairings").json()["pairing"]["pairingId"]
    env.identity["user"] = OTHER
    assert env.get(f"/api/v1/photo-measurements/pairings/{pairing_id}").status_code == 404


def test_captures_no_worker_picked_up_are_failed_and_their_photos_deleted(env):
    from datetime import datetime, timedelta, timezone

    stale_id = _upload(env).json()["capture"]["captureId"]
    env.photos.docs[0]["created_at"] = datetime.now(timezone.utc) - timedelta(hours=2)
    _upload(env)  # any new upload sweeps

    stale = next(d for d in env.photos.docs if d["_id"] == stale_id)
    assert stale["state"] == "failed" and stale["front_path"] is None
    assert not (env.upload_root / "measurement_photos" / USER / stale_id).exists()


# ------------------------------------------------------ durable onboarding

@pytest.fixture
def setup_env(env, monkeypatch):
    import src.avatars.service as avatars
    import src.avatars.engine as engine
    import src.faces.service as faces
    import src.user_measurements.service as um

    jobs, face_docs = FakeCollection(), FakeCollection()
    monkeypatch.setattr(avatars, "avatar_jobs_col", lambda: jobs)
    monkeypatch.setattr(avatars, "get_measurements", um.get_for_user)
    monkeypatch.setattr(faces, "face_captures_col", lambda: face_docs)
    env.avatar_jobs, env.face_docs, env.avatar_queued = jobs, face_docs, []
    monkeypatch.setattr(engine, "start_job", lambda j: env.avatar_queued.append(j.id))
    return env


def _setup(env):
    return env.post("/api/v1/photo-measurements/pairings", json={"buildAvatar": True}).json()["pairing"]


def _state(env, pairing_id):
    response = env.get(f"/api/v1/photo-measurements/setup/{pairing_id}")
    assert response.status_code == 200, response.text
    return response.json()["setup"]


def test_setup_waits_for_phone_finish_then_worker_starts_one_avatar(setup_env, monkeypatch):
    env = setup_env
    p = _setup(env)
    token, pid = p["token"], p["pairingId"]
    assert _state(env, pid)["state"] == "waiting"
    env.post(f"/api/v1/photo-capture/{token}/stage", json={"stage": "capturing"})
    assert _state(env, pid)["state"] == "capturing"
    _phone_upload(env, token)
    assert env.post(f"/api/v1/photo-capture/{token}/finish", json={}).status_code == 409
    env.post(f"/api/v1/photo-capture/{token}/finish", json={"skipFace": True})
    assert _state(env, pid)["state"] == "measuring"
    _run_worker(env, monkeypatch, result=RESULT)
    assert len(env.avatar_queued) == 1  # no desktop poll required to start CLO
    assert env.avatar_jobs.docs[0]["measurement_snapshot"]["waist_circumference_cm"] == 71.5
    for _ in range(3):
        assert _state(env, pid)["state"] == "building"
    assert len(env.avatar_queued) == 1
    assert env.get("/api/v1/photo-measurements/setup/latest").json()["setup"]["job"]["jobId"] == env.avatar_queued[0]
    assert env.get(f"/api/v1/photo-capture/{token}").json()["link"]["complete"] is True
    assert _phone_upload(env, token).status_code == 409


def test_model_finishing_before_phone_still_starts_on_finish(setup_env, monkeypatch):
    env = setup_env
    p = _setup(env)
    _phone_upload(env, p["token"])
    _run_worker(env, monkeypatch, result=RESULT)
    assert not env.avatar_queued and not env.measurements.docs
    env.post(f'/api/v1/photo-capture/{p["token"]}/finish', json={"skipFace": True})
    assert len(env.avatar_queued) == 1


def _ready_setup(env, monkeypatch):
    p = _setup(env)
    _phone_upload(env, p["token"])
    env.post(f'/api/v1/photo-capture/{p["token"]}/finish', json={"skipFace": True})
    _run_worker(env, monkeypatch, result=RESULT)
    env.avatar_jobs.docs[0]["state"] = "ready"
    return p


def test_review_with_corrections_rebuilds_before_completing(setup_env, monkeypatch):
    env = setup_env
    p = _ready_setup(env, monkeypatch)
    pid = p["pairingId"]
    assert _state(env, pid)["state"] == "review"
    url = f"/api/v1/photo-measurements/setup/{pid}/review"
    body = {"overrides": {"waist_circumference_cm": 73.2, "weight_kg": 62}}
    r = env.post(url, json=body)
    assert r.status_code == 200, r.text
    assert r.json()["setup"]["state"] == "updating"
    assert env.avatar_jobs.docs[-1]["measurement_snapshot"]["waist_circumference_cm"] == 73.2
    assert env.measurements.docs[0]["measurements_version"] == 2
    env.post(url, json=body)  # double submit is idempotent
    assert len(env.avatar_queued) == 2
    assert _state(env, pid)["state"] == "updating"
    env.avatar_jobs.docs[-1]["state"] = "ready"
    assert _state(env, pid)["state"] == "complete"
    assert env.pairings.docs[0]["reviewed_at"] is not None


def test_review_without_edits_does_not_rebuild(setup_env, monkeypatch):
    env = setup_env
    p = _ready_setup(env, monkeypatch)
    r = env.post(f'/api/v1/photo-measurements/setup/{p["pairingId"]}/review', json={})
    assert r.json()["setup"]["state"] == "complete"
    assert len(env.avatar_queued) == 1
    assert env.measurements.docs[0]["measurements_version"] == 1


def test_precise_review_corrections_reach_avatar_snapshot_without_replacing_baseline(setup_env, monkeypatch):
    import src.photo_measurements.setup as setup

    env = setup_env
    p = _ready_setup(env, monkeypatch)
    before = env.avatar_jobs.docs[0]["measurement_snapshot"].copy()
    overrides = {"waist_circumference_cm": 71.26, "chest_circumference_cm": 90.48}
    response = env.post(
        f'/api/v1/photo-measurements/setup/{p["pairingId"]}/review',
        json={"overrides": overrides},
    )
    assert response.status_code == 200, response.text
    assert response.json()["setup"]["state"] == "updating"
    snapshot = env.avatar_jobs.docs[-1]["measurement_snapshot"]
    for field, value in overrides.items():
        assert snapshot[field] == value
        assert env.measurements.docs[0][field] == value
    for field in ("height_cm", "hip_circumference_cm", "leg_length_cm", "bust_circumference_cm"):
        assert snapshot[field] == before[field]

    # Repeated polling/worker advancement must not re-apply the old model estimate.
    for _ in range(3):
        asyncio.run(setup.advance(p["pairingId"], USER))
        assert _state(env, p["pairingId"])["measurements"]["waist_circumference_cm"] == 71.26
    assert len(env.avatar_queued) == 2
    assert env.measurements.docs[0]["measurements_version"] == 2
    env.avatar_jobs.docs[-1]["state"] = "ready"
    assert _state(env, p["pairingId"])["state"] == "complete"


def test_replaced_setup_cannot_confirm_or_restart_a_build(setup_env, monkeypatch):
    env = setup_env
    old = _ready_setup(env, monkeypatch)
    _setup(env)  # replacing a capture link revokes the previous setup
    base = f'/api/v1/photo-measurements/setup/{old["pairingId"]}'
    assert env.post(f"{base}/review", json={}).status_code == 409
    assert env.post(f"{base}/retry", json={}).status_code == 409
    assert len(env.avatar_queued) == 1


def test_review_refuses_early_invalid_and_other_users_requests(setup_env, monkeypatch):
    env = setup_env
    p = _setup(env)
    url = f'/api/v1/photo-measurements/setup/{p["pairingId"]}/review'
    assert env.post(url, json={}).status_code == 409
    p = _ready_setup(env, monkeypatch)
    url = f'/api/v1/photo-measurements/setup/{p["pairingId"]}/review'
    assert env.post(url, json={"overrides": {"height_cm": 400}}).status_code == 422
    assert env.post(url, json={"overrides": {"user_id": 1}}).status_code == 422
    env.identity["user"] = OTHER
    assert env.post(url, json={}).status_code == 404
    assert env.get(f'/api/v1/photo-measurements/setup/{p["pairingId"]}').status_code == 404
    assert env.get("/api/v1/photo-measurements/setup/latest").json() == {"setup": None}


def test_setup_survives_link_expiry_and_refresh_keeps_capture(setup_env, monkeypatch):
    from datetime import datetime, timedelta, timezone
    env = setup_env
    p = _ready_setup(env, monkeypatch)
    env.pairings.docs[0]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert _state(env, p["pairingId"])["state"] == "review"
    renewed = env.post(f'/api/v1/photo-measurements/pairings/{p["pairingId"]}/link').json()["pairing"]
    assert renewed["captureId"] == env.photos.docs[0]["_id"]
    assert renewed["token"] != p["token"] and renewed["active"]
    assert env.get(f'/api/v1/photo-capture/{p["token"]}').status_code == 404


def test_queue_failure_is_retriable_without_reupload(setup_env, monkeypatch):
    import src.avatars.engine as engine
    from src.core.errors import ServiceUnavailable
    env = setup_env
    p = _setup(env)
    _phone_upload(env, p["token"])
    env.post(f'/api/v1/photo-capture/{p["token"]}/finish', json={"skipFace": True})
    monkeypatch.setattr(engine, "start_job", lambda _: (_ for _ in ()).throw(ServiceUnavailable("offline")))
    _run_worker(env, monkeypatch, result=RESULT)
    assert _state(env, p["pairingId"])["state"] == "failed"
    monkeypatch.setattr(engine, "start_job", lambda j: env.avatar_queued.append(j.id))
    r = env.post(f'/api/v1/photo-measurements/setup/{p["pairingId"]}/retry', json={})
    assert r.json()["setup"]["state"] == "building"
    assert len(env.avatar_queued) == 1 and len(env.photos.docs) == 1


def test_manual_measurements_share_the_same_face_build_and_review_flow(setup_env):
    env = setup_env
    env.put("/api/v1/user-measurements/me", json={"gender": "male", "height_cm": 176, "weight_kg": 72})
    p = env.post("/api/v1/photo-measurements/pairings", json={"buildAvatar": True, "measurementMethod": "manual"}).json()["pairing"]
    assert env.get(f'/api/v1/photo-capture/{p["token"]}').json()["link"]["measurementMethod"] == "manual"
    r = env.post(f'/api/v1/photo-capture/{p["token"]}/finish', json={"skipFace": True})
    assert r.status_code == 200, r.text
    assert len(env.avatar_queued) == 1 and not env.photos.docs
    env.avatar_jobs.docs[0]["state"] = "ready"
    s = _state(env, p["pairingId"])
    assert s["state"] == "review" and s["measurements"]["height_cm"] == 176


def test_face_must_finish_before_review_but_does_not_block_body_build(setup_env, monkeypatch):
    from datetime import datetime, timezone
    env = setup_env
    p = _setup(env)
    _phone_upload(env, p["token"])
    env.face_docs.docs.append({"_id": "fc_test", "user_id": USER, "state": "processing", "views": ["front"], "created_at": datetime.now(timezone.utc)})
    env.pairings.docs[0]["face_capture_id"] = "fc_test"
    r = env.post(f'/api/v1/photo-capture/{p["token"]}/finish', json={})
    assert r.status_code == 200, r.text
    _run_worker(env, monkeypatch, result=RESULT)
    env.avatar_jobs.docs[0]["state"] = "ready"
    assert _state(env, p["pairingId"])["state"] == "building"
    env.face_docs.docs[0]["state"] = "ready"
    assert _state(env, p["pairingId"])["state"] == "review"


def test_failed_face_can_be_explicitly_skipped_without_rebuilding_body(setup_env, monkeypatch):
    from datetime import datetime, timezone
    env = setup_env
    p = _ready_setup(env, monkeypatch)
    env.face_docs.docs.append({"_id": "fc_bad", "user_id": USER, "state": "failed", "views": ["front"], "created_at": datetime.now(timezone.utc), "failure_reason": "Retake your face photo."})
    env.pairings.docs[0].update(face_capture_id="fc_bad", face_skipped=False)
    assert _state(env, p["pairingId"])["state"] == "failed"
    r = env.post(f'/api/v1/photo-measurements/setup/{p["pairingId"]}/retry', json={"skipFace": True})
    assert r.json()["setup"]["state"] == "review"
    assert len(env.avatar_queued) == 1
