from __future__ import annotations

from typing import Any, Dict, Iterable, Optional
from .block import Block
from .transaction import Transaction
from .config import DEFAULT_CONFIG

try:
    from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
except Exception:  # pragma: no cover
    AsyncIOMotorClient = None  # type: ignore


class Storage:
    """Storage adapter preferring Mongo (Motor). Falls back to in-memory if Motor unavailable."""

    def __init__(self, url: Optional[str] = None, db_name: Optional[str] = None) -> None:
        self._url = url or DEFAULT_CONFIG.db_url
        self._db_name = db_name or DEFAULT_CONFIG.db_name
        self._mem_blocks: Dict[str, Dict[str, Any]] = {}
        self._mem_txs: Dict[str, Dict[str, Any]] = {}

        self._client = None
        self._db = None
        if AsyncIOMotorClient is not None:
            self._client = AsyncIOMotorClient(self._url)
            self._db = self._client[self._db_name]

    async def save_block(self, block: Block) -> None:
        if self._db:
            await self._db.blocks.insert_one({"hash": block.block_hash, "header": block.header.__dict__, "txs": [t.__dict__ for t in block.txs]})
        else:
            self._mem_blocks[block.block_hash] = {"header": block.header.__dict__, "txs": [t.__dict__ for t in block.txs]}

    async def get_block(self, block_hash: str) -> Optional[Dict[str, Any]]:
        if self._db:
            return await self._db.blocks.find_one({"hash": block_hash})
        return self._mem_blocks.get(block_hash)

    async def save_txs(self, txs: Iterable[Transaction]) -> None:
        docs = [{"txid": t.txid, **t.__dict__} for t in txs]
        if self._db:
            if docs:
                await self._db.txs.insert_many(docs, ordered=False)
        else:
            for d in docs:
                self._mem_txs[d["txid"]] = d
