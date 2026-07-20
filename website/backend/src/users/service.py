"""Users business logic: profile, consents, cascading account deletion."""

from datetime import datetime, timezone

from ..auth.service import delete_all_for_user as delete_refresh_tokens
from ..capture.service import delete_all_for_user as delete_capture_data
from ..core.errors import NotFound
from ..db import (
    avatar_jobs_col,
    avatar_profiles_col,
    measurements_col,
    signature_looks_col,
    tryon_renders_col,
    tryon_sessions_col,
    users_col,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_profile(user_id: str) -> dict:
    user = await users_col().find_one({"_id": user_id})
    if not user:
        raise NotFound("User not found")
    return user


async def update_profile(user_id: str, *, name: str | None) -> dict:
    updates: dict = {"updated_at": _now()}
    if name is not None:
        updates["name"] = name
    result = await users_col().update_one({"_id": user_id}, {"$set": updates})
    if result.matched_count == 0:
        raise NotFound("User not found")
    return await get_profile(user_id)


async def update_consents(user_id: str, consents: dict[str, bool]) -> dict:
    sets = {f"consents.{key}": bool(value) for key, value in consents.items()}
    sets["updated_at"] = _now()
    result = await users_col().update_one({"_id": user_id}, {"$set": sets})
    if result.matched_count == 0:
        raise NotFound("User not found")
    return await get_profile(user_id)


async def delete_account(user_id: str) -> None:
    """Account deletion cascades across every collection that keys on
    user_id (backend-structure-plan.md invariant). Capture's hook also
    removes the retained photo files from disk."""
    user = await users_col().find_one({"_id": user_id}, {"_id": 1})
    if not user:
        raise NotFound("User not found")

    await measurements_col().delete_many({"user_id": user_id})
    await avatar_jobs_col().delete_many({"user_id": user_id})
    await avatar_profiles_col().delete_many({"user_id": user_id})
    await tryon_sessions_col().delete_many({"user_id": user_id})
    await tryon_renders_col().delete_many({"user_id": user_id})
    await signature_looks_col().delete_many({"user_id": user_id})
    await delete_capture_data(user_id)
    await delete_refresh_tokens(user_id)
    await users_col().delete_one({"_id": user_id})
