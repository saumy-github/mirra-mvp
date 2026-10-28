"""Faces: upload -> worker -> face.glb served for the avatar viewer; one face
per user; deletion; the phone adding face photos through the QR link.

The worker test stubs face_reconstruction.pipeline.reconstruct_face (that
package has its own tests); what is checked here is the hand-off."""

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
GLB = b"glTF-fake-face"


def _png(w=640, h=800) -> bytes:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (w, h), (180, 140, 120)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def env(monkeypatch, tmp_path):
    import src.db as db_module
    import src.faces.engine as engine
    import src.faces.service as service
    import src.photo_measurements.pairing as pairing
    import src.photo_measurements.storage as storage
    import worker.face_tasks as tasks
    from src.config import Settings
    from src.core.auth_dependency import Identity, get_identity
    from src.main import create_app

    faces, pairings = FakeCollection(), FakeCollection()
    for module in (db_module, service, tasks):
        monkeypatch.setattr(module, "face_captures_col", lambda: faces, raising=False)
    for module in (db_module, pairing):
        monkeypatch.setattr(module, "photo_pairings_col", lambda: pairings, raising=False)

    settings = Settings(app_env="development")
    monkeypatch.setattr(type(settings), "avatars_upload_root", property(lambda _s: tmp_path / "upload"))
    for module in (storage, service, tasks):
        monkeypatch.setattr(module, "get_settings", lambda: settings, raising=False)

    queued: list[str] = []
    monkeypatch.setattr(engine, "start_capture", queued.append)

    app = create_app()
    app.dependency_overrides[get_identity] = lambda: Identity(user_id=USER, kind="user")
    client = TestClient(app)
    client.faces, client.queued, client.root = faces, queued, tmp_path / "upload"
    return client


def _upload(env, views=("front",)):
    files = {v: (f"{v}.png", _png(), "image/png") for v in views}
    return env.post("/api/v1/faces", files=files)


def _run_worker(env, monkeypatch, error=None):
    import face_reconstruction.pipeline as pipeline
    import worker.face_tasks as tasks

    def fake(photos):
        assert all(Path(p).is_file() for p in photos.values())
        if error:
            raise error
        return GLB, {"views": sorted(photos), "skin_tone_hex": "#C8A08A", "warnings": [], "scale_source": "iris"}

    monkeypatch.setattr(pipeline, "reconstruct_face", fake)
    asyncio.run(tasks._run_face_reconstruction(env.queued[-1]))


def test_upload_queues_and_the_worker_produces_the_face_glb(env, monkeypatch):
    r = _upload(env, ("front", "left", "right"))
    assert r.status_code == 201, r.text
    face_id = r.json()["face"]["faceId"]
    assert env.queued == [face_id]
    assert env.get("/api/v1/faces/current/glb").status_code == 404     # nothing ready yet

    _run_worker(env, monkeypatch)
    face = env.get("/api/v1/faces/latest").json()["face"]
    assert face["state"] == "ready" and face["hasModel"] and face["views"] == ["front", "left", "right"]
    glb = env.get("/api/v1/faces/current/glb")
    assert glb.status_code == 200 and glb.content == GLB
    assert not (env.root / "face_photos" / USER / face_id).exists()     # photos gone


def test_a_front_photo_is_required(env):
    r = _upload(env, ("left",))
    assert r.status_code == 422 and "front" in r.text
    assert env.faces.docs == []


def test_a_new_face_replaces_the_old_one(env, monkeypatch):
    first = _upload(env).json()["face"]["faceId"]
    _run_worker(env, monkeypatch)
    second = _upload(env).json()["face"]["faceId"]
    _run_worker(env, monkeypatch)
    assert [d["_id"] for d in env.faces.docs] == [second]
    assert not (env.root / "faces" / USER / first).exists()
    assert (env.root / "faces" / USER / second / "face.glb").is_file()


def test_failure_is_readable_and_deletes_the_photos(env, monkeypatch):
    face_id = _upload(env).json()["face"]["faceId"]
    _run_worker(env, monkeypatch, error=RuntimeError("no face detected in the front photo"))
    face = env.get(f"/api/v1/faces/{face_id}").json()["face"]
    assert face["state"] == "failed" and "front photo" in face["failureReason"]
    assert not (env.root / "face_photos" / USER / face_id).exists()


def test_delete_removes_every_face_file(env, monkeypatch):
    _upload(env)
    _run_worker(env, monkeypatch)
    assert env.delete("/api/v1/faces").json() == {"ok": True}
    assert env.faces.docs == [] and not (env.root / "faces" / USER).exists()
    assert env.get("/api/v1/faces/latest").json() == {"face": None}


def test_the_phone_adds_face_photos_through_the_qr_link(env, monkeypatch):
    token = env.post("/api/v1/photo-measurements/pairings").json()["pairing"]["token"]
    files = {"front": ("f.png", _png(), "image/png"), "right": ("r.png", _png(), "image/png")}
    r = env.post(f"/api/v1/photo-capture/{token}/face", files=files)
    assert r.status_code == 201, r.text
    assert env.faces.docs[0]["user_id"] == USER
    _run_worker(env, monkeypatch)
    progress = env.get(f"/api/v1/photo-capture/{token}/face").json()["face"]
    assert progress["state"] == "ready" and "skinToneHex" not in progress
