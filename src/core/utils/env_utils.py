#!/usr/bin/env python3
"""
Lucid Core Utilities - Environment Variable Handling
Safe environment variable parsing and validation utilities.
"""

import os
import logging
from typing import Any, Optional, Union, List
from pathlib import Path

logger = logging.getLogger(__name__)


def safe_int_env(key: str, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
    """
    Safely convert environment variable to integer with validation.
    
    Args:
        key: Environment variable name
        default: Default value if conversion fails
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Integer value from environment or default
    """
    try:
        value = int(os.getenv(key, str(default)))
        
        if min_val is not None and value < min_val:
            logger.warning(f"Environment variable {key}={value} is below minimum {min_val}, using default: {default}")
            return default
            
        if max_val is not None and value > max_val:
            logger.warning(f"Environment variable {key}={value} is above maximum {max_val}, using default: {default}")
            return default
            
        return value
        
    except ValueError as e:
        logger.warning(f"Invalid integer value for {key}: {e}, using default: {default}")
        return default


def safe_float_env(key: str, default: float, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
    """
    Safely convert environment variable to float with validation.
    
    Args:
        key: Environment variable name
        default: Default value if conversion fails
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        
    Returns:
        Float value from environment or default
    """
    try:
        value = float(os.getenv(key, str(default)))
        
        if min_val is not None and value < min_val:
            logger.warning(f"Environment variable {key}={value} is below minimum {min_val}, using default: {default}")
            return default
            
        if max_val is not None and value > max_val:
            logger.warning(f"Environment variable {key}={value} is above maximum {max_val}, using default: {default}")
            return default
            
        return value
        
    except ValueError as e:
        logger.warning(f"Invalid float value for {key}: {e}, using default: {default}")
        return default


def safe_bool_env(key: str, default: bool) -> bool:
    """
    Safely convert environment variable to boolean.
    
    Args:
        key: Environment variable name
        default: Default value if conversion fails
        
    Returns:
        Boolean value from environment or default
    """
    value = os.getenv(key, str(default)).lower()
    
    if value in ('true', '1', 'yes', 'on', 'enabled'):
        return True
    elif value in ('false', '0', 'no', 'off', 'disabled'):
        return False
    else:
        logger.warning(f"Invalid boolean value for {key}: {value}, using default: {default}")
        return default


def safe_str_env(key: str, default: str, allowed_values: Optional[List[str]] = None) -> str:
    """
    Safely get string environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not set
        allowed_values: List of allowed values
        
    Returns:
        String value from environment or default
    """
    value = os.getenv(key, default)
    
    if allowed_values is not None and value not in allowed_values:
        logger.warning(f"Environment variable {key}={value} not in allowed values {allowed_values}, using default: {default}")
        return default
        
    return value


def safe_path_env(key: str, default: str, must_exist: bool = False) -> str:
    """
    Safely get path environment variable with validation.
    
    Args:
        key: Environment variable name
        default: Default path value
        must_exist: Whether the path must exist
        
    Returns:
        Path value from environment or default
    """
    path_str = os.getenv(key, default)
    path = Path(path_str)
    
    if must_exist and not path.exists():
        logger.error(f"Environment variable {key}={path_str} points to non-existent path, using default: {default}")
        return default
        
    return path_str


def safe_list_env(key: str, default: List[str], separator: str = ',') -> List[str]:
    """
    Safely get list environment variable.
    
    Args:
        key: Environment variable name
        default: Default list value
        separator: Separator for splitting string
        
    Returns:
        List value from environment or default
    """
    value = os.getenv(key)
    
    if not value:
        return default
        
    try:
        return [item.strip() for item in value.split(separator) if item.strip()]
    except Exception as e:
        logger.warning(f"Invalid list value for {key}: {e}, using default: {default}")
        return default


def validate_port_env(key: str, default: int) -> int:
    """
    Validate port number environment variable.
    
    Args:
        key: Environment variable name
        default: Default port value
        
    Returns:
        Valid port number
    """
    return safe_int_env(key, default, min_val=1, max_val=65535)


def validate_log_level_env(key: str, default: str = "INFO") -> str:
    """
    Validate log level environment variable.
    
    Args:
        key: Environment variable name
        default: Default log level
        
    Returns:
        Valid log level
    """
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    return safe_str_env(key, default, valid_levels).upper()


def validate_url_env(key: str, default: str, required_schemes: Optional[List[str]] = None) -> str:
    """
    Validate URL environment variable.
    
    Args:
        key: Environment variable name
        default: Default URL value
        required_schemes: Required URL schemes
        
    Returns:
        Valid URL
    """
    url = os.getenv(key, default)
    
    if required_schemes:
        if not any(url.startswith(scheme) for scheme in required_schemes):
            logger.warning(f"Environment variable {key}={url} does not start with required schemes {required_schemes}, using default: {default}")
            return default
            
    return url


def get_safe_project_root() -> str:
    """
    Safely get project root path with validation.
    
    Returns:
        Valid project root path
    """
    project_root = os.getenv('LUCID_PROJECT_ROOT')
    
    if not project_root:
        # Try to determine from current file location
        current_file = Path(__file__)
        project_root = str(current_file.parent.parent.parent)
    
    project_path = Path(project_root)
    
    if not project_path.exists():
        logger.error(f"Project root path does not exist: {project_root}")
        raise FileNotFoundError(f"Project root path does not exist: {project_root}")
        
    return str(project_path)


def safe_import_with_fallback(module_name: str, fallback_module: Optional[str] = None):
    """
    Safely import module with fallback.
    
    Args:
        module_name: Primary module to import
        fallback_module: Fallback module if primary fails
        
    Returns:
        Imported module
    """
    try:
        return __import__(module_name)
    except ImportError as e:
        if fallback_module:
            logger.warning(f"Failed to import {module_name}: {e}, trying fallback: {fallback_module}")
            try:
                return __import__(fallback_module)
            except ImportError as fallback_e:
                logger.error(f"Failed to import both {module_name} and {fallback_module}: {fallback_e}")
                raise
        else:
            logger.error(f"Failed to import {module_name}: {e}")
            raise


def validate_required_env_vars(required_vars: List[str]) -> None:
    """
    Validate that required environment variables are set.
    
    Args:
        required_vars: List of required environment variable names
        
    Raises:
        ValueError: If any required variables are missing
    """
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Required environment variables not set: {', '.join(missing_vars)}")


def get_env_summary() -> dict:
    """
    Get summary of environment variables (without sensitive values).
    
    Returns:
        Dictionary with environment variable summary
    """
    sensitive_keys = ['password', 'secret', 'key', 'token', 'auth', 'credential']
    
    summary = {}
    for key, value in os.environ.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            summary[key] = "***REDACTED***"
        else:
            summary[key] = value
            
    return summary
