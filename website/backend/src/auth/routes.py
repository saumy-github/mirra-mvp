"""Auth routes — path definitions only, delegates to controller.py."""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response

from ..core.auth_dependency import Identity, get_identity
from . import controller
from .controller import REFRESH_COOKIE
from .models import (
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    SignUpRequest,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


@router.post("/sign-up", status_code=201)
async def sign_up(body: SignUpRequest, response: Response):
    return await controller.sign_up(body, response)


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    return await controller.login(body, response)


@router.post("/guest", status_code=201)
async def create_guest(response: Response):
    return await controller.create_guest(response)


@router.post("/refresh")
async def refresh(response: Response, mirra_refresh: RefreshCookie = None):
    return await controller.refresh(mirra_refresh, response)


@router.post("/logout")
async def logout(response: Response, mirra_refresh: RefreshCookie = None):
    return await controller.logout(mirra_refresh, response)


@router.get("/me")
async def me(identity: Annotated[Identity, Depends(get_identity)]):
    return await controller.me(identity.user_id)


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, identity: Annotated[Identity, Depends(get_identity)]):
    return await controller.verify_email(identity.user_id, body)


@router.post("/password-reset")
async def request_password_reset(body: PasswordResetRequest):
    return await controller.request_password_reset(body)


@router.post("/password-reset/confirm")
async def confirm_password_reset(body: PasswordResetConfirmRequest):
    return await controller.confirm_password_reset(body)
