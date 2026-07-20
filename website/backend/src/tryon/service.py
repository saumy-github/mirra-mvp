"""Try-on business logic: sessions, render lifecycle, cached restore."""

from datetime import datetime, timezone

from ..avatars.service import get_profile as get_avatar_profile
from ..catalog.service import get_garment
from ..core.errors import Conflict, NotFound
from ..core.security import new_id
from ..db import tryon_renders_col, tryon_sessions_col
from . import engine


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_session(user_id: str) -> dict:
    session = {"_id": new_id("tos"), "user_id": user_id, "created_at": _now()}
    await tryon_sessions_col().insert_one(session)
    return session


async def _get_session(session_id: str, user_id: str) -> dict:
    # Cross-user session ids are shaped identically to unknown ones.
    session = await tryon_sessions_col().find_one({"_id": session_id, "user_id": user_id})
    if not session:
        raise NotFound("Try-on session not found")
    return session


async def request_render(session_id: str, user_id: str, size_id: str) -> dict:
    await _get_session(session_id, user_id)
    garment = await get_garment(size_id)  # 404s on unknown garment
    profile = await get_avatar_profile(user_id)
    if profile is None:
        raise Conflict("Generate your avatar before requesting a try-on", code="avatar_required")

    render = {
        "_id": new_id("r"),
        "session_id": session_id,
        "user_id": user_id,
        "size_id": size_id,
        "garment_snapshot": {k: v for k, v in garment.items() if k != "_id"},
        "avatar_profile_id": profile["_id"],
        "engine_mode": engine.engine_mode(),
        "state": "requested",
        "failure_reason": None,
        "created_at": _now(),
        "completed_at": None,
    }
    engine.start_render(render)  # live mode raises until the worker exists
    await tryon_renders_col().insert_one(render)
    return render


async def get_render(session_id: str, render_id: str, user_id: str) -> dict:
    """Poll while in flight; cheap restore once ready — a ready render is
    returned straight from Mongo, nothing recomputes (Hanger path)."""
    render = await tryon_renders_col().find_one(
        {"_id": render_id, "session_id": session_id, "user_id": user_id}
    )
    if not render:
        raise NotFound("Render not found")
    if render["engine_mode"] == "demo" and render["state"] not in ("ready", "failed"):
        state = engine.derive_demo_state(render)
        if state != render["state"]:
            render["state"] = state
            updates: dict = {"state": state}
            if state == "ready":
                render["completed_at"] = _now()
                updates["completed_at"] = render["completed_at"]
            await tryon_renders_col().update_one({"_id": render_id}, {"$set": updates})
    return render


async def list_history(user_id: str, limit: int = 20) -> list[dict]:
    """Recent ready renders across sessions — seeds the Hanger."""
    cursor = (
        tryon_renders_col()
        .find({"user_id": user_id, "state": "ready"})
        .sort("created_at", -1)
        .limit(max(1, min(limit, 50)))
    )
    return await cursor.to_list(length=limit)
