"""
Configuration Management for GUI Hardware Manager
Uses Pydantic Settings for environment variable validation
Aligned with docker-compose.gui-integration.yml naming conventions
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Regex patterns for URL validation (compiled at module level)
LOCALHOST_PATTERN = re.compile(r'\blocalhost\b', re.IGNORECASE)
IP_127_PATTERN = re.compile(r'\b127\.0\.0\.1\b')


class GuiHardwareManagerSettings(BaseSettings):
    """Configuration settings for GUI Hardware Manager service"""

    # Service Configuration (standardized naming)
    PORT: int = Field(default=8099, description="Service port")
    HOST: str = Field(default="0.0.0.0", description="Service host")
    SERVICE_NAME: str = Field(default="lucid-gui-hardware-manager", description="Service name")
    SERVICE_URL: str = Field(default="http://lucid-gui-hardware-manager:8099", description="Service URL for discovery")

    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # Environment
    LUCID_ENV: str = Field(default="production", description="Environment (production/staging/development)")
    LUCID_PLATFORM: str = Field(default="arm64", description="Platform (arm64/amd64)")

    # Database Configuration (Required for persistent state)
    MONGODB_URL: str = Field(default="", description="MongoDB connection URL")
    REDIS_URL: str = Field(default="", description="Redis connection URL")

    # Integration Service URLs (Required)
    API_GATEWAY_URL: str = Field(default="http://api-gateway:8080", description="API Gateway URL")
    AUTH_SERVICE_URL: str = Field(default="http://lucid-auth-service:8089", description="Auth Service URL")
    GUI_API_BRIDGE_URL: str = Field(default="http://gui-api-bridge:8102", description="GUI API Bridge URL")
    TOR_PROXY_URL: str = Field(default="http://tor-proxy:9051", description="Tor proxy control port")

    # Security Configuration
    JWT_SECRET_KEY: str = Field(default="", description="JWT secret key")

    # Hardware Wallet Configuration
    HARDWARE_WALLET_ENABLED: bool = Field(default=True, description="Enable hardware wallet support")
    LEDGER_ENABLED: bool = Field(default=True, description="Enable Ledger support")
    LEDGER_VENDOR_ID: str = Field(default="0x2c97", description="Ledger USB vendor ID")
    TREZOR_ENABLED: bool = Field(default=True, description="Enable Trezor support")
    KEEPKEY_ENABLED: bool = Field(default=True, description="Enable KeepKey support")
    TRON_WALLET_SUPPORT: bool = Field(default=True, description="Enable TRON wallet support")
    TRON_RPC_URL: str = Field(default="https://api.trongrid.io", description="TRON RPC endpoint")
    TRON_API_KEY: str = Field(default="", description="TRON API key (optional)")

    # Device Management
    USB_DEVICE_SCAN_INTERVAL: int = Field(default=5, description="USB device scan interval in seconds")
    USB_DEVICE_TIMEOUT: int = Field(default=30, description="USB device operation timeout in seconds")
    DEVICE_CONNECTION_TIMEOUT: int = Field(default=60, description="Device connection timeout in seconds")
    MAX_CONCURRENT_DEVICES: int = Field(default=5, description="Maximum concurrent device connections")

    # Transaction Signing
    SIGN_REQUEST_TIMEOUT: int = Field(default=300, description="Signature request timeout in seconds")
    MAX_PENDING_SIGN_REQUESTS: int = Field(default=100, description="Maximum pending signature requests")

    # CORS Configuration
    CORS_ENABLED: bool = Field(default=True, description="Enable CORS")
    CORS_ORIGINS: str = Field(
        default="http://user-interface:3001,http://node-interface:3002,http://admin-interface:8120,http://localhost:3001,http://localhost:3002,http://localhost:8120",
        description="CORS allowed origins (comma-separated)"
    )
    CORS_METHODS: str = Field(default="GET,POST,PUT,DELETE,OPTIONS", description="CORS allowed methods")
    CORS_HEADERS: str = Field(default="*", description="CORS allowed headers")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="CORS allow credentials")

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Requests per minute")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="Rate limit window in seconds")
    RATE_LIMIT_BURST: int = Field(default=200, description="Burst size for rate limiting")

    # Monitoring & Health Checks
    METRICS_ENABLED: bool = Field(default=True, description="Enable metrics collection")
    HEALTH_CHECK_INTERVAL: int = Field(default=60, description="Health check interval in seconds")

    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=True,
        extra='ignore'
    )

    @field_validator('MONGODB_URL')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("MONGODB_URL must not use localhost. Use service name (e.g., lucid-mongodb)")
        return v

    @field_validator('REDIS_URL')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("REDIS_URL must not use localhost. Use service name (e.g., lucid-redis)")
        return v

    @field_validator('API_GATEWAY_URL', 'AUTH_SERVICE_URL', 'GUI_API_BRIDGE_URL', 'TOR_PROXY_URL')
    @classmethod
    def validate_service_urls(cls, v: str) -> str:
        """Validate service URLs don't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("Service URLs must not use localhost. Use service names instead.")
        return v

    @field_validator('PORT')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range"""
        if not 1 <= v <= 65535:
            raise ValueError(f"PORT must be between 1 and 65535, got {v}")
        return v

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    def get_cors_methods_list(self) -> List[str]:
        """Parse CORS methods string into list"""
        return [m.strip() for m in self.CORS_METHODS.split(",")]

    def get_cors_headers_list(self) -> List[str]:
        """Parse CORS headers string into list"""
        if self.CORS_HEADERS == "*":
            return ["*"]
        return [h.strip() for h in self.CORS_HEADERS.split(",")]


# Global settings instance
_settings_instance: Optional[GuiHardwareManagerSettings] = None


def get_settings() -> GuiHardwareManagerSettings:
    """Get configuration settings (singleton pattern)"""
    global _settings_instance
    if _settings_instance is None:
        try:
            _settings_instance = GuiHardwareManagerSettings()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    return _settings_instance
