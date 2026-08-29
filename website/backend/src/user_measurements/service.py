"""User measurements business logic — the live, website-facing measurements
store. See .agent/website-launch/23-profile-measurements-form-and-user-measurements-model.md.

Deliberately not shared with website/backend/src/measurements/service.py —
that module stays CLI/dev-fixture-only (golden_users, seed_measurements.py,
the CLO pipeline's CLI path); this one is what every website save now goes
through, dev and production alike.
"""

from datetime import datetime, timezone
from typing import Any

from ..core.errors import NotFound
from ..core.security import new_id
from ..db import user_measurements_col
from .models import UserMeasurementsDocument


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_for_user(user_id: str) -> UserMeasurementsDocument:
    raw = await user_measurements_col().find_one({"user_id": user_id})
    if not raw:
        raise NotFound("No measurements stored for this user")
    return UserMeasurementsDocument.model_validate(raw)


async def submit(user_id: str, gender: str, accuracy: str, units_preference: str, fields: dict[str, Any]) -> UserMeasurementsDocument:
    """Full submit/replace. Field keys absent when not provided — never stored as null."""
    now = _now()
    existing = await user_measurements_col().find_one({"user_id": user_id}, {"_id": 1, "created_at": 1, "measurements_version": 1})
    doc = UserMeasurementsDocument(
        id=existing["_id"] if existing else new_id("um"),
        user_id=user_id,
        gender=gender,
        accuracy=accuracy,
        units_preference=units_preference,
        measurements_version=(existing.get("measurements_version", 0) + 1) if existing else 1,
        created_at=existing["created_at"] if existing else now,
        updated_at=now,
        **{k: v for k, v in fields.items() if v is not None},
    )
    await user_measurements_col().replace_one({"user_id": user_id}, doc.to_mongo(), upsert=True)
    return await get_for_user(user_id)


async def patch(user_id: str, changes: dict[str, Any]) -> UserMeasurementsDocument:
    updates = {k: v for k, v in changes.items() if v is not None}
    if not updates:
        return await get_for_user(user_id)
    current = await get_for_user(user_id)  # 404s if none stored, same as submit's "first save" requirement
    updates["updated_at"] = _now()
    updates["measurements_version"] = current.measurements_version + 1
    result = await user_measurements_col().update_one({"user_id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise NotFound("No measurements stored for this user")
    return await get_for_user(user_id)


async def delete_for_user(user_id: str) -> None:
    """Cascade hook used by the users service."""
    await user_measurements_col().delete_many({"user_id": user_id})
