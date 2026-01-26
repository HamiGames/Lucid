"""
GUI Docker Manager Configuration Management
Uses Pydantic Settings for environment variable validation
File: gui-docker-manager/gui-docker-manager/config.py
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Regex patterns for URL validation (compiled at module level)
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')


class DockerManagerSettings(BaseSettings):
    """Settings for GUI Docker Manager service"""
    
    # Service Configuration
    SERVICE_NAME: str = Field(default="gui-docker-manager", description="Service name")
    HOST: str = Field(default="0.0.0.0", description="Service host")
    PORT: int = Field(default=8098, description="Service port")
    SERVICE_URL: str = Field(default="", description="Service URL")
    
    # Docker Configuration (Required)
    DOCKER_HOST: str = Field(default="unix:///var/run/docker.sock", description="Docker socket path")
    DOCKER_API_VERSION: str = Field(default="1.40", description="Docker API version")
    
    # Database Configuration (Optional)
    MONGODB_URL: str = Field(default="", description="MongoDB connection URL")
    REDIS_URL: str = Field(default="", description="Redis connection URL")
    
    # Security
    JWT_SECRET_KEY: str = Field(default="", description="JWT secret key")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Environment
    LUCID_ENV: str = Field(default="production", description="Lucid environment")
    LUCID_PLATFORM: str = Field(default="arm64", description="Lucid platform")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid", description="Project root")
    
    # Access Control
    GUI_ACCESS_LEVELS_ENABLED: bool = Field(default=True, description="Enable access control")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
    
    @field_validator('DOCKER_HOST')
    @classmethod
    def validate_docker_host(cls, v: str) -> str:
        """Validate Docker host is not localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("DOCKER_HOST must not use localhost. Use unix socket path instead")
        return v
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("MONGODB_URL must not use localhost. Use service name (e.g., lucid-mongodb)")
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("REDIS_URL must not use localhost. Use service name (e.g., lucid-redis)")
        return v


class DockerManagerConfigManager:
    """Configuration manager for GUI Docker Manager service"""
    
    def __init__(self):
        """Initialize configuration manager and validate settings"""
        try:
            self.settings = DockerManagerSettings()
            self._validate_config()
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def _validate_config(self):
        """Validate critical configuration"""
        required_fields = {
            'DOCKER_HOST': 'Docker host',
        }
        
        missing = []
        for field, description in required_fields.items():
            value = getattr(self.settings, field, '')
            if not value:
                missing.append(description)
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    def get_config_dict(self) -> dict:
        """Get configuration as dictionary"""
        return {
            'service_name': self.settings.SERVICE_NAME,
            'host': self.settings.HOST,
            'port': self.settings.PORT,
            'service_url': self.settings.SERVICE_URL,
            'docker_host': self.settings.DOCKER_HOST,
            'docker_api_version': self.settings.DOCKER_API_VERSION,
            'mongodb_url': self.settings.MONGODB_URL,
            'redis_url': self.settings.REDIS_URL,
            'jwt_secret_key': self.settings.JWT_SECRET_KEY,
            'log_level': self.settings.LOG_LEVEL,
            'debug': self.settings.DEBUG,
            'lucid_env': self.settings.LUCID_ENV,
            'gui_access_levels_enabled': self.settings.GUI_ACCESS_LEVELS_ENABLED,
        }


# Singleton instance
_config_manager: Optional[DockerManagerConfigManager] = None


def get_config() -> DockerManagerConfigManager:
    """Get or create config manager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = DockerManagerConfigManager()
    return _config_manager
