"""Photo measurement routes — upload a front + side photo, poll, apply.

    POST /photo-measurements              multipart: front, side, height_cm, gender, [weight_kg, shoe_sole_cm]
    GET  /photo-measurements/latest       the caller's most recent capture (restore after reload)
    POST /photo-measurements/pairings     desktop: QR link for the phone (see pairing.py)
    GET  /photo-measurements/pairings/{id}  desktop: poll the phone's upload
    GET|POST /photo-capture/{token}[/capture]  phone, signed out: pre-fill, upload, progress
    GET  /photo-measurements/{id}         poll while queued/processing
    POST /photo-measurements/{id}/apply   save (with corrections) into user_measurements
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..core.auth_dependency import Identity, get_identity
from . import controller, pairing, setup
from .schemas import ApplyCaptureRequest, CaptureStageRequest, CreatePairingRequest, FinishCaptureRequest, RetrySetupRequest

router = APIRouter(prefix="/photo-measurements", tags=["photo-measurements"])
# Phone side of the QR hand-off: no sign-in, the token in the path is the credential.
public_router = APIRouter(prefix="/photo-capture", tags=["photo-measurements"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.post("", status_code=201)
async def create_capture(
    identity: CurrentIdentity,
    front: UploadFile = File(...),
    side: UploadFile = File(...),
    height_cm: float = Form(...),
    gender: Literal["male", "female"] = Form(...),
    weight_kg: float | None = Form(None),
    shoe_sole_cm: float = Form(0.0),
):
    return await controller.create(
        identity.user_id,
        height_cm=height_cm,
        weight_kg=weight_kg,
        gender=gender,
        shoe_sole_cm=shoe_sole_cm,
        front=(front.content_type or "", await front.read()),
        side=(side.content_type or "", await side.read()),
    )


@router.post("/pairings", status_code=201)
async def create_pairing(identity: CurrentIdentity, body: CreatePairingRequest = CreatePairingRequest()):
    """Desktop: a short-lived link for the phone (shown as a QR code)."""
    return await controller.create_pairing(identity.user_id, body.buildAvatar, body.measurementMethod)


@router.get("/setup/latest")
async def latest_setup(identity: CurrentIdentity):
    p = await setup.latest(identity.user_id)
    return {"setup": await setup.status(p.id, identity.user_id) if p else None}


@router.get("/setup/{pairing_id}")
async def setup_status(pairing_id: str, identity: CurrentIdentity):
    return {"setup": await setup.status(pairing_id, identity.user_id)}


@router.post("/setup/{pairing_id}/review")
async def review_setup(pairing_id: str, body: ApplyCaptureRequest, identity: CurrentIdentity):
    return {"setup": await setup.review(pairing_id, identity.user_id, body.overrides)}


@router.post("/setup/{pairing_id}/retry")
async def retry_setup(pairing_id: str, body: RetrySetupRequest, identity: CurrentIdentity):
    return {"setup": await setup.retry(pairing_id, identity.user_id, body.skipFace)}


@router.post("/pairings/{pairing_id}/link")
async def refresh_link(pairing_id: str, identity: CurrentIdentity):
    p, token = await pairing.refresh_link(pairing_id, identity.user_id)
    return {"pairing": controller.shape_pairing(p, token)}


@router.get("/pairings/{pairing_id}")
async def get_pairing(pairing_id: str, identity: CurrentIdentity):
    """Desktop poll: has the phone uploaded, and how far is the measurement?"""
    return await controller.get_pairing(pairing_id, identity.user_id)


@public_router.get("/{token}")
async def link_prefill(token: str):
    return await controller.link_prefill(token)


@public_router.post("/{token}/stage")
async def phone_stage(token: str, body: CaptureStageRequest):
    await pairing.phone_stage(token, body.stage)
    return {"ok": True}


@public_router.post("/{token}/finish")
async def finish_capture(token: str, body: FinishCaptureRequest):
    await setup.finish(token, body.skipFace)
    return {"ok": True}


@public_router.post("/{token}", status_code=201)
async def create_via_link(
    token: str,
    front: UploadFile = File(...),
    side: UploadFile = File(...),
    height_cm: float = Form(...),
    gender: Literal["male", "female"] = Form(...),
    weight_kg: float | None = Form(None),
    shoe_sole_cm: float = Form(0.0),
):
    return await controller.create_via_link(
        token,
        height_cm=height_cm,
        weight_kg=weight_kg,
        gender=gender,
        shoe_sole_cm=shoe_sole_cm,
        front=(front.content_type or "", await front.read()),
        side=(side.content_type or "", await side.read()),
    )


@public_router.post("/{token}/face", status_code=201)
async def create_face_via_link(
    token: str,
    front: UploadFile = File(...),
    left: UploadFile | None = File(None),
    right: UploadFile | None = File(None),
):
    from ..faces.routes import read_face_photos

    return await controller.create_face_via_link(token, await read_face_photos(front, left, right))


@public_router.get("/{token}/face")
async def face_via_link(token: str):
    return await controller.face_via_link(token)


@public_router.get("/{token}/capture")
async def capture_via_link(token: str):
    return await controller.capture_via_link(token)


@router.get("/latest")
async def latest_capture(identity: CurrentIdentity):
    return await controller.latest(identity.user_id)


@router.get("/{capture_id}")
async def get_capture(capture_id: str, identity: CurrentIdentity):
    return await controller.get(capture_id, identity.user_id)


@router.post("/{capture_id}/apply")
async def apply_capture(capture_id: str, body: ApplyCaptureRequest, identity: CurrentIdentity):
    return await controller.apply(capture_id, identity.user_id, body)
