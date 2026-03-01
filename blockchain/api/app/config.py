"""
Configuration Module

This module contains configuration settings for the Blockchain API.
Includes database connections, Redis settings, and other configuration options.
"""

import os
from typing import Optional, List
import json
from pydantic import Field, AliasChoices, model_validator, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
        json_schema_extra={
            "CORS_ORIGINS": "Comma-separated list or JSON array of origins"
        }
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
    
    # CORS Settings - Accept string or list, will be converted to list
    CORS_ORIGINS: str = "*"  # Changed to string to avoid JSON parsing issues
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: str = "*"  # Changed to string
    CORS_HEADERS: str = "*"  # Changed to string
    
    # Redis connection details (derived from REDIS_URL if needed)
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    
    @field_validator("CORS_ORIGINS", "CORS_METHODS", "CORS_HEADERS", mode="before")
    @classmethod
    def parse_cors_list(cls, v):
        """Parse CORS list fields from string or list."""
        if v is None or v == "":
            return "*"  # Return string instead of list
        if isinstance(v, str):
            # Keep as string - will be converted to list in model_validator
            return v.strip()
        if isinstance(v, list):
            # Convert list to comma-separated string
            return ",".join(str(item).strip() for item in v if item)
        return "*"  # Fallback to default
    
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
            
            # Ensure CORS fields are strings to avoid JSON parsing errors
            for cors_field in ["CORS_ORIGINS", "CORS_METHODS", "CORS_HEADERS"]:
                if cors_field in data and data[cors_field]:
                    value = data[cors_field]
                    # Convert to string if it's a list
                    if isinstance(value, list):
                        data[cors_field] = ",".join(str(item).strip() for item in value if item)
                    elif isinstance(value, str):
                        # Keep as is
                        pass
                    else:
                        data[cors_field] = "*"
        return data
    
    def get_cors_origins_list(self) -> List[str]:
        """Convert CORS_ORIGINS string to list for FastAPI."""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip()]
    
    def get_cors_methods_list(self) -> List[str]:
        """Convert CORS_METHODS string to list for FastAPI."""
        if self.CORS_METHODS == "*":
            return ["*"]
        return [item.strip() for item in self.CORS_METHODS.split(",") if item.strip()]
    
    def get_cors_headers_list(self) -> List[str]:
        """Convert CORS_HEADERS string to list for FastAPI."""
        if self.CORS_HEADERS == "*":
            return ["*"]
        return [item.strip() for item in self.CORS_HEADERS.split(",") if item.strip()]

# Global settings instance
settings = Settings()

# Environment-specific overrides
def get_settings() -> Settings:
    """Get application settings with environment-specific overrides."""
    return settings