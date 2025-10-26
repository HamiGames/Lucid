from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Final


@dataclass(frozen=True)
class ChainConfig:
    """Network/runtime configuration for the Lucid chain."""

    network_id: str = os.getenv("LUCID_NETWORK_ID", "lucid-dev")
    block_time_secs: int = safe_int_env("LUCID_BLOCK_TIME", 5)
    db_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    db_name: str = os.getenv("MONGO_DB", "lucid")

    # Simplified PoA-ish
    max_block_txs: int = safe_int_env("LUCID_MAX_BLOCK_TXS", 100)

    @property
    def genesis_parent(self) -> str:
        return "0" * 64


def safe_int_env(key: str, default: int) -> int:
    """Safely convert environment variable to int."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        print(f"Warning: Invalid {key}, using default: {default}")
        return default


DEFAULT_CONFIG: Final[ChainConfig] = ChainConfig()
