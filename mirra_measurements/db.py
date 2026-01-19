"""
Database connection module for MongoDB.
"""

import os
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = "mirratest"
COLLECTION_NAME = "measurements"

_client = None
_db = None


def get_client():
    """Get MongoDB client (singleton pattern)."""
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI)
    return _client


def get_db():
    """Get the mirratest database."""
    global _db
    if _db is None:
        client = get_client()
        _db = client[DATABASE_NAME]
    return _db


def get_measurements_collection():
    """Get the measurements collection with proper indexes."""
    db = get_db()
    collection = db[COLLECTION_NAME]
    
    # Ensure indexes exist
    # Unique index on user_id
    collection.create_index([("user_id", ASCENDING)], unique=True)
    # Non-unique index on gender
    collection.create_index([("gender", ASCENDING)])
    
    return collection


def close_connection():
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
