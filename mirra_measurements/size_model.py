"""Document helpers for the sizes collection - flat schema."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

VALID_FIT_TYPES = {"slim", "regular", "relaxed", "oversized"}

# 10 required flat measurement fields
SIZE_MEASUREMENT_FIELDS = (
    "half_chest_width_cm",
    "garment_length_cm",
    "shoulder_width_cm",
    "neck_width_cm",
    "neck_depth_front_cm",
    "neck_depth_back_cm",
    "sleeve_length_cm",
    "bicep_width_cm",
    "armhole_depth_cm",
    "seam_allowance_cm",
)

def create_size_doc(
    size_id: str,
    fit_type: str,
    half_chest_width_cm: float,
    garment_length_cm: float,
    shoulder_width_cm: float,
    neck_width_cm: float,
    neck_depth_front_cm: float,
    neck_depth_back_cm: float,
    sleeve_length_cm: float,
    bicep_width_cm: float,
    armhole_depth_cm: float,
    seam_allowance_cm: float,
) -> Dict[str, Any]:
    """Build a flat size document ready to upsert into MongoDB."""
    now = datetime.now(timezone.utc)
    doc = {
        "size_id":               size_id,
        "fit_type":              fit_type,
        "half_chest_width_cm":   half_chest_width_cm,
        "garment_length_cm":     garment_length_cm,
        "shoulder_width_cm":     shoulder_width_cm,
        "neck_width_cm":         neck_width_cm,
        "neck_depth_front_cm":   neck_depth_front_cm,
        "neck_depth_back_cm":    neck_depth_back_cm,
        "sleeve_length_cm":      sleeve_length_cm,
        "bicep_width_cm":        bicep_width_cm,
        "armhole_depth_cm":      armhole_depth_cm,
        "seam_allowance_cm":     seam_allowance_cm,
        "created_at":            now,
        "updated_at":            now,
    }
    return doc

def validate_size_doc(doc: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate a flat size document. Returns (True, None) or (False, reason)."""
    required = {"size_id", "fit_type", "created_at", "updated_at"} | set(SIZE_MEASUREMENT_FIELDS)

    missing = required - set(doc.keys())
    if missing:
        return False, f"Missing required fields: {sorted(missing)}"

    if not isinstance(doc["size_id"], str) or not doc["size_id"].strip():
        return False, "size_id must be a non-empty string"

    if doc["fit_type"] not in VALID_FIT_TYPES:
        return False, f"fit_type must be one of {sorted(VALID_FIT_TYPES)}, got '{doc['fit_type']}'"

    for field in SIZE_MEASUREMENT_FIELDS:
        value = doc[field]
        if not isinstance(value, (int, float)) or value < 0:
            return False, f"{field} must be a non-negative number"

    for field in ("created_at", "updated_at"):
        if not isinstance(doc[field], datetime):
            return False, f"{field} must be a datetime object"
        
    return True, None

# Legacy aliases kept while older helpers still exist in the repo.
GARMENT_MEASUREMENT_FIELDS = SIZE_MEASUREMENT_FIELDS
create_garment_doc = create_size_doc
validate_garment_doc = validate_size_doc
