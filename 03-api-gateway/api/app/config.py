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
from pydantic import BaseSettings, validator, Field
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
    
    # Database Configuration
    MONGODB_URI: str = Field(..., env="MONGODB_URI")
    MONGODB_DATABASE: str = Field(default="lucid_gateway", env="MONGODB_DATABASE")
    REDIS_URL: str = Field(..., env="REDIS_URL")
    
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
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    HEALTH_CHECK_INTERVAL: int = Field(default=30, env="HEALTH_CHECK_INTERVAL")
    
    @validator('ALLOWED_HOSTS', pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse comma-separated allowed hosts"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(',')]
        return v
    
    @validator('CORS_ORIGINS', pre=True)
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @validator('JWT_SECRET_KEY')
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key length"""
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters long')
        return v
    
    @validator('BLOCKCHAIN_CORE_URL')
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
    
    @validator('TRON_PAYMENT_URL')
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
    
    class Config:
        """Pydantic config"""
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
