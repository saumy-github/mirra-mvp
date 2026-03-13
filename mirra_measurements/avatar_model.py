"""
Data models and validation for measurement documents.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import re

VALID_GENDERS = {"male", "female"}
VALID_ACCURACIES = {"accurate", "approx"}

REQUIRED_FIELDS = {"user_id", "gender", "accuracy", "created_at", "updated_at"}

NUMERIC_FIELDS = {
    "height_cm",
    "weight_kg",
    "shoulder_width_cm",
    "waist_circumference_cm",
    "hip_circumference_cm",
    "leg_length_cm",
    "chest_circumference_cm",
    "bust_circumference_cm",
    "under_bust_circumference_cm",
}

STRING_FIELDS = {
    "body_shape_type",
    "skin_tone_hex",
}

HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def validate_measurement_doc(doc: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    missing_fields = REQUIRED_FIELDS - set(doc.keys())
    if missing_fields:
        return False, f"Missing required fields: {sorted(missing_fields)}"

    if not isinstance(doc["user_id"], str) or not doc["user_id"].strip():
        return False, "user_id must be a non-empty string"

    if doc["gender"] not in VALID_GENDERS:
        return False, f"gender must be one of {sorted(VALID_GENDERS)}, got '{doc['gender']}'"

    if doc["accuracy"] not in VALID_ACCURACIES:
        return False, f"accuracy must be one of {sorted(VALID_ACCURACIES)}, got '{doc['accuracy']}'"

    for field in ["created_at", "updated_at"]:
        if not isinstance(doc[field], datetime):
            return False, f"{field} must be a datetime object"

    for field in NUMERIC_FIELDS:
        if field in doc and doc[field] is not None:
            value = doc[field]
            if not isinstance(value, (int, float)):
                return False, f"{field} must be a number, got {type(value).__name__}"
            if value <= 0:
                return False, f"{field} must be greater than 0, got {value}"

    for field in STRING_FIELDS:
        if field in doc and doc[field] is not None:
            if not isinstance(doc[field], str):
                return False, f"{field} must be a string, got {type(doc[field]).__name__}"

    if "skin_tone_hex" in doc and doc["skin_tone_hex"] is not None:
        if not HEX_COLOR_RE.match(doc["skin_tone_hex"]):
            return False, "skin_tone_hex must be in format '#RRGGBB'"

    return True, None


def create_measurement_doc(
    user_id: str,
    gender: str,
    accuracy: str = "accurate",
    **measurements: Any,
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)

    doc = {
        "user_id": user_id,
        "gender": gender,
        "accuracy": accuracy,
        "created_at": now,
        "updated_at": now,
    }

    doc.update(measurements)
    return doc
