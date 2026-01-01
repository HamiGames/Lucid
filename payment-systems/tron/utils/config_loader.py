"""
LUCID Payment Systems - TRON Client Configuration Loader Module
YAML/JSON configuration file loader with environment variable override
Following architecture patterns from build/docs/
"""

import os
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from functools import lru_cache

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Configuration loader for YAML and JSON files
    
    Features:
    - Load YAML/JSON configuration files
    - Merge with environment variables
    - Validate configuration
    - Support for nested configuration
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            config_dir = Path(__file__).parent.parent / "config"
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        Load YAML configuration file
        
        Args:
            filename: YAML file name (relative to config_dir)
            
        Returns:
            Configuration dictionary
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Configuration file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            logger.info(f"Loaded configuration from {filepath}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration from {filepath}: {e}")
            return {}
    
    def load_json(self, filename: str) -> Dict[str, Any]:
        """
        Load JSON configuration file
        
        Args:
            filename: JSON file name (relative to config_dir)
            
        Returns:
            Configuration dictionary
        """
        filepath = self.config_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Configuration file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"Loaded configuration from {filepath}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration from {filepath}: {e}")
            return {}
    
    def merge_with_env(self, config: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Merge configuration with environment variables
        
        Environment variables override config values.
        Nested keys are accessed via underscore notation:
        - config.network.timeout -> TRON_NETWORK_TIMEOUT
        
        Args:
            config: Configuration dictionary
            prefix: Environment variable prefix
            
        Returns:
            Merged configuration dictionary
        """
        merged = config.copy()
        
        def _merge_dict(d: Dict[str, Any], env_prefix: str):
            for key, value in d.items():
                env_key = f"{env_prefix}_{key}".upper() if env_prefix else key.upper()
                
                if isinstance(value, dict):
                    _merge_dict(value, env_key)
                else:
                    # Check environment variable
                    env_value = os.getenv(env_key)
                    if env_value is not None:
                        # Convert type based on original value
                        if isinstance(value, bool):
                            d[key] = env_value.lower() in ('true', '1', 'yes', 'on')
                        elif isinstance(value, int):
                            try:
                                d[key] = int(env_value)
                            except ValueError:
                                logger.warning(f"Invalid integer value for {env_key}: {env_value}")
                        elif isinstance(value, float):
                            try:
                                d[key] = float(env_value)
                            except ValueError:
                                logger.warning(f"Invalid float value for {env_key}: {env_value}")
                        else:
                            d[key] = env_value
        
        _merge_dict(merged, prefix)
        return merged
    
    def get_nested(self, config: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        Get nested configuration value
        
        Args:
            config: Configuration dictionary
            path: Dot-separated path (e.g., "network.connection.timeout")
            default: Default value if path not found
            
        Returns:
            Configuration value or default
        """
        keys = path.split('.')
        value = config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def validate_config(self, config: Dict[str, Any], required_keys: list) -> list:
        """
        Validate configuration
        
        Args:
            config: Configuration dictionary
            required_keys: List of required keys (supports nested paths)
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        for key_path in required_keys:
            value = self.get_nested(config, key_path)
            if value is None:
                errors.append(f"Missing required configuration: {key_path}")
        
        return errors


@lru_cache(maxsize=1)
def load_yaml_config(filename: str, merge_env: bool = True, env_prefix: str = "") -> Dict[str, Any]:
    """
    Load YAML configuration file (cached)
    
    Args:
        filename: YAML file name
        merge_env: Merge with environment variables
        env_prefix: Environment variable prefix
        
    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader()
    config = loader.load_yaml(filename)
    
    if merge_env:
        config = loader.merge_with_env(config, env_prefix)
    
    return config


# Global config loader instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get or create global config loader instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader

