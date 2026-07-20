"""HTTP ↔ domain translation for signature looks."""

from . import service


def shape_look(look: dict) -> dict:
    return {
        "lookId": look["_id"],
        "name": look["name"],
        "isDefault": look["is_default"],
        "items": [
            {"sizeId": item["size_id"], "renderId": item.get("render_id")} for item in look["items"]
        ],
        "createdAt": look["created_at"].isoformat(),
        "updatedAt": look["updated_at"].isoformat(),
    }


async def list_looks(user_id: str) -> dict:
    return {"items": [shape_look(l) for l in await service.list_looks(user_id)]}


async def create_look(user_id: str, body) -> dict:
    look = await service.create_look(
        user_id, body.name, [i.model_dump() for i in body.items], body.is_default
    )
    return {"look": shape_look(look)}


async def update_look(look_id: str, user_id: str, body) -> dict:
    look = await service.update_look(
        look_id,
        user_id,
        name=body.name,
        items=[i.model_dump() for i in body.items] if body.items is not None else None,
        is_default=body.is_default,
    )
    return {"look": shape_look(look)}


async def delete_look(look_id: str, user_id: str) -> dict:
    await service.delete_look(look_id, user_id)
    return {"ok": True}
