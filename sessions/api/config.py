#!/usr/bin/env python3
"""
Lucid Session API Configuration
Configuration management for session API service
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings
import logging

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

class SessionAPISettings(BaseSettings):
    """Session API configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-session-api"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Network Configuration
    SESSION_API_HOST: str = "0.0.0.0"  # Bind address (always 0.0.0.0 in container)
    SESSION_API_PORT: int = 8087
    SESSION_API_URL: str = ""  # Service URL (from docker-compose)
    SESSION_API_WORKERS: int = 1
    
    # Database Configuration (from .env.foundation, .env.core)
    MONGODB_URL: str = ""  # Required from environment: MONGODB_URL
    REDIS_URL: str = ""  # Required from environment: REDIS_URL
    ELASTICSEARCH_URL: str = ""  # Optional from environment: ELASTICSEARCH_URL
    
    # Integration Configuration
    API_GATEWAY_URL: str = ""  # Optional from environment
    BLOCKCHAIN_ENGINE_URL: str = ""  # Optional from environment
    AUTH_SERVICE_URL: str = ""  # Optional from environment
    
    # CORS Configuration
    CORS_ORIGINS: str = "*"  # Comma-separated list or "*" for all
    
    # Storage Configuration
    CHUNK_STORAGE_PATH: str = "/app/data/chunks"
    SESSION_STORAGE_PATH: str = "/app/data/sessions"
    TEMP_STORAGE_PATH: str = "/tmp/api"
    
    # Timeout Configuration
    SERVICE_TIMEOUT_SECONDS: int = 30
    SERVICE_RETRY_COUNT: int = 3
    SERVICE_RETRY_DELAY_SECONDS: float = 1.0
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL"""
        if not v:
            raise ValueError("MONGODB_URL is required but not set")
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError("MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)")
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL"""
        if not v:
            raise ValueError("REDIS_URL is required but not set")
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError("REDIS_URL must not use localhost - use service name (e.g., lucid-redis)")
        return v
    
    @field_validator('SESSION_API_PORT')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port number"""
        if not (1 <= v <= 65535):
            raise ValueError(f"SESSION_API_PORT must be between 1 and 65535, got {v}")
        return v
    
    class Config:
        env_file = ['.env.application', '.env.core', '.env.secrets', '.env.foundation']
        case_sensitive = True
        extra = 'ignore'

class SessionAPIConfig:
    """Session API configuration manager"""
    
    def __init__(self, settings: Optional[SessionAPISettings] = None, config_file: Optional[str] = None):
        """
        Initialize SessionAPIConfig.
        
        Args:
            settings: Optional SessionAPISettings instance. If not provided, will load from YAML and environment variables.
            config_file: Optional path to YAML configuration file. Only used if settings is None.
        """
        if settings is None:
            # Load configuration from YAML and environment variables
            self.settings = load_config(config_file)
        else:
            self.settings = settings
        logger.info(f"Session API Configuration loaded: {self.settings.SERVICE_NAME} v{self.settings.SERVICE_VERSION}")
    
    def validate_configuration(self) -> bool:
        """Validate configuration"""
        try:
            # Validate required settings
            if not self.settings.MONGODB_URL:
                logger.error("MONGODB_URL is required but not set")
                return False
            
            if not self.settings.REDIS_URL:
                logger.error("REDIS_URL is required but not set")
                return False
            
            logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_cors_origins(self) -> list:
        """Get CORS origins from configuration"""
        if self.settings.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.settings.CORS_ORIGINS.split(",") if origin.strip()]


def load_config(config_file: Optional[str] = None) -> SessionAPISettings:
    """
    Load configuration from YAML file and environment variables.
    
    Configuration loading priority (highest to lowest):
    1. Environment variables (highest priority - override everything)
    2. YAML configuration file values
    3. Pydantic field defaults (lowest priority)
    
    Args:
        config_file: Optional path to YAML configuration file. If not provided,
                     will look for 'config.yaml' in the api directory.
        
    Returns:
        Loaded SessionAPISettings object with environment variables overriding YAML values
        
    Raises:
        FileNotFoundError: If config_file is provided but doesn't exist
        ValueError: If configuration validation fails
        ImportError: If PyYAML is not available (should not happen if requirements are installed)
    """
    try:
        yaml_data: Dict[str, Any] = {}
        yaml_file_path: Optional[Path] = None
        
        # Determine YAML file path
        if config_file:
            yaml_file_path = Path(config_file)
        else:
            # Try default locations
            default_locations = [
                Path(__file__).parent / "config.yaml",  # Same directory as config.py
                Path(__file__).parent.parent / "api" / "config.yaml",  # Alternative path
            ]
            for loc in default_locations:
                if loc.exists():
                    yaml_file_path = loc
                    break
        
        # Load YAML file if it exists
        if yaml_file_path and yaml_file_path.exists():
            if not YAML_AVAILABLE:
                logger.warning(f"PyYAML not available, skipping YAML file {yaml_file_path}")
            else:
                try:
                    with open(yaml_file_path, 'r', encoding='utf-8') as f:
                        yaml_data = yaml.safe_load(f) or {}
                    logger.info(f"Loaded YAML configuration from {yaml_file_path}")
                    
                    # Filter out empty string values from YAML (they should come from env vars)
                    # Empty strings in YAML indicate "use environment variable", so we remove them
                    # and let Pydantic Settings load them from environment variables instead
                    yaml_data = {k: v for k, v in yaml_data.items() if v != ""}
                    
                except Exception as e:
                    logger.warning(f"Failed to load YAML configuration from {yaml_file_path}: {str(e)}")
                    logger.warning("Continuing with environment variables and defaults only")
                    yaml_data = {}
        elif config_file:
            # User specified a file but it doesn't exist - this is an error
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        else:
            logger.debug("No YAML configuration file found, using environment variables and defaults only")
        
        # Create configuration object
        # Priority: Environment variables (highest) > YAML values > Field defaults (lowest)
        # Strategy: Create config from YAML, then override with environment variables
        
        if yaml_data:
            try:
                # Step 1: Create config from YAML data (YAML provides defaults)
                config = SessionAPISettings.model_validate(yaml_data)
                
                # Step 2: Create config normally to get environment variable values
                env_config = SessionAPISettings()
                
                # Step 3: Override YAML config with environment variable values
                # Environment variables take highest priority
                env_dict = env_config.model_dump()
                yaml_dict = config.model_dump()
                
                # For each field, if env_config value differs from yaml_config value,
                # use the env value (environment variable was set)
                for key in env_dict.keys():
                    env_value = env_dict[key]
                    yaml_value = yaml_dict.get(key)
                    
                    # If values differ, environment variable was set - use it
                    if env_value != yaml_value:
                        try:
                            setattr(config, key, env_value)
                        except Exception as e:
                            logger.debug(f"Could not override {key} with environment variable: {str(e)}")
                
            except Exception as e:
                logger.warning(f"Error merging YAML with environment variables: {str(e)}")
                logger.warning("Falling back to environment variables and defaults only")
                config = SessionAPISettings()
        else:
            # Load from environment variables and defaults only
            config = SessionAPISettings()
        
        logger.info("Configuration loaded successfully")
        return config
        
    except FileNotFoundError:
        # Re-raise file not found errors
        raise
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise


def create_default_config_file(config_path: str = "config.yaml"):
    """
    Create a default configuration file.
    
    Args:
        config_path: Path to create the configuration file
        
    Raises:
        ImportError: If PyYAML is not available
        IOError: If file cannot be written
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML is required to create configuration files. Install it with: pip install PyYAML")
    
    default_config = {
        "SERVICE_NAME": "lucid-session-api",
        "SERVICE_VERSION": "1.0.0",
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "SESSION_API_HOST": "0.0.0.0",
        "SESSION_API_PORT": 8087,  # Default port (override with SESSION_API_PORT env var)
        "SESSION_API_URL": "",  # Set via SESSION_API_URL env var
        "SESSION_API_WORKERS": 1,
        "MONGODB_URL": "",  # Must be set from MONGODB_URL env var (required)
        "REDIS_URL": "",  # Must be set from REDIS_URL env var (required)
        "ELASTICSEARCH_URL": "",  # Set via ELASTICSEARCH_URL env var (optional)
        "API_GATEWAY_URL": "",  # Set via API_GATEWAY_URL env var (optional)
        "BLOCKCHAIN_ENGINE_URL": "",  # Set via BLOCKCHAIN_ENGINE_URL env var (optional)
        "AUTH_SERVICE_URL": "",  # Set via AUTH_SERVICE_URL env var (optional)
        "CORS_ORIGINS": "*",
        "CHUNK_STORAGE_PATH": "/app/data/chunks",
        "SESSION_STORAGE_PATH": "/app/data/sessions",
        "TEMP_STORAGE_PATH": "/tmp/api",
        "SERVICE_TIMEOUT_SECONDS": 30,
        "SERVICE_RETRY_COUNT": 3,
        "SERVICE_RETRY_DELAY_SECONDS": 1.0
    }
    
    try:
        config_file_path = Path(config_path)
        config_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file_path, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Created default configuration file: {config_path}")
        
    except Exception as e:
        logger.error(f"Failed to create configuration file: {str(e)}")
        raise


# Global configuration instance
_config: Optional[SessionAPISettings] = None


def get_config() -> SessionAPISettings:
    """
    Get the global configuration instance.
    
    Returns:
        Global SessionAPISettings instance
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(new_config: SessionAPISettings):
    """
    Set the global configuration instance.
    
    Args:
        new_config: New SessionAPISettings instance
    """
    global _config
    _config = new_config
    logger.info("Global configuration updated")

