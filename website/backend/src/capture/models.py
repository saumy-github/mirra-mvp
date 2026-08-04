"""Capture-session Mongo document shape and state machine — see schemas.py for HTTP contracts.

Photos are stored under UPLOADS_DIR/<session_id>/ and RETAINED after avatar
generation (deliberate divergence from the reference contract — Phase 0
item 2) so they can feed future avatar-accuracy work. They are removed only
by account deletion.

Upload validation: JPEG/PNG/WebP, ≤15 MB. The reference contract also
enforces minimum pixel dimensions (480×640); that needs image decoding
(Pillow) and is deferred until a real CV engine cares.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

STATES = ("created", "paired", "consented", "uploaded", "completed", "cancelled")

SESSION_TTL_MINUTES = 10
MAX_PHOTO_BYTES = 15 * 1024 * 1024
ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp")

# Unambiguous alphabet for the typable pairing code (no 0/O, 1/I/L).
MANUAL_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
MANUAL_CODE_LENGTH = 6


class CapturePhoto(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime


class CaptureSessionDocument(BaseModel):
    """The `capture_sessions` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    token: str  # one-time, unique — authenticates the phone
    manual_code: str  # short typable fallback, unique
    state: str  # created -> paired -> consented -> uploaded -> completed (terminal: completed | cancelled)
    photo: CapturePhoto | None = None
    avatar_job_id: str | None = None  # set on complete
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
    paired_at: datetime | None = None
    completed_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
