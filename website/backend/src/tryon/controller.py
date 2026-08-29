"""HTTP ↔ domain translation for try-on."""

from fastapi.responses import FileResponse

from ..catalog.controller import shape_garment
from . import service
from .models import STAGE_LABELS, TryonRenderDocument


def shape_render(render: TryonRenderDocument) -> dict:
    ready = render.state == "ready"
    return {
        "renderId": render.id,
        "sessionId": render.session_id,
        "state": render.state,
        "stageLabel": STAGE_LABELS.get(render.state, render.state),
        "clothId": render.cloth_id,
        "sizeId": render.size_id,
        "hasModel": bool(render.render_glb_path),
        "avatarProfileId": render.avatar_profile_id,
        "failureReason": render.failure_reason,
        "createdAt": render.created_at.isoformat(),
        "completedAt": render.completed_at.isoformat() if render.completed_at else None,
        "result": (
            {"garment": shape_garment(render.garment_snapshot)}
            if ready
            else None
        ),
    }


async def create_session(user_id: str) -> dict:
    session = await service.create_session(user_id)
    return {"session": {"sessionId": session.id, "createdAt": session.created_at.isoformat()}}


async def request_render(session_id: str, user_id: str, body) -> dict:
    render = await service.request_render(session_id, user_id, body.cloth_id, body.size_id)
    return {"render": shape_render(render)}


async def get_render(session_id: str, render_id: str, user_id: str) -> dict:
    render = await service.get_render(session_id, render_id, user_id)
    return {"render": shape_render(render)}


async def get_render_glb(session_id: str, render_id: str, user_id: str) -> FileResponse:
    resolved = await service.get_render_glb(session_id, render_id, user_id)
    return FileResponse(
        path=resolved.path,
        media_type="model/gltf-binary",
        filename="tryon.glb",
        # Render-scoped path, never overwritten in place.
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


async def history(user_id: str, limit: int) -> dict:
    renders = await service.list_history(user_id, limit)
    return {"items": [shape_render(r) for r in renders]}
