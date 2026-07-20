"""Try-on document shapes, staged states and request schemas.

tryon_sessions doc:
    _id (tos_…), user_id, created_at

tryon_renders doc:
    _id (r_…), session_id, user_id, size_id,
    garment_snapshot (catalog doc at request time),
    avatar_profile_id, engine_mode,
    state ("requested"|"rendering"|"ready"|"failed") — demo mode derives it
    from elapsed time on read until ready, then it's persisted and every
    later read is a cheap restore (the Hanger no-recompute path),
    failure_reason, created_at, completed_at

No cart-handoff anywhere in this service — pilot cart is local-only
(backend-implementation-plan.md, Phase 6).
"""

from pydantic import BaseModel, ConfigDict, Field

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


class RequestRenderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    size_id: str = Field(alias="sizeId", min_length=1)
