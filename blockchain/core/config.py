from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Final


def _required_env(keys: list[str]) -> str:
    """Return first available env var from keys or raise."""
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    raise RuntimeError(f"Missing required environment variable (one of {keys}) for database URL")

@dataclass(frozen=True)
class ChainConfig:
    """Network/runtime configuration for the Lucid chain."""

    network_id: str = os.getenv("LUCID_NETWORK_ID", "lucid-dev")
    block_time_secs: int = int(os.getenv("LUCID_BLOCK_TIME", "5"))
    db_url: str = _required_env(["MONGODB_URL", "MONGO_URL"])
    db_name: str = os.getenv("MONGO_DB", "lucid")

    # Simplified PoA-ish
    max_block_txs: int = int(os.getenv("LUCID_MAX_BLOCK_TXS", "100"))

    @property
    def genesis_parent(self) -> str:
        return "0" * 64


DEFAULT_CONFIG: Final[ChainConfig] = ChainConfig()
