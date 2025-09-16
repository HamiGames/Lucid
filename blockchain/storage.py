# Path: blockchain/storage.py

from __future__ import annotations
from typing import Optional, Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import PyMongoError


class Storage:
    """
    Storage helper for blockchain blocks.
    Avoid truthiness checks on Motor DB (it defines __bool__ returning int).
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db: Optional[AsyncIOMotorDatabase] = db

    @property
    def db(self) -> Optional[AsyncIOMotorDatabase]:
        return self._db

    def is_ready(self) -> bool:
        return self._db is not None

    async def ensure_indexes(self) -> None:
        if self._db is None:
            return
        try:
            await self._db["blocks"].create_index("hash", unique=True)
            await self._db["blocks"].create_index([("height", 1)])
        except PyMongoError:
            # keep bootstrap resilient
            pass

    async def put_block(self, block: dict[str, Any]) -> None:
        if self._db is None:
            raise RuntimeError("Storage DB not initialized")
        await self._db["blocks"].insert_one(block)

    async def get_block_by_hash(self, h: str) -> Optional[dict[str, Any]]:
        if self._db is None:
            return None
        return await self._db["blocks"].find_one({"hash": h})

    # Alias kept for callers/tests that expect this name
    async def save_block(self, block: dict[str, Any]) -> None:
        await self.put_block(block)
