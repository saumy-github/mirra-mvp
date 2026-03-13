"""Document helpers for the garments collection — flat schema."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


VALID_FIT_TYPES = {"slim", "regular", "relaxed", "oversized"}

# 10 required flat measurement fields
GARMENT_MEASUREMENT_FIELDS = (
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


def create_garment_doc(
    garment_id: str,
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
    """Build a flat garments document ready to upsert into MongoDB."""
    now = datetime.now(timezone.utc)
    return {
        "garment_id":           garment_id,
        "fit_type":             fit_type,
        "half_chest_width_cm":  half_chest_width_cm,
        "garment_length_cm":    garment_length_cm,
        "shoulder_width_cm":    shoulder_width_cm,
        "neck_width_cm":        neck_width_cm,
        "neck_depth_front_cm":  neck_depth_front_cm,
        "neck_depth_back_cm":   neck_depth_back_cm,
        "sleeve_length_cm":     sleeve_length_cm,
        "bicep_width_cm":       bicep_width_cm,
        "armhole_depth_cm":     armhole_depth_cm,
        "seam_allowance_cm":    seam_allowance_cm,
        "created_at":           now,
        "updated_at":           now,
    }


def validate_garment_doc(doc: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate a flat garment document. Returns (True, None) or (False, reason)."""
    required = {"garment_id", "fit_type", "created_at", "updated_at"} | set(GARMENT_MEASUREMENT_FIELDS)

    missing = required - set(doc.keys())
    if missing:
        return False, f"Missing required fields: {sorted(missing)}"

    if not isinstance(doc["garment_id"], str) or not doc["garment_id"].strip():
        return False, "garment_id must be a non-empty string"

    if doc["fit_type"] not in VALID_FIT_TYPES:
        return False, f"fit_type must be one of {sorted(VALID_FIT_TYPES)}, got '{doc['fit_type']}'"

    for field in GARMENT_MEASUREMENT_FIELDS:
        val = doc[field]
        if not isinstance(val, (int, float)) or val < 0:
            return False, f"{field} must be a non-negative number"

    for field in ("created_at", "updated_at"):
        if not isinstance(doc[field], datetime):
            return False, f"{field} must be a datetime object"

    return True, None
