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
AVATAR_COLLECTION_NAME = "measurements"  # CLI/golden-user fixtures
USER_MEASUREMENTS_COLLECTION_NAME = "user_measurements"  # written by the website
SIZES_COLLECTION_NAME = "sizes"          # product size templates
CLOTHS_COLLECTION_NAME = "cloths"        # one per product_ingestion/input/c_XXX/ folder

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


def get_user_measurements_collection():
    """The live, website-facing measurements store (dev and production)."""
    col = get_db()[USER_MEASUREMENTS_COLLECTION_NAME]
    col.create_index([("user_id", ASCENDING)], unique=True)
    return col


# Alias used by garment pipeline to read avatar input
get_avatar_collection = get_measurements_collection


def get_sizes_collection():
    """Size collection with size_id unique index."""
    col = get_db()[SIZES_COLLECTION_NAME]
    col.create_index([("size_id", ASCENDING)], unique=True, name="size_id_unique")
    return col


def get_cloths_collection():
    """Cloth collection with cloth_id unique index."""
    col = get_db()[CLOTHS_COLLECTION_NAME]
    col.create_index([("cloth_id", ASCENDING)], unique=True, name="cloth_id_unique")
    return col


def close_connection():
    """Close the MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db     = None
