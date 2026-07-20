"""Signature-look schemas.

signature_looks doc:
    _id (sl_…), user_id, name, is_default,
    items: [{size_id, render_id|None}]  (a saved outfit's layers),
    created_at, updated_at
"""

from pydantic import BaseModel, ConfigDict, Field


class LookItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    size_id: str = Field(alias="sizeId", min_length=1)
    render_id: str | None = Field(alias="renderId", default=None)


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
