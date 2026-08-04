"""Signature-look Mongo document shape — see schemas.py for HTTP contracts,
which reuse LookItem below."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LookItem(BaseModel):
    """A saved outfit's layer. Shared by SignatureLookDocument (below) and the request schemas."""

    model_config = ConfigDict(populate_by_name=True)

    size_id: str = Field(alias="sizeId", min_length=1)
    render_id: str | None = Field(alias="renderId", default=None)


class SignatureLookDocument(BaseModel):
    """The `signature_looks` collection doc shape."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(alias="_id")
    user_id: str
    name: str
    is_default: bool
    items: list[LookItem]
    created_at: datetime
    updated_at: datetime

    def to_mongo(self) -> dict:
        # Not model_dump(by_alias=True): that would also alias nested
        # LookItem fields to camelCase, corrupting the stored item shape.
        data = self.model_dump(exclude={"id"})
        data["_id"] = self.id
        return data
