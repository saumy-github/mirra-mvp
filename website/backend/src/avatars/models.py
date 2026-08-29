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

class AvatarJobDocument(BaseModel):
    """The `avatar_jobs` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    # Copy of the measurements doc at job creation, so a later measurements
    # edit can't change what an in-flight job builds from.
    measurement_snapshot: dict
    state: Literal["queued", "processing", "ready", "failed"]  # authoritative, written only by the worker
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
    # Set by worker.tasks.run_avatar_job after a pipeline run — the .avt path
    # the try-on worker task loads to drive clo_vto. Points at the versioned
    # <upload_root>/avatars/<user_id>/<version>/avatar.avt copy (see
    # worker/live_upload.py — <upload_root> is dev_upload/ or live_upload/
    # depending on the worker's APP_ENV), not the raw
    # clo_avatar_generation/output/ run. None before the first run.
    clo_avatar_avt_path: str | None = None
    # Web-facing GLB, relative to whichever upload root is configured (e.g.
    # "avatars/<user_id>/001/avatar.glb") — Step 6's serving route resolves
    # this against that root. None if the run's GLB export failed
    # (non-blocking, see step_12_export_glb.py) or hasn't run yet.
    avatar_glb_path: str | None = None
    # None for avatars predating this field; treated as "unknown", not stale.
    source_measurements_version: int | None = None
    generated_at: datetime | None = None
    # e.g. "u_001-004" — traces back to clo_avatar_generation/output/<run>/
    # for the full debug trail (run.log, step-by-step JSON) this doc doesn't
    # duplicate.
    clo_run_id: str | None = None
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
