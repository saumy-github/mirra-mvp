"""Measurements routes — submit, read back, partial update."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .models import PatchMeasurementsRequest, SubmitMeasurementsRequest

router = APIRouter(prefix="/measurements", tags=["measurements"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.get("/me")
async def get_measurements(identity: CurrentIdentity):
    return await controller.get(identity.user_id)


@router.put("/me")
async def submit_measurements(body: SubmitMeasurementsRequest, identity: CurrentIdentity):
    return await controller.submit(identity.user_id, body)


@router.patch("/me")
async def patch_measurements(body: PatchMeasurementsRequest, identity: CurrentIdentity):
    return await controller.patch(identity.user_id, body)
