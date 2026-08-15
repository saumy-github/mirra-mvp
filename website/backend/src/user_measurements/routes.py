"""User measurements routes — submit, read back, partial update. The live
website path (dev and production) — see
.agent/website-launch/23-profile-measurements-form-and-user-measurements-model.md.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .schemas import PatchUserMeasurementsRequest, SubmitUserMeasurementsRequest

router = APIRouter(prefix="/user-measurements", tags=["user-measurements"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.get("/me")
async def get_user_measurements(identity: CurrentIdentity):
    return await controller.get(identity.user_id)


@router.put("/me")
async def submit_user_measurements(body: SubmitUserMeasurementsRequest, identity: CurrentIdentity):
    return await controller.submit(identity.user_id, body)


@router.patch("/me")
async def patch_user_measurements(body: PatchUserMeasurementsRequest, identity: CurrentIdentity):
    return await controller.patch(identity.user_id, body)
