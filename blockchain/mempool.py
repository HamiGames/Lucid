from __future__ import annotations

import asyncio
from typing import Dict, List
from .transaction import Transaction


class Mempool:
    def __init__(self) -> None:
        self._txs: Dict[str, Transaction] = {}
        self._lock = asyncio.Lock()

    async def add(self, tx: Transaction) -> None:
        async with self._lock:
            self._txs[tx.txid] = tx

    async def get_all(self, limit: int | None = None) -> List[Transaction]:
        async with self._lock:
            vals = list(self._txs.values())
            return vals[:limit] if limit else vals

    async def drain(self, limit: int) -> List[Transaction]:
        async with self._lock:
            keys = list(self._txs.keys())[:limit]
            txs = [self._txs[k] for k in keys]
            for k in keys:
                self._txs.pop(k, None)
            return txs

    async def size(self) -> int:
        async with self._lock:
            return len(self._txs)
