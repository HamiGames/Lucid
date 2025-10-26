# Path: node/config.py
# Lucid Node Management Configuration
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import timedelta


def safe_int_env(key: str, default: int) -> int:
    """Safely convert environment variable to int."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        print(f"Warning: Invalid {key}, using default: {default}")
        return default


@dataclass
class NodeConfig:
    """Node management configuration"""
    
    # Node identification
    node_id: str
    node_address: str
    private_key: str
    
    # Network configuration
    tron_network: str = "mainnet"  # mainnet, testnet, shasta
    api_port: int = 8095
    rpc_port: int = 8096
    
    # Resource monitoring
    resource_monitoring_interval: int = 30  # seconds
    resource_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "cpu_percent": 80.0,
        "memory_percent": 80.0,
        "disk_percent": 85.0,
        "network_bandwidth_mbps": 100.0
    })
    
    # PoOT configuration
    poot_validation_interval: int = 300  # seconds
    poot_score_threshold: float = 0.5
    poot_history_days: int = 30
    
    # Pool configuration
    pool_join_timeout: int = 60  # seconds
    pool_health_check_interval: int = 120  # seconds
    pool_sync_interval: int = 30  # seconds
    
    # Payout configuration
    payout_processing_interval: int = 3600  # seconds
    payout_minimum_amount: float = 10.0  # USDT
    payout_batch_size: int = 10
    
    # Database configuration
    database_url: str = "mongodb://localhost:27017/lucid"
    database_name: str = "lucid_nodes"
    
    # Logging configuration
    log_level: str = "INFO"
    log_file: str = "node.log"
    log_max_size_mb: int = 100
    log_backup_count: int = 5
    
    # Security configuration
    enable_ssl: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    
    # Performance configuration
    max_concurrent_sessions: int = 10
    session_timeout: int = 7200  # seconds
    bandwidth_limit_mbps: float = 100.0
    storage_limit_gb: float = 100.0
    
    # TRON configuration
    tron_api_key: Optional[str] = None
    tron_api_url: str = "https://api.trongrid.io"
    tron_contract_address: Optional[str] = None
    
    # Monitoring configuration
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30  # seconds
    
    # Development configuration
    debug_mode: bool = False
    test_mode: bool = False
    mock_tron: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "node_id": self.node_id,
            "node_address": self.node_address,
            "private_key": self.private_key,
            "tron_network": self.tron_network,
            "api_port": self.api_port,
            "rpc_port": self.rpc_port,
            "resource_monitoring_interval": self.resource_monitoring_interval,
            "resource_thresholds": self.resource_thresholds,
            "poot_validation_interval": self.poot_validation_interval,
            "poot_score_threshold": self.poot_score_threshold,
            "poot_history_days": self.poot_history_days,
            "pool_join_timeout": self.pool_join_timeout,
            "pool_health_check_interval": self.pool_health_check_interval,
            "pool_sync_interval": self.pool_sync_interval,
            "payout_processing_interval": self.payout_processing_interval,
            "payout_minimum_amount": self.payout_minimum_amount,
            "payout_batch_size": self.payout_batch_size,
            "database_url": self.database_url,
            "database_name": self.database_name,
            "log_level": self.log_level,
            "log_file": self.log_file,
            "log_max_size_mb": self.log_max_size_mb,
            "log_backup_count": self.log_backup_count,
            "enable_ssl": self.enable_ssl,
            "ssl_cert_path": self.ssl_cert_path,
            "ssl_key_path": self.ssl_key_path,
            "max_concurrent_sessions": self.max_concurrent_sessions,
            "session_timeout": self.session_timeout,
            "bandwidth_limit_mbps": self.bandwidth_limit_mbps,
            "storage_limit_gb": self.storage_limit_gb,
            "tron_api_key": self.tron_api_key,
            "tron_api_url": self.tron_api_url,
            "tron_contract_address": self.tron_contract_address,
            "enable_metrics": self.enable_metrics,
            "metrics_port": self.metrics_port,
            "health_check_interval": self.health_check_interval,
            "debug_mode": self.debug_mode,
            "test_mode": self.test_mode,
            "mock_tron": self.mock_tron
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeConfig':
        """Create config from dictionary"""
        return cls(
            node_id=data["node_id"],
            node_address=data["node_address"],
            private_key=data["private_key"],
            tron_network=data.get("tron_network", "mainnet"),
            api_port=data.get("api_port", 8095),
            rpc_port=data.get("rpc_port", 8096),
            resource_monitoring_interval=data.get("resource_monitoring_interval", 30),
            resource_thresholds=data.get("resource_thresholds", {
                "cpu_percent": 80.0,
                "memory_percent": 80.0,
                "disk_percent": 85.0,
                "network_bandwidth_mbps": 100.0
            }),
            poot_validation_interval=data.get("poot_validation_interval", 300),
            poot_score_threshold=data.get("poot_score_threshold", 0.5),
            poot_history_days=data.get("poot_history_days", 30),
            pool_join_timeout=data.get("pool_join_timeout", 60),
            pool_health_check_interval=data.get("pool_health_check_interval", 120),
            pool_sync_interval=data.get("pool_sync_interval", 30),
            payout_processing_interval=data.get("payout_processing_interval", 3600),
            payout_minimum_amount=data.get("payout_minimum_amount", 10.0),
            payout_batch_size=data.get("payout_batch_size", 10),
            database_url=data.get("database_url", "mongodb://localhost:27017/lucid"),
            database_name=data.get("database_name", "lucid_nodes"),
            log_level=data.get("log_level", "INFO"),
            log_file=data.get("log_file", "node.log"),
            log_max_size_mb=data.get("log_max_size_mb", 100),
            log_backup_count=data.get("log_backup_count", 5),
            enable_ssl=data.get("enable_ssl", False),
            ssl_cert_path=data.get("ssl_cert_path"),
            ssl_key_path=data.get("ssl_key_path"),
            max_concurrent_sessions=data.get("max_concurrent_sessions", 10),
            session_timeout=data.get("session_timeout", 7200),
            bandwidth_limit_mbps=data.get("bandwidth_limit_mbps", 100.0),
            storage_limit_gb=data.get("storage_limit_gb", 100.0),
            tron_api_key=data.get("tron_api_key"),
            tron_api_url=data.get("tron_api_url", "https://api.trongrid.io"),
            tron_contract_address=data.get("tron_contract_address"),
            enable_metrics=data.get("enable_metrics", True),
            metrics_port=data.get("metrics_port", 9090),
            health_check_interval=data.get("health_check_interval", 30),
            debug_mode=data.get("debug_mode", False),
            test_mode=data.get("test_mode", False),
            mock_tron=data.get("mock_tron", False)
        )


def load_config(config_path: Optional[str] = None) -> NodeConfig:
    """
    Load node configuration from file or environment variables.
    
    Args:
        config_path: Path to configuration file (optional)
        
    Returns:
        NodeConfig instance
    """
    # Default config path
    if config_path is None:
        config_path = os.getenv("NODE_CONFIG_PATH", "node_config.json")
    
    config_data = {}
    
    # Try to load from file
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load config file {config_path}: {e}")
    
    # Override with environment variables
    config_data.update({
        "node_id": os.getenv("NODE_ID", config_data.get("node_id", "default_node")),
        "node_address": os.getenv("NODE_ADDRESS", config_data.get("node_address", "")),
        "private_key": os.getenv("NODE_PRIVATE_KEY", config_data.get("private_key", "")),
        "tron_network": os.getenv("TRON_NETWORK", config_data.get("tron_network", "mainnet")),
        "api_port": safe_int_env("API_PORT", config_data.get("api_port", 8095)),
        "rpc_port": safe_int_env("RPC_PORT", config_data.get("rpc_port", 8096)),
        "resource_monitoring_interval": safe_int_env("RESOURCE_MONITORING_INTERVAL", config_data.get("resource_monitoring_interval", 30)),
        "poot_validation_interval": safe_int_env("POOT_VALIDATION_INTERVAL", config_data.get("poot_validation_interval", 300)),
        "payout_processing_interval": safe_int_env("PAYOUT_PROCESSING_INTERVAL", config_data.get("payout_processing_interval", 3600)),
        "database_url": os.getenv("DATABASE_URL", config_data.get("database_url", "mongodb://localhost:27017/lucid")),
        "log_level": os.getenv("LOG_LEVEL", config_data.get("log_level", "INFO")),
        "debug_mode": os.getenv("DEBUG_MODE", "false").lower() == "true",
        "test_mode": os.getenv("TEST_MODE", "false").lower() == "true",
        "mock_tron": os.getenv("MOCK_TRON", "false").lower() == "true"
    })
    
    # Validate required fields
    if not config_data.get("node_address"):
        raise ValueError("NODE_ADDRESS is required")
    if not config_data.get("private_key"):
        raise ValueError("NODE_PRIVATE_KEY is required")
    
    return NodeConfig.from_dict(config_data)


def save_config(config: NodeConfig, config_path: str = "node_config.json"):
    """
    Save node configuration to file.
    
    Args:
        config: NodeConfig instance
        config_path: Path to save configuration
    """
    try:
        with open(config_path, 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        print(f"Configuration saved to {config_path}")
    except Exception as e:
        print(f"Failed to save configuration: {e}")


def create_default_config(node_address: str, private_key: str, 
                         node_id: Optional[str] = None) -> NodeConfig:
    """
    Create default configuration for a node.
    
    Args:
        node_address: TRON address of the node
        private_key: Private key for the node
        node_id: Optional custom node ID
        
    Returns:
        NodeConfig instance
    """
    if node_id is None:
        import hashlib
        node_id = hashlib.sha256(node_address.encode()).hexdigest()[:16]
    
    return NodeConfig(
        node_id=node_id,
        node_address=node_address,
        private_key=private_key
    )


# Environment variable mappings
ENV_VAR_MAPPINGS = {
    "NODE_ID": "node_id",
    "NODE_ADDRESS": "node_address", 
    "NODE_PRIVATE_KEY": "private_key",
    "TRON_NETWORK": "tron_network",
    "API_PORT": "api_port",
    "RPC_PORT": "rpc_port",
    "DATABASE_URL": "database_url",
    "LOG_LEVEL": "log_level",
    "DEBUG_MODE": "debug_mode",
    "TEST_MODE": "test_mode",
    "MOCK_TRON": "mock_tron"
}


def get_env_config() -> Dict[str, Any]:
    """Get configuration from environment variables"""
    config = {}
    for env_var, config_key in ENV_VAR_MAPPINGS.items():
        value = os.getenv(env_var)
        if value is not None:
            # Convert string values to appropriate types
            if config_key in ["api_port", "rpc_port", "resource_monitoring_interval", 
                            "poot_validation_interval", "payout_processing_interval"]:
                config[config_key] = int(value)
            elif config_key in ["debug_mode", "test_mode", "mock_tron"]:
                config[config_key] = value.lower() == "true"
            else:
                config[config_key] = value
    return config


if __name__ == "__main__":
    # Test configuration loading
    try:
        config = load_config()
        print(f"Loaded configuration: {config.node_id}")
        print(f"Node address: {config.node_address}")
        print(f"API port: {config.api_port}")
        print(f"Database URL: {config.database_url}")
    except Exception as e:
        print(f"Configuration error: {e}")
