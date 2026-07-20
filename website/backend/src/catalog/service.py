"""Catalog business logic — browse/search the sizes collection."""

import re

from ..core.errors import NotFound, ValidationFailed
from ..db import sizes_col
from .models import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, VALID_FIT_TYPES


async def list_garments(
    *,
    fit_type: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> tuple[list[dict], int]:
    if fit_type is not None and fit_type not in VALID_FIT_TYPES:
        raise ValidationFailed(f"fit_type must be one of {sorted(VALID_FIT_TYPES)}")
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = max(0, offset)

    query: dict = {}
    if fit_type:
        query["fit_type"] = fit_type
    if category:
        query["category"] = category
    if q:
        # Case-insensitive substring match on the human-facing label.
        query["cloth_label"] = {"$regex": re.escape(q), "$options": "i"}

    total = await sizes_col().count_documents(query)
    cursor = sizes_col().find(query).sort("size_id", 1).skip(offset).limit(limit)
    items = await cursor.to_list(length=limit)
    return items, total


async def get_garment(size_id: str) -> dict:
    doc = await sizes_col().find_one({"size_id": size_id})
    if not doc:
        raise NotFound("Garment not found")
    return doc
