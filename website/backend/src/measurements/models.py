"""Measurement schemas — ported from mirra_measurements/avatar_model.py.

The stored doc shape is byte-compatible with what the CLO pipeline
(clo_avatar_generation Step 1) already reads from the measurements
collection: user_id, gender, accuracy, created_at, updated_at + the
optional per-gender fields below, absent when not provided (never null).

Validation semantics preserved from validate_measurement_doc:
- gender ∈ {male, female}; accuracy ∈ {accurate, approx}
- every numeric measurement > 0
- skin_tone_hex matches #RRGGBB
The field set matches avatar_model.NUMERIC_FIELDS/STRING_FIELDS, which is a
superset of schema/step1_field_contract.json's v1 (male-only) fields —
female fields are stored now, consumed by the pipeline later.
"""

from typing import Literal

from pydantic import BaseModel, Field

HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"

# Ordered to match avatar_model.py for easy diffing.
NUMERIC_FIELDS = (
    "height_cm",
    "weight_kg",
    "shoulder_width_cm",
    "waist_circumference_cm",
    "hip_circumference_cm",
    "leg_length_cm",
    "chest_circumference_cm",
    "bust_circumference_cm",
    "under_bust_circumference_cm",
)

STRING_FIELDS = ("body_shape_type", "skin_tone_hex")


class MeasurementFields(BaseModel):
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


class SubmitMeasurementsRequest(MeasurementFields):
    gender: Literal["male", "female"]
    accuracy: Literal["accurate", "approx"] = "accurate"


class PatchMeasurementsRequest(MeasurementFields):
    gender: Literal["male", "female"] | None = None
    accuracy: Literal["accurate", "approx"] | None = None
