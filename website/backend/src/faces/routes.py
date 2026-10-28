"""Face routes — add a face to the avatar from 1-3 photos.

    POST   /faces                  multipart: front, [left, right]
    GET    /faces/latest           most recent capture (poll / restore)
    GET    /faces/current/glb      the current face mesh, for the avatar viewer
    GET    /faces/{id}             one capture
    DELETE /faces                  remove the face (and every stored face file)

The phone can add face photos through the QR link too:
POST/GET /photo-capture/{token}/face (photo_measurements/routes.py).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse

from ..core.auth_dependency import Identity, get_identity
from . import controller

router = APIRouter(prefix="/faces", tags=["faces"])

CurrentIdentity = Annotated[Identity, Depends(get_identity)]


async def read_face_photos(front: UploadFile, left: UploadFile | None, right: UploadFile | None) -> dict:
    photos = {"front": (front.content_type or "", await front.read())}
    for view, upload in (("left", left), ("right", right)):
        if upload is not None:
            photos[view] = (upload.content_type or "", await upload.read())
    return photos


@router.post("", status_code=201)
async def create_face(
    identity: CurrentIdentity,
    front: UploadFile = File(...),
    left: UploadFile | None = File(None),
    right: UploadFile | None = File(None),
):
    return await controller.create(identity.user_id, await read_face_photos(front, left, right))


@router.get("/latest")
async def latest_face(identity: CurrentIdentity):
    return await controller.latest(identity.user_id)


@router.get("/current/glb")
async def current_face_glb(identity: CurrentIdentity) -> FileResponse:
    return await controller.current_glb(identity.user_id)


@router.get("/{face_id}")
async def get_face(face_id: str, identity: CurrentIdentity):
    return await controller.get(face_id, identity.user_id)


@router.delete("")
async def delete_face(identity: CurrentIdentity):
    return await controller.delete(identity.user_id)
