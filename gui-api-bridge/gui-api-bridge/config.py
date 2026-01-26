"""
GUI API Bridge Configuration Management
Uses Pydantic Settings for environment variable validation
No hardcoded values - all configuration from environment
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


class GuiAPIBridgeSettings(BaseSettings):
    """Settings for GUI API Bridge service"""
    
    # Service Configuration
    SERVICE_NAME: str = Field(default="gui-api-bridge", description="Service name")
    HOST: str = Field(default="0.0.0.0", description="Service host")
    PORT: int = Field(default=8102, description="Service port")
    SERVICE_URL: str = Field(default="", description="Service URL")
    
    # Database Configuration (Required)
    MONGODB_URL: str = Field(default="", description="MongoDB connection URL")
    REDIS_URL: str = Field(default="", description="Redis connection URL")
    
    # Backend Service URLs
    API_GATEWAY_URL: str = Field(default="", description="API Gateway URL")
    BLOCKCHAIN_ENGINE_URL: str = Field(default="", description="Blockchain Engine URL")
    AUTH_SERVICE_URL: str = Field(default="", description="Auth Service URL")
    SESSION_API_URL: str = Field(default="", description="Session API URL")
    NODE_MANAGEMENT_URL: str = Field(default="", description="Node Management URL")
    ADMIN_INTERFACE_URL: str = Field(default="", description="Admin Interface URL")
    TRON_PAYMENT_URL: str = Field(default="", description="TRON Payment URL")
    
    # Security
    JWT_SECRET_KEY: str = Field(default="", description="JWT secret key")
    
    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    DEBUG: bool = Field(default=False, description="Debug mode")
    
    # Environment
    LUCID_ENV: str = Field(default="production", description="Lucid environment")
    LUCID_PLATFORM: str = Field(default="arm64", description="Lucid platform")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid", description="Project root")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
    
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
    
    @field_validator('API_GATEWAY_URL')
    @classmethod
    def validate_api_gateway_url(cls, v: str) -> str:
        """Validate API Gateway URL"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("API_GATEWAY_URL must not use localhost. Use service name (e.g., lucid-api-gateway)")
        return v
    
    @field_validator('BLOCKCHAIN_ENGINE_URL')
    @classmethod
    def validate_blockchain_engine_url(cls, v: str) -> str:
        """Validate Blockchain Engine URL"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("BLOCKCHAIN_ENGINE_URL must not use localhost. Use service name (e.g., lucid-blockchain-engine)")
        return v
    
    @field_validator('AUTH_SERVICE_URL')
    @classmethod
    def validate_auth_service_url(cls, v: str) -> str:
        """Validate Auth Service URL"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("AUTH_SERVICE_URL must not use localhost. Use service name (e.g., lucid-auth-service)")
        return v
    
    @field_validator('SESSION_API_URL')
    @classmethod
    def validate_session_api_url(cls, v: str) -> str:
        """Validate Session API URL"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("SESSION_API_URL must not use localhost. Use service name (e.g., lucid-session-api)")
        return v


class GuiAPIBridgeConfigManager:
    """Configuration manager for GUI API Bridge service"""
    
    def __init__(self):
        """Initialize configuration manager and validate settings"""
        try:
            self.settings = GuiAPIBridgeSettings()
            self._validate_config()
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise
    
    def _validate_config(self):
        """Validate critical configuration"""
        required_fields = {
            'MONGODB_URL': 'MongoDB URL',
            'REDIS_URL': 'Redis URL',
            'API_GATEWAY_URL': 'API Gateway URL',
            'AUTH_SERVICE_URL': 'Auth Service URL',
            'JWT_SECRET_KEY': 'JWT Secret Key',
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
            'mongodb_url': self.settings.MONGODB_URL,
            'redis_url': self.settings.REDIS_URL,
            'api_gateway_url': self.settings.API_GATEWAY_URL,
            'blockchain_engine_url': self.settings.BLOCKCHAIN_ENGINE_URL,
            'auth_service_url': self.settings.AUTH_SERVICE_URL,
            'session_api_url': self.settings.SESSION_API_URL,
            'node_management_url': self.settings.NODE_MANAGEMENT_URL,
            'admin_interface_url': self.settings.ADMIN_INTERFACE_URL,
            'tron_payment_url': self.settings.TRON_PAYMENT_URL,
            'jwt_secret_key': self.settings.JWT_SECRET_KEY,
            'log_level': self.settings.LOG_LEVEL,
            'debug': self.settings.DEBUG,
            'lucid_env': self.settings.LUCID_ENV,
        }
    
    def get_service_url(self, service_name: str) -> str:
        """Get backend service URL by service name"""
        service_urls = {
            'api-gateway': self.settings.API_GATEWAY_URL,
            'blockchain-engine': self.settings.BLOCKCHAIN_ENGINE_URL,
            'auth-service': self.settings.AUTH_SERVICE_URL,
            'session-api': self.settings.SESSION_API_URL,
            'node-management': self.settings.NODE_MANAGEMENT_URL,
            'admin-interface': self.settings.ADMIN_INTERFACE_URL,
            'tron-payment': self.settings.TRON_PAYMENT_URL,
        }
        
        if service_name not in service_urls:
            raise ValueError(f"Unknown service: {service_name}")
        
        return service_urls[service_name]
    
    def validate_urls(self) -> bool:
        """Validate all configured URLs"""
        try:
            urls = [
                ("API_GATEWAY", self.settings.API_GATEWAY_URL),
                ("BLOCKCHAIN_ENGINE", self.settings.BLOCKCHAIN_ENGINE_URL),
                ("AUTH_SERVICE", self.settings.AUTH_SERVICE_URL),
                ("SESSION_API", self.settings.SESSION_API_URL),
                ("NODE_MANAGEMENT", self.settings.NODE_MANAGEMENT_URL),
                ("ADMIN_INTERFACE", self.settings.ADMIN_INTERFACE_URL),
                ("TRON_PAYMENT", self.settings.TRON_PAYMENT_URL),
            ]
            
            for name, url in urls:
                if not url:
                    logger.error(f"{name} URL is not configured")
                    return False
                logger.debug(f"{name}: {url}")
            
            logger.info("All service URLs validated successfully")
            return True
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            return False


# Singleton instance
_config_manager: Optional[GuiAPIBridgeConfigManager] = None


def get_config() -> GuiAPIBridgeConfigManager:
    """Get or create config manager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = GuiAPIBridgeConfigManager()
    return _config_manager
