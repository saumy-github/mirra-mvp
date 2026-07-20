"""Try-on routes — session, render request, poll/restore, history."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .models import RequestRenderRequest

router = APIRouter(prefix="/tryon", tags=["tryon"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.post("/sessions", status_code=201)
async def create_session(identity: CurrentIdentity):
    return await controller.create_session(identity.user_id)


@router.post("/sessions/{session_id}/renders", status_code=201)
async def request_render(session_id: str, body: RequestRenderRequest, identity: CurrentIdentity):
    return await controller.request_render(session_id, identity.user_id, body)


@router.get("/sessions/{session_id}/renders/{render_id}")
async def get_render(session_id: str, render_id: str, identity: CurrentIdentity):
    return await controller.get_render(session_id, render_id, identity.user_id)


@router.get("/history")
async def history(identity: CurrentIdentity, limit: int = Query(default=20, ge=1, le=50)):
    return await controller.history(identity.user_id, limit)
