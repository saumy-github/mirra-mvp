"""Analytics event's Mongo document shape — see schemas.py for the HTTP contract.

Never stored: photographs, tokens, passwords, precise body measurements —
property keys matching the forbidden pattern are dropped server-side even
if a client fails to sanitize (same regex as the frontend).
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

FORBIDDEN_PROPERTY_KEYS = re.compile(r"photo|password|token|secret|credential|measurement", re.I)


class AnalyticsEventDocument(BaseModel):
    """The `analytics_events` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    event: str
    user_id: str | None = None
    product_public_id: str | None = None
    variant_public_id: str | None = None
    session_id: str | None = None
    authenticated: bool = False
    engine_version: str | None = None
    app_version: str | None = None
    environment: str | None = None
    properties: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    occurred_at: str | None = None  # client clock, as sent
    received_at: datetime  # server clock

    def to_mongo(self) -> dict:
        return self.model_dump(by_alias=True)
