"""HTTP ↔ domain translation for catalog."""

from . import service
from .models import SIZE_MEASUREMENT_FIELDS, ClothDocument, SizeDocument


def shape_garment(doc: SizeDocument) -> dict:
    return {
        "sizeId": doc.size_id,
        "fitType": doc.fit_type,
        "clothId": doc.cloth_id,
        "clothLabel": doc.cloth_label,
        "category": doc.category,
        # Flat cm fields kept under their pipeline names — Step 2/Step 3
        # docs (half-girth convention) refer to them by these exact keys.
        "measurements": {f: getattr(doc, f) for f in SIZE_MEASUREMENT_FIELDS},
        "updatedAt": doc.updated_at.isoformat() if doc.updated_at else None,
    }


def shape_cloth(cloth: ClothDocument, sizes: list[SizeDocument]) -> dict:
    """A product: the cloth, with its sizes as variants."""
    return {
        "clothId": cloth.cloth_id,
        "label": cloth.label,
        "category": cloth.category,
        "sizes": [shape_garment(s) for s in sizes],
        "updatedAt": cloth.updated_at.isoformat() if cloth.updated_at else None,
    }


async def list_garments(fit_type, category, q, limit, offset) -> dict:
    items, total = await service.list_cloths(category=category, q=q, limit=limit, offset=offset)
    return {
        "items": [shape_cloth(cloth, sizes) for cloth, sizes in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def get_garment(cloth_id: str) -> dict:
    cloth, sizes = await service.get_cloth(cloth_id)
    return {"garment": shape_cloth(cloth, sizes)}
