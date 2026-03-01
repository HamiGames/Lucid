# Path: blockchain/core/node.py

from __future__ import annotations
from typing import Optional, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from .storage import Storage


class Node:
    def __init__(
        self,
        storage: Optional[Storage] = None,
        db: Optional[AsyncIOMotorDatabase] = None,
    ) -> None:
        self.storage: Storage = storage or Storage(db)

    async def bootstrap(self) -> None:
        await self.storage.ensure_indexes()

    async def submit_block(self, block: dict[str, Any]) -> None:
        await self.storage.save_block(block)

    async def get_block(self, block_hash: str):
        return await self.storage.get_block_by_hash(block_hash)

    def is_ready(self) -> bool:
        return self.storage.is_ready()
