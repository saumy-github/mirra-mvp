"""Try-on request schemas — see models.py for the stored document shapes."""

from pydantic import BaseModel, ConfigDict, Field


class RequestRenderRequest(BaseModel):
    """Sizes are shared across cloths, so a render names both ids — one
    cannot be derived from the other (doc 13 section 47)."""

    model_config = ConfigDict(populate_by_name=True)

    cloth_id: str = Field(alias="clothId", min_length=1)
    size_id: str = Field(alias="sizeId", min_length=1)
