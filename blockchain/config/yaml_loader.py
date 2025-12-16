"""
YAML Configuration Loader with Environment Variable Support
Loads YAML configuration files and substitutes environment variables.

Supports:
- ${VAR_NAME} or ${VAR_NAME:default_value} syntax
- Nested configuration values
- Type conversion (int, float, bool, str)
- Required vs optional environment variables
"""

from __future__ import annotations

import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging

logger = logging.getLogger(__name__)

# Pattern to match ${VAR_NAME} or ${VAR_NAME:default}
ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]+))?\}')


def substitute_env_vars(value: Any, context: Optional[Dict[str, Any]] = None) -> Any:
    """
    Recursively substitute environment variables in configuration values.
    
    Supports:
    - ${VAR_NAME} - Required environment variable
    - ${VAR_NAME:default_value} - Optional with default
    - Nested dictionaries and lists
    """
    if isinstance(value, dict):
        return {k: substitute_env_vars(v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [substitute_env_vars(item, context) for item in value]
    elif isinstance(value, str):
        # Check if string contains environment variable pattern
        matches = ENV_VAR_PATTERN.findall(value)
        if not matches:
            return value
        
        result = value
        for var_name, default_value in matches:
            # Check context first (for nested references)
            env_value = None
            if context:
                env_value = context.get(var_name)
            
            # Then check environment
            if env_value is None:
                env_value = os.getenv(var_name)
            
            # Use default if provided
            if env_value is None:
                if default_value is not None:
                    env_value = default_value
                else:
                    raise ValueError(
                        f"Required environment variable '{var_name}' not set "
                        f"(used in: {value})"
                    )
            
            # Replace all occurrences
            result = result.replace(f"${{{var_name}}}", str(env_value))
            if default_value:
                result = result.replace(f"${{{var_name}:{default_value}}}", str(env_value))
        
        # Try to convert to appropriate type
        return _convert_type(result)
    
    return value


def _convert_type(value: str) -> Union[str, int, float, bool]:
    """Convert string value to appropriate type."""
    if not isinstance(value, str):
        return value
    
    # Boolean
    if value.lower() in ('true', 'yes', 'on', '1'):
        return True
    if value.lower() in ('false', 'no', 'off', '0'):
        return False
    
    # Integer
    try:
        return int(value)
    except ValueError:
        pass
    
    # Float
    try:
        return float(value)
    except ValueError:
        pass
    
    # String (default)
    return value


def load_yaml_config(
    config_path: Union[str, Path],
    required: bool = False,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Load YAML configuration file with environment variable substitution.
    
    Args:
        config_path: Path to YAML configuration file
        required: If True, raise error if file doesn't exist
        context: Additional context variables for substitution
    
    Returns:
        Dictionary with configuration values
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        if required:
            raise FileNotFoundError(f"Required configuration file not found: {config_path}")
        logger.warning(f"Configuration file not found: {config_path}, using defaults")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
        
        # Substitute environment variables
        config = substitute_env_vars(config, context)
        
        logger.info(f"Loaded configuration from {config_path}")
        return config
    
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {e}")
        if required:
            raise
        return {}


def get_config_dir() -> Path:
    """Get the configuration directory path."""
    return Path(__file__).parent


def load_all_configs(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Load all configuration files from the config directory.
    
    Returns:
        Dictionary with all configuration values
    """
    config_dir = get_config_dir()
    
    configs = {
        'chain': load_yaml_config(config_dir / 'config.py', required=False, context=context),
        'anchoring': load_yaml_config(config_dir / 'anchoring-policies.yaml', required=False, context=context),
        'block_storage': load_yaml_config(config_dir / 'block-storage-policies.yaml', required=False, context=context),
        'consensus': load_yaml_config(config_dir / 'consensus-config.yaml', required=False, context=context),
        'data_chain': load_yaml_config(config_dir / 'data-chain-config.yaml', required=False, context=context),
        'block_manager': load_yaml_config(config_dir / 'block-manager-config.yaml', required=False, context=context),
    }
    
    return configs

