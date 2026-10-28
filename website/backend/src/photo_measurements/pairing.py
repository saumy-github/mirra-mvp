"""QR hand-off: a signed-in desktop session lets a signed-out phone upload the
measurement photos into the same account.

    desktop  POST /photo-measurements/pairings        -> token (shown as a QR code)
    phone    GET  /photo-capture/{token}              -> pre-fill (height, gender, weight)
    phone    POST /photo-capture/{token}              -> photos -> photo_measurements capture
    phone    GET  /photo-capture/{token}/capture      -> progress on the phone
    desktop  GET  /photo-measurements/pairings/{id}   -> sees the capture, reviews it, applies

The token is the only credential the phone has, so it is random (192 bits),
stored hashed, short-lived, revoked when a newer one is issued, and capped at
a few uploads. It can create captures for its user and read those captures'
state — nothing else (applying still needs the signed-in desktop).
"""

import secrets
from datetime import datetime, timedelta, timezone

from ..core.errors import Conflict, Gone, NotFound, ValidationFailed
from ..core.security import hash_refresh_token, new_id
from ..db import photo_pairings_col
from ..user_measurements import service as user_measurements
from . import service
from ..faces import service as faces
from ..faces.models import FaceCaptureDocument
from .models import PhotoCaptureDocument, PhotoPairingDocument

PAIRING_TTL = timedelta(minutes=20)
MAX_UPLOADS_PER_PAIRING = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_pairing(user_id: str, build_avatar: bool = False, measurement_method: str = "photos") -> tuple[PhotoPairingDocument, str]:
    """Returns the pairing and the raw token (only ever available here)."""
    if measurement_method == "manual":
        await user_measurements.get_for_user(user_id)
    await photo_pairings_col().update_many(
        {"user_id": user_id, "revoked": False}, {"$set": {"revoked": True}}
    )
    token = secrets.token_urlsafe(24)
    now = _now()
    pairing = PhotoPairingDocument(
        id=new_id("pp"),
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        created_at=now,
        expires_at=now + PAIRING_TTL,
        build_avatar=build_avatar,
        measurement_method=measurement_method,
    )
    await photo_pairings_col().insert_one(pairing.to_mongo())
    return pairing, token


async def get_pairing(pairing_id: str, user_id: str) -> PhotoPairingDocument:
    raw = await photo_pairings_col().find_one({"_id": pairing_id, "user_id": user_id})
    if not raw:
        raise NotFound("Pairing not found")
    return PhotoPairingDocument.model_validate(raw)


def is_active(pairing: PhotoPairingDocument) -> bool:
    return not pairing.revoked and pairing.expires_at > _now()


async def _resolve_token(token: str) -> PhotoPairingDocument:
    raw = await photo_pairings_col().find_one({"token_hash": hash_refresh_token(token)})
    if not raw:
        raise NotFound("This link isn't valid. Scan the QR code on your computer again.")
    pairing = PhotoPairingDocument.model_validate(raw)
    if not is_active(pairing):
        raise Gone(
            "This link has expired. Refresh the QR code on your computer and scan it again.",
            code="pairing_expired",
        )
    return pairing


async def link_prefill(token: str) -> dict:
    """What the phone form can pre-fill from the account's saved measurements."""
    pairing = await _resolve_token(token)
    prefill: dict = {"expiresAt": pairing.expires_at.isoformat(),
        "buildAvatar": pairing.build_avatar, "measurementMethod": pairing.measurement_method, "captureId": pairing.capture_id,
        "faceId": pairing.face_capture_id, "complete": pairing.capture_complete_at is not None}
    try:
        saved = await user_measurements.get_for_user(pairing.user_id)
    except NotFound:
        return prefill
    prefill.update(gender=saved.gender, heightCm=saved.height_cm, weightKg=saved.weight_kg)
    return prefill


async def create_capture_via_link(token: str, **kwargs) -> PhotoCaptureDocument:
    pairing = await _resolve_token(token)
    if pairing.capture_complete_at:
        raise Conflict("These photos are already synced. Start a new capture to replace them.")
    if pairing.uploads >= MAX_UPLOADS_PER_PAIRING:
        raise ValidationFailed("Too many uploads on this link. Refresh the QR code on your computer.")
    capture = await service.create_capture(pairing.user_id, **kwargs)
    await photo_pairings_col().update_one(
        {"_id": pairing.id},
        {"$set": {"capture_id": capture.id, "uploads": pairing.uploads + 1}},
    )
    return capture


async def capture_via_link(token: str) -> PhotoCaptureDocument | None:
    pairing = await _resolve_token(token)
    if not pairing.capture_id:
        return None
    return await service.get_capture(pairing.capture_id, pairing.user_id)


async def create_face_via_link(token: str, photos: dict) -> FaceCaptureDocument:
    """The phone adds face photos on the same link (counts towards the same cap)."""
    pairing = await _resolve_token(token)
    if pairing.capture_complete_at:
        previous = await faces.get_capture(pairing.face_capture_id, pairing.user_id) if pairing.face_capture_id else None
        if pairing.reviewed_at or (previous and previous.state != "failed"):
            raise Conflict("These photos are already synced. Start a new capture to replace them.")
    if pairing.uploads >= MAX_UPLOADS_PER_PAIRING:
        raise ValidationFailed("Too many uploads on this link. Refresh the QR code on your computer.")
    capture = await faces.create_capture(pairing.user_id, photos)
    await photo_pairings_col().update_one(
        {"_id": pairing.id},
        {"$set": {"face_capture_id": capture.id, "uploads": pairing.uploads + 1, "face_skipped": False}},
    )
    return capture


async def face_via_link(token: str) -> FaceCaptureDocument | None:
    pairing = await _resolve_token(token)
    if not pairing.face_capture_id:
        return None
    return await faces.get_capture(pairing.face_capture_id, pairing.user_id)


async def delete_for_user(user_id: str) -> None:
    await photo_pairings_col().delete_many({"user_id": user_id})


async def phone_stage(token: str, stage: str) -> None:
    p = await _resolve_token(token)
    if not p.capture_complete_at:
        await photo_pairings_col().update_one({"_id": p.id}, {"$set": {"phone_stage": stage}})


async def refresh_link(pairing_id: str, user_id: str) -> tuple[PhotoPairingDocument, str]:
    p = await get_pairing(pairing_id, user_id)
    if p.revoked:
        raise Gone("This setup has been replaced by a newer one.")
    token = secrets.token_urlsafe(24)
    await photo_pairings_col().update_one({"_id": p.id}, {"$set": {
        "token_hash": hash_refresh_token(token), "expires_at": _now() + PAIRING_TTL,
    }})
    return await get_pairing(p.id, user_id), token
