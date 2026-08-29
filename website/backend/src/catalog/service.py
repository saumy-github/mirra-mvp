"""Catalog business logic — browse cloths, each carrying its sizes.

A product is a cloth and its variants are that cloth's sizes (doc 13,
Phase 3b). Sizes are shared: the same s_001 can belong to several cloths, so
a render request has to name both ids rather than deriving one from the other.
"""

import re

from ..core.errors import NotFound, ValidationFailed
from ..db import cloths_col, sizes_col
from .models import ClothDocument, SizeDocument, VALID_CATEGORIES, VALID_FIT_TYPES
from .schemas import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


async def _sizes_for(cloth: ClothDocument) -> list[SizeDocument]:
    """Resolve a cloth's size_ids into size documents, in id order."""
    if not cloth.size_ids:
        return []
    cursor = sizes_col().find({"size_id": {"$in": cloth.size_ids}}).sort("size_id", 1)
    raws = await cursor.to_list(length=len(cloth.size_ids))
    return [SizeDocument.model_validate(r) for r in raws]


async def list_cloths(
    *,
    category: str | None = None,
    q: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> tuple[list[tuple[ClothDocument, list[SizeDocument]]], int]:
    if category is not None and category not in VALID_CATEGORIES:
        raise ValidationFailed(f"category must be one of {sorted(VALID_CATEGORIES)}")
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = max(0, offset)

    query: dict = {}
    if category:
        query["category"] = category
    if q:
        # Case-insensitive substring match on the human-facing label.
        query["label"] = {"$regex": re.escape(q), "$options": "i"}

    total = await cloths_col().count_documents(query)
    cursor = cloths_col().find(query).sort("cloth_id", 1).skip(offset).limit(limit)
    raws = await cursor.to_list(length=limit)

    items = []
    for raw in raws:
        cloth = ClothDocument.model_validate(raw)
        items.append((cloth, await _sizes_for(cloth)))
    return items, total


async def get_cloth(cloth_id: str) -> tuple[ClothDocument, list[SizeDocument]]:
    raw = await cloths_col().find_one({"cloth_id": cloth_id})
    if not raw:
        raise NotFound("Garment not found")
    cloth = ClothDocument.model_validate(raw)
    return cloth, await _sizes_for(cloth)


async def get_size(size_id: str) -> SizeDocument:
    raw = await sizes_col().find_one({"size_id": size_id})
    if not raw:
        raise NotFound("Size not found")
    return SizeDocument.model_validate(raw)


async def resolve_pair(cloth_id: str, size_id: str) -> tuple[ClothDocument, SizeDocument]:
    """The (cloth, size) a render is for. 404s when the cloth is not offered
    in that size — the pairing is real data, not a formality."""
    cloth, sizes = await get_cloth(cloth_id)
    for size in sizes:
        if size.size_id == size_id:
            return cloth, size
    raise NotFound(f"{cloth_id} is not offered in {size_id}")


async def list_garments(
    *,
    fit_type: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> tuple[list[SizeDocument], int]:
    """Raw size listing. Kept for callers that browse the size chart itself
    rather than the product catalogue."""
    if fit_type is not None and fit_type not in VALID_FIT_TYPES:
        raise ValidationFailed(f"fit_type must be one of {sorted(VALID_FIT_TYPES)}")
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = max(0, offset)

    query: dict = {}
    if fit_type:
        query["fit_type"] = fit_type

    total = await sizes_col().count_documents(query)
    cursor = sizes_col().find(query).sort("size_id", 1).skip(offset).limit(limit)
    items = await cursor.to_list(length=limit)
    return [SizeDocument.model_validate(d) for d in items], total


async def get_garment(size_id: str) -> SizeDocument:
    """Backwards-compatible single-size lookup."""
    return await get_size(size_id)
