"""
Configuration Management

File: 03_api_gateway/api/app/config.py
Purpose: Centralized configuration for the API Gateway service using Pydantic settings.

Architecture Notes:
- BLOCKCHAIN_CORE_URL: Points to lucid_blocks (on-chain blockchain system)
- TRON_PAYMENT_URL: Points to isolated TRON payment service
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict  # pyright: ignore[reportMissingImports]
from functools import lru_cache
import json
import importlib
import secrets

config_path = importlib.import_module("app.infrastructure.kubernetes.01_configmaps.api-gateway-config.yaml")
CONFIG = os.getenv("CONFIG", config_path())
SETTINGS = os.getenv("SETTINGS")
if os.path.exists(SETTINGS):
    with open(SETTINGS, 'r') as f:
        SETTINGS = json.load(f)
else:
    SETTINGS = {}
if os.path.exists(CONFIG):
    with open(CONFIG, config_path()) as f:
        CONFIG = json.load(f)
else:
    CONFIG = {}




class Settings(BaseSettings):
    """Application settings"""
   
    # Service Configuration
    API_GATEWAY_SERVICE_NAME: str = Field(env="API_GATEWAY_SERVICE_NAME")
    API_VERSION: str = Field(default="v1", env="API_VERSION")
    DEBUG: bool = Field(default=False, env="DEBUG")
    ENVIRONMENT: str = Field( env="ENVIRONMENT")
    
    # Port Configuration
    HTTP_GATEWAY_PORT: int = Field(env="HTTP_GATEWAY_PORT")
    HTTPS_GATEWAY_PORT: int = Field( env="HTTPS_GATEWAY_PORT")
    
    # Security Configuration
    JWT_SECRET_KEY: str = Field(env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Database Configuration (accepts MONGODB_URI or MONGODB_URL)
    MONGODB_URI: str = Field(env="MONGODB_URI")
    MONGODB_URL: str = Field( env="MONGODB_URL")
    MONGODB_DATABASE: str = Field(env="MONGODB_GATEWAY_DB")
    REDIS_URL: str = Field(env="REDIS_URL")
    REDIS_URI: str = Field(env="REDIS_URI")
    
    @property
    def mongodb_connection_string(self) -> str:
        """Get MongoDB connection string (supports both URI and URL env vars)"""
        return self.MONGODB_URI or self.MONGODB_URL
    @property
    def redis_connection_string(self) -> str:
        return self.REDIS_URL or self.REDIS_URI
    # Backend Service URLs
    # lucid_blocks = on-chain blockchain system
    BLOCKCHAIN_CORE_URL: str = Field( env="BLOCKCHAIN_CORE_URL")
    SESSION_MANAGEMENT_URL: str = Field( env="SESSION_MANAGEMENT_URL")
    AUTH_SERVICE_URL: str = Field(env="AUTH_SERVICE_URL")
    # TRON = isolated payment service (NOT part of lucid_blocks)
    TRON_PAYMENT_URL: str = Field( env="TRON_PAYMENT_URL")
    # GUI Services
    GUI_API_BRIDGE_URL: str = Field( env="GUI_API_BRIDGE_URL")
    GUI_DOCKER_MANAGER_URL: str = Field( env="GUI_DOCKER_MANAGER_URL")
    GUI_TOR_MANAGER_URL: str = Field( env="GUI_TOR_MANAGER_URL")
    GUI_HARDWARE_MANAGER_URL: str = Field( env="GUI_HARDWARE_MANAGER_URL")
    # TRON Support Services
    TRON_PAYOUT_ROUTER_URL: str = Field( env="TRON_PAYOUT_ROUTER_URL")
    TRON_WALLET_MANAGER_URL: str = Field( env="TRON_WALLET_MANAGER_URL")
    TRON_USDT_MANAGER_URL: str = Field( env="TRON_USDT_MANAGER_URL")
    
    # Rate Limiting Configuration
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(default=100, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    RATE_LIMIT_BURST_SIZE: int = Field(default=200, env="RATE_LIMIT_BURST_SIZE")
    
    # SSL Configuration
    SSL_ENABLED: bool = Field(default=True, env="SSL_ENABLED")
    SSL_CERT_PATH: Optional[str] = Field(None, env="SSL_CERT_PATH")
    SSL_KEY_PATH: Optional[str] = Field(None, env="SSL_KEY_PATH")
    
    # CORS Configuration
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    CORS_ORIGINS: List[str] = Field(default=["*"], env="CORS_ORIGINS")
    
    # Logging Configuration
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")
    
    # Monitoring Configuration
    METRICS_ENABLED: bool = Field(default=True)
    HEALTH_CHECK_INTERVAL: str = Field(default="30")
   
    
    @model_validator(mode="before")
    @classmethod
    def parse_list_fields(cls, data):
        """Parse List fields from environment variables before pydantic-settings tries to parse as JSON."""
        if isinstance(data, dict):
            # Handle ALLOWED_HOSTS and CORS_ORIGINS
            for list_field in ["ALLOWED_HOSTS", "CORS_ORIGINS"]:
                if list_field in data:
                    value = data[list_field]
                    if value is None or value == "":
                        data[list_field] = ["*"]
                    elif isinstance(value, str):
                        # Handle single "*" value
                        if value.strip() == "*":
                            data[list_field] = ["*"]
                        else:
                            # Split comma-separated values
                            items = [item.strip() for item in value.split(",") if item.strip()]
                            data[list_field] = items if items else ["*"]
                    # If it's already a list, leave it as is
        return data
    
    @field_validator('HEALTH_CHECK_INTERVAL', mode='before')
    @classmethod
    def parse_health_check_interval(cls, v):
        """Parse health check interval, stripping 's' suffix if present"""
        if isinstance(v, str):
            return v.rstrip('s')
        return str(v)
    
    @property
    def health_check_interval_seconds(self) -> int:
        """Get health check interval as integer seconds"""
        return int(self.HEALTH_CHECK_INTERVAL)
    
    @field_validator('ALLOWED_HOSTS', mode='before')
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse comma-separated allowed hosts"""
        if v is None or v == "":
            return ["*"]  # Default to allow all
        if isinstance(v, str):
            # Handle single "*" value
            if v.strip() == "*":
                return ["*"]
            # Split comma-separated values
            items = [host.strip() for host in v.split(',') if host.strip()]
            return items if items else ["*"]
        if isinstance(v, list):
            return v
        return ["*"]  # Fallback to default
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins"""
        if v is None or v == "":
            return ["*"]  # Default to allow all
        if isinstance(v, str):
            # Handle single "*" value
            if v.strip() == "*":
                return ["*"]
            # Split comma-separated values
            items = [origin.strip() for origin in v.split(',') if origin.strip()]
            return items if items else ["*"]
        if isinstance(v, list):
            return v
        return ["*"]  # Fallback to default
    
    @field_validator('JWT_SECRET_KEY', mode='before')
    @classmethod
    def validate_jwt_secret(cls, v):
        if not v:
            import warnings
            warnings.warn(f"JWT_SECRET_KEY not set - using insecure default for startup")
            import secrets
            return secrets.token_urlsafe(32)
        if len(v) < 32:
            raise ValueError('JWT_SECRET_KEY must be at least 32 characters long')
        return v
    
    @field_validator('BLOCKCHAIN_CORE_URL')
    @classmethod
    def validate_blockchain_url(cls, v):
        """Validate blockchain core URL (should point to lucid_blocks)"""
        if v:
            # Ensure it's pointing to the correct service
            if 'lucid-blocks' not in v and 'lucid_blocks' not in v:
                import warnings
                warnings.warn(
                    f"BLOCKCHAIN_CORE_URL ({v}) should point to lucid_blocks service. "
                    "Ensure this is correct for on-chain blockchain operations."
                )
        return v or ""
    
    @field_validator('TRON_PAYMENT_URL')
    @classmethod
    def validate_tron_url(cls, v):
        """Validate TRON payment URL (should be isolated service)"""
        if v:
            # Ensure it's pointing to isolated payment service
            if 'tron' not in v.lower():
                import warnings
                warnings.warn(
                    f"TRON_PAYMENT_URL ({v}) should point to TRON payment service. "
                    "TRON is an isolated payment service, NOT part of lucid_blocks."
                )
        return v or ""
    
    @field_validator('GUI_API_BRIDGE_URL')
    @classmethod
    def validate_gui_api_bridge_url(cls, v):
        """Validate GUI API Bridge URL (should point to gui_api_bridge service)"""
        if v:
            if 'gui' not in v.lower():
                import warnings
                warnings.warn(
                    f"GUI_API_BRIDGE_URL ({v}) should point to gui_api_bridge service. "
                    "GUI API Bridge is the Electron GUI integration service."
                )
        return v or ""
    
    @field_validator('GUI_DOCKER_MANAGER_URL')
    @classmethod
    def validate_gui_docker_manager_url(cls, v):
        """Validate GUI Docker Manager URL"""
        if v:
            if 'docker' not in v.lower():
                import warnings
                warnings.warn(
                    f"GUI_DOCKER_MANAGER_URL ({v}) should point to gui_docker_manager service."
                )
        return v or ""
    
    @field_validator('GUI_TOR_MANAGER_URL')
    @classmethod
    def validate_gui_tor_manager_url(cls, v):
        """Validate GUI Tor Manager URL"""
        if v:
            if 'tor' not in v.lower():
                import warnings
                warnings.warn(
                    f"GUI_TOR_MANAGER_URL ({v}) should point to gui_tor_manager service."
                )
        return v or ""
    
    @field_validator('GUI_HARDWARE_MANAGER_URL')
    @classmethod
    def validate_gui_hardware_manager_url(cls, v):
        """Validate GUI Hardware Manager URL"""
        if v:
            if 'hardware' not in v.lower():
                import warnings
                warnings.warn(
                    f"GUI_HARDWARE_MANAGER_URL ({v}) should point to gui_hardware_manager service."
                )
        return v or ""
    
    @field_validator('TRON_PAYOUT_ROUTER_URL')
    @classmethod
    def validate_tron_payout_router_url(cls, v):
        """Validate TRON Payout Router URL"""
        if v:
            if 'payout' not in v.lower():
                import warnings
                warnings.warn(
                    f"TRON_PAYOUT_ROUTER_URL ({v}) should point to tron-payout-router service."
                )
        return v or ""
    
    @field_validator('TRON_WALLET_MANAGER_URL')
    @classmethod
    def validate_tron_wallet_manager_url(cls, v):
        """Validate TRON Wallet Manager URL"""
        if v:
            if 'wallet' not in v.lower():
                import warnings
                warnings.warn(
                    f"TRON_WALLET_MANAGER_URL ({v}) should point to tron-wallet-manager service."
                )
        return v or ""
    
    @field_validator('TRON_USDT_MANAGER_URL')
    @classmethod
    def validate_tron_usdt_manager_url(cls, v):
        """Validate TRON USDT Manager URL"""
        if v:
            if 'usdt' not in v.lower():
                import warnings
                warnings.warn(
                    f"TRON_USDT_MANAGER_URL ({v}) should point to tron-usdt-manager service."
                )
        return v or ""
    
    model_config = SettingsConfigDict(
        env_file=['.env.secrets', '.env.api-gateway'],
        case_sensitive=True
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Loads Settings from environment/env files.
    """
    import json
    import logging
    
    logger = logging.getLogger("config")
    
    # Create Settings instance from environment variables and .env files
    settings = Settings()
    
    # Try to load and merge operator settings JSON if it exists
    try:
        operator_settings_path = os.getenv("OPERATOR_SETTINGS_PATH", "operator_settings.json")
        if os.path.exists(operator_settings_path):
            with open(operator_settings_path, 'r') as f:
                operator_settings = json.load(f)
            
            # Merge operator settings into Settings instance
            for key, value in operator_settings.items():
                if hasattr(settings, key):
                    setattr(settings, key, value)
            
            logger.info(f"Loaded operator settings from {operator_settings_path}")
        else:
            logger.debug(f"Operator settings file not found at {operator_settings_path}")
    except Exception as e:
        logger.error(f"Failed to load operator settings: {e}")
    
    return settings
    