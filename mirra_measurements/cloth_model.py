"""Document helpers for the cloths collection.

A cloth is one garment product, matching one `product_ingestion/input/c_XXX/`
image folder. It names the sizes it is offered in; a size does not name a
cloth (doc 13, D1). That keeps the relationship many-to-many, so one brand's
cloths can share a size chart while another brand's cloths use entirely
different measurements.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

VALID_CATEGORIES = {"top", "bottom", "outerwear", "footwear", "accessory"}


def create_cloth_doc(
    cloth_id: str,
    label: str,
    size_ids: List[str],
    category: str = "top",
) -> Dict[str, Any]:
    """Build a cloth document ready to upsert into MongoDB."""
    now = datetime.now(timezone.utc)
    return {
        "cloth_id": cloth_id,
        "label": label,
        "category": category,
        "size_ids": list(size_ids),
        # Reserved for multi-brand: which company owns this cloth. Not used yet.
        "brand_id": None,
        "created_at": now,
        "updated_at": now,
    }


def validate_cloth_doc(
    doc: Dict[str, Any],
    known_size_ids: Optional[set] = None,
) -> Tuple[bool, Optional[str]]:
    """Validate a cloth document. Returns (True, None) or (False, reason).

    Pass `known_size_ids` to also check that every referenced size exists —
    the only referential check this model needs.
    """
    required = {"cloth_id", "label", "category", "size_ids", "created_at", "updated_at"}
    missing = required - set(doc.keys())
    if missing:
        return False, f"Missing required fields: {sorted(missing)}"

    if not isinstance(doc["cloth_id"], str) or not doc["cloth_id"].strip():
        return False, "cloth_id must be a non-empty string"

    if not isinstance(doc["label"], str) or not doc["label"].strip():
        return False, "label must be a non-empty string"

    if doc["category"] not in VALID_CATEGORIES:
        return False, f"category must be one of {sorted(VALID_CATEGORIES)}, got '{doc['category']}'"

    size_ids = doc["size_ids"]
    if not isinstance(size_ids, list) or not size_ids:
        return False, "size_ids must be a non-empty list"
    if not all(isinstance(s, str) and s.strip() for s in size_ids):
        return False, "every entry in size_ids must be a non-empty string"
    if len(set(size_ids)) != len(size_ids):
        return False, "size_ids contains duplicates"

    if known_size_ids is not None:
        unknown = sorted(set(size_ids) - known_size_ids)
        if unknown:
            return False, f"size_ids references sizes that do not exist: {unknown}"

    for field in ("created_at", "updated_at"):
        if not isinstance(doc[field], datetime):
            return False, f"{field} must be a datetime object"

    return True, None
