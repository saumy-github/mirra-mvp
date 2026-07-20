"""Capture routes.

Desktop endpoints authenticate the signed-in user; /by-token/* endpoints
authenticate by the one-time token itself — the paired phone has no JWT
(same split as the reference openapi.yaml)."""

from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .models import ResolveCodeRequest

router = APIRouter(prefix="/capture-sessions", tags=["capture"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.post("", status_code=201)
async def create_session(identity: CurrentIdentity):
    return await controller.create_session(identity.user_id)


@router.post("/resolve-code")
async def resolve_code(body: ResolveCodeRequest):
    return await controller.resolve_code(body)


@router.get("/{session_id}")
async def get_session(session_id: str, identity: CurrentIdentity):
    return await controller.get_session(session_id, identity.user_id)


@router.post("/{session_id}/cancel")
async def cancel_session(session_id: str, identity: CurrentIdentity):
    return await controller.cancel_session(session_id, identity.user_id)


@router.get("/{session_id}/photo")
async def get_photo(session_id: str, identity: CurrentIdentity):
    return await controller.get_photo(session_id, identity.user_id)


@router.get("/by-token/{token}")
async def get_by_token(token: str):
    return await controller.get_by_token(token)


@router.post("/by-token/{token}/pair")
async def pair(token: str):
    return await controller.pair(token)


@router.post("/by-token/{token}/consent")
async def give_consent(token: str):
    return await controller.give_consent(token)


@router.post("/by-token/{token}/uploads")
async def upload_photo(token: str, file: UploadFile):
    content = await file.read()
    return await controller.upload_photo(
        token, file.filename or "capture", file.content_type or "", content
    )


@router.post("/by-token/{token}/complete")
async def complete(token: str):
    return await controller.complete(token)
