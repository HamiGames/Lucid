"""
RDP Controller Configuration Management
Uses Pydantic Settings for environment variable validation with YAML/JSON file support

Configuration is loaded from:
1. Environment variables (highest priority)
2. YAML configuration file (optional)
3. Pydantic field defaults (lowest priority)
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

try:
    import json
    JSON_AVAILABLE = True
except ImportError:
    JSON_AVAILABLE = False
    json = None

logger = logging.getLogger(__name__)


class RDPControllerSettings(BaseSettings):
    """Base settings for RDP Controller service"""
    
    # Service Configuration
    RDP_CONTROLLER_HOST: str = Field(default="0.0.0.0", description="Service bind address (always 0.0.0.0 for container)")
    RDP_CONTROLLER_PORT: int = Field(default=8092, description="Service port")
    RDP_CONTROLLER_URL: str = Field(default="", description="Service URL for service discovery")
    
    # Database Configuration (Required)
    MONGODB_URL: str = Field(default="", description="MongoDB connection URL")
    REDIS_URL: str = Field(default="", description="Redis connection URL")
    
    # Integration Service URLs (Optional)
    RDP_XRDP_URL: str = Field(default="", description="RDP XRDP service URL")
    RDP_SERVER_MANAGER_URL: str = Field(default="", description="RDP Server Manager service URL")
    RDP_MONITOR_URL: str = Field(default="", description="RDP Monitor service URL")
    SESSION_RECORDER_URL: str = Field(default="", description="Session Recorder service URL")
    SESSION_PROCESSOR_URL: str = Field(default="", description="Session Processor service URL")
    SESSION_API_URL: str = Field(default="", description="Session API service URL")
    SESSION_STORAGE_URL: str = Field(default="", description="Session Storage service URL")
    SESSION_PIPELINE_URL: str = Field(default="", description="Session Pipeline service URL")
    
    # Service Timeout Configuration
    SERVICE_TIMEOUT_SECONDS: float = Field(default=30.0, description="Service request timeout")
    SERVICE_RETRY_COUNT: int = Field(default=3, description="Number of retry attempts")
    SERVICE_RETRY_DELAY_SECONDS: float = Field(default=1.0, description="Delay between retries")
    
    # Environment
    LUCID_ENV: str = Field(default="production", description="Environment name")
    LUCID_PLATFORM: str = Field(default="arm64", description="Platform architecture")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid", description="Project root directory")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Storage Paths
    LUCID_STORAGE_PATH: str = Field(default="/app/data", description="Storage base path")
    LUCID_LOGS_PATH: str = Field(default="/app/logs", description="Logs base path")
    
    # Authentication
    JWT_SECRET_KEY: str = Field(default="", description="JWT secret key for authentication")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    @field_validator('RDP_CONTROLLER_PORT')
    @classmethod
    def validate_port(cls, v: Union[str, int]) -> int:
        """Validate port number"""
        if isinstance(v, str):
            if not v:
                return 8092
            try:
                v = int(v)
            except ValueError:
                raise ValueError(f'Port must be an integer, got: {v}')
        if isinstance(v, int):
            if v < 1 or v > 65535:
                raise ValueError('Port must be between 1 and 65535')
            return v
        return v
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL doesn't use localhost"""
        if v:
            # Use regex to match localhost or 127.0.0.1 as whole words/hostnames
            # Pattern matches: localhost, 127.0.0.1, but not mylocalhost.com or 127.0.0.10
            localhost_pattern = re.compile(r'\blocalhost\b', re.IGNORECASE)
            ip_pattern = re.compile(r'\b127\.0\.0\.1\b')
            
            if localhost_pattern.search(v) or ip_pattern.search(v):
                raise ValueError("MONGODB_URL must not use localhost. Use service name (e.g., lucid-mongodb)")
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL doesn't use localhost"""
        if v:
            # Use regex to match localhost or 127.0.0.1 as whole words/hostnames
            # Pattern matches: localhost, 127.0.0.1, but not mylocalhost.com or 127.0.0.10
            localhost_pattern = re.compile(r'\blocalhost\b', re.IGNORECASE)
            ip_pattern = re.compile(r'\b127\.0\.0\.1\b')
            
            if localhost_pattern.search(v) or ip_pattern.search(v):
                raise ValueError("REDIS_URL must not use localhost. Use service name (e.g., lucid-redis)")
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'LOG_LEVEL must be one of {valid_levels}, got: {v}')
        return v.upper()


class RDPControllerConfig:
    """Configuration manager for RDP Controller"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Optional path to YAML/JSON configuration file
        """
        self.config_file = config_file or os.getenv(
            'RDP_CONTROLLER_CONFIG_FILE',
            '/app/session-controller/config.yaml'
        )
        self.settings = self._load_config()
        self._validate_config()
    
    def _load_config(self) -> RDPControllerSettings:
        """Load configuration from YAML/JSON file and environment variables"""
        config_dict = {}
        
        # Load from YAML/JSON file if available
        if os.path.exists(self.config_file):
            try:
                config_dict = self._load_config_file(self.config_file)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_file}: {e}")
        else:
            logger.info(f"Config file not found at {self.config_file}, using environment variables only")
        
        # Environment variables override file values (handled by Pydantic)
        try:
            settings = RDPControllerSettings(**config_dict)
            
            # Override with environment variables explicitly
            # Pydantic Settings automatically reads from environment, but we ensure priority
            env_overrides = {}
            for field_name in RDPControllerSettings.model_fields.keys():
                env_value = os.getenv(field_name)
                if env_value is not None:
                    env_overrides[field_name] = env_value
            
            if env_overrides:
                # Create new settings with env overrides
                settings_dict = settings.model_dump()
                settings_dict.update(env_overrides)
                settings = RDPControllerSettings(**settings_dict)
            
            return settings
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ValueError(f"Configuration loading failed: {str(e)}") from e
    
    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file"""
        path = Path(config_path)
        
        if not path.exists():
            return {}
        
        if path.suffix.lower() == '.yaml' or path.suffix.lower() == '.yml':
            if not YAML_AVAILABLE:
                logger.warning("YAML not available, cannot load YAML config file")
                return {}
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config_dict = yaml.safe_load(f) or {}
                return config_dict
            except Exception as e:
                logger.error(f"Failed to load YAML config: {e}")
                raise
        
        elif path.suffix.lower() == '.json':
            if not JSON_AVAILABLE:
                logger.warning("JSON not available, cannot load JSON config file")
                return {}
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f) or {}
                return config_dict
            except Exception as e:
                logger.error(f"Failed to load JSON config: {e}")
                raise
        
        else:
            logger.warning(f"Unsupported config file format: {path.suffix}")
            return {}
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.settings.MONGODB_URL:
            raise ValueError("MONGODB_URL is required")
        if not self.settings.REDIS_URL:
            raise ValueError("REDIS_URL is required")
        
        # Validate RDP_CONTROLLER_URL is set if not default
        if not self.settings.RDP_CONTROLLER_URL:
            # Construct from host and port
            host = self.settings.RDP_CONTROLLER_HOST
            port = self.settings.RDP_CONTROLLER_PORT
            # For service discovery, use service name, not bind address
            service_host = os.getenv('RDP_CONTROLLER_HOST', 'rdp-controller')
            if service_host == '0.0.0.0':
                service_host = 'rdp-controller'
            self.settings.RDP_CONTROLLER_URL = f"http://{service_host}:{port}"
    
    def get_controller_config_dict(self) -> Dict[str, Any]:
        """Get controller configuration as dictionary"""
        return {
            "host": self.settings.RDP_CONTROLLER_HOST,
            "port": self.settings.RDP_CONTROLLER_PORT,
            "url": self.settings.RDP_CONTROLLER_URL,
            "log_level": self.settings.LOG_LEVEL,
            "storage_path": self.settings.LUCID_STORAGE_PATH,
            "logs_path": self.settings.LUCID_LOGS_PATH,
        }
    
    def get_integration_config_dict(self) -> Dict[str, Any]:
        """Get integration service configuration as dictionary"""
        return {
            "rdp_xrdp_url": self.settings.RDP_XRDP_URL,
            "rdp_server_manager_url": self.settings.RDP_SERVER_MANAGER_URL,
            "rdp_monitor_url": self.settings.RDP_MONITOR_URL,
            "session_recorder_url": self.settings.SESSION_RECORDER_URL,
            "session_processor_url": self.settings.SESSION_PROCESSOR_URL,
            "session_api_url": self.settings.SESSION_API_URL,
            "session_storage_url": self.settings.SESSION_STORAGE_URL,
            "session_pipeline_url": self.settings.SESSION_PIPELINE_URL,
            "service_timeout": self.settings.SERVICE_TIMEOUT_SECONDS,
            "service_retry_count": self.settings.SERVICE_RETRY_COUNT,
            "service_retry_delay": self.settings.SERVICE_RETRY_DELAY_SECONDS,
        }


def load_config(config_file: Optional[str] = None) -> RDPControllerConfig:
    """
    Load configuration with fallback to defaults
    
    Args:
        config_file: Optional path to YAML/JSON configuration file
        
    Returns:
        RDPControllerConfig instance
    """
    try:
        config = RDPControllerConfig(config_file=config_file)
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        raise

