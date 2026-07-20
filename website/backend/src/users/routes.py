"""Users routes — profile, consents, account deletion."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .models import UpdateConsentsRequest, UpdateProfileRequest

router = APIRouter(prefix="/users", tags=["users"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.get("/me")
async def me(identity: CurrentIdentity):
    return await controller.me(identity.user_id)


@router.patch("/me")
async def update_profile(body: UpdateProfileRequest, identity: CurrentIdentity):
    return await controller.update_profile(identity.user_id, body)


@router.patch("/me/consents")
async def update_consents(body: UpdateConsentsRequest, identity: CurrentIdentity):
    return await controller.update_consents(identity.user_id, body)


@router.delete("/me")
async def delete_account(identity: CurrentIdentity):
    return await controller.delete_account(identity.user_id)
