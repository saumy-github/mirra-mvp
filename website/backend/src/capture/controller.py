"""HTTP ↔ domain translation for capture."""

from fastapi.responses import FileResponse

from . import service


def shape_session(session: dict, *, include_token: bool = False) -> dict:
    shaped = {
        "sessionId": session["_id"],
        "state": session["state"],
        "manualCode": session["manual_code"],
        "photoUploaded": session.get("photo") is not None,
        "avatarJobId": session.get("avatar_job_id"),
        "expiresAt": session["expires_at"].isoformat(),
        "createdAt": session["created_at"].isoformat(),
    }
    if include_token:
        # Only ever exposed to the session owner at creation (QR payload)
        # and to the phone that already presented it.
        shaped["token"] = session["token"]
    return shaped


async def create_session(user_id: str) -> dict:
    session = await service.create_session(user_id)
    return {"session": shape_session(session, include_token=True)}


async def get_session(session_id: str, user_id: str) -> dict:
    return {"session": shape_session(await service.get_session(session_id, user_id))}


async def cancel_session(session_id: str, user_id: str) -> dict:
    return {"session": shape_session(await service.cancel_session(session_id, user_id))}


async def resolve_code(body) -> dict:
    return {"token": await service.resolve_manual_code(body.code)}


async def get_by_token(token: str) -> dict:
    return {"session": shape_session(await service.get_by_token(token))}


async def pair(token: str) -> dict:
    return {"session": shape_session(await service.pair(token))}


async def give_consent(token: str) -> dict:
    return {"session": shape_session(await service.give_consent(token))}


async def upload_photo(token: str, filename: str, content_type: str, content: bytes) -> dict:
    session = await service.upload_photo(token, filename, content_type, content)
    return {"session": shape_session(session)}


async def complete(token: str) -> dict:
    return {"session": shape_session(await service.complete(token))}


async def get_photo(session_id: str, user_id: str) -> FileResponse:
    session = await service.get_session(session_id, user_id)
    path = service.photo_path(session)
    return FileResponse(path, media_type=session["photo"]["content_type"])
