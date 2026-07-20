"""Catalog routes — public browsing of preset garments (no auth required,
matching the reference contract's public product endpoints)."""

from fastapi import APIRouter, Query

from . import controller
from .models import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/garments")
async def list_garments(
    fit_type: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
):
    return await controller.list_garments(fit_type, category, q, limit, offset)


@router.get("/garments/{size_id}")
async def get_garment(size_id: str):
    return await controller.get_garment(size_id)
