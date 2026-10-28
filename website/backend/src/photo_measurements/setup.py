"""Durable photo → measurements → CLO → review orchestration.

The phone authorizes the build by finishing its capture. Both that request
and the measurement worker advance the same record; an atomic claim prevents
two CLO jobs. Browser timers only present progress, never complete a stage.
"""

import logging
import math
from datetime import timedelta

from ..avatars import service as avatars
from ..avatars.controller import shape_job
from ..core.errors import Conflict, NotFound, ValidationFailed
from ..core.security import new_id
from ..faces import service as faces
from ..faces.controller import shape_face
from ..user_measurements import service as measurements
from . import pairing, service
from .models import PhotoPairingDocument

logger = logging.getLogger(__name__)
NUMERIC_FIELDS = {
    "height_cm": (120, 230), "weight_kg": (30, 250),
    "shoulder_width_cm": (20, 80), "chest_circumference_cm": (40, 200),
    "waist_circumference_cm": (40, 200), "hip_circumference_cm": (40, 200),
    "leg_length_cm": (40, 130), "bust_circumference_cm": (40, 200),
    "under_bust_circumference_cm": (40, 200),
}


async def latest(user_id: str) -> PhotoPairingDocument | None:
    raw = await pairing.photo_pairings_col().find_one(
        {"user_id": user_id, "build_avatar": True, "revoked": False},
        sort=[("created_at", -1)],
    )
    return PhotoPairingDocument.model_validate(raw) if raw else None


async def advance(pairing_id: str, user_id: str) -> None:
    p = await pairing.get_pairing(pairing_id, user_id)
    if not p.build_avatar or p.revoked or not p.capture_complete_at:
        return
    if p.build_state in ("building", "failed"):
        return
    # A server restart between claiming and enqueueing can be resumed. A
    # reserved job id lets start_generation reuse an already-created job.
    if p.build_state == "starting":
        if p.build_claimed_at and pairing._now() - p.build_claimed_at < timedelta(minutes=2):
            return
        await pairing.photo_pairings_col().update_one(
            {"_id": p.id, "build_state": "starting", "build_claimed_at": p.build_claimed_at},
            {"$set": {"build_state": "idle"}},
        )
    capture = await service.get_capture(p.capture_id, user_id) if p.capture_id else None
    if p.measurement_method == "photos" and (not capture or capture.state not in ("ready", "applied")):
        return
    job_id = p.avatar_job_id or new_id("aj")
    claim = await pairing.photo_pairings_col().update_one(
        {"_id": p.id, "build_state": "idle", "revoked": False},
        {"$set": {"build_state": "starting", "build_claimed_at": pairing._now(),
                  "avatar_job_id": job_id, "build_error": None}},
    )
    if not claim.matched_count:
        return
    try:
        if capture and capture.state != "applied":
            # Save model estimates for a preview build. reviewed_at is only
            # written after the shopper explicitly confirms the review.
            await service.apply_capture(capture.id, user_id, {})
        if p.review_overrides:
            saved = await measurements.get_for_user(user_id)
            changed = {k: v for k, v in p.review_overrides.items() if getattr(saved, k) != v}
            if changed:
                await measurements.patch(user_id, changed)
        await avatars.start_generation(user_id, job_id=job_id)
        await pairing.photo_pairings_col().update_one(
            {"_id": p.id}, {"$set": {"build_state": "building"}},
        )
    except Exception:
        logger.exception("Could not start avatar setup %s", p.id)
        await pairing.photo_pairings_col().update_one(
            {"_id": p.id}, {"$set": {"build_state": "failed",
                "build_error": "We couldn't start your avatar. Your photos are synced; try the build again."}},
        )


async def after_measurement(capture_id: str) -> None:
    """Worker callback. A polling desktop is not required to keep work going."""
    raw = await pairing.photo_pairings_col().find_one(
        {"capture_id": capture_id, "build_avatar": True, "revoked": False}
    )
    if raw:
        await advance(raw["_id"], raw["user_id"])


async def finish(token: str, skip_face: bool) -> None:
    p = await pairing._resolve_token(token)
    if p.capture_complete_at:
        if skip_face and p.face_capture_id and not p.reviewed_at:
            face = await faces.get_capture(p.face_capture_id, p.user_id)
            if face.state == "failed":
                await pairing.photo_pairings_col().update_one(
                    {"_id": p.id}, {"$set": {"face_skipped": True}},
                )
        return
    if not p.capture_id and p.measurement_method != "manual":
        raise Conflict("Upload your front and side photos first.")
    if not p.face_capture_id and not skip_face and p.build_avatar:
        raise Conflict("Add a face photo or choose to continue without one.")
    await pairing.photo_pairings_col().update_one(
        {"_id": p.id}, {"$set": {"capture_complete_at": pairing._now(),
            "phone_stage": "complete", "face_skipped": skip_face}},
    )
    await advance(p.id, p.user_id)


async def status(pairing_id: str, user_id: str) -> dict:
    from .controller import shape_capture, shape_pairing

    await advance(pairing_id, user_id)
    p = await pairing.get_pairing(pairing_id, user_id)
    capture = await service.get_capture(p.capture_id, user_id) if p.capture_id else None
    face = await faces.get_capture(p.face_capture_id, user_id) if p.face_capture_id else None
    job = None
    if p.avatar_job_id:
        try:
            job = await avatars.get_job(p.avatar_job_id, user_id)
        except NotFound:
            pass  # the claimed job hasn't been inserted yet
    values = {}
    if p.measurement_method == "manual" or (capture and capture.state == "applied"):
        saved = await measurements.get_for_user(user_id)
        values = {k: getattr(saved, k) for k in NUMERIC_FIELDS if getattr(saved, k) is not None}
    elif capture:
        values = {k: v for k, v in (capture.profile or {}).items() if k in NUMERIC_FIELDS and v is not None}

    failure = p.build_error
    if capture and capture.state == "failed":
        failure = capture.failure_reason or "We couldn't measure your photos. Please retake them."
    elif job and job.state == "failed":
        failure = job.failure_reason or "We couldn't build your avatar. Please try again."
    elif face and face.state == "failed" and not p.face_skipped:
        failure = face.failure_reason or "We couldn't create your face. You can retake it or continue without it."

    ready = bool(p.build_state == "building" and job and job.state == "ready" and (p.face_skipped or (face and face.state == "ready")))
    if ready and p.review_requested_at and not p.reviewed_at:
        p.reviewed_at = pairing._now()
        await pairing.photo_pairings_col().update_one(
            {"_id": p.id}, {"$set": {"reviewed_at": p.reviewed_at}},
        )
    state = (
        "complete" if p.reviewed_at else "failed" if failure else
        "review" if ready else "updating" if p.review_requested_at else
        "building" if job else "measuring" if p.capture_complete_at else
        "syncing" if p.phone_stage == "uploading" else
        "capturing" if p.phone_stage == "capturing" or capture else "waiting"
    )
    return {"pairing": shape_pairing(p), "capture": shape_capture(capture) if capture else None,
            "face": shape_face(face) if face else None, "job": shape_job(job) if job else None,
            "state": state, "measurements": values, "failureReason": failure}


async def review(pairing_id: str, user_id: str, overrides: dict[str, float]) -> dict:
    p = await pairing.get_pairing(pairing_id, user_id)
    if p.revoked or not p.build_avatar:
        raise Conflict("This setup is no longer active. Open your latest setup to continue.")
    current = await status(pairing_id, user_id)
    if p.review_requested_at or p.reviewed_at:
        return current  # a double-click or retried response must not start another build
    if current["state"] != "review":
        raise Conflict("Wait until your avatar is ready before confirming your measurements.")
    for key, value in overrides.items():
        if key not in NUMERIC_FIELDS:
            raise ValidationFailed(f"Unknown measurement: {key}")
        lo, hi = NUMERIC_FIELDS[key]
        if not math.isfinite(value) or not lo <= value <= hi:
            raise ValidationFailed(f"{key} must be between {lo} and {hi}.")
    saved = await measurements.get_for_user(user_id)
    changes = {k: v for k, v in overrides.items() if getattr(saved, k) != v}
    if saved.gender == "male" and any(k in changes for k in service.FEMALE_ONLY_FIELDS):
        raise ValidationFailed("Bust measurements aren't part of this profile.")
    claim = await pairing.photo_pairings_col().update_one(
        {"_id": p.id, "review_requested_at": None, "revoked": False},
        {"$set": {"review_requested_at": pairing._now(), **(
            {"review_overrides": changes, "build_state": "idle", "avatar_job_id": new_id("aj")}
            if changes else {"reviewed_at": pairing._now()}
        )}},
    )
    if not claim.matched_count:
        return await status(p.id, user_id)
    if changes:
        await advance(p.id, user_id)
    return await status(p.id, user_id)


async def retry(pairing_id: str, user_id: str, skip_face: bool = False) -> dict:
    p = await pairing.get_pairing(pairing_id, user_id)
    if p.revoked or not p.build_avatar:
        raise Conflict("This setup is no longer active. Open your latest setup to continue.")
    current = await status(pairing_id, user_id)
    p = await pairing.get_pairing(pairing_id, user_id)
    if skip_face:
        if not current["face"] or current["face"]["state"] != "failed":
            raise Conflict("Your face is still being made.")
        await pairing.photo_pairings_col().update_one({"_id": p.id}, {"$set": {"face_skipped": True}})
    if p.build_state == "failed" or (current["job"] and current["job"]["state"] == "failed"):
        await pairing.photo_pairings_col().update_one(
            {"_id": p.id}, {"$set": {"build_state": "idle", "avatar_job_id": None, "build_error": None}},
        )
    return await status(p.id, user_id)
