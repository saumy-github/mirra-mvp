"""Public early-access application endpoint."""

from fastapi import APIRouter

from . import controller
from .schemas import JoinApplicationRequest, JoinApplicationResponse

router = APIRouter(prefix="/join", tags=["join"])


@router.post("", status_code=201, response_model=JoinApplicationResponse)
async def create_application(body: JoinApplicationRequest):
    return await controller.create(body)
