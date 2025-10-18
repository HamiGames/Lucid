from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from .transaction import Transaction
from .crypto import sha256_hex, merkle_root


@dataclass(frozen=True)
class BlockHeader:
    parent: str
    number: int
    tx_root: str
    proposer: str


@dataclass(frozen=True)
class Block:
    header: BlockHeader
    txs: List[Transaction] = field(default_factory=list)

    def compute_tx_root(self) -> str:
        roots = [bytes.fromhex(tx.txid) for tx in self.txs]
        return merkle_root(roots).hex()

    @property
    def block_hash(self) -> str:
        raw = f"{self.header.parent}:{self.header.number}:{self.header.tx_root}:{self.header.proposer}".encode(
            "utf-8"
        )
        return sha256_hex(raw)
