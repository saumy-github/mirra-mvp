"""MongoDB connection and collection accessors for mirratest."""

import os
from pathlib import Path
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

# Explicitly load the .env that lives next to this file so the URI is found
# regardless of which directory the script is run from.
_ENV_FILE = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=_ENV_FILE)

MONGODB_URI   = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = "mirratest"

# Collection names
AVATAR_COLLECTION_NAME   = "measurements"   # body measurements from avatar pipeline
GARMENTS_COLLECTION_NAME = "garments"       # generated garment pattern data

_client = None
_db = None


def _make_client() -> MongoClient:
    """Create MongoClient that works on macOS against Atlas.

    macOS Python triggers TLSV1_ALERT_INTERNAL_ERROR with Atlas unless we
    supply certifi's CA bundle explicitly via tlsCAFile.
    """
    try:
        import certifi  # type: ignore
        return MongoClient(MONGODB_URI, tlsCAFile=certifi.where())
    except ImportError:
        return MongoClient(MONGODB_URI)


def get_client() -> MongoClient:
    """Get MongoDB client (singleton)."""
    global _client
    if _client is None:
        _client = _make_client()
    return _client


def get_db():
    """Return the mirratest database."""
    global _db
    if _db is None:
        _db = get_client()[DATABASE_NAME]
    return _db


def get_measurements_collection():
    """Avatar body-measurements collection (unique index on user_id)."""
    col = get_db()[AVATAR_COLLECTION_NAME]
    col.create_index([("user_id", ASCENDING)], unique=True)
    col.create_index([("gender",  ASCENDING)])
    return col


# Alias used by garment pipeline to read avatar input
get_avatar_collection = get_measurements_collection


def get_garments_collection():
    """Garment-pattern collection with garment_id unique index."""
    col = get_db()[GARMENTS_COLLECTION_NAME]
    col.create_index([("garment_id", ASCENDING)], unique=True, name="garment_id_unique")
    return col


def close_connection():
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db     = None
