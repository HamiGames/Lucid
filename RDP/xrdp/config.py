#!/usr/bin/env python3
"""
Lucid XRDP Configuration Management
Configuration management for XRDP service
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


class XRDPAPISettings(BaseSettings):
    """XRDP API configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-rdp-xrdp"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Network Configuration (from docker-compose.application.yml)
    # Note: RDP_XRDP_HOST is service name, XRDP_PORT is service port
    HOST: str = "0.0.0.0"  # Bind address (always 0.0.0.0 for container binding)
    PORT: int = 3389  # Default port (overridden by XRDP_PORT from docker-compose)
    RDP_XRDP_HOST: str = ""  # From docker-compose: RDP_XRDP_HOST (service name, not bind address)
    XRDP_PORT: str = ""  # From docker-compose: XRDP_PORT (string, converted to int)
    RDP_XRDP_URL: str = ""  # From docker-compose: RDP_XRDP_URL (e.g., http://rdp-xrdp:3389)
    
    # Database Configuration (from .env.foundation, .env.core)
    MONGODB_URL: str = ""  # Required from environment: MONGODB_URL
    REDIS_URL: str = ""  # Required from environment: REDIS_URL
    
    # Integration Service URLs (from .env.application, .env.core)
    API_GATEWAY_URL: Optional[str] = Field(default=None, description="API Gateway URL")
    AUTH_SERVICE_URL: Optional[str] = Field(default=None, description="Auth Service URL")
    
    # Storage Configuration (use volume mount paths from docker-compose)
    CONFIG_STORAGE_PATH: str = "/app/config"  # Volume: /data/rdp-xrdp/config:/app/config:rw
    LOG_STORAGE_PATH: str = "/app/logs"  # Volume: /logs/rdp-xrdp:/app/logs:rw
    TEMP_STORAGE_PATH: str = "/tmp/xrdp"  # tmpfs mount: /tmp:size=100m
    
    # XRDP Service Configuration
    MAX_XRDP_PROCESSES: int = Field(default=10, description="Maximum concurrent XRDP processes")
    PROCESS_TIMEOUT: int = Field(default=30, description="Process timeout in seconds")
    
    # CORS Configuration (from .env.application)
    CORS_ORIGINS: str = "*"  # From environment: CORS_ORIGINS (comma-separated list, default: "*")
    
    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = 30
    HEALTH_CHECK_ENABLED: bool = True
    
    @field_validator('PORT', 'XRDP_PORT', mode='before')
    @classmethod
    def validate_port(cls, v):
        """Convert XRDP_PORT string to int and validate port range"""
        if isinstance(v, str):
            if not v:
                return 3389  # Default port
            try:
                v = int(v)
            except ValueError:
                raise ValueError(f'Port must be an integer, got: {v}')
        if isinstance(v, int):
            if v < 1 or v > 65535:
                raise ValueError('Port must be between 1 and 65535')
            return v
        return v
    
    @field_validator('MAX_XRDP_PROCESSES')
    @classmethod
    def validate_max_processes(cls, v):
        if v < 1 or v > 100:
            raise ValueError('MAX_XRDP_PROCESSES must be between 1 and 100')
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'LOG_LEVEL must be one of {allowed}')
        return v.upper()
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v):
        """Validate MongoDB URL"""
        if not v:
            raise ValueError("MONGODB_URL is required but not set")
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError("MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)")
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v):
        """Validate Redis URL"""
        if not v:
            raise ValueError("REDIS_URL is required but not set")
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError("REDIS_URL must not use localhost - use service name (e.g., lucid-redis)")
        return v
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )


class XRDPAPIConfig:
    """Configuration manager for XRDP API"""
    
    def __init__(self, settings: Optional[XRDPAPISettings] = None, config_file: Optional[str] = None):
        """
        Initialize XRDPAPIConfig.
        
        Args:
            settings: Optional XRDPAPISettings instance. If not provided, will load from YAML and environment variables.
            config_file: Optional path to YAML configuration file. Only used if settings is None.
        """
        try:
            if settings is None:
                # Load configuration from YAML and environment variables
                self.settings = load_config(config_file)
            else:
                self.settings = settings
            
            # Validate critical environment variables
            self._validate_required_env_vars()
            
            # Override PORT from XRDP_PORT if provided (HOST always stays 0.0.0.0)
            # RDP_XRDP_HOST is the service name for URLs, not the bind address
            if hasattr(self.settings, 'XRDP_PORT') and self.settings.XRDP_PORT:
                try:
                    port_value = int(self.settings.XRDP_PORT) if isinstance(self.settings.XRDP_PORT, str) else self.settings.XRDP_PORT
                    self.settings.PORT = port_value
                except (ValueError, TypeError):
                    logger.warning(f"Invalid XRDP_PORT value: {self.settings.XRDP_PORT}, using default {self.settings.PORT}")
            
            logger.info(f"XRDP API Configuration loaded: {self.settings.SERVICE_NAME} v{self.settings.SERVICE_VERSION}")
            
        except Exception as e:
            logger.error(f"Failed to initialize XRDP API configuration: {e}", exc_info=True)
            raise
    
    def _validate_required_env_vars(self):
        """Validate that required environment variables are set"""
        # MONGODB_URL and REDIS_URL validation is handled by Pydantic validators
        # But we need to check if they're empty
        if not self.settings.MONGODB_URL:
            raise ValueError("MONGODB_URL is required but not set")
        if not self.settings.REDIS_URL:
            raise ValueError("REDIS_URL is required but not set")
    
    def get_xrdp_config_dict(self) -> Dict[str, Any]:
        """Get XRDP service configuration as dictionary"""
        return {
            "max_processes": self.settings.MAX_XRDP_PROCESSES,
            "process_timeout": self.settings.PROCESS_TIMEOUT,
            "config_path": self.settings.CONFIG_STORAGE_PATH,
            "log_path": self.settings.LOG_STORAGE_PATH,
            "session_path": os.path.join(self.settings.CONFIG_STORAGE_PATH, "sessions"),
        }
    
    def get_mongodb_url(self) -> str:
        """Get MongoDB URL"""
        return self.settings.MONGODB_URL
    
    def get_redis_url(self) -> str:
        """Get Redis URL"""
        return self.settings.REDIS_URL
    
    def get_cors_origins(self) -> list:
        """Get CORS origins from configuration"""
        if self.settings.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.settings.CORS_ORIGINS.split(",") if origin.strip()]


def load_config(config_file: Optional[str] = None) -> XRDPAPISettings:
    """
    Load configuration from YAML file and environment variables.
    
    Configuration loading priority (highest to lowest):
    1. Environment variables (highest priority - override everything)
    2. YAML configuration file values
    3. Pydantic field defaults (lowest priority)
    
    Args:
        config_file: Optional path to YAML configuration file. If not provided,
                     will look for 'config.yaml' in the xrdp directory.
        
    Returns:
        Loaded XRDPAPISettings object with environment variables overriding YAML values
        
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
                Path(__file__).parent.parent / "xrdp" / "config.yaml",  # Alternative path
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
                config = XRDPAPISettings.model_validate(yaml_data)
                
                # Step 2: Create config normally to get environment variable values
                env_config = XRDPAPISettings()
                
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
                config = XRDPAPISettings()
        else:
            # Load from environment variables and defaults only
            config = XRDPAPISettings()
        
        logger.info("Configuration loaded successfully")
        return config
        
    except FileNotFoundError:
        # Re-raise file not found errors
        raise
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}", exc_info=True)
        raise ValueError(f"Configuration loading failed: {str(e)}") from e
