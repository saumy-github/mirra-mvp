"""Persistence shape for an early-access application."""

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class JoinApplicationDocument:
    id: str
    name: str
    email: str
    company: str
    website: str | None
    role: str
    monthly_orders: str | None
    goals: str
    created_at: datetime
    confirmation_email_sent: bool = False

    def to_mongo(self) -> dict:
        data = asdict(self)
        data["_id"] = data.pop("id")
        return data
