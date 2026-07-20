"""Signature-looks business logic: CRUD, single default per user."""

from datetime import datetime, timezone

from ..core.errors import NotFound
from ..core.security import new_id
from ..db import signature_looks_col


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def list_looks(user_id: str) -> list[dict]:
    cursor = signature_looks_col().find({"user_id": user_id}).sort("created_at", 1)
    return await cursor.to_list(length=100)


async def _get_look(look_id: str, user_id: str) -> dict:
    look = await signature_looks_col().find_one({"_id": look_id, "user_id": user_id})
    if not look:
        raise NotFound("Signature look not found")
    return look


async def _clear_default(user_id: str) -> None:
    await signature_looks_col().update_many(
        {"user_id": user_id, "is_default": True}, {"$set": {"is_default": False}}
    )


async def create_look(user_id: str, name: str, items: list[dict], is_default: bool) -> dict:
    if is_default:
        await _clear_default(user_id)
    now = _now()
    look = {
        "_id": new_id("sl"),
        "user_id": user_id,
        "name": name,
        "is_default": is_default,
        "items": items,
        "created_at": now,
        "updated_at": now,
    }
    await signature_looks_col().insert_one(look)
    return look


async def update_look(
    look_id: str,
    user_id: str,
    *,
    name: str | None,
    items: list[dict] | None,
    is_default: bool | None,
) -> dict:
    await _get_look(look_id, user_id)
    updates: dict = {"updated_at": _now()}
    if name is not None:
        updates["name"] = name
    if items is not None:
        updates["items"] = items
    if is_default is not None:
        if is_default:
            await _clear_default(user_id)
        updates["is_default"] = is_default
    await signature_looks_col().update_one({"_id": look_id}, {"$set": updates})
    return await _get_look(look_id, user_id)


async def delete_look(look_id: str, user_id: str) -> None:
    await _get_look(look_id, user_id)
    await signature_looks_col().delete_one({"_id": look_id})
