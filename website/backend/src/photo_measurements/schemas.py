"""Photo-measurement request schemas. Upload is multipart (see routes.py); only
`apply` takes JSON."""

from typing import Literal

from pydantic import BaseModel, Field


class ApplyCaptureRequest(BaseModel):
    # user_measurements field name -> corrected value (cm / kg), from the review step.
    overrides: dict[str, float] = Field(default_factory=dict)


class CreatePairingRequest(BaseModel):
    buildAvatar: bool = False
    measurementMethod: Literal["photos", "manual"] = "photos"


class CaptureStageRequest(BaseModel):
    stage: Literal["capturing", "uploading"]


class FinishCaptureRequest(BaseModel):
    skipFace: bool = False


class RetrySetupRequest(BaseModel):
    skipFace: bool = False
