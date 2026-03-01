"""
Block Manager Configuration Loader
Loads and validates block-manager configuration from YAML with environment variable support.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .yaml_loader import load_yaml_config, get_config_dir

logger = logging.getLogger(__name__)


@dataclass
class ServiceConfig:
    """Service configuration."""
    name: str
    host: str
    port: int
    url: str
    environment: str
    platform: str


@dataclass
class DependencyConfig:
    """Dependency configuration."""
    mongodb_url: str
    redis_url: str
    blockchain_engine_url: str
    healthcheck: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StorageConfig:
    """Storage configuration."""
    blocks_path: str
    cache_path: str
    ensure_permissions: bool = True
    owner: str = "65532:65532"


@dataclass
class LoggingConfig:
    """Logging configuration."""
    directory: str
    level: str = "INFO"
    format: str = "standard"
    rotate: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SynchronizationConfig:
    """Synchronization configuration."""
    engine_url: str
    sync_timeout_seconds: int = 30
    fetch_batch_size: int = 100


@dataclass
class APIConfig:
    """API configuration."""
    base_path: str = "/api/v1"
    blocks: Dict[str, str] = field(default_factory=dict)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    window_seconds: int = 60
    max_requests: int = 500


@dataclass
class SecurityConfig:
    """Security configuration."""
    user: int = 65532
    group: int = 65532
    read_only_root: bool = True


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    metrics_enabled: bool = True
    expose_health: bool = True
    expose_metrics: bool = False


@dataclass
class BlockManagerConfig:
    """Complete block manager configuration."""
    service: ServiceConfig
    dependencies: DependencyConfig
    storage: StorageConfig
    logging: LoggingConfig
    synchronization: SynchronizationConfig
    api: APIConfig
    rate_limits: RateLimitConfig
    security: SecurityConfig
    monitoring: MonitoringConfig
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> BlockManagerConfig:
        """Create BlockManagerConfig from dictionary."""
        service_data = config_dict.get("service", {})
        deps_data = config_dict.get("dependencies", {})
        storage_data = config_dict.get("storage", {})
        logging_data = config_dict.get("logging", {})
        sync_data = config_dict.get("synchronization", {})
        api_data = config_dict.get("api", {})
        rate_limit_data = config_dict.get("rate_limits", {})
        security_data = config_dict.get("security", {})
        monitoring_data = config_dict.get("monitoring", {})
        
        return cls(
            service=ServiceConfig(**service_data),
            dependencies=DependencyConfig(**deps_data),
            storage=StorageConfig(**storage_data),
            logging=LoggingConfig(**logging_data),
            synchronization=SynchronizationConfig(**sync_data),
            api=APIConfig(**api_data),
            rate_limits=RateLimitConfig(**rate_limit_data),
            security=SecurityConfig(**security_data),
            monitoring=MonitoringConfig(**monitoring_data)
        )


def load_block_manager_config(
    config_path: Optional[Path] = None,
    required: bool = False
) -> BlockManagerConfig:
    """
    Load block manager configuration from YAML file.
    
    Args:
        config_path: Path to configuration file. If None, uses default.
        required: If True, raise error if file doesn't exist or is invalid.
    
    Returns:
        BlockManagerConfig instance
    """
    if config_path is None:
        config_path = get_config_dir() / "block-manager-config.yaml"
    
    # Create context with environment variables
    context = {
        'BLOCK_MANAGER_HOST': os.getenv('BLOCK_MANAGER_HOST', 'block-manager'),
        'BLOCK_MANAGER_PORT': os.getenv('BLOCK_MANAGER_PORT', '8086'),
        'BLOCK_MANAGER_URL': os.getenv('BLOCK_MANAGER_URL', 'http://block-manager:8086'),
        'LUCID_ENV': os.getenv('LUCID_ENV', 'production'),
        'LUCID_PLATFORM': os.getenv('LUCID_PLATFORM', 'arm64'),
        'MONGODB_URL': os.getenv('MONGODB_URL') or os.getenv('MONGO_URL'),
        'REDIS_URL': os.getenv('REDIS_URL'),
        'BLOCKCHAIN_ENGINE_URL': os.getenv('BLOCKCHAIN_ENGINE_URL'),
        'SYNC_TIMEOUT': os.getenv('SYNC_TIMEOUT', '30'),
    }
    
    # Load YAML configuration
    config_dict = load_yaml_config(config_path, required=required, context=context)
    
    if not config_dict:
        if required:
            raise FileNotFoundError(f"Block manager configuration not found: {config_path}")
        logger.warning("Using default block manager configuration")
        return _get_default_config()
    
    try:
        return BlockManagerConfig.from_dict(config_dict)
    except Exception as e:
        if required:
            raise ValueError(f"Invalid block manager configuration: {e}") from e
        logger.error(f"Failed to parse block manager configuration: {e}, using defaults")
        return _get_default_config()


def _get_default_config() -> BlockManagerConfig:
    """Get default configuration from environment variables."""
    return BlockManagerConfig(
        service=ServiceConfig(
            name="block-manager",
            host=os.getenv("BLOCK_MANAGER_HOST", "block-manager"),
            port=int(os.getenv("BLOCK_MANAGER_PORT", "8086")),
            url=os.getenv("BLOCK_MANAGER_URL", "http://block-manager:8086"),
            environment=os.getenv("LUCID_ENV", "production"),
            platform=os.getenv("LUCID_PLATFORM", "arm64")
        ),
        dependencies=DependencyConfig(
            mongodb_url=os.getenv("MONGODB_URL") or os.getenv("MONGO_URL") or "",
            redis_url=os.getenv("REDIS_URL", ""),
            blockchain_engine_url=os.getenv("BLOCKCHAIN_ENGINE_URL", ""),
            healthcheck={
                "path": "/health",
                "interval_seconds": 30,
                "timeout_seconds": 10,
                "retries": 3,
                "start_period_seconds": 40
            }
        ),
        storage=StorageConfig(
            blocks_path=os.getenv("BLOCK_STORAGE_PATH", "/app/data/blocks"),
            cache_path="/tmp/blocks",
            ensure_permissions=True,
            owner="65532:65532"
        ),
        logging=LoggingConfig(
            directory="/app/logs",
            level=os.getenv("LOG_LEVEL", "INFO"),
            format="standard",
            rotate={
                "enabled": True,
                "max_size_mb": 10,
                "backups": 5
            }
        ),
        synchronization=SynchronizationConfig(
            engine_url=os.getenv("BLOCKCHAIN_ENGINE_URL", ""),
            sync_timeout_seconds=int(os.getenv("SYNC_TIMEOUT", "30")),
            fetch_batch_size=100
        ),
        api=APIConfig(
            base_path="/api/v1",
            blocks={
                "list": "/blocks/",
                "by_id": "/blocks/{block_id}",
                "by_height": "/blocks/height/{height}",
                "latest": "/blocks/latest",
                "validate": "/blocks/validate"
            }
        ),
        rate_limits=RateLimitConfig(
            enabled=True,
            window_seconds=60,
            max_requests=500
        ),
        security=SecurityConfig(
            user=65532,
            group=65532,
            read_only_root=True
        ),
        monitoring=MonitoringConfig(
            metrics_enabled=True,
            expose_health=True,
            expose_metrics=False
        )
    )


# Global configuration instance
_config_instance: Optional[BlockManagerConfig] = None


def get_block_manager_config() -> BlockManagerConfig:
    """Get global block manager configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = load_block_manager_config()
    return _config_instance


def reload_block_manager_config() -> BlockManagerConfig:
    """Reload block manager configuration."""
    global _config_instance
    _config_instance = load_block_manager_config()
    return _config_instance

