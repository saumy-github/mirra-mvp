"""Measurements request schemas — see models.py for MeasurementFields and the stored document shape."""

from typing import Literal

from .models import MeasurementFields


class SubmitMeasurementsRequest(MeasurementFields):
    gender: Literal["male", "female"]
    accuracy: Literal["accurate", "approx"] = "accurate"


class PatchMeasurementsRequest(MeasurementFields):
    gender: Literal["male", "female"] | None = None
    accuracy: Literal["accurate", "approx"] | None = None
