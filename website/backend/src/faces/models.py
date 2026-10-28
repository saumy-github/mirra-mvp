"""Face capture document: 1-3 face photos -> a textured face mesh (face.glb)
that the web viewer attaches to the shopper's avatar head.

    queued -> processing -> ready
                         \\-> failed

Photos live under <upload_root>/face_photos/ only until the worker has
reconstructed them; the result lives at <upload_root>/faces/<user>/<id>/face.glb
until it is replaced by a newer face or deleted.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FACE_VIEWS = ("front", "left", "right")

STAGE_LABELS = {
    "queued": "Waiting in queue",
    "processing": "Building your face",
    "ready": "Your face is on your avatar",
    "failed": "We couldn't build your face from these photos",
}


class FaceCaptureDocument(BaseModel):
    """The `face_captures` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    state: Literal["queued", "processing", "ready", "failed"]
    photo_paths: dict[str, str] = Field(default_factory=dict)   # view -> path relative to the upload root
    glb_path: str | None = None                                 # relative to the upload root, once ready
    views: list[str] = Field(default_factory=list)              # the views actually used
    skin_tone_hex: str | None = None
    warnings: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
