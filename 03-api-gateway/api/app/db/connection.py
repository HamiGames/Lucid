# Path: 03-api-gateway/api/app/db/connection.py
# Central async Mongo client via Motor. Keep a single client per process. :contentReference[oaicite:5]{index=5}

import os
from typing import Tuple
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

_MONGO_CLIENT: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _MONGO_CLIENT
    if _MONGO_CLIENT is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _MONGO_CLIENT = AsyncIOMotorClient(uri, uuidRepresentation="standard")
    return _MONGO_CLIENT


def get_database() -> AsyncIOMotorDatabase:
    db_name = os.getenv("MONGO_DB", "lucid")
    return get_client()[db_name]


async def ping() -> Tuple[bool, float]:
    import time

    start = time.perf_counter()
    try:
        await get_client().admin.command("ping")
        return True, round((time.perf_counter() - start) * 1000.0, 2)
    except Exception:
        return False, round((time.perf_counter() - start) * 1000.0, 2)
