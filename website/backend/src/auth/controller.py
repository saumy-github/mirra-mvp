"""HTTP ↔ domain translation for auth: cookies, response shaping."""

from datetime import datetime, timezone

from fastapi import Response

from ..config import get_settings
from . import service

REFRESH_COOKIE = "mirra_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"  # only ever sent to auth endpoints


def shape_account(user: dict) -> dict:
    return {
        "userId": user["_id"],
        "email": user.get("email"),
        "name": user.get("name"),
        "isGuest": bool(user.get("is_guest")),
        "emailVerified": bool(user.get("email_verified")),
        "consents": user.get("consents") or {},
        "createdAt": user["created_at"].isoformat(),
    }


def _session_payload(user: dict, access_token: str) -> dict:
    settings = get_settings()
    return {
        "account": shape_account(user),
        "accessToken": access_token,
        "tokenType": "bearer",
        "expiresInSeconds": settings.access_token_expire_minutes * 60,
    }


def _set_refresh_cookie(response: Response, raw: str, expires_at: datetime) -> None:
    settings = get_settings()
    max_age = max(0, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=max_age,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


async def sign_up(body, response: Response) -> dict:
    user, access, raw_refresh, refresh_exp = await service.sign_up(body.email, body.password, body.name)
    _set_refresh_cookie(response, raw_refresh, refresh_exp)
    return _session_payload(user, access)


async def login(body, response: Response) -> dict:
    user, access, raw_refresh, refresh_exp = await service.login(body.email, body.password)
    _set_refresh_cookie(response, raw_refresh, refresh_exp)
    return _session_payload(user, access)


async def create_guest(response: Response) -> dict:
    user, access, raw_refresh, refresh_exp = await service.create_guest()
    _set_refresh_cookie(response, raw_refresh, refresh_exp)
    return _session_payload(user, access)


async def refresh(raw_cookie: str | None, response: Response) -> dict:
    user, access, new_raw, refresh_exp = await service.refresh(raw_cookie)
    _set_refresh_cookie(response, new_raw, refresh_exp)
    return _session_payload(user, access)


async def logout(raw_cookie: str | None, response: Response) -> dict:
    await service.logout(raw_cookie)
    _clear_refresh_cookie(response)
    return {"ok": True}


async def me(user_id: str) -> dict:
    user = await service.get_account(user_id)
    return {"account": shape_account(user)}


async def verify_email(user_id: str, body) -> dict:
    user = await service.verify_email(user_id, body.code)
    return {"account": shape_account(user)}


async def request_password_reset(body) -> dict:
    await service.request_password_reset(body.email)
    return {"ok": True}


async def confirm_password_reset(body) -> dict:
    await service.confirm_password_reset(body.token, body.new_password)
    return {"ok": True}
