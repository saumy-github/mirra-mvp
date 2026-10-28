"""Photo-measurement business logic: capture lifecycle and applying the result.

Applying goes through user_measurements.service.submit — the same write the
manual form makes — so user_measurements stays the single source the avatar
pipeline reads (clo_avatar_generation step_03), whatever produced the numbers.
"""

from datetime import datetime, timedelta, timezone

from pydantic import ValidationError as PydanticValidationError

from ..core.errors import Conflict, NotFound, ServiceUnavailable, ValidationFailed
from ..core.security import new_id
from ..db import photo_measurements_col
from ..user_measurements import service as user_measurements
from ..user_measurements.models import UserMeasurementFields
from . import engine, storage
from .models import PhotoCaptureDocument

# Same sanity ranges the avatar pipeline enforces (step_03_fetch_measurements.py),
# so a capture can't be created from inputs the pipeline would later refuse.
HEIGHT_RANGE = (120.0, 230.0)
WEIGHT_RANGE = (30.0, 250.0)
MAX_SHOE_SOLE_CM = 10.0

# A capture still queued/processing after this long has no worker coming for
# it (measure worker down, job lost). Its photos must not sit on disk.
STALE_AFTER = timedelta(hours=1)

MEASUREMENT_FIELDS = tuple(UserMeasurementFields.model_fields)
# Bust and under-bust are womenswear measurements; for men the pipeline's bust
# is just the chest again, so it is not written.
FEMALE_ONLY_FIELDS = ("bust_circumference_cm", "under_bust_circumference_cm")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_range(name: str, value: float, bounds: tuple[float, float]) -> None:
    if not bounds[0] <= value <= bounds[1]:
        raise ValidationFailed(f"{name} must be between {bounds[0]:g} and {bounds[1]:g}")


async def create_capture(
    user_id: str,
    *,
    height_cm: float,
    weight_kg: float | None,
    gender: str,
    shoe_sole_cm: float,
    front: tuple[str, bytes],
    side: tuple[str, bytes],
) -> PhotoCaptureDocument:
    """front/side are (content_type, bytes)."""
    _check_range("Height (cm)", height_cm, HEIGHT_RANGE)
    if weight_kg is not None:
        _check_range("Weight (kg)", weight_kg, WEIGHT_RANGE)
    if gender not in ("male", "female"):
        raise ValidationFailed("gender must be male or female")
    if not 0 <= shoe_sole_cm <= MAX_SHOE_SOLE_CM:
        raise ValidationFailed(f"Shoe sole must be between 0 and {MAX_SHOE_SOLE_CM:g} cm")

    await expire_stale_captures()
    capture_id = new_id("pm")
    try:
        front_path = storage.store_photo(user_id, capture_id, "front", *front)
        side_path = storage.store_photo(user_id, capture_id, "side", *side)
    except Exception:
        storage.delete_capture_files(user_id, capture_id)
        raise

    capture = PhotoCaptureDocument(
        id=capture_id,
        user_id=user_id,
        state="queued",
        height_cm=height_cm,
        weight_kg=weight_kg,
        gender=gender,
        shoe_sole_cm=shoe_sole_cm,
        front_path=front_path,
        side_path=side_path,
        created_at=_now(),
    )
    # Insert before enqueueing, as the avatar/try-on services do: an idle
    # worker can otherwise look the job up before its document exists.
    await photo_measurements_col().insert_one(capture.to_mongo())
    try:
        engine.start_capture(capture_id)
    except ServiceUnavailable:
        # No queue means no worker will ever delete these photos.
        storage.delete_capture_files(user_id, capture_id)
        await photo_measurements_col().delete_many({"_id": capture_id})
        raise
    return capture


async def expire_stale_captures() -> int:
    """Fail captures no worker picked up in time, and delete their photos.

    Run opportunistically on every new upload (cheap: indexed, usually zero
    hits), so a downed `measure` worker can't leave body photos on disk.
    """
    cutoff = _now() - STALE_AFTER
    stale = await photo_measurements_col().find(
        {"state": {"$in": ["queued", "processing"]}, "created_at": {"$lt": cutoff}}
    ).to_list(length=200)
    for raw in stale:
        storage.delete_capture_files(raw["user_id"], raw["_id"])
        await photo_measurements_col().update_one(
            {"_id": raw["_id"]},
            {"$set": {"state": "failed", "completed_at": _now(), "front_path": None, "side_path": None,
                      "failure_reason": "Measuring took too long. Please try again."}},
        )
    return len(stale)


async def get_capture(capture_id: str, user_id: str) -> PhotoCaptureDocument:
    # Another user's capture id is shaped identically to an unknown one.
    raw = await photo_measurements_col().find_one({"_id": capture_id, "user_id": user_id})
    if not raw:
        raise NotFound("Photo measurement not found")
    return PhotoCaptureDocument.model_validate(raw)


async def latest_capture(user_id: str) -> PhotoCaptureDocument | None:
    raw = await photo_measurements_col().find_one({"user_id": user_id}, sort=[("created_at", -1)])
    return PhotoCaptureDocument.model_validate(raw) if raw else None


async def apply_capture(capture_id: str, user_id: str, overrides: dict[str, float]):
    """Save a ready capture (with the shopper's corrections) as their measurements.

    Fields the photos don't produce — weight when it wasn't entered, anything
    typed earlier — are kept from the existing document rather than dropped
    by the full replace.
    """
    capture = await get_capture(capture_id, user_id)
    if capture.state not in ("ready", "applied"):
        raise Conflict(f"This photo measurement is {capture.state}, not ready to save", code="capture_not_ready")
    unknown = sorted(set(overrides) - set(MEASUREMENT_FIELDS))
    if unknown:
        raise ValidationFailed(f"Unknown measurement fields: {', '.join(unknown)}")

    try:
        existing = await user_measurements.get_for_user(user_id)
    except NotFound:
        existing = None

    fields: dict = {}
    if existing is not None:
        fields.update({k: getattr(existing, k) for k in MEASUREMENT_FIELDS if getattr(existing, k) is not None})
    fields.update({k: v for k, v in (capture.profile or {}).items() if k in MEASUREMENT_FIELDS and v is not None})
    if capture.weight_kg is not None:
        fields["weight_kg"] = capture.weight_kg
    fields.update(overrides)
    if capture.gender == "male":
        for k in FEMALE_ONLY_FIELDS:
            fields.pop(k, None)
    # Re-validate the merged set exactly as a manual submit would be.
    try:
        fields = UserMeasurementFields.model_validate(fields).model_dump(exclude_none=True)
    except PydanticValidationError as exc:
        problems = "; ".join(f"{e['loc'][0]}: {e['msg']}" for e in exc.errors())
        raise ValidationFailed(f"Invalid measurements: {problems}") from exc

    doc = await user_measurements.submit(
        user_id,
        capture.gender,
        "approx",  # photo-derived, not tape-measured
        existing.units_preference if existing else "metric",
        fields,
        source="photo",
        photo_capture_id=capture.id,
    )
    await photo_measurements_col().update_one(
        {"_id": capture.id}, {"$set": {"state": "applied", "applied_at": _now()}}
    )
    return doc, await get_capture(capture.id, user_id)


async def delete_for_user(user_id: str) -> None:
    """Cascade hook used by the users service."""
    from .pairing import delete_for_user as delete_pairings

    await photo_measurements_col().delete_many({"user_id": user_id})
    await delete_pairings(user_id)
    storage.delete_user_files(user_id)
