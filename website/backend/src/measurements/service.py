"""Measurements business logic — async port of the mirra_measurements
create/read path, keyed on the real account id instead of fixture ids."""

from datetime import datetime, timezone
from typing import Any

from ..core.errors import NotFound
from ..db import measurements_col


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_for_user(user_id: str) -> dict:
    doc = await measurements_col().find_one({"user_id": user_id})
    if not doc:
        raise NotFound("No measurements stored for this user")
    return doc


async def submit(user_id: str, gender: str, accuracy: str, fields: dict[str, Any]) -> dict:
    """Full submit/replace. Field keys absent when not provided — same doc
    shape create_measurement_doc produced, so the CLO pipeline's reads keep
    working unchanged."""
    now = _now()
    doc = {
        "user_id": user_id,
        "gender": gender,
        "accuracy": accuracy,
        "updated_at": now,
        **{k: v for k, v in fields.items() if v is not None},
    }
    existing = await measurements_col().find_one({"user_id": user_id}, {"created_at": 1})
    doc["created_at"] = existing["created_at"] if existing else now
    await measurements_col().replace_one({"user_id": user_id}, doc, upsert=True)
    return await get_for_user(user_id)


async def patch(user_id: str, changes: dict[str, Any]) -> dict:
    updates = {k: v for k, v in changes.items() if v is not None}
    if not updates:
        return await get_for_user(user_id)
    updates["updated_at"] = _now()
    result = await measurements_col().update_one({"user_id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise NotFound("No measurements stored for this user")
    return await get_for_user(user_id)


async def delete_for_user(user_id: str) -> None:
    """Cascade hook used by the users service."""
    await measurements_col().delete_many({"user_id": user_id})
