"""
Configuration Module

This module contains configuration settings for the Blockchain API.
Includes database connections, Redis settings, and other configuration options.
"""

import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_TITLE: str = "Lucid Blockchain API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for the lucid_blocks blockchain system with PoOT consensus"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8084
    DEBUG: bool = False
    
    # Database Settings
    DATABASE_URL: str = "mongodb://localhost:27017/lucid_blockchain"
    DATABASE_NAME: str = "lucid_blockchain"
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Security Settings
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # Rate Limiting Settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE: str = "redis"  # "memory" or "redis"
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Blockchain Settings
    BLOCKCHAIN_NETWORK: str = "lucid_blocks_mainnet"
    CONSENSUS_ALGORITHM: str = "PoOT"
    BLOCK_TIME: int = 10  # seconds
    MAX_TRANSACTIONS_PER_BLOCK: int = 1000
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()

# Environment-specific overrides
def get_settings() -> Settings:
    """Get application settings with environment-specific overrides."""
    return settings