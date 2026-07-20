"""HTTP ↔ domain translation for catalog."""

from . import service
from .models import SIZE_MEASUREMENT_FIELDS


def shape_garment(doc: dict) -> dict:
    return {
        "sizeId": doc["size_id"],
        "fitType": doc["fit_type"],
        "clothId": doc.get("cloth_id"),
        "clothLabel": doc.get("cloth_label"),
        "category": doc.get("category"),
        # Flat cm fields kept under their pipeline names — Step 2/Step 3
        # docs (half-girth convention) refer to them by these exact keys.
        "measurements": {f: doc.get(f) for f in SIZE_MEASUREMENT_FIELDS},
        "updatedAt": doc["updated_at"].isoformat() if doc.get("updated_at") else None,
    }


async def list_garments(fit_type, category, q, limit, offset) -> dict:
    items, total = await service.list_garments(
        fit_type=fit_type, category=category, q=q, limit=limit, offset=offset
    )
    return {
        "items": [shape_garment(d) for d in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_garment(size_id: str) -> dict:
    return {"garment": shape_garment(await service.get_garment(size_id))}
