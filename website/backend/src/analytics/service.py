"""Analytics business logic — event ingest.

The pilot's real goal is learning user behaviour, so this lands events
properly instead of fire-and-forgetting them (backend-structure-plan.md)."""

from datetime import datetime, timezone
from typing import Any

from ..core.security import new_id
from ..db import analytics_events_col
from .models import FORBIDDEN_PROPERTY_KEYS


def sanitize_properties(props: dict[str, Any] | None) -> dict[str, Any]:
    """Server-side enforcement of the frontend's sanitizeProperties — drop
    any key hinting at photos/credentials/body data."""
    if not props:
        return {}
    return {k: v for k, v in props.items() if not FORBIDDEN_PROPERTY_KEYS.search(k)}


async def ingest(user_id: str | None, data: dict[str, Any]) -> str:
    event_id = new_id("ev")
    await analytics_events_col().insert_one(
        {
            "_id": event_id,
            "event": data["event"],
            "user_id": user_id,
            "product_public_id": data.get("product_public_id"),
            "variant_public_id": data.get("variant_public_id"),
            "session_id": data.get("session_id"),
            "authenticated": bool(data.get("authenticated")),
            "engine_version": data.get("engine_version"),
            "app_version": data.get("app_version"),
            "environment": data.get("environment"),
            "properties": sanitize_properties(data.get("properties")),
            "occurred_at": data.get("occurred_at"),
            "received_at": datetime.now(timezone.utc),
        }
    )
    return event_id
