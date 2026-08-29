"""Try-on Mongo document shapes and staged states — see schemas.py for HTTP contracts.

No cart-handoff anywhere in this service — pilot cart is local-only
(backend-implementation-plan.md, Phase 6).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..catalog.models import SizeDocument

RENDER_STATES = ("requested", "rendering", "ready", "failed")

STAGE_LABELS = {
    "requested": "Preparing your fitting room",
    "rendering": "Draping the garment",
    "ready": "Your try-on is ready",
    "failed": "Try-on failed",
}

class TryonSessionDocument(BaseModel):
    """The `tryon_sessions` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class TryonRenderDocument(BaseModel):
    """The `tryon_renders` collection doc shape. `state` is authoritative,
    written only by the worker; once ready every later read is a cheap
    restore (the Hanger no-recompute path)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    session_id: str
    user_id: str
    # Empty on renders created before cloth and size were both recorded.
    # Those predate real garment wiring and can only be re-requested, so the
    # worker refuses them rather than guessing a cloth.
    cloth_id: str = ""
    size_id: str
    garment_snapshot: SizeDocument  # catalog doc at request time
    avatar_profile_id: str
    state: Literal["requested", "rendering", "ready", "failed"]
    failure_reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    # Relative to the upload root, set by the worker once the render lands.
    render_glb_path: str | None = None
    clo_run_id: str | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)