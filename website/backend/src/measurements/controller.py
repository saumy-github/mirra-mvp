"""HTTP ↔ domain translation for measurements."""

from . import service
from .models import PatchMeasurementsRequest, SubmitMeasurementsRequest


def shape_measurements(doc: dict) -> dict:
    shaped = {k: v for k, v in doc.items() if k not in ("_id", "created_at", "updated_at")}
    shaped["createdAt"] = doc["created_at"].isoformat()
    shaped["updatedAt"] = doc["updated_at"].isoformat()
    return shaped


async def get(user_id: str) -> dict:
    doc = await service.get_for_user(user_id)
    return {"measurements": shape_measurements(doc)}


async def submit(user_id: str, body: SubmitMeasurementsRequest) -> dict:
    fields = body.model_dump(exclude={"gender", "accuracy"})
    doc = await service.submit(user_id, body.gender, body.accuracy, fields)
    return {"measurements": shape_measurements(doc)}


async def patch(user_id: str, body: PatchMeasurementsRequest) -> dict:
    doc = await service.patch(user_id, body.model_dump())
    return {"measurements": shape_measurements(doc)}
