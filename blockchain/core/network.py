from __future__ import annotations

import os
import asyncio
from typing import Callable, Awaitable, Tuple, Optional


class PeerServer:
    """Minimal asyncio TCP server to demonstrate P2P hooks (dev only)."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        # Use environment variables for host and port, with defaults
        self.host = host or os.getenv("P2P_HOST", "0.0.0.0")
        self.port = port or int(os.getenv("P2P_PORT", "5050"))
        self._server: asyncio.AbstractServer | None = None

    async def start(self, handler: Callable[[asyncio.StreamReader, asyncio.StreamWriter], Awaitable[None]]) -> Tuple[str, int]:
        self._server = await asyncio.start_server(handler, self.host, self.port)
        sock = next(iter(self._server.sockets or []))
        addr = sock.getsockname()
        return addr[0], addr[1]

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
