"""Signature-looks request schemas — see models.py for LookItem and the stored document shape."""

from pydantic import BaseModel, ConfigDict, Field

from .models import LookItem


class CreateLookRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=80)
    items: list[LookItem] = Field(min_length=1, max_length=10)
    is_default: bool = Field(alias="isDefault", default=False)


class UpdateLookRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=80)
    items: list[LookItem] | None = Field(default=None, min_length=1, max_length=10)
    is_default: bool | None = Field(alias="isDefault", default=None)
