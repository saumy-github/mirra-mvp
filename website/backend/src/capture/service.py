"""Capture business logic: QR pairing lifecycle, photo storage, hand-off to
avatar generation. Phone-side calls authenticate by the one-time token, not
a session (the paired phone has no cookie/JWT)."""

import secrets
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..avatars.service import start_generation
from ..config import get_settings
from ..core.errors import Conflict, Gone, NotFound, ValidationFailed
from ..core.security import new_id
from ..db import capture_sessions_col, measurements_col
from .models import (
    ALLOWED_CONTENT_TYPES,
    MANUAL_CODE_ALPHABET,
    MANUAL_CODE_LENGTH,
    MAX_PHOTO_BYTES,
    SESSION_TTL_MINUTES,
    CapturePhoto,
    CaptureSessionDocument,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _session_dir(session_id: str) -> Path:
    return get_settings().uploads_path / session_id


def _new_manual_code() -> str:
    return "".join(secrets.choice(MANUAL_CODE_ALPHABET) for _ in range(MANUAL_CODE_LENGTH))


def _is_expired(session: CaptureSessionDocument) -> bool:
    return session.state not in ("completed", "cancelled") and session.expires_at <= _now()


# --- Desktop side (authenticated user) ------------------------------------


async def create_session(user_id: str) -> CaptureSessionDocument:
    now = _now()
    for _ in range(5):  # manual_code is unique-indexed; retry on collision
        session = CaptureSessionDocument(
            id=new_id("cs"),
            user_id=user_id,
            token=secrets.token_urlsafe(24),
            manual_code=_new_manual_code(),
            state="created",
            photo=None,
            avatar_job_id=None,
            expires_at=now + timedelta(minutes=SESSION_TTL_MINUTES),
            created_at=now,
            updated_at=now,
            paired_at=None,
            completed_at=None,
        )
        try:
            await capture_sessions_col().insert_one(session.to_mongo())
            return session
        except Exception:
            continue
    raise Conflict("Could not allocate a pairing code, try again")


async def get_session(session_id: str, user_id: str) -> CaptureSessionDocument:
    raw = await capture_sessions_col().find_one({"_id": session_id, "user_id": user_id})
    if not raw:
        raise NotFound("Capture session not found")
    return CaptureSessionDocument.model_validate(raw)


async def cancel_session(session_id: str, user_id: str) -> CaptureSessionDocument:
    session = await get_session(session_id, user_id)
    if session.state in ("completed", "cancelled"):
        return session
    await _update(session_id, {"state": "cancelled"})
    return await get_session(session_id, user_id)


async def resolve_manual_code(code: str) -> str:
    raw = await capture_sessions_col().find_one({"manual_code": code.strip().upper()})
    if not raw:
        raise NotFound("Unknown pairing code")
    session = CaptureSessionDocument.model_validate(raw)
    if _is_expired(session) or session.state == "cancelled":
        raise Gone("This pairing code has expired")
    return session.token


# --- Phone side (token-scoped) --------------------------------------------


async def _get_by_token(token: str) -> CaptureSessionDocument:
    raw = await capture_sessions_col().find_one({"token": token})
    if not raw:
        raise NotFound("Capture session not found")
    session = CaptureSessionDocument.model_validate(raw)
    if _is_expired(session) or session.state == "cancelled":
        raise Gone("This capture session is no longer active")
    return session


async def get_by_token(token: str) -> CaptureSessionDocument:
    return await _get_by_token(token)


async def pair(token: str) -> CaptureSessionDocument:
    session = await _get_by_token(token)
    if session.state != "created":
        # One-time pairing: a second attempt is a hijack signal (reference
        # contract shapes this as 409).
        raise Conflict("This session is already paired", code="already_paired")
    await _update(session.id, {"state": "paired", "paired_at": _now()})
    return await _get_by_token(token)


async def give_consent(token: str) -> CaptureSessionDocument:
    session = await _get_by_token(token)
    if session.state not in ("paired",):
        raise Conflict("Pair the session before giving consent")
    await _update(session.id, {"state": "consented"})
    return await _get_by_token(token)


async def upload_photo(token: str, filename: str, content_type: str, content: bytes) -> CaptureSessionDocument:
    session = await _get_by_token(token)
    if session.state not in ("consented", "uploaded"):
        raise Conflict("Give capture consent before uploading")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationFailed(f"content type must be one of {ALLOWED_CONTENT_TYPES}")
    if len(content) == 0:
        raise ValidationFailed("Empty upload")
    if len(content) > MAX_PHOTO_BYTES:
        raise ValidationFailed("Photo exceeds the 15 MB limit")

    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[content_type]
    safe_name = f"capture{ext}"  # one photo per session; re-upload replaces
    directory = _session_dir(session.id)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / safe_name).write_bytes(content)

    await _update(
        session.id,
        {
            "state": "uploaded",
            "photo": CapturePhoto(
                filename=safe_name,
                content_type=content_type,
                size_bytes=len(content),
                uploaded_at=_now(),
            ).model_dump(),
        },
    )
    return await _get_by_token(token)


async def complete(token: str) -> CaptureSessionDocument:
    session = await _get_by_token(token)
    if session.state != "uploaded":
        raise Conflict("Upload a photo before completing capture")
    if not await measurements_col().find_one({"user_id": session.user_id}, {"_id": 1}):
        raise Conflict(
            "Submit measurements before completing capture", code="measurements_required"
        )
    job = await start_generation(session.user_id)  # the real Phase 4 call, no stub
    await _update(
        session.id,
        {"state": "completed", "avatar_job_id": job.id, "completed_at": _now()},
    )
    raw = await capture_sessions_col().find_one({"token": token})
    return CaptureSessionDocument.model_validate(raw)


# --- Shared ---------------------------------------------------------------


async def _update(session_id: str, fields: dict) -> None:
    fields["updated_at"] = _now()
    await capture_sessions_col().update_one({"_id": session_id}, {"$set": fields})


def photo_path(session: CaptureSessionDocument) -> Path:
    if not session.photo:
        raise NotFound("No photo uploaded for this session")
    path = _session_dir(session.id) / session.photo.filename
    if not path.exists():
        raise NotFound("Photo file missing from storage")
    return path


async def delete_all_for_user(user_id: str) -> None:
    """Cascade hook: rows AND photo files — retention ends at account
    deletion (backend-structure-plan.md invariant)."""
    async for raw in capture_sessions_col().find({"user_id": user_id}, {"_id": 1}):
        shutil.rmtree(_session_dir(raw["_id"]), ignore_errors=True)
    await capture_sessions_col().delete_many({"user_id": user_id})
