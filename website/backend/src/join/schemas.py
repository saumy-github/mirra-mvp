"""Public request schema for the Mirra early-access form."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class JoinApplicationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    company: str = Field(min_length=2, max_length=120)
    website: str | None = Field(default=None, max_length=2048)
    role: Literal["founder", "ecommerce", "product", "engineering", "other"]
    monthly_orders: Literal["under-1k", "1k-10k", "10k-50k", "50k-plus"] | None = Field(
        alias="monthlyOrders",
        default=None,
    )
    goals: str = Field(min_length=10, max_length=2000)

    @field_validator("name", "company", "website", "goals", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class JoinApplicationResponse(BaseModel):
    ok: Literal[True] = True
    applicationId: str
    confirmationEmailSent: bool
