"""Capture-session document shape and state machine.

capture_sessions doc:
    _id (cs_…), user_id, token (one-time, unique — authenticates the phone),
    manual_code (short typable fallback, unique),
    state: created → paired → consented → uploaded → completed
           (terminal: completed | cancelled; expiry is checked on access),
    photo: {filename, content_type, size_bytes, uploaded_at} | None,
    avatar_job_id (set on complete), expires_at,
    created_at, updated_at, paired_at, completed_at

Photos are stored under UPLOADS_DIR/<session_id>/ and RETAINED after avatar
generation (deliberate divergence from the reference contract — Phase 0
item 2) so they can feed future avatar-accuracy work. They are removed only
by account deletion.

Upload validation: JPEG/PNG/WebP, ≤15 MB. The reference contract also
enforces minimum pixel dimensions (480×640); that needs image decoding
(Pillow) and is deferred until a real CV engine cares.
"""

from pydantic import BaseModel, Field

STATES = ("created", "paired", "consented", "uploaded", "completed", "cancelled")

SESSION_TTL_MINUTES = 10
MAX_PHOTO_BYTES = 15 * 1024 * 1024
ALLOWED_CONTENT_TYPES = ("image/jpeg", "image/png", "image/webp")

# Unambiguous alphabet for the typable pairing code (no 0/O, 1/I/L).
MANUAL_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
MANUAL_CODE_LENGTH = 6


class ResolveCodeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)
