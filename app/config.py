from __future__ import annotations

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main Lucid RDP application configuration."""
    
    # Service Identity
    SERVICE_NAME: str = Field(default="lucid-rdp")
    VERSION: str = Field(default=os.getenv("SERVICE_VERSION", "0.1.0"))
    LUCID_ENV: str = Field(default=os.getenv("LUCID_ENV", "dev"))
    
    # Network Configuration
    API_HOST: str = Field(default=os.getenv("API_HOST", "0.0.0.0"))
    API_PORT: int = Field(default=int(os.getenv("API_PORT", "8080")))
    LOG_LEVEL: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    
    # MongoDB Configuration
    MONGO_URI: str = Field(
        default=os.getenv(
            "MONGO_URI",
            "mongodb://lucid:lucid@127.0.0.1:27019/lucid?authSource=admin&retryWrites=false&directConnection=true",
        )
    )
    MONGO_DB: str = Field(default=os.getenv("MONGO_DB", "lucid"))
    
    # Security Configuration
    KEY_ENC_SECRET: str = Field(
        default=os.getenv("KEY_ENC_SECRET", "")
    )  # 32-byte urlsafe base64 key for Fernet encryption
    
    # Tor Configuration
    TOR_ENABLED: bool = Field(default=os.getenv("TOR_ENABLED", "true").lower() == "true")
    TOR_SOCKS_PORT: int = Field(default=int(os.getenv("TOR_SOCKS_PORT", "9050")))
    TOR_CONTROL_PORT: int = Field(default=int(os.getenv("TOR_CONTROL_PORT", "9051")))
    
    # Blockchain Configuration
    TRON_NETWORK: str = Field(
        default=os.getenv("TRON_NETWORK", "mainnet")
    )  # mainnet | shasta
    TRONGRID_API_KEY: str = Field(
        default=os.getenv("TRONGRID_API_KEY", "")
    )  # optional but recommended
    TRON_HTTP_ENDPOINT: str = Field(
        default=os.getenv("TRON_HTTP_ENDPOINT", "")
    )  # override; else derived by network
    
    # RDP Configuration
    RDP_SESSIONS_PATH: str = Field(default=os.getenv("RDP_SESSIONS_PATH", "/data/sessions"))
    RDP_RECORDINGS_PATH: str = Field(default=os.getenv("RDP_RECORDINGS_PATH", "/data/recordings"))
    XRDP_PORT: int = Field(default=int(os.getenv("XRDP_PORT", "3389")))
    MAX_CONCURRENT_SESSIONS: int = Field(default=int(os.getenv("MAX_CONCURRENT_SESSIONS", "5")))
    
    # Session Configuration
    CHUNK_SIZE: int = Field(default=int(os.getenv("CHUNK_SIZE", "16777216")))  # 16MB
    COMPRESSION_LEVEL: int = Field(default=int(os.getenv("COMPRESSION_LEVEL", "3")))
    SESSION_TIMEOUT_MINUTES: int = Field(default=int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")))
    
    # Data Storage
    DATA_DIR: str = Field(default=os.getenv("DATA_DIR", "/opt/lucid/data"))
    
    # Optional metadata (kept consistent with project naming)
    BLOCK_ONION: str = Field(
        default=os.getenv("BLOCK_ONION", "")
    )  # e.g., 56-char .onion for the block node
    BLOCK_RPC_URL: str = Field(default=os.getenv("BLOCK_RPC_URL", ""))

    model_config = SettingsConfigDict(
        env_prefix="LUCID_", 
        env_file=".env", 
        extra="ignore"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings instance."""
    return Settings()
