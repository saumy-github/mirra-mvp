"""Auth's Mongo document shapes (DB schema) — see schemas.py for HTTP contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# refresh_tokens doc is still a plain dict built in service.py, not modeled here yet.


class UserDocument(BaseModel):
    """The `users` collection doc shape — single source of truth, used instead of raw dicts."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")  # doubles as public user_id, e.g. "u_..." / "g_..." for guests
    email: str | None = None
    name: str | None = None
    password_hash: str | None = None
    is_guest: bool = False
    email_verified: bool = False
    verification_code: str | None = None
    password_reset_hash: str | None = None
    password_reset_expires_at: datetime | None = None
    consents: dict[str, bool] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        """Insert-ready dict; unset fields (e.g. email for a guest) are dropped, not stored as null."""
        return self.model_dump(by_alias=True, exclude_none=True)
