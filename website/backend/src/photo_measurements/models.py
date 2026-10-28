"""Photo-measurement capture document and staged states.

A capture is one front + side photo pair and the measurements computed from it.
The worker never writes `user_measurements` itself. The ordinary flow reviews
then applies; avatar onboarding applies a preview estimate while building,
then requires explicit review. Both use user_measurements.service, the same
path the manual form uses, so the avatar pipeline sees one document either way.

States are stages, never percentages (same contract as AvatarJob):

    queued -> processing -> ready -> applied
                         \\-> failed
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CAPTURE_STATES = ("queued", "processing", "ready", "failed", "applied")

STAGE_LABELS = {
    "queued": "Waiting in queue",
    "processing": "Measuring from your photos",
    "ready": "Your measurements are ready to review",
    "failed": "We couldn't measure these photos",
    "applied": "Saved to your profile",
}


class PhotoCaptureDocument(BaseModel):
    """The `photo_measurements` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    state: Literal["queued", "processing", "ready", "failed", "applied"]  # worker-written until ready
    # What the shopper told us; height is the scale of the whole measurement.
    height_cm: float
    weight_kg: float | None = None
    gender: Literal["male", "female"]
    shoe_sole_cm: float = 0.0
    # Relative to the upload root while the job is pending. The worker deletes
    # the files once it has measured them and clears these (photos are never
    # kept — only the numbers below are).
    front_path: str | None = None
    side_path: str | None = None
    # Backend field names, ready for user_measurements (height_cm, chest_..., skin_tone_hex).
    profile: dict | None = None
    # Every measurement the pipeline produced, for display; cm.
    measurements: dict | None = None
    warnings: list[str] = Field(default_factory=list)
    model: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    applied_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class PhotoPairingDocument(BaseModel):
    """The `photo_pairings` collection doc shape — the desktop → phone QR hand-off.

    The desktop (signed in) creates one and shows `/capture/<token>` as a QR
    code; the phone, which is *not* signed in, uploads its photos with that
    token alone. Only a hash of the token is stored. Short-lived and capped,
    because anyone holding the link can submit photos into this user's account.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime
    revoked: bool = False
    uploads: int = 0
    capture_id: str | None = None  # the most recent capture uploaded through this link
    face_capture_id: str | None = None  # the most recent face upload through this link
    # Avatar onboarding uses the same capture contract. Ordinary measurement
    # pairings remain opt-in and never generate an avatar automatically.
    build_avatar: bool = False
    measurement_method: Literal["photos", "manual"] = "photos"
    phone_stage: Literal["waiting", "capturing", "uploading", "complete"] = "waiting"
    capture_complete_at: datetime | None = None
    face_skipped: bool = False
    build_state: Literal["idle", "starting", "building", "failed"] = "idle"
    build_claimed_at: datetime | None = None
    avatar_job_id: str | None = None
    build_error: str | None = None
    review_requested_at: datetime | None = None
    review_overrides: dict[str, float] = Field(default_factory=dict)
    reviewed_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
