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

# Taper fields, both FULL flat widths in cm. Optional: documents written before
# they existed are still valid, and product_ingestion.panel_generation_clo
# falls back to the same ratios when they are absent. Without them a straight-
# sided tee and a tapered one are indistinguishable in the schema.
SIZE_TAPER_FIELDS = (
    "hem_width_cm",
    "wrist_width_cm",
)

# CLO reference block ratios, kept byte-identical to the constants in
# product_ingestion/panel_generation_clo.py so the derived value here and the
# adapter's fallback agree exactly.
HEM_TO_CHEST_RATIO = 269.9999 / 290.0975      # 0.930697
WRIST_TO_BICEP_RATIO = 384.3506 / 490.2734    # 0.783952


def derive_hem_width_cm(half_chest_width_cm: float) -> float:
    """Hem width for a size with no measured hem, at the CLO reference taper."""
    return round(half_chest_width_cm * HEM_TO_CHEST_RATIO, 2)


def derive_wrist_width_cm(bicep_width_cm: float) -> float:
    """Wrist width for a size with no measured cuff, at the CLO reference taper.

    `bicep_width_cm` is the folded half-girth, so it doubles to the unfolded
    sleeve width before the ratio applies.
    """
    return round(bicep_width_cm * 2.0 * WRIST_TO_BICEP_RATIO, 2)


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
    hem_width_cm: Optional[float] = None,
    wrist_width_cm: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a flat size document ready to upsert into MongoDB.

    `hem_width_cm` and `wrist_width_cm` are full flat widths. Leave them out
    and the CLO reference ratios fill them in, which reproduces the untapered
    shape the older sizes were authored with.
    """
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
        "hem_width_cm":          (hem_width_cm if hem_width_cm is not None
                                  else derive_hem_width_cm(half_chest_width_cm)),
        "wrist_width_cm":        (wrist_width_cm if wrist_width_cm is not None
                                  else derive_wrist_width_cm(bicep_width_cm)),
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

    # Optional, but must be sane when supplied — an absent taper field falls
    # back to the reference ratio, a garbage one silently deforms the panel.
    for field in SIZE_TAPER_FIELDS:
        if field not in doc:
            continue
        value = doc[field]
        if not isinstance(value, (int, float)) or value <= 0:
            return False, f"{field} must be a positive number when present"

    for field in ("created_at", "updated_at"):
        if not isinstance(doc[field], datetime):
            return False, f"{field} must be a datetime object"
        
    return True, None

# Legacy aliases kept while older helpers still exist in the repo.
GARMENT_MEASUREMENT_FIELDS = SIZE_MEASUREMENT_FIELDS
create_garment_doc = create_size_doc
validate_garment_doc = validate_size_doc
