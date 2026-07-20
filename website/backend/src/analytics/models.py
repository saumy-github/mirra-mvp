"""Analytics schemas — the event vocabulary mirrors AnalyticsEventName in
website/frontend/src/lib/analytics.ts exactly. If an event is added there,
add it here too, or ingest will 422 (deliberately loud, not silent).

analytics_events doc:
    _id (ev_…), event, user_id|None, product_public_id, variant_public_id,
    session_id, authenticated, engine_version, app_version, environment,
    properties (sanitized), occurred_at (client clock), received_at (server)

Never stored: photographs, tokens, passwords, precise body measurements —
property keys matching the forbidden pattern are dropped server-side even
if a client fails to sanitize (same regex as the frontend).
"""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVENT_NAMES = (
    "page_view",
    "signup_started",
    "signup_completed",
    "login_completed",
    "guest_started",
    "saved_avatar_selected",
    "qr_session_created",
    "qr_scanned",
    "capture_consent_given",
    "capture_started",
    "capture_completed",
    "avatar_generation_started",
    "avatar_generation_completed",
    "avatar_generation_failed",
    "measurements_reviewed",
    "measurements_updated",
    "studio_opened",
    "product_selected",
    "variant_selected",
    "size_selected",
    "try_on_started",
    "try_on_completed",
    "try_on_failed",
    "hanger_item_restored",
    "signature_look_created",
    "signature_look_applied",
    "signature_look_removed",
    "add_to_cart_clicked",
    "session_abandoned",
)

FORBIDDEN_PROPERTY_KEYS = re.compile(r"photo|password|token|secret|credential|measurement", re.I)


class IngestEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event: Literal[EVENT_NAMES]  # type: ignore[valid-type]
    product_public_id: str | None = Field(alias="productPublicId", default=None)
    variant_public_id: str | None = Field(alias="variantPublicId", default=None)
    session_id: str | None = Field(alias="sessionId", default=None)
    authenticated: bool = False
    engine_version: str | None = Field(alias="engineVersion", default=None)
    app_version: str | None = Field(alias="appVersion", default=None)
    environment: str | None = None
    occurred_at: str | None = Field(alias="occurredAt", default=None)
    properties: dict[str, str | int | float | bool | None] | None = None
