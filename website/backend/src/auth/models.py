"""Auth request/response schemas + the Mongo document shapes this service owns.

users doc (string _id doubles as the public user_id, e.g. "u_9f2c…" or
"g_9f2c…" for guests — measurements and every later collection key on it):
    _id, email (absent for guests), name, password_hash (absent for guests),
    is_guest, email_verified, verification_code,
    password_reset_hash, password_reset_expires_at,
    consents: dict, created_at, updated_at

refresh_tokens doc (one per issued token; rotation chains share family_id):
    _id, token_hash (sha256, unique), user_id, kind ("user"|"guest"),
    family_id, expires_at (flat — family's original 30-day expiry),
    created_at, revoked_at, replaced_by
"""

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class VerifyEmailRequest(BaseModel):
    code: str = Field(min_length=4, max_length=12)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
