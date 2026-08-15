"""User measurements' Mongo document shape — the live, website-facing
measurements store. See .agent/website-launch/23-profile-measurements-form-and-user-measurements-model.md.

Field set/validation mirrors website/backend/src/measurements/models.py
(the CLI/dev-only collection this replaces for the website) deliberately,
so the two stay easy to compare — but this is its own model, not a subclass
or an alias, per that plan doc's explicit instruction not to touch the old
one.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class UserMeasurementFields(BaseModel):
    """Shared by UserMeasurementsDocument (below) and the request schemas."""

    height_cm: float | None = Field(default=None, gt=0)
    weight_kg: float | None = Field(default=None, gt=0)
    shoulder_width_cm: float | None = Field(default=None, gt=0)
    waist_circumference_cm: float | None = Field(default=None, gt=0)
    hip_circumference_cm: float | None = Field(default=None, gt=0)
    leg_length_cm: float | None = Field(default=None, gt=0)
    chest_circumference_cm: float | None = Field(default=None, gt=0)
    bust_circumference_cm: float | None = Field(default=None, gt=0)
    under_bust_circumference_cm: float | None = Field(default=None, gt=0)
    body_shape_type: str | None = Field(default=None, max_length=40)
    skin_tone_hex: str | None = Field(default=None, pattern=HEX_COLOR_PATTERN)


class UserMeasurementsDocument(UserMeasurementFields):
    """The `user_measurements` collection doc shape — one per user (unique
    index on user_id, same convention as every other backend-owned
    collection)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    gender: Literal["male", "female"]
    accuracy: Literal["accurate", "approx"]
    units_preference: Literal["metric", "imperial"] = "metric"
    measurements_version: int = 1
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        """Unset optional fields are dropped, not stored as null."""
        return self.model_dump(by_alias=True, exclude_none=True)
