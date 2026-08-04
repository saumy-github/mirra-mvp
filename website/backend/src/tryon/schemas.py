"""Try-on request schemas — see models.py for the stored document shapes."""

from pydantic import BaseModel, ConfigDict, Field


class RequestRenderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    size_id: str = Field(alias="sizeId", min_length=1)
