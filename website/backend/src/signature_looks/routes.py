"""Signature-looks routes — CRUD for saved outfit combinations."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .models import CreateLookRequest, UpdateLookRequest

router = APIRouter(prefix="/signature-looks", tags=["signature_looks"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


@router.get("")
async def list_looks(identity: CurrentIdentity):
    return await controller.list_looks(identity.user_id)


@router.post("", status_code=201)
async def create_look(body: CreateLookRequest, identity: CurrentIdentity):
    return await controller.create_look(identity.user_id, body)


@router.patch("/{look_id}")
async def update_look(look_id: str, body: UpdateLookRequest, identity: CurrentIdentity):
    return await controller.update_look(look_id, identity.user_id, body)


@router.delete("/{look_id}")
async def delete_look(look_id: str, identity: CurrentIdentity):
    return await controller.delete_look(look_id, identity.user_id)
