"""
Configuration Module

This module contains configuration settings for the Blockchain API.
Includes database connections, Redis settings, and other configuration options.
"""

import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_TITLE: str = "Lucid Blockchain API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for the lucid_blocks blockchain system with PoOT consensus"
    
    # Server Settings
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", os.getenv("BLOCKCHAIN_ENGINE_PORT", "8084")))
    DEBUG: bool = os.getenv("API_DEBUG", "false").lower() in ("true", "1", "yes")
    
    # Database Settings (MUST be provided via environment)
    DATABASE_URL: str = ...  # e.g., mongodb://user:pass@host:27017/lucid_blockchain
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", os.getenv("MONGO_DB", "lucid_blockchain"))
    
    # Redis Settings (MUST be provided via environment)
    REDIS_URL: str = ...
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    # Security Settings (MUST be provided via environment)
    SECRET_KEY: str = ...
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Rate Limiting Settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE: str = "redis"  # "memory" or "redis"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Blockchain Settings
    BLOCKCHAIN_NETWORK: str = os.getenv("BLOCKCHAIN_NETWORK", os.getenv("LUCID_NETWORK_ID", "lucid_blocks_mainnet"))
    CONSENSUS_ALGORITHM: str = os.getenv("CONSENSUS_ALGORITHM", "PoOT")
    BLOCK_TIME: int = int(os.getenv("BLOCK_TIME", os.getenv("LUCID_BLOCK_TIME", os.getenv("CONSENSUS_BLOCK_TIME_SECONDS", "120"))))  # ALIGNED: 120s matches SLOT_DURATION_SEC
    MAX_TRANSACTIONS_PER_BLOCK: int = int(os.getenv("MAX_TRANSACTIONS_PER_BLOCK", os.getenv("LUCID_MAX_BLOCK_TXS", "1000")))
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        fields = {
            "DATABASE_URL": {"env": ["MONGODB_URL", "DATABASE_URL"]},
            "REDIS_URL": {"env": ["REDIS_URL"]},
            "SECRET_KEY": {"env": ["BLOCKCHAIN_SECRET_KEY", "SECRET_KEY"]},
        }

# Global settings instance
settings = Settings()

# Environment-specific overrides
def get_settings() -> Settings:
    """Get application settings with environment-specific overrides."""
    return settings