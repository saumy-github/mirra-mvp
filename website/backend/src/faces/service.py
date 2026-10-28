"""Face capture lifecycle. One face per user is kept: the worker removes older
faces when a new one is ready (worker/face_tasks.py)."""

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..config import get_settings
from ..core.errors import NotFound, ServiceUnavailable, ValidationFailed
from ..core.security import new_id
from ..db import face_captures_col
from ..photo_measurements import storage as photo_storage
from . import engine
from .models import FACE_VIEWS, FaceCaptureDocument

PHOTO_ROOT = "face_photos"
FACE_ROOT = "faces"
STALE_AFTER = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def face_dir(user_id: str, capture_id: str) -> Path:
    return get_settings().avatars_upload_root / FACE_ROOT / user_id / capture_id


async def create_capture(user_id: str, photos: dict[str, tuple[str, bytes]]) -> FaceCaptureDocument:
    """photos: view -> (content_type, bytes); "front" required."""
    if "front" not in photos:
        raise ValidationFailed("A front photo of your face is required")
    unknown = set(photos) - set(FACE_VIEWS)
    if unknown:
        raise ValidationFailed(f"Unknown face photo views: {', '.join(sorted(unknown))}")
    await expire_stale_captures()

    capture_id = new_id("fc")
    paths: dict[str, str] = {}
    try:
        for view, (content_type, data) in photos.items():
            paths[view] = photo_storage.store_photo(
                user_id, capture_id, view, content_type, data, root=PHOTO_ROOT
            )
    except Exception:
        photo_storage.delete_capture_files(user_id, capture_id, root=PHOTO_ROOT)
        raise

    capture = FaceCaptureDocument(
        id=capture_id, user_id=user_id, state="queued", photo_paths=paths, created_at=_now()
    )
    await face_captures_col().insert_one(capture.to_mongo())
    try:
        engine.start_capture(capture_id)
    except ServiceUnavailable:
        photo_storage.delete_capture_files(user_id, capture_id, root=PHOTO_ROOT)
        await face_captures_col().delete_many({"_id": capture_id})
        raise
    return capture


async def expire_stale_captures() -> None:
    """Same rule as photo measurement: no worker within an hour -> failed, photos deleted."""
    cutoff = _now() - STALE_AFTER
    stale = await face_captures_col().find(
        {"state": {"$in": ["queued", "processing"]}, "created_at": {"$lt": cutoff}}
    ).to_list(length=200)
    for raw in stale:
        photo_storage.delete_capture_files(raw["user_id"], raw["_id"], root=PHOTO_ROOT)
        await face_captures_col().update_one(
            {"_id": raw["_id"]},
            {"$set": {"state": "failed", "photo_paths": {}, "completed_at": _now(),
                      "failure_reason": "Building your face took too long. Please try again."}},
        )


async def get_capture(capture_id: str, user_id: str) -> FaceCaptureDocument:
    raw = await face_captures_col().find_one({"_id": capture_id, "user_id": user_id})
    if not raw:
        raise NotFound("Face capture not found")
    return FaceCaptureDocument.model_validate(raw)


async def latest_capture(user_id: str) -> FaceCaptureDocument | None:
    raw = await face_captures_col().find_one({"user_id": user_id}, sort=[("created_at", -1)])
    return FaceCaptureDocument.model_validate(raw) if raw else None


async def current_face_path(user_id: str) -> Path:
    raw = await face_captures_col().find_one({"user_id": user_id, "state": "ready"}, sort=[("created_at", -1)])
    if not raw or not raw.get("glb_path"):
        raise NotFound("No face has been added to this avatar")
    path = photo_storage.resolve(raw["glb_path"])
    if not path.is_file():
        raise NotFound("The face model file is missing on disk")
    return path


async def delete_for_user(user_id: str) -> None:
    """Remove the face (DELETE /faces) and the account-deletion cascade."""
    await face_captures_col().delete_many({"user_id": user_id})
    photo_storage.delete_user_files(user_id, root=PHOTO_ROOT)
    shutil.rmtree(get_settings().avatars_upload_root / FACE_ROOT / user_id, ignore_errors=True)
