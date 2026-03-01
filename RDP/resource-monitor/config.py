#!/usr/bin/env python3
"""
Lucid RDP Resource Monitor Configuration
Configuration management for RDP resource monitoring service
"""

import os
from typing import Dict, Any, Optional
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


class MonitorSettings(BaseSettings):
    """RDP Resource Monitor configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-rdp-monitor"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Network Configuration (from docker-compose.application.yml)
    # Note: RDP_MONITOR_HOST is service name, RDP_MONITOR_PORT is service port
    HOST: str = "0.0.0.0"  # Bind address (always 0.0.0.0 for container binding)
    PORT: int = 8093  # Default port (overridden by RDP_MONITOR_PORT from docker-compose)
    RDP_MONITOR_HOST: str = ""  # From docker-compose: RDP_MONITOR_HOST (service name, not bind address)
    RDP_MONITOR_PORT: str = ""  # From docker-compose: RDP_MONITOR_PORT (string, converted to int)
    RDP_MONITOR_URL: str = ""  # From docker-compose: RDP_MONITOR_URL (e.g., http://rdp-monitor:8093)
    
    # Database Configuration (from .env.foundation, .env.core)
    MONGODB_URL: str = ""  # Required from environment: MONGODB_URL
    REDIS_URL: str = ""  # Optional from environment: REDIS_URL
    
    # Storage Configuration (use volume mount paths from docker-compose)
    LOG_STORAGE_PATH: str = "/app/logs"  # Volume: /logs/rdp-monitor:/app/logs:rw
    TEMP_STORAGE_PATH: str = "/tmp/monitor"  # tmpfs mount: /tmp:size=100m
    
    # Monitoring Configuration
    MONITORING_INTERVAL: int = 30  # seconds - interval for collecting metrics
    COLLECTION_INTERVAL: int = 30  # seconds - interval for metrics collection
    METRICS_HISTORY_LIMIT: int = 100  # Maximum number of metrics per session to keep in memory
    METRICS_CLEANUP_HOURS: int = 24  # Hours of metrics history to keep
    
    # Alert Thresholds Configuration
    CPU_THRESHOLD_PERCENT: float = 80.0  # CPU usage alert threshold
    MEMORY_THRESHOLD_PERCENT: float = 80.0  # Memory usage alert threshold
    DISK_THRESHOLD_PERCENT: float = 90.0  # Disk usage alert threshold
    NETWORK_BANDWIDTH_THRESHOLD_MB: float = 1000.0  # Network bandwidth alert threshold (MB/s)
    
    # Metrics Configuration
    METRICS_ENABLED: bool = True
    PROMETHEUS_ENABLED: bool = True
    EXPORT_METRICS_ENDPOINT: bool = True
    
    # Performance Configuration
    MAX_CONCURRENT_SESSIONS: int = 100  # Maximum number of sessions to monitor concurrently
    SESSION_METRICS_CACHE_SIZE: int = 1000  # Maximum cached metrics per session
    
    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = 30  # seconds
    HEALTH_CHECK_ENABLED: bool = True
    
    # Integration Service URLs (from .env.application, .env.core)
    RDP_SERVER_MANAGER_URL: str = ""  # From environment: RDP_SERVER_MANAGER_URL (e.g., http://rdp-server-manager:8081)
    RDP_XRDP_URL: str = ""  # From environment: RDP_XRDP_URL (e.g., http://rdp-xrdp:3389)
    RDP_CONTROLLER_URL: str = ""  # From environment: RDP_CONTROLLER_URL (e.g., http://rdp-controller:8092)
    
    # Integration Service Timeout Configuration
    SERVICE_TIMEOUT_SECONDS: int = 30  # Default timeout for service calls
    SERVICE_RETRY_COUNT: int = 3  # Default retry count for service calls
    SERVICE_RETRY_DELAY_SECONDS: float = 1.0  # Default delay between retries
    
    # CORS Configuration (from .env.application)
    CORS_ORIGINS: str = "*"  # From environment: CORS_ORIGINS (comma-separated list, default: "*")
    
    @field_validator('MONITORING_INTERVAL')
    @classmethod
    def validate_monitoring_interval(cls, v):
        if v < 1 or v > 3600:
            raise ValueError('Monitoring interval must be between 1 and 3600 seconds')
        return v
    
    @field_validator('COLLECTION_INTERVAL')
    @classmethod
    def validate_collection_interval(cls, v):
        if v < 1 or v > 3600:
            raise ValueError('Collection interval must be between 1 and 3600 seconds')
        return v
    
    @field_validator('CPU_THRESHOLD_PERCENT', 'MEMORY_THRESHOLD_PERCENT', 'DISK_THRESHOLD_PERCENT')
    @classmethod
    def validate_threshold_percent(cls, v):
        if v < 0 or v > 100:
            raise ValueError('Threshold percentage must be between 0 and 100')
        return v
    
    @field_validator('MAX_CONCURRENT_SESSIONS')
    @classmethod
    def validate_max_sessions(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('Max concurrent sessions must be between 1 and 1000')
        return v
    
    @field_validator('HEALTH_CHECK_INTERVAL', mode='before')
    @classmethod
    def validate_health_check_interval(cls, v):
        """Convert '30s' format to integer seconds"""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            # Strip 's' suffix if present (e.g., '30s' -> '30')
            v = v.rstrip('s').strip()
            try:
                return int(v)
            except ValueError:
                raise ValueError(f'HEALTH_CHECK_INTERVAL must be an integer or integer string (e.g., "30" or "30s"), got: {v}')
        raise ValueError(f'HEALTH_CHECK_INTERVAL must be an integer or string, got: {type(v)}')
    
    model_config = {
        # pydantic-settings will read from environment variables
        # docker-compose provides: .env.secrets, .env.core, .env.application, .env.foundation
        "env_file": None,  # Don't read .env file directly - use environment variables from docker-compose
        "case_sensitive": True,
        "env_file_encoding": "utf-8"
    }
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v):
        # MongoDB is optional for rdp-monitor, but if provided, validate it
        if v and v != "":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError('MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)')
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v):
        # Redis is optional for rdp-monitor, but if provided, validate it
        if v and v != "":
            if "localhost" in v or "127.0.0.1" in v:
                raise ValueError('REDIS_URL must not use localhost - use service name (e.g., lucid-redis)')
        return v


class MonitorConfig:
    """
    Main monitor configuration class
    Manages all monitor-related configuration
    """
    
    def __init__(self, settings: Optional[MonitorSettings] = None, config_file: Optional[str] = None):
        """
        Initialize MonitorConfig.
        
        Args:
            settings: Optional MonitorSettings instance. If not provided, will load from YAML and environment variables.
            config_file: Optional path to YAML configuration file. Only used if settings is None.
        """
        try:
            if settings is None:
                # Load configuration from YAML and environment variables
                self.settings = load_config(config_file)
            else:
                self.settings = settings
            
            # Validate critical environment variables (if required)
            self._validate_required_env_vars()
            
            # Override PORT from RDP_MONITOR_PORT if provided (HOST always stays 0.0.0.0)
            # RDP_MONITOR_HOST is the service name for URLs, not the bind address
            if hasattr(self.settings, 'RDP_MONITOR_PORT') and self.settings.RDP_MONITOR_PORT:
                try:
                    self.settings.PORT = int(self.settings.RDP_MONITOR_PORT)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid RDP_MONITOR_PORT value: {self.settings.RDP_MONITOR_PORT}, using default {self.settings.PORT}")
            
            # Integration service URLs must come from environment variables (no hardcoded defaults)
            # Pydantic Settings already loaded them from environment, so just validate they're not empty if required
            # Note: These are optional for rdp-monitor, so empty strings are acceptable
            
            logger.info("Monitor configuration initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitor configuration: {e}", exc_info=True)
            raise
    
    def _validate_required_env_vars(self):
        """Validate that required environment variables are set"""
        # MongoDB and Redis are optional for rdp-monitor
        # Only validate if they're provided
        if self.settings.MONGODB_URL and self.settings.MONGODB_URL != "":
            if "localhost" in self.settings.MONGODB_URL or "127.0.0.1" in self.settings.MONGODB_URL:
                raise ValueError("MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)")
        
        if self.settings.REDIS_URL and self.settings.REDIS_URL != "":
            if "localhost" in self.settings.REDIS_URL or "127.0.0.1" in self.settings.REDIS_URL:
                raise ValueError("REDIS_URL must not use localhost - use service name (e.g., lucid-redis)")
    
    def get_alert_thresholds(self) -> Dict[str, float]:
        """Get alert thresholds as a dictionary"""
        return {
            "cpu_percent": self.settings.CPU_THRESHOLD_PERCENT,
            "memory_percent": self.settings.MEMORY_THRESHOLD_PERCENT,
            "disk_percent": self.settings.DISK_THRESHOLD_PERCENT,
            "network_bandwidth": self.settings.NETWORK_BANDWIDTH_THRESHOLD_MB
        }
    
    def get_service_config(self) -> Dict[str, Any]:
        """Get service configuration as a dictionary"""
        return {
            "name": self.settings.SERVICE_NAME,
            "version": self.settings.SERVICE_VERSION,
            "debug": self.settings.DEBUG,
            "log_level": self.settings.LOG_LEVEL,
            "host": self.settings.HOST,
            "port": self.settings.PORT
        }
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration as a dictionary"""
        return {
            "monitoring_interval": self.settings.MONITORING_INTERVAL,
            "collection_interval": self.settings.COLLECTION_INTERVAL,
            "metrics_history_limit": self.settings.METRICS_HISTORY_LIMIT,
            "metrics_cleanup_hours": self.settings.METRICS_CLEANUP_HOURS,
            "max_concurrent_sessions": self.settings.MAX_CONCURRENT_SESSIONS,
            "session_metrics_cache_size": self.settings.SESSION_METRICS_CACHE_SIZE
        }


def load_config(config_file: Optional[str] = None) -> MonitorSettings:
    """
    Load configuration from YAML file and environment variables.
    
    Configuration loading priority (highest to lowest):
    1. Environment variables (highest priority - override everything)
    2. YAML configuration file values
    3. Pydantic field defaults (lowest priority)
    
    Args:
        config_file: Optional path to YAML configuration file. If not provided,
                     will look for 'config.yaml' in the resource-monitor directory.
        
    Returns:
        Loaded MonitorSettings object with environment variables overriding YAML values
        
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
                Path(__file__).parent.parent / "resource-monitor" / "config.yaml",  # Alternative path
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
                config = MonitorSettings.model_validate(yaml_data)
                
                # Step 2: Create config normally to get environment variable values
                env_config = MonitorSettings()
                
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
                config = MonitorSettings()
        else:
            # Load from environment variables and defaults only
            config = MonitorSettings()
        
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
        "SERVICE_NAME": "lucid-rdp-monitor",
        "SERVICE_VERSION": "1.0.0",
        "DEBUG": False,
        "LOG_LEVEL": "INFO",
        "HOST": "0.0.0.0",
        "PORT": 8093,  # Default port (override with RDP_MONITOR_PORT env var)
        "RDP_MONITOR_HOST": "",  # Set via RDP_MONITOR_HOST env var
        "RDP_MONITOR_PORT": "",  # Set via RDP_MONITOR_PORT env var
        "RDP_MONITOR_URL": "",  # Set via RDP_MONITOR_URL env var
        "MONGODB_URL": "",  # Must be set from MONGODB_URL env var (optional)
        "REDIS_URL": "",  # Must be set from REDIS_URL env var (optional)
        "LOG_STORAGE_PATH": "/app/logs",
        "TEMP_STORAGE_PATH": "/tmp/monitor",
        "MONITORING_INTERVAL": 30,
        "COLLECTION_INTERVAL": 30,
        "METRICS_HISTORY_LIMIT": 100,
        "METRICS_CLEANUP_HOURS": 24,
        "CPU_THRESHOLD_PERCENT": 80.0,
        "MEMORY_THRESHOLD_PERCENT": 80.0,
        "DISK_THRESHOLD_PERCENT": 90.0,
        "NETWORK_BANDWIDTH_THRESHOLD_MB": 1000.0,
        "METRICS_ENABLED": True,
        "PROMETHEUS_ENABLED": True,
        "EXPORT_METRICS_ENDPOINT": True,
        "MAX_CONCURRENT_SESSIONS": 100,
        "SESSION_METRICS_CACHE_SIZE": 1000,
        "HEALTH_CHECK_INTERVAL": 30,
        "HEALTH_CHECK_ENABLED": True,
        "RDP_SERVER_MANAGER_URL": "",  # Set via RDP_SERVER_MANAGER_URL env var
        "RDP_XRDP_URL": "",  # Set via RDP_XRDP_URL env var
        "RDP_CONTROLLER_URL": "",  # Set via RDP_CONTROLLER_URL env var
        "SERVICE_TIMEOUT_SECONDS": 30,
        "SERVICE_RETRY_COUNT": 3,
        "SERVICE_RETRY_DELAY_SECONDS": 1.0,
        "CORS_ORIGINS": "*"
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
_config: Optional[MonitorSettings] = None


def get_config() -> MonitorSettings:
    """
    Get the global configuration instance.
    
    Returns:
        Global MonitorSettings instance
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config


def set_config(new_config: MonitorSettings):
    """
    Set the global configuration instance.
    
    Args:
        new_config: New MonitorSettings instance
    """
    global _config
    _config = new_config
    logger.info("Global configuration updated")

