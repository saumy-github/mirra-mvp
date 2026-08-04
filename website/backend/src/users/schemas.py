"""Users request schemas — the `users` document itself is owned by auth/models.py."""

from pydantic import BaseModel, Field


class UpdateProfileRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)


class UpdateConsentsRequest(BaseModel):
    consents: dict[str, bool]
