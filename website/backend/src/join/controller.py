"""HTTP translation for early-access applications."""

from . import service
from .schemas import JoinApplicationRequest, JoinApplicationResponse


async def create(body: JoinApplicationRequest) -> JoinApplicationResponse:
    application_id, confirmation_sent = await service.create_application(body.model_dump())
    return JoinApplicationResponse(
        applicationId=application_id,
        confirmationEmailSent=confirmation_sent,
    )
