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
from pydantic import BaseSettings, validator
from pathlib import Path

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
    host: str = "0.0.0.0"
    port: int = 8085
    
    # Database Configuration
    mongodb_url: str = "mongodb://localhost:27017/lucid_sessions"
    redis_url: str = "redis://localhost:6379/0"
    
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
    
    # Storage Configuration
    storage_path: str = "/storage/chunks"
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
    
    # External Service URLs
    storage_service_url: str = "http://session-storage:8086"
    blockchain_service_url: str = "http://blockchain-core:8084"
    api_gateway_url: str = "http://api-gateway:8080"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        env_prefix = "CHUNK_PROCESSOR_"
    
    @validator('encryption_key', pre=True)
    def validate_encryption_key(cls, v):
        """Validate encryption key format."""
        if v is None:
            # Generate a default key if none provided
            import secrets
            return secrets.token_urlsafe(32)
        
        if len(v) < 32:
            raise ValueError("Encryption key must be at least 32 characters")
        
        return v
    
    @validator('max_workers')
    def validate_max_workers(cls, v):
        """Validate max workers setting."""
        if v < 1 or v > 50:
            raise ValueError("Max workers must be between 1 and 50")
        return v
    
    @validator('max_chunk_size')
    def validate_max_chunk_size(cls, v):
        """Validate max chunk size setting."""
        if v < 1024 or v > 100 * 1024 * 1024:  # 1KB to 100MB
            raise ValueError("Max chunk size must be between 1KB and 100MB")
        return v
    
    @validator('storage_path')
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
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @validator('allowed_origins', pre=True)
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
            # Validate encryption key
            if not self.encryption_key or len(self.encryption_key) < 32:
                logger.error("Invalid encryption key")
                return False
            
            # Validate storage path
            storage_path = Path(self.storage_path)
            if not storage_path.exists():
                logger.error(f"Storage path does not exist: {self.storage_path}")
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
    Load configuration from file and environment variables.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Loaded configuration object
    """
    try:
        if config_file and os.path.exists(config_file):
            # Load from specific file
            config = ChunkProcessorConfig(_env_file=config_file)
        else:
            # Load from default locations
            config = ChunkProcessorConfig()
        
        # Validate configuration
        if not config.validate_config():
            raise ValueError("Configuration validation failed")
        
        logger.info("Configuration loaded successfully")
        return config
        
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise


def create_default_config_file(config_path: str = "config.yaml"):
    """
    Create a default configuration file.
    
    Args:
        config_path: Path to create the configuration file
    """
    import yaml
    
    default_config = {
        "service_name": "chunk-processor",
        "service_version": "1.0.0",
        "debug": False,
        "host": "0.0.0.0",
        "port": 8085,
        "mongodb_url": "mongodb://localhost:27017/lucid_sessions",
        "redis_url": "redis://localhost:6379/0",
        "encryption_algorithm": "AES-256-GCM",
        "max_workers": 10,
        "queue_size": 1000,
        "storage_path": "/storage/chunks",
        "max_chunk_size": 10485760,  # 10MB
        "compression_enabled": True,
        "compression_level": 6,
        "metrics_enabled": True,
        "log_level": "INFO",
        "prometheus_enabled": True,
        "prometheus_port": 9090
    }
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        
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
