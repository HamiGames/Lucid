"""
LUCID TRON Relay - Configuration
Read-only TRON network relay for distributed caching and verification
NO PRIVATE KEY ACCESS - This service is read-only
"""

import os
from enum import Enum
from typing import Optional, List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RelayMode(str, Enum):
    """Relay operation mode"""
    VALIDATOR = "validator"  # Read-only validation
    CACHE = "cache"  # Caching only
    MONITOR = "monitor"  # Transaction monitoring
    FULL = "full"  # All capabilities


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TronRelaySettings(BaseSettings):
    """TRON Relay service configuration - READ ONLY, NO PRIVATE KEYS"""
    
    model_config = SettingsConfigDict(
        env_file=[".env.tron-relay", ".env.support", ".env.secrets", ".env.foundation", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ==========================================================================
    # SERVICE IDENTIFICATION
    # ==========================================================================
    service_name: str = Field(
        default_factory=lambda: os.getenv("SERVICE_NAME", "lucid-tron-relay"),
        description="Service name"
    )
    service_version: str = Field(default="1.0.0", description="Service version")
    relay_id: str = Field(
        default_factory=lambda: os.getenv("RELAY_ID", "relay-001"),
        description="Unique relay identifier"
    )
    node_id: Optional[str] = Field(
        default_factory=lambda: os.getenv("NODE_ID"),
        description="Associated node ID (if running on a node)"
    )
    
    # ==========================================================================
    # SERVICE CONFIGURATION
    # ==========================================================================
    service_port: int = Field(
        default_factory=lambda: int(os.getenv("SERVICE_PORT", os.getenv("TRON_RELAY_PORT", "8098"))),
        description="Service port"
    )
    service_host: str = Field(
        default_factory=lambda: os.getenv("SERVICE_HOST", os.getenv("BIND_ADDRESS", "0.0.0.0")),
        description="Service host"
    )
    workers: int = Field(
        default_factory=lambda: int(os.getenv("WORKERS", "1")),
        description="Number of workers"
    )
    relay_mode: RelayMode = Field(
        default_factory=lambda: RelayMode(os.getenv("RELAY_MODE", "full")),
        description="Relay operation mode"
    )
    
    # ==========================================================================
    # TRON NETWORK - READ ONLY ACCESS
    # ==========================================================================
    tron_network: str = Field(
        default_factory=lambda: os.getenv("TRON_NETWORK", "mainnet"),
        description="TRON network (mainnet/shasta/nile)"
    )
    tron_rpc_url: str = Field(
        default_factory=lambda: os.getenv("TRON_RPC_URL", "https://api.trongrid.io"),
        description="TRON RPC URL"
    )
    tron_rpc_url_mainnet: str = Field(
        default_factory=lambda: os.getenv("TRON_RPC_URL_MAINNET", "https://api.trongrid.io"),
        description="TRON mainnet RPC URL"
    )
    tron_rpc_url_shasta: str = Field(
        default_factory=lambda: os.getenv("TRON_RPC_URL_SHASTA", "https://api.shasta.trongrid.io"),
        description="TRON shasta testnet RPC URL"
    )
    trongrid_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("TRONGRID_API_KEY"),
        description="TronGrid API key for rate limit increase"
    )
    tron_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("TRON_API_KEY"),
        description="Alternative TRON API key"
    )
    
    # ==========================================================================
    # MASTER CONNECTION (read-only registration)
    # ==========================================================================
    tron_master_url: str = Field(
        default_factory=lambda: os.getenv("TRON_MASTER_URL", os.getenv("TRON_CLIENT_URL", "http://lucid-tron-client:8091")),
        description="TRON master service URL"
    )
    master_registration_enabled: bool = Field(
        default_factory=lambda: os.getenv("MASTER_REGISTRATION_ENABLED", "true").lower() == "true",
        description="Enable registration with master"
    )
    master_heartbeat_interval: int = Field(
        default_factory=lambda: int(os.getenv("MASTER_HEARTBEAT_INTERVAL", "60")),
        description="Heartbeat interval to master (seconds)"
    )
    
    # ==========================================================================
    # CACHE CONFIGURATION
    # ==========================================================================
    cache_enabled: bool = Field(
        default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true",
        description="Enable caching"
    )
    cache_ttl_seconds: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_TTL_SECONDS", "60")),
        description="Cache TTL in seconds"
    )
    cache_max_size_mb: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_MAX_SIZE_MB", "500")),
        description="Maximum cache size in MB"
    )
    cache_block_ttl: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_BLOCK_TTL", "300")),
        description="Block data cache TTL"
    )
    cache_transaction_ttl: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_TRANSACTION_TTL", "3600")),
        description="Transaction data cache TTL"
    )
    cache_account_ttl: int = Field(
        default_factory=lambda: int(os.getenv("CACHE_ACCOUNT_TTL", "30")),
        description="Account data cache TTL"
    )
    
    # ==========================================================================
    # VERIFICATION CONFIGURATION
    # ==========================================================================
    verification_enabled: bool = Field(
        default_factory=lambda: os.getenv("VERIFICATION_ENABLED", "true").lower() == "true",
        description="Enable transaction verification"
    )
    confirmation_threshold: int = Field(
        default_factory=lambda: int(os.getenv("CONFIRMATION_THRESHOLD", "20")),
        description="Required confirmations for verification"
    )
    verification_timeout: int = Field(
        default_factory=lambda: int(os.getenv("VERIFICATION_TIMEOUT", "30")),
        description="Verification timeout in seconds"
    )
    
    # ==========================================================================
    # RATE LIMITING
    # ==========================================================================
    rate_limit_enabled: bool = Field(
        default_factory=lambda: os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
        description="Enable rate limiting"
    )
    rate_limit_requests: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
        description="Rate limit requests per window"
    )
    rate_limit_window: int = Field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_WINDOW", "60")),
        description="Rate limit window in seconds"
    )
    
    # ==========================================================================
    # MONITORING
    # ==========================================================================
    metrics_enabled: bool = Field(
        default_factory=lambda: os.getenv("METRICS_ENABLED", "true").lower() == "true",
        description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        default_factory=lambda: int(os.getenv("METRICS_PORT", "9098")),
        description="Prometheus metrics port"
    )
    health_check_interval: int = Field(
        default_factory=lambda: int(os.getenv("HEALTH_CHECK_INTERVAL", "30")),
        description="Health check interval in seconds"
    )
    
    # ==========================================================================
    # LOGGING
    # ==========================================================================
    log_level: LogLevel = Field(
        default_factory=lambda: LogLevel(os.getenv("LOG_LEVEL", "INFO")),
        description="Logging level"
    )
    log_file: str = Field(
        default_factory=lambda: os.getenv("LOG_FILE", "/app/logs/tron-relay.log"),
        description="Log file path"
    )
    debug: bool = Field(
        default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true",
        description="Debug mode"
    )
    
    # ==========================================================================
    # DATA DIRECTORIES
    # ==========================================================================
    data_directory: str = Field(
        default_factory=lambda: os.getenv("DATA_DIRECTORY", "/data/tron-relay"),
        description="Data directory"
    )
    cache_directory: str = Field(
        default_factory=lambda: os.getenv("CACHE_DIRECTORY", "/data/cache"),
        description="Cache directory"
    )
    
    def get_tron_endpoint(self) -> str:
        """Get the appropriate TRON endpoint based on network"""
        if self.tron_network == "mainnet":
            return self.tron_rpc_url_mainnet
        elif self.tron_network in ["shasta", "testnet"]:
            return self.tron_rpc_url_shasta
        return self.tron_rpc_url
    
    def get_api_key(self) -> Optional[str]:
        """Get the TRON API key (TronGrid or alternative)"""
        return self.trongrid_api_key or self.tron_api_key


# Global configuration instance
config = TronRelaySettings()


def get_config() -> TronRelaySettings:
    """Get the configuration instance"""
    return config

