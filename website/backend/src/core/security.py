"""Password hashing, access-token (JWT) and refresh-token primitives.

Session model (backend-implementation-plan.md, Phase 0 item 1):
- access token: JWT, short-lived (~15 min), stateless — verified by
  signature only, carried in the Authorization: Bearer header
- refresh token: opaque random string, flat 30-day expiry, httpOnly cookie,
  stored hashed in the refresh_tokens collection with rotation families
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from ..config import get_settings
from .errors import Unauthorized

IDENTITY_KINDS = ("user", "guest")


def new_id(prefix: str) -> str:
    """Prefixed public id, e.g. u_9f2c41ab03d1e857 — used as the Mongo _id."""
    return f"{prefix}_{secrets.token_hex(8)}"


# --- Passwords ------------------------------------------------------------


def hash_password(plain: str) -> str:
    # bcrypt only reads the first 72 bytes; truncate explicitly so hash and
    # verify agree instead of relying on library behaviour.
    return bcrypt.hashpw(plain.encode("utf-8")[:72], bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("ascii"))
    except ValueError:
        return False


# --- Access tokens (JWT) --------------------------------------------------


def create_access_token(user_id: str, kind: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "kind": kind,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.access_token_secret, algorithm="HS256")


def decode_access_token(token: str) -> tuple[str, str]:
    """Return (user_id, kind) or raise Unauthorized."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.access_token_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Access token expired", code="token_expired")
    except jwt.InvalidTokenError:
        raise Unauthorized("Invalid access token")
    user_id = payload.get("sub")
    kind = payload.get("kind")
    if not user_id or kind not in IDENTITY_KINDS:
        raise Unauthorized("Invalid access token")
    return user_id, kind


# --- Refresh tokens -------------------------------------------------------


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def refresh_token_expiry() -> datetime:
    """Flat 30-day expiry from login — rotation reuses the family's original
    expiry, it does not slide (explicit product decision, may change later)."""
    settings = get_settings()
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
