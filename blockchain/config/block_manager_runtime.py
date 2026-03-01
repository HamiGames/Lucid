"""
Block Manager Runtime Configuration Helper
Provides runtime utilities for loading and applying block-manager configuration.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from .block_manager_config import (
    load_block_manager_config,
    get_block_manager_config,
    BlockManagerConfig
)
from .yaml_loader import load_yaml_config, get_config_dir

logger = logging.getLogger(__name__)


def setup_block_manager_runtime(
    config_path: Optional[Path] = None,
    apply_logging: bool = True,
    apply_storage: bool = True
) -> BlockManagerConfig:
    """
    Set up block manager runtime configuration.
    
    Args:
        config_path: Path to configuration file. If None, uses default.
        apply_logging: If True, configure logging from config.
        apply_storage: If True, ensure storage directories exist.
    
    Returns:
        BlockManagerConfig instance
    """
    # Load configuration
    config = load_block_manager_config(config_path, required=False)
    
    # Apply logging configuration
    if apply_logging:
        _setup_logging(config)
    
    # Apply storage configuration
    if apply_storage:
        _setup_storage(config)
    
    logger.info(f"Block manager runtime configured: {config.service.name} on {config.service.host}:{config.service.port}")
    return config


def _setup_logging(config: BlockManagerConfig):
    """Set up logging from configuration."""
    try:
        # Load logging configuration
        logging_config_path = get_config_dir() / "block-manager-logging.yaml"
        if logging_config_path.exists():
            import logging.config
            logging_config = load_yaml_config(logging_config_path, required=False)
            if logging_config:
                # Ensure log directory exists
                log_dir = Path(config.logging.directory)
                log_dir.mkdir(parents=True, exist_ok=True)
                
                # Apply logging configuration
                logging.config.dictConfig(logging_config)
                logger.info(f"Logging configured from {logging_config_path}")
        else:
            # Fallback to basic configuration
            log_dir = Path(config.logging.directory)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            logging.basicConfig(
                level=getattr(logging, config.logging.level.upper(), logging.INFO),
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                handlers=[
                    logging.StreamHandler(),
                    logging.FileHandler(log_dir / "block-manager.log")
                ]
            )
            logger.info("Logging configured with basic settings")
    except Exception as e:
        logger.error(f"Failed to configure logging: {e}", exc_info=True)


def _setup_storage(config: BlockManagerConfig):
    """Set up storage directories from configuration."""
    try:
        # Ensure blocks directory exists
        blocks_path = Path(config.storage.blocks_path)
        blocks_path.mkdir(parents=True, exist_ok=True)
        
        # Ensure cache directory exists
        cache_path = Path(config.storage.cache_path)
        cache_path.mkdir(parents=True, exist_ok=True)
        
        # Set permissions if required
        if config.storage.ensure_permissions:
            try:
                owner_parts = config.storage.owner.split(":")
                if len(owner_parts) == 2:
                    uid = int(owner_parts[0])
                    gid = int(owner_parts[1])
                    # Note: chown requires root, so this may fail in container
                    # The directory should be created with correct ownership in Dockerfile
                    logger.debug(f"Storage ownership configured: {uid}:{gid}")
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid owner format '{config.storage.owner}': {e}")
        
        logger.info(f"Storage directories configured: blocks={blocks_path}, cache={cache_path}")
    except Exception as e:
        logger.error(f"Failed to configure storage: {e}", exc_info=True)
        raise


def get_error_config() -> Dict[str, Any]:
    """Load error handling configuration."""
    error_config_path = get_config_dir() / "block-manager-errors.yaml"
    return load_yaml_config(error_config_path, required=False)


def get_runtime_env() -> Dict[str, str]:
    """
    Get runtime environment variables from configuration.
    
    Returns:
        Dictionary of environment variable names and values
    """
    config = get_block_manager_config()
    
    return {
        "BLOCK_MANAGER_HOST": config.service.host,
        "BLOCK_MANAGER_PORT": str(config.service.port),
        "BLOCK_MANAGER_URL": config.service.url,
        "BLOCK_STORAGE_PATH": config.storage.blocks_path,
        "BLOCKCHAIN_ENGINE_URL": config.synchronization.engine_url,
        "SYNC_TIMEOUT": str(config.synchronization.sync_timeout_seconds),
        "LOG_LEVEL": config.logging.level,
        "LUCID_ENV": config.service.environment,
        "LUCID_PLATFORM": config.service.platform,
    }


def validate_config(config: Optional[BlockManagerConfig] = None) -> bool:
    """
    Validate block manager configuration.
    
    Args:
        config: Configuration to validate. If None, loads current config.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    if config is None:
        config = get_block_manager_config()
    
    errors = []
    
    # Validate service configuration
    if not config.service.host:
        errors.append("Service host is required")
    if not (1 <= config.service.port <= 65535):
        errors.append(f"Service port must be between 1 and 65535, got {config.service.port}")
    
    # Validate dependencies
    if not config.dependencies.mongodb_url:
        errors.append("MongoDB URL is required")
    if not config.dependencies.blockchain_engine_url:
        errors.append("Blockchain engine URL is required")
    
    # Validate storage
    if not config.storage.blocks_path:
        errors.append("Blocks storage path is required")
    
    # Validate synchronization
    if not config.synchronization.engine_url:
        errors.append("Synchronization engine URL is required")
    if config.synchronization.sync_timeout_seconds <= 0:
        errors.append("Synchronization timeout must be positive")
    
    if errors:
        for error in errors:
            logger.error(f"Configuration validation error: {error}")
        return False
    
    logger.info("Block manager configuration validation passed")
    return True

