"""
GUI API Bridge Configuration Management
Uses Pydantic Settings for environment variable validation
No hardcoded values - all configuration from environment
Aligned with 03-api-gateway configuration patterns
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Regex patterns for URL validation (compiled at module level)
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')


class GuiAPIBridgeSettings(BaseSettings):
    """Settings for GUI API Bridge service - aligned with api-gateway"""
    
    # Service Configuration
    SERVICE_NAME: str = Field(default="gui-api-bridge", description="Service name")
    SERVICE_VERSION: str = Field(default="1.0.0", description="Service version")
    HOST: str = Field(default="0.0.0.0", description="Service host")
    PORT: int = Field(default=8102, description="Service port")
    SERVICE_URL: str = Field(default="", description="Service URL")
    
    # Database Configuration (Required)
    MONGODB_URL: str = Field(default="", description="MongoDB connection URL")
    MONGODB_URI: str = Field(default="", description="MongoDB connection URI (alternative)")
    REDIS_URL: str = Field(default="", description="Redis connection URL")
    
    # Backend Service URLs
    API_GATEWAY_URL: str = Field(default="", description="API Gateway URL")
    BLOCKCHAIN_ENGINE_URL: str = Field(default="", description="Blockchain Engine URL")
    AUTH_SERVICE_URL: str = Field(default="", description="Auth Service URL")
    SESSION_API_URL: str = Field(default="", description="Session API URL")
    NODE_MANAGEMENT_URL: str = Field(default="", description="Node Management URL")
    ADMIN_INTERFACE_URL: str = Field(default="", description="Admin Interface URL")
    TRON_PAYMENT_URL: str = Field(default="", description="TRON Payment URL")
    
    # Security Configuration
    JWT_SECRET_KEY: str = Field(default="", description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, description="JWT access token expiry minutes")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="JWT refresh token expiry days")
    
    # CORS Configuration
    ALLOWED_HOSTS: List[str] = Field(default=["*"], description="Allowed hosts")
    CORS_ORIGINS: str = Field(default="*", description="CORS origins")
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=1000, description="Rate limit requests per minute")
    RATE_LIMIT_BURST_SIZE: int = Field(default=200, description="Rate limit burst size")
    
    # SSL Configuration
    SSL_ENABLED: bool = Field(default=False, description="Enable SSL")
    SSL_CERT_PATH: Optional[str] = Field(default=None, description="SSL certificate path")
    SSL_KEY_PATH: Optional[str] = Field(default=None, description="SSL key path")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json or text)")
    
    # Monitoring
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics")
    HEALTH_CHECK_INTERVAL: str = Field(default="30", description="Health check interval in seconds")
    
    # Environment
    ENVIRONMENT: str = Field(default="production", description="Environment (production/staging/development)")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LUCID_ENV: str = Field(default="production", description="Lucid environment")
    LUCID_PLATFORM: str = Field(default="arm64", description="Lucid platform")
    PROJECT_ROOT: str = Field(default="/mnt/myssd/Lucid/Lucid", description="Project root")
    
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )
    
    @property
    def mongodb_connection_string(self) -> str:
        """Get MongoDB connection string (supports both URI and URL env vars)"""
        return self.MONGODB_URI or self.MONGODB_URL
    
    @property
    def health_check_interval_seconds(self) -> int:
        """Get health check interval as integer seconds"""
        return int(self.HEALTH_CHECK_INTERVAL.rstrip('s'))
    
    @model_validator(mode="before")
    @classmethod
    def parse_list_fields(cls, data):
        """Parse List fields from environment variables before pydantic-settings tries to parse as JSON."""
        if isinstance(data, dict):
            if "ALLOWED_HOSTS" in data:
                value = data["ALLOWED_HOSTS"]
                if value is None or value == "":
                    data["ALLOWED_HOSTS"] = ["*"]
                elif isinstance(value, str):
                    if value.strip() == "*":
                        data["ALLOWED_HOSTS"] = ["*"]
                    else:
                        items = [item.strip() for item in value.split(",") if item.strip()]
                        data["ALLOWED_HOSTS"] = items if items else ["*"]
        return data
    
    @field_validator('HEALTH_CHECK_INTERVAL', mode='before')
    @classmethod
    def parse_health_check_interval(cls, v):
        """Parse health check interval, stripping 's' suffix if present"""
        if isinstance(v, str):
            return v.rstrip('s')
        return str(v)
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse comma-separated allowed hosts"""
        if v is None or v == "":
            return ["*"]
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            items = [host.strip() for host in v.split(',') if host.strip()]
            return items if items else ["*"]
        if isinstance(v, list):
            return v
        return ["*"]
    
    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL doesn't use localhost in production"""
        if v and cls is GuiAPIBridgeSettings:
            env = os.getenv('ENVIRONMENT', 'production')
            if env == 'production':
                if LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v):
                    raise ValueError("MONGODB_URL must not use localhost in production. Use service name (e.g., lucid-mongodb)")
        return v
    
    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL doesn't use localhost in production"""
        if v and cls is GuiAPIBridgeSettings:
            env = os.getenv('ENVIRONMENT', 'production')
            if env == 'production':
                if LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v):
                    raise ValueError("REDIS_URL must not use localhost in production. Use service name (e.g., lucid-redis)")
        return v
    
    @field_validator('API_GATEWAY_URL', 'BLOCKCHAIN_ENGINE_URL', 'AUTH_SERVICE_URL', 
                     'SESSION_API_URL', 'NODE_MANAGEMENT_URL', 'ADMIN_INTERFACE_URL', 
                     'TRON_PAYMENT_URL')
    @classmethod
    def validate_service_urls(cls, v: str) -> str:
        """Validate service URLs format"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            env = os.getenv('ENVIRONMENT', 'production')
            if env == 'production':
                raise ValueError(f"Service URL must not use localhost in production. Use service name (e.g., lucid-service)")
        return v


class GuiAPIBridgeConfigManager:
    """Configuration manager for GUI API Bridge service - aligned with api-gateway"""
    
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
            logger.warning(f"Missing configuration: {', '.join(missing)}")
    
    def get_config_dict(self) -> dict:
        """Get configuration as dictionary"""
        return {
            'service_name': self.settings.SERVICE_NAME,
            'service_version': self.settings.SERVICE_VERSION,
            'host': self.settings.HOST,
            'port': self.settings.PORT,
            'service_url': self.settings.SERVICE_URL,
            'mongodb_url': self.settings.mongodb_connection_string,
            'redis_url': self.settings.REDIS_URL,
            'api_gateway_url': self.settings.API_GATEWAY_URL,
            'blockchain_engine_url': self.settings.BLOCKCHAIN_ENGINE_URL,
            'auth_service_url': self.settings.AUTH_SERVICE_URL,
            'session_api_url': self.settings.SESSION_API_URL,
            'node_management_url': self.settings.NODE_MANAGEMENT_URL,
            'admin_interface_url': self.settings.ADMIN_INTERFACE_URL,
            'tron_payment_url': self.settings.TRON_PAYMENT_URL,
            'jwt_secret_key': self.settings.JWT_SECRET_KEY,
            'jwt_algorithm': self.settings.JWT_ALGORITHM,
            'jwt_access_token_expire_minutes': self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
            'log_level': self.settings.LOG_LEVEL,
            'log_format': self.settings.LOG_FORMAT,
            'debug': self.settings.DEBUG,
            'environment': self.settings.ENVIRONMENT,
            'lucid_env': self.settings.LUCID_ENV,
            'rate_limit_enabled': self.settings.RATE_LIMIT_ENABLED,
            'rate_limit_requests_per_minute': self.settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            'ssl_enabled': self.settings.SSL_ENABLED,
            'allowed_hosts': self.settings.ALLOWED_HOSTS,
            'cors_origins': self.settings.CORS_ORIGINS,
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
        
        url = service_urls[service_name]
        if not url:
            raise ValueError(f"Service URL not configured: {service_name}")
        
        return url
    
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
                    logger.warning(f"{name} URL is not configured")
                else:
                    logger.debug(f"{name}: {url}")
            
            logger.info("Service URLs validated")
            return True
        except Exception as e:
            logger.error(f"URL validation failed: {e}")
            return False


_config_manager: Optional[GuiAPIBridgeConfigManager] = None


def get_config() -> GuiAPIBridgeConfigManager:
    """Get or create config manager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = GuiAPIBridgeConfigManager()
    return _config_manager
