"""
Configuration Management

File: 03-api-gateway/api/app/config.py
Purpose: Centralized configuration for the API Gateway service using Pydantic settings.

Architecture Notes:
- BLOCKCHAIN_CORE_URL: Points to lucid_blocks (on-chain blockchain system)
- TRON_PAYMENT_URL: Points to isolated TRON payment service
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator, model_validator, model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = Field(default="api-gateway", env="SERVICE_NAME")
    API_VERSION: str = Field(default="v1", env="API_VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field(default="production", env="ENVIRONMENT")
    
    # Port Configuration
    HTTP_PORT: int = Field(default=8080, env="HTTP_PORT")
    HTTPS_PORT: int = Field(default=8081, env="HTTPS_PORT")
    
    # Security Configuration
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Database Configuration (accepts MONGODB_URI or MONGODB_URL)
    MONGODB_URI: str = Field(default="", validation_alias="MONGODB_URI")
    MONGODB_URL: str = Field(default="", validation_alias="MONGODB_URL")
    MONGODB_DATABASE: str = Field(default="lucid_gateway")
    REDIS_URL: str = Field(...)
    
    @property
    def mongodb_connection_string(self) -> str:
        """Get MongoDB connection string (supports both URI and URL env vars)"""
        return self.MONGODB_URI or self.MONGODB_URL
    
    # Backend Service URLs
    # lucid_blocks = on-chain blockchain system
    BLOCKCHAIN_CORE_URL: str = Field(..., env="BLOCKCHAIN_CORE_URL")
    SESSION_MANAGEMENT_URL: str = Field(..., env="SESSION_MANAGEMENT_URL")
    AUTH_SERVICE_URL: str = Field(..., env="AUTH_SERVICE_URL")
    # TRON = isolated payment service (NOT part of lucid_blocks)
    TRON_PAYMENT_URL: str = Field(..., env="TRON_PAYMENT_URL")
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_BURST_SIZE: int = Field(default=200, env="RATE_LIMIT_BURST_SIZE")
    
    # SSL Configuration
    SSL_ENABLED: bool = Field(default=True, env="SSL_ENABLED")
    SSL_CERT_PATH: Optional[str] = Field(None, env="SSL_CERT_PATH")
    SSL_KEY_PATH: Optional[str] = Field(None, env="SSL_KEY_PATH")
    
    # CORS Configuration
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = Field(default=True)
    HEALTH_CHECK_INTERVAL: str = Field(default="30")
    
    @model_validator(mode="before")
    @classmethod
    def parse_list_fields(cls, data):
        """Parse List fields from environment variables before pydantic-settings tries to parse as JSON."""
        if isinstance(data, dict):
            # Handle ALLOWED_HOSTS and CORS_ORIGINS
            for list_field in ["ALLOWED_HOSTS", "CORS_ORIGINS"]:
                if list_field in data:
                    value = data[list_field]
                    if value is None or value == "":
                        data[list_field] = ["*"]
                    elif isinstance(value, str):
                        # Handle single "*" value
                        if value.strip() == "*":
                            data[list_field] = ["*"]
                        else:
                            # Split comma-separated values
                            items = [item.strip() for item in value.split(",") if item.strip()]
                            data[list_field] = items if items else ["*"]
                    # If it's already a list, leave it as is
        return data
    
    @field_validator('HEALTH_CHECK_INTERVAL', mode='before')
    @classmethod
    def parse_health_check_interval(cls, v):
        """Parse health check interval, stripping 's' suffix if present"""
        if isinstance(v, str):
            return v.rstrip('s')
        return str(v)
    
    @property
    def health_check_interval_seconds(self) -> int:
        """Get health check interval as integer seconds"""
        return int(self.HEALTH_CHECK_INTERVAL)
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse comma-separated allowed hosts"""
        if v is None or v == "":
            return ["*"]  # Default to allow all
        if isinstance(v, str):
            # Handle single "*" value
            if v.strip() == "*":
                return ["*"]
            # Split comma-separated values
            items = [host.strip() for host in v.split(',') if host.strip()]
            return items if items else ["*"]
        if isinstance(v, list):
            return v
        return ["*"]  # Fallback to default
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins"""
        if v is None or v == "":
            return ["*"]  # Default to allow all
        if isinstance(v, str):
            # Handle single "*" value
            if v.strip() == "*":
                return ["*"]
            # Split comma-separated values
            items = [origin.strip() for origin in v.split(',') if origin.strip()]
            return items if items else ["*"]
        if isinstance(v, list):
            return v
        return ["*"]  # Fallback to default
    
    @field_validator('JWT_SECRET_KEY')
    @classmethod
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key length"""
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters long')
        return v
    
    @field_validator('BLOCKCHAIN_CORE_URL')
    @classmethod
    def validate_blockchain_url(cls, v):
        """Validate blockchain core URL (should point to lucid_blocks)"""
        if not v:
            raise ValueError('BLOCKCHAIN_CORE_URL is required')
        # Ensure it's pointing to the correct service
        if 'lucid-blocks' not in v and 'lucid_blocks' not in v:
            import warnings
            warnings.warn(
                f"BLOCKCHAIN_CORE_URL ({v}) should point to lucid_blocks service. "
                "Ensure this is correct for on-chain blockchain operations."
            )
        return v
    
    @field_validator('TRON_PAYMENT_URL')
    @classmethod
    def validate_tron_url(cls, v):
        """Validate TRON payment URL (should be isolated service)"""
        if not v:
            raise ValueError('TRON_PAYMENT_URL is required')
        # Ensure it's pointing to isolated payment service
        if 'tron' not in v.lower():
            import warnings
            warnings.warn(
                f"TRON_PAYMENT_URL ({v}) should point to TRON payment service. "
                "TRON is an isolated payment service, NOT part of lucid_blocks."
            )
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
