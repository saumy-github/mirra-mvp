"""Auth business logic. No FastAPI/HTTP imports (see backend-structure-plan.md)."""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from ..core.errors import Conflict, Unauthorized, ValidationFailed
from ..core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    new_id,
    refresh_token_expiry,
    verify_password,
)
from ..db import refresh_tokens_col, users_col

logger = logging.getLogger("mirra.backend.auth")

PASSWORD_RESET_TTL = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Token issuing / rotation --------------------------------------------


async def _issue_tokens(
    user_id: str,
    kind: str,
    *,
    family_id: str | None = None,
    expires_at: datetime | None = None,
) -> tuple[str, str, datetime]:
    """Create a refresh-token doc (+ its family on first issue) and an access
    token. Returns (access_token, raw_refresh_token, refresh_expires_at)."""
    raw = generate_refresh_token()
    expires_at = expires_at or refresh_token_expiry()
    await refresh_tokens_col().insert_one(
        {
            "_id": new_id("rt"),
            "token_hash": hash_refresh_token(raw),
            "user_id": user_id,
            "kind": kind,
            "family_id": family_id or new_id("rf"),
            "expires_at": expires_at,
            "created_at": _now(),
            "revoked_at": None,
            "replaced_by": None,
        }
    )
    return create_access_token(user_id, kind), raw, expires_at


async def _revoke_family(family_id: str) -> None:
    await refresh_tokens_col().update_many(
        {"family_id": family_id, "revoked_at": None},
        {"$set": {"revoked_at": _now()}},
    )


async def revoke_all_for_user(user_id: str) -> None:
    """Kill every session for a user — used by password reset and by the
    users service's account-deletion cascade."""
    await refresh_tokens_col().update_many(
        {"user_id": user_id, "revoked_at": None},
        {"$set": {"revoked_at": _now()}},
    )


async def delete_all_for_user(user_id: str) -> None:
    """Cascade hook: hard-delete this user's refresh tokens."""
    await refresh_tokens_col().delete_many({"user_id": user_id})


# --- Accounts -------------------------------------------------------------


async def sign_up(email: str, password: str, name: str | None) -> tuple[dict, str, str, datetime]:
    email = email.strip().lower()
    if await users_col().find_one({"email": email}, {"_id": 1}):
        raise Conflict("An account with this email already exists", code="account_exists")
    now = _now()
    verification_code = f"{secrets.randbelow(1_000_000):06d}"
    user: dict[str, Any] = {
        "_id": new_id("u"),
        "email": email,
        "name": name,
        "password_hash": hash_password(password),
        "is_guest": False,
        "email_verified": False,
        "verification_code": verification_code,
        "password_reset_hash": None,
        "password_reset_expires_at": None,
        "consents": {},
        "created_at": now,
        "updated_at": now,
    }
    await users_col().insert_one(user)
    # No email provider in the pilot — the code is logged server-side.
    logger.info("verification code for %s: %s", email, verification_code)
    access, raw_refresh, refresh_exp = await _issue_tokens(user["_id"], "user")
    return user, access, raw_refresh, refresh_exp


async def login(email: str, password: str) -> tuple[dict, str, str, datetime]:
    email = email.strip().lower()
    user = await users_col().find_one({"email": email})
    if not user or user.get("is_guest") or not verify_password(password, user.get("password_hash") or ""):
        raise Unauthorized("Invalid email or password", code="invalid_credentials")
    access, raw_refresh, refresh_exp = await _issue_tokens(user["_id"], "user")
    return user, access, raw_refresh, refresh_exp


async def create_guest() -> tuple[dict, str, str, datetime]:
    now = _now()
    user: dict[str, Any] = {
        "_id": new_id("g"),
        "name": None,
        "is_guest": True,
        "email_verified": False,
        "consents": {},
        "created_at": now,
        "updated_at": now,
    }
    await users_col().insert_one(user)
    access, raw_refresh, refresh_exp = await _issue_tokens(user["_id"], "guest")
    return user, access, raw_refresh, refresh_exp


async def get_account(user_id: str) -> dict:
    user = await users_col().find_one({"_id": user_id})
    if not user:
        raise Unauthorized("Account no longer exists")
    return user


# --- Refresh / logout -----------------------------------------------------


async def refresh(raw_token: str | None) -> tuple[dict, str, str, datetime]:
    """Rotate the refresh token: new token in the same family, same flat
    expiry. Reuse of an already-rotated token revokes the whole family."""
    if not raw_token:
        raise Unauthorized("Missing refresh token")
    doc = await refresh_tokens_col().find_one({"token_hash": hash_refresh_token(raw_token)})
    if not doc:
        raise Unauthorized("Unknown refresh token")
    if doc["revoked_at"] is not None or doc["replaced_by"] is not None:
        # Rotation-family reuse: treat as theft, kill every descendant.
        await _revoke_family(doc["family_id"])
        raise Unauthorized("Refresh token reuse detected", code="refresh_reuse")
    if doc["expires_at"] <= _now():
        raise Unauthorized("Refresh token expired", code="refresh_expired")

    user = await users_col().find_one({"_id": doc["user_id"]})
    if not user:
        await _revoke_family(doc["family_id"])
        raise Unauthorized("Account no longer exists")

    access, new_raw, refresh_exp = await _issue_tokens(
        doc["user_id"], doc["kind"], family_id=doc["family_id"], expires_at=doc["expires_at"]
    )
    await refresh_tokens_col().update_one(
        {"_id": doc["_id"]},
        {"$set": {"replaced_by": hash_refresh_token(new_raw), "revoked_at": _now()}},
    )
    return user, access, new_raw, refresh_exp


async def logout(raw_token: str | None) -> None:
    """Revoke the presented token's whole family. Idempotent."""
    if not raw_token:
        return
    doc = await refresh_tokens_col().find_one({"token_hash": hash_refresh_token(raw_token)})
    if doc:
        await _revoke_family(doc["family_id"])


# --- Email verification / password reset ---------------------------------


async def verify_email(user_id: str, code: str) -> dict:
    user = await get_account(user_id)
    if user.get("is_guest"):
        raise ValidationFailed("Guest sessions have no email to verify")
    if user.get("email_verified"):
        return user
    if not code or code != user.get("verification_code"):
        raise ValidationFailed("Incorrect verification code")
    await users_col().update_one(
        {"_id": user_id},
        {"$set": {"email_verified": True, "verification_code": None, "updated_at": _now()}},
    )
    return await get_account(user_id)


async def request_password_reset(email: str) -> None:
    """Never discloses whether the account exists (matches the reference
    contract). Reset token is logged — no email provider in the pilot."""
    email = email.strip().lower()
    user = await users_col().find_one({"email": email, "is_guest": False})
    if not user:
        return
    raw = secrets.token_urlsafe(32)
    await users_col().update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_reset_hash": hash_refresh_token(raw),
                "password_reset_expires_at": _now() + PASSWORD_RESET_TTL,
                "updated_at": _now(),
            }
        },
    )
    logger.info("password reset token for %s: %s", email, raw)


async def confirm_password_reset(token: str, new_password: str) -> None:
    user = await users_col().find_one(
        {
            "password_reset_hash": hash_refresh_token(token),
            "password_reset_expires_at": {"$gt": _now()},
        }
    )
    if not user:
        raise ValidationFailed("Invalid or expired reset token")
    await users_col().update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": hash_password(new_password),
                "password_reset_hash": None,
                "password_reset_expires_at": None,
                "updated_at": _now(),
            }
        },
    )
    # A password reset ends every existing session.
    await revoke_all_for_user(user["_id"])
