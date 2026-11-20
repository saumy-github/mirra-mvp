"""Avatars routes — start generation, staged status, profile get/delete."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import Response

from ..core.auth_dependency import Identity, get_identity
from . import controller

router = APIRouter(prefix="/avatars", tags=["avatars"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.post("/generate", status_code=201)
async def start_generation(identity: CurrentIdentity, force: bool = False):
    return await controller.start_generation(identity.user_id, force)


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, identity: CurrentIdentity):
    return await controller.get_job(job_id, identity.user_id)


@router.get("/profile")
async def get_profile(identity: CurrentIdentity):
    return await controller.get_profile(identity.user_id)


@router.get("/profile/glb")
async def get_profile_glb(identity: CurrentIdentity, if_none_match: str | None = Header(default=None)) -> Response:
    return await controller.get_profile_glb(identity.user_id, if_none_match)


@router.delete("/profile")
async def delete_profile(identity: CurrentIdentity):
    return await controller.delete_profile(identity.user_id)
