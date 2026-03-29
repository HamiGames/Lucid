# 03_api_gateway/api/app/services/mongo_service.py
"""
File: /app/03_api_gateway/api/app/services/mongo_service.py
x-lucid-file-path: /app/03_api_gateway/api/app/services/mongo_service.py
x-lucid-file-type: python
"""

from __future__ import annotations

from typing import Any

from pymongo.database import Database
from pymongo.errors import PyMongoError

from api.app.database.connection import get_database
from api.app.utils.config import mongo_conn_str, mongo_timeouts_ms


def _mongo_url() -> str:
    """
    Backward-compatible function kept for existing imports.
    Now delegates to the single helper used across the app.
    """
    return mongo_conn_str()


def get_db(name: str = "lucid") -> Database:
    """
    Get (and lazily create) the named database.
    """
    return get_database().get_database(name)


def ping(timeout_ms: int | None = None) -> bool:
    """
    Ping the server using the unified client.
    """
    try:
        sst, cto = mongo_timeouts_ms()
        if timeout_ms is not None:
            sst = cto = timeout_ms
        # Running a command triggers server selection
        get_database().admin.command("ping")
        return True
    except PyMongoError:
        return False
