"""HTTP ↔ domain translation for user measurements."""

from . import service
from .models import UserMeasurementsDocument
from .schemas import PatchUserMeasurementsRequest, SubmitUserMeasurementsRequest


def shape_measurements(doc: UserMeasurementsDocument) -> dict:
    shaped = doc.model_dump(exclude={"created_at", "updated_at"}, exclude_none=True)
    shaped["createdAt"] = doc.created_at.isoformat()
    shaped["updatedAt"] = doc.updated_at.isoformat()
    return shaped


async def get(user_id: str) -> dict:
    doc = await service.get_for_user(user_id)
    return {"measurements": shape_measurements(doc)}


async def submit(user_id: str, body: SubmitUserMeasurementsRequest) -> dict:
    fields = body.model_dump(exclude={"gender", "accuracy", "units_preference"})
    doc = await service.submit(user_id, body.gender, body.accuracy, body.units_preference, fields)
    return {"measurements": shape_measurements(doc)}


async def patch(user_id: str, body: PatchUserMeasurementsRequest) -> dict:
    doc = await service.patch(user_id, body.model_dump())
    return {"measurements": shape_measurements(doc)}
