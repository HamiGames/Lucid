"""
RDP Server Manager Configuration Management
Uses Pydantic Settings for environment variable validation
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class RDPServerManagerSettings(BaseSettings):
    """Base settings for RDP Server Manager service"""
    
    # Service configuration
    RDP_SERVER_MANAGER_HOST: str = Field(default="0.0.0.0", description="Service host")
    RDP_SERVER_MANAGER_PORT: int = Field(default=8081, description="Service port")
    RDP_SERVER_MANAGER_URL: str = Field(description="Service URL")
    
    # Database configuration
    MONGODB_URL: str = Field(description="MongoDB connection URL")
    # Support MONGODB_URI as alternative (for compatibility)
    MONGODB_URI: Optional[str] = Field(default=None, description="MongoDB connection URL (alternative)")
    REDIS_URL: str = Field(description="Redis connection URL")
    
    # Optional: Additional service dependencies
    API_GATEWAY_URL: Optional[str] = Field(default=None, description="API Gateway URL")
    AUTH_SERVICE_URL: Optional[str] = Field(default=None, description="Auth Service URL")
    
    # Port management configuration
    PORT_RANGE_START: int = Field(default=13389, description="Start of port allocation range")
    PORT_RANGE_END: int = Field(default=14389, description="End of port allocation range")
    MAX_CONCURRENT_SERVERS: int = Field(default=50, description="Maximum concurrent RDP servers")
    
    # Environment
    LUCID_ENV: str = Field(default="production")
    LUCID_PLATFORM: str = Field(default="arm64")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    @field_validator('PORT_RANGE_START', 'PORT_RANGE_END')
    @classmethod
    def validate_port_range(cls, v):
        if v < 1024 or v > 65535:
            raise ValueError('Port must be between 1024 and 65535')
        return v
    
    @field_validator('MAX_CONCURRENT_SERVERS')
    @classmethod
    def validate_max_servers(cls, v):
        if v < 1 or v > 1000:
            raise ValueError('MAX_CONCURRENT_SERVERS must be between 1 and 1000')
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        allowed = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed:
            raise ValueError(f'LOG_LEVEL must be one of {allowed}')
        return v.upper()
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

class RDPServerManagerConfigManager:
    """Configuration manager for RDP Server Manager"""
    
    def __init__(self):
        self.settings = RDPServerManagerSettings()
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration"""
        # Use MONGODB_URI if MONGODB_URL is not set (for compatibility)
        if not self.settings.MONGODB_URL and self.settings.MONGODB_URI:
            self.settings.MONGODB_URL = self.settings.MONGODB_URI
        
        if not self.settings.MONGODB_URL:
            raise ValueError("MONGODB_URL or MONGODB_URI is required")
        if not self.settings.REDIS_URL:
            raise ValueError("REDIS_URL is required")
        
        # Validate port range
        if self.settings.PORT_RANGE_START >= self.settings.PORT_RANGE_END:
            raise ValueError("PORT_RANGE_START must be less than PORT_RANGE_END")
        
        # Validate MongoDB URL doesn't use localhost
        mongodb_url = self.settings.MONGODB_URL
        if "localhost" in mongodb_url or "127.0.0.1" in mongodb_url:
            raise ValueError("MONGODB_URL must not use localhost - use service name (e.g., lucid-mongodb)")
        
        # Validate Redis URL doesn't use localhost
        if "localhost" in self.settings.REDIS_URL or "127.0.0.1" in self.settings.REDIS_URL:
            raise ValueError("REDIS_URL must not use localhost - use service name (e.g., lucid-redis)")
    
    def get_server_manager_config_dict(self) -> dict:
        """Get service configuration as dictionary"""
        return {
            "host": self.settings.RDP_SERVER_MANAGER_HOST,
            "port": self.settings.RDP_SERVER_MANAGER_PORT,
            "url": self.settings.RDP_SERVER_MANAGER_URL,
            "port_range_start": self.settings.PORT_RANGE_START,
            "port_range_end": self.settings.PORT_RANGE_END,
            "max_concurrent_servers": self.settings.MAX_CONCURRENT_SERVERS,
            "api_gateway_url": self.settings.API_GATEWAY_URL,
            "auth_service_url": self.settings.AUTH_SERVICE_URL,
        }
    
    def get_mongodb_url(self) -> str:
        """Get MongoDB URL"""
        return self.settings.MONGODB_URL
    
    def get_redis_url(self) -> str:
        """Get Redis URL"""
        return self.settings.REDIS_URL

