"""HTTP ↔ domain translation for users."""

from ..auth.controller import shape_account
from . import service


async def me(user_id: str) -> dict:
    user = await service.get_profile(user_id)
    return {"account": shape_account(user)}


async def update_profile(user_id: str, body) -> dict:
    user = await service.update_profile(user_id, name=body.name)
    return {"account": shape_account(user)}


async def update_consents(user_id: str, body) -> dict:
    user = await service.update_consents(user_id, body.consents)
    return {"account": shape_account(user)}


async def delete_account(user_id: str) -> dict:
    await service.delete_account(user_id)
    return {"ok": True}
