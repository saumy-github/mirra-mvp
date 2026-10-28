"""HTTP ↔ domain translation for photo measurements."""

from ..user_measurements.controller import shape_measurements
from . import pairing, service
from .models import STAGE_LABELS, PhotoCaptureDocument, PhotoPairingDocument


def shape_capture(c: PhotoCaptureDocument) -> dict:
    return {
        "captureId": c.id,
        "state": c.state,
        "stageLabel": STAGE_LABELS.get(c.state, c.state),
        "heightCm": c.height_cm,
        "weightKg": c.weight_kg,
        "gender": c.gender,
        # Backend field names on purpose — the review step edits these and
        # sends them back unchanged as `overrides`.
        "profile": c.profile,
        "measurements": c.measurements,
        "warnings": c.warnings,
        "failureReason": c.failure_reason,
        "createdAt": c.created_at.isoformat(),
        "completedAt": c.completed_at.isoformat() if c.completed_at else None,
        "appliedAt": c.applied_at.isoformat() if c.applied_at else None,
    }


async def create(user_id: str, **kwargs) -> dict:
    capture = await service.create_capture(user_id, **kwargs)
    return {"capture": shape_capture(capture)}


async def get(capture_id: str, user_id: str) -> dict:
    return {"capture": shape_capture(await service.get_capture(capture_id, user_id))}


async def latest(user_id: str) -> dict:
    capture = await service.latest_capture(user_id)
    return {"capture": shape_capture(capture) if capture else None}


def shape_pairing(p: PhotoPairingDocument, token: str | None = None) -> dict:
    shaped = {
        "pairingId": p.id,
        "expiresAt": p.expires_at.isoformat(),
        "active": pairing.is_active(p),
        "captureId": p.capture_id,
        "buildAvatar": p.build_avatar,
        "measurementMethod": p.measurement_method,
        "phoneStage": p.phone_stage,
        "captureComplete": p.capture_complete_at is not None,
        "faceSkipped": p.face_skipped,
    }
    if token is not None:
        shaped["token"] = token  # only in the create response
    return shaped


async def create_pairing(user_id: str, build_avatar: bool = False, measurement_method: str = "photos") -> dict:
    p, token = await pairing.create_pairing(user_id, build_avatar, measurement_method)
    return {"pairing": shape_pairing(p, token)}


async def get_pairing(pairing_id: str, user_id: str) -> dict:
    p = await pairing.get_pairing(pairing_id, user_id)
    capture = await service.get_capture(p.capture_id, user_id) if p.capture_id else None
    return {"pairing": shape_pairing(p), "capture": shape_capture(capture) if capture else None}


def _public_capture(c: PhotoCaptureDocument) -> dict:
    """What the signed-out phone may see: progress only, never the numbers
    (those are reviewed on the signed-in screen)."""
    return {
        "captureId": c.id,
        "state": c.state,
        "stageLabel": STAGE_LABELS.get(c.state, c.state),
        "warnings": c.warnings,
        "failureReason": c.failure_reason,
    }


async def link_prefill(token: str) -> dict:
    return {"link": await pairing.link_prefill(token)}


async def create_via_link(token: str, **kwargs) -> dict:
    return {"capture": _public_capture(await pairing.create_capture_via_link(token, **kwargs))}


async def capture_via_link(token: str) -> dict:
    capture = await pairing.capture_via_link(token)
    return {"capture": _public_capture(capture) if capture else None}


def _public_face(c) -> dict:
    from ..faces.controller import shape_face

    shaped = shape_face(c)
    return {k: shaped[k] for k in ("faceId", "state", "stageLabel", "warnings", "failureReason")}


async def create_face_via_link(token: str, photos: dict) -> dict:
    return {"face": _public_face(await pairing.create_face_via_link(token, photos))}


async def face_via_link(token: str) -> dict:
    face = await pairing.face_via_link(token)
    return {"face": _public_face(face) if face else None}


async def apply(capture_id: str, user_id: str, body) -> dict:
    doc, capture = await service.apply_capture(capture_id, user_id, body.overrides)
    return {"measurements": shape_measurements(doc), "capture": shape_capture(capture)}
