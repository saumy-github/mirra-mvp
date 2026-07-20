"""HTTP ↔ domain translation for analytics."""

from . import service


async def ingest(user_id: str | None, body) -> dict:
    await service.ingest(user_id, body.model_dump())
    return {"ok": True}
