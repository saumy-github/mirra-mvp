"""User measurements request schemas — see models.py for UserMeasurementFields
and the stored document shape."""

from typing import Literal

from .models import UserMeasurementFields


class SubmitUserMeasurementsRequest(UserMeasurementFields):
    gender: Literal["male", "female"]
    accuracy: Literal["accurate", "approx"] = "accurate"
    units_preference: Literal["metric", "imperial"] = "metric"


class PatchUserMeasurementsRequest(UserMeasurementFields):
    gender: Literal["male", "female"] | None = None
    accuracy: Literal["accurate", "approx"] | None = None
    units_preference: Literal["metric", "imperial"] | None = None
