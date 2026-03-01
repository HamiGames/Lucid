"""
Lucid Core Configuration Manager
Centralized configuration management for all Lucid services and components.
Provides secure, validated, and environment-aware configuration handling.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import secrets
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Logging level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = "localhost"
    port: int = 27017
    name: str = "lucid"
    username: str = "lucid"
    password: str = "lucid"
    auth_source: str = "admin"
    replica_set: Optional[str] = None
    ssl: bool = False
    max_pool_size: int = 100
    min_pool_size: int = 10
    max_idle_time_ms: int = 30000
    connect_timeout_ms: int = 20000
    server_selection_timeout_ms: int = 5000


@dataclass
class RedisConfig:
    """Redis configuration settings."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    retry_on_timeout: bool = True


@dataclass
class TorConfig:
    """Tor network configuration settings."""
    enabled: bool = True
    socks_port: int = 9050
    control_port: int = 9051
    control_password: Optional[str] = None
    data_directory: str = "/var/lib/tor"
    log_level: str = "notice"
    hidden_service_dir: str = "/var/lib/tor/hidden_service"
    hidden_service_port: int = 8080


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    encryption_key: Optional[str] = None
    jwt_secret: Optional[str] = None
    session_secret: Optional[str] = None
    bcrypt_rounds: int = 12
    max_login_attempts: int = 5
    lockout_duration: int = 300  # 5 minutes
    password_min_length: int = 8
    require_2fa: bool = False
    ssl_required: bool = True
    cors_origins: List[str] = field(default_factory=list)


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    enabled: bool = True
    prometheus_port: int = 9090
    jaeger_endpoint: Optional[str] = None
    log_level: LogLevel = LogLevel.INFO
    metrics_interval: int = 30
    health_check_interval: int = 30
    alert_webhook_url: Optional[str] = None


class ServiceConfig(BaseModel):
    """Base configuration model for services."""
    name: str
    port: int
    host: str = "0.0.0.0"
    workers: int = 1
    reload: bool = False
    log_level: LogLevel = LogLevel.INFO
    
    class Config:
        use_enum_values = True


class LucidSettings(BaseSettings):
    """Main Lucid application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application settings
    app_name: str = "Lucid"
    app_version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Service configurations
    api_port: int = 8000
    gui_port: int = 8083
    blockchain_port: int = 8080
    node_port: int = 8084
    rdp_port: int = 3389
    
    # Database settings
    mongodb_url: str = Field(default_factory=lambda: os.getenv("MONGODB_URL") or os.getenv("MONGO_URL") or "")
    redis_url: str = "redis://localhost:6379/0"
    
    # Security settings
    secret_key: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    encryption_key: str = Field(default_factory=lambda: Fernet.generate_key().decode())
    
    # Tor settings
    tor_enabled: bool = True
    tor_socks_port: int = 9050
    tor_control_port: int = 9051
    
    # Monitoring settings
    monitoring_enabled: bool = True
    prometheus_port: int = 9090
    
    # File paths
    config_dir: str = "/etc/lucid"
    data_dir: str = "/var/lib/lucid"
    log_dir: str = "/var/log/lucid"
    cache_dir: str = "/var/cache/lucid"
    
    @validator('environment')
    def validate_environment(cls, v):
        if v not in [e.value for e in Environment]:
            raise ValueError(f"Invalid environment: {v}")
        if not v:
            raise ValueError("MONGODB_URL/MONGO_URL must be set")
        return v
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters")
        return v


class ConfigurationManager:
    """Central configuration manager for Lucid application."""
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (YAML or JSON)
        """
        self.config_file = Path(config_file) if config_file else None
        self._settings: Optional[LucidSettings] = None
        self._database_config: Optional[DatabaseConfig] = None
        self._redis_config: Optional[RedisConfig] = None
        self._tor_config: Optional[TorConfig] = None
        self._security_config: Optional[SecurityConfig] = None
        self._monitoring_config: Optional[MonitoringConfig] = None
        self._service_configs: Dict[str, ServiceConfig] = {}
        self._encryption_key: Optional[bytes] = None
        self._logger = logging.getLogger(__name__)
        
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration from various sources."""
        try:
            # Load from environment variables and .env file
            self._settings = LucidSettings()
            
            # Load from configuration file if provided
            if self.config_file and self.config_file.exists():
                self._load_from_file()
            
            # Initialize component configurations
            self._initialize_component_configs()
            
            # Setup encryption
            self._setup_encryption()
            
            self._logger.info(f"Configuration loaded for {self._settings.environment} environment")
            
        except Exception as e:
            self._logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _load_from_file(self) -> None:
        """Load configuration from file."""
        if not self.config_file or not self.config_file.exists():
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                if self.config_file.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                elif self.config_file.suffix.lower() == '.json':
                    config_data = json.load(f)
                else:
                    self._logger.warning(f"Unsupported config file format: {self.config_file.suffix}")
                    return
            
            # Update settings with file data
            if config_data:
                for key, value in config_data.items():
                    if hasattr(self._settings, key):
                        setattr(self._settings, key, value)
                        
        except Exception as e:
            self._logger.error(f"Failed to load configuration from file {self.config_file}: {e}")
            raise
    
    def _initialize_component_configs(self) -> None:
        """Initialize component-specific configurations."""
        # Database configuration with safe port conversion
        try:
            mongodb_port = int(os.getenv('MONGODB_PORT', '27017'))
        except ValueError:
            self._logger.warning("Invalid MONGODB_PORT, using default: 27017")
            mongodb_port = 27017
            
        self._database_config = DatabaseConfig(
            host=os.getenv('MONGODB_HOST', 'localhost'),
            port=mongodb_port,
            name=os.getenv('MONGODB_NAME', 'lucid'),
            username=os.getenv('MONGODB_USERNAME', 'lucid'),
            password=os.getenv('MONGODB_PASSWORD', 'lucid'),
            auth_source=os.getenv('MONGODB_AUTH_SOURCE', 'admin')
        )
        
        # Redis configuration
        self._redis_config = RedisConfig(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=int(os.getenv('REDIS_DB', '0')),
            password=os.getenv('REDIS_PASSWORD')
        )
        
        # Tor configuration
        self._tor_config = TorConfig(
            enabled=os.getenv('TOR_ENABLED', 'true').lower() == 'true',
            socks_port=int(os.getenv('TOR_SOCKS_PORT', '9050')),
            control_port=int(os.getenv('TOR_CONTROL_PORT', '9051')),
            control_password=os.getenv('TOR_CONTROL_PASSWORD'),
            data_directory=os.getenv('TOR_DATA_DIR', '/var/lib/tor')
        )
        
        # Security configuration
        self._security_config = SecurityConfig(
            encryption_key=self._settings.encryption_key,
            jwt_secret=self._settings.secret_key,
            session_secret=self._settings.secret_key,
            ssl_required=self._settings.environment == Environment.PRODUCTION,
            cors_origins=os.getenv('CORS_ORIGINS', '').split(',') if os.getenv('CORS_ORIGINS') else []
        )
        
        # Monitoring configuration
        self._monitoring_config = MonitoringConfig(
            enabled=os.getenv('MONITORING_ENABLED', 'true').lower() == 'true',
            prometheus_port=int(os.getenv('PROMETHEUS_PORT', '9090')),
            jaeger_endpoint=os.getenv('JAEGER_ENDPOINT'),
            log_level=LogLevel(os.getenv('LOG_LEVEL', 'INFO'))
        )
        
        # Service configurations
        self._service_configs = {
            'api': ServiceConfig(name='api', port=self._settings.api_port),
            'gui': ServiceConfig(name='gui', port=self._settings.gui_port),
            'blockchain': ServiceConfig(name='blockchain', port=self._settings.blockchain_port),
            'node': ServiceConfig(name='node', port=self._settings.node_port),
            'rdp': ServiceConfig(name='rdp', port=self._settings.rdp_port)
        }
    
    def _setup_encryption(self) -> None:
        """Setup encryption key."""
        try:
            if self._settings.encryption_key:
                self._encryption_key = self._settings.encryption_key.encode()
            else:
                self._logger.warning("No encryption key provided, generating new one")
                from cryptography.fernet import Fernet
                key = Fernet.generate_key()
                self._encryption_key = key
        except Exception as e:
            self._logger.error(f"Failed to setup encryption: {e}")
            raise
    
    def get_settings(self) -> LucidSettings:
        """Get main application settings."""
        return self._settings
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self._database_config
    
    def get_redis_config(self) -> RedisConfig:
        """Get Redis configuration."""
        return self._redis_config
    
    def get_tor_config(self) -> TorConfig:
        """Get Tor configuration."""
        return self._tor_config
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self._security_config
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return self._monitoring_config
    
    def get_service_config(self, service_name: str) -> Optional[ServiceConfig]:
        """Get configuration for a specific service."""
        return self._service_configs.get(service_name)
    
    def get_all_service_configs(self) -> Dict[str, ServiceConfig]:
        """Get all service configurations."""
        return self._service_configs.copy()
    
    def get_encryption_key(self) -> bytes:
        """Get encryption key."""
        return self._encryption_key
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self._settings.environment == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self._settings.environment == Environment.DEVELOPMENT
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return getattr(self._settings, key, default)
    
    def set_config_value(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        if hasattr(self._settings, key):
            setattr(self._settings, key, value)
        else:
            self._logger.warning(f"Unknown configuration key: {key}")
    
    def save_configuration(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save current configuration to file."""
        if not file_path:
            file_path = self.config_file
        
        if not file_path:
            self._logger.warning("No file path provided for saving configuration")
            return
        
        try:
            file_path = Path(file_path)
            config_data = self._settings.dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False)
                elif file_path.suffix.lower() == '.json':
                    json.dump(config_data, f, indent=2)
                else:
                    raise ValueError(f"Unsupported file format: {file_path.suffix}")
            
            self._logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            self._logger.error(f"Failed to save configuration to {file_path}: {e}")
            raise
    
    def validate_configuration(self) -> bool:
        """Validate current configuration."""
        try:
            # Validate settings
            self._settings.model_validate(self._settings.dict())
            
            # Validate component configurations
            if not self._database_config:
                raise ValueError("Database configuration is missing")
            
            if not self._redis_config:
                raise ValueError("Redis configuration is missing")
            
            if not self._security_config:
                raise ValueError("Security configuration is missing")
            
            # Validate service configurations
            if not self._service_configs:
                raise ValueError("Service configurations are missing")
            
            self._logger.info("Configuration validation passed")
            return True
            
        except Exception as e:
            self._logger.error(f"Configuration validation failed: {e}")
            return False
    
    def reload_configuration(self) -> None:
        """Reload configuration from sources."""
        self._logger.info("Reloading configuration...")
        self._load_configuration()
    
    def get_connection_strings(self) -> Dict[str, str]:
        """Get database connection strings."""
        return {
            'mongodb': f"mongodb://{self._database_config.username}:{self._database_config.password}@{self._database_config.host}:{self._database_config.port}/{self._database_config.name}?authSource={self._database_config.auth_source}",
            'redis': f"redis://{self._redis_config.host}:{self._redis_config.port}/{self._redis_config.db}"
        }


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def initialize_config(config_file: Optional[Union[str, Path]] = None) -> ConfigurationManager:
    """Initialize global configuration manager."""
    global _config_manager
    _config_manager = ConfigurationManager(config_file)
    return _config_manager


# Convenience functions
def get_settings() -> LucidSettings:
    """Get main application settings."""
    return get_config_manager().get_settings()


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return get_config_manager().get_database_config()


def get_redis_config() -> RedisConfig:
    """Get Redis configuration."""
    return get_config_manager().get_redis_config()


def get_tor_config() -> TorConfig:
    """Get Tor configuration."""
    return get_config_manager().get_tor_config()


def get_security_config() -> SecurityConfig:
    """Get security configuration."""
    return get_config_manager().get_security_config()


def get_service_config(service_name: str) -> Optional[ServiceConfig]:
    """Get service configuration."""
    return get_config_manager().get_service_config(service_name)


def is_production() -> bool:
    """Check if running in production."""
    return get_config_manager().is_production()


def is_development() -> bool:
    """Check if running in development."""
    return get_config_manager().is_development()
