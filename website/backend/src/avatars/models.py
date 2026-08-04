"""Avatar job/profile Mongo document shapes and staged states. No request
schemas exist for this module — every endpoint takes no body.

States are stages, never percentages (reference contract: AvatarJob).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

JOB_STATES = ("queued", "processing", "ready", "failed")

STAGE_LABELS = {
    "queued": "Waiting in queue",
    "processing": "Sculpting your digital twin",
    "ready": "Your avatar is ready",
    "failed": "Avatar generation failed",
}

# Demo-mode staged timeline (seconds since job creation).
DEMO_QUEUE_SECONDS = 2
DEMO_PROCESSING_SECONDS = 6


class AvatarJobDocument(BaseModel):
    """The `avatar_jobs` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    engine_mode: Literal["demo", "live"]
    # Copy of the measurements doc at job creation, so a later measurements
    # edit can't change what an in-flight job builds from.
    measurement_snapshot: dict
    state: Literal["queued", "processing", "ready", "failed"]  # authoritative in live mode only
    failure_reason: str | None = None
    avatar_profile_id: str | None = None  # set when ready
    created_at: datetime
    completed_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class AvatarProfileDocument(BaseModel):
    """The `avatar_profiles` collection doc shape — one per user (unique index on user_id)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    source_job_id: str
    gender: str | None = None
    measurements: dict
    body_shape_type: str | None = None
    skin_tone_hex: str | None = None
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
