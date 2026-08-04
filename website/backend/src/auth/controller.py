"""HTTP ↔ domain translation for auth: cookies, response shaping."""

import logging
import re
import secrets
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import Response
from fastapi.responses import RedirectResponse

from ..config import get_settings
from ..core.errors import DomainError
from . import google_oauth, service
from .models import UserDocument

logger = logging.getLogger("mirra.backend.auth")

REFRESH_COOKIE = "mirra_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"  # only ever sent to auth endpoints

GOOGLE_STATE_COOKIE = "mirra_oauth_state"
GOOGLE_NEXT_COOKIE = "mirra_oauth_next"
GOOGLE_OAUTH_COOKIE_PATH = "/api/v1/auth/google"
GOOGLE_OAUTH_COOKIE_MAX_AGE = 300  # 5 minutes — covers the Google consent round trip
_SAFE_NEXT_RE = re.compile(r"^/(?!/)")


def shape_account(user: UserDocument) -> dict:
    return {
        "userId": user.id,
        "email": user.email,
        "name": user.name,
        "isGuest": user.is_guest,
        "emailVerified": user.email_verified,
        "consents": user.consents,
        "createdAt": user.created_at.isoformat(),
    }


def _session_payload(user: UserDocument, access_token: str) -> dict:
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


def _safe_next(next_param: str | None) -> str | None:
    """Same allow-only-relative-path rule as the frontend's postAuthDestination — no open redirects."""
    if next_param and _SAFE_NEXT_RE.match(next_param):
        return next_param
    return None


async def google_start(next_param: str | None) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    redirect = RedirectResponse(google_oauth.build_authorize_url(state), status_code=302)
    settings = get_settings()
    redirect.set_cookie(
        GOOGLE_STATE_COOKIE,
        state,
        max_age=GOOGLE_OAUTH_COOKIE_MAX_AGE,
        path=GOOGLE_OAUTH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
    safe_next = _safe_next(next_param)
    if safe_next:
        redirect.set_cookie(
            GOOGLE_NEXT_COOKIE,
            safe_next,
            max_age=GOOGLE_OAUTH_COOKIE_MAX_AGE,
            path=GOOGLE_OAUTH_COOKIE_PATH,
            httponly=True,
            secure=settings.cookie_secure,
            samesite="lax",
        )
    return redirect


async def google_callback(
    code: str | None,
    state: str | None,
    error: str | None,
    state_cookie: str | None,
    next_cookie: str | None,
) -> RedirectResponse:
    settings = get_settings()

    def failure(reason: str) -> RedirectResponse:
        redirect = RedirectResponse(f"{settings.frontend_auth_failure_url}?error={reason}", status_code=302)
        redirect.delete_cookie(GOOGLE_STATE_COOKIE, path=GOOGLE_OAUTH_COOKIE_PATH)
        redirect.delete_cookie(GOOGLE_NEXT_COOKIE, path=GOOGLE_OAUTH_COOKIE_PATH)
        return redirect

    if error:
        return failure("google_denied")
    if not code or not state or not state_cookie or state != state_cookie:
        return failure("google_state_mismatch")

    try:
        tokens = await google_oauth.exchange_code(code)
        userinfo = await google_oauth.fetch_userinfo(tokens.get("access_token", ""))
    except DomainError as exc:
        logger.warning("Google OAuth exchange/userinfo failed: %s", exc.message)
        return failure("google_oauth_failed")
    except Exception:  # Google-side network hiccup — never let this crash the request
        logger.exception("Unexpected error during Google OAuth callback")
        return failure("google_oauth_failed")

    google_sub = userinfo.get("sub")
    email = userinfo.get("email")
    if not google_sub or not email:
        return failure("google_oauth_failed")

    _user, _access, raw_refresh, refresh_exp = await service.google_login(
        google_sub=google_sub,
        email=email,
        email_verified=bool(userinfo.get("email_verified")),
        name=userinfo.get("name"),
    )

    safe_next = _safe_next(next_cookie)
    target = settings.frontend_auth_success_url
    if safe_next:
        target = f"{target}?next={quote(safe_next, safe='')}"
    redirect = RedirectResponse(target, status_code=302)
    _set_refresh_cookie(redirect, raw_refresh, refresh_exp)
    redirect.delete_cookie(GOOGLE_STATE_COOKIE, path=GOOGLE_OAUTH_COOKIE_PATH)
    redirect.delete_cookie(GOOGLE_NEXT_COOKIE, path=GOOGLE_OAUTH_COOKIE_PATH)
    return redirect


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
