"""Async MongoDB client for the shared mirratest database.

Ported from mirra_measurements/db.py (sync) — same database, same
measurements/sizes collections the CLO pipeline reads and writes, but on
PyMongo's native async driver so a slow query can't block other in-flight
requests. Index definitions for measurements/sizes match the originals.
"""

import logging

from pymongo import ASCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from .config import get_settings

logger = logging.getLogger("mirra.backend.db")

_client: AsyncMongoClient | None = None


def _make_client() -> AsyncMongoClient:
    settings = get_settings()
    # tz_aware so stored UTC datetimes read back timezone-aware — expiry
    # comparisons against datetime.now(timezone.utc) would raise otherwise.
    kwargs: dict = {"serverSelectionTimeoutMS": 3000, "tz_aware": True}
    # Atlas on some platforms needs certifi's CA bundle (see mirra_measurements/db.py).
    if settings.mongodb_uri.startswith("mongodb+srv://") or "tls=true" in settings.mongodb_uri:
        try:
            import certifi

            kwargs["tlsCAFile"] = certifi.where()
        except ImportError:
            pass
    return AsyncMongoClient(settings.mongodb_uri, **kwargs)


def get_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        _client = _make_client()
    return _client


def get_db() -> AsyncDatabase:
    return get_client()[get_settings().database_name]


# --- Collection accessors -------------------------------------------------
# Existing collections (shared with the CLO pipeline / mirra_measurements):


def measurements_col() -> AsyncCollection:
    return get_db()["measurements"]


def sizes_col() -> AsyncCollection:
    return get_db()["sizes"]


# New collections owned by this backend:


def users_col() -> AsyncCollection:
    return get_db()["users"]


def refresh_tokens_col() -> AsyncCollection:
    return get_db()["refresh_tokens"]


def avatar_jobs_col() -> AsyncCollection:
    return get_db()["avatar_jobs"]


def avatar_profiles_col() -> AsyncCollection:
    return get_db()["avatar_profiles"]


def tryon_sessions_col() -> AsyncCollection:
    return get_db()["tryon_sessions"]


def tryon_renders_col() -> AsyncCollection:
    return get_db()["tryon_renders"]


def signature_looks_col() -> AsyncCollection:
    return get_db()["signature_looks"]


def analytics_events_col() -> AsyncCollection:
    return get_db()["analytics_events"]


def capture_sessions_col() -> AsyncCollection:
    return get_db()["capture_sessions"]


async def ensure_indexes() -> None:
    """Create all indexes once at startup (idempotent)."""
    # Parity with mirra_measurements/db.py:
    await measurements_col().create_index([("user_id", ASCENDING)], unique=True)
    await measurements_col().create_index([("gender", ASCENDING)])
    await sizes_col().create_index([("size_id", ASCENDING)], unique=True, name="size_id_unique")

    # Backend-owned collections (string _id doubles as the public id):
    await users_col().create_index([("email", ASCENDING)], unique=True, sparse=True)
    await refresh_tokens_col().create_index([("token_hash", ASCENDING)], unique=True)
    await refresh_tokens_col().create_index([("user_id", ASCENDING)])
    await refresh_tokens_col().create_index([("family_id", ASCENDING)])
    await avatar_jobs_col().create_index([("user_id", ASCENDING)])
    await avatar_profiles_col().create_index([("user_id", ASCENDING)], unique=True)
    await tryon_sessions_col().create_index([("user_id", ASCENDING)])
    await tryon_renders_col().create_index([("user_id", ASCENDING)])
    await tryon_renders_col().create_index([("session_id", ASCENDING)])
    await signature_looks_col().create_index([("user_id", ASCENDING)])
    await analytics_events_col().create_index([("event", ASCENDING), ("received_at", ASCENDING)])
    await capture_sessions_col().create_index([("token", ASCENDING)], unique=True)
    await capture_sessions_col().create_index([("manual_code", ASCENDING)], unique=True)
    await capture_sessions_col().create_index([("user_id", ASCENDING)])


async def ping() -> bool:
    try:
        await get_db().command("ping")
        return True
    except Exception:
        return False


async def close_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None
