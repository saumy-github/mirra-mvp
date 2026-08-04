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

# Demo-mode staged timeline (seconds since render request).
DEMO_REQUESTED_SECONDS = 1
DEMO_RENDERING_SECONDS = 4


class TryonSessionDocument(BaseModel):
    """The `tryon_sessions` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)


class TryonRenderDocument(BaseModel):
    """The `tryon_renders` collection doc shape. `state` derives from
    elapsed time on read in demo mode until ready, then it's persisted and
    every later read is a cheap restore (the Hanger no-recompute path)."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    session_id: str
    user_id: str
    size_id: str
    garment_snapshot: SizeDocument  # catalog doc at request time
    avatar_profile_id: str
    engine_mode: str
    state: Literal["requested", "rendering", "ready", "failed"]
    failure_reason: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)