"""Try-on business logic: sessions, render lifecycle, cached restore."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..avatars.service import get_profile as get_avatar_profile
from ..catalog.service import resolve_pair
from ..config import get_settings
from ..core.errors import Conflict, NotFound
from ..core.security import new_id
from ..db import tryon_renders_col, tryon_sessions_col
from . import engine
from .models import TryonRenderDocument, TryonSessionDocument


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_session(user_id: str) -> TryonSessionDocument:
    session = TryonSessionDocument(id=new_id("tos"), user_id=user_id, created_at=_now())
    await tryon_sessions_col().insert_one(session.to_mongo())
    return session


async def _get_session(session_id: str, user_id: str) -> TryonSessionDocument:
    # Cross-user session ids are shaped identically to unknown ones.
    raw = await tryon_sessions_col().find_one({"_id": session_id, "user_id": user_id})
    if not raw:
        raise NotFound("Try-on session not found")
    return TryonSessionDocument.model_validate(raw)


async def request_render(
    session_id: str, user_id: str, cloth_id: str, size_id: str
) -> TryonRenderDocument:
    await _get_session(session_id, user_id)
    _, garment = await resolve_pair(cloth_id, size_id)  # 404s on an unoffered pairing
    profile = await get_avatar_profile(user_id)
    if profile is None:
        raise Conflict("Generate your avatar before requesting a try-on", code="avatar_required")

    render = TryonRenderDocument(
        id=new_id("r"),
        session_id=session_id,
        user_id=user_id,
        cloth_id=cloth_id,
        size_id=size_id,
        garment_snapshot=garment,
        avatar_profile_id=profile.id,
        state="requested",
        failure_reason=None,
        created_at=_now(),
        completed_at=None,
    )
    # Insert before enqueueing: an idle worker can otherwise read the job
    # before its document exists, log "not found" and drop it, leaving the
    # render stuck in `requested` forever (doc 13 section 43).
    await tryon_renders_col().insert_one(render.to_mongo())
    engine.start_render(render)  # hands off to the CLO worker via Redis
    return render


async def get_render(session_id: str, render_id: str, user_id: str) -> TryonRenderDocument:
    """Poll while in flight; cheap restore once ready — a ready render is
    returned straight from Mongo, nothing recomputes (Hanger path)."""
    raw = await tryon_renders_col().find_one(
        {"_id": render_id, "session_id": session_id, "user_id": user_id}
    )
    if not raw:
        raise NotFound("Render not found")
    return TryonRenderDocument.model_validate(raw)


@dataclass
class ResolvedRenderGlb:
    path: Path


async def get_render_glb(session_id: str, render_id: str, user_id: str) -> ResolvedRenderGlb:
    """Resolves this render's stored GLB against the upload root. Mirrors
    avatars.service.get_profile_glb, including the traversal guard."""
    render = await get_render(session_id, render_id, user_id)  # 404s cross-user
    if not render.render_glb_path:
        raise NotFound("No try-on model is available for this render yet")

    upload_root = get_settings().avatars_upload_root.resolve()
    resolved_path = (upload_root / render.render_glb_path).resolve()

    # The path is server-written, but do not trust it blindly.
    if upload_root not in resolved_path.parents and resolved_path != upload_root:
        raise NotFound("Stored render path is invalid")

    if not resolved_path.is_file():
        raise NotFound("Try-on model file is missing on disk")

    return ResolvedRenderGlb(path=resolved_path)


async def list_history(user_id: str, limit: int = 20) -> list[TryonRenderDocument]:
    """Recent ready renders across sessions — seeds the Hanger."""
    cursor = (
        tryon_renders_col()
        .find({"user_id": user_id, "state": "ready"})
        .sort("created_at", -1)
        .limit(max(1, min(limit, 50)))
    )
    raws = await cursor.to_list(length=limit)
    return [TryonRenderDocument.model_validate(r) for r in raws]
