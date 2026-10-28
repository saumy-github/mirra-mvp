"""Face reconstruction task body — 1-3 face photos -> face.glb.

Entrypoint: worker.tasks.run_face_reconstruction, on the `measure` queue (the
photo-measurement worker: MediaPipe, no CLO). Photos are deleted once used,
whatever the outcome. A new face replaces the previous one (one face per user).
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone

from src.config import get_settings
from src.db import face_captures_col
from src.faces import service as faces
from src.faces.models import FaceCaptureDocument
from src.photo_measurements import storage

logger = logging.getLogger("mirra.worker.face")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _run_face_reconstruction(capture_id: str) -> None:
    raw = await face_captures_col().find_one({"_id": capture_id})
    if not raw:
        logger.error("run_face_reconstruction: capture %s not found", capture_id)
        return
    capture = FaceCaptureDocument.model_validate(raw)
    if capture.state != "queued":
        logger.info("run_face_reconstruction: capture %s is %s, skipping", capture_id, capture.state)
        return

    await face_captures_col().update_one({"_id": capture_id}, {"$set": {"state": "processing"}})
    try:
        if "front" not in capture.photo_paths:
            raise RuntimeError("The photos for this face are no longer available.")
        from face_reconstruction.pipeline import reconstruct_face

        glb, info = reconstruct_face({view: storage.resolve(p) for view, p in capture.photo_paths.items()})
        out_dir = faces.face_dir(capture.user_id, capture_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "face.glb").write_bytes(glb)
    except Exception as exc:
        logger.exception("run_face_reconstruction %s: failed", capture_id)
        await face_captures_col().update_one(
            {"_id": capture_id},
            {"$set": {"state": "failed", "failure_reason": _reason(exc), "completed_at": _now(), "photo_paths": {}}},
        )
        return
    finally:
        storage.delete_capture_files(capture.user_id, capture_id, root=faces.PHOTO_ROOT)

    root = get_settings().avatars_upload_root
    await face_captures_col().update_one(
        {"_id": capture_id},
        {"$set": {
            "state": "ready",
            "glb_path": (faces.face_dir(capture.user_id, capture_id) / "face.glb").relative_to(root).as_posix(),
            "views": info["views"],
            "skin_tone_hex": info["skin_tone_hex"],
            "warnings": info["warnings"],
            "completed_at": _now(),
            "photo_paths": {},
        }},
    )
    await _drop_older_faces(capture)
    logger.info("run_face_reconstruction %s: ready (%s)", capture_id, ", ".join(info["views"]))


async def _drop_older_faces(current: FaceCaptureDocument) -> None:
    """One face per user: older ready faces' files and documents go."""
    older = await face_captures_col().find(
        {"user_id": current.user_id, "state": "ready", "_id": {"$ne": current.id}}
    ).to_list(length=50)
    for raw in older:
        shutil.rmtree(faces.face_dir(current.user_id, raw["_id"]), ignore_errors=True)
        await face_captures_col().delete_many({"_id": raw["_id"]})


def _reason(exc: Exception) -> str:
    """Shopper-facing text, never the raw exception (server paths)."""
    text = str(exc).lower()
    if "no face detected in the front" in text:
        return "We couldn't find your face in the front photo. Face the camera in good light and retake it."
    return "Something went wrong building your face. Please try again."
