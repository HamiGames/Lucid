#!/usr/bin/env python3
"""
Lucid Session Storage Configuration
Configuration management for session storage service
"""

import os
from typing import Dict, Any, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class StorageSettings(BaseSettings):
    """Storage configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-session-storage"
    SERVICE_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Network Configuration (from docker-compose)
    # Note: SESSION_STORAGE_HOST and SESSION_STORAGE_PORT are provided by docker-compose
    # HOST is the bind address (should be 0.0.0.0), PORT is the service port
    HOST: str = "0.0.0.0"  # Bind address (always 0.0.0.0 for container binding)
    PORT: int = 8082  # Default port (overridden by SESSION_STORAGE_PORT from docker-compose)
    SESSION_STORAGE_HOST: str = ""  # From docker-compose: SESSION_STORAGE_HOST (service name, not bind address)
    SESSION_STORAGE_PORT: str = ""  # From docker-compose: SESSION_STORAGE_PORT (string, converted to int)
    
    # Database Configuration (from .env.foundation, .env.core)
    MONGODB_URL: str = ""  # Required from environment: MONGODB_URL or MONGO_URL
    REDIS_URL: str = ""  # Required from environment: REDIS_URL
    
    # Storage Configuration (use volume mount paths from docker-compose)
    LUCID_STORAGE_PATH: str = "/app/data/sessions"  # Volume: /data/session-storage:/app/data
    LUCID_CHUNK_STORE_PATH: str = "/app/data/chunks"  # Volume: /data/session-storage:/app/data
    TEMP_STORAGE_PATH: str = "/tmp/storage"  # tmpfs mount: /tmp:size=200m
    
    # Chunk Configuration
    LUCID_CHUNK_SIZE_MB: int = 10
    LUCID_COMPRESSION_LEVEL: int = 6
    LUCID_COMPRESSION_ALGORITHM: str = "zstd"  # zstd, lz4, gzip
    LUCID_ENCRYPTION_ENABLED: bool = True
    
    # Session Configuration
    LUCID_RETENTION_DAYS: int = 30
    LUCID_MAX_SESSIONS: int = 1000
    LUCID_MAX_CHUNKS_PER_SESSION: int = 100000
    LUCID_CLEANUP_INTERVAL_HOURS: int = 24
    
    # Backup Configuration
    LUCID_BACKUP_ENABLED: bool = True
    LUCID_BACKUP_RETENTION_DAYS: int = 7
    
    # Performance Configuration
    SESSION_STORAGE_WORKERS: int = 1  # Uvicorn workers
    MAX_STORAGE_SIZE_GB: int = 1000
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9217
    HEALTH_CHECK_INTERVAL: int = 30
    
    # CORS Configuration (from .env.application)
    CORS_ORIGINS: str = "*"  # From environment: CORS_ORIGINS (comma-separated list, default: "*")
    
    @field_validator('LUCID_CHUNK_SIZE_MB')
    @classmethod
    def validate_chunk_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('LUCID_CHUNK_SIZE_MB must be between 1 and 100 MB')
        return v
    
    @field_validator('LUCID_COMPRESSION_LEVEL')
    @classmethod
    def validate_compression_level(cls, v):
        if v < 1 or v > 9:
            raise ValueError('LUCID_COMPRESSION_LEVEL must be between 1 and 9')
        return v
    
    @field_validator('LUCID_COMPRESSION_ALGORITHM')
    @classmethod
    def validate_compression_algorithm(cls, v):
        allowed = ['zstd', 'lz4', 'gzip']
        if v not in allowed:
            raise ValueError(f'LUCID_COMPRESSION_ALGORITHM must be one of {allowed}')
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
        return v
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v):
        if not v or v == "":
            raise ValueError('MONGODB_URL or MONGO_URL environment variable is required but not set')
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError('MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)')
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v):
        if not v or v == "":
            raise ValueError('REDIS_URL environment variable is required but not set')
        if "localhost" in v or "127.0.0.1" in v:
            raise ValueError('REDIS_URL must not use localhost - use service name (e.g., lucid-redis)')
        return v
    
    model_config = {
        # pydantic-settings will read from environment variables
        # docker-compose provides: .env.secrets, .env.core, .env.application, .env.foundation
        "env_file": None,  # Don't read .env file directly - use environment variables from docker-compose
        "case_sensitive": True,
        "env_file_encoding": "utf-8"
    }


class StorageConfig:
    """
    Main storage configuration class
    Manages all storage-related configuration
    """
    
    def __init__(self, settings: Optional[StorageSettings] = None):
        try:
            self.settings = settings or StorageSettings()
            
            # Validate critical environment variables
            self._validate_required_env_vars()
            
            # Override PORT from SESSION_STORAGE_PORT if provided (HOST always stays 0.0.0.0)
            # SESSION_STORAGE_HOST is the service name for URLs, not the bind address
            if hasattr(self.settings, 'SESSION_STORAGE_PORT') and self.settings.SESSION_STORAGE_PORT:
                try:
                    self.settings.PORT = int(self.settings.SESSION_STORAGE_PORT)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid SESSION_STORAGE_PORT value: {self.settings.SESSION_STORAGE_PORT}, using default {self.settings.PORT}")
            
            # Handle MONGODB_URL vs MONGO_URL
            if not self.settings.MONGODB_URL:
                mongodb_url = os.getenv('MONGODB_URL') or os.getenv('MONGO_URL')
                if mongodb_url:
                    self.settings.MONGODB_URL = mongodb_url
            
            # Parse CORS origins (comma-separated list or "*")
            if self.settings.CORS_ORIGINS == "*":
                self.cors_origins = ["*"]
            else:
                self.cors_origins = [origin.strip() for origin in self.settings.CORS_ORIGINS.split(",") if origin.strip()]
            
            logger.info("Storage configuration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize storage configuration: {str(e)}")
            raise
    
    def _validate_required_env_vars(self):
        """Validate that required environment variables are set"""
        # MONGODB_URL validation is handled by Pydantic validator
        # But we need to check if it's empty and try MONGO_URL as fallback
        if not self.settings.MONGODB_URL:
            mongodb_url = os.getenv('MONGODB_URL') or os.getenv('MONGO_URL')
            if mongodb_url:
                self.settings.MONGODB_URL = mongodb_url
        
        # REDIS_URL validation is handled by Pydantic validator
        # The validator will raise if it's empty
    
    def get_storage_config_dict(self) -> Dict[str, Any]:
        """Get storage configuration as dictionary (for StorageConfig dataclass)"""
        return {
            "base_path": self.settings.LUCID_STORAGE_PATH,
            "chunk_size_mb": self.settings.LUCID_CHUNK_SIZE_MB,
            "compression_level": self.settings.LUCID_COMPRESSION_LEVEL,
            "encryption_enabled": self.settings.LUCID_ENCRYPTION_ENABLED,
            "retention_days": self.settings.LUCID_RETENTION_DAYS,
            "max_sessions": self.settings.LUCID_MAX_SESSIONS,
            "cleanup_interval_hours": self.settings.LUCID_CLEANUP_INTERVAL_HOURS
        }
    
    def get_chunk_store_config_dict(self) -> Dict[str, Any]:
        """Get chunk store configuration as dictionary (for ChunkStoreConfig dataclass)"""
        return {
            "base_path": self.settings.LUCID_CHUNK_STORE_PATH,
            "compression_algorithm": self.settings.LUCID_COMPRESSION_ALGORITHM,
            "compression_level": self.settings.LUCID_COMPRESSION_LEVEL,
            "chunk_size_mb": self.settings.LUCID_CHUNK_SIZE_MB,
            "max_chunks_per_session": self.settings.LUCID_MAX_CHUNKS_PER_SESSION,
            "cleanup_interval_hours": self.settings.LUCID_CLEANUP_INTERVAL_HOURS,
            "backup_enabled": self.settings.LUCID_BACKUP_ENABLED,
            "backup_retention_days": self.settings.LUCID_BACKUP_RETENTION_DAYS
        }
    
    def get_settings(self) -> StorageSettings:
        """Get the underlying settings object"""
        return self.settings
    
    def get_environment_variables(self) -> Dict[str, str]:
        """Get environment variables for configuration"""
        return {
            "SERVICE_NAME": self.settings.SERVICE_NAME,
            "SERVICE_VERSION": self.settings.SERVICE_VERSION,
            "DEBUG": str(self.settings.DEBUG),
            "LOG_LEVEL": self.settings.LOG_LEVEL,
            "HOST": self.settings.HOST,
            "PORT": str(self.settings.PORT),
            "MONGODB_URL": "***REDACTED***",
            "REDIS_URL": "***REDACTED***",
            "LUCID_STORAGE_PATH": self.settings.LUCID_STORAGE_PATH,
            "LUCID_CHUNK_STORE_PATH": self.settings.LUCID_CHUNK_STORE_PATH,
            "LUCID_CHUNK_SIZE_MB": str(self.settings.LUCID_CHUNK_SIZE_MB),
            "LUCID_COMPRESSION_LEVEL": str(self.settings.LUCID_COMPRESSION_LEVEL),
            "LUCID_COMPRESSION_ALGORITHM": self.settings.LUCID_COMPRESSION_ALGORITHM,
            "LUCID_ENCRYPTION_ENABLED": str(self.settings.LUCID_ENCRYPTION_ENABLED),
            "LUCID_RETENTION_DAYS": str(self.settings.LUCID_RETENTION_DAYS),
            "LUCID_MAX_SESSIONS": str(self.settings.LUCID_MAX_SESSIONS),
            "LUCID_MAX_CHUNKS_PER_SESSION": str(self.settings.LUCID_MAX_CHUNKS_PER_SESSION),
            "LUCID_CLEANUP_INTERVAL_HOURS": str(self.settings.LUCID_CLEANUP_INTERVAL_HOURS),
            "LUCID_BACKUP_ENABLED": str(self.settings.LUCID_BACKUP_ENABLED),
            "LUCID_BACKUP_RETENTION_DAYS": str(self.settings.LUCID_BACKUP_RETENTION_DAYS),
        }

