# app/db/connection.py
from __future__ import annotations

import os
import threading
from typing import Optional
from urllib.parse import urlparse

from pymongo import MongoClient
from pymongo.database import Database

_client_lock = threading.Lock()
_client: Optional[MongoClient] = None
_db_name: Optional[str] = None


def _resolve_uri() -> str:
    """Prefer MONGO_URI; fall back to MONGO_URL (compose compatibility)."""
    uri = os.getenv("MONGO_URI") or os.getenv("MONGO_URL")
    if not uri:
        raise RuntimeError("MONGO_URI or MONGO_URL must be set")
    return uri


def _resolve_db_name(uri: str) -> str:
    """Get DB name from URI path or MONGO_DB env; default to 'lucid'."""
    parsed = urlparse(uri)
    if parsed.path and len(parsed.path) > 1:
        return parsed.path.lstrip("/")
    return os.getenv("MONGO_DB", "lucid")


def get_client() -> MongoClient:
    """Singleton MongoClient with sane timeout."""
    global _client, _db_name
    if _client is None:
        with _client_lock:
            if _client is None:
                uri = _resolve_uri()
                _db_name = _resolve_db_name(uri)
                _client = MongoClient(uri, serverSelectionTimeoutMS=20000)
    return _client


def get_db() -> Database:
    """Return Database handle derived from the configured URI."""
    client = get_client()
    name = _db_name or _resolve_db_name(_resolve_uri())
    return client.get_database(name)


def ping() -> dict:
    """Health check: returns {'ok': 1.0} if the server is reachable."""
    return get_client().admin.command("ping")


def close_client() -> None:
    """Close and reset the singleton client (mainly for tests)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
