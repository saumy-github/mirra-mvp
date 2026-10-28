"""Photo measurement task bodies — front + side photo + height -> measurements.

Entrypoint: worker.tasks.run_photo_measurement, enqueued on the `measure` queue
by website/backend/src/photo_measurements/engine.py. Run a worker for it with

    python worker/run_worker.py --queues measure

It needs no CLO: any machine with the repo .venv (torch, mediapipe) and the
model weights in photo_measurement/models/ can serve this queue.

The photos are deleted once measured, whatever the outcome — they are images
of a person's body, and only the numbers are kept.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.db import photo_measurements_col
from src.photo_measurements import storage
from src.photo_measurements.models import PhotoCaptureDocument

logger = logging.getLogger("mirra.worker.measure")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _run_photo_measurement(capture_id: str) -> None:
    raw = await photo_measurements_col().find_one({"_id": capture_id})
    if not raw:
        logger.error("run_photo_measurement: capture %s not found, nothing to do", capture_id)
        return
    capture = PhotoCaptureDocument.model_validate(raw)
    if capture.state != "queued":
        logger.info("run_photo_measurement: capture %s is %s, skipping", capture_id, capture.state)
        return

    await photo_measurements_col().update_one({"_id": capture_id}, {"$set": {"state": "processing"}})
    try:
        if not capture.front_path or not capture.side_path:
            raise RuntimeError("The photos for this measurement are no longer available.")
        # Imported here so a CLO-only worker never pays for torch + MediaPipe.
        from photo_measurement.pipeline import measure_photos

        result = measure_photos(
            storage.resolve(capture.front_path),
            storage.resolve(capture.side_path),
            capture.height_cm,
            capture.weight_kg,
            capture.gender,
            capture.shoe_sole_cm,
        )
    except Exception as exc:  # unreadable photo, no person found, missing model...
        logger.exception("run_photo_measurement %s: failed", capture_id)
        await photo_measurements_col().update_one(
            {"_id": capture_id},
            {"$set": {"state": "failed", "failure_reason": _reason(exc), "completed_at": _now(),
                      "front_path": None, "side_path": None}},
        )
        return
    finally:
        storage.delete_capture_files(capture.user_id, capture_id)

    await photo_measurements_col().update_one(
        {"_id": capture_id},
        {
            "$set": {
                "state": "ready",
                "profile": result["profile"],
                "measurements": result["measurements"],
                "warnings": result["warnings"],
                "model": result["model"],
                "completed_at": _now(),
                "front_path": None,
                "side_path": None,
            }
        },
    )
    logger.info("run_photo_measurement %s: ready (%d warnings)", capture_id, len(result["warnings"]))
    # Onboarding continues even if the shopper closes the browser while the
    # model runs. The desktop poll also reconciles if this hand-off fails.
    try:
        from src.photo_measurements.setup import after_measurement

        await after_measurement(capture_id)
    except Exception:
        logger.exception("Could not advance onboarding for capture %s", capture_id)


def _reason(exc: Exception) -> str:
    """Shopper-facing text — never the raw exception, which carries server paths
    (the full error is in the worker log). MediaPipe finding nobody is the
    common, fixable failure."""
    if "no person detected" in str(exc).lower():
        return "We couldn't find a full body in one of the photos. Retake it with your whole body in frame."
    return "Something went wrong measuring these photos. Please try again."
