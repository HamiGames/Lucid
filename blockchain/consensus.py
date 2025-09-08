from __future__ import annotations

from typing import List
from .mempool import Mempool
from .block import Block, BlockHeader
from .config import DEFAULT_CONFIG


class SimpleProposer:
    """Simplified PoA-like proposer: batches up to max_block_txs every block_time."""

    def __init__(self, proposer_id: str = "dev-proposer") -> None:
        self.proposer_id = proposer_id
        self.cfg = DEFAULT_CONFIG
        self._height = 0
        self._parent = self.cfg.genesis_parent

    async def propose(self, mempool: Mempool) -> Block:
        txs = await mempool.drain(self.cfg.max_block_txs)
        header = BlockHeader(parent=self._parent, number=self._height, tx_root="", proposer=self.proposer_id)
        block = Block(header=header, txs=txs)
        tx_root = block.compute_tx_root()
        # Rebuild header with computed root
        header = BlockHeader(parent=self._parent, number=self._height, tx_root=tx_root, proposer=self.proposer_id)
        block = Block(header=header, txs=txs)
        # Advance chain tip
        self._parent = block.block_hash
        self._height += 1
        return block
