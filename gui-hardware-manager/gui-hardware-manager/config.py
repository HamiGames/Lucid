"""
Configuration Management for GUI Hardware Manager
Uses Pydantic Settings for environment variable validation
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

    # Service Configuration
    gui_hardware_manager_host: str = Field(default="0.0.0.0")
    gui_hardware_manager_port: int = Field(default=8099)
    gui_hardware_manager_url: str = Field(default="")
    service_name: str = Field(default="lucid-gui-hardware-manager")

    # Logging Configuration
    log_level: str = Field(default="INFO")
    debug: bool = Field(default=False)

    # Environment
    lucid_env: str = Field(default="production")
    lucid_platform: str = Field(default="arm64")
    project_root: str = Field(default="/mnt/myssd/Lucid/Lucid")

    # Database Configuration (Required)
    mongodb_url: str = Field(default="")
    redis_url: str = Field(default="")

    # Integration Service URLs (Required)
    api_gateway_url: str = Field(default="")
    auth_service_url: str = Field(default="")
    gui_api_bridge_url: str = Field(default="")

    # Security Configuration
    jwt_secret_key: str = Field(default="")

    # Hardware Wallet Configuration
    hardware_wallet_enabled: bool = Field(default=True)
    ledger_enabled: bool = Field(default=True)
    ledger_vendor_id: str = Field(default="0x2c97")
    trezor_enabled: bool = Field(default=True)
    keepkey_enabled: bool = Field(default=True)
    tron_wallet_support: bool = Field(default=True)
    tron_rpc_url: str = Field(default="https://api.trongrid.io")
    tron_api_key: str = Field(default="")

    # Device Management
    usb_device_scan_interval: int = Field(default=5)
    usb_device_timeout: int = Field(default=30)
    device_connection_timeout: int = Field(default=60)
    max_concurrent_devices: int = Field(default=5)

    # Transaction Signing
    sign_request_timeout: int = Field(default=300)
    max_pending_sign_requests: int = Field(default=100)

    # CORS Configuration
    cors_enabled: bool = Field(default=True)
    cors_origins: str = Field(default="*")
    cors_methods: str = Field(default="GET,POST,PUT,DELETE,OPTIONS")
    cors_headers: str = Field(default="*")
    cors_allow_credentials: bool = Field(default=True)

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests: int = Field(default=100)
    rate_limit_window: int = Field(default=60)
    rate_limit_burst: int = Field(default=200)

    # Monitoring
    metrics_enabled: bool = Field(default=True)
    health_check_interval: int = Field(default=60)

    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

    @field_validator('mongodb_url')
    @classmethod
    def validate_mongodb_url(cls, v: str) -> str:
        """Validate MongoDB URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("MONGODB_URL must not use localhost. Use service name (e.g., lucid-mongodb)")
        return v

    @field_validator('redis_url')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL doesn't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("REDIS_URL must not use localhost. Use service name (e.g., lucid-redis)")
        return v

    @field_validator('api_gateway_url', 'auth_service_url', 'gui_api_bridge_url')
    @classmethod
    def validate_service_urls(cls, v: str) -> str:
        """Validate service URLs don't use localhost"""
        if v and (LOCALHOST_PATTERN.search(v) or IP_127_PATTERN.search(v)):
            raise ValueError("Service URLs must not use localhost. Use service names instead.")
        return v

    def get_cors_origins_list(self) -> List[str]:
        """Parse CORS origins string into list"""
        if self.cors_origins == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",")]

    def get_cors_methods_list(self) -> List[str]:
        """Parse CORS methods string into list"""
        return [m.strip() for m in self.cors_methods.split(",")]

    def get_cors_headers_list(self) -> List[str]:
        """Parse CORS headers string into list"""
        if self.cors_headers == "*":
            return ["*"]
        return [h.strip() for h in self.cors_headers.split(",")]


# Global settings instance
def get_settings() -> GuiHardwareManagerSettings:
    """Get configuration settings"""
    return GuiHardwareManagerSettings()
