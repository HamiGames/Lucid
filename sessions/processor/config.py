"""
Configuration Module for Chunk Processor
Manages configuration settings for the chunk processing service.

This module provides configuration management for the chunk processor service,
including encryption settings, worker configuration, and performance tuning.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pydantic import field_validator
from pydantic_settings import BaseSettings
from pathlib import Path

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class EncryptionConfig:
    """Configuration for encryption settings."""
    algorithm: str = "AES-256-GCM"
    key_size: int = 32  # 256 bits
    nonce_size: int = 12  # 96 bits
    tag_size: int = 16  # 128 bits
    salt_size: int = 32  # 256 bits
    pbkdf2_iterations: int = 100000
    key_rotation_interval: int = 3600  # 1 hour in seconds


@dataclass
class WorkerConfig:
    """Configuration for worker pool settings."""
    max_workers: int = 10
    queue_size: int = 1000
    worker_timeout: int = 30  # seconds
    batch_size: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0  # seconds


@dataclass
class StorageConfig:
    """Configuration for storage settings."""
    storage_path: str = "/storage/chunks"
    max_chunk_size: int = 10 * 1024 * 1024  # 10MB
    max_session_size: int = 100 * 1024 * 1024 * 1024  # 100GB
    compression_enabled: bool = True
    compression_level: int = 6
    cleanup_interval: int = 3600  # 1 hour in seconds


@dataclass
class PerformanceConfig:
    """Configuration for performance settings."""
    metrics_enabled: bool = True
    metrics_interval: int = 10  # seconds
    profiling_enabled: bool = False
    memory_limit_mb: int = 1024  # 1GB
    cpu_limit_percent: int = 80
    io_timeout: int = 30  # seconds


@dataclass
class SecurityConfig:
    """Configuration for security settings."""
    encryption_key: Optional[str] = None
    allowed_origins: List[str] = field(default_factory=list)
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60  # seconds
    audit_logging: bool = True
    secure_headers: bool = True


@dataclass
class MonitoringConfig:
    """Configuration for monitoring settings."""
    health_check_interval: int = 30  # seconds
    log_level: str = "INFO"
    log_format: str = "json"
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    jaeger_enabled: bool = False
    jaeger_endpoint: Optional[str] = None


class ChunkProcessorConfig(BaseSettings):
    """
    Main configuration class for the chunk processor service.
    
    This class manages all configuration settings for the chunk processor,
    including encryption, workers, storage, performance, security, and monitoring.
    """
    
    # Service Configuration
    service_name: str = "chunk-processor"
    service_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"  # Bind address (always 0.0.0.0 for container)
    port: int = 8091  # Default port (overridden by SESSION_PROCESSOR_PORT from docker-compose)
    SESSION_PROCESSOR_PORT: str = ""  # From docker-compose: SESSION_PROCESSOR_PORT
    
    # Database Configuration (from .env.foundation, .env.core)
    mongodb_url: str = ""  # Required from environment: MONGODB_URL
    redis_url: str = ""  # Required from environment: REDIS_URL
    
    # Encryption Configuration
    encryption_key: Optional[str] = None
    encryption_algorithm: str = "AES-256-GCM"
    key_rotation_interval: int = 3600
    
    # Worker Configuration
    max_workers: int = 10
    queue_size: int = 1000
    worker_timeout: int = 30
    batch_size: int = 100
    retry_attempts: int = 3
    retry_delay: float = 1.0
    
    # Storage Configuration (use volume mount paths from docker-compose)
    storage_path: str = "/app/data/chunks"  # Volume: /data/session-processor:/app/data
    max_chunk_size: int = 10 * 1024 * 1024  # 10MB
    max_session_size: int = 100 * 1024 * 1024 * 1024  # 100GB
    compression_enabled: bool = True
    compression_level: int = 6
    cleanup_interval: int = 3600
    
    # Performance Configuration
    metrics_enabled: bool = True
    metrics_interval: int = 10
    profiling_enabled: bool = False
    memory_limit_mb: int = 1024
    cpu_limit_percent: int = 80
    io_timeout: int = 30
    
    # Security Configuration
    allowed_origins: List[str] = []
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60
    audit_logging: bool = True
    secure_headers: bool = True
    
    # Monitoring Configuration
    health_check_interval: int = 30
    log_level: str = "INFO"
    log_format: str = "json"
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    jaeger_enabled: bool = False
    jaeger_endpoint: Optional[str] = None
    
    # External Service URLs (from .env.core, .env.application)
    BLOCKCHAIN_ENGINE_URL: str = ""  # From environment: BLOCKCHAIN_ENGINE_URL (e.g., http://blockchain-engine:8084)
    NODE_MANAGEMENT_URL: str = ""  # From environment: NODE_MANAGEMENT_URL (e.g., http://node-management:8095)
    API_GATEWAY_URL: str = ""  # From environment: API_GATEWAY_URL (e.g., http://api-gateway:8080)
    AUTH_SERVICE_URL: str = ""  # From environment: AUTH_SERVICE_URL (e.g., http://lucid-auth-service:8089)
    SESSION_PIPELINE_URL: str = ""  # From environment: SESSION_PIPELINE_URL (e.g., http://session-pipeline:8083)
    SESSION_RECORDER_URL: str = ""  # From environment: SESSION_RECORDER_URL (e.g., http://session-recorder:8090)
    SESSION_STORAGE_URL: str = ""  # From environment: SESSION_STORAGE_URL (e.g., http://session-storage:8082)
    SESSION_API_URL: str = ""  # From environment: SESSION_API_URL (e.g., http://session-api:8087)
    
    # Integration Service Timeout Configuration (from .env.application)
    SERVICE_TIMEOUT_SECONDS: int = 30  # Default timeout for service calls
    SERVICE_RETRY_COUNT: int = 3  # Default retry count for service calls
    SERVICE_RETRY_DELAY_SECONDS: float = 1.0  # Default delay between retries
    
    model_config = {
        # pydantic-settings will read from environment variables
        # docker-compose provides: .env.secrets, .env.core, .env.application, .env.foundation
        "env_file": None,  # Don't read .env file directly - use environment variables from docker-compose
        "case_sensitive": True,
        "env_prefix": ""  # No prefix - use standard env var names (MONGODB_URL, REDIS_URL)
    }
    
    @field_validator('mongodb_url', mode='before')
    @classmethod
    def validate_mongodb_url(cls, v):
        """Validate MongoDB URL from environment"""
        if not v or v == "":
            # Try to get from environment
            import os
            v = os.getenv('MONGODB_URL', '')
        if not v or v == "":
            raise ValueError('MONGODB_URL environment variable is required but not set')
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError('MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)')
        return v
    
    @field_validator('redis_url', mode='before')
    @classmethod
    def validate_redis_url(cls, v):
        """Validate Redis URL from environment"""
        if not v or v == "":
            # Try to get from environment
            import os
            v = os.getenv('REDIS_URL', '')
        if not v or v == "":
            raise ValueError('REDIS_URL environment variable is required but not set')
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError('REDIS_URL must not use localhost - use service name (e.g., lucid-redis)')
        return v
    
    @field_validator('encryption_key', mode='before')
    @classmethod
    def validate_encryption_key_from_env(cls, v):
        """Get encryption key from environment"""
        if not v or v == "":
            import os
            v = os.getenv('ENCRYPTION_KEY', '')
        if not v or v == "":
            # This is acceptable - encryption may be optional
            return None
        if "your-" in str(v).lower() or "placeholder" in str(v).lower():
            raise ValueError('ENCRYPTION_KEY contains placeholder value - must be set from .env.secrets')
        return v
    
    @field_validator('encryption_key', mode='before')
    @classmethod
    def validate_encryption_key(cls, v):
        """Validate encryption key format."""
        if v is None:
            # Generate a default key if none provided
            import secrets
            return secrets.token_urlsafe(32)
        
        if len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters")
        
        return v
    
    @field_validator('max_workers')
    @classmethod
    def validate_max_workers(cls, v):
        """Validate max workers setting."""
        if v < 1 or v > 50:
            raise ValueError("Max workers must be between 1 and 50")
        return v
    
    @field_validator('max_chunk_size')
    @classmethod
    def validate_max_chunk_size(cls, v):
        """Validate max chunk size setting."""
        if v < 1024 or v > 100 * 1024 * 1024:  # 1KB to 100MB
            raise ValueError("Max chunk size must be between 1KB and 100MB")
        return v
    
    @field_validator('storage_path')
    @classmethod
    def validate_storage_path(cls, v):
        """Validate storage path."""
        path = Path(v)
        if not path.exists():
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created storage directory: {path}")
            except Exception as e:
                logger.warning(f"Could not create storage directory {path}: {e}")
        return str(path)
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse allowed origins from string or list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    def get_encryption_config(self) -> EncryptionConfig:
        """Get encryption configuration."""
        return EncryptionConfig(
            algorithm=self.encryption_algorithm,
            key_rotation_interval=self.key_rotation_interval
        )
    
    def get_worker_config(self) -> WorkerConfig:
        """Get worker configuration."""
        return WorkerConfig(
            max_workers=self.max_workers,
            queue_size=self.queue_size,
            worker_timeout=self.worker_timeout,
            batch_size=self.batch_size,
            retry_attempts=self.retry_attempts,
            retry_delay=self.retry_delay
        )
    
    def get_storage_config(self) -> StorageConfig:
        """Get storage configuration."""
        return StorageConfig(
            storage_path=self.storage_path,
            max_chunk_size=self.max_chunk_size,
            max_session_size=self.max_session_size,
            compression_enabled=self.compression_enabled,
            compression_level=self.compression_level,
            cleanup_interval=self.cleanup_interval
        )
    
    def get_performance_config(self) -> PerformanceConfig:
        """Get performance configuration."""
        return PerformanceConfig(
            metrics_enabled=self.metrics_enabled,
            metrics_interval=self.metrics_interval,
            profiling_enabled=self.profiling_enabled,
            memory_limit_mb=self.memory_limit_mb,
            cpu_limit_percent=self.cpu_limit_percent,
            io_timeout=self.io_timeout
        )
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return SecurityConfig(
            encryption_key=self.encryption_key,
            allowed_origins=self.allowed_origins,
            rate_limit_enabled=self.rate_limit_enabled,
            rate_limit_requests=self.rate_limit_requests,
            rate_limit_window=self.rate_limit_window,
            audit_logging=self.audit_logging,
            secure_headers=self.secure_headers
        )
    
    def get_monitoring_config(self) -> MonitoringConfig:
        """Get monitoring configuration."""
        return MonitoringConfig(
            health_check_interval=self.health_check_interval,
            log_level=self.log_level,
            log_format=self.log_format,
            prometheus_enabled=self.prometheus_enabled,
            prometheus_port=self.prometheus_port,
            jaeger_enabled=self.jaeger_enabled,
            jaeger_endpoint=self.jaeger_endpoint
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "debug": self.debug,
            "host": self.host,
            "port": self.port,
            "mongodb_url": self.mongodb_url,
            "redis_url": self.redis_url,
            "encryption_algorithm": self.encryption_algorithm,
            "max_workers": self.max_workers,
            "queue_size": self.queue_size,
            "storage_path": self.storage_path,
            "max_chunk_size": self.max_chunk_size,
            "compression_enabled": self.compression_enabled,
            "metrics_enabled": self.metrics_enabled,
            "log_level": self.log_level,
            "prometheus_enabled": self.prometheus_enabled,
            "prometheus_port": self.prometheus_port
        }
    
    def validate_config(self) -> bool:
        """
        Validate the entire configuration.
        
        Returns:
            True if configuration is valid
        """
        try:
            # Override port from SESSION_PROCESSOR_PORT if provided
            import os
            port_str = os.getenv('SESSION_PROCESSOR_PORT') or self.SESSION_PROCESSOR_PORT
            if port_str:
                try:
                    self.port = int(port_str)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid SESSION_PROCESSOR_PORT value: {port_str}, using default {self.port}")
            
            # Set integration service URLs from environment if not already set
            if not self.BLOCKCHAIN_ENGINE_URL:
                self.BLOCKCHAIN_ENGINE_URL = os.getenv('BLOCKCHAIN_ENGINE_URL', '')
            if not self.NODE_MANAGEMENT_URL:
                self.NODE_MANAGEMENT_URL = os.getenv('NODE_MANAGEMENT_URL', '')
            if not self.API_GATEWAY_URL:
                self.API_GATEWAY_URL = os.getenv('API_GATEWAY_URL', '')
            if not self.AUTH_SERVICE_URL:
                self.AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', '')
            if not self.SESSION_PIPELINE_URL:
                self.SESSION_PIPELINE_URL = os.getenv('SESSION_PIPELINE_URL', '')
            if not self.SESSION_RECORDER_URL:
                self.SESSION_RECORDER_URL = os.getenv('SESSION_RECORDER_URL', '')
            if not self.SESSION_STORAGE_URL:
                self.SESSION_STORAGE_URL = os.getenv('SESSION_STORAGE_URL', '')
            if not self.SESSION_API_URL:
                self.SESSION_API_URL = os.getenv('SESSION_API_URL', '')
            
            # Validate encryption key (optional - may be None)
            if self.encryption_key and len(self.encryption_key) < 32:
                logger.error("Encryption key must be at least 32 characters if provided")
                return False
            
            # Validate storage path (create if doesn't exist)
            storage_path = Path(self.storage_path)
            if not storage_path.exists():
                try:
                    storage_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created storage directory: {storage_path}")
                except Exception as e:
                    logger.error(f"Storage path does not exist and cannot be created: {self.storage_path}: {e}")
                    return False
            
            # Validate worker settings
            if self.max_workers < 1 or self.max_workers > 50:
                logger.error(f"Invalid max workers: {self.max_workers}")
                return False
            
            # Validate chunk size
            if self.max_chunk_size < 1024 or self.max_chunk_size > 100 * 1024 * 1024:
                logger.error(f"Invalid max chunk size: {self.max_chunk_size}")
                return False
            
            # Validate URLs
            if not self.mongodb_url or not self.redis_url:
                logger.error("Database URLs are required")
                return False
            
            logger.info("Configuration validation successful")
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False


def load_config(config_file: Optional[str] = None) -> ChunkProcessorConfig:
    """
    Load configuration from YAML file and environment variables.
    
    Configuration loading priority (highest to lowest):
    1. Environment variables (highest priority - override everything)
    2. YAML configuration file values
    3. Pydantic field defaults (lowest priority)
    
    Args:
        config_file: Optional path to YAML configuration file. If not provided,
                     will look for 'config.yaml' in the processor directory.
        
    Returns:
        Loaded configuration object with environment variables overriding YAML values
        
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
                Path(__file__).parent.parent / "processor" / "config.yaml",  # Alternative path
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
                    # This allows YAML to have placeholders like mongodb_url: "" that get filled from env
                    yaml_data = {k: v for k, v in yaml_data.items() if v != "" or k in ["mongodb_url", "redis_url", "encryption_key"]}
                    
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
                config = ChunkProcessorConfig.model_validate(yaml_data)
                
                # Step 2: Create config normally to get environment variable values
                env_config = ChunkProcessorConfig()
                
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
                config = ChunkProcessorConfig()
        else:
            # Load from environment variables and defaults only
            config = ChunkProcessorConfig()
        
        # Validate configuration
        if not config.validate_config():
            raise ValueError("Configuration validation failed")
        
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
        "service_name": "chunk-processor",
        "service_version": "1.0.0",
        "debug": False,
        "host": "0.0.0.0",
        "port": 8091,  # Default port (override with SESSION_PROCESSOR_PORT env var)
        "mongodb_url": "",  # Must be set from MONGODB_URL env var
        "redis_url": "",  # Must be set from REDIS_URL env var
        "encryption_algorithm": "AES-256-GCM",
        "key_rotation_interval": 3600,
        "max_workers": 10,
        "queue_size": 1000,
        "worker_timeout": 30,
        "batch_size": 100,
        "retry_attempts": 3,
        "retry_delay": 1.0,
        "storage_path": "/app/data/chunks",  # Volume mount path
        "max_chunk_size": 10485760,  # 10MB
        "max_session_size": 107374182400,  # 100GB
        "compression_enabled": True,
        "compression_level": 6,
        "cleanup_interval": 3600,
        "metrics_enabled": True,
        "metrics_interval": 10,
        "profiling_enabled": False,
        "memory_limit_mb": 1024,
        "cpu_limit_percent": 80,
        "io_timeout": 30,
        "allowed_origins": [],
        "rate_limit_enabled": True,
        "rate_limit_requests": 1000,
        "rate_limit_window": 60,
        "audit_logging": True,
        "secure_headers": True,
        "health_check_interval": 30,
        "log_level": "INFO",
        "log_format": "json",
        "prometheus_enabled": True,
        "prometheus_port": 9090,
        "jaeger_enabled": False,
        "jaeger_endpoint": None
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
config: Optional[ChunkProcessorConfig] = None


def get_config() -> ChunkProcessorConfig:
    """
    Get the global configuration instance.
    
    Returns:
        Global configuration instance
    """
    global config
    if config is None:
        config = load_config()
    return config


def set_config(new_config: ChunkProcessorConfig):
    """
    Set the global configuration instance.
    
    Args:
        new_config: New configuration instance
    """
    global config
    config = new_config
    logger.info("Global configuration updated")
