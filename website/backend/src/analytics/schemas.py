"""Analytics request schemas — event vocabulary mirrors AnalyticsEventName in
website/frontend/src/lib/analytics.ts; add events there and here together."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EVENT_NAMES = (
    "page_view",
    "signup_started",
    "signup_completed",
    "login_completed",
    "guest_started",
    "saved_avatar_selected",
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
