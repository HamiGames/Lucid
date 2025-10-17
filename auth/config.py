"""
Lucid Authentication Service - Configuration
Cluster 09: Authentication
"""

from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    """Authentication service configuration settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "lucid-auth-service"
    AUTH_SERVICE_PORT: int = Field(default=8089, env="AUTH_SERVICE_PORT")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(..., env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Database Configuration
    MONGODB_URI: str = Field(
        default="mongodb://mongodb:27017/lucid_auth",
        env="MONGODB_URI"
    )
    MONGODB_DATABASE: str = Field(default="lucid_auth", env="MONGODB_DATABASE")
    MONGODB_MAX_POOL_SIZE: int = Field(default=100, env="MONGODB_MAX_POOL_SIZE")
    MONGODB_MIN_POOL_SIZE: int = Field(default=10, env="MONGODB_MIN_POOL_SIZE")
    
    # Redis Configuration
    REDIS_URI: str = Field(
        default="redis://redis:6379/1",
        env="REDIS_URI"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, env="REDIS_MAX_CONNECTIONS")
    REDIS_DECODE_RESPONSES: bool = Field(default=True, env="REDIS_DECODE_RESPONSES")
    
    # Security Configuration
    BCRYPT_ROUNDS: int = Field(default=12, env="BCRYPT_ROUNDS")
    MAX_LOGIN_ATTEMPTS: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    LOGIN_COOLDOWN_MINUTES: int = Field(default=15, env="LOGIN_COOLDOWN_MINUTES")
    PASSWORD_MIN_LENGTH: int = Field(default=12, env="PASSWORD_MIN_LENGTH")
    
    # Hardware Wallet Configuration
    ENABLE_HARDWARE_WALLET: bool = Field(default=True, env="ENABLE_HARDWARE_WALLET")
    LEDGER_SUPPORTED: bool = Field(default=True, env="LEDGER_SUPPORTED")
    TREZOR_SUPPORTED: bool = Field(default=True, env="TREZOR_SUPPORTED")
    KEEPKEY_SUPPORTED: bool = Field(default=True, env="KEEPKEY_SUPPORTED")
    HW_WALLET_TIMEOUT_SECONDS: int = Field(default=30, env="HW_WALLET_TIMEOUT_SECONDS")
    
    # TRON Configuration
    TRON_NETWORK: str = Field(default="mainnet", env="TRON_NETWORK")
    TRON_SIGNATURE_MESSAGE: str = Field(
        default="Sign this message to authenticate with Lucid: {timestamp}",
        env="TRON_SIGNATURE_MESSAGE"
    )
    TRON_ADDRESS_PREFIX: str = Field(default="T", env="TRON_ADDRESS_PREFIX")
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PUBLIC: int = Field(default=100, env="RATE_LIMIT_PUBLIC")  # per minute
    RATE_LIMIT_AUTHENTICATED: int = Field(default=1000, env="RATE_LIMIT_AUTHENTICATED")
    RATE_LIMIT_ADMIN: int = Field(default=10000, env="RATE_LIMIT_ADMIN")
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    
    # Audit Logging Configuration
    AUDIT_LOG_ENABLED: bool = Field(default=True, env="AUDIT_LOG_ENABLED")
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=90, env="AUDIT_LOG_RETENTION_DAYS")
    AUDIT_LOG_SENSITIVE_FIELDS: List[str] = Field(
        default=["password", "private_key", "signature"],
        env="AUDIT_LOG_SENSITIVE_FIELDS"
    )
    
    # Session Configuration
    SESSION_CLEANUP_INTERVAL_HOURS: int = Field(default=1, env="SESSION_CLEANUP_INTERVAL_HOURS")
    SESSION_MAX_CONCURRENT_PER_USER: int = Field(default=5, env="SESSION_MAX_CONCURRENT_PER_USER")
    SESSION_IDLE_TIMEOUT_MINUTES: int = Field(default=30, env="SESSION_IDLE_TIMEOUT_MINUTES")
    
    # API Gateway Integration
    API_GATEWAY_URL: str = Field(
        default="http://api-gateway:8080",
        env="API_GATEWAY_URL"
    )
    
    # Service Mesh Integration
    SERVICE_MESH_ENABLED: bool = Field(default=False, env="SERVICE_MESH_ENABLED")
    CONSUL_HOST: str = Field(default="consul:8500", env="CONSUL_HOST")
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    HEALTH_CHECK_INTERVAL_SECONDS: int = Field(default=30, env="HEALTH_CHECK_INTERVAL_SECONDS")
    
    # Backup Configuration
    BACKUP_ENABLED: bool = Field(default=True, env="BACKUP_ENABLED")
    BACKUP_INTERVAL_HOURS: int = Field(default=24, env="BACKUP_INTERVAL_HOURS")
    BACKUP_RETENTION_DAYS: int = Field(default=30, env="BACKUP_RETENTION_DAYS")
    
    @validator("JWT_SECRET_KEY")
    def validate_jwt_secret(cls, v):
        """Validate JWT secret key is set and has minimum length"""
        if not v or v == "":
            raise ValueError("JWT_SECRET_KEY must be set")
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return v
    
    @validator("TRON_NETWORK")
    def validate_tron_network(cls, v):
        """Validate TRON network is valid"""
        valid_networks = ["mainnet", "testnet", "nile", "shasta"]
        if v not in valid_networks:
            raise ValueError(f"TRON_NETWORK must be one of {valid_networks}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper
    
    @validator("CORS_ORIGINS", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Custom env var parser"""
            if field_name == "CORS_ORIGINS":
                return [origin.strip() for origin in raw_val.split(",")]
            return raw_val


# Initialize settings
settings = Settings()

# Export settings validation function
def validate_settings():
    """Validate all settings are properly configured"""
    errors = []
    
    # Check required environment variables
    if not settings.JWT_SECRET_KEY:
        errors.append("JWT_SECRET_KEY is required")
    
    if not settings.MONGODB_URI:
        errors.append("MONGODB_URI is required")
    
    if not settings.REDIS_URI:
        errors.append("REDIS_URI is required")
    
    # Check port ranges
    if not (1024 <= settings.AUTH_SERVICE_PORT <= 65535):
        errors.append(f"AUTH_SERVICE_PORT must be between 1024 and 65535")
    
    # Check token expiry values
    if settings.ACCESS_TOKEN_EXPIRE_MINUTES < 1:
        errors.append("ACCESS_TOKEN_EXPIRE_MINUTES must be at least 1")
    
    if settings.REFRESH_TOKEN_EXPIRE_DAYS < 1:
        errors.append("REFRESH_TOKEN_EXPIRE_DAYS must be at least 1")
    
    # Check rate limits
    if settings.RATE_LIMIT_PUBLIC < 1:
        errors.append("RATE_LIMIT_PUBLIC must be at least 1")
    
    if errors:
        raise ValueError(f"Configuration validation failed: {', '.join(errors)}")
    
    return True


# Export configuration summary
def get_config_summary():
    """Get configuration summary (without secrets)"""
    return {
        "service": settings.SERVICE_NAME,
        "environment": settings.ENVIRONMENT,
        "port": settings.AUTH_SERVICE_PORT,
        "debug": settings.DEBUG,
        "features": {
            "hardware_wallet": settings.ENABLE_HARDWARE_WALLET,
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
            "audit_logging": settings.AUDIT_LOG_ENABLED,
            "service_mesh": settings.SERVICE_MESH_ENABLED,
            "metrics": settings.METRICS_ENABLED
        },
        "token_expiry": {
            "access_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            "refresh_days": settings.REFRESH_TOKEN_EXPIRE_DAYS
        },
        "tron": {
            "network": settings.TRON_NETWORK
        }
    }

