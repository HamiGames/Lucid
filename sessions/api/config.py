#!/usr/bin/env python3
"""
Lucid Session API Configuration
Configuration management for session API service
"""

import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
import logging

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
    
    def __init__(self):
        """Initialize configuration from environment"""
        self.settings = SessionAPISettings()
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

