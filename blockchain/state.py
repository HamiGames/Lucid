from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict
from .transaction import Transaction


class State:
    """In-memory account state for dev. Persisted snapshots handled by storage layer."""

    def __init__(self) -> None:
        self._balances: Dict[str, int] = defaultdict(int)
        self._nonces: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def get_balance(self, addr: str) -> int:
        async with self._lock:
            return self._balances[addr]

    async def get_nonce(self, addr: str) -> int:
        async with self._lock:
            return self._nonces[addr]

    async def apply_tx(self, tx: Transaction) -> bool:
        async with self._lock:
            if self._nonces[tx.sender] != tx.nonce:
                return False
            if self._balances[tx.sender] < tx.amount:
                return False
            self._balances[tx.sender] -= tx.amount
            self._balances[tx.recipient] += tx.amount
            self._nonces[tx.sender] += 1
            return True
