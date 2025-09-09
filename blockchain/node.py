from __future__ import annotations

import asyncio
from .config import DEFAULT_CONFIG
from .mempool import Mempool
from .consensus import SimpleProposer
from .storage import Storage


class Node:
    def __init__(self) -> None:
        self.cfg = DEFAULT_CONFIG
        self.mempool = Mempool()
        self.proposer = SimpleProposer()
        self.storage = Storage()

    async def run(self) -> None:
        interval = self.cfg.block_time_secs
        while True:
            block = await self.proposer.propose(self.mempool)
            await self.storage.save_block(block)
            await asyncio.sleep(interval)


async def _main() -> None:
    node = Node()
    await node.run()


if __name__ == "__main__":
    asyncio.run(_main())
