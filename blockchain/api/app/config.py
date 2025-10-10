from __future__ import annotations

import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Service
    SERVICE_NAME: str = Field(default="blockchain-core")
    VERSION: str = Field(default=os.getenv("SERVICE_VERSION", "0.1.0"))

    # HTTP
    API_HOST: str = Field(default=os.getenv("API_HOST", "0.0.0.0"))
    API_PORT: int = Field(default=int(os.getenv("API_PORT", "8084")))
    LOG_LEVEL: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))

    # MongoDB
    MONGO_URI: str = Field(
        default=os.getenv(
            "MONGO_URI",
            "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin&retryWrites=false&directConnection=true",
        )
    )
    MONGO_DB: str = Field(default=os.getenv("MONGO_DB", "lucid"))

    # Key encryption (Fernet requires 32-byte urlsafe base64 key)
    KEY_ENC_SECRET: str = Field(
        default=os.getenv("KEY_ENC_SECRET", "")
    )  # prefer supplying; otherwise an ephemeral will be used

    # Tron / Chain
    TRON_NETWORK: str = Field(
        default=os.getenv("TRON_NETWORK", "mainnet")
    )  # mainnet | shasta
    TRONGRID_API_KEY: str = Field(
        default=os.getenv("TRONGRID_API_KEY", "")
    )  # optional but recommended
    TRON_HTTP_ENDPOINT: str = Field(
        default=os.getenv("TRON_HTTP_ENDPOINT", "")
    )  # override; else derived by network

    # Optional metadata (kept consistent with earlier naming)
    BLOCK_ONION: str = Field(
        default=os.getenv("BLOCK_ONION", "")
    )  # e.g., 56-char .onion for the block node
    BLOCK_RPC_URL: str = Field(default=os.getenv("BLOCK_RPC_URL", ""))

    model_config = SettingsConfigDict(
        env_prefix="BLOCKCHAIN_", env_file=".env.api", extra="ignore"
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
