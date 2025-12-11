from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Final, Dict, Any, Optional

from .yaml_loader import load_yaml_config, get_config_dir


def _required_env(keys: list[str]) -> str:
    """Return first available env var from keys or raise."""
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    raise RuntimeError(f"Missing required environment variable (one of {keys}) for database URL")


def safe_int_env(key: str, default: int) -> int:
    """Safely convert environment variable to int."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        print(f"Warning: Invalid {key}, using default: {default}")
        return default


def safe_bool_env(key: str, default: bool) -> bool:
    """Safely convert environment variable to bool."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ('true', 'yes', 'on', '1', 'enabled')


@dataclass(frozen=True)
class ChainConfig:
    """Network/runtime configuration for the Lucid chain."""

    network_id: str = os.getenv("LUCID_NETWORK_ID", "lucid-dev")
    block_time_secs: int = safe_int_env("LUCID_BLOCK_TIME", 5)
    db_url: str = _required_env(["MONGODB_URL", "MONGO_URL"])
    db_name: str = os.getenv("MONGO_DB", "lucid")

    # Simplified PoA-ish
    max_block_txs: int = safe_int_env("LUCID_MAX_BLOCK_TXS", 100)

    @property
    def genesis_parent(self) -> str:
        return "0" * 64


class BlockchainConfig:
    """
    Comprehensive blockchain configuration loader.
    Loads configuration from YAML files with environment variable substitution.
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or get_config_dir()
        self._configs: Dict[str, Any] = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all configuration files."""
        # Create context with current environment variables
        context = {
            'MONGODB_URL': os.getenv('MONGODB_URL') or os.getenv('MONGO_URL'),
            'REDIS_URL': os.getenv('REDIS_URL'),
            'LUCID_NETWORK_ID': os.getenv('LUCID_NETWORK_ID', 'lucid-dev'),
            'BLOCKCHAIN_ENGINE_PORT': os.getenv('BLOCKCHAIN_ENGINE_PORT', '8084'),
            'SESSION_ANCHORING_PORT': os.getenv('SESSION_ANCHORING_PORT', '8085'),
            'BLOCK_MANAGER_PORT': os.getenv('BLOCK_MANAGER_PORT', '8086'),
            'DATA_CHAIN_PORT': os.getenv('DATA_CHAIN_PORT', '8087'),
        }
        
        # Load YAML configurations
        self._configs['anchoring'] = load_yaml_config(
            self.config_dir / 'anchoring-policies.yaml',
            required=False,
            context=context
        )
        self._configs['block_storage'] = load_yaml_config(
            self.config_dir / 'block-storage-policies.yaml',
            required=False,
            context=context
        )
        self._configs['consensus'] = load_yaml_config(
            self.config_dir / 'consensus-config.yaml',
            required=False,
            context=context
        )
        self._configs['data_chain'] = load_yaml_config(
            self.config_dir / 'data-chain-config.yaml',
            required=False,
            context=context
        )
    
    def get_anchoring_config(self) -> Dict[str, Any]:
        """Get anchoring policies configuration."""
        return self._configs.get('anchoring', {})
    
    def get_block_storage_config(self) -> Dict[str, Any]:
        """Get block storage policies configuration."""
        return self._configs.get('block_storage', {})
    
    def get_consensus_config(self) -> Dict[str, Any]:
        """Get consensus configuration."""
        return self._configs.get('consensus', {})
    
    def get_data_chain_config(self) -> Dict[str, Any]:
        """Get data chain configuration."""
        return self._configs.get('data_chain', {})
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configurations."""
        return self._configs.copy()


# Global configuration instance
_config_instance: Optional[BlockchainConfig] = None


def get_blockchain_config() -> BlockchainConfig:
    """Get global blockchain configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = BlockchainConfig()
    return _config_instance


DEFAULT_CONFIG: Final[ChainConfig] = ChainConfig()
