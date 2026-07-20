"""FastAPI dependency for resolving the current user / guest identity.

Resolves the short-lived access JWT from the Authorization: Bearer header —
signature-only, no DB hit on the hot path (backend-implementation-plan.md,
Phase 2). Refresh-token rotation/revocation lives in services/auth, not here.
"""

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Header

from .errors import Unauthorized
from .security import decode_access_token


@dataclass(frozen=True)
class Identity:
    user_id: str
    kind: Literal["user", "guest"]


async def get_identity(
    authorization: Annotated[str | None, Header()] = None,
) -> Identity:
    if not authorization or not authorization.startswith("Bearer "):
        raise Unauthorized("Missing bearer token")
    user_id, kind = decode_access_token(authorization[len("Bearer ") :])
    return Identity(user_id=user_id, kind=kind)


async def get_optional_identity(
    authorization: Annotated[str | None, Header()] = None,
) -> Identity | None:
    """Same as get_identity but anonymous callers get None instead of a 401
    (used by analytics ingest, where events may arrive before any session)."""
    try:
        return await get_identity(authorization)
    except Unauthorized:
        return None
