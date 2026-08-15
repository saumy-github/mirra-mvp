"""Avatars business logic: job lifecycle + profile storage.

"Start generation" reads the user's stored measurements directly, triggered
straight from the frontend once measurements are saved (capture-session
photo pairing was removed — see .agent/website-launch execution logs).
"""

from datetime import datetime, timezone

from ..core.errors import NotFound
from ..core.security import new_id
from ..db import avatar_jobs_col, avatar_profiles_col
from ..user_measurements.service import get_for_user as get_measurements
from . import engine
from .models import AvatarJobDocument, AvatarProfileDocument


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def start_generation(user_id: str) -> AvatarJobDocument:
    measurements = await get_measurements(user_id)  # 404s if none stored
    job = AvatarJobDocument(
        id=new_id("aj"),
        user_id=user_id,
        measurement_snapshot=measurements.model_dump(exclude_none=True),
        state="queued",
        failure_reason=None,
        avatar_profile_id=None,
        created_at=_now(),
        completed_at=None,
    )
    engine.start_job(job)  # hands off to the CLO worker via Redis
    await avatar_jobs_col().insert_one(job.to_mongo())
    return await get_job(job.id, user_id)


async def get_job(job_id: str, user_id: str) -> AvatarJobDocument:
    # Another user's job id is shaped identically to an unknown one.
    raw = await avatar_jobs_col().find_one({"_id": job_id, "user_id": user_id})
    if not raw:
        raise NotFound("Avatar job not found")
    return AvatarJobDocument.model_validate(raw)


async def _materialize_profile(job: AvatarJobDocument) -> AvatarProfileDocument:
    """Create/refresh the user's single avatar profile from the job snapshot
    (idempotent — profile is unique per user)."""
    snapshot = job.measurement_snapshot
    now = _now()
    existing = await avatar_profiles_col().find_one({"user_id": job.user_id})
    profile = AvatarProfileDocument(
        id=existing["_id"] if existing else new_id("ap"),
        user_id=job.user_id,
        source_job_id=job.id,
        gender=snapshot.get("gender"),
        measurements={k: v for k, v in snapshot.items() if k not in ("user_id", "created_at", "updated_at")},
        body_shape_type=snapshot.get("body_shape_type"),
        skin_tone_hex=snapshot.get("skin_tone_hex"),
        created_at=existing["created_at"] if existing else now,
        updated_at=now,
    )
    await avatar_profiles_col().replace_one({"user_id": job.user_id}, profile.to_mongo(), upsert=True)
    return profile


async def get_profile(user_id: str) -> AvatarProfileDocument | None:
    raw = await avatar_profiles_col().find_one({"user_id": user_id})
    return AvatarProfileDocument.model_validate(raw) if raw else None


async def delete_profile(user_id: str) -> None:
    """Deletes the avatar profile and its jobs. Measurements are left alone —
    they have their own service and the user may want to regenerate."""
    await avatar_profiles_col().delete_many({"user_id": user_id})
    await avatar_jobs_col().delete_many({"user_id": user_id})
