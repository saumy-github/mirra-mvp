"""Users request schemas. The users Mongo doc shape is owned by the auth
service (src/auth/models.py) — this service reads and mutates it."""

from pydantic import BaseModel, Field


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)


class UpdateConsentsRequest(BaseModel):
    consents: dict[str, bool]
