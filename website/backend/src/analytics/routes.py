"""Analytics routes — event ingest. Anonymous callers allowed (events fire
before any session exists, e.g. page_view on the landing page)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..core.auth_dependency import Identity, get_optional_identity
from . import controller
from .models import IngestEventRequest

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/events")
async def ingest_event(
    body: IngestEventRequest,
    identity: Annotated[Identity | None, Depends(get_optional_identity)],
):
    return await controller.ingest(identity.user_id if identity else None, body)
