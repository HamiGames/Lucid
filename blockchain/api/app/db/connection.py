from __future__ import annotations

import logging
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_logger = logging.getLogger("app.db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


def _get_client() -> AsyncIOMotorClient:
    global _client, _db
    if _client is None:
        settings = get_settings()
        # Use DATABASE_URL and DATABASE_NAME from settings (aligned with config.py)
        _client = AsyncIOMotorClient(settings.DATABASE_URL)
        _db = _client[settings.DATABASE_NAME]
        _logger.info("Mongo connected db=%s", settings.DATABASE_NAME)
    return _client


def get_db_sync() -> AsyncIOMotorDatabase:
    """Synchronous accessor (not an async dep), useful for modules needing db at import-time."""
    global _db
    if _db is None:
        _get_client()
    assert _db is not None
    return _db


async def get_db() -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    """FastAPI dependency."""
    yield get_db_sync()
