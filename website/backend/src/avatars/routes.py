"""Avatars routes — start generation, staged status, profile get/delete."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..core.auth_dependency import Identity, get_identity
from . import controller

router = APIRouter(prefix="/avatars", tags=["avatars"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.post("/generate", status_code=201)
async def start_generation(identity: CurrentIdentity):
    return await controller.start_generation(identity.user_id)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, identity: CurrentIdentity):
    return await controller.get_job(job_id, identity.user_id)


@router.get("/profile")
async def get_profile(identity: CurrentIdentity):
    return await controller.get_profile(identity.user_id)


@router.delete("/profile")
async def delete_profile(identity: CurrentIdentity):
    return await controller.delete_profile(identity.user_id)
