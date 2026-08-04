"""Google OAuth 2.0 / OpenID Connect helpers. Pure HTTP calls to Google, no
FastAPI/DB imports (same layering rule as service.py) — auth/controller.py
wires this into cookies/redirects, auth/service.py wires it into users.

Identity is established via the userinfo endpoint using the access token
Google issues on code exchange, not by verifying the id_token's signature
ourselves — Google already authenticates that request, which avoids taking
on a JWKS/RS256 verification dependency for a pilot-scale login path.
"""

from urllib.parse import urlencode

import httpx

from ..config import get_settings
from ..core.errors import ServiceUnavailable, Unauthorized

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = "openid email profile"
HTTP_TIMEOUT_SECONDS = 10.0


def is_configured() -> bool:
    settings = get_settings()
    return bool(settings.google_client_id and settings.google_client_secret)


def build_authorize_url(state: str) -> str:
    settings = get_settings()
    if not is_configured():
        raise ServiceUnavailable("Google sign-in is not configured", code="google_not_configured")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": SCOPES,
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
        )
    if resp.status_code != 200:
        raise Unauthorized("Google sign-in failed (token exchange)", code="google_token_exchange_failed")
    return resp.json()


async def fetch_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_SECONDS) as client:
        resp = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if resp.status_code != 200:
        raise Unauthorized("Google sign-in failed (fetching profile)", code="google_userinfo_failed")
    return resp.json()
