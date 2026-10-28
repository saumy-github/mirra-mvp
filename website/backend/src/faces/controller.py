"""HTTP ↔ domain translation for faces."""

from fastapi.responses import FileResponse

from . import service
from .models import STAGE_LABELS, FaceCaptureDocument


def shape_face(c: FaceCaptureDocument) -> dict:
    return {
        "faceId": c.id,
        "state": c.state,
        "stageLabel": STAGE_LABELS.get(c.state, c.state),
        "hasModel": c.state == "ready" and bool(c.glb_path),
        "views": c.views or sorted(c.photo_paths),
        "skinToneHex": c.skin_tone_hex,
        "warnings": c.warnings,
        "failureReason": c.failure_reason,
        "createdAt": c.created_at.isoformat(),
        "completedAt": c.completed_at.isoformat() if c.completed_at else None,
    }


async def create(user_id: str, photos: dict) -> dict:
    return {"face": shape_face(await service.create_capture(user_id, photos))}


async def get(capture_id: str, user_id: str) -> dict:
    return {"face": shape_face(await service.get_capture(capture_id, user_id))}


async def latest(user_id: str) -> dict:
    capture = await service.latest_capture(user_id)
    return {"face": shape_face(capture) if capture else None}


async def current_glb(user_id: str) -> FileResponse:
    return FileResponse(
        path=await service.current_face_path(user_id),
        media_type="model/gltf-binary",
        filename="face.glb",
        # Same URL for whichever face is current, so it must not be cached for long.
        headers={"Cache-Control": "private, no-cache"},
    )


async def delete(user_id: str) -> dict:
    await service.delete_for_user(user_id)
    return {"ok": True}
