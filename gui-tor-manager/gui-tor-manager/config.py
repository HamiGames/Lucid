"""
GUI Tor Manager Configuration
Pydantic-based settings management following container-design.md pattern
Environment variable validation with no hardcoding
"""

import os
from typing import Optional
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class GuiTorManagerSettings(BaseSettings):
    """Main settings for GUI Tor Manager service"""
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # Service Configuration
    SERVICE_NAME: str = Field(
        default="lucid-gui-tor-manager",
        description="Service name for identification"
    )
    PORT: int = Field(
        default=8097,
        description="FastAPI service port (must be 1-65535)"
    )
    HOST: str = Field(
        default="0.0.0.0",
        description="FastAPI host binding (must not be localhost/127.0.0.1)"
    )
    SERVICE_URL: str = Field(
        default="http://lucid-gui-tor-manager:8097",
        description="Service URL for service discovery"
    )
    
    # Environment
    LUCID_ENV: str = Field(
        default="production",
        description="Environment (production, staging, development)"
    )
    LUCID_PLATFORM: str = Field(
        default="arm64",
        description="Platform architecture (arm64, amd64)"
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    DEBUG: bool = Field(
        default=False,
        description="Debug mode flag"
    )
    
    # Tor Proxy Connection
    TOR_PROXY_URL: str = Field(
        default="http://tor-proxy:9051",
        description="Tor proxy control port URL (must not be localhost)"
    )
    TOR_PROXY_HOST: str = Field(
        default="tor-proxy",
        description="Tor proxy service host name"
    )
    TOR_SOCKS_PORT: int = Field(
        default=9050,
        description="Tor SOCKS proxy port (reference only)"
    )
    TOR_CONTROL_PORT: int = Field(
        default=9051,
        description="Tor control port (reference only)"
    )
    
    # Tor Configuration
    TOR_DATA_DIR: str = Field(
        default="/app/tor-data",
        description="Tor data directory path"
    )
    TOR_LOG_LEVEL: str = Field(
        default="notice",
        description="Tor logging level"
    )
    GUI_TOR_INTEGRATION: bool = Field(
        default=True,
        description="Enable GUI Tor integration"
    )
    ONION_ADDRESS_MASKING: bool = Field(
        default=True,
        description="Enable onion address masking"
    )
    
    # Optional: Database URLs (if state storage needed)
    MONGODB_URL: Optional[str] = Field(
        default=None,
        description="MongoDB connection URL for persistent state"
    )
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL for caching"
    )
    
    @field_validator("HOST")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Ensure HOST is not localhost (must use service name)"""
        if v in ("localhost", "127.0.0.1", "::1"):
            raise ValueError(
                f"HOST cannot be '{v}'. Use service name (e.g., 'lucid-gui-tor-manager')"
            )
        return v
    
    @field_validator("PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range"""
        if not 1 <= v <= 65535:
            raise ValueError(f"PORT must be between 1 and 65535, got {v}")
        return v
    
    @field_validator("TOR_PROXY_URL")
    @classmethod
    def validate_tor_proxy_url(cls, v: str) -> str:
        """Ensure TOR_PROXY_URL uses service name, not localhost"""
        if "localhost" in v.lower() or "127.0.0.1" in v:
            raise ValueError(
                f"TOR_PROXY_URL cannot use localhost: {v}. Use service name: http://tor-proxy:9051"
            )
        return v
    
    @field_validator("MONGODB_URL")
    @classmethod
    def validate_mongodb_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate MongoDB URL format if provided"""
        if v is None:
            return v
        if "localhost" in v.lower() or "127.0.0.1" in v:
            raise ValueError(
                f"MONGODB_URL cannot use localhost: {v}. Use service name"
            )
        if not v.startswith("mongodb://"):
            raise ValueError(f"MONGODB_URL must start with 'mongodb://': {v}")
        return v
    
    @field_validator("REDIS_URL")
    @classmethod
    def validate_redis_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate Redis URL format if provided"""
        if v is None:
            return v
        if "localhost" in v.lower() or "127.0.0.1" in v:
            raise ValueError(
                f"REDIS_URL cannot use localhost: {v}. Use service name"
            )
        if not v.startswith("redis://"):
            raise ValueError(f"REDIS_URL must start with 'redis://': {v}")
        return v


class GuiTorManagerConfigManager:
    """Configuration manager for GUI Tor Manager"""
    
    _instance: Optional["GuiTorManagerConfigManager"] = None
    _settings: Optional[GuiTorManagerSettings] = None
    
    def __new__(cls) -> "GuiTorManagerConfigManager":
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(GuiTorManagerConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize configuration"""
        if self._settings is None:
            try:
                self._settings = GuiTorManagerSettings()
            except Exception as e:
                raise RuntimeError(f"Failed to load configuration: {e}")
    
    @property
    def settings(self) -> GuiTorManagerSettings:
        """Get settings instance"""
        if self._settings is None:
            self.__init__()
        return self._settings
    
    def reload(self) -> None:
        """Reload configuration from environment"""
        self._settings = GuiTorManagerSettings()
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get configuration value"""
        if hasattr(self._settings, key):
            return getattr(self._settings, key)
        return default
    
    def verify_critical_settings(self) -> None:
        """Verify all critical settings are configured"""
        critical_settings = [
            "SERVICE_NAME",
            "PORT",
            "HOST",
            "SERVICE_URL",
            "TOR_PROXY_URL",
        ]
        
        for setting in critical_settings:
            value = getattr(self._settings, setting, None)
            if value is None:
                raise RuntimeError(f"Critical setting '{setting}' is not configured")


# Create singleton instance
_config_manager = None


def get_config() -> GuiTorManagerConfigManager:
    """Get or create config manager singleton"""
    global _config_manager
    if _config_manager is None:
        _config_manager = GuiTorManagerConfigManager()
    return _config_manager
