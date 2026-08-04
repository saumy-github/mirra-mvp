"""Capture request schemas — see models.py for the stored document shape."""

from pydantic import BaseModel, Field


class ResolveCodeRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)
