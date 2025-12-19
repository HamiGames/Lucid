"""
Configuration Module

This module contains configuration settings for the Blockchain API.
Includes database connections, Redis settings, and other configuration options.
"""

import os
from typing import Optional, List
from pydantic import Field, AliasChoices, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )
    
    # API Settings
    API_TITLE: str = "Lucid Blockchain API"
    API_VERSION: str = "1.0.0"
    API_DESCRIPTION: str = "API for the lucid_blocks blockchain system with PoOT consensus"
    
    # Server Settings
    HOST: str = os.getenv("API_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("API_PORT", os.getenv("BLOCKCHAIN_ENGINE_PORT", "8084")))
    DEBUG: bool = os.getenv("API_DEBUG", "false").lower() in ("true", "1", "yes")
    
    # Database Settings - accepts MONGODB_URL or DATABASE_URL
    DATABASE_URL: str = Field(
        default=...,
        validation_alias=AliasChoices("MONGODB_URL", "DATABASE_URL")
    )
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", os.getenv("MONGO_DB", "lucid_blockchain"))
    
    # Redis Settings
    REDIS_URL: str = ...
    
    # Security Settings - accepts BLOCKCHAIN_SECRET_KEY or SECRET_KEY
    SECRET_KEY: str = Field(
        default=...,
        validation_alias=AliasChoices("BLOCKCHAIN_SECRET_KEY", "SECRET_KEY")
    )
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
    BLOCK_TIME: int = int(os.getenv("BLOCK_TIME", os.getenv("LUCID_BLOCK_TIME", os.getenv("CONSENSUS_BLOCK_TIME_SECONDS", "120"))))
    MAX_TRANSACTIONS_PER_BLOCK: int = int(os.getenv("MAX_TRANSACTIONS_PER_BLOCK", os.getenv("LUCID_MAX_BLOCK_TXS", "1000")))
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    
    # Redis connection details (derived from REDIS_URL if needed)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    @field_validator("CORS_ORIGINS", "CORS_METHODS", "CORS_HEADERS", mode="before")
    @classmethod
    def parse_cors_list(cls, v):
        """Parse CORS list fields from string or list."""
        if v is None or v == "":
            return ["*"]  # Default to allow all
        if isinstance(v, str):
            # Handle comma-separated strings
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, list):
            return v
        return ["*"]  # Fallback to default
    
    @model_validator(mode="before")
    @classmethod
    def check_env_aliases(cls, data):
        """Check for alternative environment variable names and parse CORS fields."""
        if isinstance(data, dict):
            # Check for DATABASE_URL alias (MONGODB_URL)
            if "DATABASE_URL" not in data and "MONGODB_URL" in data:
                data["DATABASE_URL"] = data["MONGODB_URL"]
            # Check for SECRET_KEY alias (BLOCKCHAIN_SECRET_KEY)
            if "SECRET_KEY" not in data and "BLOCKCHAIN_SECRET_KEY" in data:
                data["SECRET_KEY"] = data["BLOCKCHAIN_SECRET_KEY"]
            
            # Handle CORS_ORIGINS - parse string values before pydantic-settings tries to parse as JSON
            for cors_field in ["CORS_ORIGINS", "CORS_METHODS", "CORS_HEADERS"]:
                if cors_field in data:
                    value = data[cors_field]
                    if value is None or value == "":
                        data[cors_field] = ["*"]
                    elif isinstance(value, str):
                        # Parse comma-separated string or single value
                        if value.strip() == "*":
                            data[cors_field] = ["*"]
                        else:
                            # Split comma-separated values
                            items = [item.strip() for item in value.split(",") if item.strip()]
                            data[cors_field] = items if items else ["*"]
                    # If it's already a list, leave it as is
        return data

# Global settings instance
settings = Settings()

# Environment-specific overrides
def get_settings() -> Settings:
    """Get application settings with environment-specific overrides."""
    return settings