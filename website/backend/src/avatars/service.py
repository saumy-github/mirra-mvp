"""Avatars business logic: job lifecycle + profile storage.

"Start generation" reads the user's stored measurements directly — no
capture session required (backend-implementation-plan.md, Phase 4). When the
capture service lands (Phase 8), its complete() calls start_generation too.
"""

from datetime import datetime, timezone

from ..core.errors import NotFound
from ..core.security import new_id
from ..db import avatar_jobs_col, avatar_profiles_col
from ..measurements.service import get_for_user as get_measurements
from . import engine


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def start_generation(user_id: str) -> dict:
    measurements = await get_measurements(user_id)  # 404s if none stored
    snapshot = {k: v for k, v in measurements.items() if k not in ("_id",)}
    job = {
        "_id": new_id("aj"),
        "user_id": user_id,
        "engine_mode": engine.engine_mode(),
        "measurement_snapshot": snapshot,
        "state": "queued",
        "failure_reason": None,
        "avatar_profile_id": None,
        "created_at": _now(),
        "completed_at": None,
    }
    engine.start_job(job)  # live mode raises until the worker exists
    await avatar_jobs_col().insert_one(job)
    return await get_job(job["_id"], user_id)


async def get_job(job_id: str, user_id: str) -> dict:
    # Another user's job id is shaped identically to an unknown one.
    job = await avatar_jobs_col().find_one({"_id": job_id, "user_id": user_id})
    if not job:
        raise NotFound("Avatar job not found")
    if job["engine_mode"] == "demo" and job["state"] not in ("ready", "failed"):
        state = engine.derive_demo_state(job)
        if state != job["state"]:
            job["state"] = state
            updates: dict = {"state": state}
            if state == "ready":
                profile = await _materialize_profile(job)
                job["avatar_profile_id"] = profile["_id"]
                job["completed_at"] = _now()
                updates.update(avatar_profile_id=profile["_id"], completed_at=job["completed_at"])
            await avatar_jobs_col().update_one({"_id": job_id}, {"$set": updates})
    return job


async def _materialize_profile(job: dict) -> dict:
    """Create/refresh the user's single avatar profile from the job snapshot
    (idempotent — profile is unique per user)."""
    snapshot = job["measurement_snapshot"]
    now = _now()
    existing = await avatar_profiles_col().find_one({"user_id": job["user_id"]})
    profile = {
        "_id": existing["_id"] if existing else new_id("ap"),
        "user_id": job["user_id"],
        "source_job_id": job["_id"],
        "gender": snapshot.get("gender"),
        "measurements": {k: v for k, v in snapshot.items() if k not in ("user_id", "created_at", "updated_at")},
        "body_shape_type": snapshot.get("body_shape_type"),
        "skin_tone_hex": snapshot.get("skin_tone_hex"),
        "created_at": existing["created_at"] if existing else now,
        "updated_at": now,
    }
    await avatar_profiles_col().replace_one({"user_id": job["user_id"]}, profile, upsert=True)
    return profile


async def get_profile(user_id: str) -> dict | None:
    return await avatar_profiles_col().find_one({"user_id": user_id})


async def delete_profile(user_id: str) -> None:
    """Deletes the avatar profile and its jobs. Measurements are left alone —
    they have their own service and the user may want to regenerate."""
    await avatar_profiles_col().delete_many({"user_id": user_id})
    await avatar_jobs_col().delete_many({"user_id": user_id})
